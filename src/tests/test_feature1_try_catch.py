"""
Unit & Integration Tests for Feature 1: try / catch / (optional) finally & throw.
"""

import unittest
import subprocess
import os
import sys
import tempfile


class TestFeature1TryCatch(unittest.TestCase):
    def setUp(self):
        self.compiler_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "arxc.py"))

    def compile_and_run(self, arx_code: str) -> subprocess.CompletedProcess:
        with tempfile.NamedTemporaryFile(suffix=".arx", delete=False, mode="w", encoding="utf-8") as f:
            f.write(arx_code)
            src_path = f.name
        exe_path = src_path.replace(".arx", ".exe")
        try:
            # Compile
            comp_res = subprocess.run(
                [sys.executable, self.compiler_path, src_path, "-o", exe_path],
                capture_output=True,
                text=True
            )
            self.assertEqual(comp_res.returncode, 0, f"Compilation failed:\n{comp_res.stderr}\n{comp_res.stdout}")

            # Run
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

    def test_try_catch_basic(self):
        code = """
        fn main() {
            try {
                println("inside try");
                throw "Something went wrong!";
                println("should not reach here");
            } catch err {
                println("Caught error: " + err);
            }
            println("after try-catch");
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        output = res.stdout.strip().replace("\r\n", "\n")
        self.assertIn("inside try", output)
        self.assertIn("Caught error: Something went wrong!", output)
        self.assertNotIn("should not reach here", output)
        self.assertIn("after try-catch", output)

    def test_try_catch_no_throw(self):
        code = """
        fn main() {
            try {
                println("step 1");
                println("step 2");
            } catch err {
                println("should not catch");
            }
            println("done");
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        output = res.stdout.strip().replace("\r\n", "\n")
        self.assertIn("step 1", output)
        self.assertIn("step 2", output)
        self.assertNotIn("should not catch", output)
        self.assertIn("done", output)

    def test_try_catch_finally(self):
        code = """
        fn main() {
            try {
                println("in try");
                throw "Network timeout";
            } catch e {
                println("caught: " + e);
            } finally {
                println("finally block executed");
            }
            println("normal exit");
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        output = res.stdout.strip().replace("\r\n", "\n")
        self.assertIn("in try", output)
        self.assertIn("caught: Network timeout", output)
        self.assertIn("finally block executed", output)
        self.assertIn("normal exit", output)

    def test_try_finally_without_catch(self):
        code = """
        fn test_helper() {
            try {
                println("helper try");
                throw "nested error";
            } finally {
                println("helper finally");
            }
        }

        fn main() {
            try {
                test_helper();
            } catch err {
                println("outer caught: " + err);
            }
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        output = res.stdout.strip().replace("\r\n", "\n")
        self.assertIn("helper try", output)
        self.assertIn("helper finally", output)
        self.assertIn("outer caught: nested error", output)

    def test_nested_try_catch(self):
        code = """
        fn main() {
            try {
                println("level 1");
                try {
                    println("level 2");
                    throw "inner fail";
                } catch inner_e {
                    println("inner caught: " + inner_e);
                }
                println("level 1 resumed");
            } catch outer_e {
                println("outer caught");
            }
            println("all done");
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        output = res.stdout.strip().replace("\r\n", "\n")
        self.assertIn("level 1", output)
        self.assertIn("level 2", output)
        self.assertIn("inner caught: inner fail", output)
        self.assertIn("level 1 resumed", output)
        self.assertNotIn("outer caught", output)
        self.assertIn("all done", output)


if __name__ == "__main__":
    unittest.main()
