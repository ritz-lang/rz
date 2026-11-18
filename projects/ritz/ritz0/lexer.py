"""
Ritz Lexer

Tokenizes Ritz source code with indentation-based block handling.

Syntax features:
    - [[ and ]] for attributes
    - :& for mutable borrow parameters
    - := for move/ownership parameters
    - @T and @&T for reference types
    - *& for mutable raw pointer types
    - @ for address-of operator

    See RERITZ.md for full specification.
"""
from dataclasses import dataclass
from typing import Iterator, List, Optional
from tokens import Token, TokenType, Span, KEYWORDS
from ref_rules import DOLLAR_OUTSIDE_ASM

# RERITZ mode is now the ONLY mode - legacy mode has been removed


# The value of the INDENT the lexer emits for a line indented less than its
# block but not as far as any outer one.  An error unless the parser finds
# the line continues an expression (R46, AGAST #3387).
UNMATCHED_INDENT = "Unindent does not match any outer indentation level"


class EscapeError(Exception):
    """A bad escape; the caller attaches the span (the escape char's)."""


# The escapes every literal kind accepts (LANGUAGE_SPEC section 2.6). `\{` and
# `\}` are added for "..." and '.' only: c"..." has no interpolation.
_ESCAPES = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\', '"': '"', "'": "'",
            '0': '\0', 'e': '\x1b'}
_HEX_DIGITS = '0123456789abcdefABCDEF'


