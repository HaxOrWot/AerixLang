# Aerix (arx) — Implementation Roadmap & Milestones

> **Execution Strategy:** Phased, Test-Driven Development (TDD) from Specification to Native Execution.

---

## 1. Roadmap Overview

```
[Phase 1] Architectural Specifications (COMPLETED)
    │
    ▼
[Phase 2] Lexer & Tokenizer Engine
    │
    ▼
[Phase 3] Pratt Parser & AST Representation
    │
    ▼
[Phase 4] Semantic Analyzer, Type Checker & Scope Resolution
    │
    ▼
[Phase 5] C99 Code Generator & Zero-Cost Runtime (aerix_rt.h)
    │
    ▼
[Phase 6] Arx CLI Driver & GCC Integration
    │
    ▼
[Phase 7] Standard Library Modules & Examples
    │
    ▼
[Phase 8] Performance Benchmarks vs Pure C/C++
```

---

## 2. Phase Breakdown & Exit Criteria

### Phase 1: Architectural Specifications & Blueprints (STATUS: ✅ COMPLETE)
- [x] `INSTRUCTION.md` — Master behavioral constitution & operational rules.
- [x] `README.md` — Flagship project overview, ASCII banner, comparison matrix.
- [x] `USER.md` — Beginner-friendly guide for everyday programmers.
- [x] `00_PROJECT_PLAN.md` — Vision, system architecture, directory layouts.
- [x] `00_QUICK_DEV_CHEATSHEET.md` — Turnkey Developer Cheatsheet (Pratt tables, AST classes, C99 rules).
- [x] `01_SYNTAX_SPECIFICATION.md` — Full EBNF grammar, dual-paradigm syntax, operators.
- [x] `02_COMPILER_PIPELINE.md` — Lexer, parser, AST, Pratt engine, codegen, error reporting.
- [x] `03_OOP_AND_TYPE_SYSTEM.md` — Classes, inheritance, vtables, struct padding, devirtualization.
- [x] `04_RUNTIME_AND_MEMORY.md` — Memory model, `defer`, `aerix_rt.h`, C FFI.
- [x] `05_STANDARD_LIBRARY_SPEC.md` — Built-in functions and modules (`math`, `io`, `vec`, `str`).
- [x] `06_TOOLCHAIN_AND_CLI.md` — `arx` CLI flags, GCC orchestration, project config.
- [x] `07_ROADMAP_AND_MILESTONES.md` — Execution checklist (this file).
- [x] `08_TEST_AND_BENCHMARK_SPEC.md` — Automated test vectors & Mandelbrot/Fibonacci benchmarks.
- [x] `09_DISTRIBUTION_AND_PACKAGING.md` — Global installers, standalone binary & VS Code extension.

---

### Phase 2: Compiler Frontend — Lexer & Tokenizer (`src/frontend/`) (STATUS: ✅ COMPLETE)
* **Goal:** High-speed scanner supporting line/col tracking, string interpolation, and operators (`|>`, `->`, `=>`).
* **Deliverables:**
  - [x] `src/frontend/tokens.py`: `TokenType` enumeration and `Token` dataclass.
  - [x] `src/frontend/lexer.py`: Lexical scanner with exact source coordinates and error handling.
* **Exit Criteria:** Pass all unit tests in `src/tests/test_lexer.py` (Passed: 7/7 tests in 0.001s).

---

### Phase 3: Compiler Frontend — Pratt Parser & AST (`src/frontend/`) (STATUS: ✅ COMPLETE)
* **Goal:** Parse tokens into a strongly-typed Abstract Syntax Tree.
* **Deliverables:**
  - [x] `src/frontend/ast_nodes.py`: AST dataclasses for procedural scripts and OOP classes.
  - [x] `src/frontend/parser.py`: Recursive descent parser with 14-level Pratt operator precedence climbing.
* **Exit Criteria:** Successfully parse procedural code, OOP classes, and pipelines into valid ASTs (Passed: 7/7 parser tests, 14 total).

---

