"""
Aerix Compiler (arxc) — Automated Overloading Test Suite (Phase 10)
Tests method overloading, constructor overloading, and type-mangled static dispatch.
"""

import unittest
import tempfile
import os
import subprocess
from src.driver import AerixCompiler


class TestOverloading(unittest.TestCase):
    def setUp(self):
        self.compiler = AerixCompiler()
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_code(self, source: str) -> str:
        src_path = os.path.join(self.temp_dir.name, "test.arx")
        exe_path = os.path.join(self.temp_dir.name, "test.exe")
        with open(src_path, "w", encoding="utf-8") as f:
            f.write(source)
        self.compiler.compile_file(src_path, output_binary_path=exe_path)
        result = subprocess.run([exe_path], capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def test_method_overload_by_arity(self):
        source = """
class Messenger {
    pub fn greet(name: str) -> void {
        print("Hello, {name}!")
    }

    pub fn greet(name: str, title: str) -> void {
        print("Greetings, {title} {name}!")
    }
}

fn main() {
    mut m = Messenger()
    m.greet("Arthur")
    print(" | ")
    m.greet("Arthur", "King")
}
"""
        output = self.run_code(source)
        self.assertEqual(output, "Hello, Arthur! | Greetings, King Arthur!")

    def test_method_overload_by_type(self):
        source = """
class Formatter {
    pub fn format(val: i64) -> void {
        print("Integer: {val}")
    }

    pub fn format(val: str) -> void {
        print("String: {val}")
    }
}

fn main() {
    mut f = Formatter()
    f.format(42)
    print(" | ")
    f.format("Aerix")
}
"""
        output = self.run_code(source)
        self.assertEqual(output, "Integer: 42 | String: Aerix")

    def test_constructor_overloading(self):
        source = """
class Hero {
    pub name: str
    pub hp: i64

    init(name: str) {
        self.name = name
        self.hp = 100
    }

    init(name: str, hp: i64) {
        self.name = name
        self.hp = hp
    }

    pub fn show() -> void {
        print("{self.name}:{self.hp}")
    }
}

fn main() {
    mut h1 = Hero("Arthur")
    mut h2 = Hero("Lancelot", 250)
    h1.show()
    print(" | ")
    h2.show()
}
"""
        output = self.run_code(source)
        self.assertEqual(output, "Arthur:100 | Lancelot:250")


if __name__ == "__main__":
    unittest.main()
