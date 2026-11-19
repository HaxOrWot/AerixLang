# ==============================================================================
# Aerix Multi-Stage Bootstrap Convergence Verification
# Proves compiler self-hosting correctness via bit-for-bit SHA-256 equality.
# ==============================================================================
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Arx = "C:\Aerix\bin\arx.exe"
if (-not (Test-Path $Arx)) {
    $Arx = "$Root\bin\arx.exe"
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Aerix Bootstrap Convergence Verification" -ForegroundColor Cyan
Write-Host " Root: $Root" -ForegroundColor Cyan
Write-Host " Base Compiler: $Arx" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$StageDir = "$Root\bin\bootstrap"
if (Test-Path $StageDir) { Remove-Item $StageDir -Recurse -Force }
New-Item -ItemType Directory -Path $StageDir -Force | Out-Null

$Stage2 = "$StageDir\stage2.exe"
$Stage3 = "$StageDir\stage3.exe"
$Stage4 = "$StageDir\stage4.exe"

# Stage 1 -> Stage 2
Write-Host "Building Stage 2 using base compiler..." -ForegroundColor Yellow
$sw = [System.Diagnostics.Stopwatch]::StartNew()
& $Arx build src\bootstrap\main\mod.arx -o $Stage2
$sw.Stop()
Write-Host "Stage 2 built in $($sw.ElapsedMilliseconds) ms." -ForegroundColor Green

# Stage 2 -> Stage 3
Write-Host "Building Stage 3 using Stage 2 binary..." -ForegroundColor Yellow
$sw.Restart()
& $Stage2 build src\bootstrap\main\mod.arx -o $Stage3
$sw.Stop()
Write-Host "Stage 3 built in $($sw.ElapsedMilliseconds) ms." -ForegroundColor Green

# Calculate SHA256 hashes
$Hash2 = (Get-FileHash -Algorithm SHA256 $Stage2).Hash
$Hash3 = (Get-FileHash -Algorithm SHA256 $Stage3).Hash

Write-Host "----------------------------------------------------------"
Write-Host "Stage 2 SHA-256: $Hash2"
Write-Host "Stage 3 SHA-256: $Hash3"

if ($Hash2 -eq $Hash3) {
    Write-Host "CONVERGENCE VERIFIED: Stage 2 and Stage 3 are bit-for-bit identical!" -ForegroundColor Green
    exit 0
}

# If Stage 2 differs from Stage 3 due to generator improvements, check Stage 3 -> Stage 4:
Write-Host "Stage 2 and Stage 3 differ (initial generation bootstrap step). Checking Stage 3 -> Stage 4 convergence..." -ForegroundColor Yellow
$sw.Restart()
& $Stage3 build src\bootstrap\main\mod.arx -o $Stage4
$sw.Stop()
Write-Host "Stage 4 built in $($sw.ElapsedMilliseconds) ms." -ForegroundColor Green

$Hash4 = (Get-FileHash -Algorithm SHA256 $Stage4).Hash
Write-Host "Stage 4 SHA-256: $Hash4"

if ($Hash3 -eq $Hash4) {
    Write-Host "CONVERGENCE VERIFIED: Stage 3 and Stage 4 are bit-for-bit identical!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "BOOTSTRAP DIVERGENCE ERROR: Stage 3 and Stage 4 produced different outputs!" -ForegroundColor Red
    exit 1
}
