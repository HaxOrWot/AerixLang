# -*- coding: utf-8 -*-
"""
Aerix Language — Official Release Publisher Script
Ensures that all current and future releases upload ONLY:
  1. AerixSetup-<version>.exe (The Windows Setup Installer)
  2. aerix-<version>.vsix     (The VS Code / Antigravity Extension)
and strictly nothing else.
"""

import os
import sys
import glob
import subprocess
import json

def get_project_version(root_dir):
    arx_py = os.path.join(root_dir, "src", "arx.py")
    with open(arx_py, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("VERSION ="):
                raw_ver = line.split("=")[1].strip().strip('"').strip("'")
                return raw_ver
    return "1.0.91-pre"

def publish(tag=None):
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    version = get_project_version(root_dir)
    tag_name = tag or f"v{version}"

    print("==================================================================")
    print(f"       AERIX GITHUB RELEASE PUBLISHER ({tag_name})                ")
    print("==================================================================")

    # 1. Locate Installer EXE
    installer_dir = os.path.join(root_dir, "AerixInstaller", "dist")
    setup_candidates = glob.glob(os.path.join(installer_dir, f"AerixSetup-{version}*.exe"))
    if not setup_candidates:
        setup_candidates = glob.glob(os.path.join(installer_dir, "AerixSetup*.exe"))
    
    if not setup_candidates:
        print(f"[ERROR] Could not find AerixSetup-{version}.exe in {installer_dir}")
        print("        Run 'python AerixInstaller/build.py' first.")
        sys.exit(1)
    setup_exe = setup_candidates[0]

    # 2. Locate VSIX Extension
    editors_dir = os.path.join(root_dir, "editors", "vscode-aerix")
    vsix_candidates = glob.glob(os.path.join(editors_dir, f"aerix-{version}*.vsix"))
    if not vsix_candidates:
        vsix_candidates = glob.glob(os.path.join(editors_dir, "*.vsix"))
    
    if not vsix_candidates:
        print(f"[ERROR] Could not find aerix-{version}.vsix in {editors_dir}")
        print("        Run 'npx @vscode/vsce package' first.")
        sys.exit(1)
    vsix_file = vsix_candidates[0]

    # Staged assets: STRICTLY ONLY the setup exe and the vsix extension
    allowed_assets = [setup_exe, vsix_file]

    print("[*] Strict Asset Policy: ONLY Setup EXE and VSIX will be published.")
    for a in allowed_assets:
        size_mb = os.path.getsize(a) / (1024 * 1024)
        print(f"    - {os.path.basename(a)} ({size_mb:.2f} MB)")

    # 3. Check if release already exists
    view_res = subprocess.run(["gh", "release", "view", tag_name, "--json", "assets"], capture_output=True, text=True)
    if view_res.returncode == 0:
        print(f"\n[*] Release {tag_name} already exists. Cleaning any unauthorized assets...")
        data = json.loads(view_res.stdout)
        allowed_names = {os.path.basename(setup_exe), os.path.basename(vsix_file)}
        for asset in data.get("assets", []):
            name = asset.get("name")
            if name not in allowed_names:
                print(f"    [!] Deleting unauthorized asset from release: {name}")
                subprocess.run(["gh", "release", "delete-asset", tag_name, name, "-y"], check=True)

        print(f"[*] Uploading/updating allowed assets into {tag_name}...")
        subprocess.run(["gh", "release", "upload", tag_name, setup_exe, vsix_file, "--clobber"], check=True)
    else:
        print(f"\n[*] Creating new release {tag_name}...")
        title = f"Aerix v{version}: Windows Installer & VS Code Extension"
        cmd = ["gh", "release", "create", tag_name, setup_exe, vsix_file, "--title", title]
        if any(pre in version.lower() for pre in ["-pre", "-alpha", "-beta", "-rc"]):
            cmd.append("--prerelease")
        notes_path = os.path.join(root_dir, "scratch", f"RELEASE_NOTES_v{version}.md")
        if os.path.exists(notes_path):
            cmd.extend(["--notes-file", notes_path])
        else:
            cmd.append("--generate-notes")
        subprocess.run(cmd, check=True)

    print("\n==================================================================")
    print("                    RELEASE READY & VERIFIED                      ")
    print("==================================================================")
    subprocess.run(["gh", "release", "view", tag_name])

if __name__ == "__main__":
    specified_tag = sys.argv[1] if len(sys.argv) > 1 else None
    publish(specified_tag)
