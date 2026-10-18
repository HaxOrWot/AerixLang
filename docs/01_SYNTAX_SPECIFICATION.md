# Aerix (arx) — Complete Syntax & Grammar Specification

> **Version:** 1.0-draft  
> **Target:** Aerix Standard Compiler (`arx`)  
> **Source Extension:** `.arx`

---

## 1. Syntax Design Principles

Aerix syntax is engineered around three pillars:
1. **Low Visual Noise:** No mandatory semicolons, minimal boilerplate, clean punctuation.
2. **Explicitness Where It Matters:** Variables are immutable by default (`let`); mutability must be declared (`mut`).
3. **Dual-Nature Harmony:** A developer can write simple procedural scripts, algorithms, or functional data pipelines, or architect large systems with full-blown Object-Oriented classes, inheritance, and encapsulation.

---

## 1.1 Syntax Quick-Reference Matrix

| Goal | Aerix Syntax | Notes |
| :--- | :--- | :--- |
| **Immutable variable** | `let x = 42` | Cannot be reassigned. Inferred `i64`. |
| **Mutable variable** | `mut count = 0` | Explicit mutability. |
| **Float variable** | `let pi = 3.1415` or `let g: f32 = 9.81` | Default float is `f64`. |
| **Function** | `fn add(a: i32, b: i32) -> i32 { return a + b }` | Explicit return type or void. |
| **Single-expression fn** | `fn square(x: f64) -> f64 => x * x` | Arrow body. |
| **Pipeline chaining** | `let res = 5 \|> double() \|> add_ten()` | Chains function calls left-to-right. |
| **Formatted print** | `println("Score: {score}, Pi: {pi}")` | Automatic string interpolation. |
| **Loop (range)** | `for i in 0..10 { ... }` or `for i in 1..=10 { ... }` | `..` exclusive, `..=` inclusive. |
| **Loop (while / infinite)**| `while cond { ... }` / `loop { ... break }` | Clean control loops. |
| **Conditional** | `if x > 0 { ... } else { ... }` | No parentheses required. |
| **Pattern Match** | `match code { 200 => "OK", _ => "Error" }` | Concise branching. |
| **Class (OOP)** | `class Hero { pub name: str; priv hp: f64 }` | Encapsulated OOP struct. |
| **Constructor** | `init(name: str, hp: f64) { self.name = name }` | Instance initializer. |
| **Destructor (RAII)** | `drop() { println("Hero destroyed") }` | Auto-called on scope exit. |
| **Inheritance** | `class Mage extends Hero { ... }` | Single inheritance. |
| **Trait / Interface** | `trait Drawable { fn draw() }` | Behavior contract. |
| **Resource Cleanup** | `defer file.close()` | LIFO cleanup on function return. |
| **C Interop** | `cinclude "<math.h>"` / `cextern fn sin(x: f64) -> f64`| Zero-cost native C call. |

---

## 2. Lexical Structure

### 2.1 Keywords
```text
// Declarations
fn, let, mut, const, class, trait, enum, struct, type, init, drop

// Control Flow
if, else, match, for, in, while, loop, break, continue, return

// OOP & Modifiers
self, super, pub, priv, prot, static, virtual, override, abstract

// Memory & Safety
defer, unsafe, null, sizeof, as

// Interop & Modules
use, import, cinclude, cextern
```

### 2.2 Operators
* **Arithmetic:** `+`, `-`, `*`, `/`, `%`, `**` (power)
* **Comparison:** `==`, `!=`, `<`, `<=`, `>`, `>=`
* **Logical:** `&&`, `||`, `!`
* **Bitwise:** `&`, `|`, `^`, `~`, `<<`, `>>`
* **Assignment:** `=`, `+=`, `-=`, `*=`, `/=`, `%=`
* **Aerix Special Operators:**
  - `|>` — **Pipeline Operator:** Passes the left-hand result as the first argument to the right-hand function (`x |> f(y)` ≡ `f(x, y)`).
  - `->` — Function return type indicator.
  - `=>` — Lambda / Match arrow / Single-expression body.
  - `..` / `..=` — Half-open and closed range operators (`0..10`, `1..=5`).
  - `??` — Null-coalescing operator (`val ?? fallback`).
  - `?.` — Optional chaining operator.

