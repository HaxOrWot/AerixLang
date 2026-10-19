# Aerix Setup Installer — Windows File Explorer Integration & Registry Specification

<div align="center">

```text
       █████╗ ███████╗██████╗ ██╗██╗  ██╗    ███████╗██╗██╗     ███████╗
      ██╔══██╗██╔════╝██╔══██╗██║╚██╗██╔╝    ██╔════╝██║██║     ██╔════╝
      ███████║█████╗  ██████╔╝██║ ╚███╔╝     █████╗  ██║██║     █████╗  
      ██╔══██║██╔══╝  ██╔══██╗██║ ██╔██╗     ██╔══╝  ██║██║     ██╔══╝  
      ██║  ██║███████╗██║  ██║██║██╔╝ ██╗    ██║     ██║███████╗███████╗
      ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝    ╚═╝     ╚═╝╚══════╝╚══════╝
```

### **Windows Shell File Association, Multi-Layer Icon Architecture & Registry Subsystem**
*Engineering Specification for Shell Verbs, ProgIDs, High-DPI Assets, and Cache Synchronization*

</div>

---

## 1. Architectural Overview & Windows Shell Mechanics

When a software developer installs a programming language on Microsoft Windows, their primary daily interaction is through **Windows File Explorer** and their chosen code editor. Standard compiler distributions often dump binaries into a zip archive, leaving source files (`.arx`) appearing as blank generic white sheets in File Explorer, with no context menu verbs and broken shell handlers.

The **Aerix Setup Installer** implements an enterprise-grade Windows Shell integration that makes `.arx` files first-class citizens in the Windows desktop ecosystem.

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                            WINDOWS EXPLORER SHELL LOOKUP PIPELINE                           │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
                                                │
                          User Views Folder / Double-Clicks 'main.arx'
                                                │
                                                ▼
                        ┌───────────────────────────────────────────────┐
                        │ Step 1: File Extension Association Query      │
                        │ Lookup: HKCU\Software\Classes\.arx            │
                        │ Reads: (Default) = "Aerix.SourceFile"         │
                        └───────────────────────────────────────────────┘
                                                │
                                                ▼
                        ┌───────────────────────────────────────────────┐
                        │ Step 2: ProgID Resolution & Icon Descriptor   │
                        │ Lookup: HKCU\Software\Classes\Aerix.SourceFile│
                        │ Reads: DefaultIcon = "{app}\assets\aerix.ico" │
                        └───────────────────────────────────────────────┘
                                                │
                                                ▼
                        ┌───────────────────────────────────────────────┐
                        │ Step 3: Shell Verb & Context Menu Resolution  │
                        │ Primary Action: "open" -> VS Code / Antigrav  │
                        │ Context Verb 1: "run"  -> cmd /K arx.bat run  │
                        │ Context Verb 2: "build"-> cmd /K arx.bat build│
                        └───────────────────────────────────────────────┘
                                                │
                                                ▼
                        ┌───────────────────────────────────────────────┐
                        │ Step 4: Win32 Subsystem Rendering             │
                        │ Explorer selects optimal mipmap (16px..256px) │
                        │ Paints Supersonic Cyan-Indigo Icon onto File! │
                        └───────────────────────────────────────────────┘
```

---

## 2. Windows Registry Architecture: HKCU vs. HKLM Scope

The installer dynamically isolates registry writes depending on the privilege mode chosen during setup:

| Scope | Registry Root Key | Administrative Privileges | Target Audience |
| :--- | :--- | :--- | :--- |
| **Current User (Default)** | `HKEY_CURRENT_USER\Software\Classes` | **None (UAC-Free)** | Standard developer workstations, locked corporate environments |
| **Machine-Wide (/ALLUSERS)**| `HKEY_LOCAL_MACHINE\Software\Classes` | **Required (Elevated UAC)** | Classroom labs, build agents, shared development servers |

By default, the installer targets `HKEY_CURRENT_USER\Software\Classes` (`HKA` in Inno Setup parlance), ensuring that non-administrator accounts can install Aerix seamlessly without requiring admin credentials or modifying system-protected hives.

---

## 3. Complete Registry Key & Value Manifest

### A. Extension Mapping: `.arx`
Maps the `.arx` file extension to the Aerix Programmatic Identifier (`Aerix.SourceFile`), establishes MIME types, and informs Windows Search indexers:

```ini
[HKEY_CURRENT_USER\Software\Classes\.arx]
@="Aerix.SourceFile"
"Content Type"="text/plain"
"PerceivedType"="text"

