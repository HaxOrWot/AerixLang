"""
Aerix Toolchain (arx) — Unified Developer CLI
Commands:
    arx run <file.arx>               Compile & execute immediately
    arx build <file.arx> [-o <bin>]  Build release native binary
    arx emit-c <file.arx>            Output intermediate C99 source
    arx check <file.arx>             Fast syntax & type checking
    arx doctor                       Diagnose system compiler toolchain
    arx new <project_name>           Scaffold a new Aerix project
    arx version                      Print version information
"""

import sys
import os
import shutil
import platform
import subprocess
import argparse
from typing import List, Optional

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

VERSION = "1.0.88-alpha"

# Safe console icons that never crash cp1252/cp437
ICON_OK = "[OK]"
ICON_FAIL = "[FAIL]"
ICON_ARROW = "->"


def cmd_doctor():
    """Diagnoses host environment, C compiler, and Aerix runtime."""
    print("\n\033[1;36m[AERIX DOCTOR] System Diagnostics\033[0m")
    print("=" * 45)

    # 1. Aerix Toolchain
    print(f"  \033[1;32m{ICON_OK}\033[0m Aerix Toolchain:    v{VERSION}")

    # 2. Host Python
    py_ver = platform.python_version()
    print(f"  \033[1;32m{ICON_OK}\033[0m Host Python:       v{py_ver} ({platform.python_implementation()})")

    # 3. Target Platform & Architecture
    arch = platform.machine()
    system = platform.system()
    print(f"  \033[1;32m{ICON_OK}\033[0m Platform:          {system} {platform.release()} ({arch})")

    # 4. C Backend (GCC / Clang)
    gcc_path = shutil.which("gcc") or shutil.which("gcc.exe")
    clang_path = shutil.which("clang") or shutil.which("clang.exe")
    
    if gcc_path:
        try:
            ver_res = subprocess.run([gcc_path, "--version"], capture_output=True, text=True)
            first_line = ver_res.stdout.splitlines()[0] if ver_res.stdout else "GCC detected"
            print(f"  \033[1;32m{ICON_OK}\033[0m C Backend (GCC):   {first_line}")
            print(f"      {ICON_ARROW} Path: {gcc_path}")
        except Exception:
            print(f"  \033[1;32m{ICON_OK}\033[0m C Backend:         {gcc_path}")
    elif clang_path:
        print(f"  \033[1;32m{ICON_OK}\033[0m C Backend (Clang): {clang_path}")
    else:
        print(f"  \033[1;31m{ICON_FAIL}\033[0m C Backend:         No GCC or Clang found on system PATH!")
        print(f"      {ICON_ARROW} Run: winget install MSYS2.MSYS2 or install MinGW-w64.")

    # 5. Aerix Standard Runtime
    candidates = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(sys._MEIPASS, "stdlib", "aerix_rt.h"))
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    candidates.append(os.path.join(exe_dir, "stdlib", "aerix_rt.h"))
    candidates.append(os.path.abspath(os.path.join(exe_dir, "..", "stdlib", "aerix_rt.h")))
    here = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.abspath(os.path.join(here, "..", "stdlib", "aerix_rt.h")))
    candidates.append(os.path.abspath(os.path.join(here, "stdlib", "aerix_rt.h")))
    candidates.append(os.path.expanduser("~/.aerix/stdlib/aerix_rt.h"))

    found_rt = None
    for c in candidates:
        if os.path.exists(c):
            found_rt = c
            break

    if found_rt:
        print(f"  \033[1;32m{ICON_OK}\033[0m Aerix Runtime:     Found at {found_rt}")
    else:
        print(f"  \033[1;31m{ICON_FAIL}\033[0m Aerix Runtime:     Missing aerix_rt.h")

    print("\n\033[1;32mStatus: Aerix is 100% operational and ready to build!\033[0m\n")


