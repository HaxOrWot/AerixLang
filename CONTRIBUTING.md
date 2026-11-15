# Contributing to Aerix

Thank you for your interest in contributing to the **Aerix Programming Language**! Whether you are fixing compiler bugs, adding standard library modules, optimizing code generation, improving language documentation, or enhancing the VS Code extension, your help is warmly welcomed.

Please review this guide before submitting contributions.

---

## Code of Conduct

All contributors and maintainers are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md). Please keep interactions respectful, inclusive, and collaborative.

---

## Branch Strategy & Workflow

Aerix follows a strict, well-structured branch workflow:

| Branch | Role | Purpose |
| :--- | :--- | :--- |
| **`beta`** | **Active Development** | **All PRs and active development must target `beta`.** This is where new language features, AST improvements, and experimental backends live. |
| **`pre`** | **Pre-release Testing** | Validation and staging branch before stable promotions. |
| **`master` / `stable`** | **Production Releases** | Verified releases only (`vX.Y.Z`). Synced together with matching release tags, installers, and `.vsix` packages. |

> [!IMPORTANT]
> Never open pull requests directly to `master` or `stable`. Always base your work on the latest **`beta`** branch.

---

## Development Environment Setup

### Prerequisites
* **C99 Compiler:** GCC (MinGW-w64 on Windows, GCC/Clang on Linux/macOS)
* **Git:** Version control
* **Node.js & npm** (optional, only if working on `editors/vscode-aerix/`)
* **.NET SDK / C# Compiler** (optional, only if building `AerixInstaller/`)

### Quick Clone & Build
```powershell
# Clone the repository
git clone -b beta https://github.com/HaxOrWot/AerixLang.git
cd AerixLang

# Bootstrap compiler binary from C99 seed
gcc -O2 -mconsole -Istdlib src/bootstrap/seed/arxc.c -o arx.exe

# Verify compiler execution
.\arx.exe version
```

---

## Repository Structure

```text
AerixLang/
├── src/bootstrap/             # Self-hosting compiler source code (.arx)
│   ├── frontend/              # Lexer, tokens, AST arena, and recursive parser
│   ├── middle/                # Semantic analyzer, type checking, symbol resolution
│   ├── backend/               # C99 emitter, linker, and native code generation
│   │   └── native/            # Direct AMD64/x86-64 machine code and Win64 PE32+ generator
│   ├── lsp/                   # Language Server Protocol (JSON-RPC) daemon
│   ├── seed/arxc.c            # Pre-generated ANSI C99 bootstrap seed
│   └── main.arx               # CLI toolchain entrypoint ('arx' driver)
├── stdlib/                    # Pure C runtime header (aerix_rt.h)
├── modules/                   # Standard library modules (Math, Random, Socket, Time, Window)
├── editors/vscode-aerix/      # Official VS Code & Antigravity IDE language extension
├── AerixInstaller/            # C# Windows GUI installer, Version Manager host, and Updater
├── README.md                  # General project introduction & overview
├── GUIDE.md                   # Complete handbook and language tutorial
└── USER.md                    # Core technical developer deep-dive handbook
```

---

## How to Contribute Step-by-Step

### 1. Making Changes to the Compiler
The compiler is written in Aerix itself (`src/bootstrap/**/*.arx`). When modifying compiler logic:

1. **Edit source files** in `src/bootstrap/`.
2. **Re-transpile the C seed** using your existing working compiler:
   ```powershell
   arx emit-c src/bootstrap/main.arx -o src/bootstrap/seed/arxc.c
   ```
3. **Recompile the bootstrap binary with GCC**:
   ```powershell
   gcc -O2 -mconsole -Istdlib src/bootstrap/seed/arxc.c -o arx.exe
   ```
4. **Test self-hosting bootstrap** (compile the compiler with the new compiler):
   ```powershell
   .\arx.exe emit-c src/bootstrap/main.arx -o test_seed.c
   ```

### 2. Testing Your Changes
* Run validation commands:
  ```powershell
  arx check modules/Window/Gui/window.arx
  ```
* Test language features by writing a small `.arx` program and compiling via:
  ```powershell
  arx run script.arx
  arx build script.arx -o script.exe
  ```

> [!CAUTION]
> **Ephemeral Test Rule:** Never commit test folders or temporary files (e.g. `test_*.arx`, `test_*.exe`). Always remove temporary test files from disk before staging your commit.

### 3. Modifying the VS Code / Antigravity Extension
1. Navigate to `editors/vscode-aerix/`.
2. Edit `extension.js`, `syntaxes/`, or `snippets/`.
3. Package the extension with vsce:
   ```powershell
   npx @vscode/vsce package -o aerix-new.vsix --allow-missing-repository
   ```

---

## Pull Request Guidelines

1. **Clear Commit Messages:** Use conventional commit formatting:
   - `feat(parser): add support for ...`
   - `fix(lsp): resolve completion scoping for ...`
   - `docs(handbook): clarify pattern matching syntax`
2. **Atomic Commits:** Keep distinct changes in separate, well-described commits.
3. **Check Diffs:** Ensure no extraneous binaries or test scripts are accidentally staged (`git status`).
4. **Open PR:** Submit your pull request against the `beta` branch. Include an explanation of the problem solved and steps taken to verify.

---

## Community & Discussions

* **Issues:** Use GitHub Issues for bug reports and feature proposals.
* **Security Reports:** Please refer to [SECURITY.md](SECURITY.md) for private vulnerability reporting.