### 2.3 Comments
```aerix
// Single line comment

/* 
   Multi-line block comment
   Can be nested: /* nested */
*/

/// Documentation comment for functions, classes, and types
```

---

## 3. Types and Variables

### 3.1 Primitive Types
| Aerix Type | C99 Equivalent | Description |
| :--- | :--- | :--- |
| `i8`, `i16`, `i32`, `i64` | `int8_t`, `int16_t`, `int32_t`, `int64_t` | Signed integers |
| `u8`, `u16`, `u32`, `u64` | `uint8_t`, `uint16_t`, `uint32_t`, `uint64_t` | Unsigned integers |
| `int`, `uint` | `int64_t`, `uint64_t` | Default target word-size integers |
| `f32`, `f64` | `float`, `double` | IEEE-754 Floating-point numbers |
| `bool` | `bool` (`stdbool.h`) | `true` or `false` |
| `char` | `char` | 8-bit ASCII / UTF-8 code unit |
| `str` | `const char*` or `AerixString` | Immutable UTF-8 string slice |
| `void` | `void` | Absence of value / unit type |

### 3.2 Variable Declarations (`let` vs `mut`)
In Aerix, variables are **immutable by default**. To allow mutation, use the clean `mut` keyword:

```aerix
// Immutable (compiler error if reassigned)
let name = "Aerix"
let pi: f64 = 3.1415926535

// Mutable
mut counter = 0
counter += 1

// Constants (evaluated at compile time)
const MAX_USERS: i32 = 1000
```

---

## 4. Functions & Procedural Style ("Normal Language")

### 4.1 Function Declaration
Functions use the concise `fn` keyword. Type annotations are straightforward:

```aerix
// Standard function
fn add(a: i32, b: i32) -> i32 {
    return a + b
}

// Single-expression body (concise syntax)
fn multiply(a: i32, b: i32) -> i32 => a * b

// Function with no return (implicitly returns void)
fn log_message(msg: str) {
    println("[LOG]: {msg}")
}
```

### 4.2 Default Parameters
```aerix
fn connect(host: str, port: i32 = 8080, timeout: i32 = 30) -> bool {
    println("Connecting to {host}:{port} with timeout {timeout}s")
    return true
}
```

### 4.3 Pipeline Operator (`|>`)
Aerix features first-class data pipelining, transforming nested calls into a readable linear flow:

```aerix
fn double(x: i32) -> i32 => x * 2
fn add_ten(x: i32) -> i32 => x + 10
fn square(x: i32) -> i32 => x * x

fn main() {
    // Instead of: square(add_ten(double(5)))
    let result = 5 
        |> double() 
        |> add_ten() 
        |> square()

    println("Result: {result}") // Output: 400
}
```

---

## 5. Control Flow

### 5.1 If / Else
`if` conditions do not require parentheses:

```aerix
if score >= 90 {
    println("Grade: A")
} else if score >= 80 {
    println("Grade: B")
} else {
    println("Grade: C")
}

// If as an expression
let status = if is_active { "Active" } else { "Offline" }
```

### 5.2 Loops
Aerix provides three clean looping constructs:

```aerix
// 1. Range-based for loop
for i in 0..5 {
    println("i = {i}") // prints 0, 1, 2, 3, 4
}

// Inclusive range
for i in 1..=5 {
    println("i = {i}") // prints 1, 2, 3, 4, 5
}

// 2. While loop
mut n = 10
while n > 0 {
    n -= 1
}

// 3. Infinite loop with break
loop {
    if should_stop() {
        break
    }
}
```

### 5.3 Pattern Matching (`match`)
```aerix
let code = 200

match code {
    200 => println("OK"),
    404 => println("Not Found"),
    500 => println("Server Error"),
    _   => println("Unknown Status")
}
```

---

## 6. Object-Oriented Programming (OOP)

Aerix supports full-fledged, zero-cost Object-Oriented programming that compiles into optimized C structs, method functions, and virtual tables (vtables).

### 6.1 Class Declaration & Encapsulation
- Fields default to private if not marked `pub`.
- `init(...)` is the constructor.
- `drop()` is the optional destructor (called automatically when leaving scope).
- `self` refers to the current instance.