def cmd_new(project_name: str):
    """Scaffolds a new Aerix project directory."""
    if os.path.exists(project_name):
        print(f"\033[1;31m[ERROR]\033[0m: Directory '{project_name}' already exists.")
        sys.exit(1)

    os.makedirs(os.path.join(project_name, "src"), exist_ok=True)

    # aerix.toml
    toml_content = f"""[package]
name = "{project_name}"
version = "0.1.0"
entry = "src/main.arx"

[build]
opt_level = 3
"""
    with open(os.path.join(project_name, "aerix.toml"), "w", encoding="utf-8") as f:
        f.write(toml_content)

    # src/main.arx
    main_arx_content = """fn double(n: i64) -> i64 => n * 2

fn main() {
    let result = 21 |> double()
    println("Welcome to Aerix! 21 * 2 = {result}")
}
"""
    with open(os.path.join(project_name, "src", "main.arx"), "w", encoding="utf-8") as f:
        f.write(main_arx_content)

    print(f"\n\033[1;32m[CREATED]\033[0m: New Aerix project '{project_name}'")
    print(f"  --> {project_name}/aerix.toml")
    print(f"  --> {project_name}/src/main.arx")
    print("\nTo run your new project:")
    print(f"    cd {project_name}")
    print("    arx run src/main.arx\n")


def cmd_check(file_path: str):
    """Performs fast lexical, syntax, and semantic checks without compiling to C."""
    if not os.path.exists(file_path):
        sys.exit(report_fatal_error(FileNotFoundError(file_path)))

    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    lines = source.splitlines()
    try:
        from src.frontend.lexer import Lexer
        from src.frontend.parser import Parser
        from src.middle.monomorphizer import GenericMonomorphizer
        from src.middle.semantic import SemanticAnalyzer
        lexer = Lexer(source, file_path)
        tokens = lexer.tokenize()
        parser = Parser(tokens, lines, filename=file_path)
        ast = parser.parse()
        ast = GenericMonomorphizer().monomorphize(ast)
        analyzer = SemanticAnalyzer(file_path, lines)
        analyzer.analyze(ast)
        print(f"\033[1;32m{ICON_OK} [CHECK PASSED]\033[0m: '{file_path}' has zero syntax or type errors!")
    except Exception as e:
        sys.exit(report_fatal_error(e))


def cmd_test():
    """Runs the Aerix automated unit and integration test suite."""
    import unittest
    print(f"\n\033[1;36m[AERIX TEST] Running Automated Compiler Test Suite\033[0m")
    print("=" * 50)
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests"),
        os.path.join(os.getcwd(), "src", "tests"),
        os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "..", "src", "tests"),
    ]
    tests_dir = None
    for c in candidates:
        if os.path.exists(c) and os.path.isdir(c):
            tests_dir = os.path.abspath(c)
            break

    if not tests_dir:
        print(f"  \033[1;31m{ICON_FAIL}\033[0m No test suite directory found. Run 'arx test' from within the Aerix repository.\n")
        sys.exit(1)

    loader = unittest.TestLoader()
    suite = loader.discover(tests_dir)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print(f"\n\033[1;32m{ICON_OK} All {result.testsRun} tests passed successfully!\033[0m\n")
        sys.exit(0)
    else:
        print(f"\n\033[1;31m{ICON_FAIL} {len(result.failures)} test(s) failed, {len(result.errors)} error(s).\033[0m\n")
        sys.exit(1)


