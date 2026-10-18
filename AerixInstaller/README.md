# ⚡ Aerix Universal Windows Installer Workspace

Welcome to the dedicated workspace for the **Aerix Setup Installer (`AerixSetup.exe`)**.

This workspace contains the complete engineering toolchain, assets, configuration scripts, and architectural blueprints for building the modern, zero-friction graphical installer for the **Aerix Native Systems Programming Language**.

---

## 🎯 Primary Objectives

1. **Standalone Single `.exe` Installer:**
   Users download a single, beautifully branded `AerixSetup-1.0.84.exe` (no PowerShell scripts, no manual zip extraction).
2. **Windows File Explorer Integration:**
   Native file association for `.arx` source files with the official high-resolution **Aerix Supersonic Icon** displayed in Windows Explorer, desktop folders, and taskbar.
3. **Automated IDE Extensions Setup:**
   Automatic discovery and 1-click installation of the official `aerix-1.0.84.vsix` extension into both **Visual Studio Code** and the **Antigravity IDE**.
4. **Instant PATH Configuration:**
   Adds the Aerix toolchain binaries (`arx`, `arxc`) to the persistent User `PATH` environment variable and broadcasts `WM_SETTINGCHANGE` so existing terminal sessions and new prompts recognize `arx` immediately.
5. **Modern Context Menu:**
   Optional right-click context menu shortcuts on `.arx` files:
   - **Run with Aerix (`arx run %1`)**
   - **Build with Aerix (`arx build %1`)**
   - **Edit with VS Code / Antigravity IDE**
6. **Clean Uninstaller:**
   Registers properly in Windows **Settings > Apps > Installed apps** with clean, complete removal support.

---

## 📂 Workspace Structure

```text
AerixInstaller/
├── README.md                          <-- You are here
├── docs/                              <-- Comprehensive blueprints & specifications
│   ├── 01_ARCHITECTURE_AND_SPECS.md   <-- Core architecture, component payload, and scopes
│   ├── 02_REGISTRY_AND_ICON_SPEC.md   <-- File association, DefaultIcon, and shell verbs
│   ├── 03_INSTALLER_UI_UX_FLOW.md     <-- Step-by-step wizard pages, branding, and silent flags
│   └── 04_BUILD_AND_RELEASE_PIPELINE.md<-- Automated compilation, packaging, and release pipeline
├── assets/                            <-- Official logos, icons, and wizard branding graphics
│   ├── aerix.ico                      <-- App icon (16, 24, 32, 48, 64, 128, 256 px)
│   ├── aerix_file.ico                 <-- Document icon for .arx files in Windows Explorer
│   ├── wizard_banner.bmp              <-- Modern Wizard top header graphic (492x58)
│   └── wizard_side.bmp                <-- Modern Wizard left welcome graphic (164x314)
├── src/                               <-- Source scripts and manifests
│   ├── aerix_setup.iss                <-- Inno Setup professional compiler script
│   ├── installer_manifest.json        <-- File listing, target paths, and version tags
│   └── register_file_assoc.ps1        <-- Standalone file association & icon registration script
└── build.py                           <-- One-click Python orchestrator to compile the installer
```

---

## 🛠️ Quick Commands

```powershell
# Read architecture and specifications
Get-Content AerixInstaller/docs/01_ARCHITECTURE_AND_SPECS.md

# Build the installer executable (once Inno Setup is configured)
python AerixInstaller/build.py
```