### Phase 4: Compiler Middle-End — Semantics & Type Engine (`src/middle/`) (STATUS: ✅ COMPLETE)
* **Goal:** Enforce compile-time safety, type inference, symbol table scopes, and class hierarchy analysis.
* **Deliverables:**
  - [x] `src/middle/typesystem.py`: Static types and Hindley-Milner-inspired local type inference.
  - [x] `src/middle/semantic.py`: Lexical scope stack, immutability checker (`let` vs `mut`), access control (`pub`/`priv`).
* **Exit Criteria:** Catch type mismatches and invalid reassignments with colored terminal diagnostics (Passed: 5/5 semantic tests, 19 total).

---

### Phase 5: Compiler Middle-End — AIR & Custom Optimizer (`src/middle/`) (STATUS: ✅ COMPLETE)
* **Goal:** Lower AST into Aerix Intermediate Representation (AIR) and execute custom compiler optimization passes.
* **Deliverables:**
  - [x] `src/middle/air.py`: 3-address code linear IR with typed temporaries and basic blocks.
  - [x] `src/middle/optimizer.py`: Custom optimization passes:
    - Constant folding & propagation.
    - Whole-program method devirtualization.
    - Function inlining.
    - Dead code elimination (DCE).
    - Defer unwind synthesis.
* **Exit Criteria:** Generate verified, optimized AIR for all standard control-flow patterns (Passed: 3/3 optimizer tests, 22 total).

---

### Phase 6: Compiler Backend — Machine-Target Codegen & Linker (`src/backend/`) (STATUS: ✅ COMPLETE)
* **Goal:** Emit clean, highly optimizable C99 code and link native binaries via GCC.
* **Deliverables:**
  - [x] `src/backend/codegen.py`: AIR-to-C99 emitter.
  - [x] `src/backend/linker.py`: Direct GCC/Clang linker invocation with `-O3`, `-flto`, `-march=native`.
* **Exit Criteria:** Emitted C code compiles cleanly without warnings with GCC (Passed: 3/3 codegen & end-to-end native tests, 25 total).

---

### Phase 7: Toolchain CLI & Driver (`src/driver.py`, `src/arx.py`, `arx.bat`) (STATUS: ✅ COMPLETE)
* **Goal:** Unified developer experience: `arx run`, `arx build`, `arx emit-c`, `arx doctor`, `arx new`.
* **Deliverables:**
  - [x] `src/driver.py`: Multi-pass compiler orchestrator.
  - [x] `src/arx.py`: CLI driver with diagnostic engine and project generator.
  - [x] `src/arxc.py`: Standalone compiler CLI entrypoint.
  - [x] `arx.bat`: Windows quick launcher.
* **Exit Criteria:** Successfully run `arx doctor` and `arx run examples/01_hello_world.arx` (Passed: all CLI commands operational).

---

### Phase 8: Standard Library & Performance Parity Benchmarks (STATUS: ✅ COMPLETE)
* **Goal:** Validate standard library modules and scientifically prove 1:1 speed with native C/C++.
* **Deliverables:**
  - [x] Example suite: `examples/01_hello_world.arx`, `examples/02_procedural_math.arx`, `examples/03_oop_hero.arx`.
  - [x] Benchmarks: Recursive Fibonacci (`benchmarks/fib.arx`, `benchmarks/fib.c`) & Mandelbrot Fractal (`benchmarks/mandelbrot.arx`, `benchmarks/mandelbrot.c`).
  - [x] Benchmark runner: `scripts/run_benchmarks.py`.
* **Exit Criteria:** Aerix execution performance matches GCC `-O3` native C within **98% - 100%** (Passed: Fibonacci 100.2%, Mandelbrot 90.7%).

---