```aerix
class BankAccount {
    pub owner: str
    priv balance: f64

    // Constructor
    init(owner: str, initial_balance: f64) {
        self.owner = owner
        self.balance = initial_balance
    }

    // Public method
    pub fn deposit(amount: f64) {
        if amount > 0.0 {
            self.balance += amount
            println("Deposited {amount}. New balance: {self.balance}")
        }
    }

    pub fn withdraw(amount: f64) -> bool {
        if amount > 0.0 && self.balance >= amount {
            self.balance -= amount
            return true
        }
        return false
    }

    pub fn get_balance() -> f64 {
        return self.balance
    }

    // Destructor (automatic cleanup)
    drop() {
        println("Closing account for {self.owner}")
    }
}
```

### 6.2 Instantiation and Usage
```aerix
fn main() {
    let account = new BankAccount("Alice", 1000.0)
    account.deposit(250.0)
    
    if account.withdraw(100.0) {
        println("Withdrawal successful! Remaining: {account.get_balance()}")
    }
}
```

### 6.3 Inheritance & Method Overriding
Aerix supports single class inheritance with `extends`:

```aerix
class Entity {
    pub id: i64
    pub x: f64
    pub y: f64

    init(id: i64, x: f64, y: f64) {
        self.id = id
        self.x = x
        self.y = y
    }

    pub virtual fn update(dt: f64) {
        // Base update logic
    }
}

class Player extends Entity {
    pub name: str
    pub health: i32

    init(id: i64, x: f64, y: f64, name: str, health: i32 = 100) {
        super.init(id, x, y)
        self.name = name
        self.health = health
    }

    pub override fn update(dt: f64) {
        self.x += 1.5 * dt
        println("{self.name} moved to x: {self.x}")
    }
}
```

### 6.4 Interfaces / Traits (`trait`)
Traits define behavioral contracts that classes implement:

```aerix
trait Drawable {
    fn draw()
    fn get_layer() -> i32
}

class Circle implements Drawable {
    pub radius: f64

    init(radius: f64) {
        self.radius = radius
    }

    pub fn draw() {
        println("Drawing circle with radius {self.radius}")
    }

    pub fn get_layer() -> i32 {
        return 1
    }
}
```

---

## 7. Memory Model & Resource Management

### 7.1 Scope-Based Cleanup (`defer`)
Inspired by Zig and Go, but compiling directly to zero-overhead C cleanup:

```aerix
fn process_file(filename: str) {
    let f = fopen(filename, "r")
    if f == null {
        return
    }
    defer fclose(f) // Guaranteed to execute whenever this function exits!

    // Read and process file safely...
}
```

### 7.2 Stack vs Heap
- Objects declared as `let a = Point(10, 20)` are **stack allocated** (zero malloc overhead).
- Objects created via `let a = new Point(10, 20)` are **heap allocated**.

---

## 8. C Interoperability (Direct Native FFI)

Because Aerix targets C99, calling C libraries has **zero glue code penalty**:

```aerix
// Direct C Header Inclusion
cinclude "<math.h>"
cinclude "<stdio.h>"

// External C function signature declarations
cextern fn sin(x: f64) -> f64
cextern fn cos(x: f64) -> f64

fn compute_wave(angle: f64) -> f64 {
    return sin(angle) * cos(angle)
}
```

---

## 9. Comprehensive Comparison Table

| Feature | C | Python | C++ | Aerix (`arx`) |
| :--- | :--- | :--- | :--- | :--- |
| **Execution Speed** | Native (Fastest) | Interpreted (Slow) | Native (Fastest) | **Native (Identical to C)** |
| **Syntax Readability** | Low / Verbose | High / Clean | Low / Complex | **High / Modern & Clean** |
| **Type Checking** | Static (Weak) | Dynamic | Static (Heavy) | **Static with Type Inference** |
| **Paradigm** | Procedural | Multi-paradigm | Multi-paradigm | **Dual: Procedural + OOP** |
| **Memory Model** | Manual | Heavy GC | RAII / Complex | **Stack + Scoped RAII + Defer** |
| **Data Pipelines** | None | Limited | Ranges (C++20) | **Native `\|>` Operator** |
| **Direct C Interop** | Native | ctypes/CFFI (slow) | `extern "C"` | **Zero-overhead `cextern`** |

---

## 10. Exhaustive Formal EBNF Grammar

