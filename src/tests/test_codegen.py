"""
Aerix Compiler — Unit Tests for Backend C99 Codegen & GCC Compilation
"""

import os
import tempfile
import subprocess
import unittest
from src.driver import AerixCompiler


class TestCodegen(unittest.TestCase):
    def setUp(self):
        self.compiler = AerixCompiler()

    def test_emit_c_arithmetic_pipeline(self):
        code = """
        fn double(x: i64) -> i64 => x * 2

        fn main() {
            let res = 10 |> double()
            println(res)
        }
        """
        c_code = self.compiler.compile_source_to_c(code, "test_pipeline.arx")
        self.assertIn("#include <aerix_rt.h>", c_code)
        self.assertIn("arx_double", c_code)
        self.assertIn("int main(", c_code)

    def test_emit_c_oop_class(self):
        code = """
        class Hero {
            pub name: str
            pub hp: i64

            init(name: str, hp: i64) {
                self.name = name
                self.hp = hp
            }

            pub fn heal(amount: i64) {
                self.hp += amount
            }
        }

        fn main() {
            mut h = Hero("Arthur", 100)
            h.heal(25)
            println(h.hp)
        }
        """
        c_code = self.compiler.compile_source_to_c(code, "test_hero.arx")
        self.assertIn("struct Arx_Hero {", c_code)
        self.assertIn("Arx_Hero_init", c_code)
        self.assertIn("Arx_Hero_heal", c_code)

    def test_end_to_end_gcc_execution(self):
        # Full test: write code -> compile to .exe -> execute -> assert stdout!
        code = """
        fn square(n: i64) -> i64 => n * n

        fn main() {
            let val = 7
            let result = square(val)
            println(result)
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            arx_file = os.path.join(tmpdir, "square.arx")
            exe_file = os.path.join(tmpdir, "square.exe")
            with open(arx_file, "w", encoding="utf-8") as f:
                f.write(code)

            # Compile to native binary
            out_exe = self.compiler.compile_file(arx_file, output_binary_path=exe_file)
            self.assertTrue(os.path.exists(out_exe))

            # Run the compiled native executable!
            res = subprocess.run([out_exe], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            self.assertEqual(res.stdout.strip(), "49")

    def test_vector_4_defer_order(self):
        code = """
        fn test_defer() {
            println("Step 1")
            defer println("Defer 1 (Last)")
            println("Step 2")
            defer println("Defer 2 (First)")
            println("Step 3")
        }

        fn main() {
            test_defer()
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            arx_file = os.path.join(tmpdir, "defer.arx")
            exe_file = os.path.join(tmpdir, "defer.exe")
            with open(arx_file, "w", encoding="utf-8") as f:
                f.write(code)

            out_exe = self.compiler.compile_file(arx_file, output_binary_path=exe_file)
            res = subprocess.run([out_exe], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            expected = "Step 1\nStep 2\nStep 3\nDefer 2 (First)\nDefer 1 (Last)"
            self.assertEqual(res.stdout.strip().replace("\r\n", "\n"), expected)

    def test_vector_1_pipeline_interpolation(self):
        code = """
        fn double(x: i64) -> i64 => x * 2
        fn add_five(x: i64) -> i64 => x + 5

        fn main() {
            let result = 10 |> double() |> add_five()
            println("Result: {result}")
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            arx_file = os.path.join(tmpdir, "pipeline.arx")
            exe_file = os.path.join(tmpdir, "pipeline.exe")
            with open(arx_file, "w", encoding="utf-8") as f:
                f.write(code)

            out_exe = self.compiler.compile_file(arx_file, output_binary_path=exe_file)
            res = subprocess.run([out_exe], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            self.assertEqual(res.stdout.strip(), "Result: 25")

    def test_vector_3_oop_account(self):
        code = """
        class Account {
            pub owner: str
            priv balance: f64

            init(owner: str, initial: f64) {
                self.owner = owner
                self.balance = initial
            }

            pub fn deposit(amt: f64) {
                self.balance += amt
            }

            pub fn get_balance() -> f64 => self.balance
        }

        fn main() {
            mut acc = Account("Charlie", 500.0)
            acc.deposit(250.0)
            println("{acc.owner} balance: {acc.get_balance()}")
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            arx_file = os.path.join(tmpdir, "account.arx")
            exe_file = os.path.join(tmpdir, "account.exe")
            with open(arx_file, "w", encoding="utf-8") as f:
                f.write(code)

            out_exe = self.compiler.compile_file(arx_file, output_binary_path=exe_file)
            res = subprocess.run([out_exe], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            self.assertEqual(res.stdout.strip(), "Charlie balance: 750")

    def test_user_input_codegen_and_execution(self):
        code = """
        fn main() {
            let name = input("Name: ")
            println("User: {name}")
        }
        """
        c_code = self.compiler.compile_source_to_c(code, "test_input.arx")
        self.assertIn("arx_input(", c_code)

        with tempfile.TemporaryDirectory() as tmpdir:
            arx_file = os.path.join(tmpdir, "input_test.arx")
            exe_file = os.path.join(tmpdir, "input_test.exe")
            with open(arx_file, "w", encoding="utf-8") as f:
                f.write(code)

            out_exe = self.compiler.compile_file(arx_file, output_binary_path=exe_file)
            p = subprocess.Popen([out_exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, _ = p.communicate(input="TestUser\n")
            self.assertEqual(p.returncode, 0)
            self.assertIn("User: TestUser", stdout)

    def test_string_escape_sequences_tab_and_newline(self):
        code = r"""
        fn main() {
            let age = 12
            if age >= 18 || age < 13 {
                print("\tYou are Underaged! ({age})\n")
            } else {
                print("\tYou are Old Enough! ({age})\n")
            }
        }
        """
        c_code = self.compiler.compile_source_to_c(code, "test_escapes.arx")
        self.assertIn(r"\tYou are Underaged! (%lld)\n", c_code)

        with tempfile.TemporaryDirectory() as tmpdir:
            arx_file = os.path.join(tmpdir, "escapes.arx")
            exe_file = os.path.join(tmpdir, "escapes.exe")
            with open(arx_file, "w", encoding="utf-8") as f:
                f.write(code)

            out_exe = self.compiler.compile_file(arx_file, output_binary_path=exe_file)
            res = subprocess.run([out_exe], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            self.assertEqual(res.stdout, "\tYou are Underaged! (12)\n")

    def test_dynamic_typed_input_and_typeof(self):
        code = """
        fn main() {
            let mut age = input("Enter Age: ")
            let mut num : i32 = input("Enter Num: ")
            let mut pi : f64 = input("Enter Pi: ")
            let mut ok : bool = input("Enter Ok: ")
            println("age: {age}, typeof: {typeof(age)}")
            println("num: {num}, typeof: {typeof(num)}")
            println("pi: {pi}, typeof: {typeof(pi)}")
            println("ok: {ok}, typeof: {typeof(ok)}")
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            arx_file = os.path.join(tmpdir, "test_input_types.arx")
            exe_file = os.path.join(tmpdir, "test_input_types.exe")
            with open(arx_file, "w", encoding="utf-8") as f:
                f.write(code)

            out_exe = self.compiler.compile_file(arx_file, output_binary_path=exe_file)
            p = subprocess.Popen([out_exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = p.communicate(input="25\n42\n3.14\ntrue\n")
            self.assertEqual(p.returncode, 0, f"Error: {stderr}")
            self.assertIn("age: 25, typeof: str", stdout)
            self.assertIn("num: 42, typeof: i32", stdout)
            self.assertIn("pi: 3.14, typeof: f64", stdout)
            self.assertIn("ok: true, typeof: bool", stdout)

    def test_explicit_type_casting(self):
        code = """
        fn main() {
            let s = "100"
            let n = s as i64
            let f = n as f64
            let s2 = f as str
            let b = true
            let sb = b as str
            println("n: {n}, f: {f}, s2: {s2}, sb: {sb}")
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            arx_file = os.path.join(tmpdir, "test_cast.arx")
            exe_file = os.path.join(tmpdir, "test_cast.exe")
            with open(arx_file, "w", encoding="utf-8") as f:
                f.write(code)

            out_exe = self.compiler.compile_file(arx_file, output_binary_path=exe_file)
            res = subprocess.run([out_exe], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
            self.assertIn("n: 100, f: 100, s2: 100, sb: true", res.stdout)


if __name__ == "__main__":
    unittest.main()