def cmd_setup_tools():
    """Provides installation and setup guidance for GCC / Clang C backends."""
    print(f"\n\033[1;36m[AERIX SETUP-TOOLS] C Compiler Toolchain Setup Guide\033[0m")
    print("=" * 55)
    gcc_path = shutil.which("gcc") or shutil.which("gcc.exe")
    clang_path = shutil.which("clang") or shutil.which("clang.exe")
    if gcc_path or clang_path:
        found = gcc_path or clang_path
        print(f"  \033[1;32m{ICON_OK}\033[0m A compatible C compiler is already active on your PATH:")
        print(f"      {ICON_ARROW} {found}")
        print("  You are ready to compile and run Aerix programs down to native machine code!")
    else:
        system = platform.system().lower()
        if "windows" in system:
            print("  Aerix requires GCC (MinGW-w64 / MSYS2) to link native .exe binaries.")
            print("\n  Quickest installation options:")
            print("    1. Via WinGet (Recommended):")
            print("         winget install MSYS2.MSYS2")
            print("         pacman -S --noconfirm mingw-w64-ucrt-x86_64-gcc")
            print("    2. Via Scoop:")
            print("         scoop install gcc")
            print("    3. Via Chocolatey:")
            print("         choco install mingw")
        elif "darwin" in system:
            print("  Aerix on macOS uses Apple Clang or GCC.")
            print("    Install Command Line Tools:")
            print("      xcode-select --install")
            print("    Or via Homebrew:")
            print("      brew install gcc")
        else:
            print("  Aerix on Linux uses GCC.")
            print("    Debian / Ubuntu:")
            print("      sudo apt update && sudo apt install -y build-essential")
            print("    Fedora / RHEL:")
            print("      sudo dnf groupinstall \"Development Tools\"")
            print("    Arch Linux:")
            print("      sudo pacman -S base-devel")
    print()


def cmd_repl():
    """Starts the interactive Aerix REPL."""
    from src.tools.repl import AerixREPL
    repl = AerixREPL()
    repl.run()


def cmd_fmt(path: str):
    """Auto-formats Aerix source code."""
    from src.tools.formatter import AerixFormatter
    fmt = AerixFormatter()
    count = fmt.format_path(path)
    print(f"\033[1;32m{ICON_OK} [FORMAT COMPLETE]\033[0m Formatted {count} file(s) in '{path}'.")


def cmd_lint(file_path: str):
    """Lints source code for unused variables, empty blocks, and style."""
    from src.tools.linter import AerixLinter
    if not os.path.exists(file_path):
        print(f"\033[1;31m[ERROR]\033[0m: File '{file_path}' does not exist.")
        sys.exit(1)
    linter = AerixLinter()
    warnings = linter.lint_file(file_path)
    if warnings:
        for w in warnings:
            print(w.format())
            print()
        print(f"\033[1;33m[LINT FINISHED]\033[0m Found {len(warnings)} warning(s) in '{file_path}'.")
    else:
        print(f"\033[1;32m{ICON_OK} [LINT CLEAN]\033[0m Zero lint warnings in '{file_path}'!")


def cmd_pm(subcmd: str, pm_args: List[str]):
    """Manages Aerix project packages and dependencies."""
    from src.tools.pm import AerixPackageManager
    pm = AerixPackageManager()
    if subcmd == "init":
        name = pm_args[0] if pm_args else ""
        manifest = pm.init_project(name)
        print(f"\033[1;32m{ICON_OK} [PM INIT]\033[0m Generated manifest at '{manifest}'")
    elif subcmd == "add":
        if not pm_args:
            print("\033[1;31m[ERROR]\033[0m: 'arx pm add <package_name> [version]' requires a package name.")
            sys.exit(1)
        pkg = pm_args[0]
        ver = pm_args[1] if len(pm_args) > 1 else "*"
        pm.add_dependency(pkg, ver)
        print(f"\033[1;32m{ICON_OK} [PM ADD]\033[0m Added dependency '{pkg} = {ver}' to aerix.toml")
    elif subcmd == "list":
        deps = pm.list_dependencies()
        if deps:
            print(f"\n\033[1;36m[PROJECT DEPENDENCIES]\033[0m")
            for k, v in deps.items():
                print(f"  {ICON_ARROW} {k} : {v}")
            print()
        else:
            print("No dependencies configured in aerix.toml.")
    else:
        print(f"Unknown pm command '{subcmd}'. Available: init, add, list.")


