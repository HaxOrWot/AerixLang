"""
Aerix Interactive REPL (arx repl)
Live Read-Eval-Print Loop supporting instant expression evaluation,
state accumulation, and immediate C99 native JIT execution.
"""

import sys
import os
import tempfile
import subprocess
from src.driver import AerixCompiler

BANNER = """\
\033[1;36m       ___         _      
      / _ \\___ ___(_)_ __ 
     / __ / -_) __/ /\\ \\ /
    /_/ |_\\__/_/ /_//_\\_\\ \033[0m
\033[1;32mAerix (arx) Interactive REPL v1.0.89-alpha\033[0m
Type expressions or definitions. Type '\033[1;33mexit\033[0m', '\033[1;33mquit\033[0m', or \033[1;33mCtrl+C\033[0m to quit.
Type '\033[1;33mreset\033[0m' to clear accumulated declarations.
"""


class AerixREPL:
    def __init__(self):
        self.compiler = AerixCompiler()
        self.accumulated_decls = []
        self.accumulated_statements = []

    def run(self):
        print(BANNER)
        buffer = []

        while True:
            try:
                prompt = "\033[1;36marx>\033[0m " if not buffer else "\033[1;36m ...\033[0m "
                line = input(prompt)
            except (EOFError, KeyboardInterrupt):
                print("\nExiting Aerix REPL. Farewell!")
                break

            stripped = line.strip()
            if not buffer and stripped in ("exit", "quit", ":q"):
                print("Exiting Aerix REPL. Farewell!")
                break
            if not buffer and stripped == "reset":
                self.accumulated_decls.clear()
                self.accumulated_statements.clear()
                print("\033[1;32m[REPL RESET]\033[0m Cleared session state.")
                continue
            if not buffer and not stripped:
                continue

            buffer.append(line)
            code_block = "\n".join(buffer)

            # Check brace balance
            opens = code_block.count("{")
            closes = code_block.count("}")
            if opens > closes:
                continue # Multiline continuation

            # Balanced: evaluate code
            self.eval_block(code_block)
            buffer.clear()

    def eval_block(self, code: str) -> None:
        trimmed = code.strip()

        # If it's a top-level declaration (fn, class, enum)
        is_decl = any(trimmed.startswith(kw) for kw in ("fn ", "class ", "enum ", "extend ", "cinclude ", "cextern "))
        
        # Test code generation
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_file = os.path.join(tmp_dir, "repl_turn.arx")
            exe_file = os.path.join(tmp_dir, "repl_turn.exe")

            full_code = []
            full_code.extend(self.accumulated_decls)
            if is_decl:
                full_code.append(code)
                full_code.append("fn main() { }")
            else:
                # Wrap inside main
                full_code.append("fn main() {")
                for s in self.accumulated_statements:
                    full_code.append(f"    {s}")
                
                # Check if it's an expression that should be auto-printed
                is_stmt = any(trimmed.startswith(kw) for kw in ("let ", "mut ", "for ", "while ", "if ", "defer ", "guard ", "match ")) or "=" in trimmed
                if not is_stmt and not trimmed.startswith("println(") and not trimmed.startswith("print("):
                    full_code.append(f'    println({code})')
                else:
                    full_code.append(f"    {code}")
                full_code.append("}")

            source_content = "\n".join(full_code)
            with open(source_file, "w", encoding="utf-8") as f:
                f.write(source_content)

            try:
                out_exe = self.compiler.compile_file(source_file, output_binary_path=exe_file)
                res = subprocess.run([out_exe], capture_output=True, text=True)
                if res.stdout:
                    print(res.stdout, end="")
                if res.stderr:
                    print(f"\033[1;31m{res.stderr}\033[0m", end="")

                if res.returncode == 0:
                    if is_decl:
                        self.accumulated_decls.append(code)
                    elif trimmed.startswith("let ") or trimmed.startswith("mut "):
                        self.accumulated_statements.append(code)
            except Exception as e:
                print(f"\033[1;31m[REPL ERROR]\033[0m: {e}")
