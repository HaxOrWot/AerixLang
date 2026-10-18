"""
Aerix Compiler — Unit Tests for Phase 12: Modern Ergonomics & Unique Flow Control
Tests:
- guard ... else early exit statements
- ~> fluent cascade mutation operator
- extend <Type> { ... } type extension methods
"""

import os
import tempfile
import subprocess
import unittest
from src.driver import AerixCompiler


class TestPhase12Ergonomics(unittest.TestCase):
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

    def test_guard_statement(self):
        code = """
        fn process_age(age: i64) -> i64 {
            guard age >= 18 else {
                println("Blocked: Minor")
                return 0
            }
            println("Allowed: Adult")
            return age * 2
        }

        fn main() {
            let r1 = process_age(15)
            let r2 = process_age(20)
            println("R1: {r1}")
            println("R2: {r2}")
        }
        """
        out = self._compile_and_run(code, "test_guard")
        self.assertIn("Blocked: Minor", out)
        self.assertIn("R1: 0", out)
        self.assertIn("Allowed: Adult", out)
        self.assertIn("R2: 40", out)

    def test_fluent_cascade_mutation(self):
        code = """
        class Character {
            pub name: str
            pub hp: i64
            pub xp: i64

            init(name: str, hp: i64) {
                self.name = name
                self.hp = hp
                self.xp = 0
            }

            pub fn take_damage(dmg: i64) {
                self.hp -= dmg
            }

            pub fn heal(amount: i64) {
                self.hp += amount
            }

            pub fn add_xp(points: i64) {
                self.xp += points
            }

            pub fn status() {
                println("{self.name}: HP={self.hp}, XP={self.xp}")
            }
        }

        fn main() {
            mut hero = Character("Aiden", 100)
            hero ~> take_damage(30) ~> heal(10) ~> add_xp(50)
            hero.status()
        }
        """
        out = self._compile_and_run(code, "test_cascade")
        self.assertIn("Aiden: HP=80, XP=50", out)

    def test_type_extension(self):
        code = """
        class Counter {
            pub count: i64

            init(c: i64) {
                self.count = c
            }

            pub fn get_count() -> i64 {
                return self.count
            }
        }

        extend Counter {
            pub fn increment(by: i64) {
                self.count += by
            }

            pub fn doubled() -> i64 {
                return self.count * 2
            }
        }

        fn main() {
            mut c = Counter(10)
            c.increment(5)
            let d = c.doubled()
            println("Count: {c.get_count()}, Doubled: {d}")
        }
        """
        out = self._compile_and_run(code, "test_extension")
        self.assertIn("Count: 15, Doubled: 30", out)

    def test_combined_ergonomics(self):
        code = """
        class Player {
            pub tag: str
            pub score: i64
            pub is_banned: bool

            init(tag: str) {
                self.tag = tag
                self.score = 0
                self.is_banned = false
            }

            pub fn add_score(pts: i64) {
                self.score += pts
            }

            pub fn ban() {
                self.is_banned = true
            }
        }

        extend Player {
            pub fn try_reward(pts: i64) {
                guard !self.is_banned else {
                    println("Cannot reward banned player {self.tag}")
                    return
                }
                self.score += pts
                println("Rewarded {self.tag}: +{pts} (Total: {self.score})")
            }
        }

        fn main() {
            mut p1 = Player("Viper")
            p1 ~> add_score(100) ~> try_reward(50)

            mut p2 = Player("Cheater")
            p2 ~> ban() ~> try_reward(500)
        }
        """
        out = self._compile_and_run(code, "test_combined")
        self.assertIn("Rewarded Viper: +50 (Total: 150)", out)
        self.assertIn("Cannot reward banned player Cheater", out)


if __name__ == "__main__":
    unittest.main()
