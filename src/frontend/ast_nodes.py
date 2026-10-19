"""
Aerix Compiler (arxc) — Abstract Syntax Tree (AST) Node Hierarchy
Represents typed syntax trees for expressions, statements, functions, and OOP classes.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Set, Tuple


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


@dataclass
class LoopNode(ASTNode):
    body: BlockNode



@dataclass
class BreakNode(ASTNode):
    pass


@dataclass
class ContinueNode(ASTNode):
    pass


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
class CIncludeNode(ASTNode):
    header: str


@dataclass
class CExternNode(ASTNode):
    func_def: FunctionDefNode


@dataclass
class ProgramNode(ASTNode):
    declarations: List[ASTNode] = field(default_factory=list)
    generic_uses: Set[Tuple[str, Tuple[str, ...]]] = field(default_factory=set)
