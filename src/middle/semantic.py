"""
Aerix Compiler (arxc) — Semantic Analyzer & Type Checker
Enforces static typing, immutability (let vs mut), scope resolution,
OOP access control (pub/priv), and Class Hierarchy Analysis (CHA).
"""

from typing import Dict, List, Optional, Any
from src.frontend.ast_nodes import (
    ASTNode, ProgramNode, FunctionDefNode, ParamNode, BlockNode,
    VarDeclNode, AssignNode, IfNode, WhileNode, ForNode, LoopNode,
    ReturnNode, DeferNode, ExprStmtNode, LiteralNode, IdentifierNode,
    BinaryOpNode, UnaryOpNode, CallNode, MemberAccessNode, IndexAccessNode,
    PipelineNode, RangeNode, NewNode, CastNode, StringInterpNode,
    ClassDefNode, ClassFieldNode, ConstructorDefNode, DestructorDefNode,
    TraitDefNode, CIncludeNode, CExternNode, BreakNode, ContinueNode,
    PropertyDefNode, OperatorDefNode, GuardNode, CascadeNode, ExtendDefNode,
    EnumDefNode, EnumVariantNode, MatchNode, MatchCaseNode, SpawnNode,
    TupleNode, TupleDestructureNode
)
from src.middle.typesystem import (
    Type, ClassType, FunctionType, OptionalType, EnumType, EnumVariant, TraitType,
    TYPE_I64, TYPE_F64, TYPE_BOOL, TYPE_STR, TYPE_CHAR,
    TYPE_VOID, TYPE_NULL, lookup_type, PRIMITIVES
)
from src.frontend.diagnostics import AerixDiagnostic, DiagnosticBag, format_source_snippet



OPERATOR_METHOD_NAMES = {
    "+": "op_add",
    "-": "op_sub",
    "*": "op_mul",
    "/": "op_div",
    "%": "op_mod",
    "==": "op_eq",
    "!=": "op_ne",
    "<": "op_lt",
    "<=": "op_le",
    ">": "op_gt",
    ">=": "op_ge",
    "[]": "op_index",
}


class SemanticError(AerixDiagnostic):
    def __init__(self, message: str, node: ASTNode, file: str = "<stdin>", source_line: str = "", hint: Optional[str] = None):
        self.message = message
        self.line = node.line
        self.col = node.col
        self.source_line = source_line
        self.hint = hint
        super().__init__(
            format_source_snippet(
                file=file,
                line=node.line,
                col=node.col,
                source_line=source_line,
                message=message,
                error_type="SEMANTIC ERROR",
                hint=hint
            )
        )


class Symbol:
    def __init__(self, name: str, type_obj: Type, is_mut: bool, node: ASTNode):
        self.name = name
        self.type = type_obj
        self.is_mut = is_mut
        self.node = node
        self.is_used = False


class Scope:
    def __init__(self, parent: Optional["Scope"] = None, kind: str = "block"):
        self.parent = parent
        self.kind = kind
        self.symbols: Dict[str, Symbol] = {}

    def define(self, symbol: Symbol) -> bool:
        if symbol.name in self.symbols:
            return False # Duplicate in same scope
        self.symbols[symbol.name] = symbol
        return True

    def lookup(self, name: str) -> Optional[Symbol]:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None


