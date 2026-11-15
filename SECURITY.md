# Security Policy

## Supported Versions

The Aerix project actively maintains security updates and patches for the current major and minor releases. We recommend all users keep their compiler and runtime updated to the latest stable release.

| Version | Supported | Security Maintenance |
| :--- | :---: | :--- |
| `2.x.x` (Current Stable) | :white_check_mark: | Full active security and bugfix support |
| `1.x.x` | :x: | Replaced by 2.x architectural milestone |
| Beta / Pre-release | :white_check_mark: | Best-effort experimental fixes on `beta` branch |

## Reporting a Vulnerability

The Aerix security team takes all potential vulnerabilities seriously. If you discover a security flaw, memory safety violation, compiler denial-of-service, or remote execution risk in the Aerix compiler, runtime (`aerix_rt.h`), or language server:

1. **Do NOT open a public issue.** Please report the issue confidentially so we can develop and test a fix before disclosure.
2. **Contact:**
   - Submit via **GitHub Security Advisories** on the AerixLang repository, or
   - Send an email to the project maintainers at: `security@aerix-lang.org`
3. **Include Details:**
   - Aerix version (`arx version`) and host operating system.
   - Minimal reproducible example (`.arx` source code).
   - Expected behavior versus observed behavior (e.g. stack trace, crash report, or memory dump).
   - Any potential attack vectors or impact assessment.

## Vulnerability Handling Timeline

- **Initial Response:** Within 48 hours of report receipt.
- **Triage & Reproduction:** Within 5 business days.
- **Patch Development:** Work begins immediately on a private security advisory branch.
- **Public Disclosure:** Coordinated release with patched binaries, release notes, and contributor attribution once the update is tested and deployed.

## Security Practices in Aerix

- The self-hosting compiler employs bounds checking and defensive memory arena allocation.
- The native PE32+ backend enforces 16-byte stack frame alignment and Win64 calling convention constraints.
- Generated code avoids unchecked buffer overruns and validates string slicing and array indices in safe builds.
