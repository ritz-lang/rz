"""
Ritz Token Definitions

Token types for the ritz0 lexer.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Any


class TokenType(Enum):
    # Literals
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    INTERP_STRING = auto()  # Interpolated string: "Hello, {name}!"
    CSTRING = auto()        # C-string literal: c"hello" -> *u8 (null-terminated)
    SPAN_STRING = auto()    # Span string literal: s"hello" -> Span<u8> { ptr, len }
    CHAR = auto()
    REGEX = auto()

    # Identifiers and keywords
    IDENT = auto()
    FN = auto()
    LET = auto()
    VAR = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    IN = auto()
    MATCH = auto()
    RETURN = auto()
    STRUCT = auto()
    ENUM = auto()
    IMPORT = auto()
    EXTERN = auto()
    TRUE = auto()
    FALSE = auto()
    UNSAFE = auto()
    CONST = auto()
    ASSERT = auto()
    STATIC_ASSERT = auto()
    BREAK = auto()
    CONTINUE = auto()
    AS = auto()
    TYPE = auto()
    TRAIT = auto()
    IMPL = auto()
    MUT = auto()
    ASYNC = auto()
    AWAIT = auto()
    LOOP = auto()
    NULL = auto()
    HEAP = auto()
    PUB = auto()

    # Operators
    PLUS = auto()          # +
    MINUS = auto()         # -
    STAR = auto()          # *
    SLASH = auto()         # /
    PERCENT = auto()       # %
    AMP = auto()           # &
    PIPE = auto()          # |
    CARET = auto()         # ^
    TILDE = auto()         # ~
    BANG = auto()          # !
    LT = auto()            # <
    GT = auto()            # >
    EQ = auto()            # =
    DOT = auto()           # .
    QUESTION = auto()      # ?

    # Multi-char operators
    EQEQ = auto()          # ==
    NEQ = auto()           # !=
    LEQ = auto()           # <=
    GEQ = auto()           # >=
    ARROW = auto()         # ->
    FATARROW = auto()      # =>
    DOTDOT = auto()        # ..
    DOTDOTEQ = auto()      # ..=
    AMPAMP = auto()        # &&
    PIPEPIPE = auto()      # ||
    PLUSEQ = auto()        # +=
    MINUSEQ = auto()       # -=
    STAREQ = auto()        # *=
    SLASHEQ = auto()       # /=
    COLONCOLON = auto()    # ::
    LSHIFT = auto()        # <<
    RSHIFT = auto()        # >>

    # Delimiters
    LPAREN = auto()        # (
    RPAREN = auto()        # )
    LBRACKET = auto()      # [
    RBRACKET = auto()      # ]
    LBRACE = auto()        # {
    RBRACE = auto()        # }
    COMMA = auto()         # ,
    COLON = auto()         # :
    SEMI = auto()          # ;

    # Indentation
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()

    # Attributes
    AT = auto()            # @ (for @test, @ignore, etc.)

    # Special
    EOF = auto()
    ERROR = auto()


KEYWORDS = {
    'fn': TokenType.FN,
    'let': TokenType.LET,
    'var': TokenType.VAR,
    'if': TokenType.IF,
    'else': TokenType.ELSE,
    'while': TokenType.WHILE,
    'for': TokenType.FOR,
    'in': TokenType.IN,
    'match': TokenType.MATCH,
    'return': TokenType.RETURN,
    'struct': TokenType.STRUCT,
    'enum': TokenType.ENUM,
    'import': TokenType.IMPORT,
    'extern': TokenType.EXTERN,
    'true': TokenType.TRUE,
    'false': TokenType.FALSE,
    'unsafe': TokenType.UNSAFE,
    'const': TokenType.CONST,
    'assert': TokenType.ASSERT,
    'static_assert': TokenType.STATIC_ASSERT,
    'break': TokenType.BREAK,
    'continue': TokenType.CONTINUE,
    'as': TokenType.AS,
    'type': TokenType.TYPE,
    'trait': TokenType.TRAIT,
    'impl': TokenType.IMPL,
    'mut': TokenType.MUT,
    'async': TokenType.ASYNC,
    'await': TokenType.AWAIT,
    'loop': TokenType.LOOP,
    'null': TokenType.NULL,
    'heap': TokenType.HEAP,
    'pub': TokenType.PUB,
    'for': TokenType.FOR,
}


@dataclass
class Span:
    """Source location information."""
    file: str
    line: int
    column: int
    length: int

    def __repr__(self) -> str:
        return f"{self.file}:{self.line}:{self.column}"


@dataclass
class Token:
    """A lexical token."""
    type: TokenType
    value: Any
    span: Span

    def __repr__(self) -> str:
        if self.value is not None:
            return f"Token({self.type.name}, {self.value!r}, {self.span})"
        return f"Token({self.type.name}, {self.span})"
