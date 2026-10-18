"""
Aerix Compiler (arxc) — Multi-Pass Pipeline Orchestrator
Executes the full end-to-end compilation pipeline:
Source (.arx) ➔ Lexer ➔ Parser ➔ Semantics ➔ AIR ➔ Optimizer ➔ Codegen (C99) ➔ Linker (GCC) ➔ Binary (.exe)
"""

import os
import subprocess
import tempfile
from typing import Optional, Tuple
from src.frontend.lexer import Lexer
from src.frontend.parser import Parser
from src.middle.semantic import SemanticAnalyzer
from src.middle.air import AIRLowering, AIRModule
from src.middle.optimizer import AIROptimizer
from src.backend.codegen import C99CodeGenerator
from src.backend.linker import NativeLinker


class AerixCompiler:
    def __init__(self, stdlib_path: Optional[str] = None):
        self.stdlib_path = stdlib_path
        self.linker = NativeLinker(stdlib_path)

    def compile_source_to_c(self, source: str, filename: str = "<stdin>") -> str:
        """Runs frontend and middle-end passes and emits optimized C99 source."""
        lines = source.splitlines()

        # 1. Lexer
        lexer = Lexer(source, filename)
        tokens = lexer.tokenize()

        # 2. Parser
        parser = Parser(tokens, lines)
        ast = parser.parse()

        # 2b. Generic Monomorphizer (Phase 18)
        from src.middle.monomorphizer import GenericMonomorphizer
        monomorphizer = GenericMonomorphizer()
        ast = monomorphizer.monomorphize(ast)

        # 3. Semantic Analysis
        analyzer = SemanticAnalyzer(filename, lines)
        analyzer.analyze(ast)

        # 4. AIR Lowering
        lowering = AIRLowering()
        air_module = lowering.lower(ast)

        # 5. Optimization (arxc-opt)
        optimizer = AIROptimizer()
        opt_air = optimizer.optimize(air_module)

        # 6. C99 Code Generation
        codegen = C99CodeGenerator()
        return codegen.generate(opt_air)

    def compile_file(
        self,
        input_path: str,
        output_binary_path: Optional[str] = None,
        release: bool = False,
        emit_c_path: Optional[str] = None
    ) -> str:
        """Compiles an Aerix source file (.arx) to a native executable (.exe)."""
        with open(input_path, "r", encoding="utf-8") as f:
            source = f.read()

        c_code = self.compile_source_to_c(source, input_path)

        # Save C code if requested or to cache
        if emit_c_path:
            with open(emit_c_path, "w", encoding="utf-8") as f:
                f.write(c_code)
            c_file_path = emit_c_path
        else:
            temp_cache_dir = os.path.join(tempfile.gettempdir(), "aerix_cache")
            os.makedirs(temp_cache_dir, exist_ok=True)
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            c_file_path = os.path.join(temp_cache_dir, f"{base_name}.c")
            with open(c_file_path, "w", encoding="utf-8") as f:
                f.write(c_code)

        # Determine binary name
        if not output_binary_path:
            base_name = os.path.splitext(input_path)[0]
            output_binary_path = f"{base_name}.exe" if os.name == "nt" else base_name

        self.linker.compile_c_to_binary(c_file_path, output_binary_path, release=release)
        return output_binary_path

    def run_file(self, input_path: str, args: Optional[list] = None) -> int:
        """
        Compiles an Aerix file and executes it immediately.
        Uses content-hashed incremental caching: if the source has not changed, skips compilation entirely!
        Leaves ZERO .aerix_cache and ZERO .exe in the user's project directory.
        """
        import hashlib
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        with open(input_path, "rb") as f:
            src_bytes = f.read()

        # Content hash matches native C runner (FNV-1a 64-bit)
        h = 14695981039346656037
        for b in src_bytes:
            h = (h ^ b) * 1099511628211
            h &= 0xFFFFFFFFFFFFFFFF
        h_str = f"{h:x}"
        cache_dir = os.path.join(tempfile.gettempdir(), "aerix_cache")
        os.makedirs(cache_dir, exist_ok=True)
        cached_exe = os.path.join(cache_dir, f"fast_{h_str}.exe" if os.name == "nt" else f"fast_{h_str}")

        # If cache misses or binary missing/corrupt, compile to cache
        if not os.path.exists(cached_exe) or os.path.getsize(cached_exe) == 0:
            self.compile_file(input_path, output_binary_path=cached_exe)

        cmd = [cached_exe] + (args or [])
        res = subprocess.run(cmd)
        return res.returncode


