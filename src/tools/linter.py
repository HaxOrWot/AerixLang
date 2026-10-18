"""
Aerix Code Linter (arx lint)
Detects unused variables, empty blocks, unreachable statements,
and code style inconsistencies with rich line/col diagnostics.
"""

from typing import List, Dict, Any, Optional
from src.frontend.lexer import Lexer
from src.frontend.tokens import TokenType
from src.frontend.parser import Parser
from src.frontend.ast_nodes import (
    ASTNode, ProgramNode, FunctionDefNode, BlockNode, VarDeclNode,
    ReturnNode, BreakNode, ContinueNode, ClassDefNode
)
from src.middle.semantic import SemanticAnalyzer


class LintWarning:
    def __init__(self, code: str, message: str, line: int, col: int, file: str, source_line: str = ""):
        self.code = code
        self.message = message
        self.line = line
        self.col = col
        self.file = file
        self.source_line = source_line

    def format(self) -> str:
        caret = " " * max(0, self.col - 1) + "^"
        return (
            f"\033[1;33m[AERIX LINT WARNING]\033[0m ({self.code}): {self.message}\n"
            f"  --> {self.file}:{self.line}:{self.col}\n"
            f"   |\n"
            f"{self.line:4d} | {self.source_line}\n"
            f"   | {caret}"
        )


class AerixLinter:
    def __init__(self):
        self.warnings: List[LintWarning] = []

    def lint_source(self, source: str, file_path: str = "<stdin>") -> List[LintWarning]:
        self.warnings = []
        source_lines = source.splitlines()

        # 1. Lexical checks: trailing semicolons
        lexer = Lexer(source, file_path)
        tokens = lexer.tokenize()

        for tok in tokens:
            if tok.type == TokenType.SEMICOLON:
                line_str = source_lines[tok.line - 1] if 0 < tok.line <= len(source_lines) else ""
                self.warnings.append(
                    LintWarning(
                        code="W001",
                        message="Unnecessary trailing semicolon. Aerix uses newline-delimited statements.",
                        line=tok.line,
                        col=tok.col,
                        file=file_path,
                        source_line=line_str
                    )
                )

        # 2. Parse & AST checks
        try:
            parser = Parser(tokens, source_lines)
            ast = parser.parse()
            from src.middle.monomorphizer import GenericMonomorphizer
            ast = GenericMonomorphizer().monomorphize(ast)
        except Exception:
            # If code doesn't parse, let compiler handle syntax errors
            return self.warnings

        # 3. Semantic analysis for unused variables
        try:
            analyzer = SemanticAnalyzer(file_path, source_lines)
            analyzer.analyze(ast)

            # Inspect defined symbols for unused variables
            for sym in analyzer.defined_symbols:
                if not sym.is_used and not sym.name.startswith("_") and sym.name != "self":
                    node = sym.node
                    line = getattr(node, "line", 1)
                    col = getattr(node, "col", 1)
                    line_str = source_lines[line - 1] if 0 < line <= len(source_lines) else ""
                    self.warnings.append(
                        LintWarning(
                            code="W002",
                            message=f"Variable '{sym.name}' is declared but never read. (Prefix with '_' to silence).",
                            line=line,
                            col=col,
                            file=file_path,
                            source_line=line_str
                        )
                    )

            # Traverse AST blocks to check dead code & empty blocks
            def walk_ast(node: ASTNode):
                if isinstance(node, BlockNode):
                    if len(node.statements) == 0:
                        line = node.line
                        col = node.col
                        line_str = source_lines[line - 1] if 0 < line <= len(source_lines) else ""
                        self.warnings.append(
                            LintWarning(
                                code="W003",
                                message="Empty block statement.",
                                line=line,
                                col=col,
                                file=file_path,
                                source_line=line_str
                            )
                        )
                    else:
                        for idx, s in enumerate(node.statements):
                            if isinstance(s, (ReturnNode, BreakNode, ContinueNode)) and idx < len(node.statements) - 1:
                                next_s = node.statements[idx + 1]
                                line = next_s.line
                                col = next_s.col
                                line_str = source_lines[line - 1] if 0 < line <= len(source_lines) else ""
                                self.warnings.append(
                                    LintWarning(
                                        code="W004",
                                        message="Unreachable code detected after terminating statement.",
                                        line=line,
                                        col=col,
                                        file=file_path,
                                        source_line=line_str
                                    )
                                )
                                break

                for child in getattr(node, "statements", []):
                    walk_ast(child)
                for decl in getattr(node, "declarations", []):
                    walk_ast(decl)
                if hasattr(node, "body") and isinstance(node.body, ASTNode):
                    walk_ast(node.body)

            walk_ast(ast)
        except Exception:
            pass

        return self.warnings

    def lint_file(self, file_path: str) -> List[LintWarning]:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        return self.lint_source(source, file_path)
