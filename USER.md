# Aerix (`.arx`) — Technical Specification & Engineering Manual

<div align="center">

```text
       ___         _      
      / _ \___ ___(_)_ __ 
     / __ / -_) __/ /\ \ /
    /_/ |_\__/_/ /_//_\_\ 
```

### **The Definitive A-to-Z Technical Reference Manual**
*Official System Specification for the Aerix Native Programming Language (Version 1.0.84-alpha)*

[![Version](https://img.shields.io/badge/version-1.0.84--alpha-00DCFF.svg?style=for-the-badge)](#)
[![Standard](https://img.shields.io/badge/standard-ANSI%20C99%20%2F%20C11-1E90FF.svg?style=for-the-badge)](#)
[![Architecture](https://img.shields.io/badge/architecture-x86__64%20%2F%20ARM64-00E676.svg?style=for-the-badge)](#)
[![Test Suite](https://img.shields.io/badge/tests-80%2F80%20PASS%20(100%25)-00E5FF.svg?style=for-the-badge)](#)

[Architecture](#1-architectural-specification--compilation-pipeline) • [CLI Reference](#2-cli-toolchain-reference-manual-arx) • [Type System](#3-the-complete-type-system) • [Memory Layout](#4-memory-model--physical-layout) • [Precedence](#6-expressions-operators--precedence) • [OOP System](#9-object-oriented-programming-oop) • [Concurrency](#11-concurrency-native-threads--typed-channels) • [Runtime API](#12-standard-library--runtime-api-aerix_rth) • [EBNF Grammar](#16-formal-language-grammar-ebnf)

</div>

---

## 📑 Master Table of Contents

1. [Architectural Specification & Compilation Pipeline](#1-architectural-specification--compilation-pipeline)
2. [CLI Toolchain Reference Manual (`arx`)](#2-cli-toolchain-reference-manual-arx)
3. [The Complete Type System](#3-the-complete-type-system)
   - 3.1 [Primitive Data Types](#31-primitive-data-types)
   - 3.2 [Hardware SIMD Vector Types (`f32x4`)](#32-hardware-simd-vector-types-f32x4)
   - 3.3 [Unit Type & Null Safety (`void`, `null`, `Type?`)](#33-unit-type--null-safety-void-null-type)
   - 3.4 [Generic Type System (`T`, `K, V`)](#34-generic-type-system-t-k-v)
4. [Memory Model & Physical Layout](#4-memory-model--physical-layout)
   - 4.1 [Deterministic Struct Layout & Packing](#41-deterministic-struct-layout--packing)
   - 4.2 [L1/L2 CPU Cache-Line Density](#42-l1l2-cpu-cache-line-density)
   - 4.3 [Linear Arena Bump Allocator (`LinearArena`)](#43-linear-arena-bump-allocator-lineararena)
   - 4.4 [Deterministic Resource Management (`defer`)](#44-deterministic-resource-management-defer)
5. [Variables, Constants & Mutability](#5-variables-constants--mutability)
6. [Expressions, Operators & Precedence](#6-expressions-operators--precedence)
   - 6.1 [Full Precedence Climbing Matrix](#61-full-precedence-climbing-matrix)
   - 6.2 [The Functional Pipeline Operator (`|>`)](#62-the-functional-pipeline-operator-)
   - 6.3 [The Fluent Cascade Mutation Operator (`~>`)](#63-the-fluent-cascade-mutation-operator-)
   - 6.4 [Null-Coalescing (`??`)](#64-null-coalescing-)
7. [Control Flow Architecture](#7-control-flow-architecture)
   - 7.1 [Conditionals (`if`, `elif`, `else`)](#71-conditionals-if-elif-else)
   - 7.2 [Loops & Iteration (`while`, `for in`, `loop`)](#72-loops--iteration-while-for-in-loop)
   - 7.3 [Fail-Fast Guard Invariants (`guard ... else`)](#73-fail-fast-guard-invariants-guard--else)
   - 7.4 [Tagged Unions & Exhaustive Pattern Matching (`enum`, `match`)](#74-tagged-unions--exhaustive-pattern-matching-enum-match)
8. [Functions, Overloading & Dispatch](#8-functions-overloading--dispatch)
   - 8.1 [Block & Expression Functions (`=>`)](#81-block--expression-functions-)
   - 8.2 [Static Method & Constructor Overloading](#82-static-method--constructor-overloading)
9. [Object-Oriented Programming (OOP)](#9-object-oriented-programming-oop)
   - 9.1 [Class Declarations, Fields & Lifecycle (`init`, `drop`)](#91-class-declarations-fields--lifecycle-init-drop)
   - 9.2 [Inheritance & Virtual Tables (`extends`, `virtual`, `override`)](#92-inheritance--virtual-tables-extends-virtual-override)
   - 9.3 [Abstract Trait Contracts (`trait`, `implements`)](#93-abstract-trait-contracts-trait-implements)
   - 9.4 [Retroactive Type Extensions (`extend <Type>`)](#94-retroactive-type-extensions-extend-type)
   - 9.5 [Reactive Properties (`pub prop`)](#95-reactive-properties-pub-prop)
   - 9.6 [User-Defined Operator Overloading (`pub op`)](#96-user-defined-operator-overloading-pub-op)
10. [Compile-Time Generics & Monomorphization](#10-compile-time-generics--monomorphization)
11. [Concurrency, Native Threads & Typed Channels](#11-concurrency-native-threads--typed-channels)
    - 11.1 [Thread Spawning (`spawn`) & Trampoline Architecture](#111-thread-spawning-spawn--trampoline-architecture)
    - 11.2 [Multi-Argument ArgPacks](#112-multi-argument-argpacks)
    - 11.3 [Thread-Safe Bounded Channels (`Channel<T>`)](#113-thread-safe-bounded-channels-channelt)
    - 11.4 [Synchronization & Joining (`arx_thread_join`)](#114-synchronization--joining-arx_thread_join)
12. [Standard Library & Runtime API (`aerix_rt.h`)](#12-standard-library--runtime-api-aerix_rth)
13. [C Interoperability & Foreign Function Interface (FFI)](#13-c-interoperability--foreign-function-interface-ffi)
14. [Developer Ecosystem & IDE Tooling](#14-developer-ecosystem--ide-tooling)
15. [Production Examples Catalog (26 Programs)](#15-production-examples-catalog-26-programs)
16. [Formal Language Grammar (EBNF)](#16-formal-language-grammar-ebnf)

---

## 1. Architectural Specification & Compilation Pipeline

Aerix operates as an ahead-of-time (AOT) transpiling systems compiler that produces clean, high-performance ANSI C99/C11 code, subsequently compiled into native machine code by GCC or Clang.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       AERIX TRANSFORMATION PIPELINE                         │
├─────────────────┬───────────────────────────────────────────────────────────┤
│ Stage 1: Lexer  │ UTF-8 Stream ──> Token Coordinates (line, col, index)     │
│ Stage 2: Parser │ Tokens ──> Pratt Precedence Climber ──> Concrete AST      │
│ Stage 3: Mono   │ Generic AST ──> Monomorphizer ──> Specialized AST (Box_i64)│
│ Stage 4: Semantic│ Scope Resolution & Type Checking ──> Type-Annotated AST   │
│ Stage 5: AIR    │ AST Lowering ──> Aerix Intermediate Representation (AIR)  │
│ Stage 6: Opt    │ Constant Folding, Dead Code Elimination, Algebraic Simp.  │
│ Stage 7: Codegen│ AIR ──> Formatted C99 Source (Trampolines, Structs, Runtime)│
│ Stage 8: Native │ GCC (-O3 -flto) ──> Standalone Machine Binary (.exe / elf) │
└─────────────────┴───────────────────────────────────────────────────────────┘
```

<details>
<summary><b>🔬 Click to inspect compiler intermediate representations (AST -> AIR -> C99)</b></summary>

<br>

Consider this simple Aerix function:
```aerix
fn square(x: i64) -> i64 => x * x;
```

**1. Emitted AST Node:**
```json
{
  "type": "FunctionDeclaration",
  "name": "square",
  "params": [{"name": "x", "type": "i64"}],
  "return_type": "i64",
  "body": {
    "type": "BinaryExpression",
    "op": "*",
    "left": {"type": "Identifier", "name": "x"},
    "right": {"type": "Identifier", "name": "x"}
  }
}
```

**2. Emitted 3-Address AIR Instructions:**
```
FUNCTION arx_square(x: i64) -> i64:
  t0 = x * x
  RETURN t0
```

**3. Emitted ANSI C99 Machine Code:**
```c
int64_t arx_square(int64_t x) {
    return x * x;
}
```

</details>

---

## 2. CLI Toolchain Reference Manual (`arx`)

The `arx` toolchain is a unified command-line executable distributed as a standalone binary or Python package.

### Synopsis
```bash
arx [COMMAND] [OPTIONS] [FILE]
```

### Subcommands Table

| Subcommand | Description | Common Flags |
| :--- | :--- | :--- |
| `run <file>` | Compiles and executes an Aerix program in-memory. | `--emit-c`, `-v` (verbose) |
| `build <file>` | Compiles program into a standalone native binary executable. | `-o <output>`, `-O3`, `-g`, `--emit-c` |
| `emit-c <file>` | Transpiles Aerix source code directly to formatted C99. | `-o <output.c>` |
| `check <file>` | Runs sub-millisecond syntax and type checking without compiling. | `--json` |
| `repl` | Launches the interactive Aerix Read-Eval-Print-Loop. | `--history` |
| `fmt <file>` | Formats Aerix source code to official formatting standards. | `--check`, `--write` |
| `lint <file>` | Analyzes code for unused variables, dead code, and style issues. | `--strict` |
| `pm <action>` | Aerix Package Manager (install, remove, publish dependencies). | `install`, `update`, `list` |
| `lsp` | Starts the Language Server Protocol (LSP) JSON-RPC daemon. | `--stdio`, `--socket=<port>` |
| `doctor` | Diagnostics tool checking GCC compiler and toolchain health. | `--fix` |
| `setup-tools` | Automated setup wizard installing MinGW-w64 or Clang. | `--backend=gcc` |
| `test` | Runs the full automated regression test suite (80 tests). | `-v`, `--fast` |
| `new <name>` | Scaffolds a new Aerix systems project with standard structure. | `--template=cli` |

---

## 3. The Complete Type System

Aerix is strictly, statically typed with compile-time type checking and zero runtime boxing.

### 3.1 Primitive Data Types

| Type | Bit Width | Signed? | Memory Size | Value Range | C99 Emitted Type |
| :--- | :---: | :---: | :---: | :--- | :--- |
| `i8` | 8 | Yes | 1 Byte | $-128$ to $127$ | `int8_t` |
| `i16` | 16 | Yes | 2 Bytes | $-32,768$ to $32,767$ | `int16_t` |
| `i32` | 32 | Yes | 4 Bytes | $-2,147,483,648$ to $2,147,483,647$ | `int32_t` |
| `i64` | 64 | Yes | 8 Bytes | $-9.22 \times 10^{18}$ to $9.22 \times 10^{18}$ | `int64_t` |
| `int` | 64 | Yes | 8 Bytes | Default signed word (alias for `i64`) | `int64_t` |
| `u8` | 8 | No | 1 Byte | $0$ to $255$ | `uint8_t` |
| `u16` | 16 | No | 2 Bytes | $0$ to $65,535$ | `uint16_t` |
| `u32` | 32 | No | 4 Bytes | $0$ to $4,294,967,295$ | `uint32_t` |
| `u64` | 64 | No | 8 Bytes | $0$ to $1.84 \times 10^{19}$ | `uint64_t` |
| `uint` | 64 | No | 8 Bytes | Default unsigned word (alias for `u64`) | `uint64_t` |
| `usize` | 64 | No | 8 Bytes | Architecture pointer-size unsigned word | `size_t` |
| `isize` | 64 | Yes | 8 Bytes | Architecture pointer-size signed word | `ptrdiff_t` |
| `f32` | 32 | Yes | 4 Bytes | IEEE 754 Single Precision ($\sim 7$ decimals) | `float` |
| `f64` | 64 | Yes | 8 Bytes | IEEE 754 Double Precision ($\sim 16$ decimals)| `double` |
| `float` | 64 | Yes | 8 Bytes | Default float (alias for `f64`) | `double` |
| `bool` | 8 | No | 1 Byte | `true` (1) or `false` (0) | `bool` (`stdbool.h`) |
| `char` | 8 | No | 1 Byte | ASCII character literal (e.g. `'A'`) | `char` |
| `str` | 64 | No | 8 Bytes | Immutable UTF-8 string pointer | `const char*` |

### 3.2 Hardware SIMD Vector Types (`f32x4`)
Aerix supports native hardware SIMD vectors mapping directly to SSE/AVX CPU registers:
- `f32x4`: Packed 128-bit vector holding four 32-bit floats.
- Compiles directly to GCC vector extensions: `typedef float f32x4 __attribute__((vector_size(16)));`.

### 3.3 Unit Type & Null Safety (`void`, `null`, `Type?`)
- `void`: Represents the absence of a value. Functions without return types implicitly return `void`.
- `null`: Null reference literal.
- `Type?`: Optional nullable type (e.g. `str?`, `Person?`). Checked at compile-time to prevent null dereference errors.

### 3.4 Generic Type System (`T`, `K, V`)
Generic type parameters represent compile-time placeholders monomorphized into specialized C structs and functions during compilation.

---

## 4. Memory Model & Physical Layout

Aerix uses deterministic, zero-garbage-collector memory management.

### 4.1 Deterministic Struct Layout & Packing
To eliminate internal memory holes and maximize CPU cache density, Aerix automatically orders class fields in descending alignment order:
`8-Byte (i64, f64, str, pointers) ──> 4-Byte (i32, f32) ──> 2-Byte (i16, u16) ──> 1-Byte (u8, bool, char)`

```aerix
class TelemetryData {
    pub active: bool         // 1 Byte
    pub timestamp_ns: i64    // 8 Bytes
    pub flag: char           // 1 Byte
    pub energy: f64          // 8 Bytes
}
```

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AERIX CACHE-PACKED STRUCT MEMORY MAP                     │
├───────────────┬──────────────┬──────────────┬───────────────────────────────┤
│ Field         │ Type         │ Byte Offset  │ Size & Alignment              │
├───────────────┼──────────────┼──────────────┼───────────────────────────────┤
│ timestamp_ns  │ i64          │ Offset 0     │ 8 Bytes (Aligned to 8B)       │
│ energy        │ f64          │ Offset 8     │ 8 Bytes (Aligned to 8B)       │
│ active        │ bool         │ Offset 16    │ 1 Byte                        │
│ flag          │ char         │ Offset 17    │ 1 Byte                        │
│ _pad          │ char[6]      │ Offset 18    │ 6 Bytes (Tail padding)        │
└───────────────┴──────────────┴──────────────┴───────────────────────────────┘
Total Size: 24 Bytes (Zero internal holes! Aligned to 8 bytes)
```

**Physical C99 Emitted Struct:**
```c
typedef struct Arx_TelemetryData {
    int64_t timestamp_ns; // Offset 0  (8B)
    double energy;        // Offset 8  (8B)
    bool active;          // Offset 16 (1B)
    char flag;            // Offset 17 (1B)
    char _pad[6];         // Offset 18 (6B tail padding)
} Arx_TelemetryData;      // Total: 24 Bytes
```

### 4.2 L1/L2 CPU Cache-Line Density
Every class computes its cache-line occupancy. The standard L1 data cache line is 64 bytes. If `total_size <= 64`, instances reside entirely within a single CPU cache line, guaranteeing $O(1)$ memory cycle access.

### 4.3 Linear Arena Bump Allocator (`LinearArena`)
For ultra-high-throughput simulations, games, and web servers:
```aerix
class LinearArena {
    pub capacity: i64
    pub offset: i64

    init(capacity_bytes: i64) {
        self.capacity = capacity_bytes
        self.offset = 0
    }

    pub fn alloc(size_bytes: i64) -> i64 {
        let aligned = (self.offset + 7) / 8 * 8
        guard aligned + size_bytes <= self.capacity else { return -1 }
        let ptr = aligned
        self.offset = aligned + size_bytes
        return ptr
    }

    pub fn reset() { self.offset = 0 }
}
```

### 4.4 Deterministic Resource Management (`defer`)
The `defer` statement defers statement execution until the enclosing scope exits, executing in strict **Last-In, First-Out (LIFO)** reverse order:
```aerix
fn process_stream() {
    println("1. Opening socket...")
    defer println("4. Socket closed.") // Runs second on exit

    println("2. Acquiring mutex...")
    defer println("3. Mutex unlocked.") // Runs first on exit

    println("Executing payload...")
}
```

---

## 5. Variables, Constants & Mutability

In Aerix, **immutability is the default**. Variables declared with `let` cannot be reassigned once initialized.

```aerix
// 1. Immutable binding
let host: str = "127.0.0.1"
// host = "localhost" // COMPILE ERROR: Cannot reassign immutable variable 'host'

// 2. Mutable variable
let mut counter = 0
counter += 1 // OK

// 3. Shorthand mutability
mut score = 100
score -= 10 // OK

// 4. Compile-time constant
const MAX_PACKET_SIZE: i64 = 65536
```

---

## 6. Expressions, Operators & Precedence

### 6.1 Full Precedence Climbing Matrix

| Precedence | Operators | Associativity | Description |
| :---: | :--- | :---: | :--- |
| **14** | `~>` | Left | Fluent Cascade In-Place Mutation |
| **13** | `.` | Left | Member / Field / Method Access |
| **12** | `()` | Left | Function Call |
| **11** | `[]` | Left | Array Indexing / Subscript |
| **10** | `as` | Left | Explicit Type Cast |
| **9** | `**` | Right | Exponentiation |
| **8** | `-`, `!`, `~` | Right | Unary Negation, Logical NOT, Bitwise NOT |
| **7** | `*`, `/`, `%` | Left | Multiplicative |
| **6** | `+`, `-` | Left | Additive |
| **5** | `..`, `..=` | Left | Exclusive and Inclusive Ranges |
| **4** | `<`, `<=`, `>`, `>=` | Left | Relational Comparisons |
| **3** | `==`, `!=` | Left | Equality Comparisons |
| **2** | `&&`, `\|\|` | Left | Logical AND, Logical OR |
| **1** | `\|>` | Left | Functional Pipeline Operator |
| **0** | `=`, `+=`, `-=`, `*=`, `/=`, `%=` | Right | Assignment Operations |

### 6.2 The Functional Pipeline Operator (`|>`)
Passes the evaluated left-hand expression as the first argument of the right-hand function call:
```aerix
fn double(x: i64) -> i64 => x * 2
fn add_ten(x: i64) -> i64 => x + 10
fn square(x: i64) -> i64 => x * x

let result = 5 |> double() |> add_ten() |> square() // ((5 * 2) + 10)^2 = 400
```

### 6.3 The Fluent Cascade Mutation Operator (`~>`)
Executes a mutating method call on an instance in-place and returns the instance forward without requiring `return self`:
```aerix
mut mech = BattleMech("Titan-01", 500)
mech ~> take_hit(50)
     ~> repair(20)
     ~> fire_missiles(2);
```

### 6.4 Null-Coalescing (`??`)
Evaluates the left-hand expression; if null, evaluates and returns the fallback right-hand expression:
```aerix
let nickname = user?.display_name ?? "Anonymous"
```

---

## 7. Control Flow Architecture

### 7.1 Conditionals (`if`, `elif`, `else`)
```aerix
if score >= 90 {
    grade = "A"
} elif score >= 80 {
    grade = "B"
} else {
    grade = "C"
}
```

### 7.2 Loops & Iteration (`while`, `for in`, `loop`)
```aerix
// Half-open range (0 to 9)
for i in 0..10 {
    println("Half-open: {i}")
}

// Closed inclusive range (1 to 10)
for i in 1..=10 {
    println("Inclusive: {i}")
}

// While loop
mut n = 5
while n > 0 {
    n -= 1
}
```

### 7.3 Fail-Fast Guard Invariants (`guard ... else`)
Replaces nested `if` pyramids by checking a condition and requiring early exit if false:
```aerix
fn withdraw(balance: i64, amount: i64) -> i64 {
    guard amount > 0 else {
        println("[ERROR] Amount must be positive.")
        return balance
    }
    guard balance >= amount else {
        println("[ERROR] Insufficient balance.")
        return balance
    }
    return balance - amount
}
```

### 7.4 Tagged Unions & Exhaustive Pattern Matching (`enum`, `match`)
Aerix enums are true tagged unions (algebraic data types) bearing heterogeneous payloads:
```aerix
enum SensorEvent {
    Idle,
    TemperatureAlert(celsius: f64, zone_id: i64),
    PressureSurge(psi: f64),
    HardwareFailure(code: str)
}

fn dispatch_event(evt: SensorEvent) {
    match evt {
        Idle => println("[STATUS] All sensors nominal."),
        TemperatureAlert(celsius, zone) => println("[ALERT] Zone {zone}: {celsius} C!"),
        PressureSurge(psi) => println("[WARN] Pressure surge: {psi} PSI"),
        HardwareFailure(code) => println("[PANIC] Failure code: '{code}'"),
        _ => println("[INFO] Catch-all wildcard arm")
    }
}
```

---

## 8. Functions, Overloading & Dispatch

### 8.1 Block & Expression Functions (`=>`)
```aerix
// Block function
fn add(a: i64, b: i64) -> i64 {
    return a + b
}

// Single-expression function
fn multiply(a: i64, b: i64) -> i64 => a * b
```

### 8.2 Static Method & Constructor Overloading
Aerix supports static compile-time overloading based on parameter count (arity) and types. Dispatches resolve at compile-time with **zero runtime overhead**:
```aerix
class Profile {
    pub name: str
    pub address: str
    pub age: i64

    // Constructor Overload 1: Default
    init(name: str) {
        self.name = name
        self.address = "Unassigned"
        self.age = 18
    }

    // Constructor Overload 2: Full
    init(name: str, address: str, age: i64) {
        self.name = name
        self.address = address
        self.age = age
    }

    // Method Overload A
    pub fn update_details(address: str) -> void {
        self.address = address
    }

    // Method Overload B
    pub fn update_details(address: str, age: i64) -> void {
        self.address = address
        self.age = age
    }
}
```

---

## 9. Object-Oriented Programming (OOP)

### 9.1 Class Declarations, Fields & Lifecycle (`init`, `drop`)
```aerix
class SocketConnection {
    pub host: str
    pub port: i64
    priv fd: i64

    init(host: str, port: i64) {
        self.host = host
        self.port = port
        self.fd = 1
        println("Socket connected to {self.host}:{self.port}")
    }

    // RAII Scoped Destructor
    drop() {
        println("Socket connection closed safely.")
    }
}
```

### 9.2 Inheritance & Virtual Tables (`extends`, `virtual`, `override`)
```aerix
class Entity {
    pub name: str

    init(name: str) { self.name = name }

    pub virtual fn render() {
        println("Rendering base entity: {self.name}")
    }
}

class Player extends Entity {
    pub health: i64

    init(name: str, hp: i64) {
        self.name = name
        self.health = hp
    }

    pub override fn render() {
        println("Rendering player: {self.name} (HP: {self.health})")
    }
}
```

### 9.3 Abstract Trait Contracts (`trait`, `implements`)
Traits specify compile-time interface contracts:
```aerix
trait Inspectable {
    fn inspect() -> void
}

trait Auditable {
    fn audit_log() -> str
}

class Service implements Inspectable, Auditable {
    pub name: str

    init(name: str) { self.name = name }

    pub fn inspect() -> void {
        println("Service: {self.name}")
    }

    pub fn audit_log() -> str {
        return "LOG: {self.name} active"
    }
}
```

### 9.4 Retroactive Type Extensions (`extend <Type>`)
Extends existing types with new methods without modifying the original definition or requiring inheritance:
```aerix
extend Vector2D {
    pub fn manhattan_distance() -> i64 {
        return self.x + self.y
    }
}
```

### 9.5 Reactive Properties (`pub prop`)
Properties provide zero-overhead getter and setter accessors with automatic encapsulation and validation:
```aerix
class SpaceStation {
    priv raw_docks: i64

    init() { self.raw_docks = 0 }

    pub prop docks: i64 {
        get => self.raw_docks
        set(val) {
            guard val >= 0 else {
                println("[ERROR] Docks cannot be negative!")
                return
            }
            self.raw_docks = val
        }
    }
}
```

### 9.6 User-Defined Operator Overloading (`pub op`)
```aerix
class Vector2D {
    pub x: i64
    pub y: i64

    init(x: i64, y: i64) { self.x = x; self.y = y }

    pub op +(other: Vector2D) -> Vector2D {
        return Vector2D(self.x + other.x, self.y + other.y)
    }

    pub op ==(other: Vector2D) -> bool {
        return self.x == other.x && self.y == other.y
    }
}
```

---

## 10. Compile-Time Generics & Monomorphization

Aerix uses static monomorphization (like modern C++ and Rust). Generic templates are analyzed and expanded into packed, specialized C99 structs for every concrete type used:

```aerix
class Container<T> {
    pub value: T

    init(val: T) { self.value = val }

    pub fn unwrap() -> T => self.value
}

fn main() {
    mut int_box = Container<i64>(42)        // Compiles to: Arx_Container_i64
    mut str_box = Container<str>("Aerix")    // Compiles to: Arx_Container_str
}
```
**Benefits:** Zero pointer indirection. Zero `void*` casting. 100% cache-locality.

---

## 11. Concurrency, Native Threads & Typed Channels

Aerix provides first-class, lightweight systems concurrency compiling directly into native Win32 threads (`CreateThread`) or POSIX pthreads (`pthread_create`).

### 11.1 Thread Spawning (`spawn`) & Trampoline Architecture
When `spawn func(args)` is called:
- **$\le 1$ Argument:** Compiles directly into zero-allocation thread routines passing the argument natively.
- **$\ge 2$ Arguments:** Automatically generates a typed, packed argument bundle struct (`Arx_ArgPack`) allocated in memory and unpacked by a typed C trampoline.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 AERIX MULTI-ARG THREAD TRAMPOLINE ARCHITECTURE              │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Spawn Call  │ spawn worker(id, channel, iterations)                      │
│ 2. ArgPack Gen │ struct Arx_ArgPack { int64_t a0; int64_t a1; int64_t a2; } │
│ 3. Memory Alloc│ Allocates 24-byte pack on heap or arena                    │
│ 4. OS Thread   │ CreateThread(NULL, 0, arx_trampoline, pack, 0, &tid)       │
│ 5. Trampoline  │ Unpacks a0, a1, a2 -> calls worker(...) -> frees pack      │
└─────────────────────────────────────────────────────────────────────────────┘
```

```aerix
fn background_task(worker_id: i64, ch_handle: i64, iterations: i64) {
    println("Worker {worker_id} started on thread...")
    arx_sleep_ms(20);
    arx_channel_send(ch_handle, worker_id * 100);
}

fn main() {
    mut ch = Channel<i64>(4);
    let t1 = spawn background_task(1, ch.handle, 50);
    let res = ch.recv();
    arx_thread_join(t1);
    ch.close();
}
```

### 11.2 Thread-Safe Bounded Channels (`Channel<T>`)
A high-throughput ring-buffer channel synchronized using native mutexes and condition variables:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   AERIX BOUNDED CHANNEL RING BUFFER MAP                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ [ Slot 0 ] [ Slot 1 ] [ Slot 2 ] [ Slot 3 ] [ Slot 4 ] [ Slot 5 ]           │
│      ▲                                           ▲                          │
│      │                                           │                          │
│   Head (Read)                                Tail (Write)                   │
│                                                                             │
│ Synchronized via Win32 CRITICAL_SECTION / CONDITION_VARIABLE                │
└─────────────────────────────────────────────────────────────────────────────┘
```

```aerix
class Channel<T> {
    pub handle: i64

    init(capacity: i64) { self.handle = arx_channel_new(capacity); }
    pub fn send(val: T) { arx_channel_send(self.handle, val as i64); }
    pub fn recv() -> T { return arx_channel_recv(self.handle) as T; }
    pub fn close() { arx_channel_close(self.handle); }
    pub fn free() { arx_channel_free(self.handle); }
}
```

---

## 12. Standard Library & Runtime API (`aerix_rt.h`)

| Runtime Function | Signature | Description |
| :--- | :--- | :--- |
| `println` | `println(val?: any) -> void` | Prints formatted string with `{var}` interpolation + newline. |
| `print` | `print(val: any) -> void` | Prints formatted string without appending a newline. |
| `eprintln` | `eprintln(val: any) -> void` | Prints formatted output directly to standard error (`stderr`). |
| `input` | `input(prompt?: str) -> T` | Dynamic console input parsed directly into target variable type. |
| `readln` | `readln() -> T` | Reads a line from standard input with target-typed parsing. |
| `typeof` | `typeof(expr: any) -> str` | Returns the compile-time type name of any expression as a string. |
| `assert` | `assert(cond: bool, msg?: str)`| Halts execution with panic diagnostic if condition is false. |
| `panic` | `panic(msg: str) -> void` | Halts execution immediately and displays panic backtrace. |
| `arx_time_now_ns`| `arx_time_now_ns() -> i64` | High-resolution hardware monotonic clock timestamp in nanoseconds. |
| `arx_time_now` | `arx_time_now() -> f64` | High-resolution hardware monotonic timestamp in seconds. |
| `arx_sleep_ms` | `arx_sleep_ms(ms: i64) -> void`| Suspends thread execution for specified milliseconds. |
| `arx_channel_new`| `arx_channel_new(cap: i64) -> i64` | Allocates new synchronized bounded channel ring-buffer. |
| `arx_channel_send`| `arx_channel_send(ch, val) -> void`| Pushes item into channel, blocking if full. |
| `arx_channel_recv`| `arx_channel_recv(ch) -> i64` | Pops item from channel, blocking if empty. |
| `arx_channel_close`| `arx_channel_close(ch) -> void` | Closes channel and wakes all waiting worker threads. |
| `arx_channel_free`| `arx_channel_free(ch) -> void` | Destroys synchronization mutexes and frees buffer memory. |
| `arx_thread_join`| `arx_thread_join(handle: i64) -> void`| Waits synchronously for thread termination and closes handle. |

---

## 13. C Interoperability & Foreign Function Interface (FFI)

Directly include ANSI C headers or link external C symbols with zero glue code:
```aerix
cinclude "<math.h>"
cinclude "<stdio.h>"

cextern fn sin(x: f64) -> f64
cextern fn cos(x: f64) -> f64

fn main() {
    let s = sin(3.14159 / 2.0)
    println("sin(pi/2) = {s}")
}
```

---

## 14. Developer Ecosystem & IDE Tooling

### Language Server Protocol (LSP) Daemon
Start the native LSP server:
```bash
arx lsp
```
Integrates with VS Code, Antigravity, Neovim, Sublime Text, and Helix via standard JSON-RPC 2.0.

### Automated Code Formatter & Linter
```bash
arx fmt program.arx   # Auto-formats source to official Aerix standards
arx lint program.arx  # Checks for dead code, unused variables, and style warnings
arx repl              # Starts interactive evaluation shell
```

---

## 15. Production Examples Catalog (26 Programs)

The repository provides 26 runnable programs in [`examples/`](file:///z:/VSCode/AerixLang/examples/):

| File | Topic & Concept |
| :--- | :--- |
| `01_hello_world.arx` | Entrypoint, console printing, string interpolation. |
| `02_procedural_math.arx` | Primitive types, arithmetic operators, precedence. |
| `03_oop_hero.arx` | Classes, `init`, fields, methods, `self`. |
| `04_IF_STATEMENTS.arx` | Branching logic, `if`, `elif`, `else`. |
| `05_CLASSES.arx` | OOP structures, visibility (`pub`, `priv`), methods. |
| `06_METHOD_OVERLOADING.arx` | Static arity and type mangling for methods and constructors. |
| `07_PIPELINE_OPERATOR.arx` | Functional composition with the pipeline operator `\|>`. |
| `08_LOOPS_AND_RANGES.arx` | Half-open `..` and inclusive `..=` ranges, while loops. |
| `09_USER_INPUT_AND_TYPING.arx` | Target-typed `input()`, `readln()`, and type reflection. |
| `10_DEFER_CLEANUP.arx` | Deterministic LIFO scoped cleanup (`defer`). |
| `11_INHERITANCE.arx` | Base and derived classes via `extends`. |
| `12_EXPRESSION_BODIED_FUNCTIONS.arx` | Concise inline single-expression functions (`=>`). |
| `13_STRING_INTERPOLATION.arx` | Embedded string variable expression substitution. |
| `14_METHOD_OVERRIDING.arx` | Dynamic polymorphic vtable dispatch (`virtual`, `override`). |
| `15_PROPERTIES.arx` | Reactive getters and setters with validation (`pub prop`). |
| `16_OPERATOR_OVERLOADING.arx` | User-defined operators (`pub op +`, `pub op ==`). |
| `17_GUARD_STATEMENTS.arx` | Anti-pyramid early exit assertions (`guard ... else`). |
| `18_FLUENT_CASCADE.arx` | In-place fluent mutation pipelines (`~>`). |
| `19_TYPE_EXTENSIONS.arx` | Retroactive method attachment via `extend <Type>`. |
| `20_TAGGED_UNIONS_AND_MATCH.arx` | Data-bearing `enum` variants and exhaustive `match`. |
| `21_ARENA_ALLOCATOR_AND_SIMD.arx` | Bump memory arena allocation, struct packing, `f32x4` SIMD. |
| `22_DEVELOPER_TOOLS_AND_CLI.arx` | Complete tour of `arx` toolchain commands. |
| `23_LANGUAGE_SERVER_AND_INTELLISENSE.arx` | LSP features, hover cards, completions, inlay hints. |
| `24_TRAITS_AND_INTERFACES.arx` | Abstract behavior contracts via `trait` and `implements`. |
| `25_GENERICS_AND_MONOMORPHISM.arx` | Zero-overhead static generic monomorphization (`<T>`). |
| `26_CONCURRENCY_AND_CHANNELS.arx` | Multi-core `spawn`, `Channel<T>`, joins, argpacks. |

---

## 16. Formal Language Grammar (EBNF)

```ebnf
Program         ::= ( TopLevelDecl )* ;
TopLevelDecl    ::= FunctionDecl | ClassDecl | TraitDecl | EnumDecl | ExtendDecl | ConstDecl | Directive ;

Directive       ::= "cinclude" StringLiteral | "cextern" FunctionDecl ;
FunctionDecl    ::= [ Visibility ] [ "static" | "virtual" | "override" ] "fn" Identifier [ GenericParams ] "(" [ ParamList ] ")" [ "->" Type ] ( Block | "=>" Expression ) ;
ClassDecl       ::= "class" Identifier [ GenericParams ] [ "extends" Identifier ] [ "implements" IdentifierList ] "{" ( ClassMember )* "}" ;
ClassMember     ::= FieldDecl | ConstructorDecl | DestructorDecl | MethodDecl | PropertyDecl | OperatorDecl ;

PropertyDecl    ::= [ Visibility ] "prop" Identifier ":" Type "{" "get" ( "=>" Expression | Block ) [ "set" "(" Identifier ")" Block ] "}" ;
OperatorDecl    ::= [ Visibility ] "op" OperatorSymbol "(" ParamList ")" [ "->" Type ] Block ;
TraitDecl       ::= "trait" Identifier "{" ( TraitMethodDecl )* "}" ;
EnumDecl        ::= "enum" Identifier "{" ( EnumVariant [ "," ] )* "}" ;
EnumVariant     ::= Identifier [ "(" ParamList ")" ] ;
ExtendDecl      ::= "extend" Identifier "{" ( MethodDecl )* "}" ;

Statement       ::= VarDecl | Assignment | GuardStmt | MatchStmt | DeferStmt | IfStmt | WhileStmt | ForStmt | ReturnStmt | ExprStmt ;
GuardStmt       ::= "guard" Expression "else" Block ;
MatchStmt       ::= "match" Expression "{" ( MatchArm [ "," ] )* "}" ;
MatchArm        ::= ( Pattern | "_" ) "=>" ( Expression | Block ) ;
DeferStmt       ::= "defer" Statement ;

Expression      ::= PipelineExpr ;
PipelineExpr    ::= CascadeExpr ( "|>" CascadeExpr )* ;
CascadeExpr     ::= LogicalOrExpr ( "~>" CallExpr )* ;
```

---

<div align="center">

Made with ⚡ for the **Aerix Systems Programming Language**  
*Speed of C • Safety of Rust • Elegance of Modern Scripting*

</div>
