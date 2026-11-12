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
Write-Host "     AERIX C++ WINDOWS INSTALLER BUILDER (v$version)" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

# Clean previous staging/build artifacts
if (Test-Path $buildDir) { Remove-Item $buildDir -Recurse -Force }
New-Item -ItemType Directory -Path (Join-Path $stageDir "bin") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $stageDir "stdlib") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $stageDir "modules") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $stageDir "editors\extension") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $stageDir "assets") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $stageDir "docs") -Force | Out-Null
New-Item -ItemType Directory -Path $distDir -Force | Out-Null

# 1. Compile native self-hosting compiler binaries (arxc.exe & arx.exe)
Write-Host "[1/5] Compiling native self-hosting compiler from C99 seed..."
$seedC   = Join-Path $repoRoot "src\bootstrap\seed\arxc.c"
$stdlibI = Join-Path $repoRoot "stdlib"
$arxcOut = Join-Path $stageDir "bin\arxc.exe"
$arxOut  = Join-Path $stageDir "bin\arx.exe"
& gcc -std=c99 -O2 -Wno-unused-function -I "$stdlibI" "$seedC" -o "$arxcOut" -lm
if ($LASTEXITCODE -ne 0) { throw "Failed to compile arxc.exe from seed" }
Copy-Item $arxcOut $arxOut -Force

# 2. Stage runtime header, standard modules, extension, icons, docs
Write-Host "[2/5] Staging stdlib, modules, extension, icons, and docs..."
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

# 3. Build C++ payload packager and compress staged tree
Write-Host "[3/5] Building C++ packager and compressing ARXP payload..."
$packagerExe = Join-Path $buildDir "packager.exe"
$payloadBin  = Join-Path $buildDir "payload.bin"
& g++ -std=c++17 -O2 -Wall -Wextra (Join-Path $srcDir "packager.cpp") -o "$packagerExe" -lz
if ($LASTEXITCODE -ne 0) { throw "Failed to compile packager.cpp" }
& "$packagerExe" "$stageDir" "$payloadBin"
if ($LASTEXITCODE -ne 0) { throw "Failed to pack payload" }

# 4. Compile Win32 resources
Write-Host "[4/5] Compiling Win32 resources (icons, bitmaps, manifest, payload)..."
$resObj = Join-Path $buildDir "resources.o"
Push-Location $srcDir
try {
    & windres --input-format=rc --output-format=coff -I "$srcDir" "resources.rc" "$resObj"
    if ($LASTEXITCODE -ne 0) { throw "windres failed" }
} finally {
    Pop-Location
}

# 5. Compile C++ Win32 Setup executable
Write-Host "[5/5] Compiling standalone C++ setup executable..."
Get-ChildItem $distDir -Filter "AerixSetup-*.exe" | Where-Object { $_.Name -ne "AerixSetup-$version.exe" } | Remove-Item -Force
$setupExe = Join-Path $distDir "AerixSetup-$version.exe"
& g++ -std=c++17 -O2 -Wall -Wextra `
    -DUNICODE -D_UNICODE -D_WIN32_WINNT=0x0A00 -DWINVER=0x0A00 `
    (Join-Path $srcDir "setup_main.cpp") `
    (Join-Path $srcDir "installer_engine.cpp") `
    "$resObj" `
    -o "$setupExe" `
    -mwindows -static -static-libgcc -static-libstdc++ `
    -lz -lcomctl32 -lshell32 -lole32 -luuid -ladvapi32 -lgdi32 -luser32 -lshlwapi
if ($LASTEXITCODE -ne 0) { throw "Failed to compile setup executable" }

$sizeMB = [Math]::Round((Get-Item $setupExe).Length / 1MB, 2)
$hash   = (Get-FileHash $setupExe -Algorithm SHA256).Hash
Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "  BUILT: $setupExe ($sizeMB MB)" -ForegroundColor Green
Write-Host "  SHA256: $hash" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
