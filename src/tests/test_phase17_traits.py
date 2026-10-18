"""
Tests for Phase 17: Abstract Interface Traits & Trait Conformance
Validates trait parsing, compile-time trait conformance checking, multiple traits,
error diagnostics for missing/mismatched methods, and end-to-end native execution.
"""

import unittest
from src.frontend.lexer import Lexer
from src.frontend.parser import Parser
from src.middle.semantic import SemanticAnalyzer, SemanticError
from src.driver import AerixCompiler


class TestPhase17Traits(unittest.TestCase):
    def test_valid_trait_and_class_conformance(self):
        source = """
        trait Describable {
            fn describe() -> str
        }

        class Weapon implements Describable {
            pub name: str
            init(name: str) { self.name = name }
            pub fn describe() -> str {
                return "Weapon: {self.name}"
            }
        }
        """
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)
        self.assertIn("Describable", analyzer.traits)
        self.assertIn("Weapon", analyzer.classes)
        self.assertIn("Describable", analyzer.classes["Weapon"].traits)

    def test_multiple_traits_implementation(self):
        source = """
        trait Serializable {
            fn to_json() -> str
        }

        trait Auditable {
            fn get_audit_code() -> i64
        }

        class Account implements Serializable, Auditable {
            pub id: i64
            init(id: i64) { self.id = id }

            pub fn to_json() -> str {
                return "{\\"id\\": {self.id}}"
            }

            pub fn get_audit_code() -> i64 {
                return self.id * 1000
            }
        }
        """
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)
        self.assertEqual(analyzer.classes["Account"].traits, ["Serializable", "Auditable"])

    def test_missing_trait_method_error(self):
        source = """
        trait Playable {
            fn play() -> void
            fn pause() -> void
        }

        class AudioTrack implements Playable {
            pub fn play() -> void {
                println("Playing")
            }
            // Missing pause()!
        }
        """
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        analyzer = SemanticAnalyzer()
        with self.assertRaises(SemanticError) as ctx:
            analyzer.analyze(ast)
        self.assertIn("does not implement method 'pause", str(ctx.exception))

    def test_return_type_mismatch_error(self):
        source = """
        trait Measurable {
            fn get_length() -> f64
        }

        class Bridge implements Measurable {
            pub fn get_length() -> i64 { // Wrong return type: i64 instead of f64!
                return 500
            }
        }
        """
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        analyzer = SemanticAnalyzer()
        with self.assertRaises(SemanticError) as ctx:
            analyzer.analyze(ast)
        self.assertIn("returns 'i64', but trait 'Measurable' requires 'f64'", str(ctx.exception))

    def test_undefined_trait_error(self):
        source = """
        class Gadget implements NonExistentTrait {
            pub name: str
        }
        """
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        analyzer = SemanticAnalyzer()
        with self.assertRaises(SemanticError) as ctx:
            analyzer.analyze(ast)
        self.assertIn("implements undefined trait 'NonExistentTrait'", str(ctx.exception))

    def test_end_to_end_native_trait_compilation(self):
        compiler = AerixCompiler()
        source = """
        trait Formattable {
            fn format_info() -> str
        }

        class ServerNode implements Formattable {
            pub hostname: str
            pub port: i64

            init(host: str, port: i64) {
                self.hostname = host
                self.port = port
            }

            pub fn format_info() -> str {
                return "{self.hostname}:{self.port}"
            }
        }

        fn main() {
            let node = ServerNode("citadel.node.internal", 8080)
            let formatted = node.format_info()
            println("Server Address: {formatted}")
        }
        """
        c_code = compiler.compile_source_to_c(source)
        self.assertIn("Arx_ServerNode_format_info", c_code)


if __name__ == "__main__":
    unittest.main()
