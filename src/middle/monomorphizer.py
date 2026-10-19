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
    EnumDefNode, MatchNode, MatchCaseNode, SpawnNode,
    TupleNode, TupleDestructureNode
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
        res = re.sub(r'(?<![a-zA-Z0-9])' + re.escape(k) + r'(?![a-zA-Z0-9])', v, res)
    return res


class GenericMonomorphizer:
    """
    Scans the Program AST for generic templates (class T<...>, fn f<...>)
    and requested specializations, expanding them into concrete AST representations.
    """

    def __init__(self):
        self.generic_classes: Dict[str, ClassDefNode] = {}
        self.generic_functions: Dict[str, FunctionDefNode] = {}
        self.prelude_generic_templates: Dict[str, ClassDefNode] = {}
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

        # Check prelude needs (Phase 21 & 22: Collections & Strings)
        from src.middle.prelude import get_prelude_ast
        prelude_ast = get_prelude_ast()
        for decl in prelude_ast.declarations:
            if isinstance(decl, ClassDefNode) and decl.type_params:
                self.prelude_generic_templates[decl.name] = decl

        has_split = self._has_split_call(ast)
        if has_split:
            ast.generic_uses.add(("List", ("str",)))

        # Load generic templates from prelude
        BUILTIN_TEMPLATES = {"List", "Map", "Set", "Stack", "Queue", "Deque"}
        for tpl in BUILTIN_TEMPLATES:
            has_tpl_use = any(tpl_name == tpl for tpl_name, _ in ast.generic_uses) or self._references_template(ast, tpl)
            if has_tpl_use and tpl not in self.generic_classes:
                for decl in prelude_ast.declarations:
                    if isinstance(decl, ClassDefNode) and decl.name == tpl:
                        self.generic_classes[tpl] = decl
                        break

        # Load concrete classes from prelude
        for cls_name in ("String", "ByteBuffer"):
            if self._references_class(ast, cls_name) and not any(isinstance(d, ClassDefNode) and d.name == cls_name for d in ast.declarations):
                for decl in prelude_ast.declarations:
                    if isinstance(decl, ClassDefNode) and decl.name == cls_name:
                        regular_decls.insert(0, copy.deepcopy(decl))
                        if cls_name == "String":
                            ast.generic_uses.add(("List", ("str",)))
                            if "List" not in self.generic_classes:
                                for p_decl in prelude_ast.declarations:
                                    if isinstance(p_decl, ClassDefNode) and p_decl.name == "List":
                                        self.generic_classes["List"] = p_decl
                                        break
                        break

        # If there are no generic templates and no tuple uses, return AST
        has_tuple_uses = any(tpl == "Tuple" for tpl, _ in ast.generic_uses)
        if not self.generic_classes and not self.generic_functions and not has_tuple_uses and not ast.generic_uses:
            if len(regular_decls) == len(ast.declarations):
                return ast
            return ProgramNode(
                line=ast.line,
                col=ast.col,
                declarations=regular_decls,
                generic_uses=ast.generic_uses
            )

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

            if template_name == "Tuple":
                mangled_name = f"Tuple_{'_'.join(type_args)}"
                if mangled_name not in self.monomorphized_classes:
                    fields = [
                        ClassFieldNode(line=ast.line, col=ast.col, name=f"f{i}", type_name=arg, is_pub=True)
                        for i, arg in enumerate(type_args)
                    ]
                    spec_cls = ClassDefNode(
                        line=ast.line, col=ast.col,
                        name=mangled_name,
                        fields=fields,
                        methods=[],
                        constructor=None,
                        destructor=None
                    )
                    self.monomorphized_classes[mangled_name] = spec_cls
            elif template_name in self.generic_classes or template_name in self.prelude_generic_templates:
                if template_name not in self.generic_classes:
                    self.generic_classes[template_name] = self.prelude_generic_templates[template_name]
                mangled_name = f"{template_name}_{'_'.join(type_args)}"
                if mangled_name not in self.monomorphized_classes:
                    spec_cls = self.specialize_class(self.generic_classes[template_name], type_args)
                    self.monomorphized_classes[mangled_name] = spec_cls
                    self._scan_declarations_for_uses([spec_cls])
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

    def _references_class(self, ast: ASTNode, class_name: str) -> bool:
        found = False
        def walk(n):
            nonlocal found
            if found or n is None:
                return
            if isinstance(n, IdentifierNode) and n.name == class_name:
                found = True
                return
            if isinstance(n, VarDeclNode) and getattr(n, "type_annotation", None) == class_name:
                found = True
                return
            if isinstance(n, ParamNode) and getattr(n, "type_name", None) == class_name:
                found = True
                return
            if isinstance(n, FunctionDefNode) and getattr(n, "return_type", None) == class_name:
                found = True
                return
            for attr in ("statements", "declarations", "body", "args", "params", "expr", "left", "right", "value", "target", "object_expr", "index", "condition", "then_block", "else_block", "initializer", "callee", "call", "elements"):
                v = getattr(n, attr, None)
                if isinstance(v, list):
                    for item in v:
                        walk(item)
                elif isinstance(v, ASTNode):
                    walk(v)
        walk(ast)
        return found

    def _references_template(self, ast: ASTNode, tpl_name: str) -> bool:
        found = False
        def walk(n):
            nonlocal found
            if found or n is None:
                return
            if isinstance(n, IdentifierNode) and n.name.startswith(f"{tpl_name}_"):
                found = True
                return
            if isinstance(n, VarDeclNode) and getattr(n, "type_annotation", None) and getattr(n, "type_annotation", "").startswith(f"{tpl_name}_"):
                found = True
                return
            if isinstance(n, ParamNode) and getattr(n, "type_name", None) and getattr(n, "type_name", "").startswith(f"{tpl_name}_"):
                found = True
                return
            if isinstance(n, FunctionDefNode) and getattr(n, "return_type", None) and getattr(n, "return_type", "").startswith(f"{tpl_name}_"):
                found = True
                return
            for attr in ("statements", "declarations", "body", "args", "params", "expr", "left", "right", "value", "target", "object_expr", "index", "condition", "then_block", "else_block", "initializer", "callee", "call", "elements"):
                v = getattr(n, attr, None)
                if isinstance(v, list):
                    for item in v:
                        walk(item)
                elif isinstance(v, ASTNode):
                    walk(v)
        walk(ast)
        return found

    def _has_split_call(self, ast: ASTNode) -> bool:
        found = False
        def walk(n):
            nonlocal found
            if found or n is None:
                return
            if isinstance(n, CallNode) and isinstance(n.callee, MemberAccessNode) and n.callee.member == "split":
                found = True
                return
            for attr in ("statements", "declarations", "body", "args", "params", "expr", "left", "right", "value", "target", "object_expr", "index", "condition", "then_block", "else_block", "initializer", "callee", "call"):
                v = getattr(n, attr, None)
                if isinstance(v, list):
                    for item in v:
                        walk(item)
                elif isinstance(v, ASTNode):
                    walk(v)
        walk(ast)
        return found

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

        # Specialized List helpers for primitive types (str, i64, f64)
        if template.name == "List" and len(type_args) == 1:
            elem_t = type_args[0]
            if elem_t in ("str", "i64", "f64"):
                for m in cls.methods:
                    if m.name == "push":
                        for stmt in m.body.statements:
                            if isinstance(stmt, ExprStmtNode) and isinstance(stmt.expr, CallNode) and isinstance(stmt.expr.callee, IdentifierNode):
                                if stmt.expr.callee.name == "arx_list_push":
                                    stmt.expr.callee.name = f"arx_list_push_{elem_t}"
                                    stmt.expr.args = [stmt.expr.args[0], IdentifierNode(line=stmt.line, col=stmt.col, name="val")]
                    elif m.name in ("pop", "swap_remove", "remove_at"):
                        for stmt in m.body.statements:
                            if isinstance(stmt, VarDeclNode) and isinstance(stmt.initializer, CallNode) and isinstance(stmt.initializer.callee, IdentifierNode):
                                if stmt.initializer.callee.name in ("arx_list_pop", "arx_list_swap_remove", "arx_list_remove_at"):
                                    stmt.initializer.callee.name = f"{stmt.initializer.callee.name}_{elem_t}"
                            elif isinstance(stmt, ReturnNode) and isinstance(stmt.value, CastNode):
                                stmt.value = stmt.value.expr
                    elif m.name == "get":
                        for stmt in m.body.statements:
                            if isinstance(stmt, VarDeclNode) and isinstance(stmt.initializer, CallNode) and isinstance(stmt.initializer.callee, IdentifierNode):
                                if stmt.initializer.callee.name == "arx_list_get":
                                    stmt.initializer.callee.name = f"arx_list_get_{elem_t}"
                            elif isinstance(stmt, ReturnNode) and isinstance(stmt.value, CastNode):
                                stmt.value = stmt.value.expr
                    elif m.name == "set":
                        for stmt in m.body.statements:
                            if isinstance(stmt, ExprStmtNode) and isinstance(stmt.expr, CallNode) and isinstance(stmt.expr.callee, IdentifierNode):
                                if stmt.expr.callee.name == "arx_list_set":
                                    stmt.expr.callee.name = f"arx_list_set_{elem_t}"
                                    stmt.expr.args = [stmt.expr.args[0], stmt.expr.args[1], IdentifierNode(line=stmt.line, col=stmt.col, name="val")]
                    elif m.name == "insert":
                        for stmt in m.body.statements:
                            if isinstance(stmt, ExprStmtNode) and isinstance(stmt.expr, CallNode) and isinstance(stmt.expr.callee, IdentifierNode):
                                if stmt.expr.callee.name == "arx_list_insert":
                                    stmt.expr.callee.name = f"arx_list_insert_{elem_t}"
                                    stmt.expr.args = [stmt.expr.args[0], stmt.expr.args[1], IdentifierNode(line=stmt.line, col=stmt.col, name="val")]
                    elif m.name == "contains" and elem_t == "str":
                        for stmt in m.body.statements:
                            if isinstance(stmt, ReturnNode) and isinstance(stmt.value, CallNode) and isinstance(stmt.value.callee, IdentifierNode):
                                if stmt.value.callee.name == "arx_list_contains":
                                    stmt.value.callee.name = "arx_list_contains_str"
                                    stmt.value.args = [stmt.value.args[0], IdentifierNode(line=stmt.line, col=stmt.col, name="val")]
                    elif m.name == "index_of" and elem_t == "str":
                        for stmt in m.body.statements:
                            if isinstance(stmt, ReturnNode) and isinstance(stmt.value, CallNode) and isinstance(stmt.value.callee, IdentifierNode):
                                if stmt.value.callee.name == "arx_list_index_of":
                                    stmt.value.callee.name = "arx_list_index_of_str"
                                    stmt.value.args = [stmt.value.args[0], IdentifierNode(line=stmt.line, col=stmt.col, name="val")]

        # Specialized Map helpers
        if template.name == "Map" and len(type_args) == 2:
            key_t, val_t = type_args[0], type_args[1]
            if key_t == "str":
                for ctor in cls.constructors:
                    for stmt in ctor.body.statements:
                        if isinstance(stmt, AssignNode) and isinstance(stmt.value, CallNode) and isinstance(stmt.value.callee, IdentifierNode):
                            if stmt.value.callee.name == "arx_map_new":
                                stmt.value.args = [LiteralNode(line=stmt.line, col=stmt.col, value=1, type_name="i64")]
                if cls.constructor:
                    for stmt in cls.constructor.body.statements:
                        if isinstance(stmt, AssignNode) and isinstance(stmt.value, CallNode) and isinstance(stmt.value.callee, IdentifierNode):
                            if stmt.value.callee.name == "arx_map_new":
                                stmt.value.args = [LiteralNode(line=stmt.line, col=stmt.col, value=1, type_name="i64")]
            for m in cls.methods:
                if m.name in ("insert", "set"):
                    for stmt in m.body.statements:
                        if isinstance(stmt, ExprStmtNode) and isinstance(stmt.expr, CallNode) and isinstance(stmt.expr.callee, IdentifierNode):
                            if stmt.expr.callee.name == "arx_map_insert":
                                if key_t == "str" and val_t == "str":
                                    stmt.expr.callee.name = "arx_map_insert_str_str"
                                    stmt.expr.args = [stmt.expr.args[0], IdentifierNode(line=stmt.line, col=stmt.col, name="key"), IdentifierNode(line=stmt.line, col=stmt.col, name="val")]
                                elif key_t == "str":
                                    stmt.expr.callee.name = "arx_map_insert_str_i64"
                                    stmt.expr.args = [stmt.expr.args[0], IdentifierNode(line=stmt.line, col=stmt.col, name="key"), stmt.expr.args[2]]
                                elif val_t == "str":
                                    stmt.expr.callee.name = "arx_map_insert_i64_str"
                                    stmt.expr.args = [stmt.expr.args[0], stmt.expr.args[1], IdentifierNode(line=stmt.line, col=stmt.col, name="val")]
                elif m.name == "get":
                    for stmt in m.body.statements:
                        if isinstance(stmt, VarDeclNode) and isinstance(stmt.initializer, CallNode) and isinstance(stmt.initializer.callee, IdentifierNode):
                            if stmt.initializer.callee.name == "arx_map_get":
                                if key_t == "str" and val_t == "str":
                                    stmt.initializer.callee.name = "arx_map_get_str_str"
                                    stmt.initializer.args = [stmt.initializer.args[0], IdentifierNode(line=stmt.line, col=stmt.col, name="key")]
                                elif key_t == "str":
                                    stmt.initializer.callee.name = "arx_map_get_str_i64"
                                    stmt.initializer.args = [stmt.initializer.args[0], IdentifierNode(line=stmt.line, col=stmt.col, name="key")]
                                elif val_t == "str":
                                    stmt.initializer.callee.name = "arx_map_get_i64_str"
                        elif isinstance(stmt, ReturnNode) and isinstance(stmt.value, CastNode):
                            if val_t == "str":
                                stmt.value = stmt.value.expr
                elif m.name == "has_key":
                    for stmt in m.body.statements:
                        if isinstance(stmt, ReturnNode) and isinstance(stmt.value, CallNode) and isinstance(stmt.value.callee, IdentifierNode):
                            if stmt.value.callee.name == "arx_map_has":
                                if key_t == "str":
                                    stmt.value.callee.name = "arx_map_has_str"
                                    stmt.value.args = [stmt.value.args[0], IdentifierNode(line=stmt.line, col=stmt.col, name="key")]
                elif m.name == "remove":
                    for stmt in m.body.statements:
                        if isinstance(stmt, ExprStmtNode) and isinstance(stmt.expr, CallNode) and isinstance(stmt.expr.callee, IdentifierNode):
                            if stmt.expr.callee.name == "arx_map_remove":
                                if key_t == "str":
                                    stmt.expr.callee.name = "arx_map_remove_str"
                                    stmt.expr.args = [stmt.expr.args[0], IdentifierNode(line=stmt.line, col=stmt.col, name="key")]

        # Specialized Set helpers
        if template.name == "Set" and len(type_args) == 1:
            elem_t = type_args[0]
            if elem_t == "str":
                for ctor in cls.constructors:
                    for stmt in ctor.body.statements:
                        if isinstance(stmt, AssignNode) and isinstance(stmt.value, CallNode) and isinstance(stmt.value.callee, IdentifierNode):
                            if stmt.value.callee.name == "arx_set_new":
                                stmt.value.args = [LiteralNode(line=stmt.line, col=stmt.col, value=1, type_name="i64")]
                if cls.constructor:
                    for stmt in cls.constructor.body.statements:
                        if isinstance(stmt, AssignNode) and isinstance(stmt.value, CallNode) and isinstance(stmt.value.callee, IdentifierNode):
                            if stmt.value.callee.name == "arx_set_new":
                                stmt.value.args = [LiteralNode(line=stmt.line, col=stmt.col, value=1, type_name="i64")]
                for m in cls.methods:
                    if m.name == "add":
                        for stmt in m.body.statements:
                            if isinstance(stmt, VarDeclNode) and isinstance(stmt.initializer, CallNode) and isinstance(stmt.initializer.callee, IdentifierNode):
                                if stmt.initializer.callee.name == "arx_set_add":
                                    stmt.initializer.callee.name = "arx_set_add_str"
                                    stmt.initializer.args = [stmt.initializer.args[0], IdentifierNode(line=stmt.line, col=stmt.col, name="item")]
                    elif m.name == "has":
                        for stmt in m.body.statements:
                            if isinstance(stmt, ReturnNode) and isinstance(stmt.value, CallNode) and isinstance(stmt.value.callee, IdentifierNode):
                                if stmt.value.callee.name == "arx_set_has":
                                    stmt.value.callee.name = "arx_set_has_str"
                                    stmt.value.args = [stmt.value.args[0], IdentifierNode(line=stmt.line, col=stmt.col, name="item")]
                    elif m.name == "remove":
                        for stmt in m.body.statements:
                            if isinstance(stmt, VarDeclNode) and isinstance(stmt.initializer, CallNode) and isinstance(stmt.initializer.callee, IdentifierNode):
                                if stmt.initializer.callee.name == "arx_set_remove":
                                    stmt.initializer.callee.name = "arx_set_remove_str"
                                    stmt.initializer.args = [stmt.initializer.args[0], IdentifierNode(line=stmt.line, col=stmt.col, name="item")]
                    elif m.name == "get":
                        for stmt in m.body.statements:
                            if isinstance(stmt, VarDeclNode) and isinstance(stmt.initializer, CallNode) and isinstance(stmt.initializer.callee, IdentifierNode):
                                if stmt.initializer.callee.name == "arx_set_get":
                                    stmt.initializer.callee.name = "arx_set_get_str"
                            elif isinstance(stmt, ReturnNode) and isinstance(stmt.value, CastNode):
                                stmt.value = stmt.value.expr

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
        elif isinstance(node, TupleNode):
            for e in node.elements:
                self._substitute_in_body(e, type_map)
        elif isinstance(node, TupleDestructureNode):
            if node.initializer:
                self._substitute_in_body(node.initializer, type_map)
        elif isinstance(node, IdentifierNode):
            node.name = substitute_type_str(node.name, type_map)
            self._check_for_generic_use(node.name)

    def _check_for_generic_use(self, name: Optional[str]) -> None:
        """Checks if a mangled name corresponds to an unmonomorphized generic template."""
        if not name:
            return
        # Clean off optional or pointer
        clean_name = name.rstrip("?*")
        if clean_name.startswith("Tuple_"):
            parts = tuple(clean_name[6:].split('_'))
            if parts and all(p for p in parts):
                self.queue.add(("Tuple", parts))
        all_templates = dict(self.prelude_generic_templates)
        all_templates.update(self.generic_classes)
        for template_name in all_templates:
            prefix = f"{template_name}_"
            if clean_name.startswith(prefix):
                suffix = clean_name[len(prefix):]
                type_params = all_templates[template_name].type_params
                parts = tuple(suffix.split('_'))
                if len(parts) == len(type_params):
                    if not any(p in parts for p in type_params):
                        if template_name not in self.generic_classes:
                            self.generic_classes[template_name] = all_templates[template_name]
                        self.queue.add((template_name, parts))
        for template_name in self.generic_functions:
            prefix = f"{template_name}_"
            if clean_name.startswith(prefix):
                suffix = clean_name[len(prefix):]
                type_params = self.generic_functions[template_name].type_params
                parts = tuple(suffix.split('_'))
                if len(parts) == len(type_params):
                    if not any(p in parts for p in type_params):
                        self.queue.add((template_name, parts))

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
