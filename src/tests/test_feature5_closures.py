"""
Unit & Integration Tests for Feature 5: Closures & Lambdas (|x| expr, pipelines, .map).
"""

import unittest
import subprocess
import os
import sys
import tempfile


class TestFeature5Closures(unittest.TestCase):
    def setUp(self):
        self.compiler_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "arxc.py"))

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

    def test_lambda_variable_and_call(self):
        code = """
        fn main() {
            let double_fn = |x: i64| x * 2;
            let res = double_fn(21);
            println(res);
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.stdout.strip(), "42")

    def test_multi_param_lambda(self):
        code = """
        fn main() {
            let add_fn = |a: i64, b: i64| a + b;
            let res = add_fn(15, 27);
            println(res);
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.stdout.strip(), "42")

    def test_zero_param_lambda(self):
        code = """
        fn main() {
            let answer = || 42;
            println(answer());
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.stdout.strip(), "42")

    def test_lambda_block_body(self):
        code = """
        fn main() {
            let compute = |x: i64| -> i64 {
                let temp = x * 10;
                return temp + 2;
            };
            println(compute(4));
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.stdout.strip(), "42")

    def test_higher_order_function(self):
        code = """
        fn apply_twice(f: fn(i64) -> i64, val: i64) -> i64 {
            return f(f(val));
        }

        fn main() {
            let inc = |x: i64| x + 1;
            let res = apply_twice(inc, 40);
            println(res);
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.stdout.strip(), "42")

    def test_fixed_array_map(self):
        code = """
        fn main() {
            let arr: [i64; 3] = [1, 2, 3];
            let mapped = arr.map(|x: i64| x * 10);
            println(mapped[0]);
            println(mapped[1]);
            println(mapped[2]);
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.stdout.strip().splitlines(), ["10", "20", "30"])


if __name__ == "__main__":
    unittest.main()
