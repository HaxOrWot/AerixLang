# Git Branching & Versioning Instructions (`GIT-INS.md`)

This document defines the mandatory Git workflow and versioning rules for the **AerixLang** project.

## 1. Branch Strategy

| Branch | Purpose | Version Format | Example |
| --- | --- | --- | --- |
| `beta` | **Default active development branch.** All ongoing edits, experiments, bug fixes, and work-in-progress commits must be pushed here until a build is verified and ready for release. | `<major>.<minor>.<patch>b` | `1.1.2b`, `1.1.3b`, `1.1.4b` |
| `pre` | Pre-release / release-candidate validation branch prior to stable promotion. | `<major>.<minor>.<patch>p` | `1.1.2p`, `1.1.3p` |
| `stable` / `master` | **Production / verified release branches only.** Synced identically when all changes from `beta` / `pre` are tested and working cleanly. | `<major>.<minor>.<patch>-stable` | `1.1.2-stable`, `1.1.3-stable` |

## 2. Rules for Every Change

1. **Always Work & Push to `beta` First**
   - Every time any change is made to the project during development/iteration, commit and push to the `beta` branch (`origin/beta`).
   - Do **not** push untested or intermediate fixes directly to `master` or `stable`.
   - Keep working and iterating on `beta` across multiple fixes/changes until the entire build is verified working.

2. **Increment Version by `+1` on Every Change**
   - Every change pushed increments the patch version by `1` with the branch suffix:
     - On `beta`: `1.1.2` -> `1.1.2b` -> `1.1.3b` -> `1.1.4b` ... (`b` = beta)
     - On `pre`: `<version>p` (e.g., `1.1.2p` -> `1.1.3p`, `p` = pre-release)
     - On `stable` & `master`: `<version>-stable` (e.g., `1.1.2-stable` -> `1.1.3-stable`)

3. **Keep Project & Extension Versions Synchronized**
   - Update compiler/installer version references:
     - `AerixInstaller/src/installer_manifest.json` (`"version"`)
     - `AerixInstaller/src/InstallerEngine.cs` (`DefaultVersion`)
     - `AerixInstaller/src/AssemblyInfo.cs` (`AssemblyVersion` / `AssemblyFileVersion`, numeric `X.Y.Z.0`)
     - `src/bootstrap/main.arx` (`--version` banner) and regenerate `src/bootstrap/seed/arxc.c`
   - **If anything in `editors/vscode-aerix/` changes**, also update the extension version in `editors/vscode-aerix/package.json` (`"version"`) and rebuild the packaged `.vsix` (using valid SemVer when packaging VSIX if required by `vsce`, e.g., `1.1.3-b` / `1.1.3-p` / `1.1.3-stable`, while keeping `installer_manifest.json` aligned).

4. **Promoting a Verified Build to `stable` / `master`**
   - Only after everything is built, installed, and verified end-to-end on `beta`:
     - Switch target version strings to `<major>.<minor>.<patch>-stable`.
     - Rebuild seed (`arxc.c`), VSIX (`.vsix`), and standalone installer (`AerixSetup-<version>-stable.exe`).
     - Sync both `stable` and `master` cleanly to the same commit, tag `v<version>-stable`, and publish/update the GitHub Release assets & notes.
