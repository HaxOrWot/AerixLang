# Git Branching & Versioning Instructions (`GIT-INS.md`)

This document defines the mandatory Git workflow and project-wide versioning rules for **AerixLang**.

---

## 1. Clean Semantic Versioning System (SemVer 2.0)

Aerix uses clean, standard Semantic Versioning without confusing letter suffixes or redundant `-stable` tags.

| Release Channel | Version Tag Format | Example | Installer Binary | VS Code Extension | Git Branch |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Stable** | `v<Major>.<Minor>.<Patch>` | `v2.2.25`, `v2.3.0` | `AerixSetup-2.2.25.exe` | `aerix-2.2.25.vsix` | `master` & `stable` |
| **Beta** | `v<Major>.<Minor>.<Patch>-beta.<N>` | `v2.3.0-beta.1` | `AerixSetup-2.3.0-beta.1.exe` | `aerix-2.3.0-beta.1.vsix` | `beta` |
| **Release Candidate** | `v<Major>.<Minor>.<Patch>-rc.<N>` | `v2.3.0-rc.1` | `AerixSetup-2.3.0-rc.1.exe` | `aerix-2.3.0-rc.1.vsix` | `pre` |

### Why This Format is Superior:
1. **Zero Confusion:** No letter soup (e.g. `1.1.12a-stable` vs `1.2.24b`).
2. **Universal Compatibility:** Supported by GitHub Releases, npm/vsce, Windows executable manifests (`Major.Minor.Patch.Build`), and version comparators.
3. **Clean File Names:** `AerixSetup-2.2.25.exe` and `aerix-2.2.25.vsix`.

---

## 2. Version Increment Rules

* **Major (`X.0.0`):** Breaking architectural changes or major milestones (e.g. transition to native PE32+ compiler).
* **Minor (`X.Y.0`):** New language features, new standard library modules, or syntax additions.
* **Patch (`X.Y.Z`):** Bug fixes, LSP optimizations, standard library improvements, and documentation updates.
* **Beta Iterations (`X.Y.Z-beta.N`):** During active development on the `beta` branch, increment `N` (`beta.1`, `beta.2`, `beta.3`).

---

## 3. Branch Workflow

1. **Active Work on `beta` First:**
   - All feature work, compiler edits, and bug fixes must be committed and pushed to `beta`.
   - Never push untested or work-in-progress code to `master` or `stable`.
2. **Promotion to `stable` / `master`:**
   - Once all features are verified on `beta`:
     1. Bump version string to the clean stable version (e.g. `2.3.0`).
     2. Rebuild seed (`arxc.c`), compiler binary, VSIX (`.vsix`), and installer (`AerixSetup-X.Y.Z.exe`).
     3. Merge `beta` into `master` and `stable` with fast-forward (`git merge beta --ff-only`).
     4. Push all three branches to origin.
     5. Publish a GitHub Release tagged `vX.Y.Z` with the installer and VSIX attached.

---

## 4. Project-Wide Version Checklist (Update Together)

* **Windows Installer:**
  - `AerixInstaller/src/installer_manifest.json` (`"version"`)
  - `AerixInstaller/src/InstallerEngine.cs` (`DefaultVersion`)
  - `AerixInstaller/src/AssemblyInfo.cs` (`AssemblyVersion`, `AssemblyFileVersion`: `X.Y.Z.0`)
  - `AerixInstaller/src/app.manifest` (`version="X.Y.Z.0"`)
* **Compiler & LSP Daemon:**
  - `src/bootstrap/main.arx` (`--version` banner)
  - `src/bootstrap/lsp/server.arx` (`serverInfo.version`)
  - Regenerate `src/bootstrap/seed/arxc.c`
* **Editor Extension:**
  - `editors/vscode-aerix/package.json` (`"version"`)
  - `editors/vscode-aerix/README.md`
  - Re-package `.vsix`
* **Documentation:**
  - `README.md`, `GUIDE.md`, `USER.md`

---

## 5. Ephemeral Test Rule

Never commit or push test folders or temporary files (`test_*`, `tests/`). All test scripts and temporary binaries must be removed locally and remotely before completing any task.
