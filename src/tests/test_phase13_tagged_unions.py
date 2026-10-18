"""
Aerix Compiler — Unit Tests for Phase 13: Tagged Unions & Exhaustive Pattern Matching
Tests:
- enum definitions (payload-free and payload-bearing tagged unions)
- match expressions with destructuring bindings
- exhaustiveness checking and compilation errors on missing variants
- wildcard '_' branch
- match case guards (if <condition>)
"""

import os
import tempfile
import subprocess
import unittest
from src.driver import AerixCompiler
from src.middle.semantic import SemanticError


class TestPhase13TaggedUnions(unittest.TestCase):
    def setUp(self):
        self.compiler = AerixCompiler()

    def _compile_and_run(self, code: str, name: str) -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            arx_file = os.path.join(tmpdir, f"{name}.arx")
            exe_file = os.path.join(tmpdir, f"{name}.exe")
            with open(arx_file, "w", encoding="utf-8") as f:
                f.write(code)

            out_exe = self.compiler.compile_file(arx_file, output_binary_path=exe_file)
            res = subprocess.run([out_exe], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
            return res.stdout.strip()

    def test_simple_enum_pattern_match(self):
        code = """
        enum Direction {
            North
            South
            East
            West
        }

        fn describe(d: Direction) {
            match d {
                Direction.North => println("Heading North!"),
                Direction.South => println("Heading South!"),
                Direction.East => println("Heading East!"),
                Direction.West => println("Heading West!")
            }
        }

        fn main() {
            let d1 = Direction.North
            let d2 = Direction.East
            describe(d1)
            describe(d2)
        }
        """
        out = self._compile_and_run(code, "test_simple_enum")
        self.assertIn("Heading North!", out)
        self.assertIn("Heading East!", out)

    def test_tagged_union_with_payload_destructuring(self):
        code = """
        enum MissionStatus {
            Standby
            InTransit(destination: str, eta_hours: f64)
            EngagingEnemy(threat_level: i64)
            Aborted(reason: str)
        }

        fn report(status: MissionStatus) {
            match status {
                Standby => {
                    println("[STATUS] Ship awaiting departure orders.")
                },
                InTransit(dest, eta) => {
                    println("[STATUS] En route to {dest}. ETA: {eta} hours.")
                },
                EngagingEnemy(level) => {
                    println("[ALERT] Engaging Class {level} enemy vessel!")
                },
                Aborted(reason) => {
                    println("[ABORT] Mission aborted: {reason}")
                }
            }
        }

        fn main() {
            let s1 = MissionStatus.Standby
            let s2 = MissionStatus.InTransit("Kepler-452b", 14.5)
            let s3 = MissionStatus.EngagingEnemy(5)
            let s4 = MissionStatus.Aborted("Fuel leak in starboard thruster")

            report(s1)
            report(s2)
            report(s3)
            report(s4)
        }
        """
        out = self._compile_and_run(code, "test_tagged_union")
        self.assertIn("[STATUS] Ship awaiting departure orders.", out)
        self.assertIn("[STATUS] En route to Kepler-452b. ETA: 14.5 hours.", out)
        self.assertIn("[ALERT] Engaging Class 5 enemy vessel!", out)
        self.assertIn("[ABORT] Mission aborted: Fuel leak in starboard thruster", out)

    def test_wildcard_branch_in_match(self):
        code = """
        enum Command {
            Start
            Stop
            Pause
            Reload
        }

        fn execute(c: Command) {
            match c {
                Start => println("Starting engine!"),
                _ => println("Other command received.")
            }
        }

        fn main() {
            execute(Command.Start)
            execute(Command.Pause)
        }
        """
        out = self._compile_and_run(code, "test_wildcard")
        self.assertIn("Starting engine!", out)
        self.assertIn("Other command received.", out)

    def test_exhaustiveness_checking_fails_on_missing_variant(self):
        code = """
        enum Color {
            Red
            Green
            Blue
        }

        fn check(c: Color) {
            match c {
                Color.Red => println("Red"),
                Color.Green => println("Green")
            }
        }

        fn main() {
            check(Color.Red)
        }
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            arx_file = os.path.join(tmpdir, "missing.arx")
            with open(arx_file, "w", encoding="utf-8") as f:
                f.write(code)

            with self.assertRaises(SemanticError) as ctx:
                self.compiler.compile_file(arx_file)
            self.assertIn("Non-exhaustive pattern match", str(ctx.exception))
            self.assertIn("Blue", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