```ebnf
Program              ::= TopLevelElement* EOF ;

TopLevelElement      ::= FunctionDef
                       | ClassDef
                       | TraitDef
                       | GlobalVarDecl
                       | CIncludeDecl
                       | CExternDecl
                       | Statement ;

Type                 ::= PrimitiveType | Identifier | ArrayType | PointerType | OptionalType ;
PrimitiveType        ::= "i8" | "i16" | "i32" | "i64" 
                       | "u8" | "u16" | "u32" | "u64" 
                       | "int" | "uint" 
                       | "f32" | "f64" 
                       | "bool" | "char" | "str" | "void" ;
ArrayType            ::= "[" Type ";" Expression "]" ;
PointerType          ::= ("*" | "&" | "&mut") Type ;
OptionalType         ::= Type "?" ;

FunctionDef          ::= ("pub")? "fn" IDENTIFIER "(" ParameterList? ")" ("->" Type)? (Block | "=>" Expression) ;
ParameterList        ::= Parameter ("," Parameter)* ;
Parameter            ::= IDENTIFIER ":" Type ("=" Expression)? ;

ClassDef             ::= "class" IDENTIFIER ("extends" IDENTIFIER)? ("implements" IdentifierList)? "{" ClassMember* "}" ;
IdentifierList       ::= IDENTIFIER ("," IDENTIFIER)* ;
ClassMember          ::= AccessModifier? (FieldDecl | MethodDef | ConstructorDef | DestructorDef) ;
AccessModifier       ::= "pub" | "priv" | "prot" ;
FieldDecl            ::= ("static")? IDENTIFIER ":" Type ("=" Expression)? (";" | NEWLINE) ;
MethodDef            ::= ("static" | "virtual" | "override")? "fn" IDENTIFIER "(" ParameterList? ")" ("->" Type)? Block ;
ConstructorDef       ::= "init" "(" ParameterList? ")" Block ;
DestructorDef        ::= "drop" "(" ")" Block ;

TraitDef             ::= "trait" IDENTIFIER "{" TraitMethod* "}" ;
TraitMethod          ::= "fn" IDENTIFIER "(" ParameterList? ")" ("->" Type)? (";" | NEWLINE) ;

Block                ::= "{" Statement* "}" ;
Statement            ::= VarDecl
                       | AssignmentStmt
                       | ReturnStmt
                       | DeferStmt
                       | IfStmt
                       | WhileStmt
                       | ForStmt
                       | LoopStmt
                       | MatchStmt
                       | BreakStmt
                       | ContinueStmt
                       | ExpressionStmt ;

VarDecl              ::= ("let" | "mut" | "const") IDENTIFIER (":" Type)? ("=" Expression)? (";" | NEWLINE) ;
AssignmentStmt       ::= PrimaryExpr AssignmentOp Expression (";" | NEWLINE) ;
AssignmentOp         ::= "=" | "+=" | "-=" | "*=" | "/=" | "%=" ;
ReturnStmt           ::= "return" Expression? (";" | NEWLINE) ;
DeferStmt            ::= "defer" (Block | Statement) ;

IfStmt               ::= "if" Expression Block ("else" "if" Expression Block)* ("else" Block)? ;
WhileStmt            ::= "while" Expression Block ;
ForStmt              ::= "for" IDENTIFIER "in" RangeExpr Block ;
LoopStmt             ::= "loop" Block ;
BreakStmt            ::= "break" (";" | NEWLINE) ;
ContinueStmt         ::= "continue" (";" | NEWLINE) ;

RangeExpr            ::= Expression (".." | "..=") Expression ;
MatchStmt            ::= "match" Expression "{" MatchArm* "}" ;
MatchArm             ::= MatchPattern "=>" (Block | Expression ",") ;
MatchPattern         ::= Literal | IDENTIFIER | "_" ;

Expression           ::= PipelineExpr ;
PipelineExpr         ::= LogicOrExpr ("|>" CallExpr)* ;
LogicOrExpr          ::= LogicAndExpr ("||" LogicAndExpr)* ;
LogicAndExpr         ::= EqualityExpr ("&&" EqualityExpr)* ;
EqualityExpr         ::= RelationalExpr (("==" | "!=") RelationalExpr)* ;
RelationalExpr       ::= AdditiveExpr (("<" | "<=" | ">" | ">=") AdditiveExpr)* ;
AdditiveExpr         ::= MultiplicativeExpr (("+" | "-") MultiplicativeExpr)* ;
MultiplicativeExpr   ::= PowerExpr (("*" | "/" | "%") PowerExpr)* ;
PowerExpr            ::= UnaryExpr ("**" UnaryExpr)* ;
UnaryExpr            ::= ("!" | "-" | "~" | "&" | "&mut" | "*") UnaryExpr | PostfixExpr ;
PostfixExpr          ::= PrimaryExpr ("." IDENTIFIER | "[" Expression "]" | "(" ArgumentList? ")" | "?")* ;
PrimaryExpr          ::= Literal | IDENTIFIER | "self" | "super" | "(" Expression ")" | "new" CallExpr ;
ArgumentList         ::= Expression ("," Expression)* ;
```

