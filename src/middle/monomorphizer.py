"""
Aerix Compiler (arxc) — Generic Monomorphization Engine (Phase 18)
Transforms generic class and function AST templates into zero-cost,
fully monomorphized concrete AST declarations prior to semantic analysis.
Guarantees zero runtime reflection, zero void* boxing, and zero vtable overhead in C99.
"""

import copy
import re
from typing import List, Dict, Set, Tuple, Optional, Any
from src.frontend.ast_nodes import (
    ASTNode, ProgramNode, FunctionDefNode, ParamNode, BlockNode,
    VarDeclNode, AssignNode, IfNode, WhileNode, ForNode, LoopNode,
    BreakNode, ContinueNode, ReturnNode, DeferNode, ExprStmtNode,
    LiteralNode, IdentifierNode, BinaryOpNode, UnaryOpNode, CallNode,
    MemberAccessNode, IndexAccessNode, PipelineNode, RangeNode,
    NewNode, CastNode, StringInterpNode, ClassDefNode, ClassFieldNode,
    ConstructorDefNode, DestructorDefNode, PropertyDefNode, OperatorDefNode,
    CascadeNode, GuardNode, ExtendDefNode,
    EnumDefNode, MatchNode, MatchCaseNode, SpawnNode
)


def substitute_type_str(t: Optional[str], type_map: Dict[str, str]) -> Optional[str]:
    """Recursively replaces generic parameter names with concrete types in a type signature string."""
    if not t:
        return t
    if t in type_map:
        return type_map[t]
    if t.endswith("?"):
        inner = substitute_type_str(t[:-1], type_map)
        return f"{inner}?" if inner else None
    if t.endswith("*"):
        inner = substitute_type_str(t[:-1], type_map)
        return f"{inner}*" if inner else None

    # Replace whole-word identifier matches (e.g. Pair_K_V with K->str, V->i64 => Pair_str_i64)
    res = t
    for k, v in type_map.items():
        res = re.sub(r'(?<![a-zA-Z0-9_])' + re.escape(k) + r'(?![a-zA-Z0-9_])', v, res)
    return res


