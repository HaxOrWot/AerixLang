"""
Aerix Compiler (arxc) — Lexical Scanner
Tokenizes Aerix source code into a clean, coordinate-tracked token stream.
Handles comments, string interpolation, range vs float disambiguation, and newline splicing.
"""

from typing import List, Optional
from src.frontend.tokens import Token, TokenType, KEYWORDS


class LexerError(Exception):
    """Raised when the lexer encounters an invalid character or unterminated literal."""
    def __init__(self, message: str, line: int, col: int, file: str = "<stdin>", source_line: str = ""):
        self.message = message
        self.line = line
        self.col = col
        self.file = file
        self.source_line = source_line
        caret = " " * (col - 1) + "^"
        super().__init__(
            f"\n\033[1;31m[AERIX LEXER ERROR]\033[0m: {message}\n"
            f"  --> {file}:{line}:{col}\n"
            f"   |\n"
            f"{line:4d} | {source_line}\n"
            f"   | {caret}\n"
        )


class Lexer:
    def __init__(self, source: str, filename: str = "<stdin>"):
        self.source = source
        self.filename = filename
        self.length = len(source)
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []
        self.lines = source.splitlines()

    def get_source_line(self, line_num: int) -> str:
        if 1 <= line_num <= len(self.lines):
            return self.lines[line_num - 1]
        return ""

    def error(self, msg: str, line: Optional[int] = None, col: Optional[int] = None) -> None:
        err_line = line if line is not None else self.line
        err_col = col if col is not None else self.col
        raise LexerError(msg, err_line, err_col, self.filename, self.get_source_line(err_line))

    def peek(self, offset: int = 0) -> str:
        idx = self.pos + offset
        if idx < self.length:
            return self.source[idx]
        return '\0'

    def advance(self) -> str:
        if self.pos >= self.length:
            return '\0'
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def match(self, expected: str) -> bool:
        if self.pos >= self.length or self.source[self.pos] != expected:
            return False
        self.advance()
        return True

    def tokenize(self) -> List[Token]:
        """Scans the entire source and returns the complete token stream ending with EOF."""
        self.tokens = []
        
        while self.pos < self.length:
            start_line = self.line
            start_col = self.col
            ch = self.advance()

            # --- Whitespace ---
            if ch in (' ', '\t', '\r'):
                continue

            # --- Newlines & Statement Termination ---
            if ch == '\n':
                # Check if the previous token can legally end a statement
                if self.tokens and self.can_terminate_statement(self.tokens[-1].type):
                    self.tokens.append(Token(TokenType.NEWLINE, "\\n", start_line, start_col, self.filename))
                continue

            # --- Comments ---
            if ch == '/':
                if self.peek() == '/':  # Single-line comment
                    while self.peek() not in ('\n', '\0'):
                        self.advance()
                    continue
                elif self.peek() == '*':  # Multi-line comment (supports nesting!)
                    self.skip_block_comment(start_line, start_col)
                    continue
                elif self.match('='):
                    self.tokens.append(Token(TokenType.SLASH_EQ, "/=", start_line, start_col, self.filename))
                    continue
                else:
                    self.tokens.append(Token(TokenType.SLASH, "/", start_line, start_col, self.filename))
                    continue

            # --- Identifiers and Keywords ---
            if ch.isalpha() or ch == '_':
                ident = ch + self.scan_identifier()
                token_type = KEYWORDS.get(ident, TokenType.IDENTIFIER)
                value = True if ident == "true" else False if ident == "false" else ident
                self.tokens.append(Token(token_type, value, start_line, start_col, self.filename, raw=ident))
                continue

            # --- Numbers (Integers, Floats, Hex, Binary) ---
            if ch.isdigit():
                self.scan_number(ch, start_line, start_col)
                continue

            # --- Strings & String Interpolation ---
            if ch == '"':
                self.scan_string(start_line, start_col)
                continue

            # --- Characters ---
            if ch == "'":
                self.scan_char(start_line, start_col)
                continue

            # --- Multi-Character Operators & Punctuation ---
            if ch == '|':
                if self.match('>'):
                    self.tokens.append(Token(TokenType.PIPE, "|>", start_line, start_col, self.filename))
                elif self.match('|'):
                    self.tokens.append(Token(TokenType.OR_OR, "||", start_line, start_col, self.filename))
                else:
                    self.tokens.append(Token(TokenType.PIPE_CHAR, "|", start_line, start_col, self.filename))
            elif ch == '-':
                if self.match('>'):
                    self.tokens.append(Token(TokenType.ARROW, "->", start_line, start_col, self.filename))
                elif self.match('='):
                    self.tokens.append(Token(TokenType.MINUS_EQ, "-=", start_line, start_col, self.filename))
                else:
                    self.tokens.append(Token(TokenType.MINUS, "-", start_line, start_col, self.filename))
            elif ch == '=':
                if self.match('='):
                    self.tokens.append(Token(TokenType.EQ_EQ, "==", start_line, start_col, self.filename))
                elif self.match('>'):
                    self.tokens.append(Token(TokenType.FAT_ARROW, "=>", start_line, start_col, self.filename))
                else:
                    self.tokens.append(Token(TokenType.EQUALS, "=", start_line, start_col, self.filename))
            elif ch == '!':
                if self.match('='):
                    self.tokens.append(Token(TokenType.NOT_EQ, "!=", start_line, start_col, self.filename))
                else:
                    self.tokens.append(Token(TokenType.NOT, "!", start_line, start_col, self.filename))
            elif ch == '<':
                if self.match('='):
                    self.tokens.append(Token(TokenType.LTE, "<=", start_line, start_col, self.filename))
                elif self.match('<'):
                    self.tokens.append(Token(TokenType.LSHIFT, "<<", start_line, start_col, self.filename))
                else:
                    self.tokens.append(Token(TokenType.LT, "<", start_line, start_col, self.filename))
            elif ch == '>':
                if self.match('='):
                    self.tokens.append(Token(TokenType.GTE, ">=", start_line, start_col, self.filename))
                elif self.match('>'):
                    self.tokens.append(Token(TokenType.RSHIFT, ">>", start_line, start_col, self.filename))
                else:
                    self.tokens.append(Token(TokenType.GT, ">", start_line, start_col, self.filename))
            elif ch == '+':
                if self.match('='):
                    self.tokens.append(Token(TokenType.PLUS_EQ, "+=", start_line, start_col, self.filename))
                else:
                    self.tokens.append(Token(TokenType.PLUS, "+", start_line, start_col, self.filename))
            elif ch == '*':
                if self.match('*'):
                    self.tokens.append(Token(TokenType.POWER, "**", start_line, start_col, self.filename))
                elif self.match('='):
                    self.tokens.append(Token(TokenType.STAR_EQ, "*=", start_line, start_col, self.filename))
                else:
                    self.tokens.append(Token(TokenType.STAR, "*", start_line, start_col, self.filename))
            elif ch == '%':
                if self.match('='):
                    self.tokens.append(Token(TokenType.PERCENT_EQ, "%=", start_line, start_col, self.filename))
                else:
                    self.tokens.append(Token(TokenType.PERCENT, "%", start_line, start_col, self.filename))
            elif ch == '&':
                if self.match('&'):
                    self.tokens.append(Token(TokenType.AND_AND, "&&", start_line, start_col, self.filename))
                else:
                    self.tokens.append(Token(TokenType.AMPERSAND, "&", start_line, start_col, self.filename))
            elif ch == '^':
                self.tokens.append(Token(TokenType.CARET, "^", start_line, start_col, self.filename))
            elif ch == '~':
                if self.match('>'):
                    self.tokens.append(Token(TokenType.CASCADE, "~>", start_line, start_col, self.filename))
                else:
                    self.tokens.append(Token(TokenType.TILDE, "~", start_line, start_col, self.filename))
            elif ch == '.':
                if self.match('.'):
                    if self.match('='):
                        self.tokens.append(Token(TokenType.DOT_DOT_EQ, "..=", start_line, start_col, self.filename))
                    else:
                        self.tokens.append(Token(TokenType.DOT_DOT, "..", start_line, start_col, self.filename))
                else:
                    self.tokens.append(Token(TokenType.DOT, ".", start_line, start_col, self.filename))
            elif ch == '?':
                if self.match('?'):
                    self.tokens.append(Token(TokenType.QUESTION_QUESTION, "??", start_line, start_col, self.filename))
                elif self.match('.'):
                    self.tokens.append(Token(TokenType.QUESTION_DOT, "?.", start_line, start_col, self.filename))
                else:
                    self.tokens.append(Token(TokenType.QUESTION, "?", start_line, start_col, self.filename))
            elif ch == '(':
                self.tokens.append(Token(TokenType.LPAREN, "(", start_line, start_col, self.filename))
            elif ch == ')':
                self.tokens.append(Token(TokenType.RPAREN, ")", start_line, start_col, self.filename))
            elif ch == '{':
                self.tokens.append(Token(TokenType.LBRACE, "{", start_line, start_col, self.filename))
            elif ch == '}':
                self.tokens.append(Token(TokenType.RBRACE, "}", start_line, start_col, self.filename))
            elif ch == '[':
                self.tokens.append(Token(TokenType.LBRACKET, "[", start_line, start_col, self.filename))
            elif ch == ']':
                self.tokens.append(Token(TokenType.RBRACKET, "]", start_line, start_col, self.filename))
            elif ch == ',':
                self.tokens.append(Token(TokenType.COMMA, ",", start_line, start_col, self.filename))
            elif ch == ':':
                self.tokens.append(Token(TokenType.COLON, ":", start_line, start_col, self.filename))
            elif ch == ';':
                self.tokens.append(Token(TokenType.SEMICOLON, ";", start_line, start_col, self.filename))
            else:
                self.error(f"Unexpected character '{ch}'", start_line, start_col)

        # Append final EOF token
        self.tokens.append(Token(TokenType.EOF, None, self.line, self.col, self.filename))
        return self.tokens

    def scan_identifier(self) -> str:
        start_pos = self.pos
        while self.pos < self.length and (self.source[self.pos].isalnum() or self.source[self.pos] == '_'):
            self.advance()
        return self.source[start_pos:self.pos]

    def scan_number(self, first_digit: str, line: int, col: int) -> None:
        num_str = first_digit

        # Check for Hexadecimal (0x) or Binary (0b)
        if first_digit == '0' and self.peek() in ('x', 'X', 'b', 'B', 'o', 'O'):
            prefix = self.advance()
            num_str += prefix
            if prefix.lower() == 'x':
                while self.peek().lower() in '0123456789abcdef':
                    num_str += self.advance()
                self.tokens.append(Token(TokenType.INT_LITERAL, int(num_str, 16), line, col, self.filename, raw=num_str))
                return
            elif prefix.lower() == 'b':
                while self.peek() in ('0', '1'):
                    num_str += self.advance()
                self.tokens.append(Token(TokenType.INT_LITERAL, int(num_str, 2), line, col, self.filename, raw=num_str))
                return
            elif prefix.lower() == 'o':
                while self.peek() in '01234567':
                    num_str += self.advance()
                self.tokens.append(Token(TokenType.INT_LITERAL, int(num_str, 8), line, col, self.filename, raw=num_str))
                return

        # Decimal Integer or Float
        while self.peek().isdigit():
            num_str += self.advance()

        # Disambiguate float vs range operator (e.g., 0..10 vs 3.14)
        if self.peek() == '.' and self.peek(1) != '.':
            num_str += self.advance()  # Consume '.'
            while self.peek().isdigit():
                num_str += self.advance()
            # Optional exponent (e.g. 1.0e-5)
            if self.peek() in ('e', 'E'):
                num_str += self.advance()
                if self.peek() in ('+', '-'):
                    num_str += self.advance()
                while self.peek().isdigit():
                    num_str += self.advance()
            self.tokens.append(Token(TokenType.FLOAT_LITERAL, float(num_str), line, col, self.filename, raw=num_str))
        else:
            self.tokens.append(Token(TokenType.INT_LITERAL, int(num_str), line, col, self.filename, raw=num_str))

    def scan_string(self, line: int, col: int) -> None:
        chars = []
        has_interpolation = False

        while True:
            if self.pos >= self.length or self.peek() == '\n':
                self.error("Unterminated string literal", line, col)
            ch = self.advance()
            if ch == '"':
                break
            if ch == '\\':
                escaped = self.advance()
                if escaped == 'n': chars.append('\n')
                elif escaped == 't': chars.append('\t')
                elif escaped == 'r': chars.append('\r')
                elif escaped == '\\': chars.append('\\')
                elif escaped == '"': chars.append('"')
                elif escaped == '{': chars.append(r'\{')
                elif escaped == '}': chars.append(r'\}')
                else: chars.append(escaped)

            else:
                if ch == '{':
                    has_interpolation = True
                chars.append(ch)

        raw_str = "".join(chars)
        tok_type = TokenType.STRING_INTERP if has_interpolation else TokenType.STRING_LITERAL
        self.tokens.append(Token(tok_type, raw_str, line, col, self.filename, raw=raw_str))

    def scan_char(self, line: int, col: int) -> None:
        if self.pos >= self.length or self.peek() == '\n':
            self.error("Unterminated character literal", line, col)
        ch = self.advance()
        if ch == '\\':
            esc = self.advance()
            ch = '\n' if esc == 'n' else '\t' if esc == 't' else '\r' if esc == 'r' else esc
        if not self.match("'"):
            self.error("Unterminated character literal", line, col)
        self.tokens.append(Token(TokenType.CHAR_LITERAL, ch, line, col, self.filename, raw=ch))

    def skip_block_comment(self, start_line: int, start_col: int) -> None:
        self.advance()  # Consume '*'
        depth = 1
        while depth > 0:
            if self.pos >= self.length:
                self.error("Unterminated block comment", start_line, start_col)
            if self.peek() == '/' and self.peek(1) == '*':
                self.advance()
                self.advance()
                depth += 1
            elif self.peek() == '*' and self.peek(1) == '/':
                self.advance()
                self.advance()
                depth -= 1
            else:
                self.advance()

    @staticmethod
    def can_terminate_statement(tok_type: TokenType) -> bool:
        """Determines if a token can legally end a statement for implicit semicolon insertion."""
        return tok_type in (
            TokenType.IDENTIFIER,
            TokenType.INT_LITERAL,
            TokenType.FLOAT_LITERAL,
            TokenType.STRING_LITERAL,
            TokenType.STRING_INTERP,
            TokenType.CHAR_LITERAL,
            TokenType.BOOL_LITERAL,
            TokenType.RPAREN,
            TokenType.RBRACKET,
            TokenType.RBRACE,
            TokenType.BREAK,
            TokenType.CONTINUE,
            TokenType.RETURN,
        )
