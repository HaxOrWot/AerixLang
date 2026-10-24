"""
Aerix Compiler (arxc) — Pratt & Recursive Descent Parser
Transforms a token stream into an Abstract Syntax Tree (AST).
Supports procedural scripting, OOP classes, traits, pipelines (|>), and defer.
"""

from enum import IntEnum
from typing import List, Optional, Callable, Dict, Set, Tuple
from src.frontend.tokens import Token, TokenType
from src.frontend.diagnostics import AerixDiagnostic, DiagnosticBag, ParserError, format_source_snippet
from src.frontend.ast_nodes import (
    ASTNode, ProgramNode, FunctionDefNode, ParamNode, BlockNode,
    VarDeclNode, AssignNode, IfNode, WhileNode, ForNode, LoopNode,
    BreakNode, ContinueNode, ReturnNode, DeferNode, ExprStmtNode,
    LiteralNode, IdentifierNode, BinaryOpNode, UnaryOpNode, CallNode,
    MemberAccessNode, IndexAccessNode, PipelineNode, RangeNode,
    NewNode, CastNode, StringInterpNode, ClassDefNode, ClassFieldNode,
    ConstructorDefNode, DestructorDefNode, TraitDefNode, TraitMethodNode,
    CIncludeNode, CExternNode, PropertyDefNode, OperatorDefNode,
    CascadeNode, GuardNode, ExtendDefNode,
    EnumVariantNode, EnumDefNode, MatchCaseNode, MatchNode, SpawnNode,
    TupleNode, TupleDestructureNode, FixedArrayLiteralNode, SizeofNode
)


class Precedence(IntEnum):
    NONE = 0
    ASSIGN = 1          # =, +=, -=, *=, /=
    PIPELINE = 2        # |>
    NULL_COALESCE = 3   # ??
    LOGICAL_OR = 4      # ||
    LOGICAL_AND = 5     # &&
    EQUALITY = 6        # ==, !=
    COMPARISON = 7      # <, <=, >, >=
    RANGE = 8           # .., ..=
    TERM = 9            # +, -
    FACTOR = 10         # *, /, %
    POWER = 11          # **
    UNARY = 12          # !, -, ~, &, *
    CALL = 13           # (), [], ., ?.
    PRIMARY = 14


# Operator token to precedence mapping
PRECEDENCES: Dict[TokenType, Precedence] = {
    TokenType.PIPE: Precedence.PIPELINE,
    TokenType.CASCADE: Precedence.PIPELINE,
    TokenType.QUESTION_QUESTION: Precedence.NULL_COALESCE,
    TokenType.OR_OR: Precedence.LOGICAL_OR,
    TokenType.AND_AND: Precedence.LOGICAL_AND,
    TokenType.EQ_EQ: Precedence.EQUALITY,
    TokenType.NOT_EQ: Precedence.EQUALITY,
    TokenType.LT: Precedence.COMPARISON,
    TokenType.LTE: Precedence.COMPARISON,
    TokenType.GT: Precedence.COMPARISON,
    TokenType.GTE: Precedence.COMPARISON,
    TokenType.DOT_DOT: Precedence.RANGE,
    TokenType.DOT_DOT_EQ: Precedence.RANGE,
    TokenType.PLUS: Precedence.TERM,
    TokenType.MINUS: Precedence.TERM,
    TokenType.STAR: Precedence.FACTOR,
    TokenType.SLASH: Precedence.FACTOR,
    TokenType.PERCENT: Precedence.FACTOR,
    TokenType.POWER: Precedence.POWER,
    TokenType.LPAREN: Precedence.CALL,
    TokenType.LBRACKET: Precedence.CALL,
    TokenType.DOT: Precedence.CALL,
    TokenType.AS: Precedence.CALL,
}