class GenericMonomorphizer:
    """
    Scans the Program AST for generic templates (class T<...>, fn f<...>)
    and requested specializations, expanding them into concrete AST representations.
    """

    def __init__(self):
        self.generic_classes: Dict[str, ClassDefNode] = {}
        self.generic_functions: Dict[str, FunctionDefNode] = {}
        self.monomorphized_classes: Dict[str, ClassDefNode] = {}
        self.monomorphized_functions: Dict[str, FunctionDefNode] = {}
        self.queue: Set[Tuple[str, Tuple[str, ...]]] = set()

    def monomorphize(self, ast: ProgramNode) -> ProgramNode:
        """Runs the static monomorphization pass over the Program AST."""
        regular_decls: List[ASTNode] = []

        # 1. Collect all generic class and function templates
        for decl in ast.declarations:
            if isinstance(decl, ClassDefNode) and decl.type_params:
                self.generic_classes[decl.name] = decl
            elif isinstance(decl, FunctionDefNode) and decl.type_params:
                self.generic_functions[decl.name] = decl
            else:
                regular_decls.append(decl)

        # If there are no generic templates, return AST untouched
        if not self.generic_classes and not self.generic_functions:
            return ast

        # 2. Seed queue with uses discovered by parser
        self.queue = set(ast.generic_uses)

        # Also scan regular declarations for any referenced specialized names
        self._scan_declarations_for_uses(regular_decls)

        # 3. Iteratively specialize all queued templates
        processed: Set[Tuple[str, Tuple[str, ...]]] = set()
        while self.queue:
            item = self.queue.pop()
            if item in processed:
                continue
            processed.add(item)
            template_name, type_args = item

            if template_name in self.generic_classes:
                mangled_name = f"{template_name}_{'_'.join(type_args)}"
                if mangled_name not in self.monomorphized_classes:
                    spec_cls = self.specialize_class(self.generic_classes[template_name], type_args)
                    self.monomorphized_classes[mangled_name] = spec_cls
            elif template_name in self.generic_functions:
                mangled_name = f"{template_name}_{'_'.join(type_args)}"
                if mangled_name not in self.monomorphized_functions:
                    spec_fn = self.specialize_function(self.generic_functions[template_name], type_args)
                    self.monomorphized_functions[mangled_name] = spec_fn

        # 4. Assemble new declarations: monomorphized classes, monomorphized functions, regular decls
        new_declarations: List[ASTNode] = (
            list(self.monomorphized_classes.values())
            + list(self.monomorphized_functions.values())
            + regular_decls
        )

        return ProgramNode(
            line=ast.line,
            col=ast.col,
            declarations=new_declarations,
            generic_uses=ast.generic_uses
        )

    def specialize_class(self, template: ClassDefNode, type_args: Tuple[str, ...]) -> ClassDefNode:
        """Clones and specializes a generic class template for concrete type arguments."""
        cls = copy.deepcopy(template)
        mangled_name = f"{template.name}_{'_'.join(type_args)}"
        cls.name = mangled_name
        cls.type_params = []

        type_map = {param: arg for param, arg in zip(template.type_params, type_args)}

        # Specialize fields
        for f in cls.fields:
            f.type_name = substitute_type_str(f.type_name, type_map)

        # Specialize constructors
        for ctor in cls.constructors:
            for p in ctor.params:
                p.type_name = substitute_type_str(p.type_name, type_map)
            self._substitute_in_body(ctor.body, type_map)

        if cls.constructor and cls.constructor not in cls.constructors:
            for p in cls.constructor.params:
                p.type_name = substitute_type_str(p.type_name, type_map)
            self._substitute_in_body(cls.constructor.body, type_map)

        if cls.destructor:
            self._substitute_in_body(cls.destructor.body, type_map)

        # Specialize methods
        for m in cls.methods:
            for p in m.params:
                p.type_name = substitute_type_str(p.type_name, type_map)
            m.return_type = substitute_type_str(m.return_type, type_map)
            self._substitute_in_body(m.body, type_map)

        # Specialize properties
        for prop in cls.properties:
            prop.type_name = substitute_type_str(prop.type_name, type_map)
            if prop.getter_body:
                self._substitute_in_body(prop.getter_body, type_map)
            if prop.setter_body:
                self._substitute_in_body(prop.setter_body, type_map)

        # Specialize operators
        for op in cls.operators:
            op.param_type = substitute_type_str(op.param_type, type_map)
            op.return_type = substitute_type_str(op.return_type, type_map)
            self._substitute_in_body(op.body, type_map)

        return cls

    def specialize_function(self, template: FunctionDefNode, type_args: Tuple[str, ...]) -> FunctionDefNode:
        """Clones and specializes a generic function template for concrete type arguments."""
        fn = copy.deepcopy(template)
        mangled_name = f"{template.name}_{'_'.join(type_args)}"
        fn.name = mangled_name
        fn.type_params = []

        type_map = {param: arg for param, arg in zip(template.type_params, type_args)}

        for p in fn.params:
            p.type_name = substitute_type_str(p.type_name, type_map)
        fn.return_type = substitute_type_str(fn.return_type, type_map)

        self._substitute_in_body(fn.body, type_map)
        return fn

    def _substitute_in_body(self, node: Optional[ASTNode], type_map: Dict[str, str]) -> None:
        """Walks AST expressions and statements, rewriting types and specialized names."""
        if not node:
            return

        if isinstance(node, BlockNode):
            for stmt in node.statements:
                self._substitute_in_body(stmt, type_map)
        elif isinstance(node, VarDeclNode):
            if node.type_annotation:
                node.type_annotation = substitute_type_str(node.type_annotation, type_map)
                self._check_for_generic_use(node.type_annotation)
            if node.initializer:
                self._substitute_in_body(node.initializer, type_map)
        elif isinstance(node, AssignNode):
            self._substitute_in_body(node.target, type_map)
            self._substitute_in_body(node.value, type_map)
        elif isinstance(node, IfNode):
            self._substitute_in_body(node.condition, type_map)
            self._substitute_in_body(node.then_block, type_map)
            if node.else_block:
                self._substitute_in_body(node.else_block, type_map)
        elif isinstance(node, GuardNode):
            self._substitute_in_body(node.condition, type_map)
            self._substitute_in_body(node.else_block, type_map)
        elif isinstance(node, WhileNode):
            self._substitute_in_body(node.condition, type_map)
            self._substitute_in_body(node.body, type_map)
        elif isinstance(node, ForNode):
            self._substitute_in_body(node.range_expr, type_map)
            self._substitute_in_body(node.body, type_map)
        elif isinstance(node, LoopNode):
            self._substitute_in_body(node.body, type_map)
        elif isinstance(node, ReturnNode):
            if node.value:
                self._substitute_in_body(node.value, type_map)
        elif isinstance(node, DeferNode):
            self._substitute_in_body(node.statement, type_map)
        elif isinstance(node, ExprStmtNode):
            self._substitute_in_body(node.expr, type_map)
        elif isinstance(node, MatchNode):
            self._substitute_in_body(node.expr, type_map)
            for case in node.cases:
                self._substitute_in_body(case.pattern, type_map)
                if case.guard_expr:
                    self._substitute_in_body(case.guard_expr, type_map)
                self._substitute_in_body(case.body, type_map)
        elif isinstance(node, BinaryOpNode):
            self._substitute_in_body(node.left, type_map)
            self._substitute_in_body(node.right, type_map)
        elif isinstance(node, UnaryOpNode):
            self._substitute_in_body(node.operand, type_map)
        elif isinstance(node, CallNode):
            if isinstance(node.callee, IdentifierNode):
                node.callee.name = substitute_type_str(node.callee.name, type_map)
                self._check_for_generic_use(node.callee.name)
            else:
                self._substitute_in_body(node.callee, type_map)
            for a in node.args:
                self._substitute_in_body(a, type_map)
        elif isinstance(node, MemberAccessNode):
            self._substitute_in_body(node.object_expr, type_map)
        elif isinstance(node, IndexAccessNode):
            self._substitute_in_body(node.object_expr, type_map)
            self._substitute_in_body(node.index, type_map)
        elif isinstance(node, PipelineNode):
            self._substitute_in_body(node.left, type_map)
            self._substitute_in_body(node.right, type_map)
        elif isinstance(node, CascadeNode):
            self._substitute_in_body(node.target, type_map)
            self._substitute_in_body(node.call, type_map)
        elif isinstance(node, RangeNode):
            self._substitute_in_body(node.start, type_map)
            self._substitute_in_body(node.end, type_map)
        elif isinstance(node, NewNode):
            node.class_name = substitute_type_str(node.class_name, type_map)
            self._check_for_generic_use(node.class_name)
            for a in node.args:
                self._substitute_in_body(a, type_map)
        elif isinstance(node, CastNode):
            node.target_type = substitute_type_str(node.target_type, type_map)
            self._check_for_generic_use(node.target_type)
            self._substitute_in_body(node.expr, type_map)
        elif isinstance(node, StringInterpNode):
            for p in node.parts:
                if isinstance(p, ASTNode):
                    self._substitute_in_body(p, type_map)
        elif isinstance(node, SpawnNode):
            self._substitute_in_body(node.call, type_map)
        elif isinstance(node, IdentifierNode):
            node.name = substitute_type_str(node.name, type_map)
            self._check_for_generic_use(node.name)

    def _check_for_generic_use(self, name: Optional[str]) -> None:
        """Checks if a mangled name corresponds to an unmonomorphized generic template."""
        if not name:
            return
        # Clean off optional or pointer
        clean_name = name.rstrip("?*")
        for template_name in self.generic_classes:
            prefix = f"{template_name}_"
            if clean_name.startswith(prefix):
                suffix = clean_name[len(prefix):]
                # If template has 1 parameter:
                type_params = self.generic_classes[template_name].type_params
                if len(type_params) == 1:
                    self.queue.add((template_name, (suffix,)))
        for template_name in self.generic_functions:
            prefix = f"{template_name}_"
            if clean_name.startswith(prefix):
                suffix = clean_name[len(prefix):]
                type_params = self.generic_functions[template_name].type_params
                if len(type_params) == 1:
                    self.queue.add((template_name, (suffix,)))

    def _scan_declarations_for_uses(self, declarations: List[ASTNode]) -> None:
        """Discovers any generic uses in non-generic top-level declarations."""
        empty_map: Dict[str, str] = {}
        for decl in declarations:
            if isinstance(decl, FunctionDefNode):
                for p in decl.params:
                    self._check_for_generic_use(p.type_name)
                self._check_for_generic_use(decl.return_type)
                self._substitute_in_body(decl.body, empty_map)
            elif isinstance(decl, ClassDefNode):
                for f in decl.fields:
                    self._check_for_generic_use(f.type_name)
                for ctor in decl.constructors:
                    for p in ctor.params:
                        self._check_for_generic_use(p.type_name)
                    self._substitute_in_body(ctor.body, empty_map)
                for m in decl.methods:
                    for p in m.params:
                        self._check_for_generic_use(p.type_name)
                    self._check_for_generic_use(m.return_type)
                    self._substitute_in_body(m.body, empty_map)
            elif isinstance(decl, (VarDeclNode, AssignNode, ExprStmtNode)):
                self._substitute_in_body(decl, empty_map)
