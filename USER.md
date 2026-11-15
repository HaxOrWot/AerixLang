# Aerix Architecture & Compiler Internals Handbook (`USER.md`)

This document is the **Comprehensive Technical Reference Manual** for developers, systems architects, and compiler engineers seeking an in-depth understanding of how the Aerix compiler toolchain, native code generators, and runtime execute under the hood.

---

## 📑 Technical Index

1. [Architectural Overview & Pipeline Flow](#1-architectural-overview--pipeline-flow)
2. [Frontend: Lexer, Tokens & AST Arena](#2-frontend-lexer-tokens--ast-arena)
3. [Middle-End: Semantic Analysis & Type System](#3-middle-end-semantic-analysis--type-system)
4. [Backend Pipeline A: Direct Native x86-64 Machine Code & PE32+ Emission](#4-backend-pipeline-a-direct-native-x86-64-pe32-emission)
5. [Backend Pipeline B: ANSI C99 Transpiler Engine](#5-backend-pipeline-b-ansi-c99-transpiler-engine)
6. [Win64 ABI Calling Convention & Stack Frame Model](#6-win64-abi-calling-convention--stack-frame-model)
7. [Language Server Protocol (LSP) Daemon Internals](#7-language-server-protocol-lsp-daemon-internals)
8. [Runtime Subsystem Architecture (`aerix_rt.h`)](#8-runtime-subsystem-architecture-aerix_rth)
9. [Toolchain Version Manager & Auto-Updater Design](#9-toolchain-version-manager--auto-updater-design)

---

## 1. Architectural Overview & Pipeline Flow

The Aerix toolchain is a **self-hosting, multi-target compilation engine** written entirely in Aerix itself (`src/bootstrap/**/*.arx`). It supports two primary compilation pathways:

```text
                        ┌───────────────────────────────┐
                        │      Aerix Source (.arx)      │
                        └───────────────┬───────────────┘
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │    Lexer & Tokenizer Stream   │
                        └───────────────┬───────────────┘
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │    Flat Parallel AST Arena    │
                        └───────────────┬───────────────┘
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │   Semantic Analyzer & Types   │
                        └───────┬───────────────┬───────┘
                                │               │
          ┌─────────────────────┘               └─────────────────────┐
          │                                                           │
          ▼ [Backend: Native PE32+]                                   ▼ [Backend: C99 Transpiler]
┌───────────────────────────────┐                           ┌───────────────────────────────┐
│ AMD64 x86-64 Machine Encoder  │                           │ ANSI C99 Source Transpiler    │
└───────────────┬───────────────┘                           └───────────────┬───────────────┘
                │                                                           │
                ▼                                                           ▼
┌───────────────────────────────┐                           ┌───────────────────────────────┐
│ Direct PE32+ Binary Writer    │                           │ GCC Optimization (-O3 -flto)  │
└───────────────┬───────────────┘                           └───────────────┬───────────────┘
                │                                                           │
                └───────────────────────┬───────────────────────────────────┘
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │ Standalone Native Binary (.exe│
                        └───────────────────────────────┘
```

---

## 2. Frontend: Lexer, Tokens & AST Arena

### 2.1 The Flat Parallel AST Arena Model
Traditional compilers represent Abstract Syntax Trees as deeply nested pointer-heavy heap structures (e.g. `Node*`, `unique_ptr<Node>`). This causes cache thrashing, pointer chasing, and heavy memory fragmentation.

Aerix solves this by using a **Flat Parallel List Arena** (`src/bootstrap/frontend/ast.arx`). Every node in the syntax tree is represented simply by a 64-bit integer index (`nid: i64`). Node properties are stored in contiguous, cache-aligned parallel vectors:

* `nk: List<i64>`: Node Kind enum (`NK_FN_DEF`, `NK_LET_STMT`, `NK_CALL`, `NK_IF_STMT`, etc.)
* `sa: List<str>`: Primary string payload (identifier name, variable name, module path)
* `sb: List<str>`: Secondary string payload (type annotation, string literal value)
* `ia: List<i64>`: Primary integer payload (numeric literal value, enum tag)
* `la: List<i64>`: Left-hand child node index
* `ra: List<i64>`: Right-hand child node index
* `ea: List<i64>`: Extra/Else child node index
* `nf: List<str>`: Source file path where this node originated
* `ln: List<i64>`: Source line number
* `ch: List<i64>`: First child node index for block structures

**Benefits:**
* **Contiguous Cache Locality:** Tree traversals iterate over dense arrays with zero pointer indirection.
* **Trivial Serialization:** AST snapshots can be copied or indexed without deep cloning.
* **Instant Deallocation:** Entire compilation arenas are freed in a single continuous block.

---

## 3. Middle-End: Semantic Analysis & Type System

### 3.1 Type Checking & Inference
The Analyzer pass (`src/bootstrap/middle/analyzer.arx`) executes semantic validation over the AST arena:
1. **Scope Stack Resolution:** Maintains lexical visibility scopes with tracking for read, write, and parameter mutation.
2. **Generic Monomorphization:** When generic structures such as `List<T>`, `Map<K, V>`, or `Channel<T>` are instantiated, the analyzer tracks concrete specialization types (`gen_list_types`, `gen_map_keys`). Specializations are generated at compile-time with zero runtime overhead.
3. **Strict Import Scoping:** Tracks:
   * `file_explicit_modules`: Exact module namespaces imported by the active document (`import Window.Gui`).
   * `file_imported_symbols`: Specific symbols imported via selective statements (`from Window.Gui import createWindow`).
   * `file_has_selective_imports`: Marks modules with selective bindings so unimported symbols remain unpolluted.

---

## 4. Backend Pipeline A: Direct Native x86-64 PE32+ Emission

The native backend (`src/bootstrap/backend/native/pe.arx`) generates complete Win64 Portable Executable binaries without requiring an external assembler or linker.

### 4.1 Section Layout
The emitted PE file contains three main sections aligned to 512-byte file boundaries and 4096-byte virtual memory page boundaries:
1. **`.text` (Code Section - Executable & Readable):**
   * Pre-encoded runtime startup routines (`_start`)
   * Built-in machine instructions for memory management, string helpers, and thread routines
   * Monomorphized user functions and methods
2. **`.rdata` (Read-Only Data Section):**
   * Constant string literals
   * Import Directory Table (IDT), Import Lookup Table (ILT), and Import Address Table (IAT)
   * Null-terminated DLL name strings (`kernel32.dll`, `msvcrt.dll`, `ws2_32.dll`)
3. **`.data` (Read-Write Data Section):**
   * Global mutable variables
   * Static thread handles and channel control blocks

### 4.2 Synthetic Relocation & Trampolines
Before serializing machine code, the native linker calculates Relative Virtual Addresses (RVAs) and patches all `CALL` and `JMP` relative offsets (`disp32 = TargetRVA - NextInstructionRVA`). Synthetic trampolines bridge indirect external API calls with the Import Address Table.

---

## 5. Backend Pipeline B: ANSI C99 Transpiler Engine

For maximum portability and production optimizations (`-O3`, `-flto`, `-march=native`), Aerix can transpile AST nodes to standalone, portable ANSI C99 code (`src/bootstrap/backend/emitter.arx`).

* **Struct & Class Layout:** Classes are emitted as C structs with explicit type tags and function pointer tables for virtual method dispatch.
* **Tagged Unions:** Enums with variant payloads compile to typed structs with an integer tag field and a union of variant payload structures.
* **Exception Unwinding:** Implements lightweight hardware stack snapshots (`setjmp`/`longjmp` under the hood) guaranteeing safe execution of `finally` blocks.

---

## 6. Win64 ABI Calling Convention & Stack Frame Model

All functions generated by both backends adhere strictly to the **Microsoft x64 Calling Convention**:

### 6.1 Register Allocation
* **First 4 Integer / Pointer Arguments:** Passed in registers:
  1. `RCX`
  2. `RDX`
  3. `R8`
  4. `R9`
* **First 4 Floating-Point Arguments:** Passed in `XMM0`, `XMM1`, `XMM2`, `XMM3`.
* **Subsequent Arguments:** Pushed onto the stack in right-to-left order above the shadow space.
* **Return Values:** Returned in `RAX` (integers/pointers) or `XMM0` (floating-point).

### 6.2 The 32-Byte Shadow Space (Homing Space)
The caller **must** allocate 32 bytes of shadow space immediately before executing a `CALL` instruction, regardless of the number of parameters passed:

```text
Higher Memory
┌───────────────────────────────┐
│ Argument 5, Argument 6, ...   │
├───────────────────────────────┤
│ Shadow Space (32 bytes)       │  <- RSP + 0 to RSP + 31 (reserved for RCX, RDX, R8, R9)
├───────────────────────────────┤
│ Return Address (8 bytes)      │  <- Pushed automatically by CALL
├───────────────────────────────┤
│ Saved RBP (8 bytes)           │  <- Function Prologue: push rbp; mov rbp, rsp
├───────────────────────────────┤
│ Local Variables               │  <- Allocated via: sub rsp, LocalFrameSize
└───────────────────────────────┘
Lower Memory (RSP must be 16-byte aligned before any nested call)
```

---

## 7. Language Server Protocol (LSP) Daemon Internals

The Aerix Language Server (`src/bootstrap/lsp/server.arx`) runs as a persistent background daemon:

* **Transport:** Standard input/output via JSON-RPC 2.0 with `Content-Length` framing.
* **Virtual Document Overlay:** Keeps an in-memory map of open editor buffers (`textDocument/didChange`). Diagnostics and completions analyze the virtual buffer without requiring files to be saved to disk.
* **Semantic Token Engine:** Emits full 5-tuple encoded semantic token streams (`lineDelta`, `colDelta`, `length`, `tokenType`, `tokenModifiers`) directly from the parsed AST.
* **Context-Ranked Completions:** Prioritizes locally scoped symbols (`0_name`), member fields (`1_field`), imported symbols (`1a_sym`), and modules (`1b_mod`), while filtering out unimported namespaces.

---

## 8. Runtime Subsystem Architecture (`aerix_rt.h`)

The core runtime is encapsulated in a zero-dependency header (`stdlib/aerix_rt.h`):

1. **Memory Allocation:**
   * Uses low-overhead, aligned system allocators.
   * Provides linear arenas (`LinearArena`) for zero-fragmentation batch allocations in compilers and short-lived tasks.
2. **String Model:**
   * UTF-8 length-prefixed strings (`char* data`, `int64_t len`).
   * Slicing is zero-copy where possible, avoiding unnecessary allocations.
3. **Concurrency Subsystem:**
   * Threads are mapped directly to native OS threads via `CreateThread` on Windows or `pthread_create` on POSIX.
   * Channels are circular ring buffers guarded by slim reader-writer locks or critical sections with condition variables for non-spinning blocking waits.

---

## 9. Toolchain Version Manager & Auto-Updater Design

Aerix features an integrated toolchain management architecture:

* **Zero-Privilege User Toolchains:** Stored in `%LOCALAPPDATA%\Programs\Aerix` with version snapshots cached in `cache/vX.Y.Z/`.
* **Atomic Switching:** The Version Manager updates the `bin\arx.exe` symlink or binary copy, enabling instantaneous switching between compiler revisions without registry locks.
* **Background Updater:** When configured, checks the GitHub Releases API asynchronously and prompts non-intrusively when a new stable toolchain is available.

---

*Aerix Core Engineering Team — Built for Uncompromising Performance.*
