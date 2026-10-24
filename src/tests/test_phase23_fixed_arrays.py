"""
Aerix Compiler (arxc) — Phase 23 Test Suite: Fixed-Size Stack Arrays ([T; N])
Verifies compile-time stack-allocated arrays for real-time systems, games, and embedded firmware.
Includes explicit array literals, repeat syntax [val; N], bracket indexing, compound assignment,
compile-time .len properties, collection iteration, and C ABI pointer parameter passing.
"""

import os
import unittest
import tempfile
import subprocess
from src.driver import AerixCompiler


class TestPhase23FixedArrays(unittest.TestCase):
    def setUp(self):
        self.compiler = AerixCompiler()

    def test_fixed_array_explicit_literal_and_indexing(self):
        """Validates fixed array declaration, explicit list literal, and index reading."""
        code = """
        fn main() {
            let sensor_pins: [i32; 4] = [2, 4, 12, 14]
            println(sensor_pins[0])
            println(sensor_pins[1])
            println(sensor_pins[2])
            println(sensor_pins[3])
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "test.arx")
            exe = os.path.join(tmpdir, "test.exe")
            with open(src, "w", encoding="utf-8") as f:
                f.write(code)
            out_exe = self.compiler.compile_file(src, output_binary_path=exe)
            self.assertTrue(os.path.exists(out_exe))
            res = subprocess.run([out_exe], capture_output=True, text=True, check=True)
            self.assertEqual(res.returncode, 0)
            lines = res.stdout.strip().splitlines()
            self.assertEqual(lines, ["2", "4", "12", "14"])

    def test_fixed_array_mutation_and_compound_assignment(self):
        """Validates element mutation and compound arithmetic assignments on stack arrays."""
        code = """
        fn main() {
            mut motor_pwm: [i64; 3] = [1000, 1200, 1400]
            motor_pwm[0] = 1100
            motor_pwm[1] += 50
            motor_pwm[2] -= 100
            println(motor_pwm[0])
            println(motor_pwm[1])
            println(motor_pwm[2])
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "test.arx")
            exe = os.path.join(tmpdir, "test.exe")
            with open(src, "w", encoding="utf-8") as f:
                f.write(code)
            out_exe = self.compiler.compile_file(src, output_binary_path=exe)
            self.assertTrue(os.path.exists(out_exe))
            res = subprocess.run([out_exe], capture_output=True, text=True, check=True)
            self.assertEqual(res.returncode, 0)
            lines = res.stdout.strip().splitlines()
            self.assertEqual(lines, ["1100", "1250", "1300"])

    def test_fixed_array_repeat_syntax(self):
        """Validates uniform repeat initialization syntax: [value; count]."""
        code = """
        fn main() {
            let zeroes: [i64; 5] = [0; 5]
            println(zeroes[0])
            println(zeroes[4])

            mut weights: [f64; 3] = [1.5; 3]
            println(weights[0])
            weights[1] = 3.25
            println(weights[1])
            println(weights[2])
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "test.arx")
            exe = os.path.join(tmpdir, "test.exe")
            with open(src, "w", encoding="utf-8") as f:
                f.write(code)
            out_exe = self.compiler.compile_file(src, output_binary_path=exe)
            self.assertTrue(os.path.exists(out_exe))
            res = subprocess.run([out_exe], capture_output=True, text=True, check=True)
            self.assertEqual(res.returncode, 0)
            lines = res.stdout.strip().splitlines()
            self.assertEqual(lines, ["0", "0", "1.5", "3.25", "1.5"])

    def test_fixed_array_len_property(self):
        """Validates that .len on fixed arrays compiles to a zero-cost compile-time constant."""
        code = """
        fn main() {
            let pins: [i32; 4] = [2, 4, 12, 14]
            println(pins.len)

            let buffer: [u8; 16] = [0; 16]
            println(buffer.len)
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "test.arx")
            exe = os.path.join(tmpdir, "test.exe")
            with open(src, "w", encoding="utf-8") as f:
                f.write(code)
            out_exe = self.compiler.compile_file(src, output_binary_path=exe)
            self.assertTrue(os.path.exists(out_exe))
            res = subprocess.run([out_exe], capture_output=True, text=True, check=True)
            self.assertEqual(res.returncode, 0)
            lines = res.stdout.strip().splitlines()
            self.assertEqual(lines, ["4", "16"])

    def test_fixed_array_for_loop_iteration(self):
        """Validates that 'for item in array' operates directly on stack arrays with 0 allocations."""
        code = """
        fn main() {
            let data: [i64; 4] = [10, 20, 30, 40]
            mut sum: i64 = 0
            for val in data {
                sum += val
            }
            println(sum)
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "test.arx")
            exe = os.path.join(tmpdir, "test.exe")
            with open(src, "w", encoding="utf-8") as f:
                f.write(code)
            out_exe = self.compiler.compile_file(src, output_binary_path=exe)
            self.assertTrue(os.path.exists(out_exe))
            res = subprocess.run([out_exe], capture_output=True, text=True, check=True)
            self.assertEqual(res.returncode, 0)
            lines = res.stdout.strip().splitlines()
            self.assertEqual(lines, ["100"])

    def test_fixed_array_function_parameter(self):
        """Validates passing fixed stack arrays to functions as C ABI pointers."""
        code = """
        fn dot_product_3d(a: [f64; 3], b: [f64; 3]) -> f64 {
            return (a[0] * b[0]) + (a[1] * b[1]) + (a[2] * b[2])
        }

        fn main() {
            let v1: [f64; 3] = [1.0, 2.0, 3.0]
            let v2: [f64; 3] = [4.0, 5.0, 6.0]
            let res = dot_product_3d(v1, v2)
            println(res)
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "test.arx")
            exe = os.path.join(tmpdir, "test.exe")
            with open(src, "w", encoding="utf-8") as f:
                f.write(code)
            out_exe = self.compiler.compile_file(src, output_binary_path=exe)
            self.assertTrue(os.path.exists(out_exe))
            res = subprocess.run([out_exe], capture_output=True, text=True, check=True)
            self.assertEqual(res.returncode, 0)
            lines = res.stdout.strip().splitlines()
            self.assertEqual(lines, ["32"])

    def test_fixed_array_uninitialized_zero_fill(self):
        """Validates that uninitialized fixed array declarations are safely zero-filled."""
        code = """
        fn main() {
            let arr: [i64; 3]
            println(arr[0])
            println(arr[1])
            println(arr[2])
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "test.arx")
            exe = os.path.join(tmpdir, "test.exe")
            with open(src, "w", encoding="utf-8") as f:
                f.write(code)
            out_exe = self.compiler.compile_file(src, output_binary_path=exe)
            self.assertTrue(os.path.exists(out_exe))
            res = subprocess.run([out_exe], capture_output=True, text=True, check=True)
            self.assertEqual(res.returncode, 0)
            lines = res.stdout.strip().splitlines()
            self.assertEqual(lines, ["0", "0", "0"])

    def test_fixed_array_semantic_type_mismatch(self):
        """Validates that semantic analysis rejects array literals with mismatched element types."""
        code = """
        fn main() {
            let arr: [i32; 2] = ["hello", 42]
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "test.arx")
            exe = os.path.join(tmpdir, "test.exe")
            with open(src, "w", encoding="utf-8") as f:
                f.write(code)
            with self.assertRaises(Exception):
                self.compiler.compile_file(src, output_binary_path=exe)


if __name__ == "__main__":
    unittest.main()
