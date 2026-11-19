# Aerix Language & IntelliSense Support (`v3.2.0-beta.1`)

<div align="center">

<img src="./icons/aerix-icon.png" width="128" height="128" alt="Aerix Logo" />

[![Version](https://img.shields.io/badge/version-3.2.0--beta.1-00DCFF.svg?style=for-the-badge&logo=visualstudiocode)](#)
[![Release Channel](https://img.shields.io/badge/channel-beta-blue.svg?style=for-the-badge)](#)
[![Language](https://img.shields.io/badge/language-Aerix%20(.arx)-1E90FF.svg?style=for-the-badge)](#)
[![LSP Engine](https://img.shields.io/badge/LSP-Compiler%20Driven%20(JSON--RPC)-7C4DFF.svg?style=for-the-badge)](#)
[![Architecture](https://img.shields.io/badge/arch-x86__64--windows-orange.svg?style=for-the-badge)](#)

**The official Visual Studio Code & Antigravity IDE extension for Aerix (`.arx`). Powered directly by the self-hosting native compiler daemon (`arx lsp`) for ultra-responsive semantic analysis, context-ranked autocompletions, strict import scoping, hover docs, parameter hints, cross-file Go-to-Definition, live diagnostics, integrated toolchain version manager, and one-click execution.**

</div>

---

## 🚀 Key Highlights & New in v3.2.0-beta.1

- **Compiler Escape Analysis & Stack-Allocated Structs:** Non-escaping struct value types (`struct Vec3 { ... }`) are allocated directly in local stack frames with zero heap allocation (`calloc`) and zero ARC overhead. Returning or escaping instances cleanly transition to heap storage.
- **Cache-Line Alignment Attributes (`#[align(64)]`):** Prevent multi-core false sharing on concurrent ring buffers, queues, and thread-shared state by aligning fields to hardware L1 cache-line boundaries.
- **Compile-Time Constant Folding:** Fast evaluation in AST analysis pass folds constant arithmetic, string concatenations, and boolean logic directly during compilation.
- **Call Stack Backtrace on Panic & Uncaught Exceptions:** Frame-pointer stack walking prints full call chains with frame indexes and return addresses upon runtime panics or uncaught exceptions across both native and ANSI C99 backends.
- **Deep Recursion 16MB Stack Commitment:** Expanded PE stack commit and reserve to 16 MB, completely preventing stack guard page faults during deep compiler recursions and AST walks.
- **Hardware-Direct Multi-Threading & Atomics (`Sync`, `Thread`):** Direct x86-64 `LOCK CMPXCHG` and `LOCK XADD` instructions, Win32 `CreateThread` worker spawning, `ThreadHandle.join()`, and low-latency spin-guards (`SpinLock`).
- **Thread-Local Scratch Arenas (`TLSArena`):** Instant sub-nanosecond pointer-bump memory allocation with zero lock contention and $O(1)$ zero-cost reset.
- **Bit-for-Bit Self-Hosting Convergence:** Fully validated 4-stage self-hosting compiler (`stage3` compiling `stage4` with identical SHA256 checksums).
- **Dynamic Interactive Snippets:** Instant expansions for `if`, `ifelse`, `for`, `for_in`, `while`, `match`, `guard`, `try`, `spawn`, `defer`, `fn`, `pub_fn`, `struct`, `class`, `enum`, `trait`, and `test`.
- **Call Parameter Inlay Hints:** Call-site argument names automatically rendered (`kind: 2`) with smart suppression for identical argument names.
- **Hierarchical Outline & Breadcrumbs:** Document symbols with full block range calculation for smooth code navigation.
- **Instant Demand-Driven IntelliSense & Spatial AST Indexing:** Pre-indexed scoped symbols and binary-search spatial node lookup replace flat full-AST iterations, accelerating completions, hovers, and Go-to-Definition queries by up to 1,000x.
- **Incremental Document Synchronization (`textDocumentSync: 2`):** Character-delta range splicing eliminates redundant full-file IPC re-transfers, providing sub-millisecond editor responsiveness with snappier diagnostics.
- **Multi-Document Tab-Switching LRU Cache:** Retains in-memory semantic analysis states across open files, making tab switches and cross-file navigation instantaneous with zero re-parsing lag.
- **Polished Automatic Reference Counting (ARC) & RAII Scope Drops:** Hardware-level atomic refcounting (`lock inc/dec`), sub-microsecond null/range safety checks, zero-leak string interpolation and compound assignments (`+=`), and balanced list/map operations.
- **Strict Module & Import Scoping:**
  - `import Window`: Imports the full `Window` namespace and all submodules.
  - `import Window.Gui`: Imports specifically the `Window.Gui` submodule (alias `Gui`). Parent namespace `Window` remains unimported and unpolluted.
  - `from Window.Gui import createWindow`: Strictly imports only `createWindow` (and case-variant `CreateWindow`). Autocompletion suggestions in the file only expose the imported symbol(s), preventing symbol pollution.
  - `from Window.Gui import <cursor>`: Context-aware suggestions listing all functions, classes, and structs exported by `Window.Gui`.
- **Zero-Dependency Native Compiler:** Directly compiles `.arx` sources into standalone PE32+ x86-64 native executables without needing GCC, Clang, or external toolchains.
- **Integrated Toolchain Version Manager:** Switch between installed toolchain versions (`>= 1.1.3b` up to `3.0.0-beta.4`) or install new releases on-the-fly directly from the status bar (`$(versions) Aerix`).
- **Silent & Prompted Auto-Updates:** Seamless background checking against GitHub Releases with non-intrusive notification prompts and auto-restarting LSP daemon.
- **Dual-Layer Highlighting:** Instant TextMate grammar baseline (`aerix.tmLanguage.json`) combined with compiler-accurate LSP Semantic Tokens.

---

## ⚡ Features Overview

| Capability | Description |
| :--- | :--- |
| **Dual-Layer Highlighting** | Zero-delay TextMate grammar coloring plus sub-millisecond semantic tokenization distinguishing `let` vs `mut`, constants, doc-comments, enum variants, and interpolated strings. |
| **Ranked IntelliSense** | Scoped completions: local variables & parameters first, same-file declarations, selectively imported symbols, explicit modules, built-in runtime types, and context-ranked keywords. |
| **Live Signature Help** | Multi-parameter tooltip assistance inside `(...)` with active parameter highlights, types, and parameter documentation. |
| **Hover Documentation** | Rich Markdown hovers with full type signatures, extracted `///` doc-comments, and clickable `*Defined at* [file:line]` source navigations. |
| **Code Navigation** | `F12` Go-to-Definition, `Ctrl+F12` Go-to-Type-Definition, and `Ctrl+Shift+O` Document Symbol Outline tree. |
| **Live Non-Blocking Diagnostics** | Compiler diagnostics streamed smoothly (`120ms` on file open, `650ms` while typing, instant on save). |
| **One-Click Native Run** | CodeLens `▶ Run Program` button directly above `fn main()` runs your code instantly in a dedicated terminal. |
| **Document Formatter** | Built-in source formatter triggered via `Shift+Alt+F` adhering to official Aerix code conventions. |

---

## 📦 Import Scoping Examples

### 1. Selective Symbol Import
```aerix
from Window.Gui import createWindow

fn main() {
    // Only 'createWindow' is exposed in completions!
    // 'Window' and unimported GUI widgets ('Button', 'TextBox') are strictly excluded.
    let win = createWindow("My App", 800, 600)
}
```

### 2. Specific Submodule Import
```aerix
import Window.Gui

fn main() {
    // 'Window.Gui' and 'Gui' are exposed.
    // Parent namespace 'Window' is not imported.
    let win = Gui.createWindow("Submodule Only", 640, 480)
}
```

### 3. Full Namespace Import
```aerix
import Window

fn main() {
    // Full module 'Window' and submodules are accessible.
    let win = Window.Gui.createWindow("Full Namespace", 800, 600)
}
```

---

## ⌨️ Shortcuts & Commands

| Action / Shortcut | Command Identifier | Description |
| :--- | :--- | :--- |
| `Ctrl+Space` | `editor.action.triggerSuggest` | Trigger context-aware autocompletions |
| `Ctrl+Shift+Space` | `editor.action.triggerParameterHints` | Trigger active signature parameter hints inside `(...)` |
| `F12` | `editor.action.revealDefinition` | Jump to definition across local scopes and imported modules |
| `Ctrl+Shift+O` | `workbench.action.gotoSymbol` | Navigate document symbol outline (classes, functions, enums) |
| `Shift+Alt+F` | `editor.action.formatDocument` | Format active `.arx` source file |
| `Ctrl+F5` / CodeLens `▶` | `aerix.runFile` | Build and run the active file (`arx run "<file>"`) |
| Command Palette | `aerix.checkFile` | Parse, type-check, and validate without executing |
| Command Palette | `aerix.switchVersion` | Open interactive Toolchain Version Manager |
| Command Palette | `aerix.checkUpdates` | Check GitHub for latest stable Aerix releases |

---

## 🧩 Built-In Code Snippets

| Snippet Prefix | Description / Expansion |
| :--- | :--- |
| `main` | Entrypoint `fn main() { ... }` with CodeLens runner |
| `fn` / `fn_expr` | Standard typed function or expression-body arrow function |
| `struct` | Data structure declaration with typed fields and `init()` |
| `class` | Object-oriented class with encapsulated fields and methods |
| `enum` | Tagged enum with variant types and matching support |
| `for` / `for_in` | Numeric range loop (`for i in 0..10`) or iterator loop |
| `guard` / `defer` | Early-exit condition check or deferred LIFO cleanup block |
| `spawn` | Native thread spawn block (`let th = spawn { ... }`) |
| `import` / `from` | Scoped module import statements |

---

## ⚙️ Configuration

Open your VS Code or Antigravity Settings (`Ctrl+,`) and search for **Aerix**:

```json
{
  // Path to the Aerix compiler/LSP binary (arx / arx.exe).
  // Leave empty for automatic multi-path discovery.
  "aerix.executablePath": "",

  // GitHub update checking behavior: "auto" | "prompt" | "off"
  "aerix.autoUpdate": "auto"
}
```

### Binary Auto-Detection Priority
When `aerix.executablePath` is not explicitly set, the extension automatically looks for `arx.exe` in:
1. `AERIX_HOME\bin\arx.exe`
2. `%LOCALAPPDATA%\Programs\Aerix\bin\arx.exe`
3. `C:\Aerix\bin\arx.exe` / `C:\Aerix\arx.exe`
4. `~/.aerix/bin/arx.exe`
5. System `PATH` environment variable

---

## 🛠️ Installation & Updating

### Install from VSIX
```powershell
code --install-extension aerix-3.0.0.vsix --force
```

### Install in Antigravity IDE
```powershell
antigravity --install-extension aerix-3.0.0.vsix --force
```

> **Tip:** After installing or switching compiler versions, run **`Developer: Reload Window`** (`Ctrl+Shift+P` -> `Reload Window`) to reconnect the LSP server cleanly.

---

<div align="center">
Made with ❤️ for the Aerix Programming Language Community
</div>
