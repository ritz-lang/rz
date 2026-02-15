"""
Tests for the Ritz lexer.
"""

import pytest
from lexer import Lexer, tokenize, LexerError
from tokens import TokenType, Token


def token_types(source: str) -> list[TokenType]:
    """Helper to get just token types from source."""
    return [t.type for t in tokenize(source)]


def token_values(source: str) -> list[tuple[TokenType, any]]:
    """Helper to get token types and values."""
    return [(t.type, t.value) for t in tokenize(source)]


class TestBasicTokens:
    def test_empty_source(self):
        assert token_types("") == [TokenType.EOF]

    def test_simple_identifier(self):
        assert token_values("foo") == [
            (TokenType.IDENT, "foo"),
            (TokenType.EOF, None),
        ]

    def test_keywords(self):
        tokens = token_types("fn let var if else while for in match return struct enum import")
        assert tokens == [
            TokenType.FN, TokenType.LET, TokenType.VAR, TokenType.IF,
            TokenType.ELSE, TokenType.WHILE, TokenType.FOR, TokenType.IN,
            TokenType.MATCH, TokenType.RETURN, TokenType.STRUCT, TokenType.ENUM,
            TokenType.IMPORT, TokenType.EOF,
        ]

    def test_true_false(self):
        tokens = token_types("true false")
        assert tokens == [TokenType.TRUE, TokenType.FALSE, TokenType.EOF]


class TestNumbers:
    def test_integer(self):
        assert token_values("42") == [(TokenType.INT, 42), (TokenType.EOF, None)]

    def test_integer_with_underscores(self):
        assert token_values("1_000_000") == [(TokenType.INT, 1000000), (TokenType.EOF, None)]

    def test_hex(self):
        assert token_values("0xFF") == [(TokenType.INT, 255), (TokenType.EOF, None)]

    def test_binary(self):
        assert token_values("0b1010") == [(TokenType.INT, 10), (TokenType.EOF, None)]

    def test_float(self):
        assert token_values("3.14") == [(TokenType.FLOAT, 3.14), (TokenType.EOF, None)]

    def test_float_exponent(self):
        assert token_values("1e10") == [(TokenType.FLOAT, 1e10), (TokenType.EOF, None)]
        assert token_values("1.5e-3") == [(TokenType.FLOAT, 1.5e-3), (TokenType.EOF, None)]


class TestStrings:
    def test_simple_string(self):
        assert token_values('"hello"') == [
            (TokenType.STRING, "hello"),
            (TokenType.EOF, None),
        ]

    def test_string_escape_sequences(self):
        assert token_values(r'"hello\nworld"') == [
            (TokenType.STRING, "hello\nworld"),
            (TokenType.EOF, None),
        ]

    def test_string_all_escapes(self):
        assert token_values(r'"\n\t\r\\\"\0"') == [
            (TokenType.STRING, "\n\t\r\\\"\0"),
            (TokenType.EOF, None),
        ]

    def test_unterminated_string(self):
        with pytest.raises(LexerError):
            tokenize('"hello')


class TestCStrings:
    """Tests for C-string literals: c"..." -> *u8 (null-terminated)"""

    def test_cstring_basic(self):
        assert token_values('c"hello"') == [
            (TokenType.CSTRING, "hello"),
            (TokenType.EOF, None),
        ]

    def test_cstring_empty(self):
        assert token_values('c""') == [
            (TokenType.CSTRING, ""),
            (TokenType.EOF, None),
        ]

    def test_cstring_escapes(self):
        assert token_values(r'c"a\nb\tc"') == [
            (TokenType.CSTRING, "a\nb\tc"),
            (TokenType.EOF, None),
        ]

    def test_cstring_literal_braces(self):
        """Braces in C-strings are literal, not interpolation."""
        assert token_values('c"hello {world}"') == [
            (TokenType.CSTRING, "hello {world}"),
            (TokenType.EOF, None),
        ]

    def test_cstring_unterminated(self):
        with pytest.raises(LexerError):
            tokenize('c"hello')

    def test_cstring_not_ident(self):
        """c followed by non-quote is an identifier."""
        assert token_values('c "hello"') == [
            (TokenType.IDENT, "c"),
            (TokenType.STRING, "hello"),
            (TokenType.EOF, None),
        ]

    def test_cstring_in_expression(self):
        """C-string in typical usage context."""
        tokens = token_values('let s: *u8 = c"test"')
        assert (TokenType.CSTRING, "test") in tokens


