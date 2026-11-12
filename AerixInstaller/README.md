# AerixSetup — Native C++ Windows Installer (`AerixInstaller`)

Standalone, zero-dependency **C++17 / Win32 GUI** installer and uninstaller for the **Aerix Native Systems Programming Language (`1.1.0-stable`)**.

## Overview

Replaces the legacy Python/Inno Setup pipeline with a self-contained native C++ executable (`AerixSetup-1.1.0-stable.exe`) that embeds a zlib-compressed `ARXP` payload of the self-hosting native compiler (`arx.exe` / `arxc.exe`), `stdlib/aerix_rt.h`, standard `modules/`, icons, documentation, and the packaged `aerix-1.1.0-stable.vsix` editor extension.

## Structure

- `src/setup_main.cpp` — 6-page native Win32 Setup Wizard UI + silent CLI mode + uninstall flow
- `src/installer_engine.hpp` / `src/installer_engine.cpp` — `ARXP` zlib payload extraction, `HKCU\Environment` setup (`AERIX_HOME`, `AERIX_STDLIB`, `AERIX_STDLIB_PATH`, `AERIX_MODULE_PATH`, `Path`), `.arx` Explorer file associations & context menus, Add/Remove Programs registration, IDE extension deployment, and uninstaller cleanup
- `src/packager.cpp` — Deterministic C++17 asset packager creating `build/payload.bin`
- `src/resources.rc`, `src/resource.h`, `src/app.manifest` — Icons, wizard bitmaps, MIT `LICENSE`, DPI/UTF-8 manifest, and embedded `payload.bin`
- `src/installer_manifest.json` — Version and staged payload specification
- `build.ps1` — Builds native compiler seed binaries, `packager.exe`, `payload.bin`, and `dist/AerixSetup-1.1.0-stable.exe`

## Building

Requires GCC / G++ / windres (e.g. MinGW-w64 UCRT64 with `zlib`):

```powershell
powershell -ExecutionPolicy Bypass -File .\AerixInstaller\build.ps1
```

Output: `AerixInstaller/dist/AerixSetup-1.1.0-stable.exe`

## Silent / Automated Usage

```powershell
# Install silently to custom directory without touching registry or IDE extensions
.\AerixInstaller\dist\AerixSetup-1.1.0-stable.exe --silent --dir="C:\Tools\Aerix" --no-path --no-assoc --no-vscode --no-antigravity

# Standard interactive GUI wizard
.\AerixInstaller\dist\AerixSetup-1.1.0-stable.exe

# Silent uninstall (or invoke installed Uninstall.exe)
.\Uninstall.exe --uninstall --silent
```
