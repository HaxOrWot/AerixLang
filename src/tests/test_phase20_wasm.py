"""
Aerix Compiler (arxc) — Phase 20 Test Suite: WebAssembly (WASM) Backend & Browser Target
Validates:
1. WebAssembly Text Format (.wat) S-expression emission.
2. Pure-Python WebAssembly Binary (.wasm) generation, magic headers, and section encodings.
3. Linear memory, string data segments, and browser JS runtime imports.
4. Interactive HTML5 browser runner page generation.
5. End-to-end file compilation pipeline through AerixCompiler.
"""

import os
import unittest
import tempfile
from src.driver import AerixCompiler
from src.backend.wasm import WasmBinaryEncoder, WasmTextEmitter, generate_browser_runner_html


class TestPhase20WebAssembly(unittest.TestCase):
    def setUp(self):
        self.compiler = AerixCompiler()

    def test_wat_generation_simple(self):
        """Validates standard WebAssembly Text format (.wat) generation."""
        code = """
        fn add(a: i64, b: i64) -> i64 {
            return a + b;
        }

        fn main() {
            let res = add(10, 20);
            println(res);
        }
        """
        wat = self.compiler.compile_source_to_wat(code, "test_add.arx")
        self.assertIn("(module", wat)
        self.assertIn('(import "env" "print_i64"', wat)
        self.assertIn('(memory (export "memory") 1)', wat)
        self.assertIn("(func $add", wat)
        self.assertIn("i64.add", wat)
        self.assertIn('(func $main (export "main")', wat)
        self.assertIn("call $add", wat)

    def test_wasm_binary_magic_and_header(self):
        """Validates that binary WASM output starts with standard W3C magic and version."""
        code = """
        fn compute(x: i64) -> i64 {
            return x * 2;
        }

        fn main() {
            println(compute(42));
        }
        """
        wasm_bytes = self.compiler.compile_source_to_wasm(code, "test_binary.arx")
        self.assertIsInstance(wasm_bytes, bytes)
        # Standard WASM magic: \x00asm
        self.assertEqual(wasm_bytes[:4], b"\x00asm")
        # Standard WASM version: 1 (\x01\x00\x00\x00)
        self.assertEqual(wasm_bytes[4:8], b"\x01\x00\x00\x00")
        self.assertGreater(len(wasm_bytes), 32)

    def test_wasm_canvas_and_interop_imports(self):
        """Validates canvas drawing primitives and browser runtime imports."""
        code = """
        fn draw_box() {
            arx_canvas_clear(0, 0, 0);
            arx_canvas_fill_rect(10, 20, 100, 50, 255, 128, 0);
        }

        fn main() {
            draw_box();
        }
        """
        wat = self.compiler.compile_source_to_wat(code, "test_canvas.arx")
        self.assertIn('(import "env" "arx_canvas_clear"', wat)
        self.assertIn('(import "env" "arx_canvas_fill_rect"', wat)
        self.assertIn("call $arx_canvas_clear", wat)
        self.assertIn("call $arx_canvas_fill_rect", wat)

        wasm_bytes = self.compiler.compile_source_to_wasm(code, "test_canvas.arx")
        self.assertEqual(wasm_bytes[:4], b"\x00asm")

    def test_wasm_string_literals_data_section(self):
        """Validates UTF-8 string literal encoding in linear memory data segments."""
        code = """
        fn main() {
            println("Aerix WebAssembly Native!");
        }
        """
        wat = self.compiler.compile_source_to_wat(code, "test_string.arx")
        self.assertIn('(data (i32.const 1024) "Aerix WebAssembly Native!")', wat)
        self.assertIn("call $print_str", wat)

        wasm_bytes = self.compiler.compile_source_to_wasm(code, "test_string.arx")
        # String literal should be embedded in binary data section
        self.assertIn(b"Aerix WebAssembly Native!", wasm_bytes)

    def test_compile_file_to_wasm_and_html_runner(self):
        """Validates end-to-end file compilation generating .wasm, .wat, and .html."""
        code = """
        fn main() {
            println("Browser Runner Online");
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = os.path.join(tmpdir, "app.arx")
            out_wasm = os.path.join(tmpdir, "app.wasm")
            out_wat = os.path.join(tmpdir, "app.wat")
            out_html = os.path.join(tmpdir, "app.html")

            with open(src_file, "w", encoding="utf-8") as f:
                f.write(code)

            res_wasm = self.compiler.compile_file_to_wasm(
                src_file,
                output_wasm_path=out_wasm,
                emit_html=True,
                emit_wat=True
            )

            self.assertTrue(os.path.exists(out_wasm))
            self.assertTrue(os.path.exists(out_wat))
            self.assertTrue(os.path.exists(out_html))

            with open(out_wasm, "rb") as f:
                header = f.read(8)
                self.assertEqual(header, b"\x00asm\x01\x00\x00\x00")

            with open(out_html, "r", encoding="utf-8") as f:
                html_text = f.read()
                self.assertIn("Aerix WebAssembly Browser Runtime", html_text)
                self.assertIn("app.wasm", html_text)
                self.assertIn("aerix-canvas", html_text)


if __name__ == "__main__":
    unittest.main()
