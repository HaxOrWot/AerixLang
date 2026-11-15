# Aerix (`.arx`)

<div align="center">

```text
       ___         _      
      / _ \___ ___(_)_ __ 
     / __ / -_) __/ /\ \ /
    /_/ |_\__/_/ /_//_\_\ 
```

**The Expressive Native Systems Programming Language**  
*The velocity of modern scripting — fused with the speed, safety, and bare-metal power of native C.*

[![Version](https://img.shields.io/badge/version-2.2.25-00DCFF.svg?style=flat-square)](#)
[![Backend](https://img.shields.io/badge/backend-Native%20x86--64%20PE32%2B-1E90FF.svg?style=flat-square)](#)
[![License](https://img.shields.io/badge/license-MIT%20%2F%20Apache--2.0-10B981.svg?style=flat-square)](#)
[![Platform](https://img.shields.io/badge/platform-Windows%20x64-orange.svg?style=flat-square)](#)

[Quickstart](#-quickstart) • [Highlights](#-highlights) • [Installation](#-installation) • [CLI Commands](#-cli-reference) • [Handbook (GUIDE.md)](GUIDE.md) • [Internals (USER.md)](USER.md)

</div>

---

## ⚡ What is Aerix?

**Aerix** is a statically typed, compiled systems programming language engineered to eliminate the compromise between **developer ergonomics** and **bare-metal execution performance**.

* **Zero-Dependency Native PE32+ Engine:** Directly generates AMD64/x86-64 machine instructions and standalone Windows `.exe` files with **zero GCC/Clang or external linker dependencies**.
* **Dual-Pipeline Flexibility:** Build with the instant native PE generator or transpile to ANSI C99 with GCC `-O3` / `-flto` for maximum optimizations.
* **Zero Garbage Collection:** Deterministic memory management with scope cleanup (`defer`), linear arenas, and minimal footprints.
* **Native Win32 GUI & Concurrency:** Built-in desktop windowing (`Window.Gui`), native OS threads (`spawn`), and typed synchronization channels (`Channel<T>`).
* **First-Class IDE Integration:** Native Language Server Protocol (`arx lsp`) daemon powering VS Code and Antigravity IDE with semantic highlighting, scoped autocomplete, and hover documentation.

---

## 🚀 Quickstart

Create `hello.arx`:

```aerix
fn main() {
    println("Hello, Aerix!")
}
```

Compile and run immediately:
```powershell
arx run hello.arx
```

Or build a standalone executable:
```powershell
arx build hello.arx -o hello.exe
.\hello.exe
```

---

## 🎯 Highlights

```aerix
// Concurrency with typed channels
fn worker(id: i64, ch: Channel<str>) {
    ch.send("Worker {id} done.")
}

fn main() {
    mut ch = Channel<str>(4)
    let t1 = spawn worker(1, ch)
    println(ch.recv())
    arx_thread_join(t1)
    ch.close()
}
```

* **Pattern Matching:** Exhaustive `match` on literals, tagged enums, and data payloads.
* **Modern Syntax:** Pipelines (`|>`), cascades (`~>`), and early preconditions (`guard`).
* **Retroactive Extensions:** Add methods to existing structs and classes with `extend <Type>`.
* **Scoped Imports:** Strict namespace isolation with `import Mod.Sub` and `from Mod import Sym`.
* **Native GUI:** Launch desktop windows in 5 lines with `from Window.Gui import createWindow, AppWindow`.

---

## 📦 Installation

### 1. Windows Installer (Recommended)
Download **`AerixSetup-2.2.25.exe`** from [GitHub Releases](https://github.com/HaxOrWot/AerixLang/releases).  
The installer sets up `arx.exe` in `C:\Aerix\bin`, configures your system `PATH`, and includes the VS Code / Antigravity IDE extension.

### 2. Build from Source
Aerix bootstraps using any C99 compiler (`gcc` / `clang`) via the checked-in seed:

```powershell
git clone -b beta https://github.com/HaxOrWot/AerixLang.git
cd AerixLang
gcc -O2 -mconsole -Istdlib src/bootstrap/seed/arxc.c -o arx.exe
.\arx.exe version
```

---

## 🛠️ CLI Reference

```text
arx build <file.arx> [-o <out>]    Compile to native standalone executable
arx run <file.arx>                 Compile and immediately execute
arx emit-c <file.arx> -o <out.c>   Transpile to standalone ANSI C99
arx check <file.arx>               Validate syntax and types without code generation
arx fmt <file.arx>                 Format source code in-place
arx lsp                            Start the JSON-RPC Language Server daemon
arx repl                           Start interactive REPL shell
arx vm                             Manage installed compiler toolchains
arx update                         Check for and install updates from GitHub
```

---

## 📚 Handbooks & Resources

* **[GUIDE.md](GUIDE.md) — The Complete Language Handbook & Tutorial:** Comprehensive 31-chapter handbook with examples for learning and mastering Aerix.
* **[USER.md](USER.md) — Compiler Internals Manual:** Deep technical dive into AST arenas, native x86-64 code generation, Win64 ABI, and LSP internals.
* **[CONTRIBUTING.md](CONTRIBUTING.md) — Contribution Guide:** Guidelines for contributing to the compiler, standard library, and extension.
* **[SECURITY.md](SECURITY.md) — Security Policy:** Vulnerability reporting and disclosure policies.
* **[LICENSE](LICENSE):** Dual-licensed under **MIT** ([LICENSE-MIT](LICENSE-MIT)) or **Apache-2.0** ([LICENSE-APACHE](LICENSE-APACHE)).
