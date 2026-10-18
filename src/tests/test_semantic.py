"""
Aerix Compiler — Unit Tests for Semantic Analyzer & Type Checker
"""

import unittest
from src.frontend.lexer import Lexer
from src.frontend.parser import Parser
from src.middle.semantic import SemanticAnalyzer, SemanticError


class TestSemanticAnalyzer(unittest.TestCase):
    def analyze_code(self, code: str):
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens, code.splitlines())
        ast = parser.parse()
        analyzer = SemanticAnalyzer("<test>", code.splitlines())
        analyzer.analyze(ast)
        return analyzer

    def test_immutability_enforcement(self):
        # Reassigning a 'let' variable MUST raise SemanticError
        bad_code = """
        fn main() {
            let x = 10
            x = 20
        }
        """
        with self.assertRaises(SemanticError) as ctx:
            self.analyze_code(bad_code)
        self.assertIn("Cannot reassign immutable variable 'x'", str(ctx.exception))

        # Reassigning a 'mut' variable MUST succeed
        good_code = """
        fn main() {
            mut x = 10
            x = 20
        }
        """
        analyzer = self.analyze_code(good_code)
        self.assertIsNotNone(analyzer)

    def test_type_mismatch(self):
        # Assigning string to i64 MUST raise SemanticError
        bad_code = """
        fn main() {
            let num: i64 = "this is not an integer"
        }
        """
        with self.assertRaises(SemanticError) as ctx:
            self.analyze_code(bad_code)
        self.assertIn("Type mismatch", str(ctx.exception))

    def test_return_type_mismatch(self):
        # Returning string when expecting i64
        bad_code = """
        fn compute() -> i64 {
            return "string"
        }
        """
        with self.assertRaises(SemanticError) as ctx:
            self.analyze_code(bad_code)
        self.assertIn("expects return type 'i64'", str(ctx.exception))

    def test_oop_privacy_enforcement(self):
        # Accessing private field outside class MUST raise SemanticError
        bad_code = """
        class Hero {
            pub name: str
            priv secret_code: i64

            init(name: str) {
                self.name = name
                self.secret_code = 1234
            }
        }

        fn main() {
            let h = Hero("Arthur")
            println(h.secret_code)
        }
        """
        with self.assertRaises(SemanticError) as ctx:
            self.analyze_code(bad_code)
        self.assertIn("Cannot access private field 'secret_code'", str(ctx.exception))

    def test_oop_public_access_succeeds(self):
        # Accessing public field MUST succeed
        good_code = """
        class Hero {
            pub name: str

            init(name: str) {
                self.name = name
            }
        }

        fn main() {
            let h = Hero("Arthur")
            println(h.name)
        }
        """
        analyzer = self.analyze_code(good_code)
        self.assertIsNotNone(analyzer)


if __name__ == "__main__":
    unittest.main()
