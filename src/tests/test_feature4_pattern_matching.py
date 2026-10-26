"""
Unit & Integration Tests for Feature 4: Advanced Pattern Matching
(Ranges 200..=299, OR-patterns, Tuples, Wildcards _, if let, guard let).
"""

import unittest
import subprocess
import os
import sys
import tempfile


class TestFeature4PatternMatching(unittest.TestCase):
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

    def test_range_pattern_matching(self):
        code = """
        fn classify_status(code: i64) -> str {
            match code {
                200..=299 => return "Success",
                300..=399 => return "Redirect",
                400..=499 => return "Client Error",
                500..=599 => return "Server Error",
                _ => return "Unknown"
            }
        }

        fn main() {
            println(classify_status(200));
            println(classify_status(204));
            println(classify_status(404));
            println(classify_status(503));
            println(classify_status(999));
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        output = res.stdout.strip().replace("\r\n", "\n")
        self.assertIn("Success", output)
        self.assertIn("Client Error", output)
        self.assertIn("Server Error", output)
        self.assertIn("Unknown", output)

    def test_or_alternatives_pattern(self):
        code = """
        fn describe(n: i64) -> str {
            match n {
                1 | 2 | 3 => return "small",
                4 | 5 => return "medium",
                _ => return "other"
            }
        }

        fn main() {
            println(describe(2));
            println(describe(5));
            println(describe(10));
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        output = res.stdout.strip().replace("\r\n", "\n")
        self.assertIn("small", output)
        self.assertIn("medium", output)
        self.assertIn("other", output)

    def test_guard_condition_in_match(self):
        code = """
        fn test_guard(n: i64) {
            match n {
                x if x > 100 => println("huge: " + x),
                x if x < 0 => println("negative: " + x),
                _ => println("normal")
            }
        }

        fn main() {
            test_guard(150);
            test_guard(-5);
            test_guard(42);
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        output = res.stdout.strip().replace("\r\n", "\n")
        self.assertIn("huge: 150", output)
        self.assertIn("negative: -5", output)
        self.assertIn("normal", output)

    def test_tuple_patterns(self):
        code = """
        fn test_point(p: (i64, i64)) {
            match p {
                (0, 0) => println("origin"),
                (0, _) => println("on y-axis"),
                (_, 0) => println("on x-axis"),
                (x, y) => println("point: " + x + ", " + y)
            }
        }

        fn main() {
            test_point((0, 0));
            test_point((0, 5));
            test_point((7, 0));
            test_point((3, 4));
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        output = res.stdout.strip().replace("\r\n", "\n")
        self.assertIn("origin", output)
        self.assertIn("on y-axis", output)
        self.assertIn("on x-axis", output)
        self.assertIn("point: 3, 4", output)

    def test_if_let(self):
        code = """
        fn main() {
            let status = 200;
            if let 200 = status {
                println("status is OK");
            } else {
                println("not ok");
            }

            let other = 404;
            if let 200 = other {
                println("status is OK");
            } else {
                println("status is not 200");
            }
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        output = res.stdout.strip().replace("\r\n", "\n")
        self.assertIn("status is OK", output)
        self.assertIn("status is not 200", output)

    def test_guard_let(self):
        code = """
        fn check_auth(token: i64) -> str {
            guard let 999 = token else {
                return "Unauthorized";
            }
            return "Welcome Admin";
        }

        fn main() {
            println(check_auth(999));
            println(check_auth(123));
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        output = res.stdout.strip().replace("\r\n", "\n")
        self.assertIn("Welcome Admin", output)
        self.assertIn("Unauthorized", output)


if __name__ == "__main__":
    unittest.main()
