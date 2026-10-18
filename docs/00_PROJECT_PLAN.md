# Aerix (arx) — Master Project Plan & Architecture

> **Language Name:** Aerix  
> **Short Name / Extension:** `.arx`  
> **Compiler Binary & CLI:** `arx`  
> **Target Execution Backend:** High-Performance C99 / Native Machine Code via GCC 13+  
> **Motto:** *The clarity of modern syntax with the raw, uncompromising speed of bare-metal C.*

---

## 1. Vision & Core Philosophy

Aerix is conceived to solve the fundamental friction in modern programming: developers love the clean, expressive syntax of languages like Python, TypeScript, and Go, but systems developers need the deterministic performance, predictable memory layout, and raw execution speed of C and C++.

Aerix bridges this divide by providing:

1. **Dual-Paradigm Flexibility ("Normal" + "OOP"):**
   - **Procedural / Scripting:** Write plain top-level scripts, raw algorithms, or math functions without wrapping everything in boilerplate classes.
   - **Modern Object-Oriented:** Write clean, modular systems using structured `class` definitions, encapsulation (`pub`/`priv`), constructors, inheritance, interfaces, and polymorphism.
2. **True C-Level Execution Speed:**
   - No virtual machine (VM).
   - No heavy garbage collection (GC) pauses.
   - Compiles down to optimized C99/C11 and leverages GCC with `-O3`, SIMD vectorization, and Link-Time Optimization (`-flto`).
3. **Distinctive & Expressive Syntax:**
   - Clean, lightweight keywords (`fn`, `let`, `mut`, `class`, `trait`, `defer`).
   - Built-in pipeline operator (`|>`) for intuitive data flow.
   - String interpolation (`println("Value: {x}")`).
   - Optional semicolons (newline-aware statement termination).
   - Zero-overhead native C interoperability (`cinclude`, `cextern`).

---

## 2. System Architecture & Compilation Flow

Aerix adopts an Ahead-of-Time (AOT) transpiler-to-native architecture. This guarantees that every Aerix construct maps to zero-overhead C constructs, benefiting from decades of compiler optimization while giving developers modern developer ergonomics.

```
+-----------------------------------------------------------------------+
|                             AERIX PIPELINE                            |
+-----------------------------------------------------------------------+
|  1. Source Code (.arx)                                                |
|     |                                                                 |
|  2. Lexer (Scanner)          --> Generates stream of typed Tokens     |
|     |                                                                 |
|  3. Parser                   --> Builds Abstract Syntax Tree (AST)    |
|     |                                                                 |
|  4. Semantic Analyzer        --> Type checking, Scope & Symbol Table, |
|     |                            OOP vtables, Dead-code detection     |
|     |                                                                 |
|  5. C99 Code Generator       --> Emits clean, human-readable C99      |
|     |                            with runtime header (aerix_rt.h)     |
|     |                                                                 |
|  6. Native Linker (GCC)      --> Compiles to optimized native binary   |
|                                  (.exe / ELF) with -O3 -flto          |
+-----------------------------------------------------------------------+
```

---

## 3. Master Directory Structure

The Aerix project is organized into modular directories:

