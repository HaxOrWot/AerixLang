"""
Aerix Compiler (arxc) — Standalone Compiler CLI Entrypoint
Usage:
    python arxc.py <file.arx> [-o <output_binary>] [--release] [--emit-c]
"""

import sys
import os
import argparse

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project root or bundle dir is in sys.path
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    if sys._MEIPASS not in sys.path:
        sys.path.insert(0, sys._MEIPASS)
else:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from src.driver import AerixCompiler
from src.frontend.diagnostics import report_fatal_error, enable_windows_ansi


def main():
    enable_windows_ansi()
    parser = argparse.ArgumentParser(
        prog="arxc",
        description="The Custom Aerix Compiler (arxc) — Multi-Pass Native Optimizing Compiler"
    )
    parser.add_argument("input_file", help="Path to the Aerix source file (.arx)")
    parser.add_argument("-o", "--output", help="Path to the output native executable")
    parser.add_argument("--release", action="store_true", help="Compile with maximum -O3 and LTO optimizations")
    parser.add_argument("--emit-c", help="Output path for intermediate C99 source file")
    
    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        sys.exit(report_fatal_error(FileNotFoundError(args.input_file)))

    compiler = AerixCompiler()
    try:
        if args.emit_c:
            with open(args.input_file, "r", encoding="utf-8") as f:
                c_code = compiler.compile_source_to_c(f.read(), args.input_file)
            with open(args.emit_c, "w", encoding="utf-8") as f:
                f.write(c_code)
            print(f"\033[1;32m[SUCCESS]\033[0m: Emitted C99 source to '{args.emit_c}'")
        else:
            out_bin = compiler.compile_file(
                args.input_file,
                output_binary_path=args.output,
                release=args.release
            )
            print(f"\033[1;32m[SUCCESS]\033[0m: Compiled '{args.input_file}' -> '{out_bin}'")
    except Exception as e:
        sys.exit(report_fatal_error(e))


if __name__ == "__main__":
    main()
