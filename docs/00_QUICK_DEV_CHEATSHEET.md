# Aerix (arx) — Developer's Hyper-Optimized Blueprint & Cheatsheet

> **Purpose:** Single-source-of-truth reference for implementing the Aerix compiler.  
> **Target:** Zero guesswork during implementation. Every table, regex, AST node, and C99 mapping is 100% turnkey.

---

## 1. Token Specifications & Regex Matching Table

| Token Type | Regex Pattern | Example | Notes |
| :--- | :--- | :--- | :--- |
| `INT_LITERAL` | `\b(0x[0-9a-fA-F]+|0b[01]+|[0-9]+)\b` | `42`, `0xFF`, `0b1010` | Inferred as `i64` |
| `FLOAT_LITERAL` | `\b[0-9]+\.[0-9]+([eE][+-]?[0-9]+)?\b` | `3.1415`, `1.0e-3` | Inferred as `f64` |
| `STRING_LITERAL`| `\"([^\"\\]|\\.)*\"` | `"Hello {name}!"` | Supports `{expr}` interpolation |
| `CHAR_LITERAL` | `'([^'\\]|\\.)'` | `'A'`, `'\n'` | Single character |
| `IDENTIFIER` | `\b[a-zA-Z_][a-zA-Z0-9_]*\b` | `player_score`, `Vec3` | Excludes reserved keywords |
| `PIPE` | `\|>` | `x \|> f()` | Pipeline operator |
| `ARROW` | `->` | `fn() -> i32` | Return type |
| `FAT_ARROW` | `=>` | `match { 1 => ... }` | Expression body |
| `DOT_DOT_EQ` | `\.\.=` | `1..=10` | Inclusive range |
| `DOT_DOT` | `\.\.` | `0..10` | Exclusive range |
| `QUESTION_QUESTION`| `\?\?` | `val ?? fallback` | Null coalescing |
| `EQ_EQ` | `==` | `a == b` | Equality |
| `NOT_EQ` | `!=` | `a != b` | Inequality |
| `LTE` / `GTE` | `<=` / `>=` | `a <= b` | Comparison |
| `AND_AND` / `OR_OR`| `&&` / `\|\|` | `a && b` | Short-circuit boolean logic |

---

## 2. Pratt Parser Operator Precedence Table

The expression parser uses Top-Down Operator Precedence (Pratt parsing) with binding powers:

| Precedence Enum | Level | Operators | Associativity | Description |
| :--- | :---: | :--- | :---: | :--- |
| `PREC_NONE` | 0 | — | — | Default / Terminator |
| `PREC_ASSIGN` | 1 | `=`, `+=`, `-=`, `*=`, `/=`, `%=` | Right | Assignment |
| `PREC_PIPELINE` | 2 | `\|>` | Left | Data pipeline chaining |
| `PREC_NULL_COALESCE`| 3 | `??` | Left | Null coalescing |
| `PREC_LOGICAL_OR` | 4 | `\|\|` | Left | Logical OR |
| `PREC_LOGICAL_AND`| 5 | `&&` | Left | Logical AND |
| `PREC_EQUALITY` | 6 | `==`, `!=` | Left | Equality comparison |
| `PREC_COMPARISON`| 7 | `<`, `<=`, `>`, `>=` | Left | Relational comparison |
| `PREC_RANGE` | 8 | `..`, `..=` | Left | Range creation |
| `PREC_TERM` | 9 | `+`, `-` | Left | Addition / Subtraction |
| `PREC_FACTOR` | 10 | `*`, `/`, `%` | Left | Multiplication / Division |
| `PREC_POWER` | 11 | `**` | Right | Exponentiation |
| `PREC_UNARY` | 12 | `!`, `-`, `~`, `*`, `&` | Right | Prefix unary |
| `PREC_CALL` | 13 | `()`, `[]`, `.`, `?.` | Left | Function call, indexing, member access |
| `PREC_PRIMARY` | 14 | Literals, Identifiers, Grouping `()` | — | Highest precedence |

---

## 3. Concrete AST Dataclasses (Python Ready)

```python
from dataclasses import dataclass
from typing import List, Optional, Any

@dataclass
class ASTNode:
    line: int
    col: int

# Expressions
@dataclass
class LiteralNode(ASTNode):
    value: Any
    type_name: str # "i64", "f64", "str", "bool"

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
    args: List[ASTNode]

@dataclass
class MemberAccessNode(ASTNode):
    object_expr: ASTNode
    member_name: str

@dataclass
class PipelineNode(ASTNode):
    expr: ASTNode
    call: CallNode

# Statements
@dataclass
class VarDeclNode(ASTNode):
    name: str
    is_mut: bool
    type_annotation: Optional[str]
    initializer: ASTNode

@dataclass
class AssignNode(ASTNode):
    target: ASTNode
    op: str
    value: ASTNode

@dataclass
class IfNode(ASTNode):
    condition: ASTNode
    then_block: "BlockNode"
    else_block: Optional["BlockNode"]

@dataclass
class WhileNode(ASTNode):
    condition: ASTNode
    body: "BlockNode"

@dataclass
class ForNode(ASTNode):
    var_name: str
    range_start: ASTNode
    range_end: ASTNode
    is_inclusive: bool
    body: "BlockNode"

@dataclass
class ReturnNode(ASTNode):
    value: Optional[ASTNode]

@dataclass
class DeferNode(ASTNode):
    statement: ASTNode

@dataclass
class BlockNode(ASTNode):
    statements: List[ASTNode]

# Declarations
@dataclass
class ParamNode:
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

@dataclass
class ClassMemberNode:
    is_pub: bool
    is_static: bool
    member: ASTNode # VarDeclNode, FunctionDefNode, InitNode, DropNode

@dataclass
class ClassDefNode(ASTNode):
    name: str
    base_class: Optional[str]
    traits: List[str]
    members: List[ClassMemberNode]

@dataclass
class ProgramNode(ASTNode):
    declarations: List[ASTNode]
```

---

## 4. Turnkey C99 Codegen Emission Rules

| Aerix Expression | Generated C99 Equivalent |
| :--- | :--- |
| `let x = 42` | `const int64_t x = 42;` |
| `mut count = 0` | `int64_t count = 0;` |
| `let pi = 3.1415` | `const double pi = 3.1415;` |
| `println("Score: {s}")` | `printf("Score: %lld\n", (long long)(s));` |
| `fn add(a: i32, b: i32) -> i32 { return a + b }` | `int32_t arx_add(int32_t a, int32_t b) { return a + b; }` |
| `x \|> f(y)` | `arx_f(x, y);` |
| `class Dog { pub age: i32 }` | `typedef struct Arx_Dog { int32_t age; } Arx_Dog;` |
| `let d = Dog(5)` | `Arx_Dog d; Arx_Dog_init(&d, 5);` |
| `d.bark()` | `Arx_Dog_bark(&d);` |
| `defer cleanup()` | Synthesized before function return / scope exit in reverse order |

---

## 5. Direct Execution Workflow

```bash
# 1. To run any Aerix script:
python arx.py run main.arx

# 2. To compile directly to an optimized native Windows executable:
python arx.py build main.arx -o app.exe

# 3. To view generated C99 code:
python arx.py emit-c main.arx
```
