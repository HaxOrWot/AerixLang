# Windows File Explorer Integration & Icon Specification

## 1. How Windows Explorer Renders File Icons

Windows File Explorer does not inspect program extensions or language plugins to determine how a file looks. Instead, Windows evaluates the **Windows Registry** using a 3-step lookup mechanism:

```text
[Windows Explorer Double-Clicks / Views 'main.arx']
                     │
                     ▼
1. Lookup Extension in Registry:
   HKCU\Software\Classes\.arx  ──> (Default) = "Aerix.SourceFile"
                     │
                     ▼
2. Resolve ProgID & Default Icon:
   HKCU\Software\Classes\Aerix.SourceFile\DefaultIcon
   ──> (Default) = "C:\Users\<User>\AppData\Local\Programs\Aerix\assets\aerix_file.ico,0"
                     │
                     ▼
3. Windows Explorer paints the high-res Aerix Supersonic Icon directly onto 'main.arx'!
```

---

## 2. Complete Registry Key Specification

The installer writes the following keys to `HKEY_CURRENT_USER\Software\Classes` (User scope) or `HKEY_LOCAL_MACHINE\Software\Classes` (System scope):

### A. Extension Mapping (`.arx`)
```ini
[HKEY_CURRENT_USER\Software\Classes\.arx]
@="Aerix.SourceFile"
"Content Type"="text/plain"
"PerceivedType"="text"

[HKEY_CURRENT_USER\Software\Classes\.arx\OpenWithProgids]
"Aerix.SourceFile"=""
```

### B. Program ID & Document Description
```ini
[HKEY_CURRENT_USER\Software\Classes\Aerix.SourceFile]
@="Aerix Source Code"
"FriendlyTypeName"="Aerix Source Code (.arx)"

[HKEY_CURRENT_USER\Software\Classes\Aerix.SourceFile\DefaultIcon]
@="{app}\assets\aerix_file.ico,0"
```

### C. Right-Click Context Menu Verbs
Users can right-click any `.arx` file on their desktop or folders and execute actions directly:

```ini
; 1. "Run with Aerix" (Compiles and runs in interactive terminal)
[HKEY_CURRENT_USER\Software\Classes\Aerix.SourceFile\shell\run]
@="Run with Aerix"
"Icon"="{app}\assets\aerix.ico"

[HKEY_CURRENT_USER\Software\Classes\Aerix.SourceFile\shell\run\command]
@="\"cmd.exe\" /K \"\"{app}\\bin\\arx.exe\" run \"%1\"\""

; 2. "Build with Aerix" (Compiles to native .exe)
[HKEY_CURRENT_USER\Software\Classes\Aerix.SourceFile\shell\build]
@="Build Executable (arx build)"
"Icon"="{app}\assets\aerix.ico"

[HKEY_CURRENT_USER\Software\Classes\Aerix.SourceFile\shell\build\command]
@="\"cmd.exe\" /K \"\"{app}\\bin\\arx.exe\" build \"%1\"\""

; 3. "Open in Visual Studio Code"
[HKEY_CURRENT_USER\Software\Classes\Aerix.SourceFile\shell\open]
@="Open with VS Code"

[HKEY_CURRENT_USER\Software\Classes\Aerix.SourceFile\shell\open\command]
@="\"code.cmd\" \"%1\""
```

---

## 3. High-Resolution Icon Layer Architecture

To prevent icons from looking blurry or pixelated when switching between Windows Explorer views (Details, List, Tiles, Large Icons, Extra Large Icons), `aerix.ico` and `aerix_file.ico` must contain 7 distinct resolution layers:

```text
┌─────────────────────────────────────────────────────────────┐
│                 AERIX MULTI-LAYER .ICO SPEC                 │
├──────────────┬───────────────┬──────────────────────────────┤
│ Resolution   │ Color Depth   │ Windows Explorer Display Mode│
├──────────────┼───────────────┼──────────────────────────────┤
│ 256 x 256    │ 32-bit RGBA   │ Extra Large Icons view / 4K  │
│ 128 x 128    │ 32-bit RGBA   │ Large Icons view             │
│ 64 x 64      │ 32-bit RGBA   │ Medium-Large Icons view      │
│ 48 x 48      │ 32-bit RGBA   │ Medium Icons view / Desktop  │
│ 32 x 32      │ 32-bit RGBA   │ Small Icons / Tiles view     │
│ 24 x 24      │ 32-bit RGBA   │ Taskbar / High-DPI 150% list │
│ 16 x 16      │ 32-bit RGBA   │ Details view / File dialogs  │
└──────────────┴───────────────┴──────────────────────────────┘
```

---

## 4. Immediate Icon Cache Invalidation

When new file associations are registered, Windows often keeps previous cached icons until restart.

To force Windows Explorer to refresh its icon cache **instantaneously without rebooting**, the installer executes a Win32 Shell API notification immediately after writing the registry keys:

```c
// Force Windows Shell to reload all registered file icons:
SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, NULL, NULL);
```

In PowerShell or batch scripts, this is achieved via:
```powershell
[Windows.Shell.ChangeNotify]::NotifyAssocChanged()
# Or via ie4uinit:
ie4uinit.exe -show
```
The exact second the installer completes, all `.arx` files transform into the custom Aerix icon.
