# Aerix C# Windows Installer (`AerixSetup`)

Standalone, zero-SDK **C# / WinForms (.NET Framework 4.x)** installer and uninstaller for the **Aerix Native Systems Programming Language (`1.2.19b`)**.

## Architecture

Compiles directly with the built-in Windows `.NET Framework v4.0.30319\csc.exe` into a self-contained single-file setup executable (`AerixSetup-1.2.19b.exe`) that embeds:
- `AerixPayload.zip` (native PE32+ compiler `arx.exe` & `arxc.exe`, `stdlib/aerix_rt.h`, `modules/`, icons, docs, unpacked extension fallback, and `aerix-1.2.19b.vsix`)
- `LICENSE`, `aerix.ico`, and `installer_manifest.json`

### Source Files (`src/`)
- `Program.cs` — CLI flag handling (`/S`, `--silent`, `--uninstall`, `--dir=...`, `--no-env`, `--no-assoc`, `--no-ide`, `--no-verify`) and GUI entrypoint
- `InstallerEngine.cs` — ZIP extraction with locked-binary safe swaps, legacy `~/.aerix/bin` sync, `HKCU\Environment` & `App Paths` setup, `.arx` Explorer associations/icons, stale extension pruning, multi-IDE VSIX deployment (`VS Code`, `VS Code Insiders`, `Antigravity`, `Antigravity IDE`, `Cursor`, `Windsurf`), live compiler smoke test, and clean uninstall + self-delete
- `SetupForm.cs` — Dark-obsidian / cyan GDI+ styled multi-step Windows setup & uninstall wizard
- `AssemblyInfo.cs`, `app.manifest`, `installer_manifest.json` — Version metadata, DPI awareness, and packaging manifest

## Build

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\AerixInstaller\build.ps1
```

Output: `AerixInstaller/dist/AerixSetup-1.2.19b.exe`

## Silent / CLI Usage

```powershell
# Custom non-interactive install
.\AerixInstaller\dist\AerixSetup-1.2.19b.exe --silent --dir="C:\Tools\Aerix" --no-env --no-assoc --no-ide --no-verify

# Interactive GUI setup
.\AerixInstaller\dist\AerixSetup-1.2.19b.exe

# Silent uninstall
"%LOCALAPPDATA%\Programs\Aerix\Uninstall.exe" --uninstall --silent
```
