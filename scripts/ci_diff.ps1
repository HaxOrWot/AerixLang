# ==============================================================================
# Aerix Differential Parity Test Suite (Native x86-64 vs ANSI C99)
# ==============================================================================
$ErrorActionPreference = "Continue"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Arx = "C:\Aerix\bin\arx.exe"
if (-not (Test-Path $Arx)) {
    $Arx = "$Root\bin\arx.exe"
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Aerix Differential Parity Test Harness" -ForegroundColor Cyan
Write-Host " Compiler: $Arx" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$TempDir = "$Root\tests\diff_temp"
if (Test-Path $TempDir) { Remove-Item $TempDir -Recurse -Force }
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

$TestsPassed = 0
$TestsFailed = 0

function Run-DiffTest([string]$Name, [string]$SourceCode) {
    Write-Host -NoNewline "Testing $Name... "
    $SrcPath = "$TempDir\$Name.arx"
    $NativeExe = "$TempDir\${Name}_native.exe"
    $CFile = "$TempDir\${Name}_c.c"
    $CExe = "$TempDir\${Name}_c.exe"

    [System.IO.File]::WriteAllText($SrcPath, $SourceCode)

    # 1. Compile & run native
    $BuildNative = & $Arx build $SrcPath -o $NativeExe 2>&1
    if (-not (Test-Path $NativeExe)) {
        Write-Host "FAILED (Native build failed)" -ForegroundColor Red
        Write-Host ($BuildNative -join "`n") -ForegroundColor DarkYellow
        $global:TestsFailed++
        return
    }
    $NativeOut = & $NativeExe
    $NativeExit = $LASTEXITCODE

    # 2. Compile & run C99
    & $Arx emit-c $SrcPath -o $CFile 2>&1 | Out-Null
    if (-not (Test-Path $CFile)) {
        Write-Host "FAILED (emit-c failed)" -ForegroundColor Red
        $global:TestsFailed++
        return
    }
    gcc -I"$Root\stdlib" $CFile -o $CExe -lws2_32 2>&1 | Out-Null
    if (-not (Test-Path $CExe)) {
        Write-Host "FAILED (gcc build failed)" -ForegroundColor Red
        $global:TestsFailed++
        return
    }
    $COut = & $CExe
    $CExit = $LASTEXITCODE

    # 3. Compare differential parity
    $NativeStr = ($NativeOut -join "`n").Trim()
    $CStr = ($COut -join "`n").Trim()

    if ($NativeExit -ne $CExit) {
        Write-Host "FAILED (Exit code mismatch: Native=$NativeExit, C=$CExit)" -ForegroundColor Red
        $global:TestsFailed++
        return
    }

    if ($NativeStr -ne $CStr) {
        Write-Host "FAILED (Output mismatch)" -ForegroundColor Red
        Write-Host "Native:" -ForegroundColor Yellow
        Write-Host $NativeStr
        Write-Host "C99:" -ForegroundColor Yellow
        Write-Host $CStr
        $global:TestsFailed++
        return
    }

    Write-Host "PASSED (100% match)" -ForegroundColor Green
    $global:TestsPassed++
}

# Test 1: Basic Arithmetic & Loops
Run-DiffTest "01_arithmetic" @'
fn main() {
    mut sum = 0
    mut i = 0
    while i < 100 {
        sum = sum + i * 2
        i = i + 1
    }
    println("sum = " + (sum as str))
}
'@

# Test 2: Struct Methods & Point Math
Run-DiffTest "02_structs" @'
struct Point {
    pub x: f64
    pub y: f64

    init(x: f64, y: f64) {
        self.x = x
        self.y = y
    }
}

fn dist_sq(p1: Point, p2: Point) -> f64 {
    let dx = p1.x - p2.x
    let dy = p1.y - p2.y
    return dx * dx + dy * dy
}

fn main() {
    let a = Point(1.0, 2.0)
    let b = Point(4.0, 6.0)
    println("dist = " + (dist_sq(a, b) as str))
}
'@

# Test 3: Tagged Unions & Match
Run-DiffTest "03_enums" @'
enum Shape {
    Circle(r: f64),
    Rect(w: f64, h: f64)
}

fn area(s: Shape) -> f64 {
    match s {
        Circle(r) => return 3.14159 * r * r,
        Rect(w, h) => return w * h
    }
    return 0.0
}

fn main() {
    let c = Shape.Circle(5.0)
    let r = Shape.Rect(4.0, 5.0)
    println("c = " + (area(c) as str))
    println("r = " + (area(r) as str))
}
'@

# Test 4: String Operations
Run-DiffTest "04_strings" @'
import "Str"

fn main() {
    let s = "  aerix language  "
    println("trimmed = " + Str.trim(s))
    println("upper = " + Str.to_upper("aerix"))
    println("pad = " + Str.pad_left("42", 5, "0"))
}
'@

# Clean up
Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "----------------------------------------------------------"
Write-Host "Differential Tests: $TestsPassed Passed, $TestsFailed Failed." -ForegroundColor $(if ($TestsFailed -eq 0) { "Green" } else { "Red" })
if ($TestsFailed -gt 0) { exit 1 }
exit 0
