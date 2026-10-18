"""
Aerix Compiler — Unit Tests for Phase 11: Reactive Properties & Operator Overloading
"""

import os
import tempfile
import subprocess
import unittest
from src.driver import AerixCompiler


class TestPhase11PropertiesAndOperators(unittest.TestCase):
    def setUp(self):
        self.compiler = AerixCompiler()

    def test_property_getter_and_setter(self):
        code = """
        class Station {
            pub name: str
            priv raw_docks: i64

            init(name: str) {
                self.name = name
                self.raw_docks = 0
            }

            pub prop docks: i64 {
                get => self.raw_docks
                set(val) {
                    self.raw_docks = val
                }
            }
        }

        fn main() {
            mut s = Station("DeepSpace-9")
            s.docks = 12
            let count = s.docks
            println("Station {s.name} docks: {count}")
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            arx_file = os.path.join(tmpdir, "test_prop.arx")
            exe_file = os.path.join(tmpdir, "test_prop.exe")
            with open(arx_file, "w", encoding="utf-8") as f:
                f.write(code)

            out_exe = self.compiler.compile_file(arx_file, output_binary_path=exe_file)
            res = subprocess.run([out_exe], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
            self.assertEqual(res.stdout.strip(), "Station DeepSpace-9 docks: 12")

    def test_computed_read_only_property(self):
        code = """
        class Circle {
            pub radius: f64

            init(radius: f64) {
                self.radius = radius
            }

            pub prop diameter: f64 {
                get => self.radius * 2.0
            }
        }

        fn main() {
            let c = Circle(7.5)
            let d = c.diameter
            println("Diameter: {d}")
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            arx_file = os.path.join(tmpdir, "test_circle.arx")
            exe_file = os.path.join(tmpdir, "test_circle.exe")
            with open(arx_file, "w", encoding="utf-8") as f:
                f.write(code)

            out_exe = self.compiler.compile_file(arx_file, output_binary_path=exe_file)
            res = subprocess.run([out_exe], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
            self.assertEqual(res.stdout.strip(), "Diameter: 15")

    def test_binary_operator_overloading(self):
        code = """
        class Vector2 {
            pub x: i64
            pub y: i64

            init(x: i64, y: i64) {
                self.x = x
                self.y = y
            }

            pub op +(other: Vector2) -> Vector2 {
                return Vector2(self.x + other.x, self.y + other.y)
            }

            pub op ==(other: Vector2) -> bool {
                return self.x == other.x && self.y == other.y
            }
        }

        fn main() {
            let v1 = Vector2(10, 20)
            let v2 = Vector2(30, 40)
            let v3 = v1 + v2
            let is_equal = v1 == v2
            println("v3: {v3.x}, {v3.y} | eq: {is_equal}")
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            arx_file = os.path.join(tmpdir, "test_vec.arx")
            exe_file = os.path.join(tmpdir, "test_vec.exe")
            with open(arx_file, "w", encoding="utf-8") as f:
                f.write(code)

            out_exe = self.compiler.compile_file(arx_file, output_binary_path=exe_file)
            res = subprocess.run([out_exe], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
            self.assertEqual(res.stdout.strip(), "v3: 40, 60 | eq: false")


if __name__ == "__main__":
    unittest.main()
