# -*- coding: utf-8 -*-
"""
AerixInstaller/build.py
One-click build orchestrator for the Aerix Setup Installer.
1. Generates high-DPI icons & wizard bitmaps.
2. Locates or installs Inno Setup (ISCC).
3. Compiles AerixSetup-1.0.84.exe.
4. Generates SHA-256 integrity checksums.
"""

import os
import sys
import subprocess
import hashlib
import shutil

def find_iscc():
    # 1. Check PATH
    iscc = shutil.which("iscc")
    if iscc:
        return iscc

    # 2. Check standard program directories
    standard_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\iscc.exe",
        r"C:\Program Files\Inno Setup 6\iscc.exe",
        r"C:\Program Files (x86)\Inno Setup 7\iscc.exe",
        r"C:\Program Files\Inno Setup 7\iscc.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\iscc.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 7\iscc.exe")
    ]
    for p in standard_paths:
        if os.path.exists(p):
            return p
    return None

def main():
    installer_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(installer_dir, "src")
    dist_dir = os.path.join(installer_dir, "dist")
    os.makedirs(dist_dir, exist_ok=True)

    print("==================================================================")
    print("        AERIX WINDOWS SETUP COMPILER & BUILDER          ")
    print("==================================================================")

    # Step 1: Generate assets & icons
    print("\n[*] Step 1: Generating high-DPI multi-resolution icon assets...")
    asset_gen = os.path.join(src_dir, "generate_assets.py")
    res = subprocess.run([sys.executable, asset_gen], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[ERROR] Asset generation failed: {res.stderr}")
        sys.exit(1)
    print(res.stdout.strip())

    # Step 2: Locate Inno Setup compiler
    print("\n[*] Step 2: Locating Inno Setup Compiler (ISCC)...")
    iscc_path = find_iscc()

    if not iscc_path:
        print("[!] Inno Setup compiler not found on system.")
        print("[*] Attempting automatic silent installation via winget...")
        try:
            install_cmd = ["winget", "install", "--id", "JRSoftware.InnoSetup", "-e", "--silent", "--accept-source-agreements", "--accept-package-agreements"]
            winget_res = subprocess.run(install_cmd, capture_output=True, text=True, timeout=120)
            if winget_res.returncode == 0:
                print("[OK] Inno Setup installed successfully via winget!")
                iscc_path = find_iscc()
            else:
                print(f"[!] Winget failed: {winget_res.stderr}")
        except Exception as e:
            print(f"[!] Winget error: {e}")

    if not iscc_path:
        print("\n[MANUAL ACTION NEEDED]")
        print("Please install Inno Setup 6 by running:")
        print("  winget install --id JRSoftware.InnoSetup -e")
        print("Or download from: https://jrsoftware.org/isdl.php")
        sys.exit(1)

    print(f"[OK] Found Inno Setup Compiler at: {iscc_path}")

    # Step 3: Compile Setup Executable
    iss_file = os.path.join(src_dir, "aerix_setup.iss")
    print(f"\n[*] Step 3: Compiling installer script: {iss_file}...")
    compile_cmd = [iscc_path, iss_file]
    build_res = subprocess.run(compile_cmd, capture_output=True, text=True)

    if build_res.returncode != 0:
        print(f"[ERROR] Inno Setup compilation failed:\n{build_res.stdout}\n{build_res.stderr}")
        sys.exit(1)

    print(build_res.stdout.strip())

    # Step 4: Verify Output
    expected_exe = os.path.join(dist_dir, "AerixSetup-1.0.84.exe")
    if os.path.exists(expected_exe):
        size_mb = os.path.getsize(expected_exe) / (1024 * 1024)
        hasher = hashlib.sha256()
        with open(expected_exe, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        sha256 = hasher.hexdigest()

        print("\n==================================================================")
        print("                    BUILD SUCCESSFUL!                             ")
        print("==================================================================")
        print(f"  Executable:  {expected_exe}")
        print(f"  Size:        {size_mb:.2f} MB")
        print(f"  SHA-256:     {sha256}")
        print("==================================================================")
    else:
        print(f"[!] Warning: Expected output binary not found at {expected_exe}")

if __name__ == "__main__":
    main()

