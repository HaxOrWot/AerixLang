"""
Aerix Compiler (arxc) — Token System
Defines all token types, keywords, operators, and Token dataclass.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, Optional


class TokenType(Enum):
    # --- Literals ---
    INT_LITERAL = auto()       # e.g. 42, 0xFF, 0b1010
    FLOAT_LITERAL = auto()     # e.g. 3.1415, 1.0e-3
    STRING_LITERAL = auto()    # e.g. "Hello world"
    STRING_INTERP = auto()     # String segment containing interpolated expressions
    CHAR_LITERAL = auto()      # e.g. 'A', '\n'
    BOOL_LITERAL = auto()      # true, false
    IDENTIFIER = auto()        # Variable, function, or class names
    LABEL = auto()             # Lifetime or loop label, e.g. 'outer

    # --- Keywords: Declarations ---
    FN = auto()                # fn
    LET = auto()               # let (immutable)
    MUT = auto()               # mut (mutable)
    CONST = auto()             # const
    CLASS = auto()             # class
    TRAIT = auto()             # trait (interface)
    ENUM = auto()              # enum
    STRUCT = auto()            # struct
    TYPE = auto()              # type alias
    INIT = auto()              # init (constructor)
    DROP = auto()              # drop (destructor)

    # --- Keywords: Control Flow ---
    IF = auto()                # if
    ELSE = auto()              # else
    MATCH = auto()             # match
    FOR = auto()               # for
    IN = auto()                # in
    WHILE = auto()             # while
    LOOP = auto()              # loop (infinite)
    BREAK = auto()             # break
    CONTINUE = auto()          # continue
    RETURN = auto()            # return
    SPAWN = auto()             # spawn (concurrency)
    TRY = auto()               # try (exception handling)
    CATCH = auto()             # catch
    FINALLY = auto()           # finally
    THROW = auto()             # throw

    # --- Keywords: OOP & Modifiers ---
    SELF = auto()              # self
    SUPER = auto()             # super
    PUB = auto()               # pub (public)
    PRIV = auto()              # priv (private)
    PROT = auto()              # prot (protected)
    STATIC = auto()            # static
    VIRTUAL = auto()           # virtual
    OVERRIDE = auto()          # override
    ABSTRACT = auto()          # abstract
    NEW = auto()               # new (heap allocation)
    DELETE = auto()            # delete (heap free)
    EXTENDS = auto()           # extends (inheritance)
    IMPLEMENTS = auto()        # implements (trait implementation)
    PROP = auto()              # prop (reactive property)
    OP = auto()                # op (operator overloading)
    EXTEND = auto()            # extend (type extensions)
    GUARD = auto()             # guard (early exit flow control)

    # --- Keywords: Memory & Safety ---
    DEFER = auto()             # defer (scoped cleanup)
    UNSAFE = auto()            # unsafe
    NULL = auto()              # null
    SIZEOF = auto()            # sizeof
    AS = auto()                # as (type casting)

    # --- Keywords: Interop & Modules ---
    USE = auto()               # use (module import)
    IMPORT = auto()            # import
    FROM = auto()              # from (selective import)
    CINCLUDE = auto()          # cinclude (direct C header)
    CEXTERN = auto()           # cextern (C function binding)

    # --- Operators: Arithmetic ---
    PLUS = auto()              # +
    MINUS = auto()             # -
    STAR = auto()              # *
    SLASH = auto()             # /
    PERCENT = auto()           # %
    POWER = auto()             # **

    # --- Operators: Comparison ---
    EQ_EQ = auto()             # ==
    NOT_EQ = auto()            # !=
    LT = auto()                # <
    LTE = auto()               # <=
    GT = auto()                # >
    GTE = auto()               # >=

    # --- Operators: Logical ---
    AND_AND = auto()           # &&
    OR_OR = auto()             # ||
    NOT = auto()               # !

    # --- Operators: Bitwise ---
    AMPERSAND = auto()         # & (also address-of / ref)
    PIPE_CHAR = auto()         # |
    CARET = auto()             # ^
    TILDE = auto()             # ~
    LSHIFT = auto()            # <<
    RSHIFT = auto()            # >>

    # --- Operators: Assignment ---
    EQUALS = auto()            # =
    PLUS_EQ = auto()           # +=
    MINUS_EQ = auto()          # -=
    STAR_EQ = auto()           # *=
    SLASH_EQ = auto()          # /=
    PERCENT_EQ = auto()        # %=

    # --- Operators: Aerix Special ---
    PIPE = auto()              # |> (Data Pipeline)
    CASCADE = auto()           # ~> (Fluent Cascade Mutation)
    ARROW = auto()             # -> (Return type)
    FAT_ARROW = auto()         # => (Expression body / Match arm)
    DOT_DOT = auto()           # .. (Exclusive range)
    DOT_DOT_EQ = auto()        # ..= (Inclusive range)
    QUESTION = auto()          # ? (Optional type)
    QUESTION_QUESTION = auto() # ?? (Null-coalescing)
    QUESTION_DOT = auto()      # ?. (Optional chaining)
    DOT = auto()               # . (Member access)

    # --- Delimiters ---
    LPAREN = auto()            # (
    RPAREN = auto()            # )
    LBRACE = auto()            # {
    RBRACE = auto()            # }
    LBRACKET = auto()          # [
    RBRACKET = auto()          # ]
    COMMA = auto()             # ,
    COLON = auto()             # :
    SEMICOLON = auto()         # ;
    HASH = auto()              # # (Attributes, e.g. #[packed])
    NEWLINE = auto()           # Virtual statement terminator
    EOF = auto()               # End of File


# Keyword dictionary lookup table (Case-sensitive)
KEYWORDS: dict[str, TokenType] = {
    "fn": TokenType.FN,
    "let": TokenType.LET,
    "mut": TokenType.MUT,
    "const": TokenType.CONST,
    "class": TokenType.CLASS,
    "trait": TokenType.TRAIT,
    "enum": TokenType.ENUM,
    "struct": TokenType.STRUCT,
    "type": TokenType.TYPE,
    "init": TokenType.INIT,
    "drop": TokenType.DROP,

    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "match": TokenType.MATCH,
    "for": TokenType.FOR,
    "in": TokenType.IN,
    "while": TokenType.WHILE,
    "loop": TokenType.LOOP,
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
    "return": TokenType.RETURN,
    "spawn": TokenType.SPAWN,
    "try": TokenType.TRY,
    "catch": TokenType.CATCH,
    "finally": TokenType.FINALLY,
    "throw": TokenType.THROW,

    "self": TokenType.SELF,
    "super": TokenType.SUPER,
    "pub": TokenType.PUB,
    "priv": TokenType.PRIV,
    "prot": TokenType.PROT,
    "static": TokenType.STATIC,
    "virtual": TokenType.VIRTUAL,
    "override": TokenType.OVERRIDE,
    "abstract": TokenType.ABSTRACT,
    "new": TokenType.NEW,
    "delete": TokenType.DELETE,
    "extends": TokenType.EXTENDS,
    "implements": TokenType.IMPLEMENTS,
    "prop": TokenType.PROP,
    "op": TokenType.OP,
    "extend": TokenType.EXTEND,
    "guard": TokenType.GUARD,

    "defer": TokenType.DEFER,
    "unsafe": TokenType.UNSAFE,
    "null": TokenType.NULL,
    "sizeof": TokenType.SIZEOF,
    "as": TokenType.AS,

    "use": TokenType.USE,
    "import": TokenType.IMPORT,
    "from": TokenType.FROM,
    "cinclude": TokenType.CINCLUDE,
    "cextern": TokenType.CEXTERN,

    "true": TokenType.BOOL_LITERAL,
    "false": TokenType.BOOL_LITERAL,
}


@dataclass
class Token:
    """Represents a lexical token with exact source coordinates."""
    type: TokenType
    value: Any
    line: int
    col: int
    file: str = "<stdin>"
    raw: str = ""

    def __repr__(self) -> str:
        if self.value is not None and str(self.value) != self.type.name:
            return f"Token({self.type.name}, {self.value!r}, line={self.line}, col={self.col})"
        return f"Token({self.type.name}, line={self.line}, col={self.col})"
