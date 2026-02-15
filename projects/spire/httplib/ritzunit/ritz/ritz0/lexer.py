"""
Ritz Lexer

Tokenizes Ritz source code with indentation-based block handling.
"""

from dataclasses import dataclass
from typing import Iterator, List
from tokens import Token, TokenType, Span, KEYWORDS


class LexerError(Exception):
    """Lexer error with source location."""
    def __init__(self, message: str, span: Span):
        self.message = message
        self.span = span
        super().__init__(f"{span}: {message}")


class Lexer:
    """
    Lexer for Ritz source code.

    Handles:
    - Indentation-based blocks (emits INDENT/DEDENT tokens)
    - String literals with escape sequences
    - Number literals (int, float, hex, binary)
    - Line comments (#)
    """

    def __init__(self, source: str, filename: str = "<stdin>"):
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.column = 1
        self.indent_stack: List[int] = [0]
        self.pending_tokens: List[Token] = []
        self.at_line_start = True
        self.last_token_type: TokenType = None  # Track last token for regex detection

    def _span(self, length: int = 1) -> Span:
        """Create a span at the current position."""
        return Span(self.filename, self.line, self.column, length)

    def _peek(self, offset: int = 0) -> str:
        """Peek at a character without consuming it."""
        pos = self.pos + offset
        if pos >= len(self.source):
            return '\0'
        return self.source[pos]

    def _advance(self) -> str:
        """Consume and return the current character."""
        if self.pos >= len(self.source):
            return '\0'
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _skip_whitespace_and_comments(self) -> None:
        """Skip horizontal whitespace and comments. Stop at newlines."""
        while True:
            ch = self._peek()
            if ch == ' ' or ch == '\t':
                self._advance()
            elif ch == '#':
                # Line comment - consume until newline
                while self._peek() not in ('\n', '\0'):
                    self._advance()
                # Don't consume the newline here - let main loop handle it
            elif ch == '@':
                # Attribute marker - don't skip, let tokenizer handle it
                break
            else:
                break

    def _handle_indentation(self) -> List[Token]:
        """Handle indentation at the start of a line."""
        tokens = []

        # Count leading spaces
        indent = 0
        start_span = self._span()
        while self._peek() == ' ':
            self._advance()
            indent += 1

        # Tabs are an error
        if self._peek() == '\t':
            raise LexerError("Tabs not allowed for indentation; use spaces", self._span())

        # Skip blank lines and comment-only lines (but not @attributes)
        if self._peek() == '\n':
            return []
        if self._peek() == '#':
            return []

        # Skip if at EOF
        if self._peek() == '\0':
            return []

        current = self.indent_stack[-1]

        if indent > current:
            self.indent_stack.append(indent)
            tokens.append(Token(TokenType.INDENT, None, start_span))
        elif indent < current:
            while self.indent_stack[-1] > indent:
                self.indent_stack.pop()
                tokens.append(Token(TokenType.DEDENT, None, start_span))
            if self.indent_stack[-1] != indent:
                raise LexerError(f"Unindent does not match any outer indentation level", start_span)

        return tokens

    def _lex_regex(self) -> Token:
        """Lex a regex literal."""
        start_span = self._span()
        self._advance()  # consume opening /
        chars = []

        while True:
            ch = self._peek()
            if ch == '\0' or ch == '\n':
                raise LexerError("Unterminated regex literal", start_span)
            if ch == '/':
                self._advance()
                break
            if ch == '\\':
                self._advance()
                next_ch = self._peek()
                if next_ch == '\0':
                    raise LexerError("Unterminated regex escape", start_span)
                chars.append('\\')
                chars.append(next_ch)
                self._advance()
            else:
                chars.append(ch)
                self._advance()

        value = ''.join(chars)
        return Token(TokenType.REGEX, value, start_span)

    def _lex_string(self) -> Token:
        """Lex a string or character literal.

        Single quotes with exactly one character produce a CHAR token (u8 value).
        Double quotes produce STRING or INTERP_STRING token.
        Interpolation uses {expr} syntax. Use {{ for literal brace.
        """
        start_span = self._span()
        quote = self._advance()  # consume opening quote
        chars = []
        has_interpolation = False
        parts = []      # String fragments
        expr_strs = []  # Expression strings (raw text inside {})

        while True:
            ch = self._peek()
            if ch == '\0' or ch == '\n':
                raise LexerError("Unterminated string literal", start_span)
            if ch == quote:
                self._advance()
                break
            if ch == '\\':
                self._advance()
                escape = self._peek()
                if escape == 'n':
                    chars.append('\n')
                elif escape == 't':
                    chars.append('\t')
                elif escape == 'r':
                    chars.append('\r')
                elif escape == '\\':
                    chars.append('\\')
                elif escape == '"':
                    chars.append('"')
                elif escape == "'":
                    chars.append("'")
                elif escape == '0':
                    chars.append('\0')
                elif escape == '{':
                    chars.append('{')  # \{ for literal brace
                elif escape == '}':
                    chars.append('}')  # \} for literal brace
                else:
                    raise LexerError(f"Unknown escape sequence '\\{escape}'", self._span())
                self._advance()
            elif ch == '{' and quote == '"':
                # Check for {{ (escaped brace)
                if self._peek(1) == '{':
                    chars.append('{')
                    self._advance()
                    self._advance()
                else:
                    # Start of interpolation
                    has_interpolation = True
                    parts.append(''.join(chars))
                    chars = []
                    self._advance()  # consume '{'

                    # Read expression until matching '}'
                    expr_chars = []
                    brace_depth = 1
                    while brace_depth > 0:
                        c = self._peek()
                        if c == '\0' or c == '\n':
                            raise LexerError("Unterminated interpolation in string", start_span)
                        if c == '{':
                            brace_depth += 1
                        elif c == '}':
                            brace_depth -= 1
                            if brace_depth == 0:
                                break
                        expr_chars.append(c)
                        self._advance()
                    self._advance()  # consume closing '}'
                    expr_strs.append(''.join(expr_chars))
            elif ch == '}' and quote == '"':
                # Check for }} (escaped brace)
                if self._peek(1) == '}':
                    chars.append('}')
                    self._advance()
                    self._advance()
                else:
                    # Standalone } is just a literal character (common in JSON strings)
                    # Only { starts interpolation, } by itself is not special
                    chars.append(ch)
                    self._advance()
            else:
                chars.append(ch)
                self._advance()

        # Single-quoted single character = char literal (u8)
        if quote == "'" and len(chars) == 1:
            return Token(TokenType.CHAR, ord(chars[0]), start_span)

        # Single-quoted but not exactly one char = error
        if quote == "'":
            if len(chars) == 0:
                raise LexerError("Empty character literal", start_span)
            raise LexerError(f"Character literal must contain exactly one character, got {len(chars)}", start_span)

        # Interpolated string
        if has_interpolation:
            parts.append(''.join(chars))  # Final part after last expr
            return Token(TokenType.INTERP_STRING, (parts, expr_strs), start_span)

        return Token(TokenType.STRING, ''.join(chars), start_span)

    def _lex_cstring(self) -> Token:
        """Lex a C-string literal: c"...".

        C-strings are null-terminated and produce *u8 type.
        They do NOT support interpolation.
        """
        start_span = self._span()
        self._advance()  # consume 'c'
        self._advance()  # consume opening '"'
        chars = []

        while True:
            ch = self._peek()
            if ch == '\0' or ch == '\n':
                raise LexerError("Unterminated C-string literal", start_span)
            if ch == '"':
                self._advance()
                break
            if ch == '\\':
                self._advance()
                escape = self._peek()
                if escape == 'n':
                    chars.append('\n')
                elif escape == 't':
                    chars.append('\t')
                elif escape == 'r':
                    chars.append('\r')
                elif escape == '\\':
                    chars.append('\\')
                elif escape == '"':
                    chars.append('"')
                elif escape == "'":
                    chars.append("'")
                elif escape == '0':
                    chars.append('\0')
                else:
                    raise LexerError(f"Unknown escape sequence '\\{escape}'", self._span())
                self._advance()
            elif ch == '{':
                # No interpolation in C-strings - just literal braces
                chars.append(ch)
                self._advance()
            else:
                chars.append(ch)
                self._advance()

        return Token(TokenType.CSTRING, ''.join(chars), start_span)

    def _lex_span_string(self) -> Token:
        """Lex a span string literal: s"...".

        Span strings produce Span<u8> { ptr: *u8, len: i64 } with compile-time length.
        They do NOT support interpolation.
        """
        start_span = self._span()
        self._advance()  # consume 's'
        self._advance()  # consume opening '"'
        chars = []

        while True:
            ch = self._peek()
            if ch == '\0' or ch == '\n':
                raise LexerError("Unterminated span string literal", start_span)
            if ch == '"':
                self._advance()
                break
            if ch == '\\':
                self._advance()
                escape = self._peek()
                if escape == 'n':
                    chars.append('\n')
                elif escape == 't':
                    chars.append('\t')
                elif escape == 'r':
                    chars.append('\r')
                elif escape == '\\':
                    chars.append('\\')
                elif escape == '"':
                    chars.append('"')
                elif escape == "'":
                    chars.append("'")
                elif escape == '0':
                    chars.append('\0')
                else:
                    raise LexerError(f"Unknown escape sequence '\\{escape}'", self._span())
                self._advance()
            elif ch == '{':
                # No interpolation in span strings - just literal braces
                chars.append(ch)
                self._advance()
            else:
                chars.append(ch)
                self._advance()

        return Token(TokenType.SPAN_STRING, ''.join(chars), start_span)

    def _lex_number(self) -> Token:
        """Lex a number literal (int or float)."""
        start_span = self._span()
        start_pos = self.pos

        # Check for hex/binary prefix
        if self._peek() == '0':
            next_ch = self._peek(1)
            if next_ch == 'x' or next_ch == 'X':
                self._advance()  # 0
                self._advance()  # x
                while self._peek().isalnum() or self._peek() == '_':
                    self._advance()
                text = self.source[start_pos:self.pos].replace('_', '')
                try:
                    value = int(text, 16)
                except ValueError:
                    raise LexerError(f"Invalid hex literal: {text}", start_span)
                return Token(TokenType.INT, value, start_span)
            elif next_ch == 'b' or next_ch == 'B':
                self._advance()  # 0
                self._advance()  # b
                while self._peek() in '01_':
                    self._advance()
                text = self.source[start_pos:self.pos].replace('_', '')
                try:
                    value = int(text, 2)
                except ValueError:
                    raise LexerError(f"Invalid binary literal: {text}", start_span)
                return Token(TokenType.INT, value, start_span)

        # Decimal number
        while self._peek().isdigit() or self._peek() == '_':
            self._advance()

        # Check for float
        is_float = False
        if self._peek() == '.' and self._peek(1).isdigit():
            is_float = True
            self._advance()  # .
            while self._peek().isdigit() or self._peek() == '_':
                self._advance()

        # Check for exponent
        if self._peek() in 'eE':
            is_float = True
            self._advance()
            if self._peek() in '+-':
                self._advance()
            if not self._peek().isdigit():
                raise LexerError("Expected digit after exponent", self._span())
            while self._peek().isdigit() or self._peek() == '_':
                self._advance()

        text = self.source[start_pos:self.pos].replace('_', '')

        if is_float:
            return Token(TokenType.FLOAT, float(text), start_span)
        else:
            return Token(TokenType.INT, int(text), start_span)

    def _lex_ident_or_keyword(self) -> Token:
        """Lex an identifier or keyword."""
        start_span = self._span()
        start_pos = self.pos

        while self._peek().isalnum() or self._peek() == '_':
            self._advance()

        text = self.source[start_pos:self.pos]

        # Check for keyword
        if text in KEYWORDS:
            return Token(KEYWORDS[text], text, start_span)

        return Token(TokenType.IDENT, text, start_span)

    def _lex_operator(self) -> Token:
        """Lex an operator or delimiter."""
        start_span = self._span()
        ch = self._advance()

        # Two-character operators
        next_ch = self._peek()

        if ch == '=' and next_ch == '=':
            self._advance()
            return Token(TokenType.EQEQ, '==', start_span)
        if ch == '!' and next_ch == '=':
            self._advance()
            return Token(TokenType.NEQ, '!=', start_span)
        if ch == '<' and next_ch == '=':
            self._advance()
            return Token(TokenType.LEQ, '<=', start_span)
        if ch == '>' and next_ch == '=':
            self._advance()
            return Token(TokenType.GEQ, '>=', start_span)
        if ch == '-' and next_ch == '>':
            self._advance()
            return Token(TokenType.ARROW, '->', start_span)
        if ch == '=' and next_ch == '>':
            self._advance()
            return Token(TokenType.FATARROW, '=>', start_span)
        if ch == '.' and next_ch == '.':
            self._advance()
            # Check for ..= (inclusive range)
            if self._peek() == '=':
                self._advance()
                return Token(TokenType.DOTDOTEQ, '..=', start_span)
            return Token(TokenType.DOTDOT, '..', start_span)
        if ch == '&' and next_ch == '&':
            self._advance()
            return Token(TokenType.AMPAMP, '&&', start_span)
        if ch == '|' and next_ch == '|':
            self._advance()
            return Token(TokenType.PIPEPIPE, '||', start_span)
        if ch == '+' and next_ch == '=':
            self._advance()
            return Token(TokenType.PLUSEQ, '+=', start_span)
        if ch == '-' and next_ch == '=':
            self._advance()
            return Token(TokenType.MINUSEQ, '-=', start_span)
        if ch == '*' and next_ch == '=':
            self._advance()
            return Token(TokenType.STAREQ, '*=', start_span)
        if ch == '/' and next_ch == '=':
            self._advance()
            return Token(TokenType.SLASHEQ, '/=', start_span)
        if ch == ':' and next_ch == ':':
            self._advance()
            return Token(TokenType.COLONCOLON, '::', start_span)
        if ch == '<' and next_ch == '<':
            self._advance()
            return Token(TokenType.LSHIFT, '<<', start_span)
        if ch == '>' and next_ch == '>':
            self._advance()
            return Token(TokenType.RSHIFT, '>>', start_span)

        # Single-character tokens
        single_char = {
            '+': TokenType.PLUS,
            '-': TokenType.MINUS,
            '*': TokenType.STAR,
            '/': TokenType.SLASH,
            '%': TokenType.PERCENT,
            '&': TokenType.AMP,
            '|': TokenType.PIPE,
            '^': TokenType.CARET,
            '~': TokenType.TILDE,
            '!': TokenType.BANG,
            '<': TokenType.LT,
            '>': TokenType.GT,
            '=': TokenType.EQ,
            '.': TokenType.DOT,
            '?': TokenType.QUESTION,
            '(': TokenType.LPAREN,
            ')': TokenType.RPAREN,
            '[': TokenType.LBRACKET,
            ']': TokenType.RBRACKET,
            '{': TokenType.LBRACE,
            '}': TokenType.RBRACE,
            ',': TokenType.COMMA,
            ':': TokenType.COLON,
            ';': TokenType.SEMI,
            '@': TokenType.AT,
        }

        if ch in single_char:
            return Token(single_char[ch], ch, start_span)

        raise LexerError(f"Unexpected character: '{ch}'", start_span)

    def next_token(self) -> Token:
        """Get the next token."""
        # Return pending tokens first (from indentation handling)
        if self.pending_tokens:
            tok = self.pending_tokens.pop(0)
            self.last_token_type = tok.type
            return tok

        # At line start, handle indentation before anything else
        if self.at_line_start:
            self.at_line_start = False
            indent_tokens = self._handle_indentation()
            if indent_tokens:
                self.pending_tokens.extend(indent_tokens[1:])
                tok = indent_tokens[0]
                self.last_token_type = tok.type
                return tok

        # Skip horizontal whitespace and comments
        self._skip_whitespace_and_comments()

        # Check for newline - emit NEWLINE token and prepare for indentation on next call
        if self._peek() == '\n':
            span = self._span()
            self._advance()
            self.at_line_start = True
            tok = Token(TokenType.NEWLINE, None, span)
            self.last_token_type = tok.type
            return tok

        # Check for EOF
        if self._peek() == '\0':
            # Emit remaining DEDENTs
            if len(self.indent_stack) > 1:
                self.indent_stack.pop()
                tok = Token(TokenType.DEDENT, None, self._span())
                self.last_token_type = tok.type
                return tok
            tok = Token(TokenType.EOF, None, self._span())
            self.last_token_type = tok.type
            return tok

        ch = self._peek()

        # String literal
        if ch == '"' or ch == "'":
            tok = self._lex_string()
            self.last_token_type = tok.type
            return tok

        # Regex literal (check if / appears after = or other tokens that precede patterns)
        if ch == '/' and self.last_token_type == TokenType.EQ:
            tok = self._lex_regex()
            self.last_token_type = tok.type
            return tok

        # Number literal
        if ch.isdigit():
            tok = self._lex_number()
            self.last_token_type = tok.type
            return tok

        # C-string literal: c"..."
        if ch == 'c' and self._peek(1) == '"':
            tok = self._lex_cstring()
            self.last_token_type = tok.type
            return tok

        # Span string literal: s"..."
        if ch == 's' and self._peek(1) == '"':
            tok = self._lex_span_string()
            self.last_token_type = tok.type
            return tok

        # Identifier or keyword
        if ch.isalpha() or ch == '_':
            tok = self._lex_ident_or_keyword()
            self.last_token_type = tok.type
            return tok

        # Operator or delimiter
        tok = self._lex_operator()
        self.last_token_type = tok.type
        return tok

    def tokenize(self) -> List[Token]:
        """Tokenize the entire source."""
        tokens = []
        while True:
            tok = self.next_token()
            tokens.append(tok)
            if tok.type == TokenType.EOF:
                break
        return tokens


def tokenize(source: str, filename: str = "<stdin>") -> List[Token]:
    """Convenience function to tokenize source code."""
    lexer = Lexer(source, filename)
    return lexer.tokenize()
