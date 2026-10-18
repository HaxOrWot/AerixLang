# Aerix Setup Installer — Architecture & Engineering Specification

## 1. System Requirements & Target Platforms

| Specification | Requirement |
| :--- | :--- |
| **Operating System** | Windows 10 (Version 1809+), Windows 11 |
| **CPU Architectures**| x86_64 (Intel / AMD64), ARM64 (via Windows x64 emulation) |
| **Privileges** | Standard User (Zero elevation required for default user installation) |
| **Disk Footprint** | ~35 MB unpacked |
| **Host Toolchain** | Standard C99 Compiler (GCC / MinGW-w64 recommended) |

---

## 2. Payload Inventory (Files Bundled Inside Setup `.exe`)

The installer packages all required compiler binaries, runtimes, extensions, and icons into a single, self-extracting, LZMA2-compressed setup executable:

```text
AerixSetup-1.0.84.exe (Payload Contents)
├── bin/
│   ├── arx.exe                         # Main CLI Toolchain Driver (Run, Build, Doctor, REPL)
│   ├── arxc.exe                        # Native Compiler Core (AST, AIR, C99 Transpiler)
│   └── arx.bat                         # Batch shim for seamless command-line execution
├── stdlib/
│   └── aerix_rt.h                      # ANSI C99 Native Systems Runtime & Channel Engine
├── editors/
│   └── aerix-1.0.84.vsix               # Official VS Code & Antigravity IDE Extension
├── assets/
│   ├── aerix.ico                       # High-DPI Multi-Size App Icon (256, 128, 64, 48, 32, 16)
│   └── aerix_file.ico                  # Document Icon for .arx files in Windows Explorer
├── docs/
│   ├── USER.md                         # Technical Specification & Manual
│   └── GUIDE.md                        # Master Learning Guide (34 Chapters)
└── LICENSE                             # Official Open Source License
```

---

## 3. Installation Scopes & Target Directories

### A. Current User Scope *(Default — Recommended)*
* **Target Location:** `%LOCALAPPDATA%\Programs\Aerix`  
  *(e.g., `C:\Users\<Username>\AppData\Local\Programs\Aerix`)*
* **UAC Elevation:** **Not required.** Installs in seconds without annoying Windows UAC security popups.
* **Registry Hive:** `HKEY_CURRENT_USER\Software\Classes` and `HKEY_CURRENT_USER\Environment`.
* **Ideal For:** Fast developer workstations, shared computers, school/enterprise labs without admin rights.

### B. All Users Scope *(Optional via `/ALLUSERS` flag)*
* **Target Location:** `%ProgramFiles%\Aerix`  
  *(e.g., `C:\Program Files\Aerix`)*
* **UAC Elevation:** Required (Standard Windows administrator prompt).
* **Registry Hive:** `HKEY_LOCAL_MACHINE\Software\Classes` and `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\Environment`.

---

## 4. Persistent Environment PATH Configuration

To ensure developers can immediately type `arx run main.arx` anywhere in their terminal:
1. The installer appends `{app}\bin` to the user's `PATH` environment variable.
2. It sends a Win32 broadcast message:
   ```cpp
   SendMessageTimeout(HWND_BROADCAST, WM_SETTINGCHANGE, 0, (LPARAM)"Environment", SMTO_ABORTIFHUNG, 5000, &dwResult);
   ```
3. **Result:** All new PowerShell, Command Prompt, Git Bash, and Windows Terminal windows recognize `arx` immediately without requiring a system restart or user logoff!

---

## 5. GCC Backend Auto-Discovery & Diagnostics

Aerix compiles down to ANSI C99 and links via GCC. During or immediately after installation:
1. The installer searches for existing GCC installations:
   - Evaluates current `PATH` for `gcc.exe`.
   - Checks common installation directories:
     - `C:\msys64\ucrt64\bin`
     - `C:\msys64\mingw64\bin`
     - `C:\MinGW\bin`
     - `C:\TDM-GCC-64\bin`
2. If GCC is found, Aerix links automatically.
3. If no C compiler is detected, the installer offers a 1-click option to install WinLibs / MinGW-w64 via `winget`:
   ```powershell
   winget install -e --id BrechtSanders.winlibs.llvm.posix.ucrt
   ```

---

## 6. IDE Extension Auto-Registration

The installer inspects the local machine for installed developer environments:
1. **Visual Studio Code:**
   Checks if `code` or `code.cmd` is on `PATH` or in `%LOCALAPPDATA%\Programs\Microsoft VS Code`.
   If detected, automatically invokes:
   ```powershell
   code --install-extension "{app}\editors\aerix-1.0.84.vsix" --force
   ```
2. **Google Antigravity IDE:**
   Checks for `%USERPROFILE%\.antigravity-ide\extensions`.
   If detected, extracts the extension directly into the active extension profile folder.
