"""
Aerix Compiler (arxc) — Abstract Syntax Tree (AST) Node Hierarchy
Represents typed syntax trees for expressions, statements, functions, and OOP classes.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Set, Tuple, Union


@dataclass
class ASTNode:
    """Base class for all AST nodes with source coordinates."""
    line: int
    col: int


# ==========================================
# Expressions
# ==========================================

@dataclass
class LiteralNode(ASTNode):
    value: Any
    type_name: str  # "i64", "f64", "str", "bool", "char", "null"


@dataclass
class IdentifierNode(ASTNode):
    name: str


@dataclass
class BinaryOpNode(ASTNode):
    left: ASTNode
    op: str
    right: ASTNode


@dataclass
class UnaryOpNode(ASTNode):
    op: str
    operand: ASTNode


@dataclass
class CallNode(ASTNode):
    callee: ASTNode
    args: List[ASTNode] = field(default_factory=list)
    resolved_mangled_name: Optional[str] = None


@dataclass
class NamedArgNode(ASTNode):
    """Represents a named function argument: name = value"""
    name: str
    value: ASTNode


@dataclass
class MemberAccessNode(ASTNode):
    object_expr: ASTNode
    member: str
    resolved_mangled_name: Optional[str] = None


@dataclass
class IndexAccessNode(ASTNode):
    object_expr: ASTNode
    index: ASTNode


@dataclass
class PipelineNode(ASTNode):
    left: ASTNode
    right: CallNode


@dataclass
class CascadeNode(ASTNode):
    target: ASTNode
    call: CallNode


@dataclass
class RangeNode(ASTNode):
    start: ASTNode
    end: ASTNode
    is_inclusive: bool = False


@dataclass
class NewNode(ASTNode):
    class_name: str
    args: List[ASTNode] = field(default_factory=list)


@dataclass
class CastNode(ASTNode):
    expr: ASTNode
    target_type: str


@dataclass
class StringInterpNode(ASTNode):
    """Represents a string with embedded interpolation expressions."""
    parts: List[Any]  # Mix of raw strings and ASTNodes


@dataclass
class SpawnNode(ASTNode):
    """Represents a concurrent thread/task spawn expression."""
    call: CallNode


@dataclass
class FixedArrayLiteralNode(ASTNode):
    """
    Phase 23 — Represents a fixed-size stack array literal expression.

    Two forms:
      - Explicit list:   [2, 4, 12, 14]         -> elements=[...], repeat_value=None, repeat_count=None
      - Repeat syntax:   [0; 8]                  -> elements=[], repeat_value=LiteralNode(0), repeat_count=8
    """
    elements: List[ASTNode] = field(default_factory=list)
    repeat_value: Optional[ASTNode] = None   # For [val; N] form
    repeat_count: Optional[int] = None        # For [val; N] form — N must be compile-time int
    inferred_elem_type: Optional[str] = None  # Filled in by semantic analysis
    inferred_size: Optional[int] = None       # Filled in by semantic analysis


@dataclass
class SizeofNode(ASTNode):
    """Phase 24: Represents compile-time type byte-size query: sizeof(T)"""
    target_type: str


# ==========================================
# Statements & Blocks
# ==========================================

@dataclass
class BlockNode(ASTNode):
    statements: List[ASTNode] = field(default_factory=list)


@dataclass
class VarDeclNode(ASTNode):
    name: str
    is_mut: bool
    type_annotation: Optional[str]
    initializer: Optional[ASTNode]


@dataclass
class AssignNode(ASTNode):
    target: ASTNode
    op: str
    value: ASTNode


@dataclass
class IfNode(ASTNode):
    condition: ASTNode
    then_block: BlockNode
    else_block: Optional[BlockNode] = None


@dataclass
class GuardNode(ASTNode):
    condition: ASTNode
    else_block: BlockNode


@dataclass
class WhileNode(ASTNode):
    condition: ASTNode
    body: BlockNode
    label: Optional[str] = None


@dataclass
class TryCatchNode(ASTNode):
    try_block: BlockNode
    catch_var: Optional[str] = None
    catch_block: Optional[BlockNode] = None
    finally_block: Optional[BlockNode] = None


@dataclass
class ThrowNode(ASTNode):
    expr: ASTNode


@dataclass
class TupleNode(ASTNode):
    """Represents an anonymous tuple literal: (a, b, c)."""
    elements: List[ASTNode] = field(default_factory=list)


@dataclass
class TupleDestructureNode(ASTNode):
    """Represents a tuple destructuring assignment: let (a, b) = tup."""
    names: List[str] = field(default_factory=list)
    is_mut: bool = False
    initializer: Optional[ASTNode] = None


@dataclass
class ForNode(ASTNode):
    var_name: str
    range_expr: ASTNode
    body: BlockNode
    index_var_name: Optional[str] = None
    label: Optional[str] = None


@dataclass
class LoopNode(ASTNode):
    body: BlockNode
    label: Optional[str] = None


@dataclass
class BreakNode(ASTNode):
    label: Optional[str] = None


@dataclass
class ContinueNode(ASTNode):
    label: Optional[str] = None


@dataclass
class MatchCaseNode(ASTNode):
    pattern: ASTNode
    body: BlockNode
    guard_expr: Optional[ASTNode] = None


@dataclass
class MatchNode(ASTNode):
    expr: ASTNode
    cases: List[MatchCaseNode] = field(default_factory=list)



@dataclass
class ReturnNode(ASTNode):
    value: Optional[ASTNode] = None


@dataclass
class DeferNode(ASTNode):
    statement: ASTNode


@dataclass
class ExprStmtNode(ASTNode):
    expr: ASTNode


# ==========================================
# Declarations (Functions, OOP Classes, Traits, C Interop)
# ==========================================

@dataclass
class ParamNode(ASTNode):
    name: str
    type_name: str
    default_val: Optional[ASTNode] = None


@dataclass
class FunctionDefNode(ASTNode):
    name: str
    params: List[ParamNode]
    return_type: str
    body: BlockNode
    is_pub: bool = True
    is_static: bool = False
    is_virtual: bool = False
    is_override: bool = False
    mangled_name: Optional[str] = None
    type_params: List[str] = field(default_factory=list)


@dataclass
class ClassFieldNode(ASTNode):
    name: str
    type_name: str
    default_val: Optional[ASTNode] = None
    is_pub: bool = False
    is_static: bool = False


@dataclass
class ConstructorDefNode(ASTNode):
    params: List[ParamNode]
    body: BlockNode
    variant: Optional[str] = None
    mangled_name: Optional[str] = None


@dataclass
class DestructorDefNode(ASTNode):
    body: BlockNode


@dataclass
class PropertyDefNode(ASTNode):
    name: str
    type_name: str
    getter_body: Optional[BlockNode] = None
    setter_param: Optional[str] = None
    setter_body: Optional[BlockNode] = None
    is_pub: bool = True
    is_static: bool = False


@dataclass
class OperatorDefNode(ASTNode):
    op: str
    params: List[ParamNode]
    return_type: str
    body: BlockNode
    is_pub: bool = True


@dataclass
class ClassDefNode(ASTNode):
    name: str
    base_class: Optional[str] = None
    traits: List[str] = field(default_factory=list)
    fields: List[ClassFieldNode] = field(default_factory=list)
    methods: List[FunctionDefNode] = field(default_factory=list)
    constructor: Optional[ConstructorDefNode] = None
    destructor: Optional[DestructorDefNode] = None
    constructors: List[ConstructorDefNode] = field(default_factory=list)
    properties: List[PropertyDefNode] = field(default_factory=list)
    operators: List[OperatorDefNode] = field(default_factory=list)
    type_params: List[str] = field(default_factory=list)
    is_packed: bool = False
    alignment: Optional[int] = None


    def __post_init__(self):
        if self.constructor and not self.constructors:
            self.constructors.append(self.constructor)
        elif self.constructors and not self.constructor:
            self.constructor = self.constructors[0]


@dataclass
class TraitMethodNode(ASTNode):
    name: str
    params: List[ParamNode]
    return_type: str


@dataclass
class TraitDefNode(ASTNode):
    name: str
    methods: List[TraitMethodNode] = field(default_factory=list)


@dataclass
class ExtendDefNode(ASTNode):
    target_type: str
    methods: List[FunctionDefNode] = field(default_factory=list)


@dataclass
class EnumVariantNode(ASTNode):
    name: str
    fields: List[ParamNode] = field(default_factory=list)
    tag: int = 0


@dataclass
class EnumDefNode(ASTNode):
    name: str
    variants: List[EnumVariantNode] = field(default_factory=list)



@dataclass
class ImportNode(ASTNode):
    """Phase 25: Represents an import statement:
    1. Inbuilt Module: import Math;
    2. Multiple Modules: import Math, Random;
    3. User File: import "./helper.arx";
    4. Selective Module: import { abs, sqrt } from Math;
    5. Selective User File: import { foo, bar } from "./helper.arx";
    """
    module_name: Optional[str] = None
    module_names: List[str] = field(default_factory=list)
    file_path: Optional[str] = None
    symbols: List[str] = field(default_factory=list)
    is_user_file: bool = False


@dataclass
class CIncludeNode(ASTNode):
    header: str


@dataclass
class CExternNode(ASTNode):
    func_def: FunctionDefNode


@dataclass
class LambdaNode(ASTNode):
    """Represents an anonymous lambda / closure: |x, y| expr or |x| { ... }."""
    params: List[ParamNode] = field(default_factory=list)
    body: Optional[ASTNode] = None
    return_type: Optional[str] = None


@dataclass
class ProgramNode(ASTNode):
    declarations: List[ASTNode] = field(default_factory=list)
    generic_uses: Set[Tuple[str, Tuple[str, ...]]] = field(default_factory=set)