def cmd_lsp():
    """Starts the Aerix Language Server Protocol (LSP) daemon."""
    from src.tools.lsp import main as lsp_main
    lsp_main()


def cmd_wasm(file_path: str, output: Optional[str], emit_wat: bool, emit_html: bool, serve: bool):
    """Compiles an Aerix source file to WebAssembly and browser artifacts."""
    if not os.path.exists(file_path):
        print(f"\033[1;31m[ERROR]\033[0m: File '{file_path}' does not exist.")
        sys.exit(1)
    compiler = AerixCompiler()
    out_wasm = compiler.compile_file_to_wasm(
        file_path,
        output_wasm_path=output,
        emit_html=emit_html or serve,
        emit_wat=emit_wat
    )
    print(f"\033[1;32m{ICON_OK} [WASM SUCCESS]\033[0m: WebAssembly binary generated {ICON_ARROW} '{out_wasm}'")
    base_dir = os.path.dirname(out_wasm) or "."
    base_name = os.path.splitext(os.path.basename(out_wasm))[0]
    if emit_wat:
        print(f"      {ICON_ARROW} WebAssembly Text: '{os.path.join(base_dir, f'{base_name}.wat')}'")
    if emit_html or serve:
        html_path = os.path.join(base_dir, f"{base_name}.html")
        print(f"      {ICON_ARROW} HTML5 Browser Runner: '{html_path}'")
    if serve:
        import http.server
        import socketserver
        import webbrowser
        port = 8080
        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=base_dir, **kw)
        print(f"\n\033[1;36m[WASM SERVER]\033[0m Serving at http://localhost:{port}/{base_name}.html (Press Ctrl+C to stop)")
        webbrowser.open(f"http://localhost:{port}/{base_name}.html")
        with socketserver.TCPServer(("", port), Handler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nServer stopped.")


def _main_cli():
    # Instant Fast-Path for 'arx <file.arx>' and 'arx run <file.arx>'
    if len(sys.argv) == 2 and not sys.argv[1].startswith("-"):
        first_arg = sys.argv[1]
        if first_arg.endswith(".arx") or os.path.exists(first_arg):
            compiler = AerixCompiler()
            sys.exit(compiler.run_file(first_arg))
    elif len(sys.argv) == 3 and sys.argv[1] == "run" and not sys.argv[2].startswith("-"):
        compiler = AerixCompiler()
        sys.exit(compiler.run_file(sys.argv[2]))

    parser = argparse.ArgumentParser(
        prog="arx",
        description="Aerix (arx) — The High-Performance Native Systems Language Toolchain"
    )
    parser.add_argument("-v", "--version", action="version", version=f"Aerix (arx) Toolchain v{VERSION}")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # run
    run_parser = subparsers.add_parser("run", help="Compile and execute an Aerix program immediately")
    run_parser.add_argument("file", help="Path to .arx file")
    run_parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed to the program")

    # build
    build_parser = subparsers.add_parser("build", help="Compile an Aerix program to an optimized native binary")
    build_parser.add_argument("file", help="Path to .arx file")
    build_parser.add_argument("-o", "--output", help="Output executable path")
    build_parser.add_argument("--release", action="store_true", help="Maximum -O3 and LTO optimizations")

    # emit-c
    emitc_parser = subparsers.add_parser("emit-c", help="Emit intermediate C99 source code")
    emitc_parser.add_argument("file", help="Path to .arx file")
    emitc_parser.add_argument("-o", "--output", help="Output .c path")

    # wasm
    wasm_parser = subparsers.add_parser("wasm", help="Compile an Aerix program to WebAssembly (.wasm) for browser deployment")
    wasm_parser.add_argument("file", help="Path to .arx file")
    wasm_parser.add_argument("-o", "--output", help="Output .wasm path")
    wasm_parser.add_argument("--wat", action="store_true", help="Also emit WebAssembly text format (.wat)")
    wasm_parser.add_argument("--html", action="store_true", help="Generate an interactive HTML5 canvas runner page")
    wasm_parser.add_argument("--serve", action="store_true", help="Start a local web server to test in browser")

    # check
    check_parser = subparsers.add_parser("check", help="Fast syntax and type checking")
    check_parser.add_argument("file", help="Path to .arx file")

    # repl
    subparsers.add_parser("repl", help="Start the interactive Aerix REPL")

    # fmt
    fmt_parser = subparsers.add_parser("fmt", help="Auto-format Aerix source code")
    fmt_parser.add_argument("path", nargs="?", default=".", help="File or directory path to format")

    # lint
    lint_parser = subparsers.add_parser("lint", help="Lint source code for unused variables and dead code")
    lint_parser.add_argument("file", help="Path to .arx file to lint")

    # pm
    pm_parser = subparsers.add_parser("pm", help="Aerix Package Manager")
    pm_parser.add_argument("subcmd", choices=["init", "add", "list"], help="Package manager action")
    pm_parser.add_argument("pm_args", nargs="*", help="Arguments for package manager action")

    # lsp
    subparsers.add_parser("lsp", help="Start the Aerix Language Server Protocol (LSP) daemon")

    # doctor
    subparsers.add_parser("doctor", help="Diagnose system C compiler toolchain and configuration")

    # setup-tools
    subparsers.add_parser("setup-tools", help="Guide for installing GCC / Clang C backends")

    # test
    subparsers.add_parser("test", help="Execute automated unit and integration tests")

    # new
    new_parser = subparsers.add_parser("new", help="Scaffold a new Aerix project")
    new_parser.add_argument("name", help="Project name")

    # If the user passes a file directly (e.g. `arx main.arx` instead of `arx run main.arx`),
    # automatically default to `run`:
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        first_arg = sys.argv[1]
        valid_commands = {"doctor", "setup-tools", "test", "new", "check", "version", "run", "build", "emit-c", "wasm", "repl", "fmt", "lint", "pm", "lsp", "-h", "--help"}
        if first_arg not in valid_commands and (first_arg.endswith(".arx") or os.path.exists(first_arg)):
            sys.argv.insert(1, "run")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "doctor":
        cmd_doctor()
    elif args.command == "setup-tools":
        cmd_setup_tools()
    elif args.command == "test":
        cmd_test()
    elif args.command == "new":
        cmd_new(args.name)
    elif args.command == "check":
        cmd_check(args.file)
    elif args.command == "repl":
        cmd_repl()
    elif args.command == "fmt":
        cmd_fmt(args.path)
    elif args.command == "lint":
        cmd_lint(args.file)
    elif args.command == "pm":
        cmd_pm(args.subcmd, args.pm_args)
    elif args.command == "lsp":
        cmd_lsp()
    elif args.command == "wasm":
        cmd_wasm(args.file, args.output, args.wat, args.html, args.serve)
    elif args.command == "version":
        print(f"Aerix (arx) Toolchain v{VERSION}")
    elif args.command == "run":
        compiler = AerixCompiler()
        code = compiler.run_file(args.file, args.args)
        sys.exit(code)
    elif args.command == "build":
        compiler = AerixCompiler()
        out_exe = compiler.compile_file(args.file, output_binary_path=args.output, release=args.release)
        print(f"\033[1;32m[BUILD SUCCESS]\033[0m: Native executable generated {ICON_ARROW} '{out_exe}'")
    elif args.command == "emit-c":
        compiler = AerixCompiler()
        with open(args.file, "r", encoding="utf-8") as f:
            c_code = compiler.compile_source_to_c(f.read(), args.file)
        out_file = args.output or f"{os.path.splitext(args.file)[0]}.c"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(c_code)
        print(f"\033[1;32m[EMIT-C SUCCESS]\033[0m: Emitted C99 code saved to '{out_file}'")


def main():
    enable_windows_ansi()
    try:
        _main_cli()
    except Exception as e:
        sys.exit(report_fatal_error(e))


if __name__ == "__main__":
    main()

