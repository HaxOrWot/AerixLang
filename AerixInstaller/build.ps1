$ErrorActionPreference = "Stop"

$installerDir = $PSScriptRoot
$repoRoot     = Split-Path -Parent $installerDir
$srcDir       = Join-Path $installerDir "src"
$buildDir     = Join-Path $installerDir "build"
$stageDir     = Join-Path $buildDir "stage"
$distDir      = Join-Path $installerDir "dist"

$manifest = Get-Content (Join-Path $srcDir "installer_manifest.json") -Raw | ConvertFrom-Json
$version  = $manifest.version

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "     AERIX C# WINDOWS INSTALLER BUILDER (v$version)" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

if (Test-Path $buildDir) { Remove-Item $buildDir -Recurse -Force }
New-Item -ItemType Directory -Path (Join-Path $stageDir "bin") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $stageDir "stdlib") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $stageDir "modules") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $stageDir "editors\extension") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $stageDir "assets") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $stageDir "docs") -Force | Out-Null
New-Item -ItemType Directory -Path $distDir -Force | Out-Null

# 1. Compile native self-hosting compiler binaries (arxc.exe & arx.exe)
Write-Host "[1/4] Compiling native self-hosting compiler from C99 seed..."
$seedC   = Join-Path $repoRoot "src\bootstrap\seed\arxc.c"
$stdlibI = Join-Path $repoRoot "stdlib"
$arxcOut = Join-Path $stageDir "bin\arxc.exe"
$arxOut  = Join-Path $stageDir "bin\arx.exe"
& gcc -std=c99 -O2 -static -Wno-unused-function -I "$stdlibI" "$seedC" -o "$arxcOut" -lm
if ($LASTEXITCODE -ne 0) { throw "Failed to compile arxc.exe from seed" }
Copy-Item $arxcOut $arxOut -Force

# 2. Stage runtime header, standard modules, extension, icons, docs
Write-Host "[2/4] Staging stdlib, modules, extension, icons, and docs..."
Copy-Item (Join-Path $repoRoot "stdlib\aerix_rt.h") (Join-Path $stageDir "stdlib\aerix_rt.h") -Force
Copy-Item (Join-Path $repoRoot "modules\*") (Join-Path $stageDir "modules") -Recurse -Force

$vsixName = "aerix-$version.vsix"
$vsixSrc  = Join-Path $repoRoot "editors\vscode-aerix\$vsixName"
if (-not (Test-Path $vsixSrc)) { throw "Missing packaged extension: $vsixSrc" }
Copy-Item $vsixSrc (Join-Path $stageDir "editors\$vsixName") -Force
Get-ChildItem (Join-Path $repoRoot "editors\vscode-aerix") | Where-Object { $_.Extension -ne ".vsix" } | ForEach-Object {
    Copy-Item $_.FullName (Join-Path $stageDir "editors\extension\$($_.Name)") -Recurse -Force
}

Copy-Item (Join-Path $installerDir "assets\aerix.ico") (Join-Path $stageDir "assets\aerix.ico") -Force
Copy-Item (Join-Path $installerDir "assets\aerix_file.ico") (Join-Path $stageDir "assets\aerix_file.ico") -Force
Copy-Item (Join-Path $repoRoot "README.md") (Join-Path $stageDir "docs\README.md") -Force
Copy-Item (Join-Path $repoRoot "USER.md") (Join-Path $stageDir "docs\USER.md") -Force
Copy-Item (Join-Path $repoRoot "GUIDE.md") (Join-Path $stageDir "docs\GUIDE.md") -Force
Copy-Item (Join-Path $repoRoot "LICENSE") (Join-Path $stageDir "LICENSE") -Force

# 3. Compress staged tree into embedded AerixPayload.zip
Write-Host "[3/4] Compressing AerixPayload.zip..."
$payloadZip = Join-Path $buildDir "AerixPayload.zip"
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($stageDir, $payloadZip, [System.IO.Compression.CompressionLevel]::Optimal, $false)
$zipMB = [Math]::Round((Get-Item $payloadZip).Length / 1MB, 2)
Write-Host "  [OK] Packed AerixPayload.zip ($zipMB MB)"

# 4. Compile standalone C# Setup executable via built-in .NET Framework csc.exe
Write-Host "[4/4] Compiling standalone C# setup executable..."
Get-ChildItem $distDir -Filter "AerixSetup-*.exe" | Where-Object { $_.Name -ne "AerixSetup-$version.exe" } | Remove-Item -Force
$setupExe = Join-Path $distDir "AerixSetup-$version.exe"

$fwDir = Join-Path $env:windir "Microsoft.NET\Framework64\v4.0.30319"
$csc   = Join-Path $fwDir "csc.exe"
if (-not (Test-Path $csc)) { throw "Missing .NET Framework C# compiler: $csc" }

$appIcon     = Join-Path $installerDir "assets\aerix.ico"
$brandPng    = Join-Path $repoRoot "editors\vscode-aerix\icons\aerix-icon.png"
$appManifest = Join-Path $srcDir "app.manifest"
$licenseFile = Join-Path $repoRoot "LICENSE"
$manifestRes = Join-Path $srcDir "installer_manifest.json"

& $csc /nologo /target:winexe /platform:x64 /optimize+ /warnaserror `
    /out:"$setupExe" `
    /win32icon:"$appIcon" `
    /win32manifest:"$appManifest" `
    /reference:"$fwDir\System.dll" `
    /reference:"$fwDir\System.Core.dll" `
    /reference:"$fwDir\System.Drawing.dll" `
    /reference:"$fwDir\System.Windows.Forms.dll" `
    /reference:"$fwDir\System.IO.Compression.dll" `
    /reference:"$fwDir\System.IO.Compression.FileSystem.dll" `
    /reference:"$fwDir\System.Web.Extensions.dll" `
    /resource:"$payloadZip,AerixPayload.zip" `
    /resource:"$licenseFile,LICENSE" `
    /resource:"$appIcon,aerix.ico" `
    /resource:"$brandPng,aerix-icon.png" `
    /resource:"$manifestRes,installer_manifest.json" `
    (Join-Path $srcDir "AssemblyInfo.cs") `
    (Join-Path $srcDir "InstallerEngine.cs") `
    (Join-Path $srcDir "SetupForm.cs") `
    (Join-Path $srcDir "Program.cs")

if ($LASTEXITCODE -ne 0) { throw "Failed to compile C# setup executable" }

$sizeMB = [Math]::Round((Get-Item $setupExe).Length / 1MB, 2)
$hash   = (Get-FileHash $setupExe -Algorithm SHA256).Hash
Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "  BUILT: $setupExe ($sizeMB MB)" -ForegroundColor Green
Write-Host "  SHA256: $hash" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