class TestSpanStrings:
    """Tests for Span string literals: s"..." -> Span<u8> { ptr, len }"""

    def test_span_string_basic(self):
        assert token_values('s"hello"') == [
            (TokenType.SPAN_STRING, "hello"),
            (TokenType.EOF, None),
        ]

    def test_span_string_empty(self):
        assert token_values('s""') == [
            (TokenType.SPAN_STRING, ""),
            (TokenType.EOF, None),
        ]

    def test_span_string_escapes(self):
        assert token_values(r's"a\nb\tc"') == [
            (TokenType.SPAN_STRING, "a\nb\tc"),
            (TokenType.EOF, None),
        ]

    def test_span_string_literal_braces(self):
        """Braces in span strings are literal, not interpolation."""
        assert token_values('s"hello {world}"') == [
            (TokenType.SPAN_STRING, "hello {world}"),
            (TokenType.EOF, None),
        ]

    def test_span_string_unterminated(self):
        with pytest.raises(LexerError):
            tokenize('s"hello')

    def test_span_string_not_ident(self):
        """s followed by non-quote is an identifier."""
        assert token_values('s "hello"') == [
            (TokenType.IDENT, "s"),
            (TokenType.STRING, "hello"),
            (TokenType.EOF, None),
        ]

    def test_span_string_in_expression(self):
        """Span string in typical usage context."""
        tokens = token_values('let s: Span<u8> = s"test"')
        assert (TokenType.SPAN_STRING, "test") in tokens


class TestOperators:
    def test_single_char_operators(self):
        assert token_types("+ - * / % & | ^ ~ !") == [
            TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH,
            TokenType.PERCENT, TokenType.AMP, TokenType.PIPE, TokenType.CARET,
            TokenType.TILDE, TokenType.BANG, TokenType.EOF,
        ]

    def test_comparison_operators(self):
        assert token_types("< > == != <= >=") == [
            TokenType.LT, TokenType.GT, TokenType.EQEQ, TokenType.NEQ,
            TokenType.LEQ, TokenType.GEQ, TokenType.EOF,
        ]

    def test_arrows(self):
        assert token_types("-> =>") == [TokenType.ARROW, TokenType.FATARROW, TokenType.EOF]

    def test_logical_operators(self):
        assert token_types("&& ||") == [TokenType.AMPAMP, TokenType.PIPEPIPE, TokenType.EOF]

    def test_compound_assignment(self):
        assert token_types("+= -= *= /=") == [
            TokenType.PLUSEQ, TokenType.MINUSEQ, TokenType.STAREQ,
            TokenType.SLASHEQ, TokenType.EOF,
        ]


class TestDelimiters:
    def test_parens_brackets_braces(self):
        assert token_types("( ) [ ] { }") == [
            TokenType.LPAREN, TokenType.RPAREN, TokenType.LBRACKET,
            TokenType.RBRACKET, TokenType.LBRACE, TokenType.RBRACE,
            TokenType.EOF,
        ]

    def test_punctuation(self):
        assert token_types(", : ; . .. ? ::") == [
            TokenType.COMMA, TokenType.COLON, TokenType.SEMI, TokenType.DOT,
            TokenType.DOTDOT, TokenType.QUESTION, TokenType.COLONCOLON,
            TokenType.EOF,
        ]

    def test_range_operators(self):
        """Test exclusive (..) and inclusive (..=) range operators."""
        assert token_types("0..10") == [
            TokenType.INT, TokenType.DOTDOT, TokenType.INT, TokenType.EOF
        ]
        assert token_types("0..=10") == [
            TokenType.INT, TokenType.DOTDOTEQ, TokenType.INT, TokenType.EOF
        ]
        assert token_values("..=") == [(TokenType.DOTDOTEQ, "..="), (TokenType.EOF, None)]


