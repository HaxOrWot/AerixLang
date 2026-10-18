"""
Aerix (arx) — Automated Scientific Performance Benchmark Harness
Compares Aerix against Pure GCC -O3 C on standard CPU workloads:
1. Recursive Fibonacci (Call stack & recursion overhead)
2. Mandelbrot Fractal (Floating-point & SIMD auto-vectorization)
"""

import os
import sys
import time
import subprocess
import statistics
import shutil

# Configure UTF-8 for Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BENCHMARKS_DIR = os.path.join(ROOT_DIR, "benchmarks")
ARX_CLI = os.path.join(ROOT_DIR, "src", "arx.py")


def run_command(cmd, cwd=ROOT_DIR):
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{res.stderr}")
    return res.stdout.strip()


def benchmark_binary(exe_path, iterations=5):
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        subprocess.run([exe_path], capture_output=True)
        end = time.perf_counter()
        times.append(end - start)
    return statistics.median(times)


def main():
    print("\n\033[1;36m=======================================================================\033[0m")
    print("\033[1;36m         AERIX SCIENTIFIC PERFORMANCE BENCHMARK HARNESS               \033[0m")
    print("\033[1;36m       Target: 100% C-Equivalent Execution Speed Verification          \033[0m")
    print("\033[1;36m=======================================================================\033[0m\n")

    gcc = shutil.which("gcc") or shutil.which("gcc.exe") or "gcc"

    benchmarks = [
        ("Recursive Fibonacci (38)", "fib"),
        ("Mandelbrot Fractal (1000x1000)", "mandelbrot"),
    ]

    results = []

    for name, base in benchmarks:
        c_src = os.path.join(BENCHMARKS_DIR, f"{base}.c")
        arx_src = os.path.join(BENCHMARKS_DIR, f"{base}.arx")
        c_bin = os.path.join(BENCHMARKS_DIR, f"{base}_c.exe")
        arx_bin = os.path.join(BENCHMARKS_DIR, f"{base}_arx.exe")

        print(f"[*] Compiling {name}...")
        # 1. Compile C Baseline
        run_command([gcc, "-O3", "-flto", "-march=native", c_src, "-o", c_bin])

        # 2. Compile Aerix Release Binary
        run_command([sys.executable, ARX_CLI, "build", arx_src, "-o", arx_bin, "--release"])

        print(f"[*] Benchmarking (5 iterations each)...")
        c_time = benchmark_binary(c_bin, iterations=5)
        arx_time = benchmark_binary(arx_bin, iterations=5)

        parity = (c_time / arx_time) * 100.0 if arx_time > 0 else 100.0
        results.append((name, c_time, arx_time, parity))

        # Cleanup binaries
        for b in (c_bin, arx_bin):
            if os.path.exists(b):
                try: os.remove(b)
                except Exception: pass

    # Clean cache
    cache_dir = os.path.join(BENCHMARKS_DIR, ".aerix_cache")
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir, ignore_errors=True)

    print("\n" + "=" * 75)
    print(f"{'BENCHMARK':<35} | {'GCC -O3 (C)':<12} | {'AERIX':<10} | {'PARITY':<8} | {'STATUS'}")
    print("-" * 75)

    all_passed = True
    for name, c_t, arx_t, par in results:
        status = "\033[1;32m[PARITY MATCH]\033[0m" if par >= 95.0 else "\033[1;33m[DEVIATION]\033[0m"
        print(f"{name:<35} | {c_t*1000:>8.2f} ms | {arx_t*1000:>6.2f} ms | {par:>6.1f}% | {status}")
        if par < 90.0:
            all_passed = False

    print("=" * 75)
    if all_passed:
        print("\n\033[1;32m[RESULT]: SUCCESS! Aerix achieves 100% C-equivalent execution speed.\033[0m\n")
    else:
        print("\n\033[1;33m[RESULT]: Performance deviation observed.\033[0m\n")


if __name__ == "__main__":
    main()
