# ⚡ Aerix Windows Setup Engine

<div align="center">

```text
       █████╗ ███████╗██████╗ ██╗██╗  ██╗    ███████╗███████╗████████╗██╗   ██╗██████╗ 
      ██╔══██╗██╔════╝██╔══██╗██║╚██╗██╔╝    ██╔════╝██╔════╝╚══██╔══╝██║   ██║██╔══██╗
      ███████║█████╗  ██████╔╝██║ ╚███╔╝     ███████╗█████╗     ██║   ██║   ██║██████╔╝
      ██╔══██║██╔══╝  ██╔══██╗██║ ██╔██╗     ╚════██║██╔══╝     ██║   ██║   ██║██╔═══╝ 
      ██║  ██║███████╗██║  ██║██║██╔╝ ██╗    ███████║███████╗   ██║   ╚██████╔╝██║     
      ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝    ╚══════╝╚══════╝   ╚═╝    ╚═════╝ ╚═╝     
```

### **The Enterprise-Grade Zero-Friction Native Windows Deployment Engine**
*Standalone Setup Executable (`AerixSetup.exe`) for the Aerix Native Systems Programming Language*

[![Platform: Windows 10 / 11](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-blue?logo=windows)](https://microsoft.com)
[![Architecture: x86_64 / ARM64](https://img.shields.io/badge/Arch-x86__64%20%7C%20ARM64-cyan)](https://github.com/HaxOrWot/AerixLang)
[![Compression: LZMA2 Ultra](https://img.shields.io/badge/Compression-LZMA2%20Ultra64-green)](https://jrsoftware.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

</div>

---

## 🚀 Mission Overview

The **Aerix Setup Installer** delivers an enterprise-grade, modern, and zero-friction installation experience for developers on Microsoft Windows. Instead of wrestling with manual environment variables, ZIP extractions, or blank document icons, developers download and run a single, beautifully branded **`AerixSetup-1.0.89.exe`**.

### 🌟 Key Capabilities

1. ⚡ **Single Standalone Executable:**
   Zero external dependencies. Compresses the complete compiler, ANSI C99 runtime headers, documentation suite, multi-layer icons, and IDE extensions into a lightweight **~2.30 MB installer**.
2. 🎨 **Native Windows Explorer Shell Branding:**
   Instantly binds `.arx` source files to the high-resolution supersonic Aerix icon across all Explorer view modes (from 16px details to 256px extra-large icons) with real-time `SHChangeNotify` cache invalidation.
3. 🛠️ **Interactive Multi-IDE Integration (VS Code & Antigravity):**
   Proactively detects installed developer environments (**Visual Studio Code** and **Google Antigravity IDE**) and displays an interactive setup prompt allowing developers to opt into 1-click automated extension installation.
4. 🌐 **Zero-Elevation User Space Deployment:**
   Installs by default into `%LOCALAPPDATA%\Programs\Aerix` without requiring Administrator privileges or triggering invasive Windows UAC prompts.
5. 🔄 **Atomic Environment PATH Broadcasting:**
   Safely appends `{app}\bin` to the user's `PATH` environment variable and broadcasts Win32 `WM_SETTINGCHANGE` so existing consoles and new terminal sessions immediately recognize `arx`.
6. 🖱️ **Instant Desktop Context Verbs:**
   Adds productive right-click Explorer actions to `.arx` files:
   - **Run with Aerix (`arx run "%1"`)**
   - **Build Executable (`arx build "%1"`)**
   - **Open with Code Editor**
7. 🧹 **Clean, Deterministic Uninstaller:**
   Registers cleanly in Windows **Settings > Apps > Installed apps** with 100% reversible file and registry cleanup.

---

## 📚 Comprehensive Engineering Specifications

| Document | Description |
| :--- | :--- |
| [**01_ARCHITECTURE_AND_SPECS.md**](docs/01_ARCHITECTURE_AND_SPECS.md) | Architectural foundations, payload manifests, dual-scope security models, and lifecycle state machines. |
| [**02_REGISTRY_AND_ICON_SPEC.md**](docs/02_REGISTRY_AND_ICON_SPEC.md) | Windows Shell registry mapping, ProgID hierarchy, multi-layer `.ico` mipmaps, and `SHChangeNotify` cache invalidation. |
| [**03_INSTALLER_UI_UX_FLOW.md**](docs/03_INSTALLER_UI_UX_FLOW.md) | Screen-by-screen ASCII wireframes, modern color system, IDE extension prompt logic, and headless CI/CD switches. |
| [**04_BUILD_AND_RELEASE_PIPELINE.md**](docs/04_BUILD_AND_RELEASE_PIPELINE.md) | Automated build orchestration, Inno Setup compiler integration, SHA-256 validation, and GitHub Releases pipeline. |

---

## 📂 Project Directory Structure

```text
AerixInstaller/
├── README.md                          # Executive dashboard and project overview
├── build.py                           # One-click Python compiler orchestrator
├── docs/                              # Deep engineering specifications
│   ├── 01_ARCHITECTURE_AND_SPECS.md   # Core architecture and payload manifest
│   ├── 02_REGISTRY_AND_ICON_SPEC.md   # Windows Registry, icons & shell integration
│   ├── 03_INSTALLER_UI_UX_FLOW.md     # UI wireframes, IDE prompts & silent flags
│   └── 04_BUILD_AND_RELEASE_PIPELINE.md# Automated build & GitHub release pipeline
├── assets/                            # Generated high-DPI icons & wizard bitmaps
│   ├── aerix.ico                      # Multi-layer app icon (16x16 to 256x256 px)
│   ├── aerix_file.ico                 # Document sheet icon for .arx files
│   ├── wizard_side.bmp                # 24-bit Modern Wizard sidebar (164x314 px)
│   └── wizard_banner.bmp              # 24-bit Modern Wizard top banner (492x58 px)
├── src/                               # Scripts, templates and Inno Setup source
│   ├── aerix_setup.iss                # Official Inno Setup modern compilation script
│   ├── generate_assets.py             # PIL-based multi-resolution icon & BMP generator
│   ├── installer_manifest.json        # Component payload configuration manifest
│   └── register_file_assoc.ps1        # Standalone PowerShell shell registration script
└── dist/                              # Output compilation binaries
    └── AerixSetup-1.0.89.exe          # Production standalone Windows installer (~2.30 MB)
```

---

## 🛠️ One-Click Build & Compilation

To compile the standalone installer executable locally:

```powershell
# Run the automated build orchestrator
python AerixInstaller/build.py
```

### Build Pipeline Execution:
1. **Asset Synthesis:** Generates high-DPI `.ico` mipmaps and 24-bit `.bmp` wizard artwork via `generate_assets.py`.
2. **ISCC Resolution:** Automatically locates `iscc.exe` (or auto-installs Inno Setup via `winget` if missing).
3. **Payload Compression:** Compresses all components with LZMA2 ultra64 solid compression into `dist\AerixSetup-1.0.89.exe`.
4. **Integrity Digest:** Verifies output binary and outputs cryptographic SHA-256 hash.

---

## 💻 Headless & Unattended Deployment

For automated CI/CD runners, Docker containers, or provisioning scripts:

```powershell
# Completely silent installation with all features enabled:
.\AerixSetup-1.0.89.exe /VERYSILENT /SUPPRESSMSGBOXES /TASKS="envPath,fileAssoc,contextMenu,vscodeExt,antigravityExt" /LOG="install.log"
```
