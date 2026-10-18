"""
Aerix Compiler (arxc) — Phase 19 Test Suite: Lightweight Concurrency & Channels
Validates 'spawn' worker thread dispatch, Win32/POSIX platform threading,
argument pack marshaling, thread joining, and thread-safe bounded channels.
"""

import os
import unittest
import subprocess
import tempfile
from src.driver import AerixCompiler


class TestPhase19Concurrency(unittest.TestCase):
    def setUp(self):
        self.compiler = AerixCompiler()

    def test_spawn_and_join_worker(self):
        """Validates that a thread can be spawned and joined cleanly."""
        code = """
        fn worker() {
            arx_sleep_ms(20);
        }

        fn main() {
            let t = spawn worker();
            arx_thread_join(t);
            println(101);
        }
        """
        c_code = self.compiler.compile_source_to_c(code, "test_spawn_join.arx")
        self.assertIn("arx_thread_spawn", c_code)
        self.assertIn("arx_thread_join", c_code)

        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "test.arx")
            exe = os.path.join(tmpdir, "test.exe")
            with open(src, "w", encoding="utf-8") as f:
                f.write(code)
            out_exe = self.compiler.compile_file(src, output_binary_path=exe)
            res = subprocess.run([out_exe], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            self.assertEqual(res.stdout.strip(), "101")

    def test_channel_single_producer_consumer(self):
        """Validates message passing through a thread-safe bounded channel."""
        code = """
        fn sender(ch: i64) {
            arx_sleep_ms(10);
            arx_channel_send(ch, 999);
        }

        fn main() {
            let ch = arx_channel_new(8);
            let t = spawn sender(ch);
            let received = arx_channel_recv(ch);
            arx_thread_join(t);
            arx_channel_free(ch);
            println(received);
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
            self.assertEqual(res.stdout.strip(), "999")

    def test_spawn_multiple_arguments(self):
        """Validates argument pack marshaling for multi-argument spawned functions."""
        code = """
        fn compute(ch: i64, a: i64, b: i64) {
            arx_channel_send(ch, a * b);
        }

        fn main() {
            let ch = arx_channel_new(4);
            let t = spawn compute(ch, 6, 7);
            let val = arx_channel_recv(ch);
            arx_thread_join(t);
            arx_channel_free(ch);
            println(val);
        }
        """
        c_code = self.compiler.compile_source_to_c(code, "test_multi_arg.arx")
        self.assertIn("Arx_ArgPack_", c_code)

        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "test.arx")
            exe = os.path.join(tmpdir, "test.exe")
            with open(src, "w", encoding="utf-8") as f:
                f.write(code)
            out_exe = self.compiler.compile_file(src, output_binary_path=exe)
            res = subprocess.run([out_exe], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            self.assertEqual(res.stdout.strip(), "42")

    def test_multi_producer_channel_sync(self):
        """Validates synchronization with multiple concurrent worker threads producing into one channel."""
        code = """
        fn worker(ch: i64, val: i64) {
            arx_sleep_ms(10);
            arx_channel_send(ch, val);
        }

        fn main() {
            let ch = arx_channel_new(10);
            let t1 = spawn worker(ch, 10);
            let t2 = spawn worker(ch, 20);
            let t3 = spawn worker(ch, 30);

            let v1 = arx_channel_recv(ch);
            let v2 = arx_channel_recv(ch);
            let v3 = arx_channel_recv(ch);

            arx_thread_join(t1);
            arx_thread_join(t2);
            arx_thread_join(t3);
            arx_channel_free(ch);

            let total = v1 + v2 + v3;
            println(total);
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
            self.assertEqual(res.stdout.strip(), "60")

    def test_generic_channel_class(self):
        """Validates that a generic Channel<T> class encapsulates raw channel handles with monomorphism."""
        code = """
        class Channel<T> {
            pub handle: i64

            init(cap: i64) {
                self.handle = arx_channel_new(cap);
            }

            pub fn send(val: T) {
                arx_channel_send(self.handle, val as i64);
            }

            pub fn recv() -> T {
                let res = arx_channel_recv(self.handle);
                return res as T;
            }

            pub fn free() {
                arx_channel_free(self.handle);
            }
        }

        fn producer(ch_handle: i64) {
            arx_channel_send(ch_handle, 1234);
        }

        fn main() {
            mut chan = Channel<i64>(8);
            let t = spawn producer(chan.handle);
            let val = chan.recv();
            arx_thread_join(t);
            chan.free();
            println(val);
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
            self.assertEqual(res.stdout.strip(), "1234")


if __name__ == "__main__":
    unittest.main()