class SemanticAnalyzer:
    def __init__(self, filename: str = "<stdin>", source_lines: Optional[List[str]] = None):
        self.filename = filename
        self.source_lines = source_lines or []
        self.classes: Dict[str, ClassType] = {}
        self.enums: Dict[str, EnumType] = {}
        self.traits: Dict[str, TraitType] = {}
        self.functions: Dict[str, FunctionType] = {}
        self.global_scope = Scope(kind="global")
        self.current_scope = self.global_scope
        self.current_function: Optional[FunctionDefNode] = None
        self.current_class: Optional[ClassType] = None
        self.node_types: Dict[id, Type] = {}
        self.defined_symbols: List[Symbol] = []
        self.errors: List[SemanticError] = []

    def error(self, msg: str, node: ASTNode, hint: Optional[str] = None) -> None:
        line_str = self.source_lines[node.line - 1] if 0 < node.line <= len(self.source_lines) else ""
        raise SemanticError(msg, node, self.filename, line_str, hint=hint)

    def resolve_type(self, type_name: str) -> Type:
        return lookup_type(type_name, self.classes, self.enums, self.traits)

    def analyze(self, program: ProgramNode) -> None:
        """Executes 2-pass semantic analysis over the Program AST."""
        # --- Pass 1: Collect traits, enum, class declarations and function signatures ---
        for decl in program.declarations:
            if isinstance(decl, TraitDefNode):
                self.register_trait(decl)
            elif isinstance(decl, EnumDefNode):
                self.register_enum(decl)
            elif isinstance(decl, ClassDefNode):
                self.register_class(decl)
            elif isinstance(decl, FunctionDefNode):
                self.register_function(decl)
            elif isinstance(decl, CExternNode):
                self.register_function(decl.func_def)

        # Register extensions after classes are in place
        for decl in program.declarations:
            if isinstance(decl, ExtendDefNode):
                self.register_extension(decl)

        # Validate Trait Conformance
        for decl in program.declarations:
            if isinstance(decl, ClassDefNode):
                self.validate_trait_conformance(decl)

        # --- Pass 2: Type checking, immutability enforcement, and scope analysis ---
        for decl in program.declarations:
            try:
                self.analyze_node(decl)
            except SemanticError as se:
                self.errors.append(se)
                if len(self.errors) >= 20:
                    break

        if self.errors:
            if len(self.errors) == 1:
                raise self.errors[0]
            raise DiagnosticBag(self.errors, self.filename)

    def register_trait(self, node: TraitDefNode) -> None:
        if node.name in self.traits or node.name in self.classes or node.name in self.enums:
            self.error(f"Duplicate type definition: '{node.name}'", node)
        trait_type = TraitType(node.name)
        self.traits[node.name] = trait_type

        for m in node.methods:
            param_types = [self.resolve_type(p.type_name) for p in m.params]
            ret_type = self.resolve_type(m.return_type)
            trait_type.methods[m.name] = FunctionType(param_types, ret_type)

    def validate_trait_conformance(self, node: ClassDefNode) -> None:
        cls_type = self.classes[node.name]
        for t_name in node.traits:
            if t_name not in self.traits:
                self.error(f"Class '{node.name}' implements undefined trait '{t_name}'", node)
            trait_type = self.traits[t_name]
            for m_name, trait_fn in trait_type.methods.items():
                res = cls_type.resolve_method(m_name, trait_fn.param_types)
                if not res:
                    params_str = ", ".join(p.name for p in trait_fn.param_types)
                    self.error(
                        f"Class '{node.name}' does not implement method '{m_name}({params_str}) -> {trait_fn.return_type.name}' required by trait '{t_name}'",
                        node
                    )
                else:
                    fn_type, is_pub, _, _ = res
                    if fn_type.return_type.name != trait_fn.return_type.name:
                        self.error(
                            f"Method '{m_name}' in class '{node.name}' returns '{fn_type.return_type.name}', but trait '{t_name}' requires '{trait_fn.return_type.name}'",
                            node
                        )



    def register_enum(self, node: EnumDefNode) -> None:
        if node.name in self.enums or node.name in self.classes:
            self.error(f"Duplicate type definition: '{node.name}'", node)
        enum_type = EnumType(node.name)
        self.enums[node.name] = enum_type

        for v in node.variants:
            fields = []
            for f in v.fields:
                f_type = lookup_type(f.type_name, self.classes, self.enums)
                fields.append((f.name, f_type))
            variant = EnumVariant(v.name, v.tag, fields)
            enum_type.variants[v.name] = variant

    def register_class(self, node: ClassDefNode) -> None:
        if node.name in self.classes or node.name in self.enums:
            self.error(f"Duplicate class definition: '{node.name}'", node)
        base = self.classes.get(node.base_class) if node.base_class else None
        cls_type = ClassType(name=node.name, base_class=base)
        cls_type.traits = list(node.traits)
        self.classes[node.name] = cls_type

        # Register fields
        for field in node.fields:
            field_type = lookup_type(field.type_name, self.classes, self.enums)

            cls_type.fields[field.name] = field_type
            cls_type.field_access[field.name] = field.is_pub

        # Register methods with overloading support
        method_counts = {}
        for m in node.methods:
            method_counts[m.name] = method_counts.get(m.name, 0) + 1

        for method in node.methods:
            param_types = [self.resolve_type(p.type_name) for p in method.params]
            ret_type = self.resolve_type(method.return_type)
            fn_type = FunctionType(param_types, ret_type)
            if method_counts[method.name] > 1:
                p_suffix = "_".join(p.name.replace("?", "_opt").replace("*", "_ptr") for p in param_types)
                mangled = f"Arx_{node.name}_{method.name}__{p_suffix}" if p_suffix else f"Arx_{node.name}_{method.name}__void"
            else:
                mangled = f"Arx_{node.name}_{method.name}"
            method.mangled_name = mangled

            if method.name not in cls_type.method_overloads:
                cls_type.method_overloads[method.name] = []
            cls_type.method_overloads[method.name].append((fn_type, method.is_pub, mangled, method))

            if method.name not in cls_type.methods:
                cls_type.methods[method.name] = fn_type
                cls_type.method_access[method.name] = method.is_pub

        # Register constructors with overloading & named variant support
        all_ctors = node.constructors if getattr(node, "constructors", None) else ([node.constructor] if node.constructor else [])
        ctor_counts = len(all_ctors)
        for ctor in all_ctors:
            param_types = [self.resolve_type(p.type_name) for p in ctor.params]
            fn_type = FunctionType(param_types, cls_type)
            if ctor.variant:
                p_suffix = "_".join(p.name.replace("?", "_opt").replace("*", "_ptr") for p in param_types)
                mangled = f"Arx_{node.name}_init_{ctor.variant}__{p_suffix}" if p_suffix else f"Arx_{node.name}_init_{ctor.variant}"
            elif ctor_counts > 1:
                p_suffix = "_".join(p.name.replace("?", "_opt").replace("*", "_ptr") for p in param_types)
                mangled = f"Arx_{node.name}_init__{p_suffix}" if p_suffix else f"Arx_{node.name}_init__void"
            else:
                mangled = f"Arx_{node.name}_init"
            ctor.mangled_name = mangled
            cls_type.constructors.append((fn_type, ctor.variant, mangled, ctor))
            if cls_type.constructor_type is None and ctor.variant is None:
                cls_type.constructor_type = fn_type

        # Register properties (Phase 11)
        for prop in getattr(node, "properties", []):
            prop_type = self.resolve_type(prop.type_name)
            has_get = prop.getter_body is not None
            has_set = prop.setter_body is not None
            cls_type.properties[prop.name] = (prop_type, has_get, has_set, prop.is_pub)
            if has_get:
                g_name = f"get_{prop.name}"
                g_fn = FunctionType([], prop_type)
                g_mangled = f"Arx_{node.name}_{g_name}"
                cls_type.methods[g_name] = g_fn
                cls_type.method_access[g_name] = prop.is_pub
                cls_type.method_overloads[g_name] = [(g_fn, prop.is_pub, g_mangled, None)]
            if has_set:
                s_name = f"set_{prop.name}"
                s_fn = FunctionType([prop_type], TYPE_VOID)
                s_mangled = f"Arx_{node.name}_{s_name}"
                cls_type.methods[s_name] = s_fn
                cls_type.method_access[s_name] = prop.is_pub
                cls_type.method_overloads[s_name] = [(s_fn, prop.is_pub, s_mangled, None)]

        # Register operators (Phase 11)
        for op in getattr(node, "operators", []):
            ret_t = self.resolve_type(op.return_type)
            param_t = self.resolve_type(op.params[0].type_name) if op.params else TYPE_VOID
            op_fn_name = OPERATOR_METHOD_NAMES.get(op.op, f"op_{op.op}")
            mangled = f"Arx_{node.name}_{op_fn_name}"
            op.mangled_name = mangled
            cls_type.operators[op.op] = (param_t, ret_t, mangled, op)
            fn_t = FunctionType([param_t], ret_t)
            cls_type.methods[op_fn_name] = fn_t
            cls_type.method_access[op_fn_name] = op.is_pub
            cls_type.method_overloads[op_fn_name] = [(fn_t, op.is_pub, mangled, None)]

    def register_function(self, node: FunctionDefNode) -> None:
        if node.name in self.functions:
            self.error(f"Duplicate function definition: '{node.name}'", node)
        param_types = [self.resolve_type(p.type_name) for p in node.params]
        ret_type = self.resolve_type(node.return_type)
        fn_type = FunctionType(param_types, ret_type)
        self.functions[node.name] = fn_type
        # Add to global scope
        self.global_scope.define(Symbol(node.name, fn_type, False, node))

    def register_extension(self, node: ExtendDefNode) -> None:
        if node.target_type not in self.classes:
            self.error(f"Cannot extend unknown type or class '{node.target_type}'", node)
        cls_type = self.classes[node.target_type]
        for m in node.methods:
            param_types = [self.resolve_type(p.type_name) for p in m.params]
            ret_type = self.resolve_type(m.return_type)
            fn_type = FunctionType(param_types, ret_type)
            mangled = f"Arx_{node.target_type}_{m.name}"
            m.mangled_name = mangled

            if m.name not in cls_type.method_overloads:
                cls_type.method_overloads[m.name] = []
            cls_type.method_overloads[m.name].append((fn_type, m.is_pub, mangled, m))

            if m.name not in cls_type.methods:
                cls_type.methods[m.name] = fn_type
                cls_type.method_access[m.name] = m.is_pub


    # ==========================================
    # AST Node Visitors
    # ==========================================

    def analyze_node(self, node: ASTNode) -> Type:
        if isinstance(node, VarDeclNode):
            return self.visit_var_decl(node)
        elif isinstance(node, AssignNode):
            return self.visit_assign(node)
        elif isinstance(node, FunctionDefNode):
            return self.visit_function_def(node)
        elif isinstance(node, ClassDefNode):
            return self.visit_class_def(node)
        elif isinstance(node, BlockNode):
            return self.visit_block(node)
        elif isinstance(node, IfNode):
            return self.visit_if(node)
        elif isinstance(node, GuardNode):
            return self.visit_guard(node)
        elif isinstance(node, MatchNode):
            return self.visit_match(node)
        elif isinstance(node, WhileNode):
            return self.visit_while(node)
        elif isinstance(node, ForNode):
            return self.visit_for(node)
        elif isinstance(node, LoopNode):
            return self.visit_loop(node)
        elif isinstance(node, ReturnNode):
            return self.visit_return(node)
        elif isinstance(node, DeferNode):
            return self.visit_defer(node)
        elif isinstance(node, ExprStmtNode):
            return self.analyze_node(node.expr)
        elif isinstance(node, BinaryOpNode):
            return self.visit_binary_op(node)
        elif isinstance(node, UnaryOpNode):
            return self.visit_unary_op(node)
        elif isinstance(node, LiteralNode):
            return self.visit_literal(node)
        elif isinstance(node, IdentifierNode):
            return self.visit_identifier(node)
        elif isinstance(node, CallNode):
            return self.visit_call(node)
        elif isinstance(node, PipelineNode):
            return self.visit_pipeline(node)
        elif isinstance(node, CascadeNode):
            return self.visit_cascade(node)
        elif isinstance(node, ExtendDefNode):
            return self.visit_extend_def(node)
        elif isinstance(node, EnumDefNode):
            return TYPE_VOID
        elif isinstance(node, MemberAccessNode):
            return self.visit_member_access(node)
        elif isinstance(node, IndexAccessNode):
            return self.visit_index_access(node)
        elif isinstance(node, RangeNode):
            return self.visit_range(node)
        elif isinstance(node, NewNode):
            return self.visit_new(node)
        elif isinstance(node, CastNode):
            return self.visit_cast(node)
        elif isinstance(node, StringInterpNode):
            return self.visit_string_interp(node)
        elif isinstance(node, SpawnNode):
            return self.visit_spawn(node)
        elif isinstance(node, TupleNode):
            return self.visit_tuple(node)
        elif isinstance(node, TupleDestructureNode):
            return self.visit_tuple_destructure(node)
        elif isinstance(node, (CIncludeNode, CExternNode, TraitDefNode, BreakNode, ContinueNode)):
            return TYPE_VOID
        return TYPE_VOID

    def visit_var_decl(self, node: VarDeclNode) -> Type:
        # Check for dynamic target-typed input/readln:
        if (
            isinstance(node.initializer, CallNode)
            and isinstance(node.initializer.callee, IdentifierNode)
            and node.initializer.callee.name in ("input", "readln")
        ):
            if node.type_annotation:
                node.initializer.target_type = node.type_annotation
                init_type = self.resolve_type(node.type_annotation)
                var_type = init_type
            else:
                node.initializer.target_type = "str"
                init_type = self.analyze_node(node.initializer)
                var_type = init_type
        else:
            init_type = self.analyze_node(node.initializer) if node.initializer else TYPE_VOID

            # Type Inference or Explicit Type Check
            if node.type_annotation:
                annot_type = self.resolve_type(node.type_annotation)
                if node.initializer and not init_type.is_assignable_to(annot_type):
                    self.error(f"Type mismatch: expected '{annot_type}', but found '{init_type}'", node)
                var_type = annot_type
            else:
                if not node.initializer:
                    self.error(f"Cannot infer type for variable '{node.name}' without initializer", node)
                var_type = init_type

        symbol = Symbol(node.name, var_type, node.is_mut, node)
        self.defined_symbols.append(symbol)
        if not self.current_scope.define(symbol):
            self.error(f"Variable '{node.name}' is already defined in this scope", node)
        self.node_types[id(node)] = var_type
        return var_type

    def visit_assign(self, node: AssignNode) -> Type:
        # Check target: must be mutable identifier or member
        if isinstance(node.target, IdentifierNode):
            sym = self.current_scope.lookup(node.target.name)
            if not sym:
                self.error(f"Undefined variable '{node.target.name}'", node.target)
            if not sym.is_mut:
                self.error(f"Cannot reassign immutable variable '{node.target.name}'. Declare it with 'mut' instead.", node)
            if (
                isinstance(node.value, CallNode)
                and isinstance(node.value.callee, IdentifierNode)
                and node.value.callee.name in ("input", "readln")
            ):
                node.value.target_type = sym.type.name
                val_type = sym.type
            else:
                val_type = self.analyze_node(node.value)
            if not val_type.is_assignable_to(sym.type):
                self.error(f"Type mismatch in assignment to '{node.target.name}': cannot assign '{val_type}' to '{sym.type}'", node)
            return sym.type
        elif isinstance(node.target, MemberAccessNode):
            obj_type = self.analyze_node(node.target.object_expr)
            if isinstance(obj_type, ClassType):
                if node.target.member in obj_type.properties:
                    prop_t, has_get, has_set, is_pub = obj_type.properties[node.target.member]
                    if not has_set:
                        self.error(f"Cannot assign to read-only property '{node.target.member}' of class '{obj_type.name}'", node.target)
                    if not is_pub and self.current_class != obj_type:
                        self.error(f"Cannot access private property '{node.target.member}' of class '{obj_type.name}'", node.target)
                    val_type = self.analyze_node(node.value)
                    if not val_type.is_assignable_to(prop_t):
                        self.error(f"Type mismatch in property assignment: cannot assign '{val_type}' to '{prop_t}'", node)
                    node.is_property_assign = True
                    return prop_t

                field_type = obj_type.fields.get(node.target.member)
                if not field_type:
                    self.error(f"Class '{obj_type.name}' has no field '{node.target.member}'", node.target)
                if (
                    isinstance(node.value, CallNode)
                    and isinstance(node.value.callee, IdentifierNode)
                    and node.value.callee.name in ("input", "readln")
                ):
                    node.value.target_type = field_type.name
                    val_type = field_type
                else:
                    val_type = self.analyze_node(node.value)
                if not val_type.is_assignable_to(field_type):
                    self.error(f"Type mismatch in field assignment: cannot assign '{val_type}' to '{field_type}'", node)
                return field_type

        elif isinstance(node.target, IndexAccessNode):
            obj_type = self.analyze_node(node.target.object_expr)
            idx_type = self.analyze_node(node.target.index)
            val_type = self.analyze_node(node.value)
            if isinstance(obj_type, ClassType):
                if obj_type.name.startswith("List_"):
                    elem_name = obj_type.name[5:]
                    expected_t = self.resolve_type(elem_name)
                    if not val_type.is_assignable_to(expected_t):
                        self.error(f"Type mismatch in index assignment: cannot assign '{val_type}' to element type '{expected_t}'", node)
                    node.is_index_assign = True
                    return expected_t
                if "set" in obj_type.methods:
                    node.is_index_assign = True
                    return val_type
                if "op_index_set" in obj_type.methods:
                    node.is_index_assign = True
                    return val_type
                self.error(f"Class '{obj_type.name}' does not support index assignment (no 'set' method)", node.target)
            self.error(f"Cannot assign to index of type '{obj_type}'", node.target)
            return val_type

        return val_type

    def visit_function_def(self, node: FunctionDefNode) -> Type:
        ret_type = self.resolve_type(node.return_type)
        func_scope = Scope(parent=self.current_scope, kind="function")
        prev_scope = self.current_scope
        prev_func = self.current_function
        self.current_scope = func_scope
        self.current_function = node

        # Add parameters to local function scope
        for param in node.params:
            p_type = self.resolve_type(param.type_name)
            func_scope.define(Symbol(param.name, p_type, False, param))

        # Analyze body
        self.visit_block(node.body)

        self.current_scope = prev_scope
        self.current_function = prev_func
        return ret_type

    def visit_class_def(self, node: ClassDefNode) -> Type:
        cls_type = self.classes[node.name]
        prev_class = self.current_class
        self.current_class = cls_type

        # Analyze constructors
        all_ctors = node.constructors if getattr(node, "constructors", None) else ([node.constructor] if node.constructor else [])
        for ctor in all_ctors:
            ctor_scope = Scope(parent=self.current_scope, kind="constructor")
            # Define 'self'
            ctor_scope.define(Symbol("self", cls_type, True, ctor))
            for p in ctor.params:
                p_type = self.resolve_type(p.type_name)
                ctor_scope.define(Symbol(p.name, p_type, False, p))
            prev_scope = self.current_scope
            self.current_scope = ctor_scope
            self.visit_block(ctor.body)
            self.current_scope = prev_scope

        # Analyze methods
        for method in node.methods:
            method_scope = Scope(parent=self.current_scope, kind="method")
            method_scope.define(Symbol("self", cls_type, True, method))
            prev_scope = self.current_scope
            self.current_scope = method_scope
            self.visit_function_def(method)
            self.current_scope = prev_scope

        # Analyze properties (Phase 11)
        for prop in getattr(node, "properties", []):
            prop_type = self.resolve_type(prop.type_name)
            if prop.getter_body:
                getter_scope = Scope(parent=self.current_scope, kind="method")
                getter_scope.define(Symbol("self", cls_type, True, prop))
                prev_scope = self.current_scope
                prev_func = self.current_function
                self.current_scope = getter_scope
                self.current_function = FunctionDefNode(line=prop.line, col=prop.col, name=f"get_{prop.name}", params=[], return_type=prop.type_name, body=prop.getter_body)
                self.visit_block(prop.getter_body)
                self.current_scope = prev_scope
                self.current_function = prev_func
            if prop.setter_body:
                setter_scope = Scope(parent=self.current_scope, kind="method")
                setter_scope.define(Symbol("self", cls_type, True, prop))
                setter_param_name = prop.setter_param or "val"
                setter_scope.define(Symbol(setter_param_name, prop_type, False, prop))
                prev_scope = self.current_scope
                prev_func = self.current_function
                self.current_scope = setter_scope
                self.current_function = FunctionDefNode(line=prop.line, col=prop.col, name=f"set_{prop.name}", params=[ParamNode(line=prop.line, col=prop.col, name=setter_param_name, type_name=prop.type_name)], return_type="void", body=prop.setter_body)
                self.visit_block(prop.setter_body)
                self.current_scope = prev_scope
                self.current_function = prev_func

        # Analyze operators (Phase 11)
        for op in getattr(node, "operators", []):
            op_scope = Scope(parent=self.current_scope, kind="method")
            op_scope.define(Symbol("self", cls_type, True, op))
            if op.params:
                p = op.params[0]
                p_type = self.resolve_type(p.type_name)
                op_scope.define(Symbol(p.name, p_type, False, p))
            prev_scope = self.current_scope
            prev_func = self.current_function
            self.current_scope = op_scope
            self.current_function = FunctionDefNode(line=op.line, col=op.col, name=f"op_{op.op}", params=op.params, return_type=op.return_type, body=op.body)
            self.visit_block(op.body)
            self.current_scope = prev_scope
            self.current_function = prev_func

        self.current_class = prev_class
        return cls_type

    def visit_block(self, node: BlockNode) -> Type:
        block_scope = Scope(parent=self.current_scope, kind="block")
        prev_scope = self.current_scope
        self.current_scope = block_scope

        last_type = TYPE_VOID
        for stmt in node.statements:
            last_type = self.analyze_node(stmt)

        self.current_scope = prev_scope
        return last_type

    def visit_if(self, node: IfNode) -> Type:
        cond_type = self.analyze_node(node.condition)
        if cond_type != TYPE_BOOL:
            self.error(f"Condition for 'if' must be 'bool', found '{cond_type}'", node.condition)
        self.visit_block(node.then_block)
        if node.else_block:
            self.visit_block(node.else_block)
        return TYPE_VOID

    def visit_guard(self, node: GuardNode) -> Type:
        cond_t = self.analyze_node(node.condition)
        if cond_t != TYPE_BOOL:
            self.error("Guard condition must evaluate to a boolean expression", node.condition)
        self.visit_block(node.else_block)
        return TYPE_VOID

    def visit_match(self, node: MatchNode) -> Type:
        target_type = self.analyze_node(node.expr)
        node.target_type = target_type

        if isinstance(target_type, EnumType):
            node.is_enum_match = True
            all_variants = set(target_type.variants.keys())
            handled_variants = set()
            has_wildcard = False

            for case in node.cases:
                pat = case.pattern
                v_name = None
                bindings = []

                if isinstance(pat, IdentifierNode):
                    if pat.name == "_":
                        has_wildcard = True
                    elif pat.name in target_type.variants:
                        v_name = pat.name
                    else:
                        self.error(f"Unknown enum variant '{pat.name}' for enum '{target_type.name}'", pat)
                elif isinstance(pat, MemberAccessNode):
                    if isinstance(pat.object_expr, IdentifierNode) and pat.object_expr.name == target_type.name:
                        if pat.member in target_type.variants:
                            v_name = pat.member
                        else:
                            self.error(f"Unknown variant '{pat.member}' for enum '{target_type.name}'", pat)
                    else:
                        self.error(f"Invalid match pattern on enum '{target_type.name}'", pat)
                elif isinstance(pat, CallNode):
                    if isinstance(pat.callee, IdentifierNode):
                        v_name = pat.callee.name
                    elif isinstance(pat.callee, MemberAccessNode):
                        v_name = pat.callee.member
                    
                    if v_name in target_type.variants:
                        bindings = pat.args
                    else:
                        self.error(f"Unknown enum variant '{v_name}' in match pattern", pat)
                else:
                    self.error(f"Invalid pattern for enum '{target_type.name}'", pat)

                case_scope = Scope(parent=self.current_scope, kind="match_case")
                prev_scope = self.current_scope
                self.current_scope = case_scope

                if v_name:
                    handled_variants.add(v_name)
                    variant = target_type.variants[v_name]
                    pat.resolved_enum = target_type.name
                    pat.resolved_tag = variant.tag
                    case.resolved_tag = variant.tag
                    case.variant_name = v_name
                    case.field_names = [f[0] for f in variant.fields]
                    case.field_types = [f[1].name for f in variant.fields]

                    if bindings:
                        if len(bindings) != len(variant.fields):
                            self.error(f"Variant '{v_name}' expects {len(variant.fields)} payload bindings, but got {len(bindings)}", pat)
                        for b_arg, (f_name, f_type) in zip(bindings, variant.fields):
                            if isinstance(b_arg, IdentifierNode):
                                case_scope.define(Symbol(b_arg.name, f_type, False, b_arg))

                if case.guard_expr:
                    g_type = self.analyze_node(case.guard_expr)
                    if g_type != TYPE_BOOL:
                        self.error("Match case guard condition must be a boolean", case.guard_expr)

                self.visit_block(case.body)
                self.current_scope = prev_scope

            if not has_wildcard:
                missing = all_variants - handled_variants
                if missing:
                    self.error(f"Non-exhaustive pattern match on enum '{target_type.name}': unhandled variants {', '.join(sorted(missing))}", node)
        else:
            node.is_enum_match = False
            for case in node.cases:
                pat = case.pattern
                if isinstance(pat, IdentifierNode) and pat.name == "_":
                    pass
                else:
                    p_type = self.analyze_node(pat)
                    if not p_type.is_assignable_to(target_type):
                        self.error(f"Pattern type '{p_type}' does not match expression type '{target_type}'", pat)

                case_scope = Scope(parent=self.current_scope, kind="match_case")
                prev_scope = self.current_scope
                self.current_scope = case_scope

                if case.guard_expr:
                    g_type = self.analyze_node(case.guard_expr)
                    if g_type != TYPE_BOOL:
                        self.error("Match case guard condition must be a boolean", case.guard_expr)

                self.visit_block(case.body)
                self.current_scope = prev_scope

        return TYPE_VOID


    def visit_extend_def(self, node: ExtendDefNode) -> Type:
        cls_type = self.classes.get(node.target_type)
        if not cls_type:
            self.error(f"Cannot extend unknown type '{node.target_type}'", node)
        prev_class = self.current_class
        self.current_class = cls_type
        for method in node.methods:
            method_scope = Scope(parent=self.current_scope, kind="method")
            method_scope.define(Symbol("self", cls_type, True, method))
            prev_scope = self.current_scope
            self.current_scope = method_scope
            self.visit_function_def(method)
            self.current_scope = prev_scope
        self.current_class = prev_class
        return TYPE_VOID


    def visit_while(self, node: WhileNode) -> Type:
        cond_type = self.analyze_node(node.condition)
        if cond_type != TYPE_BOOL:
            self.error(f"Condition for 'while' must be 'bool', found '{cond_type}'", node.condition)
        self.visit_block(node.body)
        return TYPE_VOID

    def visit_for(self, node: ForNode) -> Type:
        range_type = self.analyze_node(node.range_expr)
        for_scope = Scope(parent=self.current_scope, kind="for")
        elem_type = TYPE_I64
        if not isinstance(node.range_expr, RangeNode):
            if range_type.name.startswith("List_"):
                elem_name = range_type.name[5:]
                elem_type = self.resolve_type(elem_name)
            elif range_type.name.startswith("Set_"):
                elem_name = range_type.name[4:]
                elem_type = self.resolve_type(elem_name)
            elif isinstance(range_type, ClassType) and "get" in range_type.methods:
                elem_type = range_type.methods["get"].return_type
            elif range_type == TYPE_STR:
                elem_type = TYPE_STR
        for_scope.define(Symbol(node.var_name, elem_type, False, node))
        prev_scope = self.current_scope
        self.current_scope = for_scope
        self.visit_block(node.body)
        self.current_scope = prev_scope
        return TYPE_VOID

    def visit_loop(self, node: LoopNode) -> Type:
        self.visit_block(node.body)
        return TYPE_VOID

    def visit_return(self, node: ReturnNode) -> Type:
        if not self.current_function:
            self.error("'return' outside of a function body", node)
        expected_ret = self.resolve_type(self.current_function.return_type)
        actual_ret = self.analyze_node(node.value) if node.value else TYPE_VOID

        if not actual_ret.is_assignable_to(expected_ret):
            self.error(f"Function '{self.current_function.name}' expects return type '{expected_ret}', but returned '{actual_ret}'", node)
        return actual_ret

    def visit_defer(self, node: DeferNode) -> Type:
        self.analyze_node(node.statement)
        return TYPE_VOID

    def visit_literal(self, node: LiteralNode) -> Type:
        type_map = {
            "i64": TYPE_I64,
            "f64": TYPE_F64,
            "str": TYPE_STR,
            "bool": TYPE_BOOL,
            "char": TYPE_CHAR,
            "null": TYPE_NULL,
        }
        res_type = type_map.get(node.type_name, TYPE_VOID)
        self.node_types[id(node)] = res_type
        return res_type

    def visit_identifier(self, node: IdentifierNode) -> Type:
        sym = self.current_scope.lookup(node.name)
        if not sym:
            # Check built-in global functions (print, println, input, readln, typeof)
            if node.name in ("print", "println", "eprintln", "assert", "panic", "arx_time_now", "input", "readln", "typeof"):
                return TYPE_STR if node.name in ("input", "readln", "typeof") else TYPE_VOID
            # Check parameterless enum variant
            for e_name, e_type in self.enums.items():
                if node.name in e_type.variants:
                    variant = e_type.variants[node.name]
                    if not variant.fields:
                        node.is_enum_variant = True
                        node.enum_name = e_name
                        node.variant_name = node.name
                        node.resolved_mangled_name = f"Arx_{e_name}_{node.name}"
                        self.node_types[id(node)] = e_type
                        return e_type
            if node.name in self.enums:
                return self.enums[node.name]
            if node.name in ("sleep_ms", "arx_sleep_ms", "arx_channel_new", "arx_channel_send", "arx_channel_recv", "arx_channel_close", "arx_channel_free", "arx_thread_join", "arx_canvas_set_pixel", "arx_canvas_fill_rect", "arx_canvas_clear"):
                return FunctionType([], TYPE_VOID)
            if node.name == "arx_now_ms":
                return FunctionType([], TYPE_F64)
            if node.name.startswith("arx_list_") or node.name.startswith("arx_str_"):
                return FunctionType([], TYPE_I64)
            self.error(f"Undefined variable or identifier: '{node.name}'", node)
        sym.is_used = True
        self.node_types[id(node)] = sym.type
        return sym.type


    def visit_binary_op(self, node: BinaryOpNode) -> Type:
        left_type = self.analyze_node(node.left)
        right_type = self.analyze_node(node.right)

        # Phase 11: Check operator overloading on class types
        if isinstance(left_type, ClassType):
            op_res = left_type.resolve_operator(node.op, right_type)
            if op_res:
                ret_t, mangled_name, op_node = op_res
                node.is_operator_overload = True
                node.op_method_name = OPERATOR_METHOD_NAMES.get(node.op, "op_unknown")
                node.resolved_mangled_name = mangled_name
                node.return_type_name = ret_t.name
                self.node_types[id(node)] = ret_t
                return ret_t

        # Arithmetic
        if node.op in ("+", "-", "*", "/", "%", "**"):
            if left_type == TYPE_F64 or right_type == TYPE_F64:
                res_type = TYPE_F64
            else:
                res_type = TYPE_I64
        # Comparisons
        elif node.op in ("==", "!=", "<", "<=", ">", ">="):
            res_type = TYPE_BOOL
        # Logical
        elif node.op in ("&&", "||"):
            res_type = TYPE_BOOL
        # Null coalescing
        elif node.op == "??":
            res_type = right_type
        else:
            res_type = left_type

        self.node_types[id(node)] = res_type
        return res_type

    def visit_unary_op(self, node: UnaryOpNode) -> Type:
        operand_type = self.analyze_node(node.operand)
        if node.op == "!":
            return TYPE_BOOL
        return operand_type

    def visit_call(self, node: CallNode) -> Type:
        # Check callee
        if isinstance(node.callee, IdentifierNode):
            name = node.callee.name
            if name in ("println", "print", "eprintln"):
                for arg in node.args:
                    self.analyze_node(arg)
                return TYPE_VOID
            # Check enum variant constructor calls: Variant(args)
            for e_name, e_type in self.enums.items():
                if name in e_type.variants:
                    node.is_enum_constructor = True
                    node.enum_name = e_name
                    node.variant_name = name
                    node.resolved_mangled_name = f"Arx_{e_name}_{name}"
                    for arg in node.args:
                        self.analyze_node(arg)
                    return e_type

            if name in ("input", "readln"):
                for arg in node.args:
                    self.analyze_node(arg)
                target_t = getattr(node, "target_type", None)
                if target_t:
                    return self.resolve_type(target_t)
                return TYPE_STR
            if name == "typeof":
                if len(node.args) != 1:
                    self.error(f"'typeof' expects exactly 1 argument, but got {len(node.args)}", node)
                arg_type = self.analyze_node(node.args[0])
                node.inferred_type = arg_type.name
                return TYPE_STR
            if name == "arx_time_now":
                return TYPE_F64
            if name in ("sleep_ms", "arx_sleep_ms"):
                for arg in node.args:
                    self.analyze_node(arg)
                return TYPE_VOID
            if name in ("arx_channel_new", "arx_channel_recv"):
                for arg in node.args:
                    self.analyze_node(arg)
                return TYPE_I64
            if name in ("arx_channel_send", "arx_channel_close", "arx_channel_free", "arx_thread_join", "arx_canvas_set_pixel", "arx_canvas_fill_rect", "arx_canvas_clear"):
                for arg in node.args:
                    self.analyze_node(arg)
                return TYPE_VOID
            if name == "arx_now_ms":
                return TYPE_F64
            if (name.startswith("arx_list_") or name.startswith("arx_str_") or 
                name.startswith("arx_map_") or name.startswith("arx_set_") or 
                name.startswith("arx_stack_") or name.startswith("arx_queue_") or 
                name.startswith("arx_deque_") or name.startswith("arx_bytebuf_")):
                for arg in node.args:
                    self.analyze_node(arg)
                if name in (
                    "arx_str_trim", "arx_str_to_upper", "arx_str_to_lower", "arx_str_replace",
                    "arx_str_copy", "arx_str_slice", "arx_str_join", "arx_str_repeat",
                    "arx_str_concat", "arx_str_char_at", "arx_list_get_str", "arx_list_pop_str",
                    "arx_list_swap_remove_str", "arx_list_remove_at_str",
                    "arx_map_get_str_str", "arx_map_get_i64_str", "arx_set_get_str"
                ):
                    return TYPE_STR
                elif name in (
                    "arx_str_contains", "arx_str_starts_with", "arx_str_ends_with",
                    "arx_list_contains", "arx_list_contains_str", "arx_map_has", "arx_map_has_str",
                    "arx_set_add", "arx_set_has", "arx_set_remove",
                    "arx_set_add_str", "arx_set_has_str", "arx_set_remove_str"
                ):
                    return TYPE_BOOL
                elif name in (
                    "arx_list_get_f64", "arx_list_pop_f64",
                    "arx_list_swap_remove_f64", "arx_list_remove_at_f64",
                    "arx_bytebuf_read_f32", "arx_bytebuf_read_f64"
                ):
                    return TYPE_F64
                elif name in (
                    "arx_list_push", "arx_list_set", "arx_list_clear", "arx_list_free",
                    "arx_list_reverse", "arx_list_sort", "arx_list_insert",
                    "arx_list_push_i64", "arx_list_push_str", "arx_list_push_f64",
                    "arx_list_set_i64", "arx_list_set_str", "arx_list_set_f64",
                    "arx_list_insert_str", "arx_list_insert_f64", "arx_list_insert_i64",
                    "arx_map_insert", "arx_map_remove", "arx_map_clear", "arx_map_free",
                    "arx_map_insert_str_str", "arx_map_insert_str_i64", "arx_map_insert_i64_str", "arx_map_remove_str",
                    "arx_set_clear", "arx_set_free",
                    "arx_stack_push", "arx_stack_clear", "arx_stack_free",
                    "arx_queue_enqueue", "arx_queue_clear", "arx_queue_free",
                    "arx_deque_push_back", "arx_deque_push_front", "arx_deque_clear", "arx_deque_free",
                    "arx_bytebuf_write_u8", "arx_bytebuf_write_i16_le", "arx_bytebuf_write_i32_le",
                    "arx_bytebuf_write_i64_le", "arx_bytebuf_write_f32_le", "arx_bytebuf_write_f64_le",
                    "arx_bytebuf_clear", "arx_bytebuf_free"
                ):
                    return TYPE_VOID
                return TYPE_I64
            if name in self.classes:
                # Value / Stack class instantiation (e.g. Hero("Arthur"))
                cls_type = self.classes[name]
                arg_types = [self.analyze_node(arg) for arg in node.args]
                res = cls_type.resolve_constructor(arg_types)
                if res:
                    fn_type, mangled_name, ctor_node = res
                    node.resolved_mangled_name = mangled_name
                    return cls_type
                elif cls_type.constructors:
                    expected = [
                        f"{name}({', '.join(p.name for p in c[0].param_types)})"
                        for c in cls_type.constructors if c[1] is None
                    ]
                    actual = f"{name}({', '.join(a.name for a in arg_types)})"
                    self.error(f"No matching constructor for '{actual}'. Available overloads: {', '.join(expected)}", node)
                elif len(node.args) > 0:
                    self.error(f"Class '{name}' has default constructor taking 0 arguments, but received {len(node.args)}", node)
                return cls_type
            if name in self.functions:
                fn_type = self.functions[name]
                for arg in node.args:
                    self.analyze_node(arg)
                return fn_type.return_type

        # Member method call or variable call
        if isinstance(node.callee, MemberAccessNode):
            if isinstance(node.callee.object_expr, IdentifierNode) and node.callee.object_expr.name in self.enums:
                e_name = node.callee.object_expr.name
                e_type = self.enums[e_name]
                v_name = node.callee.member
                if v_name in e_type.variants:
                    node.is_enum_constructor = True
                    node.enum_name = e_name
                    node.variant_name = v_name
                    node.resolved_mangled_name = f"Arx_{e_name}_{v_name}"
                    for arg in node.args:
                        self.analyze_node(arg)
                    return e_type
                else:
                    self.error(f"Enum '{e_name}' has no variant '{v_name}'", node)

            obj_type = self.analyze_node(node.callee.object_expr)
            if isinstance(obj_type, ClassType):
                arg_types = [self.analyze_node(arg) for arg in node.args]
                res = obj_type.resolve_method(node.callee.member, arg_types)
                if res:
                    fn_type, is_pub, mangled_name, method_node = res
                    if not is_pub and self.current_class != obj_type:
                        self.error(f"Cannot access private method '{node.callee.member}' of class '{obj_type.name}'", node)
                    node.resolved_mangled_name = mangled_name
                    node.callee.resolved_mangled_name = mangled_name
                    return fn_type.return_type
                else:
                    if node.callee.member in obj_type.method_overloads:
                        expected = [
                            f"{node.callee.member}({', '.join(p.name for p in m[0].param_types)})"
                            for m in obj_type.method_overloads[node.callee.member]
                        ]
                        actual = f"{node.callee.member}({', '.join(a.name for a in arg_types)})"
                        self.error(f"No matching overload for '{actual}' on class '{obj_type.name}'. Available: {', '.join(expected)}", node)
                    else:
                        self.error(f"Class '{obj_type.name}' has no method '{node.callee.member}'", node)
            elif isinstance(obj_type, TraitType):
                arg_types = [self.analyze_node(arg) for arg in node.args]
                m_name = node.callee.member
                if m_name in obj_type.methods:
                    fn_type = obj_type.methods[m_name]
                    if len(fn_type.param_types) != len(arg_types):
                        self.error(f"Trait method '{m_name}' expects {len(fn_type.param_types)} arguments, but received {len(arg_types)}", node)
                    for a_t, p_t in zip(arg_types, fn_type.param_types):
                        if not a_t.is_assignable_to(p_t):
                            self.error(f"Argument type mismatch for trait method '{m_name}': expected '{p_t}', got '{a_t}'", node)
                    return fn_type.return_type
                else:
                    self.error(f"Trait '{obj_type.name}' has no method '{m_name}'", node)
            elif obj_type == TYPE_STR:
                member = node.callee.member
                for arg in node.args:
                    self.analyze_node(arg)
                if member in ("trim", "to_upper", "to_lower", "replace"):
                    node.resolved_mangled_name = f"arx_str_{member}"
                    return TYPE_STR
                elif member in ("contains", "starts_with", "ends_with"):
                    node.resolved_mangled_name = f"arx_str_{member}"
                    return TYPE_BOOL
                elif member in ("len", "length"):
                    node.resolved_mangled_name = "arx_str_len"
                    return TYPE_I64
                elif member == "split":
                    node.resolved_mangled_name = "arx_str_split"
                    list_str = self.classes.get("List_str")
                    if not list_str:
                        list_str = ClassType("List_str")
                    return list_str
                else:
                    self.error(f"Type 'str' has no method '{member}'", node)


        callee_type = self.analyze_node(node.callee)
        if isinstance(callee_type, FunctionType):
            return callee_type.return_type
        return TYPE_VOID

    def visit_pipeline(self, node: PipelineNode) -> Type:
        # Pipeline: left |> right(args)
        # Type of left is fed as first argument to right
        left_type = self.analyze_node(node.left)
        return self.visit_call(node.right)

    def visit_cascade(self, node: CascadeNode) -> Type:
        target_t = self.analyze_node(node.target)
        if not isinstance(target_t, ClassType):
            self.error(f"Cascade mutation '~>' can only be invoked on class instances, but found '{target_t.name}'", node)

        if isinstance(node.call.callee, IdentifierNode):
            method_name = node.call.callee.name
        elif isinstance(node.call.callee, MemberAccessNode):
            method_name = node.call.callee.member
        else:
            self.error("Cascade target must be followed by a method call", node)

        arg_types = [self.analyze_node(arg) for arg in node.call.args]
        res = target_t.resolve_method(method_name, arg_types)
        if not res:
            self.error(f"Class '{target_t.name}' has no method '{method_name}' matching arguments", node.call)

        fn_type, is_pub, mangled_name, method_node = res
        if not is_pub and self.current_class != target_t:
            self.error(f"Cannot access private method '{method_name}' of class '{target_t.name}'", node.call)

        node.call.resolved_mangled_name = mangled_name
        node.target_type = target_t
        self.node_types[id(node)] = target_t
        return target_t


    def visit_member_access(self, node: MemberAccessNode) -> Type:
        if isinstance(node.object_expr, IdentifierNode) and node.object_expr.name in self.enums:
            e_name = node.object_expr.name
            e_type = self.enums[e_name]
            v_name = node.member
            if v_name in e_type.variants:
                node.is_enum_variant = True
                node.enum_name = e_name
                node.variant_name = v_name
                node.resolved_mangled_name = f"Arx_{e_name}_{v_name}"
                self.node_types[id(node)] = e_type
                return e_type
            else:
                self.error(f"Enum '{e_name}' has no variant '{v_name}'", node)

        obj_type = self.analyze_node(node.object_expr)

        if obj_type == TYPE_STR:
            if node.member in ("len", "length"):
                node.is_str_len = True
                return TYPE_I64
            self.error(f"Type 'str' has no property '{node.member}'", node)

        if isinstance(obj_type, ClassType):
            # Check properties (Phase 11)
            if node.member in obj_type.properties:
                prop_t, has_get, has_set, is_pub = obj_type.properties[node.member]
                if not has_get:
                    self.error(f"Cannot read write-only property '{node.member}' of class '{obj_type.name}'", node)
                if not is_pub and self.current_class != obj_type:
                    self.error(f"Cannot access private property '{node.member}' of class '{obj_type.name}'", node)
                node.is_property = True
                node.prop_type = prop_t.name
                self.node_types[id(node)] = prop_t
                return prop_t

            # Check fields
            if node.member in obj_type.fields:
                is_pub = obj_type.field_access.get(node.member, False)
                # Check privacy: if not public and not inside class method, error!
                if not is_pub and self.current_class != obj_type:
                    self.error(f"Cannot access private field '{node.member}' of class '{obj_type.name}'", node)
                return obj_type.fields[node.member]
            # Check methods
            if node.member in obj_type.methods:
                return obj_type.methods[node.member]
            if node.member in obj_type.method_overloads:
                return obj_type.method_overloads[node.member][0][0]
            self.error(f"Class '{obj_type.name}' has no member '{node.member}'", node)
        return TYPE_VOID

    def visit_index_access(self, node: IndexAccessNode) -> Type:
        obj_type = self.analyze_node(node.object_expr)
        if isinstance(node.index, RangeNode):
            self.analyze_node(node.index.start)
            self.analyze_node(node.index.end)
            if obj_type == TYPE_STR:
                return TYPE_STR
            if isinstance(obj_type, ClassType):
                return obj_type
            return obj_type

        idx_type = self.analyze_node(node.index)
        if obj_type == TYPE_STR:
            return TYPE_STR
        if isinstance(obj_type, ClassType):
            if obj_type.name.startswith("List_"):
                elem_name = obj_type.name[5:]
                return self.resolve_type(elem_name)
            if obj_type.name.startswith("Map_"):
                val_name = obj_type.name.split("_")[2]
                return self.resolve_type(val_name)
            if "get" in obj_type.methods:
                return obj_type.methods["get"].return_type
            if "op_index" in obj_type.methods:
                return obj_type.methods["op_index"].return_type
            self.error(f"Class '{obj_type.name}' does not support index access (no 'get' method)", node)
        self.error(f"Cannot index into expression of type '{obj_type}'", node)
        return TYPE_VOID

    def visit_range(self, node: RangeNode) -> Type:
        self.analyze_node(node.start)
        self.analyze_node(node.end)
        return TYPE_I64

    def visit_new(self, node: NewNode) -> Type:
        if node.class_name not in self.classes:
            self.error(f"Unknown class in 'new': '{node.class_name}'", node)
        for arg in node.args:
            self.analyze_node(arg)
        return self.classes[node.class_name]

    def visit_cast(self, node: CastNode) -> Type:
        src_type = self.analyze_node(node.expr)
        node.src_type = src_type.name
        target = self.resolve_type(node.target_type)
        self.node_types[id(node)] = target
        return target

    def visit_string_interp(self, node: StringInterpNode) -> Type:
        for part in node.parts:
            if isinstance(part, ASTNode):
                self.analyze_node(part)
        return TYPE_STR

    def visit_spawn(self, node: SpawnNode) -> Type:
        self.visit_call(node.call)
        if "ThreadHandle" in self.classes:
            return self.classes["ThreadHandle"]
        return TYPE_I64

    def visit_tuple(self, node: TupleNode) -> Type:
        elem_types = [self.analyze_node(e) for e in node.elements]
        tuple_name = f"Tuple_{'_'.join(t.name for t in elem_types)}"
        tuple_type = lookup_type(tuple_name, self.classes, self.enums, self.traits)
        self.node_types[id(node)] = tuple_type
        return tuple_type

    def visit_tuple_destructure(self, node: TupleDestructureNode) -> Type:
        init_type = self.analyze_node(node.initializer)
        if not init_type.name.startswith("Tuple_"):
            self.error(f"Cannot destructure non-tuple expression of type '{init_type.name}'", node)
        parts = init_type.name[6:].split("_")
        if len(parts) != len(node.names):
            self.error(f"Destructuring pattern has {len(node.names)} variables but tuple has {len(parts)} elements", node)
        for i, name in enumerate(node.names):
            elem_t = self.resolve_type(parts[i])
            self.current_scope.define(Symbol(name, elem_t, node.is_mut, node))
        return TYPE_VOID
