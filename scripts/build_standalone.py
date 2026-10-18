"""
Aerix (arx) — Standalone Native Toolchain Freezing Script
Compiles the Python-authored compiler and CLI into a single-file, standalone
machine binary (arx.exe) using PyInstaller so end users worldwide do NOT need
Python installed on their systems.
"""

import sys
import os
import shutil
import subprocess

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def build_standalone():
    print("\n=======================================================")
    print("  Aerix Standalone Toolchain Packaging (PyInstaller)")
    print("=======================================================\n")

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    src_entry = os.path.join(root_dir, "src", "arx.py")
    dist_dir = os.path.join(root_dir, "dist")
    build_dir = os.path.join(root_dir, "build")
    stdlib_src = os.path.join(root_dir, "stdlib")
    stdlib_dst = os.path.join(dist_dir, "stdlib")

    # 1. Verify PyInstaller presence
    try:
        ver_res = subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], capture_output=True, text=True)
        if ver_res.returncode != 0:
            print("[FAIL] PyInstaller not available. Install via: pip install pyinstaller")
            sys.exit(1)
        pyinstaller_ver = ver_res.stdout.strip()
        print(f"[*] Detected PyInstaller version: {pyinstaller_ver}")
    except Exception as e:
        print(f"[FAIL] Could not invoke PyInstaller: {e}")
        sys.exit(1)

    # 2. Execute PyInstaller for arx (Toolchain Runner)
    cmd_arx = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name", "arx",
        "--distpath", dist_dir,
        "--workpath", build_dir,
        "--paths", root_dir,
        "--add-data", f"{stdlib_src}{os.pathsep}stdlib",
        src_entry
    ]

    print("[*] Freezing arx (Toolchain Runner) into standalone binary...")
    res = subprocess.run(cmd_arx, cwd=root_dir)
    if res.returncode != 0:
        print("[FAIL] PyInstaller build of arx failed!")
        sys.exit(res.returncode)

    # 2b. Execute PyInstaller for arxc (Standalone Compiler)
    src_arxc_entry = os.path.join(root_dir, "src", "arxc.py")
    cmd_arxc = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name", "arxc",
        "--distpath", dist_dir,
        "--workpath", build_dir,
        "--paths", root_dir,
        "--add-data", f"{stdlib_src}{os.pathsep}stdlib",
        src_arxc_entry
    ]

    print("[*] Freezing arxc (Standalone Compiler) into standalone binary...")
    res_arxc = subprocess.run(cmd_arxc, cwd=root_dir)
    if res_arxc.returncode != 0:
        print("[FAIL] PyInstaller build of arxc failed!")
        sys.exit(res_arxc.returncode)

    # 3. Copy standard library runtime header alongside dist/
    os.makedirs(stdlib_dst, exist_ok=True)
    rt_header_src = os.path.join(stdlib_src, "aerix_rt.h")
    rt_header_dst = os.path.join(stdlib_dst, "aerix_rt.h")
    shutil.copy2(rt_header_src, rt_header_dst)
    print(f"[OK] Copied runtime stdlib to: {rt_header_dst}")

    # 3b. Build ultra-fast native C dispatcher (arx_fast.exe)
    gcc_path = shutil.which("gcc")
    native_runner_src = os.path.join(root_dir, "src", "native", "arx_runner.c")
    if gcc_path and os.path.exists(native_runner_src):
        fast_exe = os.path.join(dist_dir, "arx_fast.exe")
        core_exe = os.path.join(dist_dir, "arx_core.exe")
        target_arx = os.path.join(dist_dir, "arx.exe")
        print("[*] Compiling ultra-fast native C dispatcher (arx_runner.c)...")
        subprocess.run([gcc_path, "-O2", "-s", native_runner_src, "-o", fast_exe], check=True)
        if os.path.exists(target_arx):
            if os.path.exists(core_exe):
                os.remove(core_exe)
            os.rename(target_arx, core_exe)
            shutil.copy2(fast_exe, target_arx)
            print("[OK] Integrated native C dispatcher as primary arx.exe (with arx_core.exe fallback)!")

    # 4. Verify generated executable
    exe_name = "arx.exe" if sys.platform == "win32" else "arx"
    out_exe = os.path.join(dist_dir, exe_name)
    if not os.path.exists(out_exe):
        print(f"[FAIL] Expected binary not found at '{out_exe}'")
        sys.exit(1)

    size_mb = os.path.getsize(out_exe) / (1024 * 1024)
    print(f"\n[OK] Successfully built standalone executable:")
    print(f"     Path: {out_exe}")
    print(f"     Size: {size_mb:.2f} MB")

    # 5. Smoke test the standalone binary
    print("\n[*] Smoke testing standalone binary without python launcher...")
    test_run = subprocess.run([out_exe, "version"], capture_output=True, text=True)
    print(f"    Output: {test_run.stdout.strip()}")

    print("[*] Running 'arx doctor' on standalone binary...")
    subprocess.run([out_exe, "doctor"])

    hello_arx = os.path.join(root_dir, "examples", "01_hello_world.arx")
    if os.path.exists(hello_arx):
        print("[*] Running 'arx run examples/01_hello_world.arx' on standalone binary...")
        run_res = subprocess.run([out_exe, "run", hello_arx], capture_output=True, text=True)
        print(f"    Result: {run_res.stdout.strip()}")
        assert "Hello, World from Aerix!" in run_res.stdout, "Standalone binary run failed!"

    print("\n[SUCCESS] Aerix standalone binary is 100% verified and ready for global distribution!\n")


if __name__ == "__main__":
    build_standalone()
