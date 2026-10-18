<#
.SYNOPSIS
    Registers the .arx file extension, Windows Explorer icon, and shell verbs in the Windows Registry.
.DESCRIPTION
    Associates .arx files with Aerix, sets DefaultIcon to aerix_file.ico,
    adds Explorer context menu actions (Run, Build, Open with VS Code),
    and flushes the Windows Shell icon cache.
#>

param(
    [string]$InstallDir = ""
)

if (-not $InstallDir) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $InstallDir = Resolve-Path (Join-Path $scriptDir "..\..")
}

$arxBin     = Join-Path $InstallDir "bin\arx.exe"
if (-not (Test-Path $arxBin)) {
    $arxBin = Join-Path $InstallDir "arx.bat"
}
$appIcon    = Join-Path $InstallDir "AerixInstaller\assets\aerix.ico"
if (-not (Test-Path $appIcon)) {
    $appIcon = Join-Path $InstallDir "assets\aerix.ico"
}
$fileIcon   = Join-Path $InstallDir "AerixInstaller\assets\aerix_file.ico"
if (-not (Test-Path $fileIcon)) {
    $fileIcon = Join-Path $InstallDir "assets\aerix_file.ico"
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Aerix - Windows File Explorer Icon & Association Register" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "[*] Install Directory: $InstallDir" -ForegroundColor Gray
Write-Host "[*] File Icon:        $fileIcon" -ForegroundColor Gray

# 1. Register .arx Extension
$extPath = "HKCU:\Software\Classes\.arx"
New-Item -Path $extPath -Force | Out-Null
Set-ItemProperty -Path $extPath -Name "(Default)" -Value "Aerix.SourceFile"
Set-ItemProperty -Path $extPath -Name "Content Type" -Value "text/plain"
Set-ItemProperty -Path $extPath -Name "PerceivedType" -Value "text"

# OpenWithProgids
$openWithPath = "HKCU:\Software\Classes\.arx\OpenWithProgids"
New-Item -Path $openWithPath -Force | Out-Null
Set-ItemProperty -Path $openWithPath -Name "Aerix.SourceFile" -Value ""

# 2. Register ProgID (Aerix.SourceFile)
$progIdPath = "HKCU:\Software\Classes\Aerix.SourceFile"
New-Item -Path $progIdPath -Force | Out-Null
Set-ItemProperty -Path $progIdPath -Name "(Default)" -Value "Aerix Source Code"
Set-ItemProperty -Path $progIdPath -Name "FriendlyTypeName" -Value "Aerix Source Code (.arx)"

# 3. Register DefaultIcon (This makes the custom icon show up in Explorer!)
$iconPath = "HKCU:\Software\Classes\Aerix.SourceFile\DefaultIcon"
New-Item -Path $iconPath -Force | Out-Null
Set-ItemProperty -Path $iconPath -Name "(Default)" -Value "$fileIcon,0"

# 4. Register Shell Verbs
# Verb: Open in VS Code
$openCmdPath = "HKCU:\Software\Classes\Aerix.SourceFile\shell\open"
New-Item -Path $openCmdPath -Force | Out-Null
Set-ItemProperty -Path $openCmdPath -Name "(Default)" -Value "Open with VS Code"
$openExecPath = Join-Path $openCmdPath "command"
New-Item -Path $openExecPath -Force | Out-Null
Set-ItemProperty -Path $openExecPath -Name "(Default)" -Value "cmd.exe /c code `"%1`""

# Verb: Run with Aerix
$runCmdPath = "HKCU:\Software\Classes\Aerix.SourceFile\shell\run"
New-Item -Path $runCmdPath -Force | Out-Null
Set-ItemProperty -Path $runCmdPath -Name "(Default)" -Value "Run with Aerix"
Set-ItemProperty -Path $runCmdPath -Name "Icon" -Value "$appIcon"
$runExecPath = Join-Path $runCmdPath "command"
New-Item -Path $runExecPath -Force | Out-Null
Set-ItemProperty -Path $runExecPath -Name "(Default)" -Value "cmd.exe /K `"`"$arxBin`" run `"%1`"`""

# Verb: Build with Aerix
$buildCmdPath = "HKCU:\Software\Classes\Aerix.SourceFile\shell\build"
New-Item -Path $buildCmdPath -Force | Out-Null
Set-ItemProperty -Path $buildCmdPath -Name "(Default)" -Value "Build Executable (arx build)"
Set-ItemProperty -Path $buildCmdPath -Name "Icon" -Value "$appIcon"
$buildExecPath = Join-Path $buildCmdPath "command"
New-Item -Path $buildExecPath -Force | Out-Null
Set-ItemProperty -Path $buildExecPath -Name "(Default)" -Value "cmd.exe /K `"`"$arxBin`" build `"%1`"`""

Write-Host "[OK] Registry keys registered successfully." -ForegroundColor Green

# 5. Flush Windows Shell Icon Cache
Write-Host "[*] Refreshing Windows Explorer icon cache..." -ForegroundColor Gray
try {
    # Use C# P/Invoke to trigger SHChangeNotify
    $code = @"
    using System;
    using System.Runtime.InteropServices;
    public class ShellNotifier {
        [DllImport("shell32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        public static extern void SHChangeNotify(int wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);
    }
"@
    Add-Type -TypeDefinition $code -ErrorAction SilentlyContinue
    [ShellNotifier]::SHChangeNotify(0x08000000, 0x0000, [IntPtr]::Zero, [IntPtr]::Zero) # SHCNE_ASSOCCHANGED
    Write-Host "[SUCCESS] Windows Explorer refreshed! .arx files now display the Aerix icon." -ForegroundColor Green
} catch {
    Write-Host "[!] Note: Restart Explorer or sign out if icons do not refresh immediately." -ForegroundColor Yellow
}
