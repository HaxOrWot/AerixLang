"""
Aerix Code Formatter (arx fmt)
Normalizes indentation (4 spaces), removes trailing whitespace,
collapses consecutive blank lines, and formats braces cleanly.
"""

import os
import re


class AerixFormatter:
    def format_source(self, code: str) -> str:
        lines = code.splitlines()
        formatted_lines = []
        indent_level = 0
        indent_str = "    "
        consecutive_blank = 0

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                consecutive_blank += 1
                if consecutive_blank <= 1:
                    formatted_lines.append("")
                continue
            consecutive_blank = 0

            # If line starts with closing brace, decrease indent before printing
            starts_close = line.startswith("}") or line.startswith(")") or line.startswith("]")
            if starts_close:
                indent_level = max(0, indent_level - 1)

            formatted_lines.append((indent_str * indent_level) + line)

            # Count opens and closes in non-string portion
            line_no_str = re.sub(r'"(\\.|[^"\\])*"', '""', line)
            opens = line_no_str.count("{")
            closes = line_no_str.count("}")

            if not starts_close:
                indent_level = max(0, indent_level + opens - closes)
            else:
                indent_level = max(0, indent_level + opens - (closes - 1))

        return "\n".join(formatted_lines).strip() + "\n"

    def format_file(self, file_path: str) -> bool:
        if not os.path.exists(file_path):
            return False
        with open(file_path, "r", encoding="utf-8") as f:
            original = f.read()
        formatted = self.format_source(original)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(formatted)
        return True

    def format_path(self, path: str) -> int:
        count = 0
        if os.path.isfile(path):
            if path.endswith(".arx") and self.format_file(path):
                count += 1
        elif os.path.isdir(path):
            for root, _, files in os.walk(path):
                for file in files:
                    if file.endswith(".arx"):
                        p = os.path.join(root, file)
                        if self.format_file(p):
                            count += 1
        return count
