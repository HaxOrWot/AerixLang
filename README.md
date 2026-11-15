# Aerix (`.arx`) — High-Performance Native Systems Programming Language

<div align="center">

```text
       ___         _      
      / _ \___ ___(_)_ __ 
     / __ / -_) __/ /\ \ /
    /_/ |_\__/_/ /_//_\_\ 
```

### **The Expressive Native Systems Programming Language**
*The speed, control, and zero-overhead of bare-metal C — paired with the elegance, safety, and velocity of modern language design.*

[![Version](https://img.shields.io/badge/version-2.2.25-00DCFF.svg?style=for-the-badge&logo=visualstudiocode)](#)
[![Backend](https://img.shields.io/badge/backend-Native%20x86--64%20PE32%2B-1E90FF.svg?style=for-the-badge)](#)
[![License](https://img.shields.io/badge/license-MIT%20%2F%20Apache--2.0-10B981.svg?style=for-the-badge)](#)
[![Platform](https://img.shields.io/badge/platform-Windows%20x64-orange.svg?style=for-the-badge)](#)
[![LSP Engine](https://img.shields.io/badge/LSP-Compiler%20Daemon%20(JSON--RPC)-7C4DFF.svg?style=for-the-badge)](#)

[Quickstart](#-quickstart-in-60-seconds) • [Language Highlights](#-why-aerix) • [Code Showcase](#-code-showcase) • [Installation](#-installation) • [Handbooks](#-documentation-handbooks) • [Toolchain CLI](#-cli-toolchain-reference) • [Contributing](CONTRIBUTING.md)

</div>

---

## ⚡ What is Aerix?

**Aerix** is a statically-typed, compiled systems programming language engineered to eliminate the historic dilemma between **developer ergonomics** and **bare-metal execution performance**.

* **C and C++** offer raw speed and memory control, but place the burden of pointer safety, arcane build systems, header management, and decades of technical debt on the programmer.
* **Rust** provides strong compile-time guarantees, but introduces steep borrow-checker friction and lengthy compilation cycles.
* **Go and Java** simplify concurrency, but rely on garbage collector pauses and heavier runtime runtimes.
* **Python and TypeScript** provide rapid prototyping, but suffer from significant execution overhead and high memory usage.

**Aerix delivers the sweet spot:**
1. **Zero-Dependency Native Code Generation:** Directly synthesizes AMD64/x86-64 machine instructions and Win64 PE32+ `.exe` files straight from the AST with **zero GCC/Clang or external linker dependencies**.
2. **Dual-Pipeline Flexibility:** Build with the blazing fast native PE generator for instant builds, or transpile to ANSI C99 with GCC `-O3` / `-flto` for peak optimization.
3. **Zero Garbage Collection:** Deterministic memory management with scope cleanup (`defer`), fast arenas, and manual control where needed.
4. **Rich Native Standard Library:** Built-in Win32 desktop GUI windowing (`Window.Gui`), high-resolution timers (`Time`), TCP/UDP networking (`Socket`), PRNG (`Random`), and thread channels (`spawn`, `Channel`).
5. **First-Class IDE Integration:** Built-in Language Server Protocol (`arx lsp`) engine providing instant semantic highlighting, scoped autocomplete, hover signatures, and Go-to-Definition.

---

## 🎯 Language Highlights

| Feature | Description |
| :--- | :--- |
| **Strict Type Safety** | Robust compile-time type inference, strong nominal typing, generics (`List<T>`, `Map<K,V>`), and tagged unions. |
| **Direct PE32+ Generation** | Zero-dependency compilation pipeline emitting standalone `.exe` files directly from memory without external assemblers. |
| **Modern Syntax** | Pattern matching (`match`), conditional guards (`guard`), expressive pipelines (`\|>`), and fluent cascades (`~>`). |
| **Zero-Cost Concurrency** | Lightweight native thread spawning (`spawn`) paired with typed bounded synchronization queues (`Channel<T>`). |
| **Scoped Module Isolation** | Granular module importing (`import Window.Gui`, `from Window.Gui import createWindow`) preventing namespace pollution. |
| **Native GUI Engine** | First-class Win32 desktop applications and hardware windowing without third-party frameworks. |
| **Retroactive Extensions** | Add methods to existing structs and types outside their definition (`extend <Type>`). |
| **Dual-Licensed** | 100% Free & Open Source under your choice of **MIT** or **Apache-2.0**. |

---

## 🚀 Quickstart in 60 Seconds

### 1. Hello World
Save as `hello.arx`:
```aerix
fn main() {
    println("Hello, Aerix World!")
}
```

Compile and run immediately:
```powershell
arx run hello.arx
```

Or build a standalone `.exe`:
```powershell
arx build hello.arx -o hello.exe
.\hello.exe
```

---

## 💻 Code Showcase

### 1. Concurrency with Channels
```aerix
fn worker(id: i64, ch: Channel<str>) {
    ch.send("Worker {id} completed computation.")
}

fn main() {
    mut ch = Channel<str>(10)
    
    // Spawn background worker threads
    let t1 = spawn worker(1, ch)
    let t2 = spawn worker(2, ch)
    
    // Receive messages
    println(ch.recv())
    println(ch.recv())
    
    arx_thread_join(t1)
    arx_thread_join(t2)
    ch.close()
}
```

### 2. Tagged Unions & Pattern Matching
```aerix
enum Shape {
    Circle(radius: f64),
    Rectangle(width: f64, height: f64)
}

fn calculate_area(s: Shape) -> f64 {
    match s {
        case Circle(r) => 3.14159 * r * r
        case Rectangle(w, h) => w * h
    }
}

fn main() {
    let disk = Shape.Circle(5.0)
    println("Area: {calculate_area(disk)}")
}
```

### 3. Native Win32 Desktop Window in 6 Lines
```aerix
from Window.Gui import createWindow, AppWindow

fn main() {
    let win = createWindow("Aerix Native Desktop Window", 800, 600)
    let app = AppWindow(win)
    app.show()
    app.run()
}
```

---

## 📦 Installation

### Option 1: Standalone Windows GUI Installer
Download the latest `AerixSetup.exe` from [Releases](https://github.com/HaxOrWot/AerixLang/releases):
* Automatically installs `arx.exe` to `C:\Aerix\bin`
* Adds Aerix to your system `PATH`
* Includes the standard library, documentation, and the VS Code / Antigravity extension
* Embeds the background updater and Version Manager

### Option 2: Self-Hosting Build from Source
Aerix can bootstrap itself using any standard C99 compiler (`gcc` or `clang`) via the pre-generated bootstrap seed:

```powershell
# 1. Clone repository
git clone -b beta https://github.com/HaxOrWot/AerixLang.git
cd AerixLang

# 2. Compile bootstrap compiler binary with GCC
gcc -O2 -mconsole -Istdlib src/bootstrap/seed/arxc.c -o arx.exe

# 3. Verify toolchain
.\arx.exe version
```

---

## 🛠️ CLI Toolchain Reference

The unified `arx` CLI provides all compiler commands in one binary:

```text
Usage:
  arx <command> [arguments...] [options]
  arx <file.arx> [-o <out>]          (Shorthand build)

Core Commands:
  build        Compile an Aerix program into a standalone native binary
  run          Compile and immediately execute an Aerix program
  emit-c       Transpile Aerix source code into standalone ANSI C99
  check        Parse, validate, and type-check without code generation
  fmt          Format Aerix source files in-place or check formatting
  test         Discover and execute unit and integration test suites

Developer & IDE Tooling:
  lsp          Start the Language Server Protocol (LSP) JSON-RPC daemon
  doc          Generate static HTML API documentation from doc-comments
  repl         Start the interactive Aerix REPL shell

Version & Toolchain Management:
  vm           Manage multiple compiler toolchains and release channels
  install      Download & install a toolchain version
  use          Switch active toolchain version
  versions     List installed toolchains
  update       Check for and install updates from GitHub
```

---

## 📚 Documentation Handbooks

Aerix comes with complete, in-depth documentation handbooks:

| Document | Purpose | Audience |
| :--- | :--- | :--- |
| **[GUIDE.md](GUIDE.md)** | **The Complete Language Handbook & Tutorial** | Everyone. A complete from-scratch guide explaining syntax, types, OOP, pattern matching, memory model, and GUI with clear code examples. |
| **[USER.md](USER.md)** | **Core Technical Deep-Dive Handbook** | Compiler developers & systems architects. Explains compiler architecture, AST arena, type inference, native x86-64 code generation, Win64 ABI, and LSP internals. |
| **[CONTRIBUTING.md](CONTRIBUTING.md)** | **Contribution & Development Guide** | Community contributors. Explains repository structure, branch workflow, how to transpile seeds, and PR guidelines. |
| **[SECURITY.md](SECURITY.md)** | **Security Policy** | Security researchers. Explains vulnerability reporting and disclosure policies. |

---

## 📄 License

Aerix is proudly dual-licensed under both the **MIT License** and the **Apache License (Version 2.0)**:
* [LICENSE-MIT](LICENSE-MIT)
* [LICENSE-APACHE](LICENSE-APACHE)