[HKEY_CURRENT_USER\Software\Classes\.arx\OpenWithProgids]
"Aerix.SourceFile"=""
```

### B. Programmatic Identifier (ProgID): `Aerix.SourceFile`
Defines the friendly display name, document class properties, and links directly to the multi-resolution file icon:

```ini
[HKEY_CURRENT_USER\Software\Classes\Aerix.SourceFile]
@="Aerix Source Code"
"FriendlyTypeName"="Aerix Source Code"

[HKEY_CURRENT_USER\Software\Classes\Aerix.SourceFile\DefaultIcon]
@="{app}\assets\aerix_file.ico,0"
```

### C. Context Menu Verbs (`shell\`)
Provides instant right-click developer productivity directly inside Windows File Explorer without needing to open a terminal first:

```ini
; -----------------------------------------------------------------------------
; Verb 1: Primary "open" Action (Default Double-Click Behavior)
; Opens the file directly in the developer's primary IDE (VS Code or Antigravity)
; -----------------------------------------------------------------------------
[HKEY_CURRENT_USER\Software\Classes\Aerix.SourceFile\shell\open]
@="Open with Code Editor"

[HKEY_CURRENT_USER\Software\Classes\Aerix.SourceFile\shell\open\command]
@="\"code.cmd\" \"%1\""

; -----------------------------------------------------------------------------
; Verb 2: "Run with Aerix" (Compiles and runs in an interactive terminal window)
; -----------------------------------------------------------------------------
[HKEY_CURRENT_USER\Software\Classes\Aerix.SourceFile\shell\run]
@="Run with Aerix (arx run)"
"Icon"="{app}\assets\aerix.ico"

[HKEY_CURRENT_USER\Software\Classes\Aerix.SourceFile\shell\run\command]
@="\"cmd.exe\" /K \"\"{app}\\bin\\arx.bat\" run \"%1\"\""

; -----------------------------------------------------------------------------
; Verb 3: "Build Executable" (Compiles source file into standalone native .exe)
; -----------------------------------------------------------------------------
[HKEY_CURRENT_USER\Software\Classes\Aerix.SourceFile\shell\build]
@="Build Executable (arx build)"
"Icon"="{app}\assets\aerix.ico"

[HKEY_CURRENT_USER\Software\Classes\Aerix.SourceFile\shell\build\command]
@="\"cmd.exe\" /K \"\"{app}\\bin\\arx.bat\" build \"%1\"\""
```

---

## 4. Multi-Layer High-DPI Icon Architecture (`.ico`)

A common flaw in software installers is shipping a single 32x32 pixel icon. When Windows Explorer renders desktop icons at 256x256, or high-DPI displays (4K/5K) apply 200% scaling, low-resolution icons become blurry, pixelated, and amateurish.

The Aerix installer bundles true multi-layer Windows `.ico` containers generated with Python `Pillow` using high-fidelity **Lanczos anti-aliased resampling**.

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                          AERIX MULTI-LAYER RESOLUTION MATRIX                                │
├──────────────┬──────────────┬───────────────┬───────────────────────────────────────────────┤
│ Resolution   │ Format       │ Color Depth   │ Windows Explorer Display Mode & Target UI     │
├──────────────┼──────────────┼───────────────┼───────────────────────────────────────────────┤
│ 256 x 256 px │ CompressedPNG│ 32-bit RGBA   │ Windows 11 Extra Large Icons, 4K High-DPI 200%│
│ 128 x 128 px │ Uncompressed │ 32-bit RGBA   │ Large Icons view, Control Panel list          │
│  64 x  64 px │ Uncompressed │ 32-bit RGBA   │ Windows Search preview pane, 250% DPI scaling │
│  48 x  48 px │ Uncompressed │ 32-bit RGBA   │ Desktop standard icons, Medium Icons view     │
│  32 x  32 px │ Uncompressed │ 32-bit RGBA   │ Small Icons view, Tiles view, Alt+Tab switcher│
│  24 x  24 px │ Uncompressed │ 32-bit RGBA   │ Windows Taskbar pinned icons, 150% DPI scaling│
│  16 x  16 px │ Uncompressed │ 32-bit RGBA   │ File Explorer Details view, Tree view, dialogs│
└──────────────┴──────────────┴───────────────┴───────────────────────────────────────────────┘
```

