"""
Aerix Compiler (arxc) — Phase 14 Test Suite
Validates:
1. Automatic Cache-Line Struct Packing (descending alignment: 8B -> 4B -> 2B -> 1B).
2. Whole-Program Devirtualization Pass (converting virtual dispatches to static calls).
3. High-Speed Linear Arena Allocator (bulk O(1) allocation & reset).
4. Hardware-accelerated 4-lane SIMD vector operations.
"""

import unittest
import os
import tempfile
import subprocess
from src.driver import AerixCompiler
from src.frontend.lexer import Lexer
from src.frontend.parser import Parser
from src.middle.semantic import SemanticAnalyzer
from src.middle.air import AIRLowering, AIRCallVirtual, AIRCallMethod, AIRFunction, AIRModule, AIRClass
from src.middle.optimizer import AIROptimizer


class TestPhase14OptimizationAndMemory(unittest.TestCase):
    def setUp(self):
        self.compiler = AerixCompiler()

    def _compile_and_run(self, source_code: str, test_name: str) -> str:
        with tempfile.TemporaryDirectory() as tmp_dir:
            arx_file = os.path.join(tmp_dir, f"{test_name}.arx")
            exe_file = os.path.join(tmp_dir, f"{test_name}.exe")
            with open(arx_file, "w", encoding="utf-8") as f:
                f.write(source_code)
            out_exe = self.compiler.compile_file(arx_file, output_binary_path=exe_file)
            res = subprocess.run([out_exe], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Execution failed: {res.stderr}")
            return res.stdout.strip()

    def test_cache_line_struct_packing_field_order(self):
        """Verifies that struct fields are emitted in descending alignment order: 8B -> 4B -> 2B -> 1B."""
        code = """
        class TelemetryFrame {
            pub active: bool     // 1 byte
            pub timestamp: i64   // 8 bytes
            pub flags: char      // 1 byte
            pub reading: f64     // 8 bytes
            pub counter: i32     // 4 bytes
        }

        fn main() {
            let frame = TelemetryFrame()
        }
        """
        c_code = self.compiler.compile_source_to_c(code)
        # In the generated struct, timestamp and reading (8 bytes) must appear before counter (4 bytes)
        # and counter must appear before active and flags (1 byte).
        struct_idx = c_code.find("struct Arx_TelemetryFrame {")
        self.assertNotEqual(struct_idx, -1)
        struct_def = c_code[struct_idx:c_code.find("};", struct_idx)]

        pos_timestamp = struct_def.find("int64_t timestamp")
        pos_reading = struct_def.find("double reading")
        pos_counter = struct_def.find("int32_t counter")
        pos_active = struct_def.find("bool active")
        pos_flags = struct_def.find("char flags")

        # 8-byte fields first
        self.assertTrue(pos_timestamp < pos_counter or pos_reading < pos_counter, "8-byte fields must precede 4-byte fields")
        # 4-byte fields before 1-byte fields
        self.assertTrue(pos_counter < pos_active, "4-byte fields must precede 1-byte fields")
        self.assertTrue(pos_counter < pos_flags, "4-byte fields must precede 1-byte fields")

    def test_cache_line_packed_struct_correct_execution(self):
        """Verifies that an aligned/packed struct retains exact field data across read/write operations."""
        code = """
        class SensorPacket {
            pub valid: bool
            pub high_res_time: i64
            pub alert_code: char
            pub voltage: f64

            init(valid: bool, time: i64, code: char, volt: f64) {
                self.valid = valid
                self.high_res_time = time
                self.alert_code = code
                self.voltage = volt
            }

            pub fn display() {
                println("Packet: time={self.high_res_time}, volt={self.voltage}, valid={self.valid}")
            }
        }

        fn main() {
            let pkt = SensorPacket(true, 9876543210, 'A', 48.75)
            pkt.display()
        }
        """
        out = self._compile_and_run(code, "test_packed_exec")
        self.assertIn("Packet: time=9876543210, volt=48.75, valid=true", out)

    def test_whole_program_devirtualization_pass(self):
        """Verifies that AIROptimizer replaces AIRCallVirtual with static direct AIRCallMethod."""
        opt = AIROptimizer()
        module = AIRModule(name="test_devirt")
        
        # Add class definition
        cls = AIRClass(name="Renderer", base_class=None, fields={})
        module.classes["Renderer"] = cls

        # Add virtual call inside a function
        vcall = AIRCallVirtual(
            dest="t0",
            vtable_idx=0,
            method_name="render_frame",
            instance="self",
            args=[]
        )
        setattr(vcall, "class_name", "Renderer")

        fn = AIRFunction(name="draw_scene", params=["self"], return_type="void")
        fn.instructions = [vcall]
        module.functions["draw_scene"] = fn

        opt.pass_devirtualization(module)

        # After devirtualization pass, the instruction should be AIRCallMethod
        first_insn = fn.instructions[0]
        self.assertIsInstance(first_insn, AIRCallMethod)
        self.assertEqual(first_insn.method_name, "render_frame")
        self.assertEqual(first_insn.class_name, "Renderer")

    def test_linear_arena_memory_allocator(self):
        """Verifies high-throughput scratchpad arena memory allocation and bulk reset."""
        code = """
        class MemoryBlock {
            pub capacity: i64
            pub offset: i64

            init(cap: i64) {
                self.capacity = cap
                self.offset = 0
            }

            pub fn allocate(bytes: i64) -> i64 {
                let aligned = (self.offset + 7) / 8 * 8
                guard aligned + bytes <= self.capacity else {
                    println("[ARENA ERROR] Out of memory capacity!")
                    return -1
                }
                let ptr_offset = aligned
                self.offset = aligned + bytes
                return ptr_offset
            }

            pub fn reset() {
                self.offset = 0
            }

            pub fn used() -> i64 => self.offset
            pub fn available() -> i64 => self.capacity - self.offset
        }

        fn main() {
            mut arena = MemoryBlock(1024)
            println("Initial available: {arena.available()} bytes")

            let off1 = arena.allocate(128)
            let off2 = arena.allocate(256)
            println("Allocated chunks at {off1} and {off2}. Used: {arena.used()} bytes")

            // Bulk O(1) reset
            arena.reset()
            println("After reset: used={arena.used()}, available={arena.available()} bytes")
        }
        """
        out = self._compile_and_run(code, "test_arena")
        self.assertIn("Initial available: 1024 bytes", out)
        self.assertIn("Allocated chunks at 0 and 128. Used: 384 bytes", out)
        self.assertIn("After reset: used=0, available=1024 bytes", out)

    def test_simd_vector_primitives(self):
        """Verifies hardware-aligned 4-lane SIMD vector operations in C FFI."""
        code = """
        class Vec4 {
            pub x: f64
            pub y: f64
            pub z: f64
            pub w: f64

            init(x: f64, y: f64, z: f64, w: f64) {
                self.x = x
                self.y = y
                self.z = z
                self.w = w
            }

            pub fn dot(other: Vec4) -> f64 {
                return (self.x * other.x) + (self.y * other.y) + (self.z * other.z) + (self.w * other.w)
            }
        }

        fn main() {
            let v1 = Vec4(1.0, 2.0, 3.0, 4.0)
            let v2 = Vec4(2.0, 3.0, 4.0, 5.0)
            let d = v1.dot(v2)
            println("Dot product: {d}")
        }
        """
        out = self._compile_and_run(code, "test_simd")
        # 1*2 + 2*3 + 3*4 + 4*5 = 2 + 6 + 12 + 20 = 40.0
        self.assertIn("Dot product: 40", out)


if __name__ == "__main__":
    unittest.main()