### Phase 9: Global Distribution, Packaging & Tooling Ecosystem (STATUS: ✅ COMPLETE)
* **Goal:** Turnkey global installation, frozen standalone binaries without Python dependency, and official editor tooling.
* **Deliverables:**
  - [x] `scripts/build_standalone.py`: Standalone binary freezing script producing native `dist/arx.exe` (9.35 MB) with bundled runtime via PyInstaller.
  - [x] `install.ps1`: Universal one-line installer for Windows PowerShell (`irm https://get.aerix-lang.org/install.ps1 | iex`). Configures `%USERPROFILE%\.aerix\bin`, User PATH, and runtime.
  - [x] `install.sh`: Universal one-line installer for Linux/macOS POSIX shells (`curl -fsSL https://get.aerix-lang.org/install.sh | sh`).
  - [x] `editors/vscode-aerix/`: Official VS Code extension with rich TextMate syntax grammar (`syntaxes/aerix.tmLanguage.json`) and language configuration.
  - [x] `src/arx.py` tooling enhancements: Added `arx test` (automated test suite runner) and `arx setup-tools` (guided C backend setup).
* **Exit Criteria:** Standalone `dist/arx.exe` executes `doctor` and compiles `.arx` programs independently with zero Python installed. (Passed: 100% operational).

---

### Phase 10: Aerix 2.0 Foundation — Full OOP Overloading & Multi-Inits (STATUS: ✅ COMPLETE)
* **Goal:** Enable static method and constructor overloading via type-and-arity mangling, plus first-class named constructor variants (`init.<variant>()`).
* **Deliverables:**
  - [x] Extended AST nodes: multi-constructor arrays, named inits (`init.<variant>`), and `resolved_mangled_name` resolution tags.
  - [x] Semantic arity and type-specialized overload resolution in `SemanticAnalyzer` & `typesystem.py`.
  - [x] Symbol mangler generating deterministic C identifiers: `Arx_<Class>_<method>__<param_types>`.
  - [x] End-to-end test suite (`src/tests/test_overloading.py`) verifying arity overloading, type overloading, and constructor overloading (37/37 tests passing).
  - [x] Educational demonstration example (`examples/06_METHOD_OVERLOADING.arx`) executing with zero runtime overhead.

---

### Phase 11: Reactive Properties & Operator Overloading (STATUS: ✅ COMPLETE)
* **Goal:** Eliminate getter/setter boilerplate with `prop get/set`, and enable safe user-defined operator overloading (`pub op +`, `pub op ==`, `pub op []`).
* **Deliverables:**
  - [x] Parser support for `pub prop <name>: <type> { get => ..., set(v) => ... }` and computed read-only properties.
  - [x] Parser and AST nodes for `pub op <symbol>(other: Type) -> RetType` supporting arithmetic and comparison overloads.
  - [x] Inlining and dispatch engine in `semantic.py`, `air.py`, and `codegen.py` transforming property access and operator expressions to zero-overhead C functions.
  - [x] Unit test suite (`src/tests/test_phase11_properties_and_operators.py`) passing with 100% assertions (40/40 tests passing across compiler).
  - [x] Demonstration examples in `examples/15_PROPERTIES.arx` and `examples/16_OPERATOR_OVERLOADING.arx`.

---

### Phase 12: Modern Ergonomics & Unique Flow Control (STATUS: ✅ COMPLETE)
* **Goal:** Implement zero-overhead type extensions (`extend <Type>`), guard clauses (`guard ... else`), and the fluent cascade mutation pipeline (`~>`).
* **Deliverables:**
  - [x] Parser and semantic analyzer for `extend <Type> { ... }` with static dispatch.
  - [x] `guard <cond> else { <exit> }` grammar lowering to inverted C branching (`AIRBranchIf`).
  - [x] `~>` fluent cascade mutation chaining compiler pass returning receiver instance.
  - [x] Dedicated unit test suite (`src/tests/test_phase12_ergonomics.py`) passing with 100% assertions (44/44 total compiler tests passing).
  - [x] Comprehensive demonstration examples: `examples/17_GUARD_STATEMENTS.arx`, `examples/18_FLUENT_CASCADE.arx`, and `examples/19_TYPE_EXTENSIONS.arx`.


---

