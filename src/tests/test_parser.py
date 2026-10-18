"""
Aerix Compiler — Unit Tests for Pratt & Recursive Descent Parser
"""

import unittest
from src.frontend.lexer import Lexer
from src.frontend.parser import Parser
from src.frontend.ast_nodes import (
    ProgramNode, FunctionDefNode, VarDeclNode, IfNode, WhileNode,
    ForNode, BinaryOpNode, CallNode, PipelineNode, ClassDefNode,
    StringInterpNode, ReturnNode, DeferNode, LiteralNode
)


class TestParser(unittest.TestCase):
    def parse_code(self, code: str) -> ProgramNode:
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens, code.splitlines())
        return parser.parse()

    def test_operator_precedence(self):
        # 2 + 3 * 4 should be 2 + (3 * 4)
        ast = self.parse_code("let res = 2 + 3 * 4")
        decl = ast.declarations[0]
        self.assertIsInstance(decl, VarDeclNode)
        init = decl.initializer
        self.assertIsInstance(init, BinaryOpNode)
        self.assertEqual(init.op, "+")
        self.assertIsInstance(init.right, BinaryOpNode)
        self.assertEqual(init.right.op, "*")

    def test_pipeline_operator(self):
        code = "let x = 5 |> double() |> add_ten()"
        ast = self.parse_code(code)
        decl = ast.declarations[0]
        self.assertIsInstance(decl.initializer, PipelineNode)
        pipe2 = decl.initializer
        self.assertEqual(pipe2.right.callee.name, "add_ten")
        self.assertIsInstance(pipe2.left, PipelineNode)
        pipe1 = pipe2.left
        self.assertEqual(pipe1.right.callee.name, "double")

    def test_function_declarations(self):
        code = """
        fn add(a: i64, b: i64) -> i64 {
            return a + b
        }

        fn double(x: f64) -> f64 => x * 2.0
        """
        ast = self.parse_code(code)
        self.assertEqual(len(ast.declarations), 2)
        fn1 = ast.declarations[0]
        self.assertIsInstance(fn1, FunctionDefNode)
        self.assertEqual(fn1.name, "add")
        self.assertEqual(len(fn1.params), 2)
        self.assertEqual(fn1.return_type, "i64")

        fn2 = ast.declarations[1]
        self.assertIsInstance(fn2, FunctionDefNode)
        self.assertEqual(fn2.name, "double")
        self.assertEqual(fn2.return_type, "f64")

    def test_control_flow(self):
        code = """
        if x > 0 {
            println("Positive")
        } else {
            println("Non-positive")
        }

        while n > 0 {
            n -= 1
        }

        for i in 0..10 {
            println(i)
        }
        """
        ast = self.parse_code(code)
        self.assertEqual(len(ast.declarations), 3)
        self.assertIsInstance(ast.declarations[0], IfNode)
        self.assertIsInstance(ast.declarations[1], WhileNode)
        self.assertIsInstance(ast.declarations[2], ForNode)

    def test_defer_statement(self):
        code = """
        fn test() {
            let f = open()
            defer close(f)
        }
        """
        ast = self.parse_code(code)
        fn_node = ast.declarations[0]
        stmts = fn_node.body.statements
        self.assertEqual(len(stmts), 2)
        self.assertIsInstance(stmts[1], DeferNode)

    def test_oop_class(self):
        code = """
        class Hero extends Entity implements Drawable {
            pub name: str
            priv hp: f64

            init(name: str, hp: f64 = 100.0) {
                self.name = name
                self.hp = hp
            }

            pub fn take_damage(dmg: f64) {
                self.hp -= dmg
            }

            drop() {
                println("Hero dropped")
            }
        }
        """
        ast = self.parse_code(code)
        cls = ast.declarations[0]
        self.assertIsInstance(cls, ClassDefNode)
        self.assertEqual(cls.name, "Hero")
        self.assertEqual(cls.base_class, "Entity")
        self.assertEqual(cls.traits, ["Drawable"])
        self.assertEqual(len(cls.fields), 2)
        self.assertTrue(cls.fields[0].is_pub)
        self.assertFalse(cls.fields[1].is_pub)
        self.assertIsNotNone(cls.constructor)
        self.assertIsNotNone(cls.destructor)
        self.assertEqual(len(cls.methods), 1)

    def test_string_interpolation(self):
        code = 'let msg = "Hello {name}, your score is {score + 10}!"'
        ast = self.parse_code(code)
        decl = ast.declarations[0]
        self.assertIsInstance(decl.initializer, StringInterpNode)
        parts = decl.initializer.parts
        self.assertEqual(len(parts), 5)  # "Hello ", Node(name), ", your score is ", Node(score+10), "!"

    def test_multi_field_declaration_same_type(self):
        code = """
        class User {
            pub name: str, addr: str
            pub num1: i64, num2: i64
            priv x: f64, y: f64, z: f64
        }
        """
        ast = self.parse_code(code)
        cls = ast.declarations[0]
        self.assertEqual(len(cls.fields), 7)
        self.assertEqual([f.name for f in cls.fields], ["name", "addr", "num1", "num2", "x", "y", "z"])
        self.assertEqual([f.type_name for f in cls.fields], ["str", "str", "i64", "i64", "f64", "f64", "f64"])
        self.assertTrue(cls.fields[0].is_pub)
        self.assertTrue(cls.fields[1].is_pub)
        self.assertTrue(cls.fields[2].is_pub)
        self.assertTrue(cls.fields[3].is_pub)
        self.assertFalse(cls.fields[4].is_pub)
        self.assertFalse(cls.fields[5].is_pub)
        self.assertFalse(cls.fields[6].is_pub)

    def test_multi_field_declaration_mismatched_types_fails(self):
        code = """
        class User {
            pub name: str, age: i64
        }
        """
        from src.frontend.parser import ParserError
        with self.assertRaises(ParserError) as ctx:
            self.parse_code(code)
        self.assertIn("Multi-field declarations must be of the same type", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
