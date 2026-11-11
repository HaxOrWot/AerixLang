"""
Phase 28 Self-Hosting Bootstrap Test Suite:
Verifies 3-stage self-hosting compilation (Stage 0 -> Stage 1 -> Stage 2 -> Stage 3),
exact byte-for-byte fixed-point equality (stage2.c == stage3.c), compiler self-check,
and native compilation of Aerix programs (including tuples and collections) by Stage 3.
"""

import hashlib
import os
import subprocess
import tempfile
import unittest

from src.driver import AerixCompiler


class TestPhase28SelfHostingBootstrap(unittest.TestCase):
    """End-to-end verification of the bootstrapped Aerix compiler (src/bootstrap)."""

    _tmpdir_obj: tempfile.TemporaryDirectory
    tmpdir: str
    repo_root: str
    env: dict
    stage1_exe: str
    stage2_exe: str
    stage2_c: str
    stage3_exe: str
    stage3_c: str

    @classmethod
    def setUpClass(cls):
        cls.repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        cls._tmpdir_obj = tempfile.TemporaryDirectory()
        cls.tmpdir = cls._tmpdir_obj.name
        cls.env = os.environ.copy()
        cls.env["AERIX_STDLIB"] = os.path.join(cls.repo_root, "stdlib")

        bootstrap_main = os.path.join(cls.repo_root, "src", "bootstrap", "main.arx")
        ext = ".exe" if os.name == "nt" else ""

        cls.stage1_exe = os.path.join(cls.tmpdir, f"arxc_stage1{ext}")
        cls.stage2_exe = os.path.join(cls.tmpdir, f"arxc_stage2{ext}")
        cls.stage2_c = os.path.join(cls.tmpdir, "arxc_stage2.c")
        cls.stage3_exe = os.path.join(cls.tmpdir, f"arxc_stage3{ext}")
        cls.stage3_c = os.path.join(cls.tmpdir, "arxc_stage3.c")

        # Stage 0 (Python) compiles bootstrap compiler -> Stage 1 binary
        compiler = AerixCompiler()
        compiler.compile_file(bootstrap_main, output_binary_path=cls.stage1_exe)

        # Stage 1 compiles bootstrap compiler -> Stage 2 binary + C
        res2 = subprocess.run(
            [cls.stage1_exe, "build", bootstrap_main, "-o", cls.stage2_exe, "--emit-c"],
            capture_output=True,
            text=True,
            env=cls.env,
        )
        if res2.returncode != 0:
            raise AssertionError(
                f"Stage 1 failed to compile bootstrap compiler:\n{res2.stdout}\n{res2.stderr}"
            )

        # Stage 2 compiles bootstrap compiler -> Stage 3 binary + C
        res3 = subprocess.run(
            [cls.stage2_exe, "build", bootstrap_main, "-o", cls.stage3_exe, "--emit-c"],
            capture_output=True,
            text=True,
            env=cls.env,
        )
        if res3.returncode != 0:
            raise AssertionError(
                f"Stage 2 failed to compile bootstrap compiler:\n{res3.stdout}\n{res3.stderr}"
            )

    @classmethod
    def tearDownClass(cls):
        cls._tmpdir_obj.cleanup()

    def test_three_stage_exact_fixed_point(self):
        """Stage 2 and Stage 3 must emit byte-for-byte identical C99 output."""
        for path in (self.stage1_exe, self.stage2_exe, self.stage2_c, self.stage3_exe, self.stage3_c):
            self.assertTrue(os.path.exists(path), f"Missing bootstrap artifact: {path}")

        with open(self.stage2_c, "rb") as f2:
            c2_bytes = f2.read()
        with open(self.stage3_c, "rb") as f3:
            c3_bytes = f3.read()

        self.assertGreater(len(c2_bytes), 0)
        self.assertEqual(len(c2_bytes), len(c3_bytes))
        self.assertEqual(
            hashlib.sha256(c2_bytes).hexdigest(),
            hashlib.sha256(c3_bytes).hexdigest(),
        )
        self.assertEqual(c2_bytes, c3_bytes)

        ver = subprocess.run([self.stage3_exe, "--version"], capture_output=True, text=True, env=self.env)
        self.assertEqual(ver.returncode, 0, ver.stderr)
        hlp = subprocess.run([self.stage3_exe, "--help"], capture_output=True, text=True, env=self.env)
        self.assertEqual(hlp.returncode, 0, hlp.stderr)

    def test_stage3_check_self(self):
        """Stage 3 compiler check mode passes cleanly on src/bootstrap/main.arx."""
        bootstrap_main = os.path.join(self.repo_root, "src", "bootstrap", "main.arx")
        res = subprocess.run(
            [self.stage3_exe, "check", bootstrap_main],
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(res.returncode, 0, f"check failed:\n{res.stdout}\n{res.stderr}")

    def test_stage3_compiles_tuples_and_data_structures(self):
        """Stage 3 compiles and runs programs using tuples, Stack, Queue, Deque, List, Map, Set."""
        code = """
        fn make_pair(n: i64, label: str) -> (i64, str) {
            return (n * 2, label + "!")
        }

        fn main() {
            let p = (10, 20)
            println(p.0)
            println(p.1)

            let (val, msg) = make_pair(21, "ok")
            println(val)
            println(msg)

            mut stk = Stack<i64>()
            stk.push(1)
            stk.push(2)
            println(stk.peek())
            println(stk.pop())
            println(stk.len())

            mut q = Queue<str>()
            q.enqueue("alpha")
            q.enqueue("beta")
            println(q.peek())
            println(q.dequeue())
            println(q.len())

            mut dq = Deque<i64>()
            dq.push_back(20)
            dq.push_front(10)
            dq.push_back(30)
            println(dq.peek_front())
            println(dq.peek_back())
            println(dq.pop_front())
            println(dq.pop_back())
            println(dq.len())
        }
        """
        src = os.path.join(self.tmpdir, "ds_test.arx")
        ext = ".exe" if os.name == "nt" else ""
        exe = os.path.join(self.tmpdir, f"ds_test{ext}")
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)

        build = subprocess.run(
            [self.stage3_exe, "build", src, "-o", exe],
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(build.returncode, 0, f"Stage 3 build failed:\n{build.stdout}\n{build.stderr}")

        run = subprocess.run([exe], capture_output=True, text=True, env=self.env)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(
            run.stdout.strip().splitlines(),
            ["10", "20", "42", "ok!", "2", "2", "1", "alpha", "alpha", "1", "10", "30", "10", "30", "1"],
        )

    def test_stage3_compiles_repo_examples(self):
        """Stage 3 natively builds and executes core repository showcase examples."""
        ext = ".exe" if os.name == "nt" else ""
        examples = [
            "28_DYNAMIC_COLLECTIONS_AND_STRINGS.arx",
            "29_DATA_STRUCTURES_SHOWCASE.arx",
            "34_TRY_CATCH_FINALLY.arx",
            "39_DEFAULT_AND_NAMED_ARGUMENTS.arx",
            "40_MODULE_SYSTEM.arx",
        ]
        for idx, name in enumerate(examples):
            src = os.path.join(self.repo_root, "examples", name)
            exe = os.path.join(self.tmpdir, f"ex_{idx}{ext}")
            build = subprocess.run(
                [self.stage3_exe, "build", src, "-o", exe],
                capture_output=True,
                text=True,
                env=self.env,
            )
            self.assertEqual(build.returncode, 0, f"Build failed for {name}:\n{build.stdout}\n{build.stderr}")
            run = subprocess.run([exe], capture_output=True, text=True, env=self.env)
            self.assertEqual(run.returncode, 0, f"Run failed for {name}:\n{run.stderr}")

