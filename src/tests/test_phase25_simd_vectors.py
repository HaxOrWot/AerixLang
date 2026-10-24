"""
Aerix Compiler (arxc) — Phase 25 Test Suite: First-Class SIMD Arithmetic Operators & Vector Math
Verifies:
1. 128-bit SIMD vector types: f32x4 and f64x2.
2. Direct constructor and splat syntax: f32x4(x, y, z, w) and f32x4(scalar).
3. Lane access via .x, .y, .z, .w properties and [i] indexing.
4. Native vector-vector and vector-scalar arithmetic (+, -, *, /).
5. Vector geometric intrinsics: dot(), cross(), length(), normalize(), min(), max().
6. Component mutation (v.x = ..., v[i] = ...).
7. Vector equality and inequality (==, !=).
8. Semantic diagnostics rejecting invalid lane counts, types, or cross() on f64x2.
"""

import os
import unittest
import tempfile
import subprocess
from src.driver import AerixCompiler
from src.middle.semantic import SemanticError
from src.frontend.diagnostics import DiagnosticBag


class TestPhase25SimdVectors(unittest.TestCase):
    def setUp(self):
        self.compiler = AerixCompiler()

    def test_f32x4_constructor_components_and_indexing(self):
        """Verifies f32x4 construction, .x/.y/.z/.w component access, and [i] indexing."""
        code = """
        fn main() {
            let v = f32x4(1.0, 2.0, 3.0, 4.0)
            println(v.x)
            println(v.y)
            println(v.z)
            println(v.w)
            println(v[0])
            println(v[1])
            println(v[2])
            println(v[3])
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
            self.assertEqual(lines, ["1", "2", "3", "4", "1", "2", "3", "4"])

    def test_f32x4_splat_and_f64x2(self):
        """Verifies splat initialization and f64x2 double-precision vector operations."""
        code = """
        fn main() {
            let s = f32x4(7.5)
            println(s.x)
            println(s.w)

            let d = f64x2(10.5, 20.5)
            println(d.x)
            println(d.y)
            println(d[0])
            println(d[1])

            let d_splat = f64x2(99.0)
            println(d_splat.x)
            println(d_splat.y)
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
            self.assertEqual(lines, ["7.5", "7.5", "10.5", "20.5", "10.5", "20.5", "99", "99"])

    def test_simd_arithmetic_operators(self):
        """Verifies +, -, *, / between vector operands and vector-scalar operations."""
        code = """
        fn main() {
            let a = f32x4(1.0, 2.0, 3.0, 4.0)
            let b = f32x4(10.0, 20.0, 30.0, 40.0)

            let sum = a + b
            println(sum.x)
            println(sum.w)

            let diff = b - a
            println(diff.x)
            println(diff.w)

            let scaled = a * 2.0
            println(scaled.x)
            println(scaled.w)

            let div = b / 2.0
            println(div.x)
            println(div.w)
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
            self.assertEqual(lines, ["11", "44", "9", "36", "2", "8", "5", "20"])

    def test_simd_geometric_intrinsics(self):
        """Verifies dot(), cross(), length(), normalize(), min(), max()."""
        code = """
        fn main() {
            let u = f32x4(1.0, 2.0, 3.0, 4.0)
            let v = f32x4(2.0, 2.0, 2.0, 2.0)
            let d = u.dot(v)
            println(d)

            let x_axis = f32x4(1.0, 0.0, 0.0, 0.0)
            let y_axis = f32x4(0.0, 1.0, 0.0, 0.0)
            let z_axis = x_axis.cross(y_axis)
            println(z_axis.x)
            println(z_axis.y)
            println(z_axis.z)

            let p = f32x4(3.0, 4.0, 0.0, 0.0)
            println(p.length())

            let norm = p.normalize()
            println(norm.x)
            println(norm.y)

            let m1 = f32x4(1.0, 10.0, 3.0, 8.0)
            let m2 = f32x4(5.0, 2.0, 7.0, 4.0)
            let minimums = m1.min(m2)
            println(minimums.x)
            println(minimums.y)

            let maximums = m1.max(m2)
            println(maximums.x)
            println(maximums.y)
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
            self.assertEqual(lines, ["20", "0", "0", "1", "5", "0.6", "0.8", "1", "2", "5", "10"])

    def test_simd_component_and_index_mutation(self):
        """Verifies mutable SIMD vectors allow in-place lane assignment."""
        code = """
        fn main() {
            mut pos = f32x4(0.0, 0.0, 0.0, 1.0)
            pos.x = 100.0
            pos.y = 200.0
            pos[2] = 300.0
            println(pos.x)
            println(pos.y)
            println(pos.z)
            println(pos.w)
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
            self.assertEqual(lines, ["100", "200", "300", "1"])

    def test_simd_equality_operators(self):
        """Verifies == and != operators on SIMD vectors."""
        code = """
        fn main() {
            let v1 = f32x4(1.0, 2.0, 3.0, 4.0)
            let v2 = f32x4(1.0, 2.0, 3.0, 4.0)
            let v3 = f32x4(1.0, 2.0, 3.0, 5.0)

            println(v1 == v2)
            println(v1 == v3)
            println(v1 != v3)
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
            self.assertEqual(lines, ["true", "false", "true"])

    def test_simd_semantic_errors(self):
        """Verifies semantic analyzer catches invalid SIMD constructor arity and unsupported ops."""
        # Test 1: Invalid constructor arity (e.g. 2 args for f32x4)
        code1 = """
        fn main() {
            let v = f32x4(1.0, 2.0)
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "test.arx")
            exe = os.path.join(tmpdir, "test.exe")
            with open(src, "w", encoding="utf-8") as f:
                f.write(code1)
            with self.assertRaises((SemanticError, DiagnosticBag)) as ctx:
                self.compiler.compile_file(src, output_binary_path=exe)
            self.assertIn("'f32x4' constructor expects 1 argument (splat) or 4 arguments", str(ctx.exception))

        # Test 2: .cross() on f64x2
        code2 = """
        fn main() {
            let v1 = f64x2(1.0, 2.0)
            let v2 = f64x2(3.0, 4.0)
            let c = v1.cross(v2)
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "test.arx")
            exe = os.path.join(tmpdir, "test.exe")
            with open(src, "w", encoding="utf-8") as f:
                f.write(code2)
            with self.assertRaises((SemanticError, DiagnosticBag)) as ctx:
                self.compiler.compile_file(src, output_binary_path=exe)
            self.assertIn("'cross()' is only supported on 'f32x4'", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
