"""
Aerix Compiler (arxc) — Aerix Intermediate Representation (AIR)
Defines the linear, 3-address code IR and the AST-to-AIR lowering engine.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
from src.frontend.ast_nodes import (
    ASTNode, ProgramNode, FunctionDefNode, BlockNode, VarDeclNode,
    AssignNode, IfNode, WhileNode, ForNode, LoopNode, BreakNode,
    ContinueNode, ReturnNode, DeferNode, ExprStmtNode, LiteralNode,
    IdentifierNode, BinaryOpNode, UnaryOpNode, CallNode, MemberAccessNode,
    PipelineNode, RangeNode, NewNode, CastNode, StringInterpNode,
    ClassDefNode, CIncludeNode, CExternNode, PropertyDefNode, OperatorDefNode,
    GuardNode, CascadeNode, ExtendDefNode,
    EnumDefNode, EnumVariantNode, MatchNode, MatchCaseNode, SpawnNode
)




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


# ==========================================
# AIR Instruction Hierarchy
# ==========================================

class AIRInstruction:
    """Base class for all AIR 3-address code instructions."""
    pass


@dataclass
class AIRConst(AIRInstruction):
    dest: str
    value: Any
    type_name: str

    def __repr__(self) -> str:
        return f"{self.dest} = CONST {self.value!r} ({self.type_name})"


@dataclass
class AIRBinOp(AIRInstruction):
    dest: str
    op: str
    left: str
    right: str

    def __repr__(self) -> str:
        return f"{self.dest} = {self.left} {self.op} {self.right}"


@dataclass
class AIRUnaryOp(AIRInstruction):
    dest: str
    op: str
    operand: str

    def __repr__(self) -> str:
        return f"{self.dest} = {self.op}{self.operand}"


@dataclass
class AIRAssign(AIRInstruction):
    dest: str
    src: str

    def __repr__(self) -> str:
        return f"{self.dest} = {self.src}"


@dataclass
class AIRLoad(AIRInstruction):
    dest: str
    var_name: str

    def __repr__(self) -> str:
        return f"{self.dest} = LOAD {self.var_name}"


@dataclass
class AIRStore(AIRInstruction):
    var_name: str
    src: str

    def __repr__(self) -> str:
        return f"STORE {self.var_name} = {self.src}"


@dataclass
class AIRCast(AIRInstruction):
    dest: str
    src: str
    target_type: str
    src_type: str = "unknown"

    def __repr__(self) -> str:
        return f"{self.dest} = CAST ({self.target_type}) {self.src} (from {self.src_type})"


@dataclass
class AIRCall(AIRInstruction):
    dest: Optional[str]
    fn_name: str
    args: List[str]

    def __repr__(self) -> str:
        args_str = ", ".join(self.args)
        if self.dest:
            return f"{self.dest} = CALL {self.fn_name}({args_str})"
        return f"CALL {self.fn_name}({args_str})"


@dataclass
class AIRCallConstructor(AIRInstruction):
    dest: str
    class_name: str
    args: List[str]
    ctor_name: Optional[str] = None

    def __repr__(self) -> str:
        args_str = ", ".join(self.args)
        ctor = self.ctor_name or self.class_name
        return f"{self.dest} = INIT {ctor}({args_str})"


@dataclass
class AIRCallMethod(AIRInstruction):
    dest: Optional[str]
    class_name: str
    method_name: str
    instance: str
    args: List[str]

    def __repr__(self) -> str:
        args_str = ", ".join([self.instance] + self.args)
        if self.dest:
            return f"{self.dest} = CALL_STATIC {self.class_name}_{self.method_name}({args_str})"
        return f"CALL_STATIC {self.class_name}_{self.method_name}({args_str})"


@dataclass
class AIRCallVirtual(AIRInstruction):
    dest: Optional[str]
    vtable_idx: int
    method_name: str
    instance: str
    args: List[str]

    def __repr__(self) -> str:
        args_str = ", ".join([self.instance] + self.args)
        if self.dest:
            return f"{self.dest} = CALL_VIRTUAL {self.instance}->vtable[{self.vtable_idx}] ({self.method_name})({args_str})"
        return f"CALL_VIRTUAL {self.instance}->vtable[{self.vtable_idx}] ({self.method_name})({args_str})"


@dataclass
class AIRGetField(AIRInstruction):
    dest: str
    instance: str
    field_name: str

    def __repr__(self) -> str:
        return f"{self.dest} = GET_FIELD {self.instance}.{self.field_name}"


@dataclass
class AIRSetField(AIRInstruction):
    instance: str
    field_name: str
    value: str

    def __repr__(self) -> str:
        return f"SET_FIELD {self.instance}.{self.field_name} = {self.value}"


@dataclass
class AIRBranchIf(AIRInstruction):
    condition: str
    target_label: str

    def __repr__(self) -> str:
        return f"BRANCH_IF {self.condition} GOTO {self.target_label}"


@dataclass
class AIRBranchIfNot(AIRInstruction):
    condition: str
    target_label: str

    def __repr__(self) -> str:
        return f"BRANCH_IF_NOT {self.condition} GOTO {self.target_label}"


@dataclass
class AIRJump(AIRInstruction):
    target_label: str

    def __repr__(self) -> str:
        return f"JUMP {self.target_label}"


@dataclass
class AIRLabel(AIRInstruction):
    name: str

    def __repr__(self) -> str:
        return f"{self.name}:"


@dataclass
class AIRReturn(AIRInstruction):
    value: Optional[str] = None

    def __repr__(self) -> str:
        return f"RETURN {self.value or 'void'}"


@dataclass
class AIRFormatString(AIRInstruction):
    dest: str
    fmt: str
    args: List[str]

    def __repr__(self) -> str:
        args_str = ", ".join(self.args)
        return f'{self.dest} = FORMAT "{self.fmt}" ({args_str})'


@dataclass
class AIRDeferPush(AIRInstruction):
    cleanup_instructions: List[AIRInstruction]

    def __repr__(self) -> str:
        return f"DEFER_PUSH ({len(self.cleanup_instructions)} insns)"


@dataclass
class AIRSpawn(AIRInstruction):
    dest: Optional[str]
    fn_name: str
    args: List[str]

    def __repr__(self) -> str:
        args_str = ", ".join(self.args)
        if self.dest:
            return f"{self.dest} = SPAWN {self.fn_name}({args_str})"
        return f"SPAWN {self.fn_name}({args_str})"


# ==========================================
# Higher-Level AIR Containers
# ==========================================

@dataclass
class AIRFunction:
    name: str
    params: List[str]
    return_type: str
    instructions: List[AIRInstruction] = field(default_factory=list)
    is_pub: bool = True
    is_static: bool = False
    param_types: List[str] = field(default_factory=list)
    var_types: Dict[str, str] = field(default_factory=dict)


@dataclass
class AIRClass:
    name: str
    base_class: Optional[str]
    fields: Dict[str, str]  # field_name -> type_name
    methods: Dict[str, AIRFunction] = field(default_factory=dict)
    constructor: Optional[AIRFunction] = None
    destructor: Optional[AIRFunction] = None
    constructors: Dict[str, AIRFunction] = field(default_factory=dict)


@dataclass
class AIRGetPayloadField(AIRInstruction):
    dest: str
    instance: str
    variant_name: str
    field_name: str

    def __repr__(self) -> str:
        return f"{self.dest} = GET_PAYLOAD {self.instance}.{self.variant_name}.{self.field_name}"


@dataclass
class AIREnumVariant:
    name: str
    tag: int
    fields: Dict[str, str]


@dataclass
class AIREnum:
    name: str
    variants: List[AIREnumVariant]


@dataclass
class AIRModule:
    name: str
    classes: Dict[str, AIRClass] = field(default_factory=dict)
    enums: Dict[str, AIREnum] = field(default_factory=dict)
    functions: Dict[str, AIRFunction] = field(default_factory=dict)
    c_includes: List[str] = field(default_factory=list)



# ==========================================
# AST ➔ AIR Lowering Engine
# ==========================================

class AIRLowering:
    def __init__(self):
        self.temp_count = 0
        self.label_count = 0
        self.current_insns: List[AIRInstruction] = []
        self.defer_stack: List[List[AIRInstruction]] = []
        self.temp_types: Dict[str, str] = {}
        self.var_types: Dict[str, str] = {}
        self.classes: Set[str] = set()
        self.class_fields: Dict[str, Dict[str, str]] = {}
        self.current_class: Optional[str] = None

    def new_temp(self) -> str:
        self.temp_count += 1
        return f"t{self.temp_count}"

    def new_label(self, prefix: str = "L") -> str:
        self.label_count += 1
        return f"{prefix}_{self.label_count}"

    def lower(self, program: ProgramNode) -> AIRModule:
        module = AIRModule(name="main_module")
        self.classes = {decl.name for decl in program.declarations if isinstance(decl, ClassDefNode)}
        self.class_fields = {
            decl.name: {f.name: f.type_name for f in decl.fields}
            for decl in program.declarations if isinstance(decl, ClassDefNode)
        }
        self.function_return_types = {
            decl.name: decl.return_type
            for decl in program.declarations if isinstance(decl, FunctionDefNode)
        }
        self.class_method_returns = {}
        for decl in program.declarations:
            if isinstance(decl, ClassDefNode):
                m_map = {}
                for m in decl.methods:
                    m_map[m.name] = m.return_type
                    if getattr(m, "mangled_name", None):
                        m_map[m.mangled_name] = m.return_type
                for p in getattr(decl, "properties", []):
                    m_map[f"get_{p.name}"] = p.type_name
                    m_map[f"set_{p.name}"] = "void"
                for op in getattr(decl, "operators", []):
                    op_m = OPERATOR_METHOD_NAMES.get(op.op, f"op_{op.op}")
                    m_map[op_m] = op.return_type
                    if getattr(op, "mangled_name", None):
                        m_map[op.mangled_name] = op.return_type
                self.class_method_returns[decl.name] = m_map
            elif isinstance(decl, ExtendDefNode):
                if decl.target_type not in self.class_method_returns:
                    self.class_method_returns[decl.target_type] = {}
                m_map = self.class_method_returns[decl.target_type]
                for m in decl.methods:
                    m_map[m.name] = m.return_type
                    if getattr(m, "mangled_name", None):
                        m_map[m.mangled_name] = m.return_type


        for decl in program.declarations:
            if isinstance(decl, CIncludeNode):
                module.c_includes.append(decl.header)
            elif isinstance(decl, FunctionDefNode):
                fn = self.lower_function(decl)
                module.functions[fn.name] = fn
            elif isinstance(decl, ClassDefNode):
                cls = self.lower_class(decl)
                module.classes[cls.name] = cls
            elif isinstance(decl, EnumDefNode):
                variants = [
                    AIREnumVariant(
                        name=v.name,
                        tag=v.tag,
                        fields={f.name: f.type_name for f in v.fields}
                    )
                    for v in decl.variants
                ]
                module.enums[decl.name] = AIREnum(decl.name, variants)
            elif isinstance(decl, ExtendDefNode):

                if decl.target_type in module.classes:
                    cls = module.classes[decl.target_type]
                    self.current_class = decl.target_type
                    for m in decl.methods:
                        fn = self.lower_function(m)
                        fn.params = ["self"] + fn.params
                        fn.param_types = ["self"] + fn.param_types
                        m_key = getattr(m, "mangled_name", None) or f"Arx_{decl.target_type}_{m.name}"
                        fn.name = m_key
                        cls.methods[m_key] = fn
                        cls.methods[m.name] = fn
                    self.current_class = None


        return module

    def lower_function(self, node: FunctionDefNode) -> AIRFunction:
        self.current_insns = []
        self.defer_stack = []
        self.temp_types = {}
        params = [p.name for p in node.params]
        param_types = [(getattr(p, "type_name", None) or "i64") for p in node.params]
        self.var_types = {p.name: (getattr(p, "type_name", None) or "i64") for p in node.params}
        if self.current_class:
            self.var_types["self"] = self.current_class

        for stmt in node.body.statements:
            self.lower_statement(stmt)

        # Implicit return if last instruction isn't return
        if not self.current_insns or not isinstance(self.current_insns[-1], AIRReturn):
            self.emit_defer_unwinds()
            self.current_insns.append(AIRReturn(None))

        return AIRFunction(
            name=node.name,
            params=params,
            return_type=node.return_type,
            instructions=self.current_insns,
            is_pub=node.is_pub,
            is_static=node.is_static,
            param_types=param_types,
            var_types=dict(self.var_types)
        )

    def lower_class(self, node: ClassDefNode) -> AIRClass:
        self.current_class = node.name
        fields = {f.name: f.type_name for f in node.fields}
        cls = AIRClass(name=node.name, base_class=node.base_class, fields=fields)

        # Constructors
        all_ctors = node.constructors if getattr(node, "constructors", None) else ([node.constructor] if node.constructor else [])
        for ctor in all_ctors:
            self.current_insns = []
            self.defer_stack = []
            self.temp_types = {}
            params = ["self"] + [p.name for p in ctor.params]
            param_types = ["self"] + [(getattr(p, "type_name", None) or "i64") for p in ctor.params]
            self.var_types = {"self": node.name}
            self.var_types.update({p.name: (getattr(p, "type_name", None) or "i64") for p in ctor.params})
            for stmt in ctor.body.statements:
                self.lower_statement(stmt)
            self.emit_defer_unwinds()
            self.current_insns.append(AIRReturn(None))
            fn_name = getattr(ctor, "mangled_name", None) or (
                f"Arx_{node.name}_init_{ctor.variant}" if ctor.variant else f"Arx_{node.name}_init"
            )
            air_ctor = AIRFunction(fn_name, params, "void", self.current_insns, param_types=param_types, var_types=dict(self.var_types))
            cls.constructors[fn_name] = air_ctor
            if cls.constructor is None and (ctor.variant is None):
                cls.constructor = air_ctor

        # Destructor
        if node.destructor:
            self.current_insns = []
            self.defer_stack = []
            self.temp_types = {}
            self.var_types = {"self": node.name}
            for stmt in node.destructor.body.statements:
                self.lower_statement(stmt)
            self.emit_defer_unwinds()
            self.current_insns.append(AIRReturn(None))
            cls.destructor = AIRFunction(f"Arx_{node.name}_drop", ["self"], "void", self.current_insns, param_types=["self"], var_types=dict(self.var_types))

        # Methods
        for m in node.methods:
            fn = self.lower_function(m)
            fn.params = ["self"] + fn.params
            fn.param_types = ["self"] + fn.param_types
            m_key = getattr(m, "mangled_name", None) or m.name
            fn.name = m_key
            cls.methods[m_key] = fn

        # Properties (Phase 11)
        for prop in getattr(node, "properties", []):
            if prop.getter_body:
                self.current_insns = []
                self.defer_stack = []
                self.temp_types = {}
                self.var_types = {"self": node.name}
                for stmt in prop.getter_body.statements:
                    self.lower_statement(stmt)
                if not self.current_insns or not isinstance(self.current_insns[-1], AIRReturn):
                    self.emit_defer_unwinds()
                    self.current_insns.append(AIRReturn(None))
                g_sym = f"Arx_{node.name}_get_{prop.name}"
                cls.methods[f"get_{prop.name}"] = AIRFunction(
                    name=g_sym,
                    params=["self"],
                    return_type=prop.type_name,
                    instructions=self.current_insns,
                    param_types=["self"],
                    var_types=dict(self.var_types)
                )
            if prop.setter_body:
                self.current_insns = []
                self.defer_stack = []
                self.temp_types = {}
                s_param = prop.setter_param or "val"
                self.var_types = {"self": node.name, s_param: prop.type_name}
                for stmt in prop.setter_body.statements:
                    self.lower_statement(stmt)
                if not self.current_insns or not isinstance(self.current_insns[-1], AIRReturn):
                    self.emit_defer_unwinds()
                    self.current_insns.append(AIRReturn(None))
                s_sym = f"Arx_{node.name}_set_{prop.name}"
                cls.methods[f"set_{prop.name}"] = AIRFunction(
                    name=s_sym,
                    params=["self", s_param],
                    return_type="void",
                    instructions=self.current_insns,
                    param_types=["self", prop.type_name],
                    var_types=dict(self.var_types)
                )

        # Operators (Phase 11)
        for op in getattr(node, "operators", []):
            op_method = OPERATOR_METHOD_NAMES.get(op.op, f"op_{op.op}")
            self.current_insns = []
            self.defer_stack = []
            self.temp_types = {}
            p_name = op.params[0].name if op.params else "other"
            p_type = op.params[0].type_name if op.params else "i64"
            self.var_types = {"self": node.name, p_name: p_type}
            for stmt in op.body.statements:
                self.lower_statement(stmt)
            if not self.current_insns or not isinstance(self.current_insns[-1], AIRReturn):
                self.emit_defer_unwinds()
                self.current_insns.append(AIRReturn(None))
            op_sym = op.mangled_name or f"Arx_{node.name}_{op_method}"
            cls.methods[op_method] = AIRFunction(
                name=op_sym,
                params=["self", p_name],
                return_type=op.return_type,
                instructions=self.current_insns,
                param_types=["self", p_type],
                var_types=dict(self.var_types)
            )

        self.current_class = None
        return cls

    def emit_defer_unwinds(self) -> None:
        """Unrolls all active defers in reverse order (LIFO)."""
        for cleanup in reversed(self.defer_stack):
            self.current_insns.extend(cleanup)

    def lower_statement(self, stmt: ASTNode) -> None:
        if isinstance(stmt, VarDeclNode):
            if stmt.initializer:
                val_temp = self.lower_expression(stmt.initializer)
                self.current_insns.append(AIRStore(stmt.name, val_temp))
                if stmt.type_annotation:
                    self.var_types[stmt.name] = stmt.type_annotation
                elif val_temp in self.temp_types:
                    self.var_types[stmt.name] = self.temp_types[val_temp]
        elif isinstance(stmt, AssignNode):
            val_temp = self.lower_expression(stmt.value)
            if getattr(stmt, "is_property_assign", False):
                obj = stmt.target.object_expr
                if isinstance(obj, IdentifierNode):
                    inst_temp = obj.name
                    cls_name = self.current_class if obj.name == "self" else self.var_types.get(obj.name)
                else:
                    inst_temp = self.lower_expression(obj)
                    cls_name = self.temp_types.get(inst_temp)
                self.current_insns.append(AIRCallMethod(
                    dest=None,
                    class_name=cls_name or "",
                    method_name=f"set_{stmt.target.member}",
                    instance=inst_temp,
                    args=[val_temp]
                ))
            elif isinstance(stmt.target, IdentifierNode):
                if stmt.op == "=":
                    self.current_insns.append(AIRStore(stmt.target.name, val_temp))
                else:
                    # Target op= value -> temp = target op value; store
                    op = stmt.op[:-1] # strip '='
                    curr_temp = self.new_temp()
                    self.current_insns.append(AIRLoad(curr_temp, stmt.target.name))
                    res_temp = self.new_temp()
                    self.current_insns.append(AIRBinOp(res_temp, op, curr_temp, val_temp))
                    self.current_insns.append(AIRStore(stmt.target.name, res_temp))
            elif isinstance(stmt.target, MemberAccessNode):
                obj = stmt.target.object_expr
                if isinstance(obj, IdentifierNode):
                    inst_temp = obj.name
                    cls_name = self.current_class if obj.name == "self" else self.var_types.get(obj.name)
                else:
                    inst_temp = self.lower_expression(obj)
                    cls_name = self.temp_types.get(inst_temp)

                if stmt.op == "=":
                    self.current_insns.append(AIRSetField(inst_temp, stmt.target.member, val_temp))
                else:
                    op = stmt.op[:-1]
                    curr_val = self.new_temp()
                    field_t = "i64"
                    if cls_name and cls_name in self.class_fields and stmt.target.member in self.class_fields[cls_name]:
                        field_t = self.class_fields[cls_name][stmt.target.member]
                    else:
                        for cf in self.class_fields.values():
                            if stmt.target.member in cf:
                                field_t = cf[stmt.target.member]
                                break
                    self.temp_types[curr_val] = field_t
                    self.current_insns.append(AIRGetField(curr_val, inst_temp, stmt.target.member))
                    res_val = self.new_temp()
                    self.temp_types[res_val] = field_t
                    self.current_insns.append(AIRBinOp(res_val, op, curr_val, val_temp))
                    self.current_insns.append(AIRSetField(inst_temp, stmt.target.member, res_val))
        elif isinstance(stmt, ReturnNode):
            ret_val = self.lower_expression(stmt.value) if stmt.value else None
            self.emit_defer_unwinds()
            self.current_insns.append(AIRReturn(ret_val))
        elif isinstance(stmt, DeferNode):
            # Record defer cleanup instructions
            old_insns = self.current_insns
            self.current_insns = []
            self.lower_statement(stmt.statement)
            cleanup_insns = self.current_insns
            self.current_insns = old_insns
            self.defer_stack.append(cleanup_insns)
            self.current_insns.append(AIRDeferPush(cleanup_insns))
        elif isinstance(stmt, GuardNode):
            cond_temp = self.lower_expression(stmt.condition)
            guard_ok_lbl = self.new_label("guard_ok")
            self.current_insns.append(AIRBranchIf(cond_temp, guard_ok_lbl))
            for s in stmt.else_block.statements:
                self.lower_statement(s)
            self.current_insns.append(AIRLabel(guard_ok_lbl))
        elif isinstance(stmt, IfNode):

            cond_temp = self.lower_expression(stmt.condition)
            else_lbl = self.new_label("else")
            end_lbl = self.new_label("endif")
            self.current_insns.append(AIRBranchIfNot(cond_temp, else_lbl))
            for s in stmt.then_block.statements:
                self.lower_statement(s)
            self.current_insns.append(AIRJump(end_lbl))
            self.current_insns.append(AIRLabel(else_lbl))
            if stmt.else_block:
                for s in stmt.else_block.statements:
                    self.lower_statement(s)
            self.current_insns.append(AIRLabel(end_lbl))
        elif isinstance(stmt, WhileNode):
            loop_lbl = self.new_label("while_start")
            end_lbl = self.new_label("while_end")
            self.current_insns.append(AIRLabel(loop_lbl))
            cond_temp = self.lower_expression(stmt.condition)
            self.current_insns.append(AIRBranchIfNot(cond_temp, end_lbl))
            for s in stmt.body.statements:
                self.lower_statement(s)
            self.current_insns.append(AIRJump(loop_lbl))
            self.current_insns.append(AIRLabel(end_lbl))
        elif isinstance(stmt, ForNode):
            # For i in start..end
            start_temp = self.lower_expression(stmt.range_expr.start)
            end_temp = self.lower_expression(stmt.range_expr.end)
            self.current_insns.append(AIRStore(stmt.var_name, start_temp))
            loop_lbl = self.new_label("for_start")
            end_lbl = self.new_label("for_end")
            self.current_insns.append(AIRLabel(loop_lbl))
            
            # Check condition (i < end or i <= end)
            cmp_op = "<=" if stmt.range_expr.is_inclusive else "<"
            cur_i = self.new_temp()
            self.current_insns.append(AIRLoad(cur_i, stmt.var_name))
            cond_temp = self.new_temp()
            self.current_insns.append(AIRBinOp(cond_temp, cmp_op, cur_i, end_temp))
            self.current_insns.append(AIRBranchIfNot(cond_temp, end_lbl))
            
            for s in stmt.body.statements:
                self.lower_statement(s)
                
            # Increment: i += 1
            one_temp = self.new_temp()
            self.current_insns.append(AIRConst(one_temp, 1, "i64"))
            nxt_i = self.new_temp()
            self.current_insns.append(AIRBinOp(nxt_i, "+", cur_i, one_temp))
            self.current_insns.append(AIRStore(stmt.var_name, nxt_i))
            self.current_insns.append(AIRJump(loop_lbl))
            self.current_insns.append(AIRLabel(end_lbl))
        elif isinstance(stmt, ExprStmtNode):
            self.lower_expression(stmt.expr, is_statement=True)
        elif isinstance(stmt, MatchNode):
            target_temp = self.lower_expression(stmt.expr)
            match_end_lbl = self.new_label("match_end")
            is_enum = getattr(stmt, "is_enum_match", False)

            for case in stmt.cases:
                case_next_lbl = self.new_label("case_next")
                pat = case.pattern
                if isinstance(pat, IdentifierNode) and pat.name == "_":
                    for s in case.body.statements:
                        self.lower_statement(s)
                    self.current_insns.append(AIRJump(match_end_lbl))
                    self.current_insns.append(AIRLabel(case_next_lbl))
                    continue

                if is_enum or hasattr(case, "resolved_tag"):
                    tag_temp = self.new_temp()
                    self.temp_types[tag_temp] = "i64"
                    self.current_insns.append(AIRGetField(tag_temp, target_temp, "tag"))
                    const_tag = self.new_temp()
                    self.temp_types[const_tag] = "i64"
                    self.current_insns.append(AIRConst(const_tag, case.resolved_tag, "i64"))
                    cmp_temp = self.new_temp()
                    self.temp_types[cmp_temp] = "bool"
                    self.current_insns.append(AIRBinOp(cmp_temp, "==", tag_temp, const_tag))
                    self.current_insns.append(AIRBranchIfNot(cmp_temp, case_next_lbl))

                    if isinstance(pat, CallNode) and pat.args and hasattr(case, "field_names"):
                        for arg, f_name, f_type in zip(pat.args, case.field_names, case.field_types):
                            if isinstance(arg, IdentifierNode):
                                p_temp = self.new_temp()
                                self.temp_types[p_temp] = f_type
                                self.var_types[arg.name] = f_type
                                self.current_insns.append(AIRGetPayloadField(p_temp, target_temp, case.variant_name, f_name))
                                self.current_insns.append(AIRStore(arg.name, p_temp))

                    if case.guard_expr:
                        g_temp = self.lower_expression(case.guard_expr)
                        self.current_insns.append(AIRBranchIfNot(g_temp, case_next_lbl))

                    for s in case.body.statements:
                        self.lower_statement(s)
                    self.current_insns.append(AIRJump(match_end_lbl))
                    self.current_insns.append(AIRLabel(case_next_lbl))
                else:
                    pat_temp = self.lower_expression(pat)
                    cmp_temp = self.new_temp()
                    self.temp_types[cmp_temp] = "bool"
                    self.current_insns.append(AIRBinOp(cmp_temp, "==", target_temp, pat_temp))
                    self.current_insns.append(AIRBranchIfNot(cmp_temp, case_next_lbl))

                    if case.guard_expr:
                        g_temp = self.lower_expression(case.guard_expr)
                        self.current_insns.append(AIRBranchIfNot(g_temp, case_next_lbl))

                    for s in case.body.statements:
                        self.lower_statement(s)
                    self.current_insns.append(AIRJump(match_end_lbl))
                    self.current_insns.append(AIRLabel(case_next_lbl))

            self.current_insns.append(AIRLabel(match_end_lbl))


    def lower_expression(self, expr: ASTNode, is_statement: bool = False) -> Optional[str]:
        if getattr(expr, "is_enum_variant", False):
            dest = self.new_temp()
            self.temp_types[dest] = getattr(expr, "enum_name", "Enum")
            self.current_insns.append(AIRCall(dest, getattr(expr, "resolved_mangled_name", "enum_variant"), []))
            return dest

        if getattr(expr, "is_enum_constructor", False) and isinstance(expr, CallNode):
            arg_temps = [self.lower_expression(a) for a in expr.args]
            dest = self.new_temp()
            self.temp_types[dest] = getattr(expr, "enum_name", "Enum")
            self.current_insns.append(AIRCall(dest, getattr(expr, "resolved_mangled_name", "enum_ctor"), arg_temps))
            return dest

        if isinstance(expr, LiteralNode):

            dest = self.new_temp()
            self.temp_types[dest] = expr.type_name
            self.current_insns.append(AIRConst(dest, expr.value, expr.type_name))
            return dest
        elif isinstance(expr, IdentifierNode):
            dest = self.new_temp()
            if expr.name in self.var_types:
                self.temp_types[dest] = self.var_types[expr.name]
            self.current_insns.append(AIRLoad(dest, expr.name))
            return dest
        elif isinstance(expr, BinaryOpNode):
            if getattr(expr, "is_operator_overload", False):
                left_t = self.lower_expression(expr.left)
                right_t = self.lower_expression(expr.right)
                cls_name = self.var_types.get(left_t, self.temp_types.get(left_t))
                dest = self.new_temp()
                ret_t = getattr(expr, "return_type_name", "i64")
                self.temp_types[dest] = ret_t
                self.current_insns.append(AIRCallMethod(dest=dest, class_name=cls_name or "", method_name=expr.op_method_name, instance=left_t, args=[right_t]))
                return dest
            left_t = self.lower_expression(expr.left)
            right_t = self.lower_expression(expr.right)
            dest = self.new_temp()
            l_type = self.temp_types.get(left_t, "i64")
            r_type = self.temp_types.get(right_t, "i64")
            if expr.op in ("<", "<=", ">", ">=", "==", "!=", "&&", "||"):
                self.temp_types[dest] = "bool"
            elif l_type in ("f32", "f64") or r_type in ("f32", "f64"):
                self.temp_types[dest] = "f64"
            else:
                self.temp_types[dest] = "i64"
            self.current_insns.append(AIRBinOp(dest, expr.op, left_t, right_t))
            return dest
        elif isinstance(expr, CastNode):
            src_t = self.lower_expression(expr.expr)
            dest = self.new_temp()
            src_type = getattr(expr, "src_type", None) or self.temp_types.get(src_t)
            if not src_type:
                if isinstance(expr.expr, IdentifierNode):
                    src_type = self.var_types.get(expr.expr.name, "unknown")
                elif isinstance(expr.expr, LiteralNode):
                    src_type = expr.expr.type_name
                else:
                    src_type = "unknown"
            self.temp_types[dest] = expr.target_type
            self.current_insns.append(AIRCast(dest, src_t, expr.target_type, src_type))
            return dest
        elif isinstance(expr, UnaryOpNode):
            op_t = self.lower_expression(expr.operand)
            dest = self.new_temp()
            self.temp_types[dest] = self.temp_types.get(op_t, "i64")
            self.current_insns.append(AIRUnaryOp(dest, expr.op, op_t))
            return dest
        elif isinstance(expr, CallNode):
            arg_temps = [self.lower_expression(a) for a in expr.args]
            dest = None if is_statement else self.new_temp()
            if isinstance(expr.callee, IdentifierNode):
                fn_name = expr.callee.name
                if fn_name == "typeof":
                    dest = self.new_temp()
                    arg_type_name = getattr(expr, "inferred_type", None)
                    if not arg_type_name and expr.args:
                        arg = expr.args[0]
                        if isinstance(arg, IdentifierNode):
                            arg_type_name = self.var_types.get(arg.name)
                        elif isinstance(arg, LiteralNode):
                            arg_type_name = arg.type_name
                    if not arg_type_name and arg_temps:
                        arg_type_name = self.temp_types.get(arg_temps[0])
                    if not arg_type_name:
                        arg_type_name = "unknown"
                    self.temp_types[dest] = "str"
                    self.current_insns.append(AIRConst(dest, arg_type_name, "str"))
                    return dest
                elif fn_name in self.classes:
                    dest = self.new_temp()
                    self.temp_types[dest] = fn_name
                    ctor_target = getattr(expr, "resolved_mangled_name", None) or f"Arx_{fn_name}_init"
                    self.current_insns.append(AIRCallConstructor(dest, fn_name, arg_temps, ctor_target))
                elif fn_name in ("input", "readln"):
                    target_t = getattr(expr, "target_type", "str") or "str"
                    if target_t in ("i8", "i16", "i32", "i64", "int"):
                        c_call_name = f"arx_{fn_name}_int"
                        temp_t = target_t
                    elif target_t in ("u8", "u16", "u32", "u64", "uint"):
                        c_call_name = f"arx_{fn_name}_uint"
                        temp_t = target_t
                    elif target_t in ("f32", "f64", "float"):
                        c_call_name = f"arx_{fn_name}_float"
                        temp_t = target_t
                    elif target_t == "bool":
                        c_call_name = f"arx_{fn_name}_bool"
                        temp_t = "bool"
                    elif target_t == "char":
                        c_call_name = f"arx_{fn_name}_char"
                        temp_t = "char"
                    else:
                        c_call_name = f"arx_{fn_name}"
                        temp_t = "str"
                    if dest:
                        self.temp_types[dest] = temp_t
                    self.current_insns.append(AIRCall(dest, c_call_name, arg_temps))
                else:
                    if fn_name == "sleep_ms":
                        fn_name = "arx_sleep_ms"
                    if dest:
                        if fn_name in self.function_return_types:
                            self.temp_types[dest] = self.function_return_types[fn_name]
                        elif fn_name == "arx_time_now":
                            self.temp_types[dest] = "f64"
                        elif fn_name in ("arx_channel_new", "arx_channel_recv"):
                            self.temp_types[dest] = "i64"
                    self.current_insns.append(AIRCall(dest, fn_name, arg_temps))
            elif isinstance(expr.callee, MemberAccessNode):
                obj = expr.callee.object_expr
                if isinstance(obj, IdentifierNode):
                    inst_temp = obj.name
                    cls_name = self.current_class if obj.name == "self" else self.var_types.get(obj.name, "Class")
                else:
                    inst_temp = self.lower_expression(obj)
                    cls_name = self.temp_types.get(inst_temp, "Class")
                method_target = getattr(expr, "resolved_mangled_name", None) or getattr(expr.callee, "resolved_mangled_name", None) or expr.callee.member
                if dest and cls_name in self.class_method_returns:
                    m_returns = self.class_method_returns[cls_name]
                    ret_t = m_returns.get(method_target, m_returns.get(expr.callee.member))
                    if ret_t:
                        self.temp_types[dest] = ret_t
                self.current_insns.append(AIRCallMethod(dest, cls_name or "Class", method_target, inst_temp, arg_temps))
            return dest
        elif isinstance(expr, PipelineNode):
            # Pipeline: left |> right(args)
            left_temp = self.lower_expression(expr.left)
            call_args = [left_temp] + [self.lower_expression(a) for a in expr.right.args]
            dest = self.new_temp()
            fn_name = expr.right.callee.name if isinstance(expr.right.callee, IdentifierNode) else "unknown"
            if fn_name in self.function_return_types:
                self.temp_types[dest] = self.function_return_types[fn_name]
            self.current_insns.append(AIRCall(dest, fn_name, call_args))
            return dest
        elif isinstance(expr, CascadeNode):
            if isinstance(expr.target, IdentifierNode):
                inst_temp = expr.target.name
                cls_name = self.current_class if expr.target.name == "self" else self.var_types.get(expr.target.name, "Class")
            else:
                inst_temp = self.lower_expression(expr.target)
                cls_name = self.temp_types.get(inst_temp, "Class")

            arg_temps = [self.lower_expression(a) for a in expr.call.args]
            method_name = ""
            if isinstance(expr.call.callee, IdentifierNode):
                method_name = expr.call.callee.name
            elif isinstance(expr.call.callee, MemberAccessNode):
                method_name = expr.call.callee.member

            method_target = getattr(expr.call, "resolved_mangled_name", None) or method_name
            self.current_insns.append(AIRCallMethod(
                dest=None,
                class_name=cls_name or "Class",
                method_name=method_target,
                instance=inst_temp,
                args=arg_temps
            ))
            return inst_temp
        elif isinstance(expr, MemberAccessNode):

            obj = expr.object_expr
            if isinstance(obj, IdentifierNode):
                inst_temp = obj.name
                cls_name = self.current_class if obj.name == "self" else self.var_types.get(obj.name)
            else:
                inst_temp = self.lower_expression(obj)
                cls_name = self.temp_types.get(inst_temp)
            dest = self.new_temp()
            if getattr(expr, "is_property", False):
                p_type = getattr(expr, "prop_type", "i64")
                self.temp_types[dest] = p_type
                self.current_insns.append(AIRCallMethod(dest, cls_name or "", f"get_{expr.member}", inst_temp, []))
                return dest
            # Determine field type
            field_t = "i64"
            if cls_name and cls_name in self.class_fields and expr.member in self.class_fields[cls_name]:
                field_t = self.class_fields[cls_name][expr.member]
            else:
                for cf in self.class_fields.values():
                    if expr.member in cf:
                        field_t = cf[expr.member]
                        break
            self.temp_types[dest] = field_t
            self.current_insns.append(AIRGetField(dest, inst_temp, expr.member))
            return dest
        elif isinstance(expr, NewNode):
            arg_temps = [self.lower_expression(a) for a in expr.args]
            dest = self.new_temp()
            self.current_insns.append(AIRCall(dest, f"new_{expr.class_name}", arg_temps))
            return dest
        elif isinstance(expr, SpawnNode):
            arg_temps = [self.lower_expression(a) for a in expr.call.args]
            dest = self.new_temp()
            self.temp_types[dest] = "i64"
            fn_name = expr.call.callee.name if isinstance(expr.call.callee, IdentifierNode) else "unknown"
            self.current_insns.append(AIRSpawn(dest, fn_name, arg_temps))
            return dest
        elif isinstance(expr, StringInterpNode):
            fmt_pieces = []
            arg_temps = []
            for part in expr.parts:
                if isinstance(part, ASTNode):
                    t = self.lower_expression(part)
                    arg_temps.append(t)
                    t_type = self.temp_types.get(t, "i64")
                    if t_type == "str":
                        fmt_pieces.append("%s")
                    elif t_type in ("f32", "f64"):
                        fmt_pieces.append("%g")
                    elif t_type == "bool":
                        fmt_pieces.append("%s")
                    else:
                        fmt_pieces.append("%lld")
                else:
                    escaped = str(part).replace("%", "%%")
                    fmt_pieces.append(escaped)
            dest = self.new_temp()
            fmt_str = "".join(fmt_pieces)
            self.temp_types[dest] = "str"
            self.current_insns.append(AIRFormatString(dest, fmt_str, arg_temps))
            return dest

        dest = self.new_temp()
        self.current_insns.append(AIRConst(dest, 0, "i64"))
        return dest
