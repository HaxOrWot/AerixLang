"""
Unit & Integration Tests for Feature 2: Loop Ergonomics (break, continue, Labeled Loops, .enumerate()).
"""

import unittest
import subprocess
import os
import sys
import tempfile


class TestFeature2LoopErgonomics(unittest.TestCase):
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

    def test_break_and_continue_in_for(self):
        code = """
        fn main() {
            let mut sum: i64 = 0;
            for i in 0..10 {
                if i % 2 == 1 {
                    continue;
                }
                if i > 6 {
                    break;
                }
                sum += i;
            }
            println("sum=" + sum);
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        # Even numbers <= 6: 0 + 2 + 4 + 6 = 12
        self.assertIn("sum=12", res.stdout.strip())

    def test_while_break_continue(self):
        code = """
        fn main() {
            let mut i: i64 = 0;
            let mut count: i64 = 0;
            while i < 10 {
                i += 1;
                if i == 3 {
                    continue;
                }
                if i == 7 {
                    break;
                }
                count += 1;
            }
            println("count=" + count);
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        # i goes 1, 2 (skip 3), 4, 5, 6 (break at 7) -> 5 iterations counted
        self.assertIn("count=5", res.stdout.strip())

    def test_infinite_loop_construct(self):
        code = """
        fn main() {
            let mut counter: i64 = 0;
            loop {
                counter += 1;
                if counter >= 5 {
                    break;
                }
            }
            println("counter=" + counter);
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        self.assertIn("counter=5", res.stdout.strip())

    def test_labeled_loop_break(self):
        code = """
        fn main() {
            let mut found: i64 = 0;
            'outer: for i in 0..5 {
                for j in 0..5 {
                    if i == 2 && j == 3 {
                        found = i * 10 + j;
                        break 'outer;
                    }
                }
            }
            println("found=" + found);
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        self.assertIn("found=23", res.stdout.strip())

    def test_labeled_loop_continue(self):
        code = """
        fn main() {
            let mut passes: i64 = 0;
            outer: for i in 0..4 {
                for j in 0..4 {
                    if j == 2 {
                        continue outer;
                    }
                    passes += 1;
                }
            }
            println("passes=" + passes);
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        # Each outer iteration executes for j=0 and j=1 (2 times), then skips to next i
        # 4 outer iterations * 2 = 8
        self.assertIn("passes=8", res.stdout.strip())

    def test_enumerate_fixed_array(self):
        code = """
        fn main() {
            let arr: [i64; 3] = [10, 20, 30];
            for (idx, val) in arr.enumerate() {
                println("item " + idx + " is " + val);
            }
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        output = res.stdout.strip().replace("\r\n", "\n")
        self.assertIn("item 0 is 10", output)
        self.assertIn("item 1 is 20", output)
        self.assertIn("item 2 is 30", output)

    def test_enumerate_range(self):
        code = """
        fn main() {
            for (idx, val) in 5..8 {
                println("idx=" + idx + ", val=" + val);
            }
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        output = res.stdout.strip().replace("\r\n", "\n")
        self.assertIn("idx=0, val=5", output)
        self.assertIn("idx=1, val=6", output)
        self.assertIn("idx=2, val=7", output)


if __name__ == "__main__":
    unittest.main()
