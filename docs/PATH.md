# Aerix Lang: v3.0 Stabilization & Hardening Blueprint (`PATH.md`)
## The Direct Path to `v3.0.0 Stable`: Polishing, Hardening, and Perfecting the Core

---

## 1. Executive Mission: Solid Foundation Before High Concurrency

As defined in [FUTURE-PLAN.md](file:///Z:/VSCode/AerixLang/docs/FUTURE-PLAN.md), the long-term goal of Aerix is high-concurrency systems programming (multi-threading, spatial chunk ticking, atomics, IOCP networking, and SIMD).

However, **a high-concurrency runtime cannot stand on an unhardened compiler**.

Before opening the v3.1+ multi-threading track, **v3.0 must become rock-solid**:
* **Zero Runtime Crashes:** No unexpected segfaults (`0xC0000005`), invalid pointer dereferences, or stack corruptions on valid syntax.
* **Deterministic ARC Memory:** Automatic Reference Counting must never leak memory in loops or corrupt non-string stack slots.
* **Helpful Diagnostics:** Every syntax mistake or type mismatch must give a clear error with file, line, and column coordinates, with zero compiler panics.
* **First-Class Developer Experience:** Instant CLI commands, responsive LSP / VS Code extension, and a clean Windows installer/uninstaller.

---

## 2. Master Progress & Release Sequence

```
  v3.0.0-beta.4 (Current State)
         │
         ▼
  [Phase 1] Compiler & Native Codegen Hardening
         │
         ▼
  [Phase 2] Standard Library & Built-in Verification
         │
         ▼
  [Phase 3] Developer Tooling, LSP & Extension Polish
         │
         ▼
  [Phase 4] Automated Stress Suite & Dogfooding Apps
         │
         ▼
  [Phase 5] Release Candidate: v3.0.0-rc.1 (7-14 Day Buffer)
         │
         ▼
  v3.0.0 STABLE RELEASE 🚀
```

---

## 3. Detailed Milestone Breakdown

### Phase 1: Compiler & Native Backend Hardening (Core Stability)
*Goal: Ensure the native x86_64 PE32+ emitter and C99 transpiler generate flawless machine code.*

- [x] **Target-Typed Input Desugaring:**
  - `let x: i64 = input(...)` safely parses numeric types (`i8`..`i64`, `u8`..`u64`, `f32`, `f64`).
- [x] **ARC Slot Misclassification Fix:**
  - Prevent temporary string initializers from corrupting primitive variable slot types in `scope_types`.
- [ ] **ARC Lifecycle & Scope Drop Audit:**
  - [ ] Audit variable reassignment in `while` and `for` loops (ensure old values release without memory leakage).
  - [ ] Audit function return expressions (ensure returned strings/lists are retained while local temporaries are dropped).
  - [ ] Audit branch exits (`if`, `else if`, `else`, `break`, `continue`) to ensure stack cleanup matches scope depth.
- [ ] **Register Allocation & Spill Safety:**
  - [ ] Ensure non-volatile registers and caller-saved registers (`RAX`, `RCX`, `RDX`, `XMM0`) do not clobber during nested function calls.
  - [ ] Verify 16-byte stack alignment across all Win64 ABI call boundaries.
- [ ] **Diagnostics & Error Reporting Polish:**
  - [ ] Ensure all semantic errors emit structured diagnostic formats: `E0xxx: <description> @ [file:L:C]`.
  - [ ] Add suggestions / tips (`help: ...`) for common syntax mistakes.
  - [ ] Clean up redundant mutable variable analysis warnings (`mut` vs `let`).

---

### Phase 2: Standard Library & Primitives Verification
*Goal: Guarantee all built-in types and standard modules work consistently and without crashes.*

- [ ] **String (`str`) Primitive Methods:**
  - [ ] `.len()`, `.slice()`, `.contains()`, `.starts_with()`, `.ends_with()`.
  - [ ] `.trim()`, `.split()`, `.replace()`.
  - [ ] Numeric conversions (`to_i64()`, `to_f64()`) with safe defaults on invalid/empty strings.
- [ ] **Dynamic Collections (`List<T>`, `Map<K, V>`):**
  - [ ] `List<T>`: `.push()`, `.pop()`, `.get()`, `.set()`, `.len()`, `.clear()`.
  - [ ] Bounds checking: clear runtime panic on out-of-bounds indexing instead of silent memory corruption.
- [ ] **Console & File I/O:**
  - [ ] Interpolated string formatting: `{var}`, `{expr}`, escaped braces `\{` and `\}`.
  - [ ] File operations: `File.read()`, `File.write()`, `File.append()`, `File.exists()`.
- [ ] **Standard Module Audits (`modules/`):**
  - [ ] `Math` (trigonometry, rounding, clamps, constants).
  - [ ] `Random` (seed generation, integer/float ranges).
  - [ ] `Time` (clock, timestamps, sleep).
  - [ ] `Socket` (basic TCP stream connectivity).

---

### Phase 3: Developer Tooling, LSP & Extension Polish
*Goal: Provide a smooth, friction-free developer experience from installation to code editing.*

- [x] **Uninstaller Process Cleanup:**
  - Uninstaller detects and terminates lingering background `arx.exe` or LSP processes before file deletion.
- [x] **Modern Uninstaller GUI:**
  - Dark-mode layout, progress reporting, and full cleanup of registry/PATH entries.
- [ ] **VS Code Extension (`editors/vscode-aerix`):**
  - [ ] Update syntax grammar for latest keywords (`??`, `mut`, `let`, `extend`, `struct`, `class`).
  - [ ] Verify Language Server Protocol (LSP) auto-complete, diagnostics squiggles, and hover tooltips.
  - [ ] Package and test latest `.vsix` bundle.
- [ ] **Aerix CLI (`arx`):**
  - [ ] `arx --version`: Clean SemVer output matching installer version.
  - [ ] `arx --help`: Clear, organized command list (`run`, `build`, `emit-c`, `check`).
  - [ ] `arx check`: Fast syntax and type verification without generating output binaries.

---

### Phase 4: Automated Stress Testing & Dogfooding Apps
*Goal: Prove compiler and runtime stability under realistic, multi-thousand-iteration workloads.*

- [ ] **The ARC 100,000 Iteration Loop Test:**
  - Run a loop that allocates, concatenates, and drops strings 100,000 times. Verify zero memory drift (no leaks) and clean process exit.
- [ ] **Dogfood Application 1: CLI Expression Calculator:**
  - Tokenizes, parses, and evaluates math expressions using `input()`, `??` fallbacks, strings, and loops.
- [ ] **Dogfood Application 2: Text Search Utility (Mini-Grep):**
  - Reads files from disk, splits lines, searches patterns, and prints formatted output.
- [ ] **Dogfood Application 3: Interactive Console Game (Tic-Tac-Toe / Guess Number):**
  - Tests user input loops, mutable state transitions, and game logic.

---

### Phase 5: Release Candidate (`v3.0.0-rc.1`) & Launch Gate
*Goal: Execute the clean promotion workflow per [GIT-INS.md](file:///Z:/VSCode/AerixLang/docs/GIT-INS.md).*

- [ ] **Declare Feature Freeze:** No new keywords, syntax, or breaking grammar changes.
- [ ] **Update Project-Wide Version Checklist:**
  - `AerixInstaller/src/installer_manifest.json` (`3.0.0-rc.1`)
  - `AerixInstaller/src/InstallerEngine.cs`
  - `AerixInstaller/src/AssemblyInfo.cs`
  - `src/bootstrap/main.arx` & `src/bootstrap/lsp/server.arx`
  - `editors/vscode-aerix/package.json`
  - Documentation files (`README.md`, `GUIDE.md`, `USER.md`).
- [ ] **Build RC Artifacts:**
  - `AerixSetup-3.0.0-rc.1.exe`
  - `aerix-3.0.0-rc.1.vsix`
- [ ] **7–14 Day RC Stabilization Buffer:**
  - Daily testing on real codebases.
- [ ] **Promote to `v3.0.0 Stable`:**
  - Fast-forward merge `beta` into `master` and `stable`.
  - Tag `v3.0.0`.
  - Publish GitHub Release.
