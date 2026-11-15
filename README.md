# Aerix (`.arx`) — High-Performance Native Systems Programming Language

<div align="center">

```text
       ___         _      
      / _ \___ ___(_)_ __ 
     / __ / -_) __/ /\ \ /
    /_/ |_\__/_/ /_//_\_\ 
```

### **The Expressive Native Systems Programming Language**
*The uncompromising speed and control of bare-metal C — fused with the elegance, safety, and rapid feedback of modern language design.*

[![Version](https://img.shields.io/badge/version-2.2.25-00DCFF.svg?style=for-the-badge&logo=visualstudiocode)](#)
[![Backend](https://img.shields.io/badge/backend-Native%20x86--64%20PE32%2B-1E90FF.svg?style=for-the-badge)](#)
[![License](https://img.shields.io/badge/license-MIT%20%2F%20Apache--2.0-10B981.svg?style=for-the-badge)](#)
[![Platform](https://img.shields.io/badge/platform-Windows%20x64-orange.svg?style=for-the-badge)](#)
[![LSP Engine](https://img.shields.io/badge/LSP-Compiler%20Daemon%20(JSON--RPC)-7C4DFF.svg?style=for-the-badge)](#)

[Quickstart](#-quickstart-in-60-seconds) • [Why Aerix?](#-why-aerix) • [Code Showcase](#-code-showcase) • [Installation](#-installation) • [Handbooks](#-handbooks--documentation) • [Toolchain CLI](#-cli-toolchain-reference) • [Contributing](CONTRIBUTING.md)

</div>

---

## ⚡ What is Aerix?

**Aerix** is a compiled, statically typed systems programming language engineered to eliminate the historic dilemma between **developer velocity** and **bare-metal execution performance**.

* **C and C++** offer raw hardware speed and memory control, but burden developers with manual pointer hazards, header file management, complex build systems, and decades of legacy complexity.
* **Rust** provides compile-time memory safety, but introduces steep borrow-checker cognitive friction and lengthy compilation times.
* **Go and Java** simplify programming, but rely on background garbage collectors that introduce unpredictable latency spikes and larger memory footprints.
* **Python and TypeScript** offer great developer ergonomics, but suffer from significant execution overhead and high memory consumption.

**Aerix delivers the sweet spot:**
1. **Zero-Dependency Native PE32+ Code Generation:** The compiler synthesizes AMD64/x86-64 machine instructions and standalone Windows `.exe` binaries directly from the AST with **zero GCC, Clang, or external linker dependencies**.
2. **Dual-Pipeline Flexibility:** Build with the blazing-fast native PE generator for instant builds, or transpile to ANSI C99 with GCC `-O3` / `-flto` for peak mathematical optimization.
3. **Zero Garbage Collection:** Deterministic, real-time memory management with scope cleanup (`defer`), lightweight arenas, and explicit control.
4. **First-Class Win32 Desktop GUI:** Built-in desktop windowing (`Window.Gui`) enabling high-performance desktop applications with zero third-party UI framework dependencies.
5. **Native Concurrency:** True OS-level thread spawning (`spawn`) paired with thread-safe typed synchronization queues (`Channel<T>`).
6. **Built-in Language Server (LSP):** A native background daemon (`arx lsp`) providing instant semantic token highlighting, context-ranked autocompletions, strict import scoping, hover docs, and Go-to-Definition.

---

## 🎯 Language Highlights

| Capability | Description |
| :--- | :--- |
| **Strict Type Safety** | Robust compile-time type inference, strong nominal typing, generic collections (`List<T>`, `Map<K, V>`), and tagged unions. |
| **Direct PE32+ Engine** | Generates standalone PE32+ Windows executables directly from memory without invoking external assemblers or linkers. |
| **Modern Syntax** | Pattern matching (`match`), conditional guards (`guard`), expressive pipelines (`\|>`), and fluent cascades (`~>`). |
| **Zero-Cost Concurrency** | Lightweight native thread spawning (`spawn`) paired with typed bounded synchronization queues (`Channel<T>`). |
| **Scoped Module Isolation** | Strict module importing (`import Window.Gui`, `from Window.Gui import createWindow`) preventing symbol and namespace pollution. |
| **Native Win32 GUI** | Create high-performance native desktop applications without relying on bulky web-view runtimes or external UI kits. |
| **Retroactive Extensions** | Add new methods to existing structs and classes outside their initial declaration (`extend <Type>`). |
| **Dual-Licensed** | 100% Free & Open Source under your choice of **MIT** or **Apache-2.0**. |

---

## 🚀 Quickstart in 60 Seconds

### 1. Hello World
Save the following as `hello.arx`:

```aerix
fn main() {
    println("Hello from Aerix Systems Programming!")
}
```

Compile and run immediately in one command:
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
    
    // Spawn concurrent native OS threads
    let t1 = spawn worker(1, ch)
    let t2 = spawn worker(2, ch)
    
    // Receive messages from workers
    println(ch.recv())
    println(ch.recv())
    
    arx_thread_join(t1)
    arx_thread_join(t2)
    ch.close()
}
```

### 2. Tagged Unions & Exhaustive Pattern Matching
```aerix
enum NetworkStatus {
    Disconnected,
    Connecting(attempt: i64),
    Connected(ip: str, ping_ms: i64),
    Failed(reason: str)
}

fn log_status(status: NetworkStatus) {
    match status {
        case Disconnected => println("Status: Offline")
        case Connecting(att) => println("Status: Connecting (attempt {att})...")
        case Connected(ip, ping) => println("Status: Online ({ip}) - {ping}ms")
        case Failed(err) => println("Status: Connection Failed - {err}")
    }
}

fn main() {
    let state = NetworkStatus.Connected("192.168.1.100", 14)
    log_status(state)
}
```

### 3. Native Win32 Desktop Window in 6 Lines
```aerix
from Window.Gui import createWindow, AppWindow

fn main() {
    let win = createWindow("Aerix Native Window", 800, 600)
    let app = AppWindow(win)
    app.show()
    app.run()
}
```

### 4. Retroactive Type Extensions (`extend`)
```aerix
struct Vector2D {
    pub x: f64
    pub y: f64
    
    init(x: f64, y: f64) {
        self.x = x
        self.y = y
    }
}

// Add methods to Vector2D after declaration
extend Vector2D {
    pub fn magnitude() -> f64 {
        return Math.sqrt(self.x * self.x + self.y * self.y)
    }
}

fn main() {
    let vec = Vector2D(3.0, 4.0)
    println("Magnitude: {vec.magnitude()}") // 5.0
}
```

---

## 📦 Installation

### Option 1: Standalone Windows GUI Installer
Download the latest `AerixSetup-2.2.25.exe` from [Releases](https://github.com/HaxOrWot/AerixLang/releases):
* Installs the complete compiler toolchain to `C:\Aerix\bin`
* Automatically configures your system `PATH`
* Includes the standard library, documentation, and the VS Code / Antigravity IDE extension
* Automatically installs the background update checker and Version Manager

### Option 2: Self-Hosting Bootstrap Build from Source
Aerix can bootstrap itself using any standard C99 compiler (`gcc` or `clang`) via the checked-in bootstrap seed:

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

## 📚 Handbooks & Documentation

Aerix includes comprehensive documentation:

| Handbook | Purpose | Target Audience |
| :--- | :--- | :--- |
| **[GUIDE.md](GUIDE.md)** | **The Complete Language Handbook & Tutorial** | Everyone. A complete tutorial explaining syntax, types, OOP, pattern matching, memory model, and GUI with clear code examples. |
| **[USER.md](USER.md)** | **Core Technical Deep-Dive Handbook** | Compiler developers & systems architects. Explains compiler architecture, AST arena, type inference, native x86-64 code generation, Win64 ABI, and LSP internals. |
| **[CONTRIBUTING.md](CONTRIBUTING.md)** | **Contribution & Development Guide** | Community contributors. Explains repository structure, branch workflow, how to transpile seeds, and PR guidelines. |
| **[SECURITY.md](SECURITY.md)** | **Security Policy** | Security researchers. Explains vulnerability reporting and disclosure policies. |
| **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** | **Community Code of Conduct** | Community members and contributors. |

---

## 📄 License

Aerix is proudly dual-licensed under both the **MIT License** and the **Apache License (Version 2.0)**:
* [LICENSE-MIT](LICENSE-MIT)
* [LICENSE-APACHE](LICENSE-APACHE)
