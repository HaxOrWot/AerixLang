"""
Unit & Integration Tests for Feature 3: Slices & Range Views (&[T], &mut [T], arr[start..end]).
"""

import unittest
import subprocess
import os
import sys
import tempfile


class TestFeature3Slices(unittest.TestCase):
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

    def test_basic_slice_creation_and_indexing(self):
        code = """
        fn main() {
            let arr: [i64; 6] = [10, 20, 30, 40, 50, 60];
            let s: &[i64] = arr[1..4];
            println("len=" + s.len);
            println("s0=" + s[0]);
            println("s1=" + s[1]);
            println("s2=" + s[2]);
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        output = res.stdout.strip().replace("\r\n", "\n")
        self.assertIn("len=3", output)
        self.assertIn("s0=20", output)
        self.assertIn("s1=30", output)
        self.assertIn("s2=40", output)

    def test_inclusive_range_slice(self):
        code = """
        fn main() {
            let arr: [i64; 5] = [100, 200, 300, 400, 500];
            let s = arr[1..=3];
            println("len=" + s.len);
            println("s2=" + s[2]);
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        output = res.stdout.strip().replace("\r\n", "\n")
        self.assertIn("len=3", output)
        self.assertIn("s2=400", output)

    def test_mutable_slice_modifies_underlying_array(self):
        code = """
        fn main() {
            let mut arr: [i64; 5] = [1, 2, 3, 4, 5];
            let s: &mut [i64] = arr[1..4];
            s[1] = 999;
            println("arr2=" + arr[2]);
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        output = res.stdout.strip().replace("\r\n", "\n")
        # s[1] corresponds to arr[2]! Zero-copy view check:
        self.assertIn("arr2=999", output)

    def test_slice_passed_to_function(self):
        code = """
        fn sum_slice(s: &[i64]) -> i64 {
            let mut total: i64 = 0;
            for x in s {
                total += x;
            }
            return total;
        }

        fn main() {
            let arr: [i64; 5] = [10, 20, 30, 40, 50];
            let total = sum_slice(arr[1..4]);
            println("total=" + total);
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        output = res.stdout.strip().replace("\r\n", "\n")
        # 20 + 30 + 40 = 90
        self.assertIn("total=90", output)

    def test_sub_slice_of_slice(self):
        code = """
        fn main() {
            let arr: [i64; 7] = [10, 20, 30, 40, 50, 60, 70];
            let s1 = arr[1..6];     // [20, 30, 40, 50, 60], len=5
            let s2 = s1[1..4];      // [30, 40, 50], len=3
            println("s2_len=" + s2.len);
            println("s2_0=" + s2[0]);
            println("s2_2=" + s2[2]);
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        output = res.stdout.strip().replace("\r\n", "\n")
        self.assertIn("s2_len=3", output)
        self.assertIn("s2_0=30", output)
        self.assertIn("s2_2=50", output)

    def test_slice_enumerate_iteration(self):
        code = """
        fn main() {
            let arr: [i64; 4] = [11, 22, 33, 44];
            let s = arr[1..3];
            for (idx, val) in s.enumerate() {
                println("idx=" + idx + ", val=" + val);
            }
        }
        """
        res = self.compile_and_run(code)
        self.assertEqual(res.returncode, 0)
        output = res.stdout.strip().replace("\r\n", "\n")
        self.assertIn("idx=0, val=22", output)
        self.assertIn("idx=1, val=33", output)


if __name__ == "__main__":
    unittest.main()
