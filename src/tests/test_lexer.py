"""
Aerix Compiler — Unit Tests for Lexer & Tokenizer
"""

import unittest
from src.frontend.tokens import TokenType
from src.frontend.lexer import Lexer, LexerError


class TestLexer(unittest.TestCase):
    def test_numbers(self):
        code = "42 3.1415 0xFF 0b1010"
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        
        self.assertEqual(tokens[0].type, TokenType.INT_LITERAL)
        self.assertEqual(tokens[0].value, 42)
        
        self.assertEqual(tokens[1].type, TokenType.FLOAT_LITERAL)
        self.assertAlmostEqual(tokens[1].value, 3.1415)
        
        self.assertEqual(tokens[2].type, TokenType.INT_LITERAL)
        self.assertEqual(tokens[2].value, 255)
        
        self.assertEqual(tokens[3].type, TokenType.INT_LITERAL)
        self.assertEqual(tokens[3].value, 10)

    def test_float_vs_range_disambiguation(self):
        # 0..10 should be INT(0), DOT_DOT, INT(10) — NOT FLOAT!
        code = "0..10 1..=5 3.14"
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        
        self.assertEqual(tokens[0].type, TokenType.INT_LITERAL)
        self.assertEqual(tokens[0].value, 0)
        self.assertEqual(tokens[1].type, TokenType.DOT_DOT)
        self.assertEqual(tokens[2].type, TokenType.INT_LITERAL)
        self.assertEqual(tokens[2].value, 10)
        
        self.assertEqual(tokens[3].type, TokenType.INT_LITERAL)
        self.assertEqual(tokens[3].value, 1)
        self.assertEqual(tokens[4].type, TokenType.DOT_DOT_EQ)
        self.assertEqual(tokens[5].type, TokenType.INT_LITERAL)
        self.assertEqual(tokens[5].value, 5)
        
        self.assertEqual(tokens[6].type, TokenType.FLOAT_LITERAL)
        self.assertAlmostEqual(tokens[6].value, 3.14)

    def test_aerix_special_operators(self):
        code = "|> -> => ?? ?. == !="
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        
        expected = [
            TokenType.PIPE,
            TokenType.ARROW,
            TokenType.FAT_ARROW,
            TokenType.QUESTION_QUESTION,
            TokenType.QUESTION_DOT,
            TokenType.EQ_EQ,
            TokenType.NOT_EQ,
            TokenType.EOF
        ]
        self.assertEqual([t.type for t in tokens], expected)

    def test_keywords_and_identifiers(self):
        code = "fn let mut class defer trait pub priv init drop"
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        
        expected = [
            TokenType.FN,
            TokenType.LET,
            TokenType.MUT,
            TokenType.CLASS,
            TokenType.DEFER,
            TokenType.TRAIT,
            TokenType.PUB,
            TokenType.PRIV,
            TokenType.INIT,
            TokenType.DROP,
            TokenType.EOF
        ]
        self.assertEqual([t.type for t in tokens], expected)

    def test_string_interpolation(self):
        code = '"Normal string" "Score is {score}!"'
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        
        self.assertEqual(tokens[0].type, TokenType.STRING_LITERAL)
        self.assertEqual(tokens[0].value, "Normal string")
        
        self.assertEqual(tokens[1].type, TokenType.STRING_INTERP)
        self.assertEqual(tokens[1].value, "Score is {score}!")

    def test_comments(self):
        code = """
        // Single line comment
        let x = 10 /* inline comment */
        /*
           Nested comment /* inside */ still in comment
        */
        let y = 20
        """
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        
        # Should cleanly see x = 10, y = 20
        types = [t.type for t in tokens if t.type != TokenType.NEWLINE and t.type != TokenType.EOF]
        self.assertEqual(types, [
            TokenType.LET, TokenType.IDENTIFIER, TokenType.EQUALS, TokenType.INT_LITERAL,
            TokenType.LET, TokenType.IDENTIFIER, TokenType.EQUALS, TokenType.INT_LITERAL
        ])

    def test_full_oop_class(self):
        code = """
        class Hero {
            pub name: str
            priv hp: f64

            init(name: str, hp: f64 = 100.0) {
                self.name = name
                self.hp = hp
            }

            pub fn take_damage(dmg: f64) {
                self.hp -= dmg
            }
        }
        """
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        self.assertEqual(tokens[0].type, TokenType.CLASS)
        self.assertEqual(tokens[1].value, "Hero")
        self.assertTrue(any(t.type == TokenType.INIT for t in tokens))
        self.assertTrue(any(t.type == TokenType.MINUS_EQ for t in tokens))


if __name__ == "__main__":
    unittest.main()