class Parser:
    def __init__(self, tokens: List[Token], source_lines: Optional[List[str]] = None, filename: str = "<stdin>"):
        self.tokens = tokens
        self.pos = 0
        self.source_lines = source_lines or []
        self.filename = filename
        self.errors: List[ParserError] = []
        self.generic_uses: Set[Tuple[str, Tuple[str, ...]]] = set()
        
        # Pratt Parsing rule tables
        self.prefix_parselets: Dict[TokenType, Callable[[], ASTNode]] = {
            TokenType.INT_LITERAL: self.parse_int_literal,
            TokenType.FLOAT_LITERAL: self.parse_float_literal,
            TokenType.STRING_LITERAL: self.parse_string_literal,
            TokenType.STRING_INTERP: self.parse_string_interp,
            TokenType.CHAR_LITERAL: self.parse_char_literal,
            TokenType.BOOL_LITERAL: self.parse_bool_literal,
            TokenType.NULL: self.parse_null_literal,
            TokenType.IDENTIFIER: self.parse_identifier,
            TokenType.SELF: self.parse_identifier,
            TokenType.SUPER: self.parse_identifier,
            TokenType.MINUS: self.parse_unary,
            TokenType.NOT: self.parse_unary,
            TokenType.TILDE: self.parse_unary,
            TokenType.AMPERSAND: self.parse_unary,
            TokenType.LPAREN: self.parse_grouped_expr,
            TokenType.NEW: self.parse_new_expr,
            TokenType.SPAWN: self.parse_spawn_expr,
            TokenType.LBRACKET: self.parse_fixed_array_literal,  # Phase 23
            TokenType.SIZEOF: self.parse_sizeof,                 # Phase 24
            TokenType.LOOP: self.parse_loop_ident,
        }

        self.infix_parselets: Dict[TokenType, Callable[[ASTNode], ASTNode]] = {
            TokenType.PLUS: self.parse_binary,
            TokenType.MINUS: self.parse_binary,
            TokenType.STAR: self.parse_binary,
            TokenType.SLASH: self.parse_binary,
            TokenType.PERCENT: self.parse_binary,
            TokenType.POWER: self.parse_binary,
            TokenType.EQ_EQ: self.parse_binary,
            TokenType.NOT_EQ: self.parse_binary,
            TokenType.LT: self.parse_binary,
            TokenType.LTE: self.parse_binary,
            TokenType.GT: self.parse_binary,
            TokenType.GTE: self.parse_binary,
            TokenType.AND_AND: self.parse_binary,
            TokenType.OR_OR: self.parse_binary,
            TokenType.QUESTION_QUESTION: self.parse_binary,
            TokenType.PIPE: self.parse_pipeline,
            TokenType.CASCADE: self.parse_cascade,
            TokenType.DOT_DOT: self.parse_range,
            TokenType.DOT_DOT_EQ: self.parse_range,
            TokenType.LPAREN: self.parse_call,
            TokenType.LBRACKET: self.parse_index_access,
            TokenType.DOT: self.parse_member_access,
            TokenType.AS: self.parse_cast,
        }

    def error(self, msg: str, token: Optional[Token] = None, hint: Optional[str] = None) -> None:
        err_tok = token or self.current()
        line_str = self.source_lines[err_tok.line - 1] if 0 < err_tok.line <= len(self.source_lines) else ""
        raise ParserError(msg, err_tok, line_str, hint=hint)

    def synchronize(self) -> None:
        """Discards tokens until reaching a synchronization boundary (statement/declaration starter or terminator)."""
        SYNC_STARTERS = {
            TokenType.FN, TokenType.LET, TokenType.MUT, TokenType.CONST,
            TokenType.IF, TokenType.WHILE, TokenType.FOR, TokenType.LOOP,
            TokenType.RETURN, TokenType.DEFER, TokenType.BREAK, TokenType.CONTINUE,
            TokenType.GUARD, TokenType.MATCH, TokenType.CLASS, TokenType.ENUM,
            TokenType.EXTEND, TokenType.TRAIT, TokenType.PUB, TokenType.PRIV,
            TokenType.CINCLUDE, TokenType.CEXTERN, TokenType.RBRACE
        }

        # Advance at least once if not at EOF
        if self.current().type != TokenType.EOF:
            self.advance()

        while self.current().type != TokenType.EOF:
            # Did previous token end a statement?
            prev_tok = self.tokens[self.pos - 1] if self.pos > 0 else None
            if prev_tok and prev_tok.type in (TokenType.SEMICOLON, TokenType.NEWLINE):
                return

            # Does current token start a new construct or close a block?
            if self.current().type in SYNC_STARTERS:
                return

            self.advance()

    def current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]

    def peek(self, offset: int = 1) -> Token:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]

    def advance(self) -> Token:
        tok = self.current()
        if tok.type != TokenType.EOF:
            self.pos += 1
        return tok

    def match(self, expected: TokenType) -> bool:
        if self.current().type == expected:
            self.advance()
            return True
        return False

    def consume(self, expected: TokenType, msg: str) -> Token:
        if self.current().type == expected:
            return self.advance()
        self.error(msg)
        return self.current()

    def skip_newlines(self) -> None:
        while self.current().type == TokenType.NEWLINE:
            self.advance()

    def current_precedence(self) -> Precedence:
        if self.current().type == TokenType.NEWLINE:
            idx = self.pos
            while idx < len(self.tokens) and self.tokens[idx].type == TokenType.NEWLINE:
                idx += 1
            if idx < len(self.tokens):
                next_tok = self.tokens[idx]
                if next_tok.type in (TokenType.PIPE, TokenType.CASCADE, TokenType.DOT, TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH):
                    self.pos = idx
                    return PRECEDENCES.get(next_tok.type, Precedence.NONE)
        return PRECEDENCES.get(self.current().type, Precedence.NONE)

    # ==========================================
    # Top-Level Program & Declarations
    # ==========================================

    def record_generic_use(self, template_name: str, type_args: List[str]) -> None:
        self.generic_uses.add((template_name, tuple(type_args)))

    def parse(self) -> ProgramNode:
        decls = []
        self.skip_newlines()
        
        while self.current().type != TokenType.EOF:
            try:
                decl = self.parse_top_level_declaration()
                if decl:
                    decls.append(decl)
            except ParserError as pe:
                self.errors.append(pe)
                if len(self.errors) >= 25:
                    break
                self.synchronize()

            while self.match(TokenType.SEMICOLON):
                pass
            self.skip_newlines()

        if self.errors:
            if len(self.errors) == 1:
                raise self.errors[0]
            raise DiagnosticBag(self.errors, self.filename)
            
        first_tok = self.tokens[0] if self.tokens else Token(TokenType.EOF, None, 1, 1)
        return ProgramNode(line=first_tok.line, col=first_tok.col, declarations=decls, generic_uses=set(self.generic_uses))

    def parse_top_level_declaration(self) -> ASTNode:
        # Phase 24: Parse attributes #[packed], #[align(N)]
        attributes = []
        while self.current().type == TokenType.HASH:
            self.advance()  # consume '#'
            self.consume(TokenType.LBRACKET, "Expected '[' after '#' for attribute")
            while True:
                attr_name_tok = self.consume(TokenType.IDENTIFIER, "Expected attribute name")
                attr_arg = None
                if self.match(TokenType.LPAREN):
                    if self.current().type == TokenType.INT_LITERAL:
                        attr_arg = int(self.advance().value)
                    elif self.current().type == TokenType.IDENTIFIER:
                        attr_arg = self.advance().value
                    self.consume(TokenType.RPAREN, "Expected ')' after attribute argument")
                attributes.append((attr_name_tok.value, attr_arg))
                if not self.match(TokenType.COMMA):
                    break
            self.consume(TokenType.RBRACKET, "Expected ']' to close attribute")
            self.skip_newlines()

        tok = self.current()
        is_packed = any(name == "packed" for name, _ in attributes)
        alignment = None
        for name, arg in attributes:
            if name == "align":
                alignment = int(arg) if arg is not None else 64

        if tok.type == TokenType.CINCLUDE:
            return self.parse_cinclude()
        elif tok.type == TokenType.CEXTERN:
            return self.parse_cextern()
        elif tok.type in (TokenType.PUB, TokenType.FN):
            if tok.type == TokenType.PUB and self.peek().type == TokenType.CLASS:
                self.advance() # consume pub
                return self.parse_class_def(is_packed=is_packed, alignment=alignment)
            return self.parse_function_def()
        elif tok.type == TokenType.CLASS:
            return self.parse_class_def(is_packed=is_packed, alignment=alignment)
        elif tok.type == TokenType.ENUM:
            return self.parse_enum_def()
        elif tok.type == TokenType.EXTEND:
            return self.parse_extend_def()
        elif tok.type == TokenType.TRAIT:
            return self.parse_trait_def()

        else:
            return self.parse_statement()

    def parse_cinclude(self) -> CIncludeNode:
        tok = self.advance() # consume cinclude
        header_tok = self.consume(TokenType.STRING_LITERAL, "Expected header string after 'cinclude'")
        return CIncludeNode(line=tok.line, col=tok.col, header=header_tok.value)

    def parse_cextern(self) -> CExternNode:
        tok = self.advance() # consume cextern
        func_def = self.parse_function_def(is_extern=True)
        return CExternNode(line=tok.line, col=tok.col, func_def=func_def)

    def parse_function_def(self, is_extern: bool = False, is_static: bool = False, is_virtual: bool = False, is_override: bool = False, is_pub: Optional[bool] = None) -> FunctionDefNode:
        start_tok = self.current()
        
        if self.match(TokenType.PUB):
            is_pub = True
        elif self.match(TokenType.PRIV):
            is_pub = False
        elif is_pub is None:
            is_pub = True
            
        self.consume(TokenType.FN, "Expected 'fn' keyword")
        if self.current().type == TokenType.LOOP:
            name_tok = self.advance()
        else:
            name_tok = self.consume(TokenType.IDENTIFIER, "Expected function name")
        
        # Generic Type Parameters: fn identity<T>(x: T) -> T
        type_params = []
        if self.match(TokenType.LT):
            while True:
                type_params.append(self.consume(TokenType.IDENTIFIER, "Expected generic type parameter").value)
                if not self.match(TokenType.COMMA):
                    break
            self.consume(TokenType.GT, "Expected '>' to close generic type parameters")

        # Parameters
        self.consume(TokenType.LPAREN, "Expected '(' after function name")
        params = self.parse_parameter_list()
        self.consume(TokenType.RPAREN, "Expected ')' after parameters")
        
        # Optional return type
        return_type = "void"
        if self.match(TokenType.ARROW):
            return_type = self.parse_type_annotation()
            
        # Body
        if is_extern:
            body = BlockNode(line=start_tok.line, col=start_tok.col, statements=[])
        elif self.match(TokenType.FAT_ARROW):
            # Single-expression body (fn foo() -> i32 => expr)
            expr = self.parse_expression()
            ret_stmt = ReturnNode(line=expr.line, col=expr.col, value=expr)
            body = BlockNode(line=start_tok.line, col=start_tok.col, statements=[ret_stmt])
        else:
            body = self.parse_block()
            
        return FunctionDefNode(
            line=start_tok.line, col=start_tok.col,
            name=name_tok.value, params=params, return_type=return_type,
            body=body, is_pub=is_pub, is_static=is_static,
            is_virtual=is_virtual, is_override=is_override,
            type_params=type_params
        )

    def parse_parameter_list(self) -> List[ParamNode]:
        params = []
        if self.current().type == TokenType.RPAREN:
            return params
            
        while True:
            param_tok = self.consume(TokenType.IDENTIFIER, "Expected parameter name")
            self.consume(TokenType.COLON, "Expected ':' after parameter name")
            param_type = self.parse_type_annotation()
            
            default_val = None
            if self.match(TokenType.EQUALS):
                default_val = self.parse_expression()
                
            params.append(ParamNode(line=param_tok.line, col=param_tok.col, name=param_tok.value, type_name=param_type, default_val=default_val))
            
            if not self.match(TokenType.COMMA):
                break
        return params

    def parse_type_annotation(self) -> str:
        tok = self.current()
        # Phase 23: Fixed-size array type [T; N]
        if tok.type == TokenType.LBRACKET:
            self.advance()  # consume '['
            elem_type = self.parse_type_annotation()
            self.consume(TokenType.SEMICOLON, "Expected ';' in fixed array type '[T; N]'")
            size_tok = self.consume(TokenType.INT_LITERAL, "Expected integer size in fixed array type '[T; N]'")
            size = int(size_tok.value)
            self.consume(TokenType.RBRACKET, "Expected ']' to close fixed array type")
            return f"FixedArray_{elem_type}_{size}"
        if tok.type == TokenType.LPAREN:
            self.advance() # consume '('
            elem_types = []
            while True:
                elem_types.append(self.parse_type_annotation())
                if not self.match(TokenType.COMMA):
                    break
            self.consume(TokenType.RPAREN, "Expected ')' after tuple type annotation")
            tuple_t = f"Tuple_{'_'.join(elem_types)}"
            self.record_generic_use("Tuple", elem_types)
            return tuple_t
        if tok.type in (TokenType.IDENTIFIER, TokenType.FN):
            base_type = self.advance().value
            if self.match(TokenType.LT):
                type_args = []
                while True:
                    type_args.append(self.parse_type_annotation())
                    if not self.match(TokenType.COMMA):
                        break
                self.consume(TokenType.GT, "Expected '>' to close generic type arguments")
                self.record_generic_use(base_type, type_args)
                base_type = f"{base_type}_{'_'.join(type_args)}"
            if self.match(TokenType.QUESTION):
                return f"{base_type}?"
            return base_type
        self.error(f"Expected type identifier, found '{tok.value}'")
        return "void"

    # ==========================================
    # OOP Class & Trait Declarations
    # ==========================================

    def parse_class_def(self, is_packed: bool = False, alignment: Optional[int] = None) -> ClassDefNode:
        start_tok = self.consume(TokenType.CLASS, "Expected 'class'")
        name_tok = self.consume(TokenType.IDENTIFIER, "Expected class name")

        # Generic Type Parameters: class Box<T> { ... }
        type_params = []
        if self.match(TokenType.LT):
            while True:
                type_params.append(self.consume(TokenType.IDENTIFIER, "Expected generic type parameter").value)
                if not self.match(TokenType.COMMA):
                    break
            self.consume(TokenType.GT, "Expected '>' to close generic type parameters")
        
        base_class = None
        if self.match(TokenType.EXTENDS) or self.match(TokenType.COLON):
            base_class = self.consume(TokenType.IDENTIFIER, "Expected base class name").value
            
        traits = []
        if self.match(TokenType.IMPLEMENTS):
            while True:
                traits.append(self.consume(TokenType.IDENTIFIER, "Expected trait name").value)
                if not self.match(TokenType.COMMA):
                    break

                    
        self.consume(TokenType.LBRACE, "Expected '{' to start class body")
        self.skip_newlines()

        
        fields = []
        methods = []
        constructors = []
        constructor = None
        destructor = None
        properties = []
        operators = []
        
        while self.current().type != TokenType.RBRACE and self.current().type != TokenType.EOF:
            is_pub = False
            is_static = False
            is_virtual = False
            is_override = False
            
            # Access Modifiers
            if self.match(TokenType.PUB):
                is_pub = True
            elif self.match(TokenType.PRIV):
                is_pub = False
            elif self.match(TokenType.PROT):
                is_pub = False
                
            # Modifiers
            if self.match(TokenType.STATIC):
                is_static = True
            if self.match(TokenType.VIRTUAL):
                is_virtual = True
            if self.match(TokenType.OVERRIDE):
                is_override = True
                
            member_tok = self.current()
            
            if member_tok.type == TokenType.INIT:
                init_tok = self.advance()
                variant = None
                if self.match(TokenType.DOT):
                    variant = self.consume(TokenType.IDENTIFIER, "Expected constructor variant name after 'init.'").value
                self.consume(TokenType.LPAREN, "Expected '(' after 'init'")
                params = self.parse_parameter_list()
                self.consume(TokenType.RPAREN, "Expected ')' after parameters")
                body = self.parse_block()
                ctor_node = ConstructorDefNode(line=init_tok.line, col=init_tok.col, params=params, body=body, variant=variant)
                constructors.append(ctor_node)
                if constructor is None and variant is None:
                    constructor = ctor_node
            elif member_tok.type == TokenType.DROP:
                drop_tok = self.advance()
                self.consume(TokenType.LPAREN, "Expected '(' after 'drop'")
                self.consume(TokenType.RPAREN, "Expected ')' after '(' in drop()")
                body = self.parse_block()
                destructor = DestructorDefNode(line=drop_tok.line, col=drop_tok.col, body=body)
            elif member_tok.type == TokenType.PROP:
                prop_tok = self.advance()
                prop_name = self.consume(TokenType.IDENTIFIER, "Expected property name after 'prop'").value
                self.consume(TokenType.COLON, "Expected ':' after property name")
                prop_type = self.parse_type_annotation()
                self.consume(TokenType.LBRACE, "Expected '{' to start property definition")
                self.skip_newlines()
                getter_body = None
                setter_param = None
                setter_body = None

                while self.current().type != TokenType.RBRACE and self.current().type != TokenType.EOF:
                    if self.current().value == "get":
                        self.advance() # consume "get"
                        if self.match(TokenType.FAT_ARROW):
                            expr = self.parse_expression()
                            getter_body = BlockNode(line=prop_tok.line, col=prop_tok.col, statements=[ReturnNode(line=prop_tok.line, col=prop_tok.col, value=expr)])
                        else:
                            getter_body = self.parse_block()
                    elif self.current().value == "set":
                        self.advance() # consume "set"
                        param = "val"
                        if self.match(TokenType.LPAREN):
                            param = self.consume(TokenType.IDENTIFIER, "Expected parameter name in property setter").value
                            self.consume(TokenType.RPAREN, "Expected ')' after setter parameter")
                        setter_param = param
                        if self.match(TokenType.FAT_ARROW):
                            expr = self.parse_expression()
                            setter_body = BlockNode(line=prop_tok.line, col=prop_tok.col, statements=[ExprStmtNode(line=prop_tok.line, col=prop_tok.col, expr=expr)])
                        else:
                            setter_body = self.parse_block()
                    else:
                        self.error(f"Expected 'get' or 'set' inside property, but found '{self.current().value}'")
                    self.skip_newlines()
                self.consume(TokenType.RBRACE, "Expected '}' to close property definition")
                properties.append(PropertyDefNode(
                    line=prop_tok.line, col=prop_tok.col,
                    name=prop_name, type_name=prop_type,
                    getter_body=getter_body, setter_param=setter_param, setter_body=setter_body,
                    is_pub=is_pub, is_static=is_static
                ))
            elif member_tok.type == TokenType.OP:
                op_tok = self.advance()
                cur = self.current()
                op_str = ""
                if self.match(TokenType.LBRACKET):
                    self.consume(TokenType.RBRACKET, "Expected ']' after '[' in operator overload")
                    op_str = "[]"
                elif cur.type in (
                    TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH, TokenType.PERCENT,
                    TokenType.EQ_EQ, TokenType.NOT_EQ, TokenType.LT, TokenType.LTE, TokenType.GT, TokenType.GTE
                ):
                    op_str = self.advance().value
                else:
                    self.error(f"Invalid operator for overload: '{cur.value}'")

                self.consume(TokenType.LPAREN, "Expected '(' after operator")
                params = self.parse_parameter_list()
                self.consume(TokenType.RPAREN, "Expected ')' after parameters")
                ret_type = "void"
                if self.match(TokenType.ARROW):
                    ret_type = self.parse_type_annotation()
                if self.match(TokenType.FAT_ARROW):
                    expr = self.parse_expression()
                    body = BlockNode(line=op_tok.line, col=op_tok.col, statements=[ReturnNode(line=op_tok.line, col=op_tok.col, value=expr)])
                else:
                    body = self.parse_block()
                operators.append(OperatorDefNode(
                    line=op_tok.line, col=op_tok.col,
                    op=op_str, params=params, return_type=ret_type, body=body, is_pub=is_pub
                ))
            elif member_tok.type == TokenType.FN:
                methods.append(self.parse_function_def(is_static=is_static, is_virtual=is_virtual, is_override=is_override, is_pub=is_pub))
            elif member_tok.type == TokenType.IDENTIFIER:
                # Class field declaration:
                # Supports single field:
                #   pub name: str (= default)
                # And comma-separated multi-field declarations of the SAME type:
                #   pub name: str, addr: str
                #   pub num1: i64, num2: i64
                field_decls = []

                # First field
                first_tok = self.advance()
                first_name = first_tok.value
                self.consume(TokenType.COLON, "Expected ':' after field name")
                first_type = self.parse_type_annotation()
                first_default = None
                if self.match(TokenType.EQUALS):
                    first_default = self.parse_expression()
                field_decls.append((first_tok, first_name, first_type, first_default))

                # Check for comma-separated fields: , addr: str
                while self.match(TokenType.COMMA):
                    next_tok = self.consume(TokenType.IDENTIFIER, "Expected field name after ',' in multi-field declaration")
                    next_name = next_tok.value
                    self.consume(TokenType.COLON, "Expected ':' after field name in multi-field declaration")
                    next_type = self.parse_type_annotation()

                    # Enforce that all variables in a multi-field declaration must be of the same type
                    if next_type != first_type:
                        self.error(
                            f"Multi-field declarations must be of the same type. "
                            f"Field '{first_name}' has type '{first_type}', but '{next_name}' has type '{next_type}'",
                            next_tok
                        )

                    next_default = None
                    if self.match(TokenType.EQUALS):
                        next_default = self.parse_expression()
                    field_decls.append((next_tok, next_name, next_type, next_default))

                for tok, name, type_name, default_val in field_decls:
                    fields.append(ClassFieldNode(
                        line=tok.line, col=tok.col,
                        name=name, type_name=type_name,
                        default_val=default_val,
                        is_pub=is_pub, is_static=is_static
                    ))
            else:
                self.error(f"Unexpected class member '{member_tok.value}'")
                
            while self.match(TokenType.SEMICOLON):
                pass
            self.skip_newlines()
            
        self.consume(TokenType.RBRACE, "Expected '}' to close class body")
        
        return ClassDefNode(
            line=start_tok.line, col=start_tok.col,
            name=name_tok.value, base_class=base_class, traits=traits,
            fields=fields, methods=methods, constructor=constructor,
            destructor=destructor, constructors=constructors,
            properties=properties, operators=operators,
            type_params=type_params,
            is_packed=is_packed, alignment=alignment
        )

    def parse_trait_def(self) -> TraitDefNode:
        start_tok = self.consume(TokenType.TRAIT, "Expected 'trait'")
        name_tok = self.consume(TokenType.IDENTIFIER, "Expected trait name")
        self.consume(TokenType.LBRACE, "Expected '{' to start trait body")
        self.skip_newlines()
        
        methods = []
        while self.current().type != TokenType.RBRACE and self.current().type != TokenType.EOF:
            self.consume(TokenType.FN, "Expected 'fn' in trait")
            fn_name = self.consume(TokenType.IDENTIFIER, "Expected method name").value
            self.consume(TokenType.LPAREN, "Expected '('")
            params = self.parse_parameter_list()
            self.consume(TokenType.RPAREN, "Expected ')'")
            ret_type = "void"
            if self.match(TokenType.ARROW):
                ret_type = self.parse_type_annotation()
            methods.append(TraitMethodNode(line=start_tok.line, col=start_tok.col, name=fn_name, params=params, return_type=ret_type))
            self.skip_newlines()
            
        self.consume(TokenType.RBRACE, "Expected '}' to close trait body")
        return TraitDefNode(line=start_tok.line, col=start_tok.col, name=name_tok.value, methods=methods)

    def parse_extend_def(self) -> ExtendDefNode:
        tok = self.consume(TokenType.EXTEND, "Expected 'extend'")
        target_tok = self.consume(TokenType.IDENTIFIER, "Expected type name to extend")
        target_type = target_tok.value
        self.consume(TokenType.LBRACE, "Expected '{' to start extend block")
        self.skip_newlines()

        methods = []
        while self.current().type != TokenType.RBRACE and self.current().type != TokenType.EOF:
            is_pub = True
            if self.match(TokenType.PUB):
                is_pub = True
            elif self.match(TokenType.PRIV):
                is_pub = False

            if self.current().type == TokenType.FN:
                fn = self.parse_function_def(is_pub=is_pub)
                methods.append(fn)
            else:
                self.error(f"Only methods can be defined inside an 'extend' block, found '{self.current().value}'")
            self.skip_newlines()

        self.consume(TokenType.RBRACE, "Expected '}' to close extend block")
        return ExtendDefNode(line=tok.line, col=tok.col, target_type=target_type, methods=methods)

    def parse_enum_def(self) -> EnumDefNode:
        start_tok = self.consume(TokenType.ENUM, "Expected 'enum'")
        name_tok = self.consume(TokenType.IDENTIFIER, "Expected enum name")
        self.consume(TokenType.LBRACE, "Expected '{' to start enum definition")
        self.skip_newlines()

        variants: List[EnumVariantNode] = []
        tag = 0
        while self.current().type != TokenType.RBRACE and self.current().type != TokenType.EOF:
            v_tok = self.consume(TokenType.IDENTIFIER, "Expected enum variant name")
            fields: List[ParamNode] = []
            if self.match(TokenType.LPAREN):
                fields = self.parse_parameter_list()
                self.consume(TokenType.RPAREN, "Expected ')' after enum variant parameters")
            variants.append(EnumVariantNode(line=v_tok.line, col=v_tok.col, name=v_tok.value, fields=fields, tag=tag))
            tag += 1
            self.match(TokenType.COMMA)
            self.skip_newlines()

        self.consume(TokenType.RBRACE, "Expected '}' to close enum definition")
        return EnumDefNode(line=start_tok.line, col=start_tok.col, name=name_tok.value, variants=variants)



    # ==========================================
    # Statements
    # ==========================================

    def parse_statement(self) -> ASTNode:
        self.skip_newlines()
        while self.match(TokenType.SEMICOLON):
            self.skip_newlines()
        tok = self.current()

        if tok.type in (TokenType.LET, TokenType.MUT, TokenType.CONST):
            return self.parse_var_decl()
        elif tok.type == TokenType.GUARD:
            return self.parse_guard()
        elif tok.type == TokenType.MATCH:
            return self.parse_match()
        elif tok.type == TokenType.IF:
            return self.parse_if()

        elif tok.type == TokenType.WHILE:
            return self.parse_while()
        elif tok.type == TokenType.FOR:
            return self.parse_for()
        elif tok.type == TokenType.LOOP:
            if self.peek().type == TokenType.LPAREN:
                expr = self.parse_expression()
                while self.match(TokenType.SEMICOLON):
                    pass
                return ExprStmtNode(line=expr.line, col=expr.col, expr=expr)
            return self.parse_loop()
        elif tok.type == TokenType.RETURN:
            return self.parse_return()
        elif tok.type == TokenType.DEFER:
            return self.parse_defer()
        elif tok.type == TokenType.BREAK:
            self.advance()
            while self.match(TokenType.SEMICOLON):
                pass
            return BreakNode(line=tok.line, col=tok.col)
        elif tok.type == TokenType.CONTINUE:
            self.advance()
            while self.match(TokenType.SEMICOLON):
                pass
            return ContinueNode(line=tok.line, col=tok.col)
        elif tok.type == TokenType.LBRACE:
            return self.parse_block()
        else:
            return self.parse_expr_statement()

    def parse_var_decl(self) -> ASTNode:
        start_tok = self.advance() # consume let/mut/const
        is_mut = (start_tok.type == TokenType.MUT)
        if start_tok.type == TokenType.LET and self.current().type == TokenType.MUT:
            self.advance() # consume 'mut' in 'let mut'
            is_mut = True

        # Check for tuple destructuring: let (a, b) = ...
        if self.match(TokenType.LPAREN):
            names = []
            while True:
                n_tok = self.consume(TokenType.IDENTIFIER, "Expected variable name in tuple destructuring")
                names.append(n_tok.value)
                if not self.match(TokenType.COMMA):
                    break
            self.consume(TokenType.RPAREN, "Expected ')' after tuple destructuring names")
            self.consume(TokenType.EQUALS, "Expected '=' in tuple destructuring")
            init_expr = self.parse_expression()
            while self.match(TokenType.SEMICOLON):
                pass
            return TupleDestructureNode(line=start_tok.line, col=start_tok.col, names=names, is_mut=is_mut, initializer=init_expr)

        name_tok = self.consume(TokenType.IDENTIFIER, "Expected variable name")
        
        type_annot = None
        if self.match(TokenType.COLON):
            type_annot = self.parse_type_annotation()
            
        initializer = None
        if self.match(TokenType.EQUALS):
            initializer = self.parse_expression()
        while self.match(TokenType.SEMICOLON):
            pass
            
        return VarDeclNode(line=start_tok.line, col=start_tok.col, name=name_tok.value, is_mut=is_mut, type_annotation=type_annot, initializer=initializer)

    def parse_if(self) -> IfNode:
        start_tok = self.consume(TokenType.IF, "Expected 'if'")
        condition = self.parse_expression()
        then_block = self.parse_block()
        
        else_block = None
        if self.match(TokenType.ELSE):
            if self.current().type == TokenType.IF:
                nested_if = self.parse_if()
                else_block = BlockNode(line=nested_if.line, col=nested_if.col, statements=[nested_if])
            else:
                else_block = self.parse_block()
                
        return IfNode(line=start_tok.line, col=start_tok.col, condition=condition, then_block=then_block, else_block=else_block)

    def parse_guard(self) -> GuardNode:
        tok = self.consume(TokenType.GUARD, "Expected 'guard'")
        condition = self.parse_expression()
        self.consume(TokenType.ELSE, "Expected 'else' after guard condition")
        if self.current().type == TokenType.LBRACE:
            else_block = self.parse_block()
        else:
            stmt = self.parse_statement()
            else_block = BlockNode(line=stmt.line, col=stmt.col, statements=[stmt])
        return GuardNode(line=tok.line, col=tok.col, condition=condition, else_block=else_block)


    def parse_while(self) -> WhileNode:
        start_tok = self.consume(TokenType.WHILE, "Expected 'while'")
        condition = self.parse_expression()
        body = self.parse_block()
        return WhileNode(line=start_tok.line, col=start_tok.col, condition=condition, body=body)

    def parse_for(self) -> ForNode:
        start_tok = self.consume(TokenType.FOR, "Expected 'for'")
        var_tok = self.consume(TokenType.IDENTIFIER, "Expected loop variable name")
        self.consume(TokenType.IN, "Expected 'in' after for variable")
        range_expr = self.parse_expression()
        body = self.parse_block()
        return ForNode(line=start_tok.line, col=start_tok.col, var_name=var_tok.value, range_expr=range_expr, body=body)

    def parse_loop(self) -> LoopNode:
        start_tok = self.consume(TokenType.LOOP, "Expected 'loop'")
        body = self.parse_block()
        return LoopNode(line=start_tok.line, col=start_tok.col, body=body)

    def parse_return(self) -> ReturnNode:
        start_tok = self.consume(TokenType.RETURN, "Expected 'return'")
        val = None
        if self.current().type not in (TokenType.NEWLINE, TokenType.SEMICOLON, TokenType.RBRACE, TokenType.EOF):
            val = self.parse_expression()
        while self.match(TokenType.SEMICOLON):
            pass
        return ReturnNode(line=start_tok.line, col=start_tok.col, value=val)

    def parse_defer(self) -> DeferNode:
        start_tok = self.consume(TokenType.DEFER, "Expected 'defer'")
        stmt = self.parse_statement()
        while self.match(TokenType.SEMICOLON):
            pass
        return DeferNode(line=start_tok.line, col=start_tok.col, statement=stmt)

    def parse_match(self) -> MatchNode:
        start_tok = self.consume(TokenType.MATCH, "Expected 'match'")
        expr = self.parse_expression()
        self.consume(TokenType.LBRACE, "Expected '{' to start match body")
        self.skip_newlines()

        cases: List[MatchCaseNode] = []
        while self.current().type != TokenType.RBRACE and self.current().type != TokenType.EOF:
            pat_tok = self.current()
            pattern = self.parse_expression()
            guard_expr = None
            if self.match(TokenType.IF):
                guard_expr = self.parse_expression()
            self.consume(TokenType.FAT_ARROW, "Expected '=>' after match pattern")
            if self.current().type == TokenType.LBRACE:
                body = self.parse_block()
            else:
                stmt_expr = self.parse_expression()
                body = BlockNode(line=stmt_expr.line, col=stmt_expr.col, statements=[ExprStmtNode(line=stmt_expr.line, col=stmt_expr.col, expr=stmt_expr)])
            cases.append(MatchCaseNode(line=pat_tok.line, col=pat_tok.col, pattern=pattern, body=body, guard_expr=guard_expr))
            self.match(TokenType.COMMA)
            while self.match(TokenType.SEMICOLON):
                pass
            self.skip_newlines()

        self.consume(TokenType.RBRACE, "Expected '}' to close match body")
        return MatchNode(line=start_tok.line, col=start_tok.col, expr=expr, cases=cases)


    def parse_block(self) -> BlockNode:
        start_tok = self.consume(TokenType.LBRACE, "Expected '{'")
        self.skip_newlines()
        stmts = []
        
        while self.current().type != TokenType.RBRACE and self.current().type != TokenType.EOF:
            try:
                stmt = self.parse_statement()
                if stmt:
                    stmts.append(stmt)
            except ParserError as pe:
                self.errors.append(pe)
                if len(self.errors) >= 25:
                    break
                self.synchronize()

            while self.match(TokenType.SEMICOLON):
                pass
            self.skip_newlines()
            
        if self.current().type == TokenType.EOF:
            self.error(
                f"Unclosed block: expected '}}' to match '{{' from line {start_tok.line}",
                token=self.current(),
                hint=f"add '}}' to close the block opened at line {start_tok.line}"
            )
        self.consume(TokenType.RBRACE, "Expected '}'")
        return BlockNode(line=start_tok.line, col=start_tok.col, statements=stmts)

    def parse_expr_statement(self) -> ASTNode:
        expr = self.parse_expression()
        # Check for assignment: target = expr, target += expr
        if self.current().type in (TokenType.EQUALS, TokenType.PLUS_EQ, TokenType.MINUS_EQ, TokenType.STAR_EQ, TokenType.SLASH_EQ, TokenType.PERCENT_EQ):
            op_tok = self.advance()
            val = self.parse_expression()
            while self.match(TokenType.SEMICOLON):
                pass
            return AssignNode(line=expr.line, col=expr.col, target=expr, op=op_tok.value, value=val)
        while self.match(TokenType.SEMICOLON):
            pass
        return ExprStmtNode(line=expr.line, col=expr.col, expr=expr)

    # ==========================================
    # Pratt Expression Parsing
    # ==========================================

    def parse_expression(self, precedence: Precedence = Precedence.NONE) -> ASTNode:
        self.skip_newlines()
        tok = self.current()
        prefix_fn = self.prefix_parselets.get(tok.type)
        if not prefix_fn:
            if tok.type in (TokenType.NEWLINE, TokenType.SEMICOLON, TokenType.EOF, TokenType.RBRACE, TokenType.RPAREN):
                self.error("Expected expression", tok, hint="provide a valid expression or literal value")
            else:
                self.error(f"Unexpected token in expression: '{tok.value}'", tok)

        left = prefix_fn()

        while precedence < self.current_precedence():
            tok = self.current()
            infix_fn = self.infix_parselets.get(tok.type)
            if not infix_fn:
                break
            left = infix_fn(left)

        return left

    # --- Prefix Parselets ---

    def parse_int_literal(self) -> ASTNode:
        tok = self.advance()
        return LiteralNode(line=tok.line, col=tok.col, value=tok.value, type_name="i64")

    def parse_float_literal(self) -> ASTNode:
        tok = self.advance()
        return LiteralNode(line=tok.line, col=tok.col, value=tok.value, type_name="f64")

    def parse_string_literal(self) -> ASTNode:
        tok = self.advance()
        return LiteralNode(line=tok.line, col=tok.col, value=tok.value, type_name="str")

    def parse_string_interp(self) -> ASTNode:
        tok = self.advance()
        raw = tok.value
        parts = []
        i = 0
        current_text = []

        while i < len(raw):
            if raw[i:i+2] in (r'\{', '{{'):
                current_text.append('{')
                i += 2
            elif raw[i:i+2] in (r'\}', '}}'):
                current_text.append('}')
                i += 2
            elif raw[i] == '{':
                if current_text:
                    parts.append("".join(current_text))
                    current_text = []

                # Find matching closing brace
                j = i + 1
                brace_depth = 1
                while j < len(raw) and brace_depth > 0:
                    if raw[j] == '{': brace_depth += 1
                    elif raw[j] == '}': brace_depth -= 1
                    j += 1
                expr_sub = raw[i+1 : j-1]
                # Lex and parse embedded expression
                from src.frontend.lexer import Lexer
                sub_lexer = Lexer(expr_sub, filename=self.current().file)
                sub_tokens = sub_lexer.tokenize()
                sub_parser = Parser(sub_tokens, [expr_sub])
                embedded_ast = sub_parser.parse_expression()
                parts.append(embedded_ast)
                i = j
            else:
                current_text.append(raw[i])
                i += 1

        if current_text:
            parts.append("".join(current_text))

        return StringInterpNode(line=tok.line, col=tok.col, parts=parts)

    def parse_char_literal(self) -> ASTNode:
        tok = self.advance()
        return LiteralNode(line=tok.line, col=tok.col, value=tok.value, type_name="char")

    def parse_bool_literal(self) -> ASTNode:
        tok = self.advance()
        return LiteralNode(line=tok.line, col=tok.col, value=tok.value, type_name="bool")

    def parse_null_literal(self) -> ASTNode:
        tok = self.advance()
        return LiteralNode(line=tok.line, col=tok.col, value=None, type_name="null")

    def _is_generic_instantiation(self) -> bool:
        if self.current().type != TokenType.LT:
            return False
        idx = self.pos + 1
        depth = 1
        valid_in_type = {
            TokenType.IDENTIFIER, TokenType.COMMA, TokenType.LT, TokenType.GT,
            TokenType.QUESTION, TokenType.STAR
        }
        while idx < len(self.tokens) and depth > 0:
            tok = self.tokens[idx]
            if tok.type == TokenType.LT:
                depth += 1
            elif tok.type == TokenType.GT:
                depth -= 1
                if depth == 0:
                    next_idx = idx + 1
                    if next_idx < len(self.tokens):
                        return self.tokens[next_idx].type == TokenType.LPAREN
                    return False
            elif tok.type not in valid_in_type:
                return False
            idx += 1
        return False

    def parse_loop_ident(self) -> ASTNode:
        tok = self.advance()
        return IdentifierNode(line=tok.line, col=tok.col, name=tok.value)

    def parse_identifier(self) -> ASTNode:
        tok = self.advance()
        name = tok.value
        if self.current().type == TokenType.LT and self._is_generic_instantiation():
            self.consume(TokenType.LT, "Expected '<'")
            type_args = []
            while True:
                type_args.append(self.parse_type_annotation())
                if not self.match(TokenType.COMMA):
                    break
            self.consume(TokenType.GT, "Expected '>' to close generic type arguments")
            self.record_generic_use(name, type_args)
            name = f"{name}_{'_'.join(type_args)}"
        return IdentifierNode(line=tok.line, col=tok.col, name=name)

    def parse_unary(self) -> ASTNode:
        tok = self.advance()
        operand = self.parse_expression(Precedence.UNARY)
        return UnaryOpNode(line=tok.line, col=tok.col, op=tok.value, operand=operand)

    def parse_grouped_expr(self) -> ASTNode:
        lparen = self.advance() # consume '('
        if self.match(TokenType.RPAREN):
            return TupleNode(line=lparen.line, col=lparen.col, elements=[])
        expr = self.parse_expression()
        if self.match(TokenType.COMMA):
            elements = [expr]
            if self.current().type != TokenType.RPAREN:
                while True:
                    elements.append(self.parse_expression())
                    if not self.match(TokenType.COMMA):
                        break
            self.consume(TokenType.RPAREN, "Expected ')' after tuple elements")
            return TupleNode(line=lparen.line, col=lparen.col, elements=elements)
        self.consume(TokenType.RPAREN, "Expected ')' after grouped expression")
        return expr

    def parse_new_expr(self) -> ASTNode:
        start_tok = self.advance() # consume 'new'
        class_name = self.parse_type_annotation()
        self.consume(TokenType.LPAREN, "Expected '(' after class name")
        args = self.parse_argument_list()
        self.consume(TokenType.RPAREN, "Expected ')' after arguments")
        return NewNode(line=start_tok.line, col=start_tok.col, class_name=class_name, args=args)

    def parse_spawn_expr(self) -> ASTNode:
        start_tok = self.advance() # consume 'spawn'
        call_expr = self.parse_expression(Precedence.UNARY)
        if not isinstance(call_expr, CallNode):
            self.error("Expected function call after 'spawn' (e.g. spawn worker())", start_tok)
        return SpawnNode(line=start_tok.line, col=start_tok.col, call=call_expr)

    def parse_sizeof(self) -> ASTNode:
        """Phase 24 — Parse sizeof(T) compile-time type byte-size expression."""
        start_tok = self.advance() # consume 'sizeof'
        self.consume(TokenType.LPAREN, "Expected '(' after 'sizeof'")
        target_t = self.parse_type_annotation()
        self.consume(TokenType.RPAREN, "Expected ')' after type in 'sizeof'")
        return SizeofNode(line=start_tok.line, col=start_tok.col, target_type=target_t)

    # --- Infix Parselets ---

    def parse_binary(self, left: ASTNode) -> ASTNode:
        op_tok = self.advance()
        prec = PRECEDENCES.get(op_tok.type, Precedence.NONE)
        right = self.parse_expression(prec)
        return BinaryOpNode(line=op_tok.line, col=op_tok.col, left=left, op=op_tok.value, right=right)

    def parse_pipeline(self, left: ASTNode) -> ASTNode:
        pipe_tok = self.advance() # consume '|>'
        right = self.parse_expression(Precedence.PIPELINE)
        if isinstance(right, CallNode):
            return PipelineNode(line=pipe_tok.line, col=pipe_tok.col, left=left, right=right)
        elif isinstance(right, IdentifierNode):
            call_node = CallNode(line=right.line, col=right.col, callee=right, args=[])
            return PipelineNode(line=pipe_tok.line, col=pipe_tok.col, left=left, right=call_node)
        self.error("Right side of '|>' must be a function call", pipe_tok)
        return left

    def parse_cascade(self, left: ASTNode) -> ASTNode:
        casc_tok = self.advance() # consume '~>'
        right = self.parse_expression(Precedence.PIPELINE)
        if isinstance(right, CallNode):
            return CascadeNode(line=casc_tok.line, col=casc_tok.col, target=left, call=right)
        elif isinstance(right, IdentifierNode):
            call_node = CallNode(line=right.line, col=right.col, callee=right, args=[])
            return CascadeNode(line=casc_tok.line, col=casc_tok.col, target=left, call=call_node)
        self.error("Right side of '~>' must be a method call", casc_tok)
        return left


    def parse_range(self, left: ASTNode) -> ASTNode:
        range_tok = self.advance() # .. or ..=
        is_inclusive = (range_tok.type == TokenType.DOT_DOT_EQ)
        right = self.parse_expression(Precedence.RANGE)
        return RangeNode(line=range_tok.line, col=range_tok.col, start=left, end=right, is_inclusive=is_inclusive)

    def parse_call(self, left: ASTNode) -> ASTNode:
        lparen = self.advance() # consume '('
        args = self.parse_argument_list()
        self.consume(TokenType.RPAREN, "Expected ')' after arguments")
        return CallNode(line=left.line, col=left.col, callee=left, args=args)

    def parse_argument_list(self) -> List[ASTNode]:
        args = []
        if self.current().type == TokenType.RPAREN:
            return args
        while True:
            args.append(self.parse_expression())
            if not self.match(TokenType.COMMA):
                break
        return args

    def parse_member_access(self, left: ASTNode) -> ASTNode:
        self.advance() # consume '.'
        if self.current().type == TokenType.INT_LITERAL:
            num_tok = self.advance()
            member_name = f"f{num_tok.value}"
            return MemberAccessNode(line=left.line, col=left.col, object_expr=left, member=member_name)
        member_tok = self.consume(TokenType.IDENTIFIER, "Expected member name after '.'")
        return MemberAccessNode(line=left.line, col=left.col, object_expr=left, member=member_tok.value)

    def parse_fixed_array_literal(self) -> ASTNode:
        """
        Phase 23 — Parse a fixed-size stack array literal.
        Handles two forms:
          [a, b, c, d]   -> FixedArrayLiteralNode(elements=[a, b, c, d])
          [0; 8]         -> FixedArrayLiteralNode(repeat_value=0, repeat_count=8)
        """
        start_tok = self.advance()  # consume '['

        # Empty array literal: [] — not valid for fixed arrays, but parse gracefully
        if self.current().type == TokenType.RBRACKET:
            self.advance()
            return FixedArrayLiteralNode(line=start_tok.line, col=start_tok.col, elements=[])

        # Parse the first element (or the repeat value)
        first_expr = self.parse_expression()

        # Check for [value; N] repeat syntax
        if self.match(TokenType.SEMICOLON):
            size_tok = self.consume(TokenType.INT_LITERAL, "Expected integer size N in '[value; N]' repeat array")
            repeat_count = int(size_tok.value)
            self.consume(TokenType.RBRACKET, "Expected ']' to close array literal")
            return FixedArrayLiteralNode(
                line=start_tok.line, col=start_tok.col,
                elements=[],
                repeat_value=first_expr,
                repeat_count=repeat_count
            )

        # Otherwise it's an explicit element list: [a, b, c]
        elements = [first_expr]
        while self.match(TokenType.COMMA):
            if self.current().type == TokenType.RBRACKET:
                break  # Allow trailing comma
            elements.append(self.parse_expression())
        self.consume(TokenType.RBRACKET, "Expected ']' to close array literal")
        return FixedArrayLiteralNode(line=start_tok.line, col=start_tok.col, elements=elements)

    def parse_index_access(self, left: ASTNode) -> ASTNode:
        self.advance() # consume '['
        index_expr = self.parse_expression()
        self.consume(TokenType.RBRACKET, "Expected ']' after index")
        return IndexAccessNode(line=left.line, col=left.col, object_expr=left, index=index_expr)

    def parse_cast(self, left: ASTNode) -> ASTNode:
        self.advance() # consume 'as'
        target_type = self.parse_type_annotation()
        return CastNode(line=left.line, col=left.col, expr=left, target_type=target_type)

