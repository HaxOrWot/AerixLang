"""
Aerix (arx) — Root Launcher Proxy
Delegates directly to src/arx.py
"""

import sys
import os

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

# Redirect execution directly to src.arx
if __name__ == "__main__":
    src_arx_path = os.path.join(os.path.dirname(__file__), "src", "arx.py")
    with open(src_arx_path, "r", encoding="utf-8") as f:
        code = f.read()
    globs = {
        "__file__": src_arx_path,
        "__name__": "__main__",
    }
    exec(compile(code, src_arx_path, "exec"), globs)


