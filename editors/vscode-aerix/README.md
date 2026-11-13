# Aerix Language & IntelliSense Support (`v1.2.22b`)

<div align="center">

<img src="./icons/aerix-icon.png" width="120" height="120" alt="Aerix Logo" />

[![Version](https://img.shields.io/badge/version-1.2.22b-00DCFF.svg?style=for-the-badge&logo=visualstudiocode)](#)
[![Language](https://img.shields.io/badge/language-Aerix%20(.arx)-1E90FF.svg?style=for-the-badge)](#)
[![LSP](https://img.shields.io/badge/LSP-Native%20Compiler%20Driven-7C4DFF.svg?style=for-the-badge)](#)

**Official language support for Aerix (`.arx`) powered directly by the self-hosting `arx lsp` server — instant TextMate + compiler semantic highlighting, ranked context-aware IntelliSense, rich Markdown hover documentation, live signature help, `F12` Go-to-Definition, inlay hints, document formatting, and one-click native x64 execution.**

</div>

---

## Features at a Glance

| Capability | Description |
| :--- | :--- |
| **Dual-Layer Syntax Highlighting** | Instant [aerix.tmLanguage.json](./syntaxes/aerix.tmLanguage.json) baseline colors refined in milliseconds by compiler-driven LSP Semantic Tokens (`arx lsp`). |
| **Rich Hover Documentation** | Typed signatures, extracted `///` / `//` doc comments, clickable source links (`file:line`), builtin signatures, keyword docs, class members, and enum variants. |
| **Ranked IntelliSense** | Prioritized completions: locals/parameters first, then same-file declarations, imported project symbols, static stdlib modules, builtins, types, and keywords. |
| **Chained & Cascade Completions** | Type-aware member suggestions across `.`, `?.`, `~>` cascades, chained calls (`list.get(0).`, `s.trim().`), `Enum.` variants, and `extend` methods. |
| **Live Signature Help** | Multi-line active parameter highlighting with documentation for user functions, constructors, methods, container methods, and runtime builtins. |
| **Navigation & Refactoring Tools** | `F12` Go-to-Definition across imports/modules/members, `Ctrl+F12` Go-to-Type-Definition, `Ctrl+Shift+O` Outline Tree, Inlay Type Hints, and `Shift+Alt+F` Formatting. |
| **One-Click Native Build & Run** | CodeLens `▶ Run Program` above `fn main()` compiles via the built-in PE32+ x86-64 native backend on Windows with zero external C compiler dependencies. |

---

## 1. Syntax Highlighting

Aerix combines two complementary layers:
1. **TextMate Grammar (`syntaxes/aerix.tmLanguage.json`)**: Zero-delay coloring on file open, search previews, diffs, and Markdown ` ```aerix ` code fences.
2. **Compiler Semantic Tokens (`arx lsp`)**: Context-accurate tokens differentiating:
   - Immutable bindings (`let`, `const`, non-`mut` parameters) vs mutable locals (`mut`)
   - Doc comments (`///`, `//!`, `/**`) vs regular comments
   - Declarations vs call sites for functions, methods, classes, structs, traits, enums, and generic type parameters (`<T>`)
   - Enum variants (`Status.Active`), static runtime namespaces (`File`, `Directory`, `Env`, `Process`, `Math`, `Random`), attributes (`#[...]`), and expressions embedded inside string interpolation (`"val = {x.len()}"`)
   - Fluent cascade (`~>`) and pipeline (`|>`) operators

---

## 2. Hover, Go-to-Definition (`F12`), & Diagnostics

- **Hover (`Ctrl+K Ctrl+I` or mouse hover):**
  - Displays typed code blocks, `///` / `//` doc comments above declarations, and clickable `*Defined at* [file:line]` links.
  - Works on locals, parameters, `for` variables, `self` / `super`, class fields & inherited methods, chained calls (`a.b().c`), cascade calls (`obj~>step()`), enums & variants, import paths, keywords, primitives, and runtime builtins (`println`, `File.read_to_string`, `List.push`, `Math.sqrt`, etc.).
- **Navigation:**
  - **`F12` (Go to Definition):** Jumps to local/global declarations, functions, classes, enums, variants, fields, methods, or imported `.arx` files.
  - **Go to Type Definition:** Jumps straight to the class/enum declaration of any typed expression or variable.
  - **`Ctrl+Shift+O` (Document Outline / Breadcrumbs):** Lists classes (with nested fields, constructors, methods), enums (with variants), globals, and functions.
- **Non-Blocking Live Diagnostics:**
  - Compiler errors publish smoothly (`120ms` on file open, `650ms` idle while typing, immediate on save) without blocking highlighting responsiveness.

---

## 3. Keyboard Shortcuts & Commands

| Shortcut / Action | Command |
| :--- | :--- |
| `Ctrl+Space` | Trigger context-aware completions |
| `Ctrl+Shift+Space` | Trigger parameter signature help inside `(...)` |
| `F12` | Go to Definition (including cross-file imports) |
| `Ctrl+Shift+O` | Jump to symbol in Document Outline |
| `Shift+Alt+F` | Format active `.arx` document |
| CodeLens / Editor Title Run (`▶`) | `Aerix: Run Aerix Program` (`arx run "<file>"`) |
| Command Palette | `Aerix: Check Syntax & Types` (`arx check "<file>"`) |
| Command Palette | `Aerix: Compile to WebAssembly (WASM)` (`arx wasm "<file>" --wat --html`) |
| Command Palette | `Aerix: Run WebAssembly in Browser (Live)` (`arx wasm "<file>" --serve`) |

---

## 4. Built-In Snippets

| Prefix | Expands To | Prefix | Expands To |
| :--- | :--- | :--- | :--- |
| `main` | `fn main() { ... }` | `class` | `class Name { init(...) }` |
| `fn` | `fn name(params) -> i64 { ... }` | `struct` | `struct Name { pub field: i64 }` |
| `fn_expr` | `fn name(params) -> i64 => expr` | `enum` | `enum Name { Variant1, Variant2(...) }` |
| `fn_generic` | `fn name<T>(arg: T) -> T` | `trait` | `trait Name { fn ... }` |
| `let` / `mut` | `let name = ...` / `mut name = ...` | `extend` | `extend Type { pub fn ... }` |
| `for` / `for_in` | Range (`0..10`) / collection loop | `prop` | Reactive `prop` getter |
| `if` / `ifelse` | Conditional blocks | `match` | Exhaustive pattern match |
| `guard` / `defer` | Early guard / LIFO cleanup | `try` | `try { ... } catch err { ... }` |
| `import` | `import "./module.arx"` | `doc` | `///` doc comment block |
| `spawn` / `channel` | Thread spawn / bounded channel | `test` | `#[test] fn test_...()` |

---

## 5. Configuration & Binary Resolution

Set **`aerix.executablePath`** in VS Code / Antigravity Settings if you want to point to a custom `arx` binary. When left empty, the extension auto-detects `arx` in order:
1. `AERIX_HOME\bin\arx.exe` (`arxc.exe`)
2. `%LOCALAPPDATA%\Programs\Aerix\bin\arx.exe` (default Windows installer path)
3. `~/.aerix/bin/arx.exe`
4. `arx` on your system `PATH`

### Manual VSIX Installation

```powershell
code --install-extension aerix-1.2.22b.vsix --force
antigravity --install-extension aerix-1.2.22b.vsix --force
```

After updating the extension or `arx.exe`, run **`Developer: Reload Window`** (`Ctrl+Shift+P`) to restart the language server cleanly.