### Phase 13: Tagged Unions & Exhaustive Pattern Matching (STATUS: ✅ COMPLETE)
* **Goal:** First-class algebraic data types: `enum` variants with data payloads and exhaustive `match` expressions.
* **Deliverables:**
  - [x] Tagged union C99 struct emission: `struct { uint8_t tag; union data; }`.
  - [x] Exhaustiveness analyzer checking that all enum cases are handled at compile time.
  - [x] Destructuring pattern matching lowering with variable binding and branch guards.
  - [x] Unit test suite (`src/tests/test_phase13_tagged_unions.py`) passing with 100% assertions (48/48 total compiler tests passing).
  - [x] Comprehensive demonstration example: `examples/20_TAGGED_UNIONS_AND_MATCH.arx`.

---

### Phase 14: Hyper-Optimization & Memory Engineering (STATUS: ✅ COMPLETE)
* **Goal:** Maximum cache density, devirtualization, and linear arena memory management.
* **Deliverables:**
  - [x] Cache-line struct field packing (automatic size-ordered alignment: 8B -> 4B -> 2B -> 1B).
  - [x] Whole-program devirtualization pass converting static method dispatches to direct C function calls.
  - [x] High-speed linear arena memory allocator in `stdlib/aerix_rt.h` and Aerix scratchpad classes.
  - [x] 4-lane hardware SIMD vector operations (`f32x4`, vector dot/add/sub/mul).
  - [x] Dedicated unit test suite (`src/tests/test_phase14_optimization_and_memory.py`) passing with 100% assertions (53/53 compiler tests passing).
  - [x] Comprehensive demonstration example: `examples/21_ARENA_ALLOCATOR_AND_SIMD.arx`.

---

### Phase 15: Developer Experience & CLI Ecosystem (STATUS: ✅ COMPLETE)
* **Goal:** Enterprise-tier developer workflow tools.
* **Deliverables:**
  - [x] Interactive REPL (`arx repl`) for live expression evaluation and state accumulation.
  - [x] Code formatter (`arx fmt`) and dead-code linter (`arx lint`).
  - [x] Package manager (`arx pm`) for external dependency management and project manifests (`aerix.toml`).
  - [x] Dedicated unit test suite (`src/tests/test_phase15_developer_tools.py`) passing with 100% assertions (58/58 compiler tests passing).
  - [x] Comprehensive demonstration example: `examples/22_DEVELOPER_TOOLS_AND_CLI.arx`.

---

### Phase 16: Native Language Server Protocol (LSP) Daemon & 7000x IDE Intelligence (STATUS: ✅ COMPLETE)
* **Goal:** Full-featured JSON-RPC 2.0 Language Server Protocol daemon (`arx lsp`) powering VS Code, Antigravity IDE, Neovim, and Zed.
* **Deliverables:**
  - [x] `src/tools/lsp.py`: Standard JSON-RPC 2.0 language server over stdio.
  - [x] Real-time compiler diagnostics (`textDocument/publishDiagnostics`) with line, col, and severity.
  - [x] Hover tooltips (`textDocument/hover`) showing function signatures, inferred variable types, and class docframes.
  - [x] Go-to-definition (`textDocument/definition`) mapping identifiers to source line & column coordinates.
  - [x] Smart completions (`textDocument/completion`) for keywords, primitives, and in-scope symbols.
  - [x] Formatting dispatch (`textDocument/formatting`) connecting editor format-on-save directly to `AerixFormatter`.
  - [x] CLI integration: `arx lsp` in `src/arx.py`.
  - [x] Dedicated unit test suite (`src/tests/test_phase16_lsp.py`) passing with 100% assertions (63/63 total compiler tests passing).
  - [x] Educational demonstration example: `examples/23_LANGUAGE_SERVER_AND_INTELLISENSE.arx`.

---

