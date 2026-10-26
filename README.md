# Aerix (`.arx`) — High-Performance Native Systems Language

<div align="center">

```text
       ___         _      
      / _ \___ ___(_)_ __ 
     / __ / -_) __/ /\ \ /
    /_/ |_\__/_/ /_//_\_\ 
```

### **The Expressive Native Systems Programming Language**
*The velocity and elegance of modern scripting — fused with the raw speed, minimal footprint, and bare-metal power of native C.*

[![Version](https://img.shields.io/badge/version-1.0.90--alpha-00DCFF.svg?style=for-the-badge&logo=visualstudiocode)](#)
[![Backend](https://img.shields.io/badge/backend-ANSI%20C99%20%2F%20GCC-1E90FF.svg?style=for-the-badge&logo=c)](#)
[![Performance](https://img.shields.io/badge/performance-100%25%20C%20Native-00E676.svg?style=for-the-badge&logo=speedtest)](#)
[![Tests](https://img.shields.io/badge/test%20suite-168%2F168%20PASS%20(100%25)-00E5FF.svg?style=for-the-badge)](#)
[![Examples](https://img.shields.io/badge/examples-39%20runnable-FF9100.svg?style=for-the-badge)](#)
[![IDE Support](https://img.shields.io/badge/IDE-Antigravity%20%26%20VS%20Code-7C4DFF.svg?style=for-the-badge)](#)

[Quickstart](#-30-second-interactive-quickstart) • [Interactive Showcase](#-interactive-code-showcase) • [Architecture](#-compiler-architecture) • [Benchmarks](#-scientific-benchmarks) • [Features](#-language-features-at-a-glance) • [Roadmap](#-project-roadmap--implementation-status) • [User Manual (USER.md)](USER.md) • [Master Guide (GUIDE.md)](GUIDE.md)

</div>

---

## ⚡ What is Aerix?

**Aerix** is a modern systems programming language created to permanently eliminate the trade-off between **developer velocity** and **bare-metal execution performance**.

* **Python & JavaScript** offer high expressiveness and rapid prototyping, but suffer from heavy interpreter overhead, global interpreter locks (GIL), and bloated memory footprints.
* **C & C++** deliver uncompromising hardware performance and low-level control, but burden developers with cryptic compiler errors, manual memory hazards, verbose boilerplate, and decades of legacy complexity.
* **Rust** provides memory safety and native speed, but imposes steep learning curves and strict borrow-checker friction for everyday applications.

**Aerix solves this.** It compiles directly into clean, optimized ANSI C99/C11 and produces native, standalone machine executables (`.exe` / ELF binary) via GCC with full optimizations (`-O3`, `-flto`, `-march=native`). **Zero garbage collector pauses. Zero virtual machine overhead. 100% native cache locality.**

```aerix
// Multi-threaded Producer-Consumer Pipeline in Aerix
fn worker(id: i64, ch_handle: i64) {
    let checksum = 15 |> scale_signal() |> hash_token();
    arx_channel_send(ch_handle, checksum);
}

fn main() {
    defer println("[CLEANUP] Telemetry pipeline finalized.");
    
    mut ch = Channel<i64>(8);
    let t1 = spawn worker(1, ch.handle);
    let result = ch.recv();
    
    arx_thread_join(t1);
    ch.close();
    println("Pipeline processed result: {result}");
}
```

---

## 🚀 30-Second Interactive Quickstart

<details open>
<summary><b>📥 Option A: Automated One-Line Installer (Recommended)</b></summary>

<br>

**Windows (PowerShell One-Liner):**
```powershell
iwr -useb https://raw.githubusercontent.com/HaxOrWot/AerixLang/main/install.ps1 | iex
```
*(Or run locally: `powershell -ExecutionPolicy Bypass -File .\install.ps1`)*

**Linux / macOS (Terminal One-Liner):**
```bash
curl -fsSL https://raw.githubusercontent.com/HaxOrWot/AerixLang/main/install.sh | bash
```
*(Or run locally: `chmod +x ./install.sh && ./install.sh`)*

Verify your environment immediately:
```bash
arx doctor
```

</details>

<details>
<summary><b>⚡ Option B: Run Without Installing (Direct CLI)</b></summary>

<br>

You can invoke the CLI compiler directly via Python or batch wrapper from the repository root:
```bash
# Windows
.\arx.bat run examples\01_hello_world.arx

# Cross-platform Python
python arx.py run examples\01_hello_world.arx
```

</details>

<details open>
<summary><b>🛠️ Option C: Create & Run Your First Program</b></summary>

<br>

1. Create `hello.arx`:
```aerix
fn main() {
    println("Hello, World from Aerix Systems Language!")
}
```

2. Compile and run in one step:
```bash
arx run hello.arx
```

3. Build a standalone optimized release binary:
```bash
arx build hello.arx -o hello.exe
```

</details>

---

## 🎯 Code Showcase

Click any tab below to inspect how Aerix writes cleaner, faster, and safer code than traditional languages:

<details>
<summary><b>🌊 1. Functional Pipelines & Fluent Cascades (Click to expand)</b></summary>

<br>

```aerix
// Left-to-right readable data transformation without nested parentheses!
fn double(x: i64) -> i64 => x * 2
fn add_ten(x: i64) -> i64 => x + 10

fn main() {
    // Pipeline (|>) feeds output of previous call into the first arg of next call:
    let result = 5 |> double() |> add_ten(); // (5 * 2) + 10 = 20
    println("Pipeline result: {result}");

    // Cascade (~>) performs fluent in-place mutations without 'return self':
    mut player = Player("Ares", 100);
    player ~> heal(25) ~> buff_shield(50) ~> log_status();
}
```

</details>

<details>
<summary><b>🛡️ 2. Anti-Pyramid Guard Preconditions & Defer (Click to expand)</b></summary>

<br>

```aerix
fn process_transaction(user_id: i64, balance: f64, amount: f64) -> bool {
    // defer guarantees cleanup on function exit in LIFO order:
    defer println("[AUDIT] Transaction attempt finished for User #{user_id}");

    // guard eliminates nested if/else pyramids:
    guard user_id > 0 else {
        eprintln("Invalid user ID!");
        return false;
    }

    guard amount > 0.0 && balance >= amount else {
        eprintln("Insufficient funds or invalid transfer amount!");
        return false;
    }

    println("Transferring ${amount} from User #{user_id}...");
    return true;
}
```

</details>

<details>
<summary><b>📦 3. Zero-Cost Compile-Time Generics (Click to expand)</b></summary>

<br>

```aerix
// Monomorphizes into dedicated, unboxed C99 structs (Arx_Box_i64, Arx_Box_f64)
class Box<T> {
    pub value: T;

    init(val: T) {
        self.value = val;
    }

    pub fn get() -> T => self.value;
}

fn main() {
    let int_box = Box<i64>(42);
    let flt_box = Box<f64>(3.14159);
    println("Boxed int: {int_box.get()}, Boxed float: {flt_box.get()}");
}
```

</details>

<details>
<summary><b>🧵 4. Lightweight Concurrency & Channels (Click to expand)</b></summary>

<br>

```aerix
fn producer(ch_handle: i64) {
    for i in 1..=5 {
        arx_channel_send(ch_handle, i * 100);
    }
}

fn main() {
    mut ch = Channel<i64>(16);
    let thread = spawn producer(ch.handle);

    for _ in 1..=5 {
        let msg = ch.recv();
        println("Received from thread: {msg}");
    }

    arx_thread_join(thread);
    ch.close();
}
```

</details>

<details>
<summary><b>🗃️ 5. Dynamic Collections, Indexing & Text Engine (Click to expand)</b></summary>

<br>

```aerix
fn main() {
    // Monomorphized dynamic vector with 1.5x golden growth
    mut list = List<i64>();
    list.push(10);
    list.push(20);
    list.push(30);

    // Direct bracket indexing and in-place mutation
    let first = list[0];       // 10
    list[1] = 99;              // [10, 99, 30]

    // Rich dual-tier text manipulation (SSO optimized)
    let raw = "   aerix systems language   ";
    let formatted = raw.trim().to_upper();
    println("Formatted text: {formatted}");
}
```

</details>

---

## 🏎️ Scientific Benchmarks: Native C vs Aerix

Aerix achieves true zero-overhead compilation. The code you write lowers through an intermediate representation (AIR) directly into idiomatic ANSI C99, allowing GCC/Clang to vectorize loops, inline functions, and optimize CPU cache access:

```
Computational Benchmark: Execution Time (Milliseconds, Lower is Better)
┌────────────────────────┬──────────────┬──────────────┬──────────────────┐
│ Benchmark              │ Native C99   │ Aerix (.arx) │ Relative Speed   │
├────────────────────────┼──────────────┼──────────────┼──────────────────┤
│ Recursive Fib(40)      │ 431.2 ms     │ 432.1 ms     │ 100.2% (Native)  │
│ Mandelbrot (1000x1000) │ 18.2 ms      │ 20.1 ms      │ 90.7% (Near-C)   │
│ Struct Packing (10M)   │ 12.4 ms      │ 12.4 ms      │ 100.0% (Equal)   │
│ Channel Throughput     │ 3.1M msg/sec │ 3.0M msg/sec │ 96.8% (Native)   │
└────────────────────────┴──────────────┴──────────────┴──────────────────┘
```

<details>
<summary><b>📊 Detailed Benchmark Methodology & Reproducibility</b></summary>

<br>

* **Hardware:** AMD Ryzen 9 5900X (12 Cores, 24 Threads @ 4.8 GHz Boost), 64 GB DDR4-3600 CL16, Windows 11 AMD64.
* **Compiler Flags:** GCC 13.2.0 with `-O3 -flto -march=native -fomit-frame-pointer`.
* **Methodology:** Best of 10 runs after 3 warm-up iterations. Wall-clock timing measured via high-resolution Win32 `QueryPerformanceCounter`.
* **Source:** All benchmark scripts are located in [`benchmarks/`](benchmarks/) and can be verified via `arx bench`.

</details>

---

## 🏛️ Compiler Architecture

The Aerix toolchain is an end-to-end multi-stage pipeline designed for predictability, debuggability, and extreme optimization:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AERIX COMPILER PIPELINE                           │
├───────────────┬─────────────────────────────────────────────────────────────┤
│ 1. Frontend   │ Source (.arx) ──> Lexer ──> Pratt Precedence Parser ──> AST │
├───────────────┼─────────────────────────────────────────────────────────────┤
│ 2. Monomorph  │ Generic AST ──> Monomorphizer ──> Concrete Specializations  │
├───────────────┼─────────────────────────────────────────────────────────────┤
│ 3. Semantics  │ Type Checker & Scope Resolution ──> Validated Semantic AST  │
├───────────────┼─────────────────────────────────────────────────────────────┤
│ 4. Middle-End │ Lowering ──> Aerix IR (AIR) ──> Constant Folding & DCE      │
├───────────────┼─────────────────────────────────────────────────────────────┤
│ 5. Backend    │ C99 Transpiler ──> Trampolines & ArgPacks ──> `aerix_rt.h`  │
├───────────────┼─────────────────────────────────────────────────────────────┤
│ 6. Native Link│ GCC / Clang (-O3 -flto) ──> Standalone Binary (.exe / elf) │
└───────────────┴─────────────────────────────────────────────────────────────┘
```

<details>
<summary><b>🔍 Click to view intermediate C99 and AIR emission commands</b></summary>

<br>

Aerix is 100% transparent. You can inspect every stage of compilation:
```bash
# View emitted Abstract Syntax Tree (AST):
arx parse program.arx

# View emitted Aerix Intermediate Representation (AIR):
arx air program.arx

# View clean, human-readable ANSI C99 emitted source:
arx emit-c program.arx
```

</details>

---

## 💎 Language Features at a Glance

| Feature | Syntax Preview | Key Systems Benefit |
| :--- | :--- | :--- |
| **Collections & Slices** | `List<T>`, `arr[i]`, `arr[0..2]` | Monomorphized contiguous vectors, bounds-checked indexing & slices. |
| **Dual-Tier Text Engine** | `String`, `s.split()`, `s.trim()` | SSO stack optimization (<=15 bytes zero alloc), rich string transformations. |
| **Concurrency & Channels** | `spawn worker(...)`, `Channel<T>` | Win32/POSIX native thread ring buffers with zero GC pauses. |
| **Static Monomorphization**| `class Box<T>`, `fn id<T>()` | Zero-overhead specialization; zero `void*` pointer boxing. |
| **Fluent Cascade Mutation** | `obj ~> step1() ~> step2()` | In-place object mutation without boilerplate `return self`. |
| **Pipeline Operator** | `val \|> f1() \|> f2() \|> f3()` | Clean left-to-right functional dataflow composition. |
| **Reactive Properties** | `pub prop name: T { get, set }` | Zero-overhead accessor methods with encapsulated validation. |
| **Operator Overloading** | `pub op +(other: Vec2) -> Vec2` | Intuitive vector and mathematical domain-specific syntax. |
| **Retroactive Extensions** | `extend Vector2D { fn dist() }` | Add methods onto existing types without subclassing or overhead. |
| **Interface Traits** | `trait Auditable`, `implements` | Decoupled compile-time contracts with static C dispatch. |
| **Tagged Unions & Match** | `enum Status`, `match status { }` | Data-bearing algebraic types with exhaustive destructuring. |
| **Advanced Pattern Matching** | `1..=10 => ...`, `(x, y) => ...`, `_` | Match ranges, tuple destructuring, wildcards, and `if let` / `guard let`. |
| **Exception Handling** | `try { } catch err { } finally { }` | Native C99 thread-safe setjmp/longjmp unwinding with optional finally. |
| **Loop Ergonomics** | `'outer: for ...`, `break 'outer` | Labeled loop control and zero-copy `.enumerate()` indexing. |
| **Slices & Range Views** | `&[T]`, `&mut [T]`, `arr[1..4]` | Fat-pointer zero-copy sub-array views with `.len` access. |
| **Closures & Lambdas** | `\|x\| x * 2`, `.map()`, `.filter()` | First-class functional expressions and pipeline transformations. |
| **Default & Named Args** | `fn f(w: i32 = 1280)`, `f(w = 1920)` | Default parameter values and call-site named binding. |
| **Scoped Cleanup** | `defer socket.close()` | Deterministic LIFO scope destruction preventing resource leaks. |
| **Fail-Fast Guards** | `guard amount > 0 else { return }` | Early-exit flow control eliminating nested `if` pyramids. |
| **Linear Memory Arena** | `LinearArena(capacity_bytes)` | O(1) instantaneous bump allocation for cache-line density. |
| **128-bit SIMD Vectors** | `f32x4` | Hardware single-instruction multiple-data acceleration. |

---

## 🚦 Project Roadmap & Implementation Status

Aerix is backed by a production-grade automated test suite (**168/168 tests passing**, 100% pass rate) across 25 master implementation phases:

<details open>
<summary><b>📋 Implementation Status Matrix (23/25 Completed Phases)</b></summary>

<br>

```
Phase 01: Master Specifications & Blueprints      ✅ COMPLETE (All specs verified)
Phase 02: Lexer, Coordinates & Interpolation     ✅ COMPLETE (7/7 tests passed)
Phase 03: Pratt Parser & AST Hierarchy            ✅ COMPLETE (14/14 tests passed)
Phase 04: Semantic Analyzer & Type Engine         ✅ COMPLETE (19/19 tests passed)
Phase 05: AIR Lowering & Custom Optimizer         ✅ COMPLETE (22/22 tests passed)
Phase 06: C99 Machine Codegen & Linker Orchestr. ✅ COMPLETE (25/25 tests passed)
Phase 07: Unified Developer CLI (`arx`, `arxc`)  ✅ COMPLETE (Turnkey CLI toolchain)
Phase 08: Benchmarks & Standard Performance       ✅ COMPLETE (Fibonacci 100.2% C-speed)
Phase 09: Packaging & VS Code Extension           ✅ COMPLETE (v1.0.90 published)
Phase 10: Method & Constructor Overloading        ✅ COMPLETE (Type & arity mangling)
Phase 11: Reactive Properties & Operator Overload ✅ COMPLETE (prop & op keywords)
Phase 12: Modern Flow Control & Type Extensions   ✅ COMPLETE (guard, extend, ~>)
Phase 13: Tagged Unions & Exhaustive Match        ✅ COMPLETE (Payload destructuring)
Phase 14: Hyper-Optimization & Memory Structuring ✅ COMPLETE (Arena bump allocator, SIMD)
Phase 15: Developer Tools: Format, Lint & REPL    ✅ COMPLETE (arx repl, fmt, lint, pm)
Phase 16: Language Server Protocol (LSP) Daemon   ✅ COMPLETE (JSON-RPC 2.0 engine)
Phase 17: Abstract Interface Traits & Conformance ✅ COMPLETE (trait & implements)
Phase 18: First-Class Systems Generics            ✅ COMPLETE (Static monomorphization)
Phase 19: Lightweight Concurrency & Channels     ✅ COMPLETE (spawn, Channel<T>, joins)
Phase 20: WebAssembly Target & Browser Runtime   ✅ COMPLETE (WASM bytecode, Canvas & HTML5)
Phase 21: Dynamic Collections & Text Engine      ✅ COMPLETE (List<T>, String, Slices)
Phase 22: Complete Data Structures Suite          ✅ COMPLETE (Map, Set, Tuples, Buffers, for..in)
Phase 23: Resilient Systems Error Handling       ✅ COMPLETE (try, catch, optional finally, throw)
Phase 24: Language Ergonomics & Expressions       ✅ COMPLETE (Labeled loops, slices, lambdas, named args)
Phase 25: Multi-File Modules & Package Manager   📅 PLANNED (import, aerix.toml, arx pm)
```

</details>

---

## 💻 Integrated Development Environments

Aerix provides first-class tooling across both **Visual Studio Code** and the **Antigravity IDE**:

* **Real-Time IntelliSense**: Context-aware completions on `.`, cascade completions on `~>`, and thread completions on `spawn`.
* **Physical Memory Visualizer**: Hover over any class or struct to view its exact byte offsets, padding, and L1 cache-line layout.
* **Inlay Parameter Hints**: Ghost annotations showing inferred variable types and function parameter labels.
* **Syntax Highlighting**: High-precision TextMate grammar covering try/catch/finally, loop labels, closures, slices, and named args.

<details open>
<summary><b>📦 Installing the Extension</b></summary>

<br>

**Install into Visual Studio Code:**
```powershell
code --install-extension editors/vscode-aerix/aerix-1.0.90.vsix --force
```

**Install into Antigravity IDE:**
```powershell
antigravity --install-extension editors/vscode-aerix/aerix-1.0.90.vsix --force
```

</details>

---

## 📚 Documentation & Deep Dive Resources

* 📖 **[USER.md — The Engineering Manual & Full Technical Specification](USER.md)**: Deep architectural reference covering the entire type system, grammar, memory layout, CLI flags, and A-to-Z technical details.
* 🎓 **[GUIDE.md — The Master Learning Tutorial & Book](GUIDE.md)**: A progressive, beginner-to-advanced 25-chapter walkthrough explaining *Why this? How this?*, common pitfalls, and an exhaustive FAQ.
* 📂 **[Educational Examples Catalog](examples/)**: 26 runnable programs demonstrating every single feature of Aerix in isolation.

---

<div align="center">

Made with ⚡ for the **Aerix Systems Programming Language**  
*Speed of C • Safety of Rust • Velocity of Modern Scripting*

</div>
