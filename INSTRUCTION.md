# Aerix (arx) — Master Instruction & Behavioral Constitution

> **Status:** Permanent Mandatory Operational Directives  
> **Target:** Antigravity AI Assistant & Aerix Engineering Team  
> **Axiom:** Follow these rules strictly on EVERY task, prompt, and iteration without exception.

---

## 1. Golden Operational Rules

### 1.1 Dedicated `src/` Folder Structure
- **ALL code must be created and built inside `z:\VSCode\AerixLang\src\`**:
  The compiler, AST, parser, optimizer, codegen, runtime wrappers, and tests must live exclusively inside `src/`.
- **NEVER move `.md` files into `src/`**:
  All specification files (`00` through `09`) are located in `docs/` (`z:\VSCode\AerixLang\docs\`), while `README.md`, `USER.md`, and `INSTRUCTION.md` remain in the project root (`z:\VSCode\AerixLang\`).

### 1.2 Keep Everything Updated (Zero Stale State)
- **Always update all relevant files synchronously**:
  When a feature, AST node, token, command, or pass is added or modified, update:
  1. The code in `src/`.
  2. The corresponding specification files in `docs/` (`00` through `11`).
  3. The **Live Implementation Status Table in [README.md](file:///z:/VSCode/AerixLang/README.md)**.
  4. The milestone checklist in **[docs/07_ROADMAP_AND_MILESTONES.md](file:///z:/VSCode/AerixLang/docs/07_ROADMAP_AND_MILESTONES.md)**.
  5. The beginner guide in **[USER.md](file:///z:/VSCode/AerixLang/USER.md)**.
  6. The master reference manual in **[GUIDE.md](file:///z:/VSCode/AerixLang/GUIDE.md)**.

### 1.3 Critical Thinking — Never Blindly Agree ("No Yes-Man")
- **Sanity check every instruction first**:
  Before executing, check if the request is already implemented, contradicts the core design, creates redundancy, or can be improved.
- If something is flawed, suboptimal, or already exists, point it out upfront with technical facts and offer the optimal solution.

### 1.4 User-Reported Errors Are Priority #1
- If the user reports an error, glitch, or unexpected behavior in their environment, **listen immediately and treat it as absolute truth**.
- Investigate the root cause directly, do not dismiss it with "it works on paper", and resolve it completely.

### 1.5 Always Keep Everything TOP-NOTCH
- **Zero compromises on quality**:
  No sloppy placeholders, no half-baked solutions, no "TODO: implement later" for critical paths.
  Every module, test vector, and document must be textbook-grade, enterprise-ready, and production-clean.

### 1.6 Wait for the "Start" Command
- Do not jump ahead and start writing compiler code until the user explicitly commands to **"Start"**.

### 1.7 Aerix 2.0 Invariants & Zero-Cost Abstractions
- **Symbol Mangling Invariant**: Methods and constructors must NEVER overwrite each other in the symbol tables. Use static name mangling (`Arx_Class_method__<types>`) to support full arity and type overloading.
- **Zero Runtime Overhead**: Resolve all overloads, named inits, and properties at compile time during semantic analysis. Generated C99 code must contain direct function calls with 0 virtual dispatch when types are statically known.
- **Cache-Line Alignment**: Optimize struct definitions in descending alignment order ($8 \rightarrow 4 \rightarrow 2 \rightarrow 1$ bytes) to maximize CPU L1 cache utilization.

---

## 2. Aerix Language Core Identity

1. **Name:** **Aerix** (`.arx` / `arx`).
2. **Speed:** 100% native C/C++ execution speed (compiled to machine code via GCC `-O3` / zero-cost C99 emission, zero VM, zero GC pauses).
3. **Dual-Paradigm & Modern Ergonomics:**
   - **Procedural / Scripting:** Top-level functions (`fn`), expressions (`=>`), pipeline operator (`|>`), zero boilerplate.
   - **Full-Spectrum OOP:** Classes (`class`), method/ctor overloading, named inits (`init.<variant>`), reactive properties (`prop`), operator overloading (`pub op`), single inheritance (`:`), and zero-cost type extensions (`extend`).
   - **Control Flow:** Anti-pyramid guard clauses (`guard ... else`), fluent cascade mutation (`~>`), and tagged unions with exhaustive matching (`enum` + `match`).
4. **Custom Compiler Engine (`arxc`):**
   - A dedicated multi-pass compiler with:
     - Frontend: Lexer & 14-level Pratt Parser.
     - Middle-End: Static Type Checker, **Aerix Intermediate Representation (AIR)**, and Custom Optimizer (`arxc-opt`: constant folding, devirtualization, inlining, DCE, defer lowering).
     - Backend: Machine-target code generator & native GCC linker.
5. **Global Distribution & Tooling:**
   - Standalone `arx.exe` (no Python needed by end users).
   - Universal 1-line installers for Windows, Linux, and macOS.
   - Built-in `arx doctor` and `arx new`.
   - Official VS Code & Antigravity IDE syntax highlighting and language tooling extension.

---

## 3. Directory Layout Blueprint

```text
Z:\VSCode\AerixLang\
├── INSTRUCTION.md                 # This File (Permanent AI Directive)
├── README.md                      # Flagship Project Overview & Live Progress Status
├── USER.md                        # Simple, Friendly Guide for Everyday Programmers
├── GUIDE.md                       # Comprehensive Definitive Reference Manual
├── docs/                          # 📚 Architectural Specifications & Blueprints
│   ├── 00_MASTER_PLAN_50000X.md       # Master 4-Pillar Architectural Foundation & Roadmap
│   ├── 00_PROJECT_PLAN.md             # Master Architecture, Directory Layout & Tech Stack
│   ├── 00_QUICK_DEV_CHEATSHEET.md     # Turnkey Token Regexes, Pratt Table, AST Classes
│   ├── 01_SYNTAX_SPECIFICATION.md     # Full EBNF Grammar & Language Rules
│   ├── 02_COMPILER_PIPELINE.md        # 6-Stage Pipeline, AIR Specs & Optimizer Passes
│   ├── 03_OOP_AND_TYPE_SYSTEM.md      # Classes, VTables, Mangling & Memory Layout
│   ├── 04_RUNTIME_AND_MEMORY.md       # Zero-Cost Memory, Cache Packing & Linear Arenas
│   ├── 05_STANDARD_LIBRARY_SPEC.md    # Modules: math, io, vec, str, time, fs
│   ├── 06_TOOLCHAIN_AND_CLI.md        # arx CLI Commands, Flags, GCC Orchestration
│   ├── 07_ROADMAP_AND_MILESTONES.md   # Phased TDD Milestones & Exit Criteria
│   ├── 08_TEST_AND_BENCHMARK_SPEC.md  # Test Vectors, Mandelbrot & Fibonacci Benchmarks
│   ├── 09_DISTRIBUTION_AND_PACKAGING.md # Global Installers, Standalone Binary & VSCode Ext
│   ├── 10_ADVANCED_INTELLISENSE_AND_LSP_SPEC.md # LSP Architecture, Inlay Hints & Profiling
│   └── 11_UNIQUE_OOP_AND_MODERN_LANGUAGE_FEATURES.md # Overloading, Inits, Properties, Guard, Cascade
├── stdlib/                        # Pre-Built Zero-Cost Runtime
│   └── aerix_rt.h                 # Verified ANSI C99 Runtime Header
└── src/                           # ⚡ THE ENTIRE COMPILER CODEBASE LIVES HERE
    ├── arxc.py                    # Standalone Compiler Entrypoint
    ├── arx.py                     # Developer Toolchain CLI (run, build, doctor, new)
    ├── frontend/                  # Lexer, Tokens, AST, Pratt Parser
    ├── middle/                    # Type System, Semantics, AIR, Optimizer (arxc-opt)
    ├── backend/                   # AIR-to-C99 Codegen & GCC Linker
    ├── driver.py                  # Multi-Pass Compilation Pipeline Driver
    └── tests/                     # Automated Unit & Integration Tests
```