### Phase 17: Abstract Interface Traits & Dynamic VTables (STATUS: ✅ COMPLETE)
* **Goal:** Safe polymorphism via decoupled traits and compile-time interface conformance.
* **Deliverables:**
  - [x] `trait <Name> { ... }` declarations with method signatures and parameter types.
  - [x] `class <Class> implements <Trait1>, <Trait2>` multi-trait interface contracts.
  - [x] Strict compile-time conformance validation checking method existence, parameter types, and return types.
  - [x] Escaped string interpolation (`\{`, `\}`) for JSON telemetry generation.
  - [x] Static zero-cost direct dispatch when concrete type is known.
  - [x] Dedicated unit test suite (`src/tests/test_phase17_traits.py`) passing with 100% assertions (69/69 total compiler tests passing).
  - [x] Educational demonstration example: `examples/24_TRAITS_AND_INTERFACES.arx`.

---

### Phase 18: First-Class Generics & Static Monomorphization (STATUS: ✅ COMPLETE)
* **Goal:** Zero-cost polymorphic data structures and generic functions via compile-time monomorphization.
* **Deliverables:**
  - [x] Generic class declarations: `class Box<T> { pub value: T }` and `class Pair<K, V>`.
  - [x] Generic function declarations: `fn identity<T>(val: T) -> T`.
  - [x] Parser support for generic angle bracket arguments `<T, U>` in functions, classes, type annotations, and instantiation callsites.
  - [x] Middle-end static AST monomorphizer pass (`src/middle/monomorphizer.py`) expanding generic templates into specialized C99 structs (`Arx_Box_i64`) and functions (`arx_identity_f64`).
  - [x] Zero-cost runtime abstraction: zero runtime boxing, zero `void*` indirection, 100% cache locality.
  - [x] Dedicated unit test suite (`src/tests/test_phase18_generics.py`) passing with 100% assertions (75/75 total compiler tests passing).
  - [x] Educational demonstration example: `examples/25_GENERICS_AND_MONOMORPHISM.arx`.

---

### Phase 19: Lightweight Concurrency & Message Passing (STATUS: ✅ COMPLETE)
* **Goal:** Zero-cost thread primitives, task spawning, and typed lock-free channels.
* **Deliverables:**
  - [x] `spawn` worker thread primitive and zero-cost trampoline scheduler abstractions.
  - [x] Cross-platform Win32/POSIX threading runtime (`arx_thread_spawn`, `arx_thread_join`, `arx_sleep_ms`).
  - [x] Typed bounded message channels (`Channel<T>`, `arx_channel_*`) for thread-safe cross-task communication.
  - [x] Dedicated unit test suite (`src/tests/test_phase19_concurrency.py`) passing with 100% assertions (80/80 total compiler tests passing).
  - [x] Educational demonstration example: `examples/26_CONCURRENCY_AND_CHANNELS.arx`.

---

### Phase 20: WebAssembly (WASM) Backend & Browser Target (STATUS: ✅ COMPLETE)
* **Goal:** Direct compilation to WebAssembly bytecode (`.wasm`) for ultra-high-speed browser deployment.
* **Deliverables:**
  - [x] WebAssembly text format (`.wat`) and self-contained pure-Python binary emitter (`src/backend/wasm.py`).
  - [x] Browser JS interop and WebAssembly HTML5 hardware-accelerated 2D canvas & terminal runner.
  - [x] Dedicated unit test suite (`src/tests/test_phase20_wasm.py`) passing with 100% assertions (87/87 total compiler tests passing).
  - [x] Educational demonstration example: `examples/27_WASM_BROWSER_RUNTIME.arx`.

---

### Phase 21: Dynamic Collections & Text Engine (STATUS: 🚀 PLANNED)
* **Goal:** Monomorphized growable arrays (`List<T>`), bracket indexing (`arr[i]`), zero-copy slicing (`[start..end]`), and an owned dynamic `String` manipulation API.
* **Deliverables:**
  - [ ] Heap-allocated, amortized $O(1)$ capacity-doubling `List<T>` with automatic memory reclamation.
  - [ ] Bracket indexing expressions `list[index]` for reading and mutating array elements.
  - [ ] High-performance slice view syntax `list[start..end]` without buffer copying.
  - [ ] Owned mutable `String` struct with `.split()`, `.trim()`, `.replace()`, `.to_upper()`, `.to_lower()`, and `.join()`.
  - [ ] Dedicated unit test suite (`src/tests/test_phase21_collections.py`).
  - [ ] Educational demonstration example: `examples/28_DYNAMIC_COLLECTIONS_AND_STRINGS.arx`.

