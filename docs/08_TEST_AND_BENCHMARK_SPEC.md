# Aerix (arx) — Test Vectors & Benchmark Specification

> **Subsystem:** Automated Test Harness & Native Performance Verification  
> **Target:** 100% C-equivalent execution speed verification across standardized CPU benchmarks.

---

## 1. Automated Test Suite Architecture

Aerix employs a multi-tiered testing strategy:

```
+-------------------------------------------------------------+
|                     AERIX TEST HARNESS                      |
+-------------------------------------------------------------+
| 1. Unit Tests: Lexer (tokens, coordinates, regex)          |
| 2. Unit Tests: Parser (AST validation, precedence trees)   |
| 3. Unit Tests: Semantic Analyzer (typecheck, scoping)      |
| 4. Unit Tests: C99 Codegen (emitted C syntax checking)     |
| 5. End-to-End Tests: (arx run -> verify stdout / exit code) |
| 6. Performance Benchmarks: (Aerix vs Pure GCC -O3 C)        |
+-------------------------------------------------------------+
```

---

## 2. Test Vectors (Input `.arx` ➡️ Expected Stdout)

### Test Vector 1: Basic Procedural Arithmetic & Pipeline
* **Source:** `tests/fixtures/01_pipeline.arx`
```aerix
fn double(x: i64) -> i64 => x * 2
fn add_five(x: i64) -> i64 => x + 5

fn main() {
    let result = 10 |> double() |> add_five()
    println("Result: {result}")
}
```
* **Expected Output:**
```text
Result: 25
```

---

### Test Vector 2: Immutability Enforcement (Compile Error Test)
* **Source:** `tests/fixtures/02_immutability_error.arx`
```aerix
fn main() {
    let x = 10
    x = 20 // Semantic Error: Cannot reassign immutable variable 'x'
}
```
* **Expected Compiler Error:**
```text
[AERIX ERROR]: Reassignment to immutable variable 'x'
  --> tests/fixtures/02_immutability_error.arx:3:5
```

---

### Test Vector 3: Object-Oriented Encapsulation & Methods
* **Source:** `tests/fixtures/03_oop_account.arx`
```aerix
class Account {
    pub owner: str
    priv balance: f64

    init(owner: str, initial: f64) {
        self.owner = owner
        self.balance = initial
    }

    pub fn deposit(amt: f64) {
        self.balance += amt
    }

    pub fn get_balance() -> f64 => self.balance
}

fn main() {
    mut acc = Account("Charlie", 500.0)
    acc.deposit(250.0)
    println("{acc.owner} balance: {acc.get_balance()}")
}
```
* **Expected Output:**
```text
Charlie balance: 750
```

---

### Test Vector 4: Defer Scoped Resource Management
* **Source:** `tests/fixtures/04_defer_order.arx`
```aerix
fn test_defer() {
    println("Step 1")
    defer println("Defer 1 (Last)")
    println("Step 2")
    defer println("Defer 2 (First)")
    println("Step 3")
}

fn main() {
    test_defer()
}
```
* **Expected Output:**
```text
Step 1
Step 2
Step 3
Defer 2 (First)
Defer 1 (Last)
```

---

## 3. Scientific Performance Benchmark Suite (Aerix vs Native C)

To objectively prove that Aerix achieves C/C++ execution speed, the following three benchmarks compare Aerix code directly against hand-written C compiled with `gcc -O3 -flto -march=native`.

---

### Benchmark 1: Recursive Fibonacci (Stack & Function Call Overhead)

#### Pure C Baseline (`benchmarks/fib.c`):
```c
#include <stdio.h>
#include <stdint.h>
#include <time.h>

int64_t fib(int64_t n) {
    if (n <= 1) return n;
    return fib(n - 1) + fib(n - 2);
}

int main(void) {
    clock_t start = clock();
    int64_t result = fib(40);
    clock_t end = clock();
    double cpu_time = (double)(end - start) / CLOCKS_PER_SEC;
    printf("C Result: %lld in %f seconds\n", (long long)result, cpu_time);
    return 0;
}
```

#### Aerix Equivalent (`benchmarks/fib.arx`):
```aerix
fn fib(n: i64) -> i64 {
    if n <= 1 { return n }
    return fib(n - 1) + fib(n - 2)
}

fn main() {
    let start = arx_time_now()
    let result = fib(40)
    let elapsed = arx_time_now() - start
    println("Aerix Result: {result} in {elapsed} seconds")
}
```
*Target Performance:* Aerix execution time within **99% - 100%** of C.

---

### Benchmark 2: Mandelbrot Fractal (SIMD & Floating-Point Throughput)

Computes escape time for a 1000x1000 complex grid with max 1000 iterations per pixel.

#### Aerix Implementation (`benchmarks/mandelbrot.arx`):
```aerix
fn compute_mandelbrot(width: i32, height: i32, max_iter: i32) -> i64 {
    mut total_iterations: i64 = 0
    
    for y in 0..height {
        let ci = ((y as f64) * 2.0 / (height as f64)) - 1.0
        for x in 0..width {
            let cr = ((x as f64) * 3.0 / (width as f64)) - 2.0
            mut zr = 0.0
            mut zi = 0.0
            mut iter = 0

            while (zr * zr + zi * zi <= 4.0) && (iter < max_iter) {
                let temp = zr * zr - zi * zi + cr
                zi = 2.0 * zr * zi + ci
                zr = temp
                iter += 1
            }
            total_iterations += iter
        }
    }
    return total_iterations
}

fn main() {
    let start = arx_time_now()
    let total = compute_mandelbrot(1000, 1000, 1000)
    let elapsed = arx_time_now() - start
    println("Mandelbrot Total: {total} in {elapsed} seconds")
}
```
*Target Performance:* Identical machine code emitted as GCC `-O3` (auto-vectorized loops).

---

## 4. Automated Benchmark Runner (`scripts/run_benchmarks.py`)

A single command:
```bash
python scripts/run_benchmarks.py
```
Will:
1. Compile the C baseline with `gcc -O3 -flto -march=native`.
2. Compile the Aerix source with `arx build --release`.
3. Run each binary 5 times, compute median execution times, and print a formatted performance parity table.
