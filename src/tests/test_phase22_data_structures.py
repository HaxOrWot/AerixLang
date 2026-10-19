"""
Aerix Compiler (arxc) — Phase 22 Test Suite: Comprehensive Data Structures
Verifies Tuples, Robin Hood Hash Maps, Hash Sets, Linear Buffers (Stack, Queue, Deque),
Binary ByteBuffer, List Algorithms, and Generalized Collection Iteration.
"""

import os
import unittest
import tempfile
import subprocess
from src.driver import AerixCompiler


class TestPhase22DataStructures(unittest.TestCase):
    def setUp(self):
        self.compiler = AerixCompiler()

    def test_tuples_creation_indexing_and_destructuring(self):
        """Validates tuple literals, element access via t.0 / t.1, functions returning tuples, and destructuring."""
        code = """
        fn get_coords() -> (i64, str) {
            return (42, "Apex");
        }

        fn main() {
            // Literal and field access
            let point = (10, 20);
            println(point.0);
            println(point.1);

            // Function returning tuple and destructuring
            let (val, label) = get_coords();
            println(val);
            println(label);
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
            self.assertEqual(lines, ["10", "20", "42", "Apex"])

    def test_map_string_and_int_keys(self):
        """Validates Robin Hood Map with string keys and integer keys, indexing, and membership."""
        code = """
        fn main() {
            mut scores = Map<str, i64>();
            scores["alice"] = 95;
            scores["bob"] = 88;

            println(scores["alice"]);
            println(scores["bob"]);
            println(scores.has_key("alice"));
            println(scores.has_key("charlie"));
            println(scores.len());

            scores.remove("bob");
            println(scores.has_key("bob"));
            println(scores.len());

            // Integer key map
            mut lookup = Map<i64, str>();
            lookup[1] = "First";
            lookup[2] = "Second";
            println(lookup[1]);
            println(lookup[2]);
            println(lookup.len());
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
                "95", "88", "true", "false", "2",
                "false", "1",
                "First", "Second", "2"
            ])

    def test_set_operations_and_algebra(self):
        """Validates Set insertion, lookup, removal, and set algebra (union, intersection, difference)."""
        code = """
        fn main() {
            mut tags = Set<str>();
            tags.add("aerix");
            tags.add("fast");
            tags.add("safe");

            println(tags.has("aerix"));
            println(tags.has("slow"));
            println(tags.len());

            tags.remove("fast");
            println(tags.has("fast"));
            println(tags.len());

            // Set Algebra with integer sets
            mut s1 = Set<i64>();
            s1.add(1);
            s1.add(2);
            s1.add(3);

            mut s2 = Set<i64>();
            s2.add(2);
            s2.add(3);
            s2.add(4);

            let u = s1.union(s2);
            println(u.len());

            let inter = s1.intersection(s2);
            println(inter.len());

            let diff = s1.difference(s2);
            println(diff.len());
            println(diff.has(1));
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
                "true", "false", "3",
                "false", "2",
                "4", "2", "1", "true"
            ])

    def test_stack_operations(self):
        """Validates LIFO Stack push, pop, peek, and capacity management."""
        code = """
        fn main() {
            mut s = Stack<i64>();
            s.push(10);
            s.push(20);
            s.push(30);

            println(s.len());
            println(s.peek());
            println(s.pop());
            println(s.pop());
            println(s.peek());
            println(s.len());
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
            self.assertEqual(lines, ["3", "30", "30", "20", "10", "1"])

    def test_queue_operations(self):
        """Validates FIFO Queue enqueue, dequeue, peek, and len."""
        code = """
        fn main() {
            mut q = Queue<i64>();
            q.enqueue(100);
            q.enqueue(200);
            q.enqueue(300);

            println(q.len());
            println(q.peek());
            println(q.dequeue());
            println(q.dequeue());
            println(q.peek());
            println(q.len());
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
            self.assertEqual(lines, ["3", "100", "100", "200", "300", "1"])

    def test_deque_operations(self):
        """Validates double-ended Queue (push_front, push_back, pop_front, pop_back)."""
        code = """
        fn main() {
            mut dq = Deque<i64>();
            dq.push_back(20);
            dq.push_front(10);
            dq.push_back(30);

            println(dq.len());
            println(dq.peek_front());
            println(dq.peek_back());
            println(dq.pop_front());
            println(dq.pop_back());
            println(dq.len());
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
            self.assertEqual(lines, ["3", "10", "30", "10", "30", "1"])

    def test_byte_buffer(self):
        """Validates binary ByteBuffer serialization and deserialization."""
        code = """
        fn main() {
            mut buf = ByteBuffer();
            buf.write_u8(65);
            buf.write_i32_le(42000);

            println(buf.len());
            buf.reset();
            println(buf.read_u8());
            println(buf.read_i32_le());
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
            self.assertEqual(lines, ["5", "65", "42000"])

    def test_list_algorithms(self):
        """Validates advanced List algorithms: sort, reverse, contains, index_of, swap_remove, insert."""
        code = """
        fn main() {
            mut list = List<i64>();
            list.push(30);
            list.push(10);
            list.push(20);

            list.sort();
            println(list[0]);
            println(list[1]);
            println(list[2]);

            list.reverse();
            println(list[0]);
            println(list[1]);
            println(list[2]);

            println(list.contains(20));
            println(list.contains(99));
            println(list.index_of(20));

            let removed = list.swap_remove(0);
            println(removed);
            println(list.len());
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
                "10", "20", "30",
                "30", "20", "10",
                "true", "false", "1",
                "30", "2"
            ])

    def test_collection_iteration_for_in(self):
        """Validates collection iteration syntax: for item in list."""
        code = """
        fn main() {
            mut nums = List<i64>();
            nums.push(100);
            nums.push(200);
            nums.push(300);

            for n in nums {
                println(n);
            }

            mut words = List<str>();
            words.push("Aerix");
            words.push("ZeroCost");

            for w in words {
                println(w);
            }
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
            self.assertEqual(lines, ["100", "200", "300", "Aerix", "ZeroCost"])


if __name__ == "__main__":
    unittest.main()
