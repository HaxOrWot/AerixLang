# Aerix (arx) — Standard Library Specification

> **Package Root:** `stdlib/`  
> **Philosophy:** *Lean, highly optimized, zero-dependency modules built directly on the C standard library.*

---

## 1. Built-in Global Functions

These functions are natively available in every Aerix scope without explicit imports:

| Function | Signature | Description |
| :--- | :--- | :--- |
| `print` | `fn print(fmt: str, ...)` | Prints text to stdout without appending a newline. |
| `println` | `fn println(fmt: str, ...)` | Formatted print with string interpolation and automatic newline. |
| `eprintln` | `fn eprintln(fmt: str, ...)` | Formatted print to stderr. |
| `assert` | `fn assert(cond: bool, msg: str = "")` | Aborts with panic message if `cond` is false. |
| `panic` | `fn panic(msg: str)` | Immediately terminates the program with stack and line information. |
| `sizeof` | `fn sizeof(T: type) -> usize` | Returns the byte size of type `T` at compile time. |

---

## 2. Core Modules Overview

Aerix ships with 6 foundational standard library modules in `stdlib/`:

```text
stdlib/
├── core.arx       # Basic language traits, Result, Option, memory utilities
├── io.arx         # File streams, reading, writing, terminal helpers
├── math.arx       # Advanced mathematical functions, constants, vectors
├── str.arx        # Dynamic strings, splitting, trimming, searching
├── vec.arx        # Dynamic auto-resizing array collection (Vec[T])
└── time.arx       # High-resolution timers, benchmark clocks, sleep
```

---

## 3. Module Details & API

### 3.1 `stdlib/math.arx`
Provides high-performance mathematical functions compiling directly into C `<math.h>` CPU intrinsics:

```aerix
const PI: f64 = 3.14159265358979323846
const E: f64  = 2.71828182845904523536

fn abs(x: f64) -> f64
fn sqrt(x: f64) -> f64
fn pow(base: f64, exp: f64) -> f64
fn sin(rad: f64) -> f64
fn cos(rad: f64) -> f64
fn tan(rad: f64) -> f64
fn floor(x: f64) -> f64
fn ceil(x: f64) -> f64
fn round(x: f64) -> f64
fn min(a: f64, b: f64) -> f64
fn max(a: f64, b: f64) -> f64
fn clamp(val: f64, low: f64, high: f64) -> f64
```

### 3.2 `stdlib/io.arx`
Clean, safe file system access:

```aerix
class File {
    pub path: str
    priv handle: *void

    static fn open(path: str, mode: str = "r") -> File?
    pub fn read_all() -> str
    pub fn write_all(content: str) -> bool
    pub fn read_line() -> str?
    pub fn close()
}

fn file_exists(path: str) -> bool
fn read_to_string(path: str) -> str
fn write_to_file(path: str, text: str) -> bool
```

### 3.3 `stdlib/vec.arx` (Dynamic Arrays)
Fast, cache-friendly resizable array with amortized O(1) appending:

```aerix
class Vec[T] {
    priv data: *T
    pub len: usize
    pub cap: usize

    init(initial_cap: usize = 8)
    pub fn push(item: T)
    pub fn pop() -> T?
    pub fn get(index: usize) -> T
    pub fn set(index: usize, item: T)
    pub fn clear()
    drop() // Frees allocated buffer automatically!
}
```

### 3.4 `stdlib/time.arx`
High-precision benchmarking and system time:

```aerix
fn now_ms() -> i64          // Current UNIX epoch in milliseconds
fn high_res_timer() -> f64  // Sub-microsecond CPU performance counter
fn sleep_ms(ms: u32)        // Sleep execution for N milliseconds
```

---

## 4. Module Import System

Aerix uses the `use` keyword to import standard and local modules:

```aerix
// Import an entire module
use math

// Selective import
use math::{sqrt, PI}

// Import local project file
use "engine/physics.arx" as phys

fn main() {
    let hypotenuse = sqrt(3.0 * 3.0 + 4.0 * 4.0)
    println("Hypotenuse: {hypotenuse}, PI: {PI}")
}
```
