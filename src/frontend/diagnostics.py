"""
Aerix Compiler (arxc) — Unified Diagnostic Architecture
Industry-grade diagnostic error reporting, multi-error aggregation,
source-code caret rendering, and ANSI terminal color support.
"""

import os
import sys
from typing import List, Optional, Any


def enable_windows_ansi() -> None:
    """Enables ANSI escape sequence processing in Windows Console."""
    if os.name == "nt":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # STD_OUTPUT_HANDLE = -11, STD_ERROR_HANDLE = -12
            for handle_id in (-11, -12):
                handle = kernel32.GetStdHandle(handle_id)
                mode = ctypes.c_ulong()
                if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                    # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
                    kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            pass


def supports_color() -> bool:
    """Checks whether the output stream supports ANSI color sequences."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return hasattr(sys.stderr, "isatty") and sys.stderr.isatty()


def format_source_snippet(
    file: str,
    line: int,
    col: int,
    source_line: str,
    message: str,
    error_type: str = "PARSER ERROR",
    length: int = 1,
    hint: Optional[str] = None
) -> str:
    """Formats a clean Rust/Clang-style source diagnostic."""
    use_color = supports_color()
    bold_red = "\033[1;31m" if use_color else ""
    bold_blue = "\033[1;34m" if use_color else ""
    bold_cyan = "\033[1;36m" if use_color else ""
    bold_white = "\033[1;37m" if use_color else ""
    reset = "\033[0m" if use_color else ""

    caret = "^" * max(1, length)
    indent = " " * max(0, col - 1)

    hint_str = ""
    if hint:
        hint_str = f"\n   {bold_cyan}={reset} {bold_white}help{reset}: {hint}"

    return (
        f"{bold_red}[AERIX {error_type}]{reset}: {bold_white}{message}{reset}\n"
        f"  {bold_blue}-->{reset} {file}:{line}:{col}\n"
        f"   {bold_blue}|{reset}\n"
        f"{bold_blue}{line:4d} |{reset} {source_line}\n"
        f"   {bold_blue}|{reset} {indent}{bold_red}{caret}{reset}{hint_str}"
    )


def format_simple_error(error_type: str, message: str, hint: Optional[str] = None) -> str:
    """Formats a clean non-code diagnostic (e.g. CLI, Linker, FileSystem)."""
    use_color = supports_color()
    bold_red = "\033[1;31m" if use_color else ""
    bold_white = "\033[1;37m" if use_color else ""
    bold_cyan = "\033[1;36m" if use_color else ""
    reset = "\033[0m" if use_color else ""

    hint_str = ""
    if hint:
        hint_str = f"\n  {bold_cyan}={reset} {bold_white}help{reset}: {hint}"

    return f"{bold_red}[AERIX {error_type}]{reset}: {bold_white}{message}{reset}{hint_str}"


class AerixDiagnostic(Exception):
    """Base class for all Aerix compiler errors and diagnostics."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ParserError(AerixDiagnostic):
    """Raised on syntax or parsing grammar errors."""
    def __init__(self, message: str, token: Optional[Any] = None, source_line: str = "", hint: Optional[str] = None):
        self.message = message
        self.token = token
        self.line = getattr(token, "line", 1) if token else 1
        self.col = getattr(token, "col", 1) if token else 1
        self.source_line = source_line
        self.hint = hint
        formatted = format_source_snippet(
            file=getattr(token, "file", "<stdin>") if token else "<stdin>",
            line=self.line,
            col=self.col,
            source_line=source_line,
            message=message,
            error_type="PARSER ERROR",
            hint=hint
        ) if token else message
        super().__init__(formatted)


class DiagnosticBag(ParserError):
    """Aggregates multiple compiler errors so the developer sees all issues in one compiler pass."""
    def __init__(self, errors: List[AerixDiagnostic], file: str = ""):
        self.errors = errors
        self.file = file
        count = len(errors)
        err_word = "error" if count == 1 else "errors"
        
        rendered = "\n\n".join(str(e).strip() for e in errors)
        use_color = supports_color()
        bold_red = "\033[1;31m" if use_color else ""
        reset = "\033[0m" if use_color else ""

        target_file = f"'{file}'" if file else "target"
        summary = f"\n\n{bold_red}error{reset}: could not compile {target_file} due to {count} previous {err_word}"
        first_err = errors[0] if errors else None
        super().__init__(
            message=f"{rendered}{summary}",
            token=getattr(first_err, "token", None),
            source_line=getattr(first_err, "source_line", "")
        )
        self.line = getattr(first_err, "line", 1) if first_err else 1
        self.col = getattr(first_err, "col", 1) if first_err else 1


def report_fatal_error(e: Exception) -> int:
    """
    Top-level CLI error handler.
    Prints a beautiful, professional Aerix diagnostic to stderr with NO Python tracebacks,
    unless AERIX_DEBUG=1 is set in the environment.
    """
    enable_windows_ansi()

    if os.environ.get("AERIX_DEBUG") == "1":
        import traceback
        traceback.print_exc()
        return 1

    if isinstance(e, AerixDiagnostic):
        sys.stderr.write(f"{str(e)}\n")
    elif isinstance(e, FileNotFoundError):
        msg = format_simple_error("IO ERROR", f"File not found: '{e.filename or str(e)}'", hint="verify that the file path is correct and exists")
        sys.stderr.write(f"{msg}\n")
    elif isinstance(e, PermissionError):
        msg = format_simple_error("PERMISSION ERROR", f"Permission denied accessing: '{e.filename or str(e)}'")
        sys.stderr.write(f"{msg}\n")
    elif isinstance(e, KeyboardInterrupt):
        sys.stderr.write("\nCompilation aborted by user.\n")
        return 130
    else:
        msg = format_simple_error("INTERNAL ERROR", str(e), hint="run with AERIX_DEBUG=1 to see full internal traceback")
        sys.stderr.write(f"{msg}\n")
    return 1
