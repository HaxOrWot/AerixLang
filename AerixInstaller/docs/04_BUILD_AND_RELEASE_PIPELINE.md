# Aerix Setup Installer — Build & Release Pipeline

## 1. End-to-End Build Workflow

Building the standalone `AerixSetup-1.0.84.exe` installer follows an automated 4-stage pipeline orchestrated by `AerixInstaller/build.py`:

```mermaid
flowchart LR
    A[SVG & Icons Source] -->|Render Multi-Layer .ico| B[Assets Staging]
    C[Compiler & Runtime Core] -->|Stage Binaries & VSIX| D[Payload Assembly]
    B --> E[Inno Setup Engine (ISCC)]
    D --> E
    E -->|Compile LZMA2| F[AerixSetup-1.0.84.exe]
    F -->|Verify & Test| G[GitHub Releases Upload]
```

---

## 2. Detailed Pipeline Stages

### Stage 1: High-DPI Icon Generation
* **Input:** `editors/vscode-aerix/icons/aerix-icon.svg` and `aerix-icon.png` (128x128).
* **Process:** Uses Python's `Pillow` library to rasterize and compose a multi-layer Windows Icon file:
  - `AerixInstaller/assets/aerix.ico` (16, 24, 32, 48, 64, 128, 256 px).
  - `AerixInstaller/assets/aerix_file.ico` (Customized document badge for `.arx` source files).
  - Generates 24-bit uncompressed `.bmp` wizard header and sidebar images.

### Stage 2: Payload Assembly & Staging
* Creates a temporary clean staging sandbox `AerixInstaller/staging/`.
* Copies required artifacts:
  1. `arx.exe` & `arxc.exe` from `dist/` or creates standalone wrapper shims.
  2. `stdlib/aerix_rt.h` (the core runtime header).
  3. `editors/vscode-aerix/aerix-1.0.84.vsix` (the IDE extension).
  4. `README.md`, `USER.md`, `GUIDE.md`, `LICENSE`.
* Validates that all files are uncorrupted and match release checksums.

### Stage 3: Inno Setup Compilation (`ISCC`)
* Invokes Inno Setup command-line compiler:
  ```powershell
  iscc.exe AerixInstaller/src/aerix_setup.iss
  ```
* Compression: `lzma2/ultra64` with solid compression dictionary, shrinking the entire payload to under 15 MB.
* Output: `AerixInstaller/dist/AerixSetup-1.0.84.exe`.

### Stage 4: Automated Verification & Smoke Testing
* Computes SHA-256 cryptographic hash:
  ```powershell
  Get-FileHash AerixInstaller/dist/AerixSetup-1.0.84.exe -Algorithm SHA256
  ```
* Tests silent installation on a test sandbox:
  ```powershell
  AerixSetup-1.0.84.exe /VERYSILENT /DIR="test_sandbox"
  ```
* Verifies `arx doctor` runs and `.arx` icon renders correctly.

---

## 3. GitHub Releases Integration

Once the setup `.exe` is generated, it can be published directly to GitHub via GitHub CLI:

```powershell
# Create GitHub Release v1.0.84 with attached installer
gh release create v1.0.84-alpha AerixInstaller/dist/AerixSetup-1.0.84.exe \
   --title "Aerix v1.0.84-alpha: Official Windows Installer Release" \
   --notes "Download and run AerixSetup-1.0.84.exe for complete one-click setup on Windows."
```
