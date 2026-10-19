"""
Aerix Compiler (arxc) — Native Linker & Toolchain Orchestrator
Invokes host C compiler (GCC / Clang) to produce optimized standalone native binaries.
"""

import os
import shutil
import subprocess
from typing import List, Optional, Tuple
from src.frontend.diagnostics import AerixDiagnostic, format_simple_error


class LinkerError(AerixDiagnostic):
    def __init__(self, message: str, gcc_output: str = "", hint: Optional[str] = None):
        self.message = message
        self.gcc_output = gcc_output
        self.hint = hint
        
        detail = message
        if gcc_output:
            detail = f"{message}\n\n[GCC OUTPUT]:\n{gcc_output.strip()}"
        super().__init__(format_simple_error("LINKER ERROR", detail, hint=hint))


class NativeLinker:
    def __init__(self, stdlib_path: Optional[str] = None):
        self.stdlib_path = stdlib_path or self.discover_stdlib_path()
        self.compiler_exe = self.discover_c_compiler()

    def discover_stdlib_path(self) -> str:
        import sys
        candidates = []
        # 1. PyInstaller bundled temp dir
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            candidates.append(os.path.join(sys._MEIPASS, "stdlib"))
        # 2. Next to executable
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        candidates.append(os.path.join(exe_dir, "stdlib"))
        candidates.append(os.path.abspath(os.path.join(exe_dir, "..", "stdlib")))
        # 3. Relative to this module
        current_dir = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.abspath(os.path.join(current_dir, "..", "..", "stdlib")))
        candidates.append(os.path.abspath(os.path.join(current_dir, "..", "stdlib")))
        # 4. User home installation directory (~/.aerix/stdlib)
        candidates.append(os.path.expanduser("~/.aerix/stdlib"))

        for c in candidates:
            if os.path.exists(os.path.join(c, "aerix_rt.h")):
                return os.path.abspath(c)
        return candidates[2] if len(candidates) > 2 else candidates[0]

    def discover_c_compiler(self) -> str:
        """Finds gcc or clang on system PATH."""
        for name in ("gcc", "clang", "gcc.exe", "clang.exe"):
            found = shutil.which(name)
            if found:
                return found
        return "gcc" # Fallback

    def compile_c_to_binary(
        self,
        c_source_path: str,
        output_binary_path: str,
        release: bool = False,
        extra_flags: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        """Compiles a .c file into a standalone native executable using GCC."""
        flags = [
            self.compiler_exe,
            "-pipe",
            "-std=c99",
            "-Wall",
            "-Wno-unused-variable",
            "-Wno-unused-function",
            "-I", self.stdlib_path,
        ]

        if release:
            flags.extend(["-O3", "-flto", "-march=native", "-s", "-DNDEBUG"])
        else:
            flags.extend(["-O1", "-s"])

        if extra_flags:
            flags.extend(extra_flags)

        flags.extend([c_source_path, "-o", output_binary_path, "-lm"])

        try:
            res = subprocess.run(
                flags,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            if res.returncode != 0:
                raise LinkerError("Native C compilation failed", res.stderr or res.stdout)
            return True, res.stdout
        except FileNotFoundError:
            raise LinkerError(
                f"C compiler '{self.compiler_exe}' was not found on PATH. "
                f"Please ensure GCC or MinGW is installed."
            )