def decode_escape(text: str, i: int, braces: bool) -> tuple:
    r"""Decode the escape whose escape char (the one after the backslash) is
    `text[i]`. Returns (cooked char, chars consumed from `i`).

    The one escape table for `_lex_string`, `_lex_cstring` and `_cook_plain`
    (AGAST #3450 noted the ladder was copied per literal kind). ritz1's twin
    is lexer.ritz `lexer_cook_escape_at`; the two must agree.

    AGAST #1872 added `\e` (ESC) and `\xNN`: exactly two hex digits, either
    case, and at most 0x7F. A literal is UTF-8 text, so a lone byte above
    0x7F would be half a character; write a non-ASCII character as itself.
    """
    esc = text[i] if i < len(text) else '\0'
    if esc in _ESCAPES:
        return _ESCAPES[esc], 1
    if braces and esc in '{}':
        return esc, 1
    if esc == 'x':
        digits = text[i + 1:i + 3]
        if len(digits) != 2 or any(c not in _HEX_DIGITS for c in digits):
            raise EscapeError("Hex escape '\\x' needs exactly two hex digits")
        value = int(digits, 16)
        if value > 0x7F:
            raise EscapeError(
                f"Hex escape '\\x{digits}' is above '\\x7F': a literal is "
                f"UTF-8 text, so write a non-ASCII character as itself")
        return chr(value), 3
    raise EscapeError(f"Unknown escape sequence '\\{esc}'")


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
        # The current line's indentation.
        self.line_indent = 0
        # asm body mode (LANGUAGE_SPEC §18.6, AGAST #3396; ritz1's lexer.ritz
        # has the same).  An `asm` block's body is text, not Ritz:
        # `movq $3, %rcx` must reach the parser whole.  From an `asm` token
        # to the end of its line the lexer is in 'header' (newlines inside
        # the clause list's parentheses are spaces); a header ending in `:`
        # puts it in 'raw' for the lines indented deeper than the `asm`
        # line: each is one ASM_LINE, then NEWLINE.  The first gets the
        # block's INDENT; a deeper one none of its own (its extra indentation
        # is dropped).  The first line no deeper than the `asm` line leaves
        # the mode and is laid out as usual, DEDENTing the body.
        self.asm_state = None       # None, 'header' or 'raw'
        self.asm_base = 0           # the `asm` line's indentation
        self.asm_body = False       # the body's INDENT has been pushed
        # Open ( [ { (spec §2.2, AGAST #3426).  Inside them a line break and
        # the next line's indentation are whitespace: no NEWLINE, INDENT or
        # DEDENT (ritz1 lexer.ritz's bracket_depth).  `[[` opens two, as the
        # parser closes it with two `]`.  This also lets an asm header's
        # clause list span lines (#3396).
        self.bracket_depth = 0

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
        self.line_indent = indent

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
                # Not an error yet: the line may continue an expression after
                # a binary operator (R46, #3387), which only the parser can
                # tell.  It gets a marked INDENT; the parser raises
                # UNMATCHED_INDENT at it unless a relayout made it a
                # continuation (Parser._check_unmatched_indent).
                self.indent_stack.append(indent)
                tokens.append(Token(TokenType.INDENT, UNMATCHED_INDENT, start_span))

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
        Double quotes produce a STRING token.

        AGAST #2102: a "..." literal is plain bytes everywhere; `{expr}`
        placeholders mean something only to the print / eprint builtins
        (ritz1's rule, interp.ritz). So `value` keeps every brace, and a
        literal with a matched `{...}` additionally carries `interp`, its
        print-time split (parts, expression strings), which the parser turns
        into an InterpString only for `print(...)` / `eprint(...)`.

        AGAST #1913: `{{` / `}}` are the brace escape of print interpolation,
        not of the literal (LANGUAGE_SPEC section 2, and ritz1's rule). A plain
        STRING token's `value` keeps them as two bytes; its `print_value` is
        the text the print / eprint builtins write, with each pair collapsed
        to one brace. They are tracked side by side rather than collapsing the
        cooked value later, which could not tell `\\{{` (two braces) from `{{`.
        `interp` parts are only ever printed, so they collapse.
        """
        start_span = self._span()
        quote = self._advance()  # consume opening quote
        body_start = self.pos
        chars = []
        pchars = []     # print_value: chars with `{{` / `}}` collapsed
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
                chars.append(self._read_escape(braces=True))
                pchars.append(chars[-1])
            elif ch == '{' and quote == '"':
                # Check for {{ (escaped brace)
                if self._peek(1) == '{':
                    chars.append('{{')
                    pchars.append('{')
                    self._advance()
                    self._advance()
                elif not self._has_placeholder_close(quote):
                    # No matching } — treat { as literal character
                    chars.append('{')
                    pchars.append('{')
                    self._advance()
                else:
                    # Start of interpolation
                    has_interpolation = True
                    parts.append(''.join(pchars))
                    chars = []
                    pchars = []
                    expr_strs.append(self._read_placeholder(start_span))
            elif ch == '}' and quote == '"':
                # Check for }} (escaped brace)
                if self._peek(1) == '}':
                    chars.append('}}')
                    pchars.append('}')
                    self._advance()
                    self._advance()
                else:
                    # Standalone } is just a literal character (common in JSON strings)
                    # Only { starts interpolation, } by itself is not special
                    chars.append(ch)
                    pchars.append(ch)
                    self._advance()
            else:
                chars.append(ch)
                pchars.append(ch)
                self._advance()

        # Single-quoted single character = char literal (u8)
        if quote == "'" and len(chars) == 1:
            # No escape yields a code point above 0x7F, so one here is a
            # non-ASCII source character: more than one UTF-8 byte, which no
            # u8 holds. ord() would have emitted 'µ' as 181 and '€' as an
            # out-of-range 8364 (AGAST #1694). ritz1 refuses these too.
            if ord(chars[0]) > 0x7F:
                width = len(chars[0].encode('utf-8'))
                raise LexerError(
                    f"character literal '{chars[0]}' is {width} bytes in UTF-8; "
                    f"a character literal is one byte (u8): use a \"...\" "
                    f"string for non-ASCII text",
                    start_span)
            return Token(TokenType.CHAR, ord(chars[0]), start_span)

        # Single-quoted but not exactly one char = error
        if quote == "'":
            if len(chars) == 0:
                raise LexerError("Empty character literal", start_span)
            raise LexerError(f"Character literal must contain exactly one character, got {len(chars)}", start_span)

        # A literal with placeholders is still a plain literal (AGAST #2102).
        # The loop above split it for print; its own bytes are the body cooked
        # with braces as ordinary characters, placeholder text included.
        if has_interpolation:
            parts.append(''.join(pchars))  # Final part after last expr
            body = self.source[body_start:self.pos - 1]
            return Token(TokenType.STRING, self._cook_plain(body, start_span),
                         start_span, interp=(parts, expr_strs))

        return Token(TokenType.STRING, ''.join(chars), start_span,
                     print_value=''.join(pchars))

    def _has_placeholder_close(self, quote: str) -> bool:
        """With the lexer on a `{`, is there a matching `}` before the closing
        quote or the end of the line? Without this check, strings like "{"
        would be misinterpreted as interpolation."""
        depth = 1
        offset = 1
        while True:
            sc = self._peek(offset)
            if sc == '\0' or sc == '\n' or sc == quote:
                return False
            if sc == '{':
                depth += 1
            elif sc == '}':
                depth -= 1
                if depth == 0:
                    return True
            offset += 1

    def _read_placeholder(self, start_span: Span) -> str:
        """Consume `{expr}` (the lexer is on the `{`) and return the raw
        expression text between the braces."""
        self._advance()  # consume '{'
        expr_chars = []
        depth = 1
        while True:
            c = self._peek()
            if c == '\0' or c == '\n':
                raise LexerError("Unterminated interpolation in string", start_span)
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    break
            expr_chars.append(c)
            self._advance()
        self._advance()  # consume closing '}'
        return ''.join(expr_chars)

    def _read_escape(self, braces: bool) -> str:
        """Consume the escape at the current position (the char after the
        backslash) and return its cooked char. A bad one is located at the
        escape char, as every unknown escape always was."""
        try:
            cooked, width = decode_escape(self.source, self.pos, braces)
        except EscapeError as e:
            raise LexerError(str(e), self._span())
        for _ in range(width):
            self._advance()
        return cooked

    def _cook_plain(self, body: str, span: Span) -> str:
        """Cook a "..." body's escapes, treating every brace as a plain byte.

        Used for literals holding `{...}`, whose placeholder text the print
        split read raw (AGAST #2102).
        """
        out = []
        i = 0
        while i < len(body):
            ch = body[i]
            if ch == '\\':
                try:
                    cooked, width = decode_escape(body, i + 1, True)
                except EscapeError as e:
                    raise LexerError(str(e), span)
                out.append(cooked)
                i += 1 + width
            else:
                out.append(ch)
                i += 1
        return ''.join(out)

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
                chars.append(self._read_escape(braces=False))
            elif ch == '{':
                # No interpolation in C-strings - just literal braces
                chars.append(ch)
                self._advance()
            else:
                chars.append(ch)
                self._advance()

        return Token(TokenType.CSTRING, ''.join(chars), start_span)

    # Numeric literal type suffixes, longest first so `0usize` is not read as
    # `0u` + `size`. Written as `0u32`, `1i64`, `2.5f32`.
    NUMBER_SUFFIXES = ('usize', 'isize', 'u16', 'u32', 'u64', 'i16', 'i32',
                       'i64', 'f32', 'f64', 'u8', 'i8')

    def _lex_number_suffix(self) -> Optional[str]:
        """Consume a numeric literal type suffix at the current position."""
        for suffix in self.NUMBER_SUFFIXES:
            if not self.source.startswith(suffix, self.pos):
                continue
            after = self.source[self.pos + len(suffix):self.pos + len(suffix) + 1]
            if after and (after.isalnum() or after == '_'):
                continue  # part of a longer identifier, not a suffix
            for _ in range(len(suffix)):
                self._advance()
            return suffix
        return None

    # LANGUAGE_SPEC §2.6, LARB R73 (AGAST #3584): a `_` only ever stands
    # between two digits.  ritz1's lexer_check_separators says the same.
    SEPARATOR_MESSAGE = "`_` must stand between two digits of a numeric literal"

    def _check_separators(self, start_pos: int, start_span: Span, digits: str):
        """Refuse a `_` in source[start_pos:self.pos] that isn't between two
        of `digits`: one that starts or ends the digits, follows the `0x` /
        `0b` prefix, stands by another `_`, or touches a `.`, an exponent or
        a suffix.  The scan loops take every `_` they meet, so each of those
        is inside the span, and the error is at it.  A literal is one line.
        """
        for i in range(start_pos, self.pos):
            if self.source[i] != '_':
                continue
            before, after = self.source[i - 1], self.source[i + 1:i + 2]
            if before not in digits or not after or after not in digits:
                at = Span(self.filename, start_span.line,
                          start_span.column + (i - start_pos), 1)
                raise LexerError(self.SEPARATOR_MESSAGE, at)

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
                while self._peek() in '0123456789abcdefABCDEF_':
                    self._advance()
                self._check_separators(start_pos, start_span, '0123456789abcdefABCDEF')
                text = self.source[start_pos:self.pos].replace('_', '')
                try:
                    value = int(text, 16)
                except ValueError:
                    raise LexerError(f"Invalid hex literal: {text}", start_span)
                return Token(TokenType.INT, value, start_span,
                             self._lex_number_suffix())
            elif next_ch == 'b' or next_ch == 'B':
                self._advance()  # 0
                self._advance()  # b
                while self._peek() in '01_':
                    self._advance()
                self._check_separators(start_pos, start_span, '01')
                text = self.source[start_pos:self.pos].replace('_', '')
                try:
                    value = int(text, 2)
                except ValueError:
                    raise LexerError(f"Invalid binary literal: {text}", start_span)
                return Token(TokenType.INT, value, start_span,
                             self._lex_number_suffix())

        # Decimal number
        while self._peek().isdigit() or self._peek() == '_':
            self._advance()

        # A number right after `.` is a tuple field index, never a float:
        # `p.0.1` is the path p . 0 . 1, not p . FLOAT(0.1) (AGAST #2284).
        # Rust splits the float token in its parser for the same reason.
        if self.last_token_type == TokenType.DOT:
            self._check_separators(start_pos, start_span, '0123456789')
            text = self.source[start_pos:self.pos].replace('_', '')
            return Token(TokenType.INT, int(text), start_span)

        # Check for float.  `1._5` takes the `_` in, for _check_separators to
        # refuse: a `_` may not touch the `.` (`1.e5` stays `1 . e5`).
        is_float = False
        if self._peek() == '.' and (self._peek(1).isdigit() or
                                    (self._peek(1) == '_' and self._peek(2).isdigit())):
            is_float = True
            self._advance()  # .
            while self._peek().isdigit() or self._peek() == '_':
                self._advance()

        # Check for exponent.  A `_` straight after `e` or its sign is taken
        # in too, and refused by _check_separators, not as a missing digit.
        if self._peek() in 'eE':
            is_float = True
            self._advance()
            if self._peek() in '+-':
                self._advance()
            if not (self._peek().isdigit() or self._peek() == '_'):
                raise LexerError("Expected digit after exponent", self._span())
            while self._peek().isdigit() or self._peek() == '_':
                self._advance()

        self._check_separators(start_pos, start_span, '0123456789')
        text = self.source[start_pos:self.pos].replace('_', '')

        suffix = self._lex_number_suffix()
        if suffix in ('f32', 'f64'):
            is_float = True

        if is_float:
            return Token(TokenType.FLOAT, float(text), start_span, suffix)
        else:
            return Token(TokenType.INT, int(text), start_span, suffix)

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
        # `+%` `-%` `*%` and `+%=` `-%=` `*%=`: wrapping arithmetic (LARB R63,
        # AGAST #3485).  `%` is never a prefix, so `a +% b` can't mean `a + %b`.
        if ch in '+-*' and next_ch == '%':
            self._advance()
            if self._peek() == '=':
                self._advance()
                kind = {'+': TokenType.PLUSPCTEQ, '-': TokenType.MINUSPCTEQ,
                        '*': TokenType.STARPCTEQ}[ch]
                return Token(kind, ch + '%=', start_span)
            kind = {'+': TokenType.PLUSPCT, '-': TokenType.MINUSPCT, '*': TokenType.STARPCT}[ch]
            return Token(kind, ch + '%', start_span)
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

        # [[ for attributes - works in BOTH legacy and RERITZ modes
        # This allows gradual migration: [[test]] works everywhere
        # Note: We ONLY tokenize [[ as LBRACKET2, NOT ]] as RBRACKET2
        # The parser handles ]] by looking for two consecutive RBRACKET tokens
        # This avoids ambiguity with nested array indexing like foo[bar[x]]
        if ch == '[' and next_ch == '[':
            self._advance()
            return Token(TokenType.LBRACKET2, '[[', start_span)

        # @& - mutable reference type / take mutable reference (works in both modes)
        if ch == '@' and next_ch == '&':
            self._advance()
            return Token(TokenType.AT_AMP, '@&', start_span)

        # :& - mutable borrow parameter
        if ch == ':' and next_ch == '&':
            self._advance()
            return Token(TokenType.COLON_AMP, ':&', start_span)
        # := - move/ownership parameter
        if ch == ':' and next_ch == '=':
            self._advance()
            return Token(TokenType.COLON_EQ, ':=', start_span)
        # *& - mutable raw pointer type
        if ch == '*' and next_ch == '&':
            self._advance()
            return Token(TokenType.STAR_AMP, '*&', start_span)

        # Single-character tokens
        single_char = {
            '+': TokenType.PLUS,
            '-': TokenType.MINUS,
            '*': TokenType.STAR,
            '/': TokenType.SLASH,
            '%': TokenType.PERCENT,
            '$': TokenType.DOLLAR,
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

        # `$` is no identifier character: a monomorph's `W$i32_bump` can't be
        # written (§2.5, LARB R37, AGAST #3372).  An asm body's lines are text
        # and never get here; DOLLAR stays for an asm header until #1619.
        if ch == '$' and self.asm_state is None:
            raise LexerError(DOLLAR_OUTSIDE_ASM, start_span)

        if ch in single_char:
            return Token(single_char[ch], ch, start_span)

        raise LexerError(f"Unexpected character: '{ch}'", start_span)

    def _asm_line_start(self) -> Optional[List[Token]]:
        """At the start of a line in asm body mode: the tokens for the line
        (the body's INDENT, if not yet pushed, and its ASM_LINE), [] for a
        blank or comment-only line (skipped), or None if the line ends the
        body (the mode is off; it is laid out as usual)."""
        indent = 0
        while self._peek(indent) == ' ':
            indent += 1
        ch = self._peek(indent)
        if ch in ('\n', '#', '\t', '\0'):
            return None if ch == '\0' else self._handle_indentation()
        if indent <= self.asm_base:
            self.asm_state = None
            return None
        tokens = []
        if not self.asm_body:
            self.asm_body = True
            self.indent_stack.append(indent)
            tokens.append(Token(TokenType.INDENT, None, self._span()))
        for _ in range(indent):
            self._advance()
        self.line_indent = indent
        tokens.append(self._lex_asm_text())
        return tokens

    def _lex_asm_text(self) -> Token:
        """The rest of the line as one ASM_LINE: a `#` and what follows it is
        a comment and is left out, as is trailing whitespace.  The newline
        is lexed next, as usual."""
        span = self._span()
        start = self.pos
        while self._peek() not in ('\n', '\0'):
            self._advance()
        text = self.source[start:self.pos].split('#', 1)[0].rstrip(' \t\r')
        return Token(TokenType.ASM_LINE, text, Span(span.file, span.line, span.column, len(text)))

    def next_token(self) -> Token:
        """Get the next token."""
        tok = self._next_token()
        # AGAST #3396: track an asm header (see __init__).
        if tok.type == TokenType.ASM:
            self.asm_state = 'header'
            self.asm_base = self.line_indent
            self.asm_body = False
        tt = tok.type
        if tt in (TokenType.LPAREN, TokenType.LBRACKET, TokenType.LBRACE):
            self.bracket_depth += 1
        elif tt == TokenType.LBRACKET2:
            self.bracket_depth += 2
        elif tt in (TokenType.RPAREN, TokenType.RBRACKET, TokenType.RBRACE):
            # A close with nothing open is the parser's to report.
            self.bracket_depth = max(0, self.bracket_depth - 1)
        return tok

    def _next_token(self) -> Token:
        # Return pending tokens first (from indentation handling)
        if self.pending_tokens:
            tok = self.pending_tokens.pop(0)
            self.last_token_type = tok.type
            return tok

        # An asm body's line is text (AGAST #3396).
        while self.at_line_start and self.asm_state == 'raw':
            line_tokens = self._asm_line_start()
            if line_tokens is None:
                break
            if not line_tokens:
                # A blank or comment-only line: skip it.
                while self._peek() not in ('\n', '\0'):
                    self._advance()
                if self._peek() == '\0':
                    break
                self._advance()
                continue
            self.at_line_start = False
            self.pending_tokens.extend(line_tokens[1:])
            tok = line_tokens[0]
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

        # Inside ( [ { a line break and the next line's indentation are
        # whitespace (spec §2.2, AGAST #3426); so is a blank or comment-only
        # line.
        while self._peek() == '\n' and self.bracket_depth > 0:
            self._advance()
            self._skip_whitespace_and_comments()

        # Check for newline - emit NEWLINE token and prepare for indentation on next call
        if self._peek() == '\n':
            if self.asm_state == 'header':
                self.asm_state = 'raw' if self.last_token_type == TokenType.COLON else None
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

        # Note: s"..." (Span string) was removed in AGAST #98 — bare "..."
        # now produces StrView which is layout-compatible.

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


def relayout(tokens: list[Token], continuations: set[int]) -> list[Token]:
    """Re-derive INDENT / DEDENT for `tokens`, given its continuation lines.

    LARB R46 (spec §2.2, AGAST #3387): a line after one ending in a binary
    operator or `as` opens and closes no block, and must be indented at
    least as far as the statement's first line.  The lexer can't tell a
    binary `>` / `>>` from a generic list's close (`fn f() -> Vec<T>` then
    its body), so the parser, which can, names each continuation line (by
    line number) and asks for the layout again.

    Every non-layout token is kept as is; INDENT / DEDENT are dropped and
    recomputed exactly as `Lexer._handle_indentation` does (same spans,
    same UNMATCHED_INDENT marker), except that a
    continuation line emits none, and one shallower than its statement is
    an error.  With no continuations the result equals the lexer's own output
    (pinned by test_deeper_continuation.py).
    """
    out: list[Token] = []
    stack = [0]
    at_line_start = True
    for tok in tokens:
        tt = tok.type
        if tt in (TokenType.INDENT, TokenType.DEDENT):
            continue
        if tt == TokenType.EOF:
            for _ in range(len(stack) - 1):
                out.append(Token(TokenType.DEDENT, None, tok.span))
            out.append(tok)
            break
        if tt == TokenType.NEWLINE:
            at_line_start = True
            out.append(tok)
            continue
        if at_line_start:
            at_line_start = False
            indent = tok.span.column - 1
            start = Span(tok.span.file, tok.span.line, 1, 1)
            if tok.span.line in continuations:
                if indent < stack[-1]:
                    raise LexerError(
                        "continuation line is indented less than the "
                        "statement it continues; indent it at least as "
                        "far as the statement's first line", start)
            elif indent > stack[-1]:
                stack.append(indent)
                out.append(Token(TokenType.INDENT, None, start))
            elif indent < stack[-1]:
                while stack[-1] > indent:
                    stack.pop()
                    out.append(Token(TokenType.DEDENT, None, start))
                if stack[-1] != indent:
                    stack.append(indent)
                    out.append(Token(TokenType.INDENT, UNMATCHED_INDENT, start))
        out.append(tok)
    return out


def tokenize(source: str, filename: str = "<stdin>") -> List[Token]:
    """Convenience function to tokenize source code.

    Args:
        source: The source code to tokenize
        filename: The filename for error reporting
    """
    lexer = Lexer(source, filename)
    return lexer.tokenize()
