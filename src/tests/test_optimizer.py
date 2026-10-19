"""
Aerix Compiler — Unit Tests for AIR Lowering & Custom Optimizer (arxc-opt)
"""

import unittest
from src.frontend.lexer import Lexer
from src.frontend.parser import Parser
from src.middle.air import AIRLowering, AIRConst, AIRReturn
from src.middle.optimizer import AIROptimizer


class TestAIROptimizer(unittest.TestCase):
    def lower_code(self, code: str):
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens, code.splitlines())
        ast = parser.parse()
        lowering = AIRLowering()
        return lowering.lower(ast)

    def test_ast_to_air_lowering(self):
        code = """
        fn calculate(a: i64, b: i64) -> i64 {
            let sum = a + b
            return sum
        }
        """
        module = self.lower_code(code)
        self.assertIn("calculate", module.functions)
        fn = module.functions["calculate"]
        self.assertEqual(fn.params, ["a", "b"])
        self.assertEqual(fn.return_type, "i64")
        self.assertTrue(any(isinstance(i, AIRReturn) for i in fn.instructions))

    def test_constant_folding(self):
        # 10 + 20 should be folded into constant 30 by arxc-opt
        code = """
        fn math_test() -> i64 {
            let res = 10 + 20
            return res
        }
        """
        module = self.lower_code(code)
        optimizer = AIROptimizer()
        opt_module = optimizer.optimize(module)
        fn = opt_module.functions["math_test"]

        # Look for the folded constant 30!
        folded_constants = [i.value for i in fn.instructions if isinstance(i, AIRConst)]
        self.assertIn(30, folded_constants)

    def test_dead_code_elimination(self):
        # Instructions placed after an unconditional return must be eliminated!
        code = """
        fn dead_code_test() -> i64 {
            return 42
            let dead_val = 100 // Unreachable!
        }
        """
        module = self.lower_code(code)
        optimizer = AIROptimizer()
        opt_module = optimizer.optimize(module)
        fn = opt_module.functions["dead_code_test"]

        # The last instruction before EOF should be the return 42
        last_insn = fn.instructions[-1]
        self.assertIsInstance(last_insn, AIRReturn)
        # Should NOT contain any instruction for dead_val 100
        const_vals = [i.value for i in fn.instructions if isinstance(i, AIRConst)]
        self.assertNotIn(100, const_vals)

    def test_algebraic_simplifications(self):
        # x * 0 should be simplified to constant 0
        code = """
        fn identity_test(x: i64) -> i64 {
            let zero = x * 0
            return zero
        }
        """
        module = self.lower_code(code)
        opt_module = AIROptimizer().optimize(module)
        fn = opt_module.functions["identity_test"]
        const_vals = [i.value for i in fn.instructions if isinstance(i, AIRConst)]
        self.assertIn(0, const_vals)

    def test_comparison_folding(self):
        # 10 > 5 should fold into True (bool)
        code = """
        fn cmp_test() -> bool {
            let b = 10 > 5
            return b
        }
        """
        module = self.lower_code(code)
        opt_module = AIROptimizer().optimize(module)
        fn = opt_module.functions["cmp_test"]
        const_vals = [i.value for i in fn.instructions if isinstance(i, AIRConst)]
        self.assertIn(True, const_vals)


if __name__ == "__main__":
    unittest.main()