class TestComments:
    def test_line_comment(self):
        assert token_types("foo # comment\nbar") == [
            TokenType.IDENT, TokenType.NEWLINE, TokenType.IDENT, TokenType.EOF,
        ]

    def test_comment_at_eof(self):
        assert token_types("foo # comment") == [TokenType.IDENT, TokenType.EOF]


class TestIndentation:
    def test_simple_indent(self):
        source = "fn main()\n  print(\"hello\")"
        tokens = token_types(source)
        assert tokens == [
            TokenType.FN, TokenType.IDENT, TokenType.LPAREN, TokenType.RPAREN,
            TokenType.NEWLINE,
            TokenType.INDENT,
            TokenType.IDENT, TokenType.LPAREN, TokenType.STRING, TokenType.RPAREN,
            TokenType.DEDENT, TokenType.EOF,
        ]

    def test_nested_indent(self):
        source = "if x\n  if y\n    print(z)"
        tokens = token_types(source)
        assert tokens == [
            TokenType.IF, TokenType.IDENT,
            TokenType.NEWLINE,
            TokenType.INDENT,
            TokenType.IF, TokenType.IDENT,
            TokenType.NEWLINE,
            TokenType.INDENT,
            TokenType.IDENT, TokenType.LPAREN, TokenType.IDENT, TokenType.RPAREN,
            TokenType.DEDENT, TokenType.DEDENT, TokenType.EOF,
        ]

    def test_dedent_multiple_levels(self):
        source = "fn main()\n  if true\n    print(\"a\")\n  print(\"b\")"
        tokens = token_types(source)
        # After print("a"), we dedent back to 2-space level
        assert TokenType.INDENT in tokens
        assert TokenType.DEDENT in tokens

    def test_blank_lines_ignored(self):
        source = "fn main()\n\n  print(\"hello\")"
        tokens = token_types(source)
        assert TokenType.INDENT in tokens


class TestHelloWorld:
    """Test tokenizing our hello world example."""

    def test_hello_main(self):
        source = 'import ritzlib.fmt.print\n\nfn main()\n  print("Hello, Ritz!\\n")'
        tokens = token_values(source)

        expected = [
            (TokenType.IMPORT, "import"),
            (TokenType.IDENT, "ritzlib"),
            (TokenType.DOT, "."),
            (TokenType.IDENT, "fmt"),
            (TokenType.DOT, "."),
            (TokenType.IDENT, "print"),
            (TokenType.NEWLINE, None),
            (TokenType.NEWLINE, None),
            (TokenType.FN, "fn"),
            (TokenType.IDENT, "main"),
            (TokenType.LPAREN, "("),
            (TokenType.RPAREN, ")"),
            (TokenType.NEWLINE, None),
            (TokenType.INDENT, None),
            (TokenType.IDENT, "print"),
            (TokenType.LPAREN, "("),
            (TokenType.STRING, "Hello, Ritz!\n"),
            (TokenType.RPAREN, ")"),
            (TokenType.DEDENT, None),
            (TokenType.EOF, None),
        ]
        assert tokens == expected


class TestAsyncKeywords:
    """Test async and await keywords."""

    def test_async_keyword(self):
        tokens = token_values("async")
        assert tokens == [(TokenType.ASYNC, "async"), (TokenType.EOF, None)]

    def test_await_keyword(self):
        tokens = token_values("await")
        assert tokens == [(TokenType.AWAIT, "await"), (TokenType.EOF, None)]

    def test_async_fn(self):
        source = "async fn foo()"
        tokens = token_types(source)
        assert TokenType.ASYNC in tokens
        assert TokenType.FN in tokens

    def test_await_expression(self):
        source = "await foo()"
        tokens = token_types(source)
        assert TokenType.AWAIT in tokens
        assert TokenType.IDENT in tokens


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
