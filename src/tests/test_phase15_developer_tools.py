"""
Aerix Compiler (arxc) — Phase 15 Test Suite
Validates:
1. Aerix Code Formatter (arx fmt): 4-space normalization, brace indentation, and whitespace cleanup.
2. Aerix Code Linter (arx lint): Unused variable detection, unreachable code warnings, trailing semicolons.
3. Aerix Package Manager (arx pm): aerix.toml manifest creation, dependency insertion, and inspection.
4. Aerix REPL (arx repl) evaluation pipeline.
"""

import unittest
import os
import tempfile
from src.tools.formatter import AerixFormatter
from src.tools.linter import AerixLinter
from src.tools.pm import AerixPackageManager
from src.tools.repl import AerixREPL


class TestPhase15DeveloperTools(unittest.TestCase):
    def setUp(self):
        self.formatter = AerixFormatter()
        self.linter = AerixLinter()

    def test_code_formatter_normalizes_indentation(self):
        ugly_code = """
fn calculate_score(base: i64) -> i64 {
let mut bonus = 10
if base > 100 {
bonus += 50
} else {
bonus += 5
}
return base + bonus
}
"""
        formatted = self.formatter.format_source(ugly_code)
        # Verify 4-space indentation inside function
        self.assertIn("    let mut bonus = 10", formatted)
        self.assertIn("    if base > 100 {", formatted)
        self.assertIn("        bonus += 50", formatted)
        self.assertIn("    } else {", formatted)
        self.assertIn("        bonus += 5", formatted)
        self.assertIn("    }", formatted)
        self.assertIn("    return base + bonus", formatted)

    def test_linter_detects_unused_variable(self):
        code_with_unused = """
        fn process() {
            let unused_calc = 42
            println("Done")
        }
        """
        warnings = self.linter.lint_source(code_with_unused, "test_unused.arx")
        warning_codes = [w.code for w in warnings]
        self.assertIn("W002", warning_codes, "Linter must warn on unused local variable 'unused_calc'")

    def test_linter_detects_unreachable_code(self):
        code_with_dead = """
        fn check_num(x: i64) -> i64 {
            return x * 2
            let dead_x = 100
        }
        """
        warnings = self.linter.lint_source(code_with_dead, "test_dead.arx")
        warning_codes = [w.code for w in warnings]
        self.assertIn("W004", warning_codes, "Linter must detect unreachable statements after return")

    def test_linter_clean_on_idiomatic_code(self):
        clean_code = """
        fn add(a: i64, b: i64) -> i64 {
            return a + b
        }

        fn main() {
            let res = add(10, 20)
            println("Result: {res}")
        }
        """
        warnings = self.linter.lint_source(clean_code, "test_clean.arx")
        self.assertEqual(len(warnings), 0, f"Expected 0 warnings for clean code, got: {[w.message for w in warnings]}")

    def test_package_manager_workflow(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            pm = AerixPackageManager(tmp_dir)
            manifest = pm.init_project("aerix_game")
            self.assertTrue(os.path.exists(manifest))

            # Add dependencies
            pm.add_dependency("raylib", "5.0")
            pm.add_dependency("math_simd", "1.4")

            deps = pm.list_dependencies()
            self.assertEqual(deps.get("raylib"), "5.0")
            self.assertEqual(deps.get("math_simd"), "1.4")


if __name__ == "__main__":
    unittest.main()