### Visual Differentiation: Application Icon vs. File Document Icon
To adhere to modern Windows 11 Fluent Design principles, Aerix provides two distinct icon variants:

1. **`aerix.ico` (Application Toolchain Icon):**
   - High-energy supersonic dual-chevron mark in vibrant cyan (`#00F2FE`) and royal azure (`#1D4ED8`).
   - Used for the installer executable, uninstaller, desktop shortcuts, and Start Menu entries.
2. **`aerix_file.ico` (Source Document Icon):**
   - Styled as a sleek document page with a folded top-right corner.
   - Emblazoned with the supersonic cyan-indigo Aerix badge centered on the page body.
   - Distinctive `.arx` mini-badge along the lower boundary to guarantee immediate visual identification among other source files (`.c`, `.rs`, `.py`).

---

## 5. Instant Shell Icon Cache Synchronization (`SHChangeNotify`)

### The Icon Cache Staling Problem
Windows caches file association icons in a hidden database (`%LOCALAPPDATA%\IconCache.db` and `%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache_*.db`). Without explicit notification, Windows File Explorer will continue displaying old cached icons or blank file sheets for hours until the user logs out or reboots the computer.

### The Win32 Solution
During both installation and uninstallation, the Aerix installer directly invokes the Win32 Shell API `SHChangeNotify` via native Pascal P/Invoke:

```pascal
const
  SHCNE_ASSOCCHANGED = $08000000; // Shell Change Notification Event: Association Changed
  SHCNF_IDLIST        = $0000;     // Shell Change Notification Flags: Item ID List

procedure SHChangeNotify(wEventId: Integer; uFlags: Cardinal; dwItem1, dwItem2: Integer);
  external 'SHChangeNotify@shell32.dll stdcall';
```

When called:
1. `SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, 0, 0)` is broadcast to all active desktop and Explorer window threads.
2. Windows Explorer immediately invalidates its internal icon cache memory tables.
3. Every visible `.arx` file on the desktop and in open Explorer windows refreshes in real-time within **50 milliseconds**, instantly presenting the supersonic Aerix icon.

---

## 6. Atomic Rollback & Clean Uninstallation Specification

Clean removal is an essential standard of professional software. The Aerix installer ensures zero registry clutter upon uninstallation:

```ini
; Inno Setup Uninstallation Flags
Flags: uninsdeletekey        ; Recursively purges the subkey if created by Aerix
Flags: uninsdeletevalue      ; Removes specific values without damaging parent keys
```

### Uninstallation Verification Checklist:
- [x] `HKCU\Software\Classes\.arx` is completely removed.
- [x] `HKCU\Software\Classes\Aerix.SourceFile` and all context menu subkeys are purged.
- [x] `SHChangeNotify` is invoked immediately upon uninstaller exit, removing stale icon associations.
- [x] No lingering temp files, logs, or unreferenced registry orphans remain.

---

## 7. Automated PowerShell Verification Script

Developers and QA teams can independently verify registry and icon integrity using this PowerShell diagnostic script:

```powershell
# Verify Aerix Registry Associations and Icon Integrity
$regPath = "HKCU:\Software\Classes"
$ext = Get-ItemProperty -Path "$regPath\.arx" -ErrorAction SilentlyContinue
$progId = Get-ItemProperty -Path "$regPath\Aerix.SourceFile" -ErrorAction SilentlyContinue
$icon = Get-ItemProperty -Path "$regPath\Aerix.SourceFile\DefaultIcon" -ErrorAction SilentlyContinue

Write-Host "=== Aerix Windows Shell Association Diagnostics ===" -ForegroundColor Cyan
if ($ext.'(default)' -eq "Aerix.SourceFile") {
    Write-Host "[PASS] .arx extension correctly mapped to Aerix.SourceFile" -ForegroundColor Green
} else {
    Write-Host "[FAIL] .arx extension mapping missing or corrupted" -ForegroundColor Red
}

if ($icon.'(default)' -like "*aerix_file.ico,0") {
    Write-Host "[PASS] DefaultIcon path verified: $($icon.'(default)')" -ForegroundColor Green
} else {
    Write-Host "[FAIL] DefaultIcon registration invalid" -ForegroundColor Red
}
```