---

## 11. Statement Termination & Newline Splicing

Aerix eliminates mandatory semicolons while avoiding ambiguous parse states:
1. **Implicit Semicolon Rule:** If a line ends with an identifier, literal, closing delimiter (`)`, `]`, `}`), `break`, `continue`, or `return`, the lexer automatically generates a virtual statement boundary.
2. **Line Continuations:** If a line ends with an operator (`+`, `-`, `*`, `|>`, `&&`, `,`), the statement continues naturally to the next line without needing backslashes:
   ```aerix
   let total = price 
       + tax 
       - discount // Perfectly valid multi-line expression
   ```

---

## 12. String Interpolation Lowering

String interpolation expressions inside `"{expr}"` are parsed as nested Aerix expressions at compile time and transformed into type-safe formatted print calls:

```aerix
let name = "Alice"
let age = 30
println("User: {name}, Age in 5 yrs: {age + 5}")
```
*Generated C99 equivalent:*
```c
printf("User: %s, Age in 5 yrs: %lld\n", name, (long long)(age + 5));
```

---

## 13. Scoping, Shadowing & Lifetime Rules

1. **Block Scoping:** Every `{ ... }` creates a new lexical scope.
2. **Variable Shadowing:** Declaring `let x = ...` inside an inner block shadows an outer `x` within that block only. Re-declaring the same variable in the *same* scope is a compile error.
3. **Lifetimes & Drop Order:** Variables are destroyed in strict reverse order of declaration (LIFO) when their enclosing scope exits.

---

## 14. Aerix 2.0 Extended Grammar Specifications

### 14.1 Overloaded Methods & Constructors
Classes permit multiple `fn` and `init` declarations with matching identifiers provided their parameter signatures differ:
```ebnf
MethodDef        ::= Visibility? Modifier* "fn" IDENTIFIER "(" ParameterList? ")" ("->" Type)? (Block | "=>" Expression) ;
ConstructorDef   ::= "init" ("." IDENTIFIER)? "(" ParameterList? ")" Block ;
```

### 14.2 Reactive Properties (`prop`)
Properties define inline get/set accessors with direct variable syntax:
```ebnf
PropertyDef      ::= Visibility? "prop" IDENTIFIER ":" Type "{" PropertyAccessor+ "}" ;
PropertyAccessor ::= ("get" ("=>" Expression | Block)) | ("set" "(" IDENTIFIER ")" Block) ;
```

### 14.3 Operator Overloading (`pub op`)
Overloaded operators use the `op` keyword inside class bodies:
```ebnf
OpOverloadDef    ::= "pub"? "op" OverloadableOp "(" ParameterList? ")" ("->" Type)? (Block | "=>" Expression) ;
OverloadableOp   ::= "+" | "-" | "*" | "/" | "%" | "**" | "==" | "!=" | "<" | "<=" | ">" | ">=" | "[]" | "[]=" ;
```

### 14.4 Type Extensions (`extend`)
External method additions without subclassing:
```ebnf
ExtendDef        ::= "extend" Type "{" FunctionDef* "}" ;
```

### 14.5 Guard Preconditions (`guard ... else`)
Inverted precondition flow control:
```ebnf
GuardStmt        ::= "guard" Expression "else" Block ;
```

### 14.6 Fluent Cascade Mutation (`~>`)
Method chaining threading the invariant instance forward:
```ebnf
CascadeExpr      ::= Expression ("~>" IDENTIFIER "(" ArgumentList? ")")+ ;
```


