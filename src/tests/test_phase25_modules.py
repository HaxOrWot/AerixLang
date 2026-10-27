"""
Aerix Compiler (arxc) — Phase 25 Multi-File Module System Tests
Verifies:
1. Inbuilt Language Modules (import Math) with folder bundling & strict case-sensitivity
2. User-Created Multi-File imports (import "./helper.arx")
3. Distinct separation between User Files and Inbuilt Modules
4. Selective Symbol Imports (import { a, b } from ...)
5. Topological dependency resolution and cycle rejection
6. Full end-to-end native C compilation and execution
"""

import os
import sys
import shutil
import tempfile
import unittest

from src.frontend.lexer import Lexer
from src.frontend.parser import Parser
from src.frontend.ast_nodes import ImportNode
from src.middle.modules import (
    ModuleResolver, ModuleError, ModuleNotFoundError,
    ModuleCaseError, ModuleCircularError, ModuleSymbolNotFoundError,
    ModuleVerificationError
)
from src.driver import AerixCompiler


class TestPhase25Modules(unittest.TestCase):
    def setUp(self):
        self.compiler = AerixCompiler()

    def test_dynamic_file_discovery_in_module(self):
        # Adding a file inside a module folder dynamically must automatically be recognized
        with tempfile.TemporaryDirectory() as tmpdir:
            mod_dir = os.path.join(tmpdir, "DynMod")
            os.makedirs(mod_dir)

            with open(os.path.join(mod_dir, "initial.arx"), "w", encoding="utf-8") as f:
                f.write("pub fn f1() -> i64 { return 10; }\n")

            resolver = ModuleResolver(base_filename="main.arx", search_paths=[tmpdir])
            ast1 = Parser(Lexer("import DynMod;\n", "main.arx").tokenize(), ["import DynMod;"], filename="main.arx").parse()
            res1 = resolver.resolve(ast1)
            self.assertTrue(any(getattr(d, "name", None) == "f1" for d in res1.declarations))

            # Dynamically add a second file into DynMod
            with open(os.path.join(mod_dir, "added_later.arx"), "w", encoding="utf-8") as f:
                f.write("pub fn f2() -> i64 { return 20; }\n")

            resolver2 = ModuleResolver(base_filename="main.arx", search_paths=[tmpdir])
            ast2 = Parser(Lexer("import DynMod;\n", "main.arx").tokenize(), ["import DynMod;"], filename="main.arx").parse()
            res2 = resolver2.resolve(ast2)
            # Both f1 and dynamically added f2 must be recognized
            names = [getattr(d, "name", None) for d in res2.declarations]
            self.assertIn("f1", names)
            self.assertIn("f2", names)

    def test_new_module_test_compiled_and_registered(self):
        # Create a new module folder TEST with 3 .arx files
        with tempfile.TemporaryDirectory() as tmpdir:
            test_mod = os.path.join(tmpdir, "TEST")
            os.makedirs(test_mod)

            with open(os.path.join(test_mod, "calc.arx"), "w", encoding="utf-8") as f:
                f.write("pub fn calc_val(x: f64) -> f64 { return x * 2.5; }\n")

            with open(os.path.join(test_mod, "format.arx"), "w", encoding="utf-8") as f:
                f.write("pub fn format_code(id: i64) -> i64 { return id + 1000; }\n")

            with open(os.path.join(test_mod, "logic.arx"), "w", encoding="utf-8") as f:
                f.write("pub fn is_valid_range(x: f64) -> bool { return x > 0.0 && x < 100.0; }\n")

            main_file = os.path.join(tmpdir, "app.arx")
            with open(main_file, "w", encoding="utf-8") as f:
                f.write("""
import TEST;

fn main() {
    let c = calc_val(10.0);
    let code = format_code(42);
    let ok = is_valid_range(c);
    println(c);
}
""")
            with open(main_file, "r", encoding="utf-8") as f:
                content = f.read()
            resolver = ModuleResolver(base_filename=main_file, search_paths=[tmpdir])
            ast = Parser(Lexer(content, main_file).tokenize(), content.splitlines(), filename=main_file).parse()
            resolved = resolver.resolve(ast)

            # Check that .module_verified lockfile was generated upon verification & registration
            lockfile = os.path.join(test_mod, ".module_verified")
            self.assertTrue(os.path.isfile(lockfile), "Module TEST should be registered with .module_verified lockfile")

            # Check that all 3 files' symbols were bundled
            resolved_names = [getattr(d, "name", None) for d in resolved.declarations]
            self.assertIn("calc_val", resolved_names)
            self.assertIn("format_code", resolved_names)
            self.assertIn("is_valid_range", resolved_names)

    def test_new_module_rejected_if_compilation_errors(self):
        # A new module with syntax or semantic errors must NOT be registered
        with tempfile.TemporaryDirectory() as tmpdir:
            broken_mod = os.path.join(tmpdir, "BROKEN")
            os.makedirs(broken_mod)

            with open(os.path.join(broken_mod, "bad.arx"), "w", encoding="utf-8") as f:
                f.write("pub fn incomplete(\n") # syntax error!

            main_file = os.path.join(tmpdir, "main.arx")
            with open(main_file, "w", encoding="utf-8") as f:
                f.write("import BROKEN;\nfn main() { return; }\n")

            with open(main_file, "r", encoding="utf-8") as f:
                content = f.read()
            resolver = ModuleResolver(base_filename=main_file, search_paths=[tmpdir])
            ast = Parser(Lexer(content, main_file).tokenize(), content.splitlines(), filename=main_file).parse()

            with self.assertRaises(ModuleVerificationError) as ctx:
                resolver.resolve(ast)
            self.assertIn("failed compilation check", str(ctx.exception))
            self.assertFalse(os.path.isfile(os.path.join(broken_mod, ".module_verified")))

    def test_expanded_math_functions(self):
        # Verify expanded Math module with trigonometry, exponential, rounding, and number theory
        code = """
import Math;

fn main() {
    let fl: f64 = floor(5.7);
    let ce: f64 = ceil(5.2);
    let rd: f64 = round(5.5);
    let s: f64 = sin(0.0);
    let c: f64 = cos(0.0);
    let t: f64 = tan(0.0);
    let e: f64 = exp(0.0);
    let l: f64 = ln(1.0);
    let cb: f64 = cbrt(27.0);
    let prime_check: bool = is_prime(29);
    let next_p: i64 = next_prime(29);
    let comb: i64 = nCr(5, 2);
    let perm: i64 = nPr(5, 2);
    let sqrt2_c: f64 = Math.SQRT2;

    println(fl);
}
"""
        c_code = self.compiler.compile_source_to_c(code, filename="test_math_expanded.arx")
        self.assertIn("sin", c_code)
        self.assertIn("cos", c_code)
        self.assertIn("exp", c_code)
        self.assertIn("ln", c_code)
        self.assertIn("cbrt", c_code)
        self.assertIn("nCr", c_code)
        self.assertIn("is_prime", c_code)

    def test_parser_parses_inbuilt_module_import(self):
        code = "import Math;\nfn main() { return; }\n"
        lexer = Lexer(code, "<test>")
        tokens = lexer.tokenize()
        parser = Parser(tokens, code.splitlines(), filename="<test>")
        ast = parser.parse()
        self.assertTrue(any(isinstance(d, ImportNode) and d.module_name == "Math" and not d.is_user_file for d in ast.declarations))

    def test_parser_parses_user_file_import(self):
        code = 'import "./helper.arx";\nfn main() { return; }\n'
        lexer = Lexer(code, "<test>")
        tokens = lexer.tokenize()
        parser = Parser(tokens, code.splitlines(), filename="<test>")
        ast = parser.parse()
        self.assertTrue(any(isinstance(d, ImportNode) and d.file_path == "./helper.arx" and d.is_user_file for d in ast.declarations))

    def test_parser_parses_selective_import(self):
        code = 'import { abs, sqrt } from Math;\nimport { my_func } from "./utils.arx";\nfn main() { return; }\n'
        lexer = Lexer(code, "<test>")
        tokens = lexer.tokenize()
        parser = Parser(tokens, code.splitlines(), filename="<test>")
        ast = parser.parse()
        import_nodes = [d for d in ast.declarations if isinstance(d, ImportNode)]
        self.assertEqual(len(import_nodes), 2)
        self.assertEqual(import_nodes[0].symbols, ["abs", "sqrt"])
        self.assertEqual(import_nodes[0].module_name, "Math")
        self.assertFalse(import_nodes[0].is_user_file)

        self.assertEqual(import_nodes[1].symbols, ["my_func"])
        self.assertEqual(import_nodes[1].file_path, "./utils.arx")
        self.assertTrue(import_nodes[1].is_user_file)

    def test_inbuilt_module_strict_case_sensitivity(self):
        # 'Math' is an inbuilt module in modules/Math/
        code_lower = "import math;\nfn main() { return; }\n"
        with self.assertRaises(ModuleCaseError) as ctx:
            self.compiler.compile_source_to_c(code_lower, filename="test_case.arx")
        self.assertIn("case mismatch", str(ctx.exception))
        self.assertIn("strictly case-sensitive", str(ctx.exception))

    def test_missing_inbuilt_module_error(self):
        code = "import NonExistentModuleXYZ999;\nfn main() { return; }\n"
        with self.assertRaises(ModuleNotFoundError) as ctx:
            self.compiler.compile_source_to_c(code, filename="test_missing.arx")
        self.assertIn("Inbuilt module 'NonExistentModuleXYZ999' could not be found", str(ctx.exception))

    def test_missing_user_file_error(self):
        code = 'import "./non_existent_user_file.arx";\nfn main() { return; }\n'
        with self.assertRaises(ModuleNotFoundError) as ctx:
            self.compiler.compile_source_to_c(code, filename="test_missing_file.arx")
        self.assertIn("User source file", str(ctx.exception))

    def test_user_file_multi_file_compilation(self):
        # User creates helper.arx and imports it from main.arx
        with tempfile.TemporaryDirectory() as tmpdir:
            helper_path = os.path.join(tmpdir, "helper.arx")
            main_path = os.path.join(tmpdir, "main.arx")

            with open(helper_path, "w", encoding="utf-8") as f:
                f.write("""
pub fn calculate_bonus(salary: f64, rating: f64) -> f64 {
    return salary * (rating / 100.0);
}
""")

            with open(main_path, "w", encoding="utf-8") as f:
                f.write("""
import "./helper.arx";

fn main() {
    let bonus: f64 = calculate_bonus(50000.0, 15.0);
    println(bonus);
}
""")

            with open(main_path, "r", encoding="utf-8") as f:
                c_code = self.compiler.compile_source_to_c(f.read(), filename=main_path)
            self.assertIn("calculate_bonus", c_code)

    def test_selective_symbol_import_user_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            utils_path = os.path.join(tmpdir, "utils.arx")
            main_path = os.path.join(tmpdir, "main.arx")

            with open(utils_path, "w", encoding="utf-8") as f:
                f.write("""
pub fn allowed_fn() -> i64 { return 100; }
pub fn hidden_fn() -> i64 { return 200; }
""")

            with open(main_path, "w", encoding="utf-8") as f:
                f.write("""
import { allowed_fn } from "./utils.arx";

fn main() {
    let x: i64 = allowed_fn();
    println(x);
}
""")

            with open(main_path, "r", encoding="utf-8") as f:
                c_code = self.compiler.compile_source_to_c(f.read(), filename=main_path)
            self.assertIn("allowed_fn", c_code)
            self.assertNotIn("hidden_fn", c_code)

    def test_selective_symbol_import_missing_symbol_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            utils_path = os.path.join(tmpdir, "utils.arx")
            main_path = os.path.join(tmpdir, "main.arx")

            with open(utils_path, "w", encoding="utf-8") as f:
                f.write("pub fn fn_a() -> i64 { return 1; }\n")

            with open(main_path, "w", encoding="utf-8") as f:
                f.write('import { fn_missing } from "./utils.arx";\nfn main() { return; }\n')

            with open(main_path, "r", encoding="utf-8") as f:
                source = f.read()
            with self.assertRaises(ModuleSymbolNotFoundError) as ctx:
                self.compiler.compile_source_to_c(source, filename=main_path)
            self.assertIn("fn_missing", str(ctx.exception))

    def test_circular_dependency_user_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_a = os.path.join(tmpdir, "file_a.arx")
            file_b = os.path.join(tmpdir, "file_b.arx")

            with open(file_a, "w", encoding="utf-8") as f:
                f.write('import "./file_b.arx";\npub fn a() -> i64 { return 1; }\n')

            with open(file_b, "w", encoding="utf-8") as f:
                f.write('import "./file_a.arx";\npub fn b() -> i64 { return 2; }\n')

            with open(file_a, "r", encoding="utf-8") as f:
                source = f.read()
            with self.assertRaises(ModuleCircularError) as ctx:
                self.compiler.compile_source_to_c(source, filename=file_a)
            self.assertIn("Circular file dependency detected", str(ctx.exception))

    def test_full_native_execution_multi_file_and_inbuilt_module(self):
        gcc_path = shutil.which("gcc") or shutil.which("gcc.exe")
        if not gcc_path:
            self.skipTest("GCC is not available on PATH for native execution test")

        with tempfile.TemporaryDirectory() as tmpdir:
            user_math = os.path.join(tmpdir, "custom_math.arx")
            main_path = os.path.join(tmpdir, "main.arx")
            out_bin = os.path.join(tmpdir, "main.exe")

            # 1. User file custom_math.arx
            with open(user_math, "w", encoding="utf-8") as f:
                f.write("""
pub fn triple(x: f64) -> f64 {
    return x * 3.0;
}
""")

            # 2. Main program importing BOTH inbuilt module Math AND user file custom_math.arx
            with open(main_path, "w", encoding="utf-8") as f:
                f.write("""
import Math;
import "./custom_math.arx";

fn main() {
    // Call inbuilt Math module functions
    let s: f64 = Math.sqrt(144.0);
    let a: f64 = abs(-10.0);

    // Call user file function
    let t: f64 = triple(s);

    if s != 12.0 {
        println("sqrt failed");
        return;
    }
    if a != 10.0 {
        println("abs failed");
        return;
    }
    if t != 36.0 {
        println("triple failed");
        return;
    }
    println("MULTI FILE AND MODULE COEXISTENCE SUCCESS");
}
""")

            self.compiler.compile_file(main_path, output_binary_path=out_bin)
            self.assertTrue(os.path.exists(out_bin))

            import subprocess
            proc = subprocess.run([out_bin], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, f"Execution failed: {proc.stderr}")
            self.assertIn("MULTI FILE AND MODULE COEXISTENCE SUCCESS", proc.stdout)

    def test_selective_import_transitive_dependencies(self):
        """
        Validates that when a function is selectively imported, its internal helper functions
        are automatically pulled in via transitive dependency resolution, while unrelated functions
        and any 'fn main()' from the imported file are excluded.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            sorter_path = os.path.join(tmpdir, "sorter.arx")
            main_path = os.path.join(tmpdir, "main.arx")
            out_bin = os.path.join(tmpdir, "main.exe")

            with open(sorter_path, "w", encoding="utf-8") as f:
                f.write("""
fn helper_add(a: i64, b: i64) -> i64 => a + b;

pub fn calculate_sum(val: i64) -> i64 {
    return helper_add(val, 10);
}

pub fn unneeded_func() -> i64 {
    return 999;
}

fn main() {
    println("Should not execute");
}
""")

            with open(main_path, "w", encoding="utf-8") as f:
                f.write("""
import { calculate_sum } from "./sorter.arx";

fn main() {
    let res = calculate_sum(40);
    if res == 50 {
        println("TRANSITIVE DEPENDENCY IMPORT SUCCESS");
    }
}
""")

            with open(main_path, "r", encoding="utf-8") as f:
                c_code = self.compiler.compile_source_to_c(f.read(), filename=main_path)
            self.assertIn("calculate_sum", c_code)
            self.assertIn("helper_add", c_code)
            self.assertNotIn("unneeded_func", c_code)

            self.compiler.compile_file(main_path, output_binary_path=out_bin)
            self.assertTrue(os.path.exists(out_bin))

            import subprocess
            proc = subprocess.run([out_bin], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, f"Execution failed: {proc.stderr}")
            self.assertIn("TRANSITIVE DEPENDENCY IMPORT SUCCESS", proc.stdout)


if __name__ == "__main__":
    unittest.main()