```text
Z:\VSCode\AerixLang\
├── INSTRUCTION.md                 # Master Behavioral Constitution & AI Rules
├── README.md                      # Flagship Project Overview & Quick Tour
├── USER.md                        # Friendly, Simple Guide for Everyday Programmers
├── 00_PROJECT_PLAN.md             # Master Blueprint & Roadmap (This file)
├── 00_QUICK_DEV_CHEATSHEET.md     # Turnkey Developer Cheatsheet (Pratt tables, AST classes, C99 rules)
├── 01_SYNTAX_SPECIFICATION.md     # Full Language Grammar & Syntax Spec
├── 02_COMPILER_PIPELINE.md        # Lexer, Parser, AST, Semantics, Codegen
├── 03_OOP_AND_TYPE_SYSTEM.md      # Classes, Inheritance, Interfaces, VTables
├── 04_RUNTIME_AND_MEMORY.md       # RAII, Memory Model, C Interop, aerix_rt.h
├── 05_STANDARD_LIBRARY_SPEC.md    # Built-in modules (io, math, str, vec, fs)
├── 06_TOOLCHAIN_AND_CLI.md        # arx CLI commands, flags, build options
├── 07_ROADMAP_AND_MILESTONES.md   # Phased execution checklist
├── 08_TEST_AND_BENCHMARK_SPEC.md  # Test vectors & scientific C benchmarks
├── 09_DISTRIBUTION_AND_PACKAGING.md # Global 1-line Installers, Standalone Binary & VSCode Ext
├── arx.bat                        # Windows CMD/PowerShell quick launcher
├── stdlib/                        # Aerix Standard Library & Runtime
│   ├── aerix_rt.h                 # Header-only zero-cost C runtime
│   ├── core.arx                   # Core language primitives
│   ├── io.arx                     # Console and stream I/O
│   ├── math.arx                   # Math utilities & vector math
│   ├── str.arx                    # String manipulation
│   └── vec.arx                    # Dynamic array collections
├── src/                           # ⚡ ALL COMPILER & TOOLCHAIN CODE LIVES HERE
│   ├── arxc.py                    # Standalone Compiler Entrypoint
│   ├── arx.py                     # Developer Toolchain CLI (run, build, doctor, new)
│   ├── frontend/                  # Lexer, Tokens, AST, Pratt Parser
│   │   ├── __init__.py
│   │   ├── tokens.py              # Token definitions & regex patterns
│   │   ├── lexer.py               # Lexical scanner & source coordinates
│   │   ├── ast_nodes.py           # AST hierarchy
│   │   └── parser.py              # Pratt & Recursive Descent Parser
│   ├── middle/                    # Type System, Semantics, AIR, Optimizer
│   │   ├── __init__.py
│   │   ├── typesystem.py          # Static types & inference engine
│   │   ├── semantic.py            # Scoped symbol tables & CHA
│   │   ├── air.py                 # Aerix Intermediate Representation (AIR)
│   │   └── optimizer.py           # Custom optimizer passes (folding, inlining, DCE, devirtualization)
│   ├── backend/                   # Code Generation & Native Linking
│   │   ├── __init__.py
│   │   ├── codegen.py             # AIR-to-C99 machine-target emitter
│   │   └── linker.py              # GCC/Clang linker orchestration
│   ├── driver.py                  # Multi-pass compilation pipeline orchestrator
│   └── tests/                     # Automated Test Suite
│       ├── test_lexer.py
│       ├── test_parser.py
│       ├── test_semantic.py
│       ├── test_codegen.py
│       └── test_integration.py
└── examples/                      # Example Aerix Programs
    ├── 01_hello_world.arx         # Minimal script
    ├── 02_procedural_math.arx     # Procedural mode & pipeline
    ├── 03_oop_bank_account.arx    # OOP classes & encapsulation
    ├── 04_oop_polymorphism.arx    # Interfaces & virtual dispatch
    └── 05_mandelbrot_benchmark.arx# High-performance benchmark
```

---

## 4. Key Paradigms Supported

| Paradigm | How Aerix Implements It |
| :--- | :--- |
| **Procedural ("Normal")** | Standalone functions (`fn`), top-level statements, direct memory manipulation, loops (`for`, `while`, `loop`), clean imperative logic. |
| **Object-Oriented (OOP)** | Classes (`class`), explicit fields with access modifiers (`pub`, `priv`), constructors (`init`), instance methods, destructors (`drop`), interfaces (`trait`), and inheritance. |
| **Functional-Infused** | First-class functions, pipeline chaining operator (`|>`), immutability by default (`let`), pure expression bodies (`=>`). |
| **Systems / Bare Metal** | Explicit pointer access (`*T`, `&mut T`), manual/scoped memory management (`defer free()`), direct C FFI without wrapper overhead. |

---

## 5. Technology Stack Selection

* **Host Compiler Implementation:** Python 3.13 (Native on the machine, clean AST modeling, fast iteration, self-contained with no heavy third-party dependencies required).
* **Target Native Compiler:** GCC 13.2 (MSYS2 installed on path: `gcc.exe`).
* **Runtime:** Zero-dependency ANSI C99 / C11 Header (`aerix_rt.h`).
* **Platform:** Windows (native `.exe`), cross-compilable to Linux and macOS.

---

## 6. Next Steps & Documentation Flow

Every aspect of Aerix is detailed in the accompanying markdown specifications:
- Read **[01_SYNTAX_SPECIFICATION.md](file:///z:/VSCode/AerixLang/01_SYNTAX_SPECIFICATION.md)** for syntax and language examples.
- Read **[02_COMPILER_PIPELINE.md](file:///z:/VSCode/AerixLang/02_COMPILER_PIPELINE.md)** for compiler internal mechanics.
- Read **[03_OOP_AND_TYPE_SYSTEM.md](file:///z:/VSCode/AerixLang/03_OOP_AND_TYPE_SYSTEM.md)** for class and type implementation.
- Read **[04_RUNTIME_AND_MEMORY.md](file:///z:/VSCode/AerixLang/04_RUNTIME_AND_MEMORY.md)** for memory and C-level efficiency.
- Read **[05_STANDARD_LIBRARY_SPEC.md](file:///z:/VSCode/AerixLang/05_STANDARD_LIBRARY_SPEC.md)** for standard modules.
- Read **[06_TOOLCHAIN_AND_CLI.md](file:///z:/VSCode/AerixLang/06_TOOLCHAIN_AND_CLI.md)** for CLI architecture.
- Read **[07_ROADMAP_AND_MILESTONES.md](file:///z:/VSCode/AerixLang/07_ROADMAP_AND_MILESTONES.md)** for execution timeline.
