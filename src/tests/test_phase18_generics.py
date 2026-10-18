"""
Aerix Compiler (arxc) — Phase 18 Test Suite: First-Class Generics & Monomorphization
Validates compile-time template monomorphization for generic functions and classes.
Guarantees zero-cost abstractions, zero type erasure, and zero runtime vtable penalties in C99.
"""

import os
import unittest
import subprocess
import tempfile
from src.driver import AerixCompiler


class TestPhase18Generics(unittest.TestCase):
    def setUp(self):
        self.compiler = AerixCompiler()

    def test_generic_function_specialization(self):
        """Validates that generic functions are monomorphized into specialized C99 functions."""
        code = """
        fn identity<T>(x: T) -> T {
            return x;
        }

        fn main() {
            let a = identity<i64>(42);
            let b = identity<f64>(3.14);
            println(a);
            println(b);
        }
        """
        c_code = self.compiler.compile_source_to_c(code, "test_generic_fn.arx")
        self.assertIn("arx_identity_i64", c_code)
        self.assertIn("arx_identity_f64", c_code)

        # Native GCC compilation & execution
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "test.arx")
            exe = os.path.join(tmpdir, "test.exe")
            with open(src, "w", encoding="utf-8") as f:
                f.write(code)
            out_exe = self.compiler.compile_file(src, output_binary_path=exe)
            res = subprocess.run([out_exe], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            lines = res.stdout.strip().splitlines()
            self.assertEqual(lines[0], "42")
            self.assertTrue(lines[1].startswith("3.14"))

    def test_generic_class_single_param(self):
        """Validates generic class monomorphization with a single type parameter."""
        code = """
        class Box<T> {
            pub value: T

            init(val: T) {
                self.value = val
            }

            pub fn get() -> T {
                return self.value
            }
        }

        fn main() {
            let b1 = Box<i64>(100);
            let b2 = Box<str>("Aerix Systems");
            println(b1.get());
            println(b2.get());
        }
        """
        c_code = self.compiler.compile_source_to_c(code, "test_box.arx")
        self.assertIn("struct Arx_Box_i64 {", c_code)
        self.assertIn("struct Arx_Box_str {", c_code)

        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "test.arx")
            exe = os.path.join(tmpdir, "test.exe")
            with open(src, "w", encoding="utf-8") as f:
                f.write(code)
            out_exe = self.compiler.compile_file(src, output_binary_path=exe)
            res = subprocess.run([out_exe], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            lines = res.stdout.strip().splitlines()
            self.assertEqual(lines[0], "100")
            self.assertEqual(lines[1], "Aerix Systems")

    def test_generic_class_multi_params(self):
        """Validates generic class monomorphization with multiple type parameters."""
        code = """
        class Pair<K, V> {
            pub key: K
            pub val: V

            init(k: K, v: V) {
                self.key = k
                self.val = v
            }

            pub fn get_key() -> K {
                return self.key
            }

            pub fn get_val() -> V {
                return self.val
            }
        }

        fn main() {
            let p = Pair<str, i64>("CPU_UTILIZATION", 87);
            println(p.get_key());
            println(p.get_val());
        }
        """
        c_code = self.compiler.compile_source_to_c(code, "test_pair.arx")
        self.assertIn("struct Arx_Pair_str_i64 {", c_code)

        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "test.arx")
            exe = os.path.join(tmpdir, "test.exe")
            with open(src, "w", encoding="utf-8") as f:
                f.write(code)
            out_exe = self.compiler.compile_file(src, output_binary_path=exe)
            res = subprocess.run([out_exe], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            lines = res.stdout.strip().splitlines()
            self.assertEqual(lines[0], "CPU_UTILIZATION")
            self.assertEqual(lines[1], "87")

    def test_generic_container_mutation(self):
        """Validates mutating state on a monomorphized generic class instance."""
        code = """
        class Cell<T> {
            pub val: T

            init(initial: T) {
                self.val = initial
            }

            pub fn set(new_val: T) {
                self.val = new_val
            }

            pub fn get() -> T {
                return self.val
            }
        }

        fn main() {
            mut c = Cell<i64>(10);
            println(c.get());
            c.set(99);
            println(c.get());
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "test.arx")
            exe = os.path.join(tmpdir, "test.exe")
            with open(src, "w", encoding="utf-8") as f:
                f.write(code)
            out_exe = self.compiler.compile_file(src, output_binary_path=exe)
            res = subprocess.run([out_exe], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            lines = res.stdout.strip().splitlines()
            self.assertEqual(lines[0], "10")
            self.assertEqual(lines[1], "99")

    def test_generic_explicit_type_annotation(self):
        """Validates variable declaration with explicit generic type annotation."""
        code = """
        class Holder<T> {
            pub datum: T

            init(d: T) {
                self.datum = d
            }
        }

        fn main() {
            let h: Holder<i64> = Holder<i64>(777);
            println(h.datum);
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "test.arx")
            exe = os.path.join(tmpdir, "test.exe")
            with open(src, "w", encoding="utf-8") as f:
                f.write(code)
            out_exe = self.compiler.compile_file(src, output_binary_path=exe)
            res = subprocess.run([out_exe], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            self.assertEqual(res.stdout.strip(), "777")

    def test_uninstantiated_generic_template_causes_no_errors(self):
        """Validates that unused generic templates are excluded from C99 codegen."""
        code = """
        class UnusedContainer<T> {
            pub payload: T
        }

        fn unused_function<T>(x: T) -> T {
            return x;
        }

        fn main() {
            println("Active Only");
        }
        """
        c_code = self.compiler.compile_source_to_c(code, "test_unused.arx")
        self.assertNotIn("UnusedContainer", c_code)
        self.assertNotIn("unused_function", c_code)


if __name__ == "__main__":
    unittest.main()
