# Aerix Language Support for Visual Studio Code

<div align="center">

<img src="./icons/aerix-icon.png" width="128" height="128" alt="Aerix Logo" />

# ⚡ Aerix 1.0.90 VS Code IntelliSense & Language Tooling

[![Version](https://img.shields.io/badge/version-v1.0.90-00DCFF.svg?style=for-the-badge&logo=visualstudiocode)](#)
[![Language](https://img.shields.io/badge/language-Aerix%20(.arx)-1E90FF.svg?style=for-the-badge)](#)
[![Tests](https://img.shields.io/badge/test%20suite-138%2F138%20PASS-00E676.svg?style=for-the-badge)](#)
[![Status](https://img.shields.io/badge/IntelliSense-SUPERCHARGED-7C4DFF.svg?style=for-the-badge)](#)

**The official, ultra-high-performance language extension for Aerix (`.arx`) — High-precision TextMate syntax highlighting, intelligent context-aware completions, real-time struct memory layout diagnostics, multi-threaded signature assistance, WebAssembly compilation & live browser preview, and native compilation integration.**

</div>

---

## 🌟 Overview

The **Aerix VS Code Extension** transforms Visual Studio Code into a world-class Integrated Development Environment (IDE) tailored specifically for modern systems programming in Aerix. Built with zero external dependencies and fine-tuned for instantaneous response times, the extension provides deep static analysis directly as you type.

---

## ⚡ Key Capabilities at a Glance

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    AERIX VS CODE INTELLISENSE SUITE                          │
├─────────────────────┬──────────────────────────┬─────────────────────────────┤
│ 💡 Smart Completion │ 🔍 Precision Hover       │ 📊 Struct Memory Visualizer │
│ Contextual fields,  │ Full docstrings, type    │ Live byte offsets, padding, │
│ cascade ~> chaining │ layout & overload lists  │ & L1 cache line alignment   │
├─────────────────────┼──────────────────────────┼─────────────────────────────┤
│ 🏎️ Native Concurrency│ 🌐 WebAssembly Engine    │ 🛡️ On-The-Fly Diagnostics   │
│ spawn thread help & │ W3C pure binary emitter, │ Sub-millisecond compiler    │
│ Channel<T> routing  │ canvas primitives & live │ checks via `arx check`      │
└─────────────────────┴──────────────────────────┴─────────────────────────────┘
```

---

## 🎨 1. Precision Syntax Highlighting

Aerix features a meticulously engineered TextMate grammar (`aerix.tmLanguage.json`) adhering to universal VS Code semantic color tokens across all standard themes (*Dark+*, *One Dark Pro*, *Dracula*, *Monokai*, *GitHub Dark*, *Catppuccin*):

| Feature | Syntax Example | Highlighted Semantic Token |
| :--- | :--- | :--- |
| **Cascade Mutation** | `phoenix ~> promote(2) ~> set_clearance(8)` | `keyword.operator.cascade.aerix` |
| **Pipeline Operator** | `raw \|> scale() \|> hash()` | `keyword.operator.pipeline.aerix` |
| **Concurrency** | `let t = spawn worker(ch, 100);` | `keyword.control.spawn.aerix` |
| **Traits & Interfaces** | `trait Inspectable`, `class Foo implements Bar` | `keyword.declaration.trait.aerix`, `storage.modifier.implements` |
| **Reactive Properties**| `pub prop clearance: i64 { get => ... set(v) ... }` | `variable.other.property.aerix`, `storage.modifier.accessor` |
| **Operator Overload** | `pub op +(other: Vector2D) -> Vector2D` | `entity.name.function.operator.aerix` |
| **Type Extensions** | `extend Vector2D { ... }` | `keyword.declaration.extend.aerix` |
| **Tagged Unions** | `enum NodeStatus { Standby(i64), Active(i64, i64) }` | `entity.name.type.enum.aerix`, `variable.other.enummember` |
| **String Interpolation**| `"Profile: {self.name} | Clearance: {self.clearance}"` | `punctuation.definition.template-expression` & embedded vars |
| **Fail-Fast Guards** | `guard balance >= amount else { return false }` | `keyword.control.guard.aerix` |
| **Scope Cleanup** | `defer println("Socket closed.")` | `keyword.control.defer.aerix` |
| **Exhaustive Matching** | `match event { Alert(code) => ..., _ => ... }` | `keyword.control.match.aerix`, `constant.language.wildcard` |

---

## 💡 2. Ultra-Charged IntelliSense Engine

### A. Context-Aware Dot & Cascade Completions
- **`obj.` or `self.`**: Automatically inspects the receiver's type, enumerating all public fields, reactive properties, and methods.
- **`obj ~>`**: Automatically surfaces mutating methods suitable for fluent method chaining pipelines.
- **`spawn `**: Automatically suggests all top-level functions and worker routines with thread parameters.
- **`implements `**: Suggests all declared interface traits in the project.
- **`extend `**: Suggests all known classes and user-defined structs.
- **`NodeStatus.`**: Lists all enum variants with parameter payload documentation.

### B. High-Precision Struct Memory Visualizer (Hover)
Hovering over any class or struct computes physical memory packing on-the-fly and prints an exact C99 memory offset table:

```
📦 class Person
Total Size: 24 bytes | Alignment: 8 bytes | Cache Line: 1 (✨ Fits within single 64B cache line)

| Offset   | Field         | Type | Vis  | Size |
| :------- | :------------ | :--- | :--- | :--- |
| [0..7]   | name          | str  | pub  | 8B   |
| [8..15]  | address       | str  | pub  | 8B   |
| [16..23] | raw_clearance | i64  | priv | 8B   |
```

### C. Live Parameter Signature Help
Type `(` or `,` on any function or constructor call to receive live parameter hints with bold highlighting for the active argument index:
```aerix
telemetry_worker(worker_id: i64, ch_handle: i64, packet_count: i64)
                 ^^^^^^^^^^^^^^
```

### D. Real-Time Inlay Hints
- **Variable Inferred Types**: Displays phantom `: type` annotations beside un-annotated `let` variables.
- **Parameter Labels**: Inlays argument parameter names into function calls for clarity without cluttering your code.

### E. Hierarchical Outline Tree (`Ctrl+Shift+O`)
Breadcrumbs and Outline View neatly categorize:
- **Classes** $\rightarrow$ Nested Fields, Properties, Operators, Constructors, and Methods
- **Traits** $\rightarrow$ Method contracts
- **Enums** $\rightarrow$ Enum variants and data payloads
- **Functions** $\rightarrow$ Signature and return types

### F. Interactive CodeLens & One-Click Runner
Interactive action buttons appear directly above `fn main()` in any `.arx` file:
- **`▶ Run Aerix Program`**: Executes `arx run` inside the integrated Aerix Terminal.
- **`⚡ Fast Syntax Check`**: Runs sub-millisecond semantic validation via `arx check`.
- **`🌐 Compile WASM`**: Compiles to pure WebAssembly `.wasm`, `.wat`, and HTML5 harness via `arx wasm <file> --wat --html`.
- **`🚀 Live WASM Browser`**: Compiles and launches an instant local HTTP server with live browser runtime preview via `arx wasm <file> --serve`.


---

## ⌨️ Interactive Snippets Catalog

| Prefix | Description | Generated Template |
| :--- | :--- | :--- |
| `main` | Entrypoint | `fn main() { ... }` |
| `fn` | Block Function | `fn name(params) -> ret { ... }` |
| `fn_expr` | Expression Function | `fn name(params) -> ret => expr` |
| `fn_generic`| Generic Function | `fn name<T>(val: T) -> T { ... }` |
| `class` | OOP Class | `class Name { pub x: i64 ... init(...) { ... } }` |
| `class_generic` | Generic Class | `class Container<T> { pub item: T ... }` |
| `prop` | Reactive Property | `pub prop name: type { get => ... set(v) ... }` |
| `op` | Operator Overload | `pub op +(other: T) -> T { ... }` |
| `spawn` | Thread Spawn | `let t = spawn worker(args)` |
| `channel` | Bounded Channel | `let ch = arx_channel_new(8)` |
| `guard` | Early Exit Guard | `guard cond else { return }` |
| `match` | Pattern Matching | `match val { Variant => ..., _ => ... }` |
| `enum` | Tagged Union | `enum Name { Variant1, Variant2(data: i64) }` |
| `cascade` | Cascade Operator | `~> method()` |
| `pipe` | Pipeline Operator | `\|> func()` |
| `defer` | Scoped Cleanup | `defer cleanup()` |
| `canvas_rect` | WASM Canvas Fill Rect | `arx_canvas_fill_rect(x, y, w, h, r, g, b, 255);` |
| `canvas_clear` | WASM Canvas Clear | `arx_canvas_clear(13, 17, 23, 255);` |
| `wasm_app` | WASM Canvas Starter | `fn main() { ... arx_canvas_clear(...) }` |

---

## 📁 3. Supersonic "X" File Symbol / Icon Theme

The extension includes the official **Aerix Supersonic "X"** file icon:
- Clean two-tone chevrons combining Electric Aero Cyan (`#00DCFF`) and Royal Azure (`#1E90FF`).
- Automatically attached to all `.arx` files in your VS Code Explorer.

---

## 🚀 Installation & Setup

### Option 1: Aerix Setup Wizard (GUI)
Run `AerixSetup-1.0.90.exe` from the `AerixInstaller/dist` directory. Ensure the **Visual Studio Code** and/or **Google Antigravity IDE** checkboxes are selected under the IDE Extensions category.

### Option 2: Command-Line Installation

From the repository root (`z:\VSCode\AerixLang`):
```powershell
# For Visual Studio Code
code --install-extension editors/vscode-aerix/aerix-1.0.90.vsix --force

# For Google Antigravity IDE
antigravity --install-extension editors/vscode-aerix/aerix-1.0.90.vsix --force
```

From inside the `editors/vscode-aerix` folder:
```powershell
cd z:\VSCode\AerixLang\editors\vscode-aerix
code --install-extension aerix-1.0.90.vsix --force
antigravity --install-extension aerix-1.0.90.vsix --force
```

### Reloading Your Editor
To activate the new grammar and IntelliSense immediately:
1. Open Command Palette: `Ctrl + Shift + P`
2. Run: `Developer: Reload Window`
3. Open any `.arx` file (e.g. `test.arx`) and enjoy the full Aerix systems experience!

---

<div align="center">

Made with ⚡ for the **Aerix Systems Programming Language**  
*Speed of C • Safety of Rust • Elegance of Modern Scripting*

</div>
