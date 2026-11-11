"""
Phase 27 Unit Tests: Bootstrap Stage 0 Prerequisites
Verifies OS/FS/Process/CLI-args runtime primitives, static class methods,
runtime str content equality/comparison & match, ByteBuffer string helpers,
str.byte_at / slice / to_i64, and eprintln stderr output.
"""

import os
import sys
import subprocess
import tempfile
import unittest

from src.driver import AerixCompiler
from src.middle.semantic import SemanticError


class TestPhase27BootstrapPrereqs(unittest.TestCase):
    def setUp(self):
        self.compiler = AerixCompiler()

    def _compile_and_run(self, code: str, cli_args=None):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "prog.arx")
            exe = os.path.join(tmpdir, "prog.exe")
            with open(src, "w", encoding="utf-8") as f:
                f.write(code)
            out_exe = self.compiler.compile_file(src, output_binary_path=exe)
            cmd = [out_exe] + (cli_args or [])
            return subprocess.run(cmd, capture_output=True, text=True)

    def test_static_methods_and_eprintln(self):
        code = """
        class Counter {
            pub static fn add_two(a: i64, b: i64) -> i64 {
                return a + b + 2
            }
            pub static fn greeting(name: str) -> str {
                return "hello " + name
            }
            pub static fn ping() -> i64 {
                return 42
            }
        }

        fn main() {
            println(Counter.add_two(10, 20))
            println(Counter.greeting("aerix"))
            println(Counter.ping())
            eprintln("err-line-1")
            eprintln(99)
        }
        """
        res = self._compile_and_run(code)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(res.stdout.strip().splitlines(), ["32", "hello aerix", "42"])
        self.assertEqual(res.stderr.strip().splitlines(), ["err-line-1", "99"])

    def test_instance_method_called_statically_rejected(self):
        code = """
        class Box {
            pub v: i64
            pub fn get() -> i64 {
                return self.v
            }
        }
        fn main() {
            println(Box.get())
        }
        """
        with self.assertRaises(SemanticError):
            self.compiler.compile_source_to_c(code)

    def test_str_content_equality_and_match(self):
        code = """
        fn classify(tok: str) -> str {
            match tok {
                "fn" => { return "KW_FN" }
                "let" => { return "KW_LET" }
                _ => { return "IDENT" }
            }
            return "NONE"
        }

        fn main() {
            let prefix = "hel"
            let s1 = prefix + "lo"
            let s2 = "hello"
            let s3 = "world"
            println(s1 == s2)
            println(s1 != s3)
            println(s1 == s3)
            println(s1 < s3)
            let kw = "f" + "n"
            let id_tok = "foo" + "bar"
            println(classify(kw))
            println(classify(id_tok))
        }
        """
        res = self._compile_and_run(code)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(
            res.stdout.strip().splitlines(),
            ["true", "true", "false", "true", "KW_FN", "IDENT"],
        )

    def test_byte_at_slice_and_bytebuffer(self):
        code = """
        fn main() {
            let src = "fn main() -> i64"
            println(src.byte_at(0))
            println(src.byte_at(1))
            println(src.slice(3, 7))
            let num_s = "1234"
            println(num_s.to_i64() + 6)

            let bb = ByteBuffer()
            bb.write_str("int x = ")
            bb.write_str("42;")
            let emitted = bb.to_str()
            println(emitted)
            println(emitted == "int x = 42;")
            bb.free()
        }
        """
        res = self._compile_and_run(code)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(
            res.stdout.strip().splitlines(),
            ["102", "110", "main", "1240", "int x = 42;", "true"],
        )

    def test_env_args_cwd_file_dir_process(self):
        with tempfile.TemporaryDirectory() as workdir:
            work_norm = workdir.replace("\\", "/")
            code = f"""
            fn main() {{
                let args = Env.args()
                println(args.len())
                println(args.get(1))
                println(args.get(2))

                let dpath = "{work_norm}/sub"
                println(Directory.create(dpath))
                println(Directory.exists(dpath))

                let fpath = "{work_norm}/sub/hello.txt"
                println(File.write_string(fpath, "line1\\n"))
                println(File.append_string(fpath, "line2"))
                println(File.exists(fpath))
                println(File.read_to_string(fpath) == "line1\\nline2")

                let files = Directory.list_files(dpath)
                println(files.len())
                println(files.get(0))

                let dirs = Directory.list_dirs("{work_norm}")
                println(dirs.len())
                println(dirs.get(0))

                let cpath = "{work_norm}/sub/copy.txt"
                println(File.copy(fpath, cpath))
                println(File.remove(cpath))
                println(File.exists(cpath))

                Env.set("ARX_BOOT_TEST", "ok_val")
                println(Env.get("ARX_BOOT_TEST"))
                println(Env.cwd().len() > 0)
                println(Env.os_name().len() > 0)

                let mut cmd = "echo proc_ok"
                let mut exit_cmd = "sh -c 'exit 7'"
                if Env.os_name() == "windows" {{
                    cmd = "cmd /c echo proc_ok"
                    exit_cmd = "cmd /c exit 7"
                }}
                let captured = Process.run_capture(cmd).trim()
                println(captured)
                let rc = Process.execute(exit_cmd)
                println(rc)
            }}
            """
            res = self._compile_and_run(code, cli_args=["--emit-c", "foo.arx"])
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(
                res.stdout.strip().splitlines(),
                [
                    "3",
                    "--emit-c",
                    "foo.arx",
                    "true",
                    "true",
                    "true",
                    "true",
                    "true",
                    "true",
                    "1",
                    "hello.txt",
                    "1",
                    "sub",
                    "true",
                    "true",
                    "false",
                    "ok_val",
                    "true",
                    "true",
                    "proc_ok",
                    "7",
                ],
            )


if __name__ == "__main__":
    unittest.main()
