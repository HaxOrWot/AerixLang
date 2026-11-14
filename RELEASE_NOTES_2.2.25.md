# Aerix v2.2.25-stable: Zero-Dependency Native x86-64 Machine Code Generation & Direct PE32+ Engine

**Release Date:** November 14, 2026  
**Channel:** Stable  
**Version:** `2.2.25-stable` (Major Milestone Transition from `v1.2.24b`)  
**Target Architecture:** `x86_64-pc-windows-msvc` / Win64 PE32+  

---

## 🌟 Executive Summary

Aerix **v2.2.25-stable** marks the most monumental architectural milestone in the history of the Aerix programming language. With this release, Aerix graduates from an ANSI C99 transpiler into a **fully autonomous, self-hosting, zero-dependency systems programming language toolchain**. 

Aerix now generates **native AMD64/x86-64 machine instructions** directly from the compiler's Abstract Syntax Tree and emits structured, valid **Win64 PE32+ (Portable Executable) binary executables** directly to disk — **requiring zero external C compilers, zero GCC/Clang installations, zero MinGW toolchains, and zero external assemblers or linkers**.

---

## 🚀 Key Major Features & Innovations

### 1. Zero-Dependency Native x86-64 PE32+ Code Generation
- **Direct PE Binary Synthesis (`pe.arx`)**: Emits complete DOS headers, PE headers, COFF section headers (`.text`, `.rdata`, `.data`), export/import directories, and relative relocation tables without relying on external system linkers.
- **Pure Win64 ABI Compliance**:
  - 16-byte stack frame alignment prior to function invocations.
  - 32-byte preallocated shadow space across all external and internal calls.
  - Standard register parameter passing: `RCX`, `RDX`, `R8`, `R9` for integers/pointers; `XMM0`–`XMM3` for floating-point values.
  - Callee-saved register preservation (`RBP`, `RBX`, `RDI`, `RSI`, `R12`–`R15`).
- **x86-64 SIB & Displacement Correction**: Native byte encoder fix for complex stack and pointer displacements, resolving ModR/M addressing across dynamically-sized local stack frames.

### 2. Built-in Pure x86-64 Runtime (`runtime.arx`)
- Zero external runtime requirement: all core language primitives are encoded directly into the `.text` section of every emitted executable.
- Builtin memory allocators, string manipulation, and UTF-8 console output routines with Windows codepage initialization (`SetConsoleOutputCP(65001)`).
- Direct IAT (Import Address Table) synthesis binding dynamic imports to `kernel32.dll`, `msvcrt.dll`, and `ws2_32.dll`.

### 3. Native Structured Exception Handling (`try` / `catch` / `finally` / `throw`)
- Pure x86-64 hardware stack unwinding implementation:
  - `__rt_try_push`: Non-destructive caller environment preservation (`RSP`, `RBP`, `RBX`, `R12`–`R15`, and return `RIP`) on a thread-safe execution stack.
  - `__rt_try_pop`: Normal-path unwinding upon clean block completion.
  - `__rt_throw`: Instantaneous multi-frame register restoration and RIP redirection with dynamic exception message payload passing in `RAX`.
- Guaranteed `finally` block execution across both normal exit paths and handled exceptions.

### 4. Native Built-in Generic Collections & Data Structures
- **`Queue<T>` and `Deque<T>`**: Ring-buffered high-performance double-ended queues with `enqueue`, `dequeue`, `peek`, `len`, `is_empty`, `clear`, and `free`.
- **`Stack<T>`**: LIFO stack wrappers with fast pointer updates and peak inspection.
- **`List<T>`**: Dynamic growable arrays with bounds safety.
- **`Map<K, V>` and `Set<T>`**: Native hash map and set implementations supporting string and integer keys.
- **Tuples**: Direct heap-allocated heterogeneous tuple expressions and destructuring (`let (a, b) = packet`).

### 5. Retroactive Type Extensions (`extend <Type>`)
- The native PE backend now fully analyzes and emits retroactive type extensions (`NK_EXTEND_DEF`).
- Developers can declare methods on existing structs, external types, and primitives outside the original type declaration:
  ```aerix
  extend Vector2D {
      pub fn manhattan_distance() -> i64 {
          return self.x.abs() + self.y.abs()
      }
  }
  ```

### 6. Universal Synthetic Trampoline Resolver
- Resolves all polymorphic method calls and collection monomorphizations right before PE serialization.
- Eliminates linker errors or unresolved label references when mixing complex collections and user-defined structs.

### 7. Language Safety & Assertion Engine
- Added native machine implementations of `assert()` and `assert_eq()`.
- Assertion failures print human-readable diagnostic messages to `stderr` and safely terminate with non-zero exit codes.
- Added native dispatch for `panic()`, `abort()`, `exit()`, and command-line argument queries via `Env.arg()`.

---

## 📊 Verification & Test Suite Matrix

Every core language feature has been verified on the native backend with **100% pass rates**:

| Category | Test Suite / Benchmark | Native PE Execution Status |
| :--- | :--- | :---: |
| **Object-Oriented Programming** | Class hierarchies, constructors, overloading, properties, guards | **PASS** |
| **Type Extensions** | `extend` method emission, retroactive symbol binding | **PASS** |
| **Tagged Unions** | Pattern matching, payload extraction, enum singletons | **PASS** |
| **Generic Collections** | `List`, `Stack`, `Queue`, `Deque`, `Map`, `Set`, `Tuple` | **PASS** |
| **Exception Handling** | `try / catch / finally / throw` stack unwinding | **PASS** |
| **Low-Level Systems** | Sockets, non-blocking I/O, `ByteBuffer`, File I/O | **PASS** |
| **Algorithms** | MergeSort, QuickSort, Circular Linked List | **PASS** |
| **Interactive Applications** | Snake Game, High-Performance TCP Server v1.0 | **PASS** |

---

## 🛠️ Installation & Upgrading

### Direct Binary Download / Channel Switch
To upgrade your active Aerix installation to `v2.2.25-stable`:

```powershell
# Using the Aerix Version Manager
arx vm use stable
# Or install explicitly
arx vm install 2.2.25-stable
```

### Self-Hosting Bootstrap Build from Source
```powershell
# In AerixLang directory
arx emit-c src/bootstrap/main.arx -o src/bootstrap/seed/arxc.c
gcc -O2 -mconsole -Istdlib src/bootstrap/seed/arxc.c -o arx.exe
```

---

*Aerix Core Team — Systems Programming at the Speed of Light.*
