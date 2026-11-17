<div align="center">

<img src="editors/vscode-aerix/icons/aerix-icon.png" width="128" height="128" alt="Aerix Logo" />

# Aerix (`.arx`)

### **The Expressive Native Systems Programming Language**
*The developer ergonomics of modern scripting &bull; The bare-metal velocity of native x86-64 machine code*

---

[![Release](https://img.shields.io/github/v/release/HaxOrWot/AerixLang?style=flat-square&color=00DCFF&label=Release)](https://github.com/HaxOrWot/AerixLang/releases)
[![Build](https://img.shields.io/badge/build-passing-10B981.svg?style=flat-square)](#)
[![Backend](https://img.shields.io/badge/backend-Native%20x86--64%20PE32%2B-1E90FF.svg?style=flat-square)](#)
[![Architecture](https://img.shields.io/badge/arch-AMD64%20%2F%20x86--64-8B5CF6.svg?style=flat-square)](#)
[![License](https://img.shields.io/badge/license-MIT%20%2F%20Apache--2.0-F59E0B.svg?style=flat-square)](#)
[![Platform](https://img.shields.io/badge/platform-Windows%20x64-EF4444.svg?style=flat-square)](#)

[Quickstart](#-quickstart) &bull; [Language Tour](#-language-tour) &bull; [Why Aerix?](#-why-aerix) &bull; [Installation](#-installation) &bull; [CLI Reference](#-cli-toolchain) &bull; [Handbook (GUIDE.md)](GUIDE.md) &bull; [Internals (USER.md)](USER.md)

</div>

---

## ⚡ What is Aerix?

**Aerix** is a modern, statically typed systems programming language designed from the ground up for high productivity, predictable zero-overhead execution, and instant developer feedback.

### 🌟 Core Architectural Pillars

| Pillar | How Aerix Achieves It |
| :--- | :--- |
| **🚀 Direct Native Code Generation** | Emits raw x86-64 machine code directly into valid PE32+ executables with **zero external compiler or linker dependencies**. |
| **⚡ Dual Compilation Pipelines** | Instant native emission (< 50ms) for lightning-fast dev iterations; transpilation to ANSI C99 with GCC/Clang `-O3 -flto` for max production speed. |
| **🛡️ Deterministic Zero-GC Safety** | Zero garbage collector pauses. Memory is managed cleanly with lexical lifetimes, `defer` unwinding, and high-performance linear arenas. |
| **🪟 Built-In Win32 Desktop GUI** | Native Windows desktop GUI framework (`Window.Gui`) with double-buffered canvas rendering in fewer than 10 lines of code. |
| **🧵 Native Concurrency** | Lightweight OS thread spawning (`spawn`) paired with type-safe synchronization channels (`Channel<T>`). |
| **🧩 First-Class Tooling** | Built-in Language Server Protocol (`arx lsp`), zero-config test runner (`arx test`), automatic formatter (`arx fmt`), and interactive REPL (`arx repl`). |

---

## 📊 Feature Comparison Matrix

| Capability | Aerix | C / C++ | Rust | Go | Python |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Compilation Speed** | **Instant (< 50ms)** | Slow | Very Slow | Fast | Interpreted |
| **External Toolchain Required** | **None (Native PE)** | MSVC / GCC | Cargo + LLVM | Go Toolchain | Python Runtime |
| **Garbage Collector Overhead** | **Zero GC** | None | None | Stop-the-World GC | Reference Counting GC |
| **Binary Size** | **< 25 KB** | ~30 KB | ~300 KB | ~2 MB | N/A (Bundled ~40 MB) |
| **Pipeline (`\|>`) & Cascades (`~>`)** | **Yes** | No | No | No | No |
| **Scope Unwinding (`defer`)** | **Yes** | Destructors | RAII Drop | `defer` | Context Managers (`with`) |
| **Native Win32 GUI Module** | **Built-in** | Win32 API C | External crate | External package | Tkinter |
| **Full IDE Language Server (LSP)** | **Built-in (`arx lsp`)** | Clangd / MSVC | rust-analyzer | gopls | Pylance / Pyright |

---

## 🚀 Quickstart

### 1. Write Hello World

Save as `hello.arx`:

```aerix
fn main() {
    println("Hello, bare-metal Aerix!")
}
```

### 2. Run Instantly (Under 50ms)

```powershell
arx run hello.arx
```

### 3. Build a Standalone Executable

```powershell
arx build hello.arx -o hello.exe
.\hello.exe
```

---

## 🎨 Language Tour

### 1. Pipeline & Fluent Cascade Operators
```aerix
fn double(x: i64) -> i64 => x * 2
fn add_ten(x: i64) -> i64 => x + 10

fn main() {
    // Pipeline operator (|>) forwards expressions left-to-right
    let result = 5 |> double |> add_ten
    println("Result: {result}") // Output: 20
}
```

### 2. Concurrency with Typed Channels
```aerix
fn compute_worker(id: i64, ch: Channel<str>) {
    ch.send("Worker #{id} finished computation.")
}

fn main() {
    mut ch = Channel<str>(4)
    let t1 = spawn compute_worker(1, ch)
    let t2 = spawn compute_worker(2, ch)

    println(ch.recv())
    println(ch.recv())

    arx_thread_join(t1)
    arx_thread_join(t2)
    ch.close()
}
```

### 3. Native Win32 Desktop GUI in 6 Lines
```aerix
from Window.Gui import createWindow, AppWindow

fn main() {
    mut win = createWindow("Aerix Native Window", 800, 600)
    win.show()
    win.runEventLoop()
}
```

### 4. Deterministic Resource Management with `defer`
```aerix
import File

fn process_log(path: str) {
    let handle = File.open(path, "r")
    defer File.close(handle) // Always runs on scope exit, even during exceptions!

    let content = File.readAll(handle)
    println("Read {content.len()} bytes.")
}
```

---

## 📦 Installation

### Option A: Windows Installer (Recommended)
Download **`AerixSetup-3.0.0-rc.1.exe`** from [GitHub Releases](https://github.com/HaxOrWot/AerixLang/releases).
* Installs `arx.exe`, standard modules, and headers to `C:\Aerix\bin`.
* Automatically configures user & machine `PATH` environment variables.
* Includes background update manager (`Updater.exe`) and the official VS Code / Antigravity extension.

### Option B: Build from Source
Aerix can self-host or bootstrap via any standard C99 compiler (`gcc` or `clang`):

```powershell
git clone -b beta https://github.com/HaxOrWot/AerixLang.git
cd AerixLang
gcc -O2 -mconsole -Istdlib src/bootstrap/seed/arxc.c -o arx.exe
.\arx.exe version
```

---

## 🛠️ CLI Toolchain

```text
  arx build <file.arx> [-o <out>]    Compile directly to a native standalone executable
  arx run <file.arx>                 Compile and immediately execute the program
  arx emit-c <file.arx> -o <out.c>   Transpile Aerix source code into standalone ANSI C99
  arx check <file.arx>               Validate syntax and types without code generation
  arx fmt <file.arx>                 Format Aerix source files in-place
  arx test [pattern]                 Discover and run test suites marked with #[test]
  arx lsp                            Launch the Language Server Protocol (LSP) daemon
  arx repl                           Start the interactive Aerix REPL shell
  arx doc [module]                   Generate static HTML API documentation from doc-comments
  arx pkg search|install|audit|list  Community package manager & capability security scanner
  arx vm <list|use|install>          Manage multiple installed compiler versions
  arx update                         Check for and install updates from GitHub
```

---

## 📚 Handbooks & Documentation

<div align="center">

| Resource | Scope | Description |
| :--- | :---: | :--- |
| 📦 **[aerix-packages](https://github.com/HaxOrWot/aerix-packages)** | **Registry** | Official community package registry & security-verified module index. |
| 📖 **[GUIDE.md](GUIDE.md)** | **Handbook** | Comprehensive 42-chapter developer guide with code snippets, tutorials, and real-world architectures. |
| ⚙️ **[USER.md](USER.md)** | **Internals** | Deep technical architecture of the AST arena, native AMD64 code generator, PE32+ emission, and Win64 ABI. |
| 🤝 **[CONTRIBUTING.md](CONTRIBUTING.md)** | **Governance** | Contributing guidelines, compiler bootstrap workflow, coding standards, and branch policies. |
| 🛡️ **[SECURITY.md](SECURITY.md)** | **Security** | Security advisory procedures and vulnerability reporting channels. |
| 📜 **[LICENSE](LICENSE-MIT)** | **Legal** | Dual-licensed under the **MIT** or **Apache-2.0** open-source licenses. |

</div>

---

<div align="center">
  <sub>Built with ❤️ for high-performance systems engineers. Designed by Aerix Core Team.</sub>
</div>
