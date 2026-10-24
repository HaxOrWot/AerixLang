"""
Aerix Compiler (arxc) — Phase 24 Test Suite: Memory Layout Attributes & Volatile MMIO Registers
Verifies:
1. sizeof(T) type byte size operator on primitives, fixed-size arrays, and classes.
2. #[packed] layout attribute ensuring 0 struct padding and strict declaration order.
3. #[align(N)] layout attribute ensuring power-of-two struct memory alignment.
4. Semantic validation rejecting invalid alignment (e.g. non-power-of-two, zero, negative).
5. Volatile MMIO read/write register intrinsics (volatile_read_*, volatile_write_*, arx_address_of).
"""

import os
import unittest
import tempfile
import subprocess
from src.driver import AerixCompiler
from src.middle.semantic import SemanticError
from src.frontend.diagnostics import DiagnosticBag


class TestPhase24LayoutAndMMIO(unittest.TestCase):
    def setUp(self):
        self.compiler = AerixCompiler()

    def test_sizeof_primitives_and_arrays(self):
        """Verifies compile-time sizeof operator on standard primitives and fixed-size stack arrays."""
        code = """
        fn main() {
            println(sizeof(u8))
            println(sizeof(u16))
            println(sizeof(u32))
            println(sizeof(u64))
            println(sizeof(i32))
            println(sizeof(f64))
            println(sizeof([i32; 4]))
            println(sizeof([u8; 10]))
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
            self.assertEqual(lines, ["1", "2", "4", "8", "4", "8", "16", "10"])

    def test_packed_struct_layout(self):
        """Verifies #[packed] removes padding bytes and preserves physical declaration order."""
        code = """
        #[packed]
        class TelemetryHeader {
            pub magic: u8
            pub seq: u16
            pub status: u8
        }

        fn main() {
            // Unpacked would be 1 + 1(pad) + 2 + 1 + 1(pad) = 6 bytes
            // Packed must be exactly 1 + 2 + 1 = 4 bytes!
            println(sizeof(TelemetryHeader))

            mut pkt = TelemetryHeader()
            pkt.magic = 0xAA
            pkt.seq = 1024
            pkt.status = 1
            println(pkt.magic)
            println(pkt.seq)
            println(pkt.status)
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
            self.assertEqual(lines, ["4", "170", "1024", "1"])

    def test_aligned_struct(self):
        """Verifies #[align(64)] enforces 64-byte boundary padding and alignment."""
        code = """
        #[align(64)]
        class CachePaddedState {
            counter: u64
        }

        fn main() {
            let sz = sizeof(CachePaddedState)
            println(sz)
            let is_aligned = (sz % 64 == 0)
            println(is_aligned)
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
            self.assertEqual(lines, ["64", "true"])

    def test_packed_and_aligned_combined(self):
        """Verifies combined #[packed, align(32)] attributes on a single class."""
        code = """
        #[packed, align(32)]
        class BufferDescriptor {
            flags: u8
            addr: u32
        }

        fn main() {
            println(sizeof(BufferDescriptor))
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
            self.assertEqual(res.stdout.strip(), "32")

    def test_invalid_alignment_semantic_error(self):
        """Verifies that non-power-of-two alignments produce a clear compile-time error."""
        code = """
        #[align(15)]
        class InvalidAlignmentClass {
            val: i32
        }

        fn main() {}
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "test.arx")
            exe = os.path.join(tmpdir, "test.exe")
            with open(src, "w", encoding="utf-8") as f:
                f.write(code)
            with self.assertRaises((SemanticError, DiagnosticBag)) as ctx:
                self.compiler.compile_file(src, output_binary_path=exe)
            err_msg = str(ctx.exception)
            self.assertIn("Invalid alignment '15'", err_msg)
            self.assertIn("power of 2", err_msg)

    def test_volatile_mmio_read_write_u32(self):
        """Verifies volatile MMIO register write and read semantics using stack address."""
        code = """
        fn main() {
            mut control_reg: u32 = 0
            let reg_addr: usize = arx_address_of(control_reg)

            volatile_write_u32(reg_addr, 0xCAFEBABE)
            let read_back: u32 = volatile_read_u32(reg_addr)
            println(read_back)
            println(control_reg)
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
            self.assertEqual(lines, ["3405691582", "3405691582"])

    def test_volatile_mmio_u8_u16_u64(self):
        """Verifies volatile read/write for u8, u16, and u64 bit widths."""
        code = """
        fn main() {
            mut byte_val: u8 = 0
            mut word_val: u16 = 0
            mut quad_val: u64 = 0

            let b_addr: usize = address_of(byte_val)
            let w_addr: usize = address_of(word_val)
            let q_addr: usize = address_of(quad_val)

            volatile_write_u8(b_addr, 255)
            volatile_write_u16(w_addr, 65530)
            volatile_write_u64(q_addr, 100000000000)

            println(volatile_read_u8(b_addr))
            println(volatile_read_u16(w_addr))
            println(volatile_read_u64(q_addr))
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
            self.assertEqual(lines, ["255", "65530", "100000000000"])


if __name__ == "__main__":
    unittest.main()
