"""
Phase 26 Unit Tests: Freestanding Bare-Metal Compilation Mode (--freestanding)
Validates strict bare-metal semantic rules (no heap, no libc, no threads),
pure ANSI C99 freestanding header emission, MMIO, fixed arrays, microcontroller
entrypoints (setup/loop), and GCC -ffreestanding -c compilation.
"""

import os
import tempfile
import unittest
import subprocess
from src.driver import AerixCompiler
from src.middle.semantic import SemanticError


class TestPhase26Freestanding(unittest.TestCase):
    def setUp(self):
        self.compiler = AerixCompiler()

    def test_rejection_of_heap_collections(self):
        """Freestanding mode must reject List<T>, Map<K,V>, Set<T>, Channel<T>."""
        src_list = """
        fn setup() {
            let mut items: List<i32> = [1, 2, 3]
        }
        """
        with self.assertRaises(SemanticError) as ctx:
            self.compiler.compile_source_to_c(src_list, freestanding=True)
        self.assertIn("is prohibited in freestanding bare-metal mode", str(ctx.exception))
        self.assertIn("List_i32", str(ctx.exception))

        src_map = """
        fn setup() {
            let mut cache: Map<i32, i32>
        }
        """
        with self.assertRaises(SemanticError) as ctx:
            self.compiler.compile_source_to_c(src_map, freestanding=True)
        self.assertIn("is prohibited in freestanding bare-metal mode", str(ctx.exception))
        self.assertIn("Map_i32_i32", str(ctx.exception))

    def test_rejection_of_heap_allocation_new(self):
        """Freestanding mode must reject 'new' operator."""
        src = """
        class MotorConfig {
            pub speed: u32
        }

        fn setup() {
            let cfg = new MotorConfig()
        }
        """
        with self.assertRaises(SemanticError) as ctx:
            self.compiler.compile_source_to_c(src, freestanding=True)
        self.assertIn("Dynamic heap allocation via 'new' is prohibited in freestanding bare-metal mode", str(ctx.exception))

    def test_rejection_of_spawn_multithreading(self):
        """Freestanding mode must reject 'spawn' threads."""
        src = """
        fn worker() {}

        fn setup() {
            spawn worker()
        }
        """
        with self.assertRaises(SemanticError) as ctx:
            self.compiler.compile_source_to_c(src, freestanding=True)
        self.assertIn("OS multithreading via 'spawn' is prohibited in freestanding bare-metal mode", str(ctx.exception))

    def test_rejection_of_os_libc_io_functions(self):
        """Freestanding mode must reject println, print, input, readln, arx_time_now."""
        for fn_call in ["println(\"hello\")", "print(\"hello\")", "input()", "readln()", "arx_time_now()"]:
            src = f"""
            fn setup() {{
                {fn_call}
            }}
            """
            with self.assertRaises(SemanticError) as ctx:
                self.compiler.compile_source_to_c(src, freestanding=True)
            self.assertIn("requires OS libc and is unavailable in freestanding mode", str(ctx.exception))

    def test_rejection_of_string_interpolation_and_concat(self):
        """Freestanding mode must reject dynamic string interpolation and heap string concatenation."""
        src_interp = """
        fn setup() {
            let speed: u32 = 120
            let msg = "speed: {speed}"
        }
        """
        with self.assertRaises(SemanticError) as ctx:
            self.compiler.compile_source_to_c(src_interp, freestanding=True)
        self.assertIn("Dynamic string interpolation is prohibited in freestanding bare-metal mode", str(ctx.exception))

        src_concat = """
        fn setup() {
            let a = "hello"
            let b = "world"
            let c = a + b
        }
        """
        with self.assertRaises(SemanticError) as ctx:
            self.compiler.compile_source_to_c(src_concat, freestanding=True)
        self.assertIn("Dynamic string concatenation is prohibited in freestanding bare-metal mode", str(ctx.exception))

    def test_clean_freestanding_c_emission(self):
        """Freestanding C emission must contain only freestanding headers and no libc / OS headers."""
        src = """
        #[packed]
        class TelemetryPacket {
            pub status: u8
            pub rpm: u16
            pub temperature: f32
        }

        fn setup() {
            let reg_addr: u64 = 0x40020000
            volatile_store_u32(reg_addr, 0x01)
        }

        fn loop() {
            let reg_addr: u64 = 0x40020000
            let state: u32 = volatile_load_u32(reg_addr)
            if state > 0 {
                volatile_store_u32(reg_addr, 0x00)
            }
        }
        """
        c_code = self.compiler.compile_source_to_c(src, freestanding=True)

        # Freestanding header checks
        self.assertIn("#include <stdint.h>", c_code)
        self.assertIn("#include <stdbool.h>", c_code)
        self.assertIn("#include <stddef.h>", c_code)
        self.assertNotIn("#include <stdio.h>", c_code)
        self.assertNotIn("#include <stdlib.h>", c_code)
        self.assertNotIn("#include <aerix_rt.h>", c_code)
        self.assertNotIn("malloc(", c_code)
        self.assertNotIn("free(", c_code)
        self.assertNotIn("printf(", c_code)

        # Volatile MMIO helpers present
        self.assertIn("volatile_load_u32", c_code)
        self.assertIn("volatile_store_u32", c_code)

        # Microcontroller unmangled entrypoints present
        self.assertIn("void setup(void)", c_code)
        self.assertIn("void loop(void)", c_code)

        # Synthetic main suppressed
        self.assertNotIn("int main(", c_code)

    def test_native_gcc_freestanding_object_compilation(self):
        """Host GCC must compile the emitted freestanding C99 code into an object file (.o) with -ffreestanding -c."""
        src = """
        #[packed]
        class SensorReading {
            pub seq: u32
            pub val: f32
        }

        fn read_sensor(base_addr: u64) -> SensorReading {
            let raw: u32 = volatile_load_u32(base_addr)
            let mut result = SensorReading()
            result.seq = raw
            result.val = 12.5
            return result
        }

        fn setup() {
            let gpio_addr: u64 = 0x40021000
            volatile_store_u32(gpio_addr, 0x00000001)
        }

        fn loop() {
            let sensor = read_sensor(0x40021000)
            if sensor.seq > 100 {
                volatile_store_u32(0x40021000, 0x00)
            }
        }
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            arx_file = os.path.join(tmp_dir, "firmware.arx")
            out_obj = os.path.join(tmp_dir, "firmware.o")
            with open(arx_file, "w", encoding="utf-8") as f:
                f.write(src)

            res_path = self.compiler.compile_file(arx_file, output_binary_path=out_obj, freestanding=True)
            self.assertTrue(os.path.exists(res_path))
            self.assertTrue(os.path.getsize(res_path) > 0)
            self.assertTrue(res_path.endswith(".o"))

    def test_freestanding_simd_vector_emission(self):
        """Freestanding mode must support SIMD vector math with __builtin_sqrtf."""
        src = """
        fn compute_vector(v: f32x4) -> f32x4 {
            let doubled = v * 2.0
            return doubled
        }

        fn setup() {
            let a = f32x4(1.0, 2.0, 3.0, 4.0)
            let b = compute_vector(a)
        }
        """
        c_code = self.compiler.compile_source_to_c(src, freestanding=True)
        self.assertIn("typedef float  f32x4", c_code)
        self.assertIn("__builtin_sqrtf", c_code)
        self.assertNotIn("#include <math.h>", c_code)


if __name__ == "__main__":
    unittest.main()