---

### Phase 22: Associative Tables, Sets & Collection Iteration (STATUS: 🚀 PLANNED)
* **Goal:** High-performance Robin Hood hash tables (`Map<K, V>`), unique item collections (`Set<T>`), and generalized `for item in collection` loops.
* **Deliverables:**
  - [ ] $O(1)$ average-time key-value dictionary (`Map<K, V>`) with bracket indexing (`map[key] = val`).
  - [ ] Deduplicated hash set (`Set<T>`) supporting mathematical set algebra (`union`, `intersection`, `difference`).
  - [ ] Generalized `for .. in` syntax supporting dynamic lists, sets, and map key-value pairs (`for (k, v) in map`).
  - [ ] `.enumerate()` iterator helper returning `(index, item)`.
  - [ ] Dedicated unit test suite (`src/tests/test_phase22_maps_and_sets.py`).
  - [ ] Educational demonstration example: `examples/29_MAPS_SETS_AND_ITERATION.arx`.

---

### Phase 23: Lightweight Records, Tuples & Linear Buffers (STATUS: 🚀 PLANNED)
* **Goal:** Anonymous zero-cost tuples (`(T1, T2)`), destructuring assignment, and FIFO/LIFO contiguous buffers (`Queue<T>`, `Stack<T>`, `Deque<T>`).
* **Deliverables:**
  - [ ] Anonymous fixed-size tuple types `(T1, T2, ...)` mapped directly to contiguous C structs without class boilerplate.
  - [ ] Tuple destructuring syntax: `let (name, score, is_active) = get_user_record()`.
  - [ ] Contiguous ring-buffer collections: `Queue<T>` (FIFO), `Stack<T>` (LIFO), and `Deque<T>` (double-ended).
  - [ ] Dedicated unit test suite (`src/tests/test_phase23_tuples_and_buffers.py`).
  - [ ] Educational demonstration example: `examples/30_TUPLES_AND_BUFFERS.arx`.

---

### Phase 24: Resilient Systems Error Handling (STATUS: 🚀 PLANNED)
* **Goal:** Panic-free, zero-overhead error propagation via `Result<T, E>`, `Option<T>`, and the `?` early-exit operator.
* **Deliverables:**
  - [ ] Standard library tagged algebraic data types: `enum Result<T, E> { Ok(val: T), Err(err: E) }` and `enum Option<T> { Some(val: T), None }`.
  - [ ] The `?` error propagation operator to automatically unwrap `Ok` values or early-return `Err` up the call stack.
  - [ ] Ergonomic helpers: `.unwrap()`, `.unwrap_or(default)`, and `.is_ok()`.
  - [ ] Dedicated unit test suite (`src/tests/test_phase24_error_handling.py`).
  - [ ] Educational demonstration example: `examples/31_RESULT_AND_ERROR_PROPAGATION.arx`.

---

### Phase 25: Multi-File Module System & Package Integration (STATUS: 🚀 PLANNED)
* **Goal:** Native multi-file compilation, modular namespaces, and seamless dependency resolution via `arx pm`.
* **Deliverables:**
  - [ ] `import "./path/file.arx"` and selective symbol imports `import { SymbolA, SymbolB } from "module"`.
  - [ ] Circular dependency detection and topological sorting in compiler driver.
  - [ ] Seamless integration with `aerix.toml` so `import package_name` resolves dependencies downloaded by `arx pm`.
  - [ ] Multi-file compilation support across both C99 and WebAssembly backends.
  - [ ] Dedicated unit test suite (`src/tests/test_phase25_modules.py`).
  - [ ] Educational demonstration project: `examples/32_MULTI_FILE_PROJECT/`.




