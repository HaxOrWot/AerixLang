# Aerix (arx) - Universal Windows PowerShell Installer & Setup Engine
param(
    [switch]$OnlyExtensions,
    [string]$VsixPath,
    [switch]$VSCode,
    [switch]$Antigravity,
    [switch]$UninstallExtensions
)

$ErrorActionPreference = "Stop"

# Resolve source location (script root or current directory)
$scriptDir = $PSScriptRoot
if (-not $scriptDir) {
    $scriptDir = (Get-Location).Path
}

$aerixHome    = Join-Path $HOME ".aerix"
$aerixEditors = Join-Path $aerixHome "editors"

# -----------------------------------------------------------------
# Dedicated Extension Uninstallation Handler
# -----------------------------------------------------------------
if ($UninstallExtensions) {
    # Check Antigravity IDE
    $antigravityPaths = @(
        (Get-Command "antigravity-ide" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
        (Get-Command "antigravity" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
        (Join-Path $env:LOCALAPPDATA "Programs\Antigravity IDE\bin\antigravity-ide.cmd"),
        "X:\Antigravity IDE\bin\antigravity-ide.cmd",
        "X:\Antigravity\bin\antigravity.cmd",
        (Join-Path $env:ProgramFiles "Antigravity IDE\bin\antigravity-ide.cmd")
    )
    foreach ($p in $antigravityPaths) {
        if ($p -and (Test-Path $p)) {
            & $p --uninstall-extension aerix-lang.aerix 2>&1 | Out-Null
            break
        }
    }

    # Check VS Code
    $codePaths = @(
        (Get-Command "code" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
        (Join-Path $env:LOCALAPPDATA "Programs\Microsoft VS Code\bin\code.cmd"),
        (Join-Path $env:ProgramFiles "Microsoft VS Code\bin\code.cmd"),
        "C:\Program Files (x86)\Microsoft VS Code\bin\code.cmd"
    )
    foreach ($p in $codePaths) {
        if ($p -and (Test-Path $p)) {
            & $p --uninstall-extension aerix-lang.aerix 2>&1 | Out-Null
            break
        }
    }

    # Remove direct extension directories
    $extDirs = @(
        (Join-Path $HOME ".vscode\extensions\aerix-lang.aerix-1.0.84"),
        (Join-Path $HOME ".antigravity\extensions\aerix-lang.aerix-1.0.84"),
        (Join-Path $HOME ".antigravity-ide\extensions\aerix-lang.aerix-1.0.84")
    )
    foreach ($dir in $extDirs) {
        if (Test-Path $dir) {
            Remove-Item -Path $dir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    exit 0
}

# -----------------------------------------------------------------
# Dedicated Extension Installation Handler (Invoked by AerixSetup)
# -----------------------------------------------------------------
if ($OnlyExtensions) {
    if (-not $VsixPath -or -not (Test-Path $VsixPath)) {
        $candidates = @(
            (Join-Path $scriptDir "..\editors\vscode-aerix\aerix-1.0.84.vsix"),
            (Join-Path $scriptDir "..\editors\aerix-1.0.84.vsix"),
            (Join-Path $scriptDir "editors\aerix-1.0.84.vsix"),
            (Join-Path $scriptDir "aerix-1.0.84.vsix"),
            (Join-Path $aerixEditors "aerix-1.0.84.vsix"),
            (Join-Path $aerixEditors "aerix-1.0.82.vsix")
        )
        foreach ($c in $candidates) {
            if ($c -and (Test-Path $c)) {
                $VsixPath = (Resolve-Path $c).Path
                break
            }
        }
    }

    if (-not $VsixPath -or -not (Test-Path $VsixPath)) {
        Write-Warning "Aerix VSIX extension not found."
        exit 1
    }

    if (-not $VSCode -and -not $Antigravity) {
        $VSCode = $true
        $Antigravity = $true
    }

    # Install Antigravity IDE Extension
    if ($Antigravity) {
        $antigravityPaths = @(
            (Get-Command "antigravity-ide" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
            (Get-Command "antigravity" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
            (Join-Path $env:LOCALAPPDATA "Programs\Antigravity IDE\bin\antigravity-ide.cmd"),
            "X:\Antigravity IDE\bin\antigravity-ide.cmd",
            "X:\Antigravity\bin\antigravity.cmd",
            (Join-Path $env:ProgramFiles "Antigravity IDE\bin\antigravity-ide.cmd")
        )
        $antigravityCmd = $null
        foreach ($p in $antigravityPaths) {
            if ($p -and (Test-Path $p)) {
                $antigravityCmd = $p
                break
            }
        }

        if ($antigravityCmd) {
            Write-Host "[*] Found Antigravity IDE at '$antigravityCmd'. Installing extension..." -ForegroundColor Gray
            $prevEAP = $ErrorActionPreference
            $ErrorActionPreference = "SilentlyContinue"
            & $antigravityCmd --install-extension $VsixPath --force 2>&1 | Out-Null
            $ErrorActionPreference = $prevEAP
            Write-Host "[OK] Installed Aerix extension into Antigravity IDE!" -ForegroundColor Green
        }
    }

    # Install VS Code Extension
    if ($VSCode) {
        $codePaths = @(
            (Get-Command "code" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
            (Join-Path $env:LOCALAPPDATA "Programs\Microsoft VS Code\bin\code.cmd"),
            (Join-Path $env:ProgramFiles "Microsoft VS Code\bin\code.cmd"),
            "C:\Program Files (x86)\Microsoft VS Code\bin\code.cmd"
        )
        $codeCmd = $null
        foreach ($p in $codePaths) {
            if ($p -and (Test-Path $p)) {
                $codeCmd = $p
                break
            }
        }

        if ($codeCmd) {
            Write-Host "[*] Found VS Code at '$codeCmd'. Installing extension..." -ForegroundColor Gray
            $prevEAP = $ErrorActionPreference
            $ErrorActionPreference = "SilentlyContinue"
            & $codeCmd --install-extension $VsixPath --force 2>&1 | Out-Null
            $ErrorActionPreference = $prevEAP
            Write-Host "[OK] Installed Aerix extension into VS Code!" -ForegroundColor Green
        }
    }

    exit 0
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "    ___         _      " -ForegroundColor Cyan
Write-Host "   / _ \___ ___(_)_ __ " -ForegroundColor Cyan
Write-Host "  / __ / -_) __/ /\ \ /" -ForegroundColor Cyan
Write-Host " /_/ |_\__/_/ /_//_\_\ " -ForegroundColor Cyan
Write-Host " Aerix Programming Language - Universal Windows Installer" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$aerixHome    = Join-Path $HOME ".aerix"
$aerixBin     = Join-Path $aerixHome "bin"
$aerixStdlib  = Join-Path $aerixHome "stdlib"
$aerixEditors = Join-Path $aerixHome "editors"

Write-Host "[*] Target installation directory: $aerixHome" -ForegroundColor Gray
New-Item -ItemType Directory -Path $aerixBin -Force | Out-Null
New-Item -ItemType Directory -Path $aerixStdlib -Force | Out-Null
New-Item -ItemType Directory -Path $aerixEditors -Force | Out-Null

# Resolve source location (script root or current directory)
$scriptDir = $PSScriptRoot
if (-not $scriptDir) {
    $scriptDir = (Get-Location).Path
}

# Potential local file paths
$localDistArx  = Join-Path $scriptDir "dist\arx.exe"
$localDistArxc = Join-Path $scriptDir "dist\arxc.exe"
$localRtHeader = Join-Path $scriptDir "stdlib\aerix_rt.h"
$localVsixCandidate = Get-ChildItem -Path (Join-Path $scriptDir "editors\vscode-aerix") -Filter "*.vsix" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$localVsix = if ($localVsixCandidate) { $localVsixCandidate.FullName } else { Join-Path $scriptDir "editors\vscode-aerix\aerix-1.0.82.vsix" }

# GitHub fallback repository
$GitHubRepo = if ($env:AERIX_REPO) { $env:AERIX_REPO } else { "HaxOrWot/AerixLang" }
$ReleaseBase = "https://github.com/$GitHubRepo/releases/latest/download"
$RawBase     = "https://raw.githubusercontent.com/$GitHubRepo/main"

# ----------------------------------------------------
# 1. Install Toolchain Binaries (arx.exe and arxc.exe)
# ----------------------------------------------------
if (Test-Path $localDistArx) {
    Write-Host "[*] Installing local standalone toolchain (arx.exe)..." -ForegroundColor Gray
    Copy-Item -Path $localDistArx -Destination (Join-Path $aerixBin "arx.exe") -Force
    $localDistCore = Join-Path $scriptDir "dist\arx_core.exe"
    if (Test-Path $localDistCore) {
        Copy-Item -Path $localDistCore -Destination (Join-Path $aerixBin "arx_core.exe") -Force
    }
} else {
    Write-Host "[*] Fetching arx.exe from GitHub Release ($ReleaseBase/arx.exe)..." -ForegroundColor Gray
    try {
        Invoke-WebRequest -Uri "$ReleaseBase/arx.exe" -OutFile (Join-Path $aerixBin "arx.exe") -UseBasicParsing
    } catch {
        Write-Host "[!] Could not download arx.exe from GitHub release. Skipping remote fetch." -ForegroundColor Yellow
    }
}

if (Test-Path $localDistArxc) {
    Write-Host "[*] Installing local standalone compiler (arxc.exe)..." -ForegroundColor Gray
    Copy-Item -Path $localDistArxc -Destination (Join-Path $aerixBin "arxc.exe") -Force
} else {
    Write-Host "[*] Fetching arxc.exe from GitHub Release ($ReleaseBase/arxc.exe)..." -ForegroundColor Gray
    try {
        Invoke-WebRequest -Uri "$ReleaseBase/arxc.exe" -OutFile (Join-Path $aerixBin "arxc.exe") -UseBasicParsing
    } catch {
        Write-Host "[!] Could not download arxc.exe from GitHub release." -ForegroundColor Yellow
    }
}

# ----------------------------------------------------
# 2. Install Runtime Standard Library (aerix_rt.h)
# ----------------------------------------------------
$targetRt = Join-Path $aerixStdlib "aerix_rt.h"
if (Test-Path $localRtHeader) {
    Copy-Item -Path $localRtHeader -Destination $targetRt -Force
    Write-Host "[OK] Installed runtime stdlib to: $aerixStdlib" -ForegroundColor Green
} else {
    Write-Host "[*] Fetching aerix_rt.h from GitHub raw repository..." -ForegroundColor Gray
    try {
        Invoke-WebRequest -Uri "$RawBase/stdlib/aerix_rt.h" -OutFile $targetRt -UseBasicParsing
        Write-Host "[OK] Downloaded runtime stdlib to: $aerixStdlib" -ForegroundColor Green
    } catch {
        Write-Host "[!] Could not download aerix_rt.h." -ForegroundColor Yellow
    }
}

# ----------------------------------------------------
# 3. Cache Extension VSIX
# ----------------------------------------------------
$targetVsix = Join-Path $aerixEditors "aerix-1.0.82.vsix"
if ($localVsix -and (Test-Path $localVsix)) {
    Copy-Item -Path $localVsix -Destination $targetVsix -Force
} elseif (-not (Test-Path $targetVsix)) {
    try {
        Invoke-WebRequest -Uri "$ReleaseBase/aerix-1.0.82.vsix" -OutFile $targetVsix -UseBasicParsing
    } catch {
        # Optional extension download
    }
}

# ----------------------------------------------------
# 4. Install Editor Extension (Antigravity IDE & VS Code)
# ----------------------------------------------------
if (Test-Path $targetVsix) {
    # Check Antigravity IDE
    $antigravityPaths = @(
        (Get-Command "antigravity-ide" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
        (Join-Path $env:LOCALAPPDATA "Programs\Antigravity IDE\bin\antigravity-ide.cmd"),
        "X:\Antigravity IDE\bin\antigravity-ide.cmd",
        (Join-Path $env:ProgramFiles "Antigravity IDE\bin\antigravity-ide.cmd")
    )
    $antigravityCmd = $null
    foreach ($p in $antigravityPaths) {
        if ($p -and (Test-Path $p)) {
            $antigravityCmd = $p
            break
        }
    }

    if ($antigravityCmd) {
        Write-Host "[*] Found Antigravity IDE at '$antigravityCmd'. Installing extension..." -ForegroundColor Gray
        $prevEAP = $ErrorActionPreference
        $ErrorActionPreference = "SilentlyContinue"
        & $antigravityCmd --install-extension $targetVsix --force 2>&1 | Out-Null
        $ErrorActionPreference = $prevEAP
        Write-Host "[OK] Installed Aerix extension into Antigravity IDE!" -ForegroundColor Green
    }

    # Check VS Code
    $codePaths = @(
        (Get-Command "code" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
        (Join-Path $env:LOCALAPPDATA "Programs\Microsoft VS Code\bin\code.cmd"),
        (Join-Path $env:ProgramFiles "Microsoft VS Code\bin\code.cmd")
    )
    $codeCmd = $null
    foreach ($p in $codePaths) {
        if ($p -and (Test-Path $p)) {
            $codeCmd = $p
            break
        }
    }

    if ($codeCmd) {
        Write-Host "[*] Found VS Code at '$codeCmd'. Installing extension..." -ForegroundColor Gray
        $prevEAP = $ErrorActionPreference
        $ErrorActionPreference = "SilentlyContinue"
        & $codeCmd --install-extension $targetVsix --force 2>&1 | Out-Null
        $ErrorActionPreference = $prevEAP
        Write-Host "[OK] Installed Aerix extension into VS Code!" -ForegroundColor Green
    }
}

# ----------------------------------------------------
# 5. Add to User PATH
# ----------------------------------------------------
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$aerixBin*") {
    Write-Host "[*] Adding $aerixBin to User PATH..." -ForegroundColor Gray
    $newPath = if ($userPath) { "$userPath;$aerixBin" } else { $aerixBin }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    $env:Path = "$aerixBin;" + $env:Path
    Write-Host "[OK] Added Aerix to User PATH." -ForegroundColor Green
} else {
    Write-Host "[OK] Aerix is already present in User PATH." -ForegroundColor Green
    if ($env:Path -notlike "*$aerixBin*") {
        $env:Path = "$aerixBin;" + $env:Path
    }
}

# ----------------------------------------------------
# 6. Verify C Compiler (Backend)
# ----------------------------------------------------
$gccCmd = Get-Command "gcc" -ErrorAction SilentlyContinue
$clangCmd = Get-Command "clang" -ErrorAction SilentlyContinue
if ($gccCmd) {
    Write-Host "[OK] Native C Compiler: GCC detected at $($gccCmd.Source)" -ForegroundColor Green
} elseif ($clangCmd) {
    Write-Host "[OK] Native C Compiler: Clang detected at $($clangCmd.Source)" -ForegroundColor Green
} else {
    Write-Host "[!] Warning: No C compiler (GCC or Clang) detected on PATH." -ForegroundColor Yellow
    Write-Host "    Aerix requires a C compiler for native binary generation." -ForegroundColor Yellow
    Write-Host "    Quick install via Windows Terminal:" -ForegroundColor Yellow
    Write-Host "      winget install -e --id MSYS2.MSYS2" -ForegroundColor Cyan
}

# ----------------------------------------------------
# 7. Run Aerix Diagnostics
# ----------------------------------------------------
$arxExe = Join-Path $aerixBin "arx.exe"
if (Test-Path $arxExe) {
    Write-Host ""
    & $arxExe doctor
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "[SUCCESS] Aerix is ready to use!" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "Available commands anywhere in your terminal:"
Write-Host "  arx run <file.arx>    - Compile and run instantly"
Write-Host "  arxc <file.arx>       - Compile standalone native .exe"
Write-Host "  arx new <project>     - Generate project template"
Write-Host "  arx doctor            - Check environment health"
Write-Host ""
