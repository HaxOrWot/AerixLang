"""
Aerix Compiler (arxc) — Phase 21 Test Suite: Dynamic Collections & Dual-Tier Text Engine
Verifies dynamic contiguous vectors (List<T>), bracket indexing, slicing,
and the dual-tier string processing engine (str & String).
"""

import os
import unittest
import tempfile
import subprocess
from src.driver import AerixCompiler


class TestPhase21Collections(unittest.TestCase):
    def setUp(self):
        self.compiler = AerixCompiler()

    def test_list_i64_push_pop_indexing(self):
        """Validates List<i64> creation, push, pop, and bracket indexing."""
        code = """
        fn main() {
            mut items = List<i64>();
            items.push(10);
            items.push(20);
            items.push(30);

            println(items[0]);
            println(items[1]);
            println(items[2]);

            // Mutate index
            items[1] = 99;
            println(items[1]);

            let popped = items.pop();
            println(popped);
            println(items.len());
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
            self.assertEqual(lines, ["10", "20", "30", "99", "30", "2"])

    def test_list_str_operations(self):
        """Validates List<str> with string push, indexing, and mutation."""
        code = """
        fn main() {
            mut words = List<str>();
            words.push("Aerix");
            words.push("Systems");
            words.push("Language");

            println(words[0]);
            println(words[1]);
            println(words[2]);

            words[1] = "Native";
            println(words[1]);
            println(words.len());
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
            self.assertEqual(lines, ["Aerix", "Systems", "Language", "Native", "3"])

    def test_list_slicing(self):
        """Validates zero-copy range slicing on List<T>."""
        code = """
        fn main() {
            mut nums = List<i64>();
            nums.push(100);
            nums.push(200);
            nums.push(300);
            nums.push(400);

            let sub = nums[1..3];
            println(sub.len());
            println(sub[0]);
            println(sub[1]);
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
            self.assertEqual(lines, ["2", "200", "300"])

    def test_str_methods_and_transformations(self):
        """Validates fluent text manipulation methods on str primitives."""
        code = """
        fn main() {
            let raw = "   hello aerix   ";
            let trimmed = raw.trim();
            let upper = trimmed.to_upper();
            let lower = upper.to_lower();
            let replaced = lower.replace("aerix", "world");

            println(trimmed);
            println(upper);
            println(lower);
            println(replaced);
            println(raw.contains("aerix"));
            println(trimmed.starts_with("hello"));
            println(trimmed.ends_with("aerix"));
            println(trimmed.len());
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
            self.assertEqual(lines, [
                "hello aerix",
                "HELLO AERIX",
                "hello aerix",
                "hello world",
                "true",
                "true",
                "true",
                "11"
            ])

    def test_str_split_and_indexing(self):
        """Validates splitting str into List<str> and indexing parts."""
        code = """
        fn main() {
            let sentence = "alpha beta gamma delta";
            let parts = sentence.split(" ");
            println(parts.len());
            println(parts[0]);
            println(parts[1]);
            println(parts[2]);
            println(parts[3]);
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
            self.assertEqual(lines, ["4", "alpha", "beta", "gamma", "delta"])

    def test_string_class_object(self):
        """Validates String class object API with chaining and interpolation."""
        code = """
        fn main() {
            mut s = String("  fast native language  ");
            let clean = s.trim().to_upper();
            println(clean.as_str());
            println(clean.len);

            let tokens = clean.split(" ");
            println(tokens.len());
            println(tokens[0]);
            println(tokens[1]);
            println(tokens[2]);
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
            self.assertEqual(lines, [
                "FAST NATIVE LANGUAGE",
                "20",
                "3",
                "FAST",
                "NATIVE",
                "LANGUAGE"
            ])


if __name__ == "__main__":
    unittest.main()
