"""
Unit tests for Feature 6: Default & Named Function Arguments.
"""

import unittest
import os
import sys
import subprocess
import tempfile
from src.frontend.lexer import Lexer
from src.frontend.parser import Parser
from src.middle.semantic import SemanticAnalyzer, SemanticError

class TestFeature6DefaultNamedArgs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compiler_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "arxc.py"))

    def compile_and_run(self, arx_code: str) -> subprocess.CompletedProcess:
        with tempfile.NamedTemporaryFile(suffix=".arx", delete=False, mode="w", encoding="utf-8") as f:
            f.write(arx_code)
            src_path = f.name
        exe_path = src_path.replace(".arx", ".exe")
        try:
            comp_res = subprocess.run(
                [sys.executable, self.compiler_path, src_path, "-o", exe_path],
                capture_output=True,
                text=True
            )
            self.assertEqual(comp_res.returncode, 0, f"Compilation failed:\n{comp_res.stderr}\n{comp_res.stdout}")

            run_res = subprocess.run([exe_path], capture_output=True, text=True)
            return run_res
        finally:
            if os.path.exists(src_path):
                os.remove(src_path)
            if os.path.exists(exe_path):
                try:
                    os.remove(exe_path)
                except OSError:
                    pass

    def test_parser_default_param(self):
        code = "fn greet(name: str = \"World\", times: i64 = 1) -> void { }"
        tokens = Lexer(code).tokenize()
        ast = Parser(tokens).parse()
        fn = ast.declarations[0]
        self.assertEqual(len(fn.params), 2)
        self.assertEqual(fn.params[0].name, "name")
        self.assertIsNotNone(fn.params[0].default_val)
        self.assertEqual(fn.params[0].default_val.value, "World")
        self.assertEqual(fn.params[1].name, "times")
        self.assertIsNotNone(fn.params[1].default_val)
        self.assertEqual(fn.params[1].default_val.value, 1)

    def test_parser_named_arg_call(self):
        code = "fn main() -> i64 { greet(times = 5, name = \"Alice\"); return 0; }"
        tokens = Lexer(code).tokenize()
        ast = Parser(tokens).parse()
        fn = ast.declarations[0]
        call_stmt = fn.body.statements[0]
        call = call_stmt.expr
        self.assertEqual(len(call.args), 2)
        self.assertEqual(call.args[0].name, "times")
        self.assertEqual(call.args[0].value.value, 5)
        self.assertEqual(call.args[1].name, "name")
        self.assertEqual(call.args[1].value.value, "Alice")

    def test_e2e_default_and_named_args(self):
        code = '''
fn add_nums(a: i64, b: i64 = 10, c: i64 = 100) -> i64 {
    return a + b + c;
}

fn main() -> i64 {
    // 1. All positional
    let r1 = add_nums(1, 2, 3);
    println("r1: {r1}");

    // 2. Using defaults for b and c
    let r2 = add_nums(5);
    println("r2: {r2}");

    // 3. Using default for c only
    let r3 = add_nums(5, 20);
    println("r3: {r3}");

    // 4. Named args out of order
    let r4 = add_nums(1, c = 50, b = 25);
    println("r4: {r4}");

    // 5. Named arg specifying only c (b uses default)
    let r5 = add_nums(7, c = 300);
    println("r5: {r5}");

    return 0;
}
'''
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        lines = res.stdout.strip().splitlines()
        self.assertEqual(lines[0], "r1: 6")      # 1 + 2 + 3
        self.assertEqual(lines[1], "r2: 115")    # 5 + 10 + 100
        self.assertEqual(lines[2], "r3: 125")    # 5 + 20 + 100
        self.assertEqual(lines[3], "r4: 76")     # 1 + 25 + 50
        self.assertEqual(lines[4], "r5: 317")    # 7 + 10 + 300

    def test_class_constructor_and_method_defaults(self):
        code = '''
class Window {
    pub title: str;
    pub width: i64;
    pub height: i64;

    init(title: str = "Aerix App", width: i64 = 800, height: i64 = 600) {
        self.title = title;
        self.width = width;
        self.height = height;
    }

    pub fn resize(w: i64 = 1920, h: i64 = 1080) -> void {
        self.width = w;
        self.height = h;
    }
}

fn main() -> i64 {
    let mut win1 = Window();
    println("win1: {win1.title} {win1.width}x{win1.height}");

    let win2 = Window("Custom", 1024, 768);
    println("win2: {win2.title} {win2.width}x{win2.height}");

    let win3 = Window(height = 400, title = "Named");
    println("win3: {win3.title} {win3.width}x{win3.height}");

    win1.resize(w = 1280);
    println("win1 resized: {win1.width}x{win1.height}");

    return 0;
}
'''
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        lines = res.stdout.strip().splitlines()
        self.assertEqual(lines[0], "win1: Aerix App 800x600")
        self.assertEqual(lines[1], "win2: Custom 1024x768")
        self.assertEqual(lines[2], "win3: Named 800x400")
        self.assertEqual(lines[3], "win1 resized: 1280x1080")

    def test_semantic_missing_required_arg(self):
        code = '''
fn add_nums(a: i64, b: i64 = 10) -> i64 {
    return a + b;
}
fn main() -> i64 {
    let x = add_nums();
    return x;
}
'''
        tokens = Lexer(code).tokenize()
        ast = Parser(tokens).parse()
        sa = SemanticAnalyzer()
        with self.assertRaises(SemanticError) as ctx:
            sa.analyze(ast)
        self.assertIn("Missing required argument 'a'", str(ctx.exception))

    def test_semantic_unknown_named_arg(self):
        code = '''
fn add_nums(a: i64, b: i64 = 10) -> i64 {
    return a + b;
}
fn main() -> i64 {
    let x = add_nums(1, foo = 20);
    return x;
}
'''
        tokens = Lexer(code).tokenize()
        ast = Parser(tokens).parse()
        sa = SemanticAnalyzer()
        with self.assertRaises(SemanticError) as ctx:
            sa.analyze(ast)
        self.assertIn("Function 'add_nums' has no parameter named 'foo'", str(ctx.exception))

if __name__ == '__main__':
    unittest.main()
