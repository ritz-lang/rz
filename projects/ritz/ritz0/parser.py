"""
Ritz Parser

Recursive descent parser with Pratt parsing for expressions.

Syntax features:
    - [[attr]] for attributes
    - :& for mutable borrow parameters
    - := for move/ownership parameters
    - @T for immutable reference types
    - @&T for mutable reference types

    See RERITZ.md for full specification.
"""

import re
from typing import List, Optional, Callable
from tokens import Token, TokenType, Span, KEYWORDS
from lexer import Lexer, LexerError, UNMATCHED_INDENT, relayout
import ritz_ast as rast
import index_rules
from qualified_access import module_item_access_removed
from monomorph import TypeSubstitution


def _defer_escape(node, in_loop: bool) -> Optional[str]:
    """The first `return`, `?`, `break` or `continue` that would leave a
    deferred statement, or None (LANGUAGE_SPEC §13.7). A `break`/`continue`
    inside a loop that is itself inside the deferred statement is fine. A
    nested `defer` was checked when it was parsed; a lambda is its own fn."""
    if isinstance(node, (rast.ReturnStmt, rast.ReturnExpr)):
        return "return"
    if isinstance(node, rast.TryOp):
        return "?"
    if isinstance(node, (rast.BreakStmt, rast.BreakExpr)) and not in_loop:
        return "break"
    if isinstance(node, (rast.ContinueStmt, rast.ContinueExpr)) and not in_loop:
        return "continue"
    if isinstance(node, (rast.DeferStmt, rast.Lambda, rast.Closure)):
        return None
    if isinstance(node, (rast.WhileStmt, rast.ForStmt)):
        in_loop = True
    if isinstance(node, list):
        children = node
    elif isinstance(node, rast.Node):
        children = [getattr(node, f) for f in node.__dataclass_fields__]
    else:
        return None
    for child in children:
        if isinstance(child, (list, rast.Node)):
            found = _defer_escape(child, in_loop)
            if found is not None:
                return found
    return None


# LARB R52 (AGAST #3409): the old union type and type-name pattern.
UNION_TYPE_REFUSED = ("`A | B` isn't a type: declare an enum with a payload "
                      "per kind (LANGUAGE_SPEC §3.8)")
TYPE_PATTERN_REFUSED = "a type isn't a pattern"


class ParseError(Exception):
    """Parser error with source location."""
    def __init__(self, message: str, span: Span):
        self.message = message
        self.span = span
        super().__init__(f"{span}: {message}")


# The attributes (LANGUAGE_SPEC §17, AGAST #1847): name -> (takes a
# `= "value"`, item kinds it applies to). Everything else is an error; ritz1
# keeps the same table in ritz1/src/ast_helpers.ritz.
ATTRS = {
    "test": (False, ("fn",)),
    # LANGUAGE_SPEC §17.1 (AGAST #1869): a fn that may `assert`, reporting
    # the calling [[test]] fn's location.
    "test_helper": (False, ("fn",)),
    "target_os": (True, ("fn", "struct", "const")),
    "packed": (False, ("struct",)),
    "naked": (False, ("fn",)),
    "inline": (False, ("fn",)),
    "always_inline": (False, ("fn",)),
    "noinline": (False, ("fn",)),
    # LANGUAGE_SPEC §17.7 (AGAST #1879). On a `type` item only when the
    # alias names a fn type (parse_type_alias checks).
    "callconv": (True, ("fn", "extern fn", "type")),
    # LANGUAGE_SPEC §17.8 (AGAST #2137): a call's result may not be
    # discarded (emitter_llvmlite.py _reject_discarded_must_use).
    "must_use": (False, ("fn",)),
}

# `[[callconv = "<name>"]]` values. "c" is the default, written out.
CALLCONVS = ("c", "win64")

# The tail of every "can't be `= extern`" diagnostic (AGAST #1900). ritz1
# prints the same words (ritz1/src/ast_helpers.ritz decl_refused).
DECL_REFUSED = "cannot be declaration-only (= extern)"

# LARB R46a (AGAST #3429, spec §2.2): inside ( [ { there is no layout, so no
# block can open there.  ritz1 prints the same words (#3388).
_OPENERS = {
    TokenType.LPAREN: "(",
    TokenType.LBRACKET: "[",
    TokenType.LBRACKET2: "[[",
    TokenType.LBRACE: "{",
}
_CLOSERS = (TokenType.RPAREN, TokenType.RBRACKET, TokenType.RBRACKET2, TokenType.RBRACE)


def block_in_brackets_message(bracket: str) -> str:
    return f"a block can't open inside `{bracket}`: bind the `if`/`match` to a `let` first"


def _enclosing_brackets(tokens: List[Token]) -> dict:
    """Map each `if` / `match` token inside brackets to its innermost bracket.

    Keyed by (line, column): the parser rewrites its token list (`>>` splits,
    continuation relayouts) but never moves a bracket or a keyword.  A close
    with nothing open is left to the parser to report.
    """
    found = {}
    stack = []
    for tok in tokens:
        tt = tok.type
        if tt in _OPENERS:
            stack.append(_OPENERS[tt])
        elif tt in _CLOSERS:
            if stack:
                stack.pop()
        elif stack and tt in (TokenType.IF, TokenType.MATCH):
            found[(tok.span.line, tok.span.column)] = stack[-1]
    return found


# Inline assembly (LANGUAGE_SPEC §18.6, AGAST #3396).  The architectures an
# `asm` block may name, and the x86_64 general registers a clause may pin or
# clobber, by their 64-bit names (ritz1: ast_helpers.ritz asm_reg_index).
ASM_ARCHES = ("x86_64",)
ASM_GPRS = ("rax", "rcx", "rdx", "rbx", "rsi", "rdi",
            "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15")
# `{name}` at a `{`, and a named label at the start of an asm line.
ASM_OPERAND = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
ASM_NAMED_LABEL = re.compile(r"([A-Za-z_.][A-Za-z0-9_.$]*):")


def _asm_reg(tok) -> str:
    """The register `tok` names, refused unless a clause may pin or clobber it."""
    if tok.value in ("rsp", "rbp"):
        raise ParseError(f"asm can't pin or clobber '{tok.value}'", tok.span)
    if tok.value not in ASM_GPRS:
        raise ParseError(
            f"'{tok.value}' is not a general register (rax, rbx, rcx, rdx, rsi, rdi, r8-r15)",
            tok.span)
    return tok.value


# LARB R53 (#3463): `usize` is another name for `u64`, and `isize` for `i64`.
# Every Ritz target is 64-bit, so they are the same types, not new ones. The
# parser resolves the names where it reads a type, so no later pass sees them.
TYPE_NAME_SYNONYMS = {'usize': 'u64', 'isize': 'i64'}


def resolve_type_name(name: str) -> str:
    """`name`, or the type it is another name for (LARB R53)."""
    return TYPE_NAME_SYNONYMS.get(name, name)


class Parser:
    """
    Parser for Ritz source code.

    Uses recursive descent for statements/items and Pratt parsing for expressions.
    """

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        # Undo log for token-list rewrites made while parsing speculatively:
        # `>>`/`>=` splits in type-argument context, (index, original_token)
        # (see _split_leading_gt), and continuation relayouts, (None,
        # previous_token_list) (see _continue_after_operator).
        self._angle_splits: List[tuple] = []
        # Lines that continue an expression after a binary operator or `as`
        # (LARB R46, AGAST #3387): they open and close no block.
        self._continuations: set = set()
        # `if` / `match` tokens inside ( [ { -> the innermost bracket (R46a).
        self._in_brackets = _enclosing_brackets(tokens)

    def _current(self) -> Token:
        """Get the current token."""
        if self.pos >= len(self.tokens):
            return self.tokens[-1]  # EOF
        return self.tokens[self.pos]

    def _peek(self, offset: int = 0) -> Token:
        """Peek at a token."""
        pos = self.pos + offset
        if pos >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[pos]

    def _at(self, *types: TokenType) -> bool:
        """Check if current token is one of the given types."""
        return self._current().type in types

    def _peek_at(self, offset: int, *types: TokenType) -> bool:
        """Check if token at offset is one of the given types."""
        return self._peek(offset).type in types

    def _advance(self) -> Token:
        """Consume and return the current token."""
        tok = self._current()
        if self.pos < len(self.tokens):
            self.pos += 1
        return tok

    def _expect(self, type: TokenType, msg: str = None) -> Token:
        """Consume a token of the expected type or raise an error."""
        tok = self._current()
        if tok.type != type:
            if type == TokenType.IDENT and tok.type == TokenType.ASM:
                # `asm` is a keyword (§18.6), in ritz1's words.
                msg = "unexpected 'asm'"
            if msg is None:
                msg = f"Expected {type.name}, got {tok.type.name}"
            raise ParseError(msg, tok.span)
        return self._advance()

    # ------------------------------------------------------------------
    # Closing angle brackets (AGAST #1299)
    #
    # The lexer greedily merges `>>` into RSHIFT and `>=` into GEQ, so a
    # nested type-argument list like `Vec<Vec<i64>>` never presents two `>`
    # tokens to the parser. Rather than teaching the lexer about type
    # context (a parser-driven lexer mode is a classic source of subtle
    # bugs), the parser splits the token *in type-argument context only*:
    # the leading `>` is rewritten in place and the remainder is pushed back
    # onto the token stream. Expression context is untouched, so `a >> b`
    # still lexes and parses as a right shift.
    #
    # Splits are recorded in an undo log so speculative parses that
    # backtrack (see _mark/_reset) restore the original RSHIFT/GEQ token.
    # ------------------------------------------------------------------

    # Tokens that begin with `>` and therefore may close a type-arg list.
    _SPLITTABLE_GT = {
        TokenType.RSHIFT: (TokenType.GT, '>'),      # >> -> > >
        TokenType.GEQ: (TokenType.EQ, '='),         # >= -> > =
    }

    def _mark(self) -> tuple:
        """Snapshot parser state for speculative parsing."""
        return (self.pos, len(self._angle_splits))

    def _reset(self, mark: tuple) -> None:
        """Restore parser state captured by _mark(), undoing any angle splits."""
        pos, split_depth = mark
        while len(self._angle_splits) > split_depth:
            index, original = self._angle_splits.pop()
            if index is None:      # a continuation relayout
                self.tokens, line = original
                self._continuations.discard(line)
            else:
                self.tokens[index:index + 2] = [original]
        self.pos = pos

    def _split_leading_gt(self) -> bool:
        """If the current token starts with `>` but is not GT, split it.

        `>>` becomes `>` `>`; `>=` becomes `>` `=`. Returns True if a split
        was performed (leaving a GT token at the current position).
        """
        tok = self._current()
        rest = self._SPLITTABLE_GT.get(tok.type)
        if rest is None:
            return False
        rest_type, rest_value = rest
        span = tok.span
        gt_span = Span(span.file, span.line, span.column, 1)
        rest_span = Span(span.file, span.line, span.column + 1, len(rest_value))
        self._angle_splits.append((self.pos, tok))
        self.tokens[self.pos:self.pos + 1] = [
            Token(TokenType.GT, '>', gt_span),
            Token(rest_type, rest_value, rest_span),
        ]
        return True

    def _at_type_args_close(self) -> bool:
        """True if the current token can close a type-arg list (`>`, `>>`, `>=`)."""
        return self._at(TokenType.GT) or self._current().type in self._SPLITTABLE_GT

    def _expect_type_args_close(self, msg: str) -> Token:
        """Consume one closing `>`, splitting a `>>`/`>=` token if needed."""
        self._split_leading_gt()
        return self._expect(TokenType.GT, msg)

    def _skip_newlines(self) -> None:
        """Skip any newline tokens."""
        while self._at(TokenType.NEWLINE):
            self._advance()

    def _skip_whitespace_tokens(self) -> None:
        """Skip newlines, indents, and dedents (for multiline constructs inside brackets)."""
        while self._at(TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
            self._advance()

    def _at_double_rbracket(self) -> bool:
        """Check if we're at ]] (either RBRACKET2 token or two RBRACKET tokens)."""
        if self._at(TokenType.RBRACKET2):
            return True
        return self._at(TokenType.RBRACKET) and self._peek_at(1, TokenType.RBRACKET)

    def _expect_double_rbracket(self) -> None:
        """Consume ]] (either RBRACKET2 or two RBRACKET tokens)."""
        if self._at(TokenType.RBRACKET2):
            self._advance()
        elif self._at(TokenType.RBRACKET) and self._peek_at(1, TokenType.RBRACKET):
            self._advance()  # first ]
            self._advance()  # second ]
        else:
            raise ParseError("Expected ]] to close attribute", self._current().span)

    def _parse_type_params(self) -> tuple[List[str], dict]:
        """Parse optional generic type parameters with optional trait bounds.

        Syntax:
            <T>                 - unbounded
            <T: Drop>           - single bound
            <T: Drop + Clone>   - multiple bounds
            <T: Drop, U: Clone> - multiple params with bounds

        Returns (type_params, type_param_bounds) where:
            type_params: list of parameter names
            type_param_bounds: dict mapping param name to list of trait names
        """
        type_params = []
        type_param_bounds = {}
        if self._at(TokenType.LT):
            self._advance()  # consume <
            if not self._at(TokenType.GT):
                name_tok = self._expect(TokenType.IDENT, "Expected type parameter name")
                type_params.append(name_tok.value)
                # Parse optional bounds: T: Drop + Clone
                if self._at(TokenType.COLON):
                    self._advance()
                    bounds = self._parse_trait_bounds()
                    type_param_bounds[name_tok.value] = bounds
                while self._at(TokenType.COMMA):
                    self._advance()
                    if self._at(TokenType.GT):
                        break  # trailing comma
                    name_tok = self._expect(TokenType.IDENT, "Expected type parameter name")
                    type_params.append(name_tok.value)
                    # Parse optional bounds
                    if self._at(TokenType.COLON):
                        self._advance()
                        bounds = self._parse_trait_bounds()
                        type_param_bounds[name_tok.value] = bounds
            self._expect(TokenType.GT, "Expected '>' after type parameters")
        return type_params, type_param_bounds

    def _parse_trait_bounds(self) -> List[str]:
        """Parse trait bounds: Drop or Drop + Clone + Serialize.

        Returns list of trait names.
        """
        bounds = []
        trait_tok = self._expect(TokenType.IDENT, "Expected trait name")
        bounds.append(trait_tok.value)
        # Parse additional bounds with +
        while self._at(TokenType.PLUS):
            self._advance()
            trait_tok = self._expect(TokenType.IDENT, "Expected trait name after '+'")
            bounds.append(trait_tok.value)
        return bounds

    def _can_start_type(self) -> bool:
        """Check if current token can start a type expression.

        Types can start with: identifier, *, &, [, fn
        """
        return self._at(TokenType.IDENT, TokenType.STAR, TokenType.AMP,
                        TokenType.LBRACKET, TokenType.FN)

    def _parse_type_args(self) -> List['rast.Type']:
        """Parse optional generic type arguments: <i32> or <i32, *u8>.

        Returns a list of type arguments.

        Uses lookahead to disambiguate: only treats < as starting type args
        if the next token can start a type (identifier, *, &, [, fn) or is >.
        This avoids misinterpreting `x < 0` as type arguments.
        """
        type_args = []
        if self._at(TokenType.LT):
            # Lookahead: check if this looks like type args or a comparison
            # Type args: <T>, <*u8>, <&T>, <[T]>, <fn()>, <@T>, <@&T>
            # Comparison: < 0, < x + y, etc.
            # `<dyn` is no comparison: parse_type refuses the `dyn` (#1620).
            if not self._peek_at(1, TokenType.IDENT, TokenType.STAR, TokenType.AMP,
                                  TokenType.LBRACKET, TokenType.FN, TokenType.GT,
                                  TokenType.AT, TokenType.AT_AMP, TokenType.LPAREN,
                                  TokenType.DYN):
                return type_args  # Not type args, leave < for expression parser

            self._advance()  # consume <
            if not self._at_type_args_close():
                type_args.append(self.parse_type())
                while self._at(TokenType.COMMA):
                    self._advance()
                    if self._at_type_args_close():
                        break  # trailing comma
                    type_args.append(self.parse_type())
            self._expect_type_args_close("Expected '>' after type arguments")
        return type_args

    def _try_parse_type_args_for_expr(self) -> List['rast.Type']:
        """Try to parse type arguments in an expression context.

        This uses lookahead to disambiguate foo<T> from foo < T.
        Returns empty list if not type arguments (i.e., it's a comparison).

        The heuristic: if we see < followed by valid type content and >,
        followed by ( or {, then it's type arguments.
        """
        if not self._at(TokenType.LT):
            return []

        # Save position for backtracking (also undoes any `>>` splits)
        mark = self._mark()

        try:
            self._advance()  # consume <

            type_args = []
            if not self._at_type_args_close():
                type_args.append(self.parse_type())
                while self._at(TokenType.COMMA):
                    self._advance()
                    if self._at_type_args_close():
                        break
                    type_args.append(self.parse_type())

            if not self._at_type_args_close():
                # Not a valid type arg list
                self._reset(mark)
                return []

            self._split_leading_gt()
            self._advance()  # consume >

            # Check if followed by ( or { - this confirms it's type args
            if self._at(TokenType.LPAREN, TokenType.LBRACE):
                return type_args

            # Not followed by ( or {, could be comparison
            # Backtrack and let expression parser handle it
            self._reset(mark)
            return []

        except ParseError:
            # Failed to parse as type args, backtrack
            self._reset(mark)
            return []

    def _try_parse_sizeof_generic_type(self) -> Optional[rast.TypeExpr]:
        """`Box<i64>` as sizeof's whole operand (AGAST #3268), else None.

        Only a type that runs right up to sizeof's `)` counts: `sizeof(n < m)`
        fails to parse as a type (or leaves tokens before the `)`), so the
        parser backs up and reads it as the comparison it is.
        """
        mark = self._mark()
        start = self._peek().span
        try:
            ty = self.parse_type()
        except ParseError:
            self._reset(mark)
            return None
        if not self._at(TokenType.RPAREN):
            self._reset(mark)
            return None
        return rast.TypeExpr(start, ty)

    # Tokens that start an operand.  After a cast's closing `>` one of these
    # means the `<` ... `>` were comparisons: `f(a as Sz < b, c > d)`.
    _OPERAND_START = frozenset((
        TokenType.IDENT, TokenType.INT, TokenType.FLOAT, TokenType.STRING,
        TokenType.CSTRING, TokenType.CHAR, TokenType.REGEX, TokenType.TRUE,
        TokenType.FALSE, TokenType.NULL, TokenType.LPAREN, TokenType.LBRACKET,
        TokenType.AT, TokenType.AT_AMP, TokenType.BANG, TokenType.NOT,
        TokenType.TILDE))

    def _try_parse_cast_type_args(self) -> List['rast.Type']:
        """Type arguments of a cast's target type: `x as *Box<i64>` (#3124).

        A cast's type sits in expression context, where `<` may be a
        comparison (`a as i64 < b`).  The list is kept only when it is a
        complete `<T, ...>` closed by a plain `>` (not a split `>>`/`>=`,
        which would be a shift or `>=` in a comparison) and no operand follows
        the `>`.  Anything else backtracks and leaves the `<` to the
        expression parser.
        """
        if not self._at(TokenType.LT):
            return []
        mark = self._mark()
        try:
            self._advance()  # consume <
            type_args = [self.parse_type()]
            while self._at(TokenType.COMMA):
                self._advance()
                type_args.append(self.parse_type())
            if self._at(TokenType.GT):
                self._advance()
                if self._current().type not in self._OPERAND_START:
                    return type_args
        except ParseError:
            pass
        self._reset(mark)
        return []

    def _interpolate_print_arg(self, callee: rast.Expr,
                               args: List[rast.Expr]) -> List[rast.Expr]:
        """Split `{expr}` placeholders in print / eprint's literal argument.

        AGAST #2102: interpolation belongs to the print / eprint builtins, as
        in ritz1 (interp.ritz). A "..." anywhere else -- a `let`, a call to
        any other function, a return, a field init, a bare statement -- keeps
        its braces as plain bytes, so only here does a StringLit carrying an
        `interp` split become an InterpString with parsed expressions.
        """
        if (isinstance(callee, rast.Ident) and callee.name in ('print', 'eprint')
                and len(args) == 1 and isinstance(args[0], rast.StringLit)
                and args[0].interp is not None):
            lit = args[0]
            parts, expr_strs = lit.interp
            exprs = [self._parse_interp_expr(e, lit.span) for e in expr_strs]
            return [rast.InterpString(lit.span, parts, exprs)]
        # AGAST #1824: format_into(sink, "...") -- the same literal rules,
        # on its second argument.
        if (isinstance(callee, rast.Ident) and callee.name == 'format_into'
                and len(args) == 2 and isinstance(args[1], rast.StringLit)
                and args[1].interp is not None):
            lit = args[1]
            parts, expr_strs = lit.interp
            exprs = [self._parse_interp_expr(e, lit.span) for e in expr_strs]
            return [args[0], rast.InterpString(lit.span, parts, exprs)]
        return args

    def _parse_interp_expr(self, expr_str: str, parent_span: Span) -> rast.Expr:
        """Parse an expression string from inside an interpolated string.

        For simple identifiers, returns an Ident directly.
        For complex expressions, lexes and parses the full expression.
        """
        expr_str = expr_str.strip()
        if not expr_str:
            raise ParseError("Empty interpolation expression", parent_span)

        # Simple case: just an identifier (most common)
        if expr_str.isidentifier():
            return rast.Ident(parent_span, expr_str)

        # Complex expression: lex and parse it
        try:
            lexer = Lexer(expr_str, parent_span.file)
            tokens = list(lexer.tokenize())
            sub_parser = Parser(tokens)
            return sub_parser.parse_expr()
        except (LexerError, ParseError) as e:
            raise ParseError(f"Invalid interpolation expression: {e}", parent_span)

    # ========================================================================
    # Types
    # ========================================================================

    def _at_type_start(self) -> bool:
        """Check if current token can start a type expression."""
        return self._at(
            TokenType.IDENT,    # Named type: i32, MyStruct
            TokenType.AMP,      # Reference: &T
            TokenType.STAR,     # Pointer: *T
            TokenType.LBRACKET, # Array/Slice: [N]T, [T]
            TokenType.FN,       # Function type: fn(A) -> B
        )

    def _parse_array_size_expr(self) -> rast.Expr:
        """Parse an expression for array size.

        Supports a limited set of constant expressions:
        - Integer literals: 512
        - Named constants: SIZE
        - Binary ops: SIZE * 2, 1 << 9
        - Unary ops: -1, ~0
        - Parenthesized: (SIZE + 1)
        """
        return self._parse_const_expr()

    def _parse_const_expr(self, min_prec: int = 0) -> rast.Expr:
        """Parse a constant expression with Pratt-style precedence.

        This is a simplified version of parse_expr that only allows
        constant-evaluable expressions.
        """
        left = self._parse_const_primary()

        # Binary operators with precedence
        const_precedence = {
            TokenType.PIPEPIPE: 1,  # ||
            TokenType.AMPAMP: 2,    # &&
            TokenType.PIPE: 3,      # |
            TokenType.CARET: 4,     # ^
            TokenType.AMP: 5,       # &
            TokenType.LSHIFT: 8,    # <<
            TokenType.RSHIFT: 8,    # >>
            TokenType.PLUS: 9,      # +
            TokenType.MINUS: 9,     # -
            TokenType.STAR: 10,     # *
            TokenType.SLASH: 10,    # /
            TokenType.PERCENT: 10,  # %
        }

        while True:
            tok = self._current()
            prec = const_precedence.get(tok.type, -1)
            if prec < min_prec:
                break
            op = tok.value
            self._advance()
            right = self._parse_const_expr(prec + 1)
            left = rast.BinOp(left.span, op, left, right)

        return left

    def _parse_const_primary(self) -> rast.Expr:
        """Parse a primary constant expression."""
        span = self._current().span

        # Integer literal
        if self._at(TokenType.INT):
            value = self._advance().value
            return rast.IntLit(span, value)

        # Identifier (constant name)
        if self._at(TokenType.IDENT):
            name = self._advance().value
            return rast.Ident(span, name)

        # Parenthesized expression
        if self._at(TokenType.LPAREN):
            self._advance()
            expr = self._parse_const_expr()
            self._expect(TokenType.RPAREN)
            return rast.Grouped(span, expr)

        # Unary minus
        if self._at(TokenType.MINUS):
            self._advance()
            operand = self._parse_const_primary()
            return rast.UnaryOp(span, '-', operand)

        # Bitwise NOT
        if self._at(TokenType.TILDE):
            self._advance()
            operand = self._parse_const_primary()
            return rast.UnaryOp(span, '~', operand)

        raise ParseError(f"Expected constant expression, got {self._current().type}", span)

    def parse_type(self, allow_type_args: bool = True) -> rast.Type:
        """Parse a type expression.

        Args:
            allow_type_args: If False (a cast's target, after `as`), a
                named type's `<...>` is read speculatively, since `<` may be
                a comparison there (_try_parse_cast_type_args, #3124).

        `|` always ends a type.  Where nothing may follow it but a type's end
        (here), a `|` is the old union syntax: LARB R52 removed it
        (LANGUAGE_SPEC §3.8, AGAST #3409).  A cast's target and a closure
        param's type, which `|` may legitimately follow, read the primary.
        """
        ty = self._parse_type_primary(allow_type_args)
        if self._at(TokenType.PIPE):
            raise ParseError(UNION_TYPE_REFUSED, self._current().span)
        return ty

    def _parse_type_primary(self, allow_type_args: bool = True) -> rast.Type:
        """Parse a type; a `|` after it is left for the caller."""
        span = self._current().span

        # @&T (mutable reference) - works in both legacy and RERITZ modes
        # Must check before @T
        if self._at(TokenType.AT_AMP):
            self._advance()
            inner = self._parse_type_primary(allow_type_args)
            return rast.RefType(span, inner, mutable=True)

        # @T (immutable reference) - works in both legacy and RERITZ modes
        if self._at(TokenType.AT):
            self._advance()
            inner = self._parse_type_primary(allow_type_args)
            return rast.RefType(span, inner, mutable=False)

        # Legacy reference types: &T, &mut T - REMOVED, emit helpful error
        if self._at(TokenType.AMP):
            # Check if this is &mut T or just &T
            if self._peek(1) and self._peek(1).type == TokenType.MUT:
                raise ParseError(
                    "Legacy `&mut T` syntax is no longer supported. Use `@&T` for mutable reference types.\n"
                    "  RERITZ migration guide:\n"
                    "    - `&mut T` → `@&T` (mutable reference type)\n"
                    "    - `data: &mut T` → `data:& T` (mutable borrow parameter)",
                    span
                )
            else:
                raise ParseError(
                    "Legacy `&T` reference syntax is no longer supported. Use `@T` for reference types.\n"
                    "  RERITZ migration guide:\n"
                    "    - `&T` → `@T` (immutable reference type)\n"
                    "    - `data: &T` → `data: T` (const borrow is the default)",
                    span
                )

        # *&T (mutable raw pointer) - must check before *T
        if self._at(TokenType.STAR_AMP):
            self._advance()
            inner = self._parse_type_primary(allow_type_args)
            return rast.PtrType(span, inner, mutable=True)

        # Pointer types: *T (immutable by default), *mut T (mutable)
        if self._at(TokenType.STAR):
            self._advance()
            mutable = False
            if self._at(TokenType.MUT):
                self._advance()
                mutable = True
            inner = self._parse_type_primary(allow_type_args)
            return rast.PtrType(span, inner, mutable)

        # Array type: [N]T or [EXPR]T, or Slice type: [T]
        # Disambiguation: if after ] there's a type, it's an array; otherwise slice
        if self._at(TokenType.LBRACKET):
            self._advance()
            # Check if this is an array size expression
            # Array sizes start with: INT, IDENT (constant), (, -, ~
            if self._at(TokenType.INT, TokenType.LPAREN, TokenType.MINUS, TokenType.TILDE):
                # Definitely an array size expression
                size_expr = self._parse_array_size_expr()
                self._expect(TokenType.RBRACKET)
                inner = self._parse_type_primary(allow_type_args)
                return rast.ArrayType(span, size_expr, inner)
            elif self._at(TokenType.IDENT):
                # Could be array size (constant) or slice type
                # Peek ahead: if after IDENT we see ] followed by a type-starting token,
                # and the token after ] is not a newline-like boundary, it's array
                saved_pos = self.pos
                ident = self._advance()  # consume IDENT
                if self._at(TokenType.RBRACKET):
                    # Peek after ]: if there's a type, it's array; otherwise slice
                    self._advance()  # consume ]
                    if self._at_type_start():
                        # Array with constant size
                        inner = self._parse_type_primary(allow_type_args)
                        return rast.ArrayType(span, rast.Ident(ident.span, ident.value), inner)
                    else:
                        # Slice type [T] where T was an identifier.
                        # `[T]` is sugar for `Span<T>` (see make_slice_type).
                        return rast.make_slice_type(span, rast.NamedType(ident.span, resolve_type_name(ident.value)))
                else:
                    # More complex expression after IDENT (e.g., SIZE * 2)
                    self.pos = saved_pos
                    size_expr = self._parse_array_size_expr()
                    self._expect(TokenType.RBRACKET)
                    inner = self._parse_type_primary(allow_type_args)
                    return rast.ArrayType(span, size_expr, inner)
            else:
                # Slice type: [T] — sugar for `Span<T>` (see make_slice_type).
                inner = self.parse_type()
                self._expect(TokenType.RBRACKET)
                return rast.make_slice_type(span, inner)

        # Tuple type: (T1, T2, ...) or (T,) or ()
        # Distinguished from grouped types by comma presence
        if self._at(TokenType.LPAREN):
            self._advance()
            # Empty tuple: ()
            if self._at(TokenType.RPAREN):
                self._advance()
                return rast.TupleType(span, [])
            # Parse first type
            first_type = self.parse_type()
            # Check for comma (tuple) vs no comma (error - grouped types not allowed in type position)
            if self._at(TokenType.COMMA):
                types = [first_type]
                while self._at(TokenType.COMMA):
                    self._advance()
                    if self._at(TokenType.RPAREN):
                        break  # Trailing comma allowed
                    types.append(self.parse_type())
                self._expect(TokenType.RPAREN)
                return rast.TupleType(span, types)
            else:
                # Single element without comma - treat as single-element tuple
                # (T) is just parenthesized for grouping, (T,) is a single-element tuple
                self._expect(TokenType.RPAREN)
                # Just a parenthesized type - return the inner type directly
                return first_type

        # Function type: fn(A, B) -> C or fn(name: A, name2: B) -> C
        # Named parameters are allowed for documentation purposes
        if self._at(TokenType.FN):
            self._advance()
            self._expect(TokenType.LPAREN)
            params = []
            if not self._at(TokenType.RPAREN):
                params.append(self._parse_fn_type_param())
                while self._at(TokenType.COMMA):
                    self._advance()
                    params.append(self._parse_fn_type_param())
            self._expect(TokenType.RPAREN)
            ret = None
            if self._at(TokenType.ARROW):
                self._advance()
                # Undelimited: a `|` after it is the caller's (#2230).
                ret = self._parse_type_primary()
            return rast.FnType(span, params, ret)

        # `dyn` is reserved: the language has no trait objects (LANGUAGE_SPEC
        # §12.2, AGAST #1620). Refused at the token, in ritz1's words (#2298).
        if self._at(TokenType.DYN):
            raise ParseError("`dyn Trait` is not supported (AGAST #1620)", self._current().span)

        # Named type (possibly with generics)
        name_tok = self._expect(TokenType.IDENT, "Expected type name")
        name = name_tok.value

        # `m.S`: there is no `module.item` access (LANGUAGE_SPEC §15.3,
        # AGAST #2215).  It used to be joined into a type name nothing
        # declares, which lowered to i8 and failed at the use, unlocated.
        if self._at(TokenType.DOT):
            parts = [name]
            while self._at(TokenType.DOT):
                self._advance()
                parts.append(self._expect(TokenType.IDENT).value)
            raise ParseError(module_item_access_removed(".".join(parts[:-1]), parts[-1]),
                             name_tok.span)

        # Handle namespace qualifier: alias::Type
        if self._at(TokenType.COLONCOLON):
            self._advance()
            qualified_name = self._expect(TokenType.IDENT, "Expected type name after '::'").value
            name = f"{name}::{qualified_name}"

        # Generic args: Type<Arg1, Arg2>.  In a cast's target (`as`), `<` may
        # equally be a comparison, so the list is read speculatively (#3124).
        if allow_type_args:
            args = self._parse_type_args()
        else:
            args = self._try_parse_cast_type_args()

        return rast.NamedType(span, resolve_type_name(name), args)

    def _parse_fn_type_param(self) -> rast.Type:
        """Parse a parameter in a function type.

        Supports:
            Type               - just a type
            name: Type         - named parameter (name is ignored, just for docs)
        """
        # Check if this looks like "name: Type" by peeking ahead
        if self._at(TokenType.IDENT):
            saved_pos = self.pos
            self._advance()  # consume potential name
            if self._at(TokenType.COLON):
                # It's "name: Type", skip the name and parse the type
                self._advance()  # consume :
                return self.parse_type()
            else:
                # It's just a type starting with an identifier
                self.pos = saved_pos
        return self.parse_type()

    # ========================================================================
    # Expressions (Pratt parser)
    # ========================================================================

    # Operator precedence (higher = binds tighter)
    # Follows C precedence: https://en.cppreference.com/w/c/language/operator_precedence
    # Note: 'and', 'or' are keyword aliases for &&, ||
    PRECEDENCE = {
        TokenType.PIPEPIPE: 1,   # ||
        TokenType.OR: 1,         # or (keyword alias for ||)
        TokenType.AMPAMP: 2,     # &&
        TokenType.AND: 2,        # and (keyword alias for &&)
        TokenType.PIPE: 3,       # |
        TokenType.CARET: 4,      # ^
        TokenType.AMP: 5,        # &
        TokenType.EQEQ: 6,       # ==
        TokenType.NEQ: 6,        # !=
        TokenType.LT: 7,         # <
        TokenType.GT: 7,         # >
        TokenType.LEQ: 7,        # <=
        TokenType.GEQ: 7,        # >=
        TokenType.LSHIFT: 8,     # <<
        TokenType.RSHIFT: 8,     # >>
        TokenType.PLUS: 9,       # +
        TokenType.MINUS: 9,      # -
        TokenType.STAR: 10,      # *
        TokenType.SLASH: 10,     # /
        TokenType.PERCENT: 10,   # %
        # Ranges bind loosest of all the binary operators (as in Rust), so
        # `a..b + 1` is `a .. (b + 1)` and `0..n as usize` is `0 .. (n as usize)`.
        # They used to bind *tighter* than arithmetic, which silently produced
        # `(a..b) + 1` and forced every consumer to un-pick it.
        TokenType.DOTDOT: 1,     # ..
        TokenType.DOTDOTEQ: 1,   # ..=
        TokenType.AS: 12,        # as (type cast) - high precedence
    }

    def _prefix_precedence(self) -> int:
        """Get precedence for prefix operators."""
        return 11  # Higher than all binary ops

    def _infix_precedence(self) -> int:
        """Get precedence for the current token as an infix operator."""
        return self.PRECEDENCE.get(self._current().type, 0)

    def parse_expr(self, min_prec: int = 0) -> rast.Expr:
        """Parse an expression with Pratt parsing."""
        left = self.parse_prefix()

        # Block expressions (if, match) don't participate in infix parsing
        # They naturally terminate at their closing block, so we shouldn't
        # look for infix operators like * which would be parsed as multiplication
        if isinstance(left, (rast.If, rast.Match)):
            return left

        while True:
            prec = self._infix_precedence()
            if prec <= min_prec:
                break

            op_tok = self._advance()

            # Skip newlines after binary operator for multi-line expressions
            # e.g., `(a >= 1) or\n  (b <= 2)` continues on the next line
            self._skip_newlines()
            self._continue_after_operator(op_tok)

            if op_tok.type == TokenType.AS:
                # Cast expression: expr as Type
                # Don't allow type args to avoid ambiguity: `x as i64 < y`
                # should parse as (x as i64) < y, not x as i64<y>.  A `|`
                # after the type is a bitwise or (#3409).
                target_type = self._parse_type_primary(allow_type_args=False)
                left = rast.Cast(left.span, left, target_type, op_tok.span)
            elif op_tok.type == TokenType.DOTDOT:
                right = self.parse_expr(prec)
                left = rast.Range(left.span, left, right, False)
            elif op_tok.type == TokenType.DOTDOTEQ:
                right = self.parse_expr(prec)
                left = rast.Range(left.span, left, right, True)  # inclusive=True
            else:
                right = self.parse_expr(prec)
                left = rast.BinOp(left.span, op_tok.value, left, right)

        return left

    def _check_unmatched_indent(self, up_to_line: int | None) -> None:
        """Raise the lexer's deferred unindent error, if any is left.

        The lexer marks a line indented between two levels instead of
        refusing it, because it may be a continuation (R46, #3387).  Once
        parsing is done (or has failed at `up_to_line`), any marker still in
        the tokens is a real error.
        """
        for tok in self.tokens:
            if (tok.type == TokenType.INDENT and tok.value == UNMATCHED_INDENT
                    and (up_to_line is None or tok.span.line <= up_to_line)):
                raise LexerError(UNMATCHED_INDENT, tok.span)

    def _continue_after_operator(self, op_tok: Token) -> None:
        """Make the line after a line-ending operator a continuation (R46).

        LARB R46 (spec §2.2, AGAST #3387): after a line ending in a binary
        operator or `as`, the next line opens and closes no block, and must
        be indented at least as far as the statement's first line.  The
        lexer laid that line out as a block (an INDENT if deeper, DEDENTs if
        shallower); only here is it known that `op_tok` was an operator, so
        the layout is re-derived with the line marked as a continuation.  A
        same-indent line (#2954) has no layout token and needs nothing.
        """
        if not self._at(TokenType.INDENT, TokenType.DEDENT):
            return
        if self.pos == 0 or self.tokens[self.pos - 1].type != TokenType.NEWLINE:
            return
        k = self.pos
        while k < len(self.tokens) and self.tokens[k].type in (
                TokenType.INDENT, TokenType.DEDENT):
            k += 1
        if k >= len(self.tokens) or self.tokens[k].type == TokenType.EOF:
            return
        line = self.tokens[k].span.line
        if line == op_tok.span.line:
            return
        previous = self.tokens
        self._continuations.add(line)
        try:
            self.tokens = relayout(previous, self._continuations)
        except LexerError as e:
            self._continuations.discard(line)
            raise ParseError(e.message, e.span)
        self._angle_splits.append((None, (previous, line)))

    def parse_prefix(self) -> rast.Expr:
        """Parse a prefix expression."""
        tok = self._current()
        span = tok.span

        # Await expression
        if self._at(TokenType.AWAIT):
            self._advance()
            operand = self.parse_prefix()
            return rast.Await(span, operand)

        # Heap allocation expression: heap expr
        if self._at(TokenType.HEAP):
            self._advance()
            operand = self.parse_prefix()
            return rast.HeapExpr(span, operand)

        # @& for taking mutable reference (address-of mutable)
        if self._at(TokenType.AT_AMP):
            self._advance()
            operand = self.parse_prefix()
            return rast.UnaryOp(span, '@&', operand)

        # @ for taking immutable reference (address-of)
        if self._at(TokenType.AT):
            self._advance()
            operand = self.parse_prefix()
            return rast.UnaryOp(span, '@', operand)

        # Unary operators
        # Note: NOT is keyword alias for BANG (!)
        # Note: AMP (&) is removed - use @ for references
        if self._at(TokenType.MINUS, TokenType.BANG, TokenType.NOT, TokenType.STAR, TokenType.TILDE):
            op = self._advance()
            operand = self.parse_prefix()
            return rast.UnaryOp(span, op.value, operand)

        # Legacy &x and &mut x - emit helpful error
        if self._at(TokenType.AMP):
            if self._peek(1) and self._peek(1).type == TokenType.MUT:
                raise ParseError(
                    "Legacy `&mut x` syntax is no longer supported. Use `@&x` for mutable references.\n"
                    "  RERITZ migration guide:\n"
                    "    - `&mut x` → `@&x` (take mutable reference)",
                    span
                )
            else:
                raise ParseError(
                    "Legacy `&x` syntax is no longer supported. Use `@x` for references.\n"
                    "  RERITZ migration guide:\n"
                    "    - `&x` → `@x` (take immutable reference)",
                    span
                )

        return self.parse_postfix()

    def parse_postfix(self) -> rast.Expr:
        """Parse postfix expressions: calls, indexing, field access, ?."""
        expr = self.parse_primary()

        # Block expressions (if, match) consume their block including DEDENT.
        # Don't allow postfix operators to continue - they belong to next statement.
        if isinstance(expr, (rast.If, rast.Match)):
            return expr

        while True:
            if self._at(TokenType.LPAREN):
                # Function call - check if the expr has type_args attached
                type_args = getattr(expr, '_type_args', [])
                self._advance()
                # Skip any newlines/indentation after opening paren (multiline calls)
                while self._at(TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                    self._advance()
                args = []
                if (isinstance(expr, rast.Ident) and expr.name == 'sizeof'
                        and self._at(TokenType.LBRACKET)):
                    # `sizeof([8]u8)`: an array type can't parse as an
                    # expression (AGAST #2124), so read it as a type.
                    ty_start = self._peek().span
                    args.append(rast.TypeExpr(ty_start, self.parse_type()))
                elif (isinstance(expr, rast.Ident) and expr.name == 'sizeof'
                        and self._at(TokenType.IDENT)
                        and self._peek(1).type == TokenType.LT
                        and (sized := self._try_parse_sizeof_generic_type()) is not None):
                    # `sizeof(Box<i64>)` (AGAST #3268): a generic instance
                    # is a type, not `Box < i64 >` comparisons.
                    args.append(sized)
                elif (isinstance(expr, rast.Ident) and expr.name == 'sizeof'
                        and self._at(TokenType.IDENT)
                        and self._current().value in TYPE_NAME_SYNONYMS
                        and self._peek(1).type == TokenType.RPAREN):
                    # `sizeof(usize)` is `sizeof(u64)` (LARB R53): the operand
                    # is read as an expression, so resolve the name here too.
                    tok = self._advance()
                    args.append(rast.Ident(tok.span, resolve_type_name(tok.value)))
                elif not self._at(TokenType.RPAREN):
                    args.append(self.parse_expr())
                    # Skip any newlines after argument
                    while self._at(TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                        self._advance()
                    while self._at(TokenType.COMMA):
                        self._advance()
                        # Skip any newlines after comma
                        while self._at(TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                            self._advance()
                        if self._at(TokenType.RPAREN):
                            break  # trailing comma
                        args.append(self.parse_expr())
                        # Skip any newlines after argument
                        while self._at(TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                            self._advance()
                self._expect(TokenType.RPAREN)
                args = self._interpolate_print_arg(expr, args)
                expr = rast.Call(expr.span, expr, args, type_args=type_args)

            elif self._at(TokenType.LBRACKET):
                # Index or Slice: a[i] or a[start:end] or a[:end] or a[start:]
                bracket = self._advance().span

                # Check for slice with empty start: [:end] or [:]
                if self._at(TokenType.COLON):
                    self._advance()
                    # [:end] or [:]
                    if self._at(TokenType.RBRACKET):
                        # [:] - full slice (equivalent to clone/copy)
                        self._advance()
                        expr = rast.SliceExpr(expr.span, expr, None, None)
                    else:
                        # [:end]
                        end = self.parse_expr()
                        self._expect(TokenType.RBRACKET)
                        expr = rast.SliceExpr(expr.span, expr, None, end)
                else:
                    # [start...] - could be [i] or [start:] or [start:end]
                    first = self.parse_expr()
                    if self._at(TokenType.COLON):
                        self._advance()
                        # [start:end] or [start:]
                        if self._at(TokenType.RBRACKET):
                            # [start:] - from start to end
                            self._advance()
                            expr = rast.SliceExpr(expr.span, expr, first, None)
                        else:
                            # [start:end]
                            end = self.parse_expr()
                            self._expect(TokenType.RBRACKET)
                            expr = rast.SliceExpr(expr.span, expr, first, end)
                    else:
                        # [i] - simple index
                        self._expect(TokenType.RBRACKET)
                        expr = rast.Index(expr.span, expr, first, bracket)

            elif self._at(TokenType.DOT):
                # Field access, tuple field access, or method call
                self._advance()
                # Check for tuple field access: expr.0, expr.1, etc.
                if self._at(TokenType.INT):
                    field_tok = self._advance()
                    field_name = str(field_tok.value)
                    # At the number: `h.0` of a struct is refused there (#3233).
                    expr = rast.Field(expr.span, expr, field_name, field_tok.span)
                else:
                    field_tok = self._expect(TokenType.IDENT)
                    if self._at(TokenType.LPAREN):
                        # Method call
                        self._advance()
                        # Skip any newlines/indentation after opening paren (multiline calls)
                        while self._at(TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                            self._advance()
                        args = []
                        if not self._at(TokenType.RPAREN):
                            args.append(self.parse_expr())
                            # Skip any newlines after argument
                            while self._at(TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                                self._advance()
                            while self._at(TokenType.COMMA):
                                self._advance()
                                # Skip any newlines after comma
                                while self._at(TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                                    self._advance()
                                if self._at(TokenType.RPAREN):
                                    break
                                args.append(self.parse_expr())
                                # Skip any newlines after argument
                                while self._at(TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                                    self._advance()
                        self._expect(TokenType.RPAREN)
                        expr = rast.MethodCall(expr.span, expr, field_tok.value, args,
                                               field_tok.span)
                    else:
                        expr = rast.Field(expr.span, expr, field_tok.value, field_tok.span)

            elif self._at(TokenType.STAR) and self._peek(1).type == TokenType.STAR:
                # Postfix dereference: expr** (followed by . or [ or ()
                # Disambiguate from multiplication + prefix deref (a * *b):
                # expr** is postfix deref only when followed by DOT, LBRACKET,
                # LPAREN, or another ** (chained deref). Otherwise it's
                # multiplication and prefix deref handled by parse_expr.
                peek2_type = self._peek(2).type
                if peek2_type in (TokenType.DOT, TokenType.LBRACKET, TokenType.LPAREN,
                                  TokenType.STAR):
                    self._advance()  # consume first *
                    self._advance()  # consume second *
                    expr = rast.UnaryOp(expr.span, '*', expr)
                else:
                    break

            elif self._at(TokenType.QUESTION):
                # Try operator
                self._advance()
                expr = rast.TryOp(expr.span, expr)

            else:
                break

        return expr

    def parse_primary(self) -> rast.Expr:
        """Parse a primary expression."""
        tok = self._current()
        span = tok.span

        # Closure: |params| body
        if self._at(TokenType.PIPE):
            return self.parse_closure()

        # Integer literal (with optional type suffix: `0u32`)
        if self._at(TokenType.INT):
            self._advance()
            return self._apply_literal_suffix(rast.IntLit(span, tok.value), tok)

        # Float literal (with optional type suffix: `1.5f32`)
        if self._at(TokenType.FLOAT):
            self._advance()
            return self._apply_literal_suffix(rast.FloatLit(span, tok.value), tok)

        # String literal
        if self._at(TokenType.STRING):
            self._advance()
            return rast.StringLit(span, tok.value, tok.print_value, tok.interp)

        # C-string literal: c"..."
        if self._at(TokenType.CSTRING):
            self._advance()
            return rast.CStringLit(span, tok.value)

        # Note: s"..." (SPAN_STRING) was removed in AGAST #98 — bare "..."
        # now produces StrView which is layout-compatible.

        # Character literal (u8)
        if self._at(TokenType.CHAR):
            self._advance()
            return rast.CharLit(span, tok.value)

        # Boolean literals
        if self._at(TokenType.TRUE):
            self._advance()
            return rast.BoolLit(span, True)
        if self._at(TokenType.FALSE):
            self._advance()
            return rast.BoolLit(span, False)

        # Null pointer literal
        if self._at(TokenType.NULL):
            self._advance()
            return rast.NullLit(span)

        # Identifier, possibly with :: qualifier, generic type arguments, or struct literal
        if self._at(TokenType.IDENT):
            name = self._advance().value

            # Check for qualified identifier: alias::name
            if self._at(TokenType.COLONCOLON):
                self._advance()
                qualified_name = self._expect(TokenType.IDENT, "Expected identifier after '::'").value
                return rast.QualifiedIdent(span, qualifier=name, name=qualified_name)

            # Try to parse generic type arguments: Name<T, U>
            # This is tricky because < is also used for comparison
            # We use lookahead: if < is followed by an identifier and eventually >,
            # and then { or (, treat it as type args
            type_args = []
            if self._at(TokenType.LT):
                type_args = self._try_parse_type_args_for_expr()

            # Check for struct literal: Name { field: value, ... } or Name<T> { ... }
            if self._at(TokenType.LBRACE):
                self._advance()
                fields = []
                # Skip any newlines/indentation after opening brace
                while self._at(TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                    self._advance()
                while not self._at(TokenType.RBRACE, TokenType.EOF):
                    # Skip any newlines/indentation between fields
                    while self._at(TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                        self._advance()
                    if self._at(TokenType.RBRACE):
                        break
                    # Parse field name
                    if not self._at(TokenType.IDENT):
                        raise ParseError("Expected field name in struct literal", self._current().span)
                    field_name = self._advance().value

                    self._expect(TokenType.COLON, "Expected ':' after field name in struct literal")

                    # Parse field value
                    field_value = self.parse_expr()
                    fields.append((field_name, field_value))

                    # Skip any newlines after field value
                    while self._at(TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                        self._advance()

                    if self._at(TokenType.COMMA):
                        self._advance()
                        # Skip any newlines after comma
                        while self._at(TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                            self._advance()
                        if self._at(TokenType.RBRACE):
                            break
                    elif not self._at(TokenType.RBRACE):
                        raise ParseError("Expected ',' or '}' in struct literal", self._current().span)

                self._expect(TokenType.RBRACE, "Expected '}' to close struct literal")
                return rast.StructLit(span, name, fields, type_args=type_args)
            elif type_args:
                # We have type_args but no struct literal - this is a generic identifier
                # that will be used in a call like foo<T>(args)
                # Store as Ident with attached type_args for now (handled in postfix)
                ident = rast.Ident(span, name)
                ident._type_args = type_args  # Temporary attribute for postfix handling
                return ident
            else:
                return rast.Ident(span, name)

        # Parenthesized expression or tuple literal
        if self._at(TokenType.LPAREN):
            self._advance()

            # Empty tuple: ()
            if self._at(TokenType.RPAREN):
                self._advance()
                return rast.TupleLit(span, [])

            # Parse first expression
            first_expr = self.parse_expr()

            # Check for comma (tuple) vs no comma (grouped expression)
            if self._at(TokenType.COMMA):
                # It's a tuple literal: (expr1, expr2, ...) or (expr,)
                elements = [first_expr]
                while self._at(TokenType.COMMA):
                    self._advance()
                    if self._at(TokenType.RPAREN):
                        break  # Trailing comma allowed
                    elements.append(self.parse_expr())
                self._expect(TokenType.RPAREN)
                return rast.TupleLit(span, elements)
            else:
                # Single grouped expression: (expr)
                self._expect(TokenType.RPAREN)
                return first_expr

        # If expression
        if self._at(TokenType.IF):
            return self.parse_if()

        # Match expression
        if self._at(TokenType.MATCH):
            return self.parse_match()

        # Lambda
        if self._at(TokenType.FN):
            return self.parse_lambda()

        # Array literal: [a, b, c] or array fill: [value; count]
        # Supports multiline for readability (like struct literals)
        if self._at(TokenType.LBRACKET):
            self._advance()
            # Skip newlines after opening bracket
            while self._at(TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                self._advance()
            elements = []
            if not self._at(TokenType.RBRACKET):
                first = self.parse_expr()
                # Check for fill syntax: [value; count]
                if self._at(TokenType.SEMI):
                    self._advance()
                    count_expr = self.parse_expr()
                    if not isinstance(count_expr, rast.IntLit):
                        raise ParseError("Array fill count must be an integer literal", count_expr.span)
                    self._expect(TokenType.RBRACKET)
                    return rast.ArrayFill(span, first, count_expr.value)
                # Regular array literal
                elements.append(first)
                # Skip newlines after first element
                while self._at(TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                    self._advance()
                while self._at(TokenType.COMMA):
                    self._advance()
                    # Skip newlines after comma
                    while self._at(TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                        self._advance()
                    if self._at(TokenType.RBRACKET):
                        break  # trailing comma
                    elements.append(self.parse_expr())
                    # Skip newlines after element
                    while self._at(TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                        self._advance()
            self._expect(TokenType.RBRACKET)
            return rast.ArrayLit(span, elements)

        raise ParseError(f"Expected expression, got {tok.type.name}", span)

    def parse_if(self) -> rast.If:
        """Parse an if expression.

        Supports both block-style and ternary style:
            if cond                           # block style
                body
            else
                other

            if cond then a else b             # ternary style (single line)
        """
        span = self._current().span
        self._expect(TokenType.IF)
        cond = self.parse_expr()

        # Check for ternary style: if cond then a else b
        if self._at(TokenType.THEN):
            self._advance()
            then_expr = self.parse_expr()
            self._expect(TokenType.ELSE)
            else_expr = self.parse_expr()
            # Wrap expressions in blocks for consistency
            then_block = rast.Block(then_expr.span, [], then_expr)
            else_block = rast.Block(else_expr.span, [], else_expr)
            return rast.If(span, cond, then_block, else_block)

        # Block style
        self._refuse_block_in_brackets(span)
        then_block = self.parse_block()

        else_block = None
        if self._at(TokenType.ELSE):
            self._advance()
            if self._at(TokenType.IF):
                # else if -> nested if in else block
                nested_if = self.parse_if()
                else_block = rast.Block(nested_if.span, [], nested_if)
            else:
                else_block = self.parse_block()

        return rast.If(span, cond, then_block, else_block)

    def _refuse_block_in_brackets(self, keyword: Span) -> None:
        """LARB R46a: a block `if` / `match` can't open inside ( [ {."""
        bracket = self._in_brackets.get((keyword.line, keyword.column))
        if bracket is not None:
            raise ParseError(block_in_brackets_message(bracket), keyword)

    def parse_match(self) -> rast.Match:
        """Parse a match expression."""
        span = self._current().span
        self._refuse_block_in_brackets(span)
        self._expect(TokenType.MATCH)
        expr = self.parse_expr()
        # Skip newline before expecting indent (match x\n    ...)
        self._skip_newlines()
        self._expect(TokenType.INDENT)

        arms = []
        while not self._at(TokenType.DEDENT, TokenType.EOF):
            arm = self.parse_match_arm()
            arms.append(arm)

        if self._at(TokenType.DEDENT):
            self._advance()

        return rast.Match(span, expr, arms)

    def parse_match_arm(self) -> rast.MatchArm:
        """Parse a match arm.

        Supports both single-line and multiline arms:
            Ok(x) => x + 1                    # single expression
            Err(e) =>                         # multiline block
                log(e)
                return -1
        """
        span = self._current().span
        pattern = self.parse_pattern()

        # Match-arm guards (`n if n == 4 => ...`) are not part of the language
        # (docs/LANGUAGE_SPEC.md; ritz1 does not parse them). ritz0 once parsed
        # them, but the emitter ignored the guard and always took the arm, a
        # silent miscompile (AGAST #1939). Refuse them until they are specified.
        if self._at(TokenType.IF):
            raise ParseError(
                "match-arm guards (`pattern if cond => ...`) are not supported; "
                "move the condition into the arm body",
                self._current().span,
            )
        guard = None

        self._expect(TokenType.FATARROW)

        # Check for multiline arm: => followed by newline+indent
        if self._at(TokenType.NEWLINE):
            self._skip_newlines()  # Skip all newlines (handles comments producing extra NEWLINEs)
            if self._at(TokenType.INDENT):
                # Multiline: parse as block
                body = self.parse_block()
            else:
                # Just newline, then next arm - error
                raise ParseError("Expected expression or indented block after '=>'", span)
        else:
            # Single line: parse expression or control flow statement
            body = self.parse_match_arm_body()
            # Skip newline after arm body
            self._skip_newlines()

        return rast.MatchArm(span, pattern, guard, body)

    def parse_match_arm_body(self) -> rast.Expr:
        """Parse a single-line match arm body.

        Supports regular expressions plus control flow and assignments:
            Some(x) => x + 1
            None => continue
            None => break
            None => return -1
            Some(x) => self.field = x   (assignment as side-effect)
        """
        span = self._current().span

        # continue as expression
        if self._at(TokenType.CONTINUE):
            self._advance()
            return rast.ContinueExpr(span)

        # break as expression
        if self._at(TokenType.BREAK):
            self._advance()
            return rast.BreakExpr(span)

        # return as expression
        if self._at(TokenType.RETURN):
            self._advance()
            # Check if there's a value (not at newline/EOF)
            if not self._at(TokenType.NEWLINE, TokenType.EOF, TokenType.DEDENT):
                value = self.parse_expr()
                return rast.ReturnExpr(span, value)
            return rast.ReturnExpr(span, None)

        # Parse expression - but check for assignment after
        expr = self.parse_expr()

        # Check for assignment (convert to AssignExpr for match arm context)
        if self._at(TokenType.EQ):
            self._advance()
            value = self.parse_expr()
            return rast.AssignExpr(span, expr, value)

        return expr

    def parse_pattern(self) -> rast.Pattern:
        """Parse a pattern."""
        span = self._current().span

        # Wildcard
        if self._at(TokenType.IDENT) and self._current().value == '_':
            self._advance()
            return rast.WildcardPattern(span)

        # Literal patterns
        if self._at(TokenType.INT):
            val = self._advance().value
            return rast.LitPattern(span, val)
        if self._at(TokenType.STRING):
            val = self._advance().value
            return rast.LitPattern(span, val)
        if self._at(TokenType.TRUE):
            self._advance()
            return rast.LitPattern(span, True)
        if self._at(TokenType.FALSE):
            self._advance()
            return rast.LitPattern(span, False)

        # A type isn't a pattern (LARB R52, AGAST #3409): `*T`, `&T` and a
        # primitive type name were the union arms of `match v` on a removed
        # `A | B` type.  Refused at the pattern.
        if self._at(TokenType.STAR, TokenType.AMP):
            raise ParseError(TYPE_PATTERN_REFUSED, span)

        # Identifier or variant pattern
        if self._at(TokenType.IDENT):
            name = self._current().value

            if name in ('i8', 'i16', 'i32', 'i64', 'u8', 'u16', 'u32', 'u64', 'bool'):
                raise ParseError(TYPE_PATTERN_REFUSED, span)

            # Otherwise consume as identifier
            self._advance()

            # Check for qualified variant pattern: Type.Variant or Type.Variant(fields)
            qualifier = None
            if self._at(TokenType.DOT):
                self._advance()
                if not self._at(TokenType.IDENT):
                    raise ParseError(f"Expected variant name after '.', got {self._current().type.name}", span)
                qualifier = name
                name = self._advance().value

            # Variant with fields: Some(x) or Type.Some(x)
            if self._at(TokenType.LPAREN):
                self._advance()
                fields = []
                if not self._at(TokenType.RPAREN):
                    fields.append(self.parse_pattern())
                    while self._at(TokenType.COMMA):
                        self._advance()
                        if self._at(TokenType.RPAREN):
                            break
                        fields.append(self.parse_pattern())
                self._expect(TokenType.RPAREN)
                return rast.VariantPattern(span, name, fields, qualifier)

            # Qualified variant without fields: Type.None
            if qualifier:
                return rast.VariantPattern(span, name, [], qualifier)

            # Simple identifier pattern
            return rast.IdentPattern(span, name, False)

        raise ParseError(f"Expected pattern, got {self._current().type.name}", span)

    def parse_lambda(self) -> rast.Lambda:
        """Parse a lambda/closure."""
        span = self._current().span
        self._expect(TokenType.FN)
        self._expect(TokenType.LPAREN)

        params = []
        if not self._at(TokenType.RPAREN):
            params.append(self.parse_param())
            while self._at(TokenType.COMMA):
                self._advance()
                if self._at(TokenType.RPAREN):
                    break
                params.append(self.parse_param())
        self._expect(TokenType.RPAREN)

        ret_type = None
        if self._at(TokenType.ARROW):
            self._advance()
            ret_type = self.parse_type()

        body = self.parse_expr()
        return rast.Lambda(span, params, ret_type, body)

    def _apply_literal_suffix(self, lit, tok):
        """Apply a numeric literal's type suffix: `0u32` -> `0 as u32`.

        Lowering to a cast keeps one representation of "this literal has this
        type" for every downstream pass.
        """
        suffix = getattr(tok, 'suffix', None)
        if not suffix:
            return lit
        return rast.Cast(lit.span, lit, rast.NamedType(lit.span, resolve_type_name(suffix), []))

    def parse_closure(self) -> rast.Closure:
        """Parse a closure expression: |params| body.

        Examples:
            |x| x * 2           - single param, inferred type
            |x, y| x + y        - multiple params
            |x: i32| x * 2      - explicit param type
            || 42               - zero params
        """
        span = self._current().span
        self._expect(TokenType.PIPE)

        params = []
        if not self._at(TokenType.PIPE):
            params.append(self._parse_closure_param())
            while self._at(TokenType.COMMA):
                self._advance()
                if self._at(TokenType.PIPE):
                    break  # trailing comma
                params.append(self._parse_closure_param())
        self._expect(TokenType.PIPE)

        body = self.parse_expr()
        return rast.Closure(span, params, body)

    def _parse_closure_param(self) -> rast.ClosureParam:
        """Parse a closure parameter: name or name: type."""
        name_tok = self._expect(TokenType.IDENT, "Expected parameter name")
        param_type = None
        if self._at(TokenType.COLON):
            self._advance()
            # `|` closes the param list here (#2230).
            param_type = self._parse_type_primary()
        return rast.ClosureParam(name_tok.value, param_type, name_tok.span)

    # ========================================================================
    # Statements
    # ========================================================================

    def parse_block(self) -> rast.Block:
        """Parse an indented block."""
        span = self._current().span
        self._skip_newlines()
        self._expect(TokenType.INDENT)

        stmts = []
        while not self._at(TokenType.DEDENT, TokenType.EOF):
            stmt = self.parse_stmt()
            stmts.append(stmt)
            self._skip_newlines()  # Skip newlines after each statement

        if self._at(TokenType.DEDENT):
            self._advance()

        # Check if last statement is an expression (becomes block value)
        expr = None
        if stmts and isinstance(stmts[-1], rast.ExprStmt):
            expr = stmts[-1].expr
            stmts = stmts[:-1]

        return rast.Block(span, stmts, expr)

    def parse_stmt(self) -> rast.Stmt:
        """Parse a statement."""
        tok = self._current()
        span = tok.span

        # Let binding
        if self._at(TokenType.LET):
            return self.parse_let()

        # Var binding
        if self._at(TokenType.VAR):
            return self.parse_var()

        # Assert
        if self._at(TokenType.ASSERT):
            self._advance()
            condition = self.parse_expr()
            message = None
            # Optional message: `assert x, "error message"`.  Accept either
            # bare-string ("...") or c-string (c"...") form — both lex with
            # the same payload, and the message is just text the emitter
            # bakes into a global cstr at compile time.  Older code uses
            # c"..."; idiomatic ritz prefers "..." (StrView).
            if self._at(TokenType.COMMA):
                self._advance()
                if self._at(TokenType.STRING) or self._at(TokenType.CSTRING):
                    message = self._advance().value
            return rast.AssertStmt(span, condition, message)

        # Return
        if self._at(TokenType.RETURN):
            self._advance()
            value = None
            if not self._at(TokenType.DEDENT, TokenType.EOF, TokenType.NEWLINE):
                value = self.parse_expr()
            return rast.ReturnStmt(span, value)

        # Break
        if self._at(TokenType.BREAK):
            self._advance()
            return rast.BreakStmt(span)

        # Continue
        if self._at(TokenType.CONTINUE):
            self._advance()
            return rast.ContinueStmt(span)

        # Defer (LANGUAGE_SPEC §13.7)
        if self._at(TokenType.DEFER):
            return self.parse_defer()

        # While
        if self._at(TokenType.WHILE):
            self._advance()
            cond = self.parse_expr()
            body = self.parse_block()
            return rast.WhileStmt(span, cond, body)

        # Loop (infinite loop - syntactic sugar for while true)
        if self._at(TokenType.LOOP):
            self._advance()
            body = self.parse_block()
            cond = rast.BoolLit(span, True)
            return rast.WhileStmt(span, cond, body)

        # For
        if self._at(TokenType.FOR):
            self._advance()
            var_tok = self._expect(TokenType.IDENT)
            self._expect(TokenType.IN)
            iter_expr = self.parse_expr()
            body = self.parse_block()
            return rast.ForStmt(span, var_tok.value, iter_expr, body, var_tok.span)

        # Asm (inline assembly)
        if self._at(TokenType.ASM):
            return self.parse_asm()

        # Unsafe block
        if self._at(TokenType.UNSAFE):
            return self.parse_unsafe()

        # Expression statement (possibly assignment)
        expr = self.parse_expr()

        # Check for assignment
        if self._at(TokenType.EQ, TokenType.PLUSEQ, TokenType.MINUSEQ,
                    TokenType.STAREQ, TokenType.SLASHEQ):
            op_tok = self._advance()
            value = self.parse_expr()
            if op_tok.type != TokenType.EQ:
                # Desugar += to = ... + ...
                op = {
                    TokenType.PLUSEQ: '+',
                    TokenType.MINUSEQ: '-',
                    TokenType.STAREQ: '*',
                    TokenType.SLASHEQ: '/',
                }[op_tok.type]
                value = rast.BinOp(span, op, expr, value)
                return rast.AssignStmt(span, expr, value, op)
            return rast.AssignStmt(span, expr, value)

        return rast.ExprStmt(span, expr)

    def parse_defer(self) -> rast.DeferStmt:
        """`defer <stmt>` or `defer` + an indented block (LANGUAGE_SPEC §13.7).

        The refusals that need only the syntax are made here, all located at
        the `defer`: a bare `defer`, a deferred `let`/`var`, and a `return`,
        `?`, `break` or `continue` that would leave the deferred statement.
        (A moved-before-exit name is the move checker's.)
        """
        span = self._expect(TokenType.DEFER).span
        if self._at(TokenType.NEWLINE, TokenType.DEDENT, TokenType.EOF):
            # The block form: an indented block must follow.
            save = self.pos
            self._skip_newlines()
            if not self._at(TokenType.INDENT):
                self.pos = save
                raise ParseError("`defer` needs a statement", span)
            self.pos = save
            block = self.parse_block()
            if block.expr is not None:
                # Its value is discarded: keep it as a statement.
                block.stmts.append(rast.ExprStmt(block.expr.span, block.expr))
                block.expr = None
        else:
            stmt = self.parse_stmt()
            if isinstance(stmt, (rast.LetStmt, rast.VarStmt, rast.LetTupleStmt)):
                raise ParseError("a deferred `let` or `var` would die at once", span)
            block = rast.Block(stmt.span, [stmt], None)
        escape = _defer_escape(block, in_loop=False)
        if escape is not None:
            raise ParseError(f"`{escape}` can't leave a deferred statement", span)
        return rast.DeferStmt(span, block)

    def parse_let(self) -> rast.Stmt:
        """Parse a let binding.

        Supports both regular bindings and tuple destructuring:
            let x = expr
            let x: T = expr
            let (a, b, c) = expr
        """
        span = self._current().span
        self._expect(TokenType.LET)

        # Check for tuple destructuring: let (a, b, ...) = expr
        if self._at(TokenType.LPAREN):
            self._advance()
            names = []
            name_spans = []
            while not self._at(TokenType.RPAREN):
                name_tok = self._expect(TokenType.IDENT)
                names.append(name_tok.value)
                name_spans.append(name_tok.span)
                if self._at(TokenType.COMMA):
                    self._advance()
                else:
                    break
            self._expect(TokenType.RPAREN)
            self._expect(TokenType.EQ)
            value = self.parse_expr()
            return rast.LetTupleStmt(span, names, value, name_spans)

        # Regular binding
        name_tok = self._expect(TokenType.IDENT)

        type_ann = None
        if self._at(TokenType.COLON):
            self._advance()
            type_ann = self.parse_type()

        value = None
        if self._at(TokenType.EQ):
            self._advance()
            value = self.parse_expr()

        return rast.LetStmt(span, name_tok.value, type_ann, value, name_tok.span)

    def parse_var(self) -> rast.VarStmt:
        """Parse a var binding."""
        span = self._current().span
        self._expect(TokenType.VAR)
        name_tok = self._expect(TokenType.IDENT)

        type_ann = None
        if self._at(TokenType.COLON):
            self._advance()
            type_ann = self.parse_type()

        value = None
        if self._at(TokenType.EQ):
            self._advance()
            value = self.parse_expr()

        return rast.VarStmt(span, name_tok.value, type_ann, value, name_tok.span)

    def parse_asm(self) -> rast.AsmStmt:
        """Parse an inline assembly block (LANGUAGE_SPEC §18.6, AGAST #3396).

        Syntax:
            asm <arch> (<clause>, ...)?:
                <assembly text line>
                ...
            clause := (in | out | inout) NAME (: REG)? | clobber REG

        The lexer hands over each body line whole, as an ASM_LINE.  Every
        §18.6 error that needs no types is reported here, located, in
        ritz1's words (ritz1/src/ast_helpers.ritz stmt_asm); the [[naked]]
        rules are checked with the fn (_check_naked_asm), and the ones that
        need types by the emitter (_emit_asm).
        """
        span = self._current().span
        self._expect(TokenType.ASM)
        arch_tok = self._expect(TokenType.IDENT)
        if arch_tok.value not in ASM_ARCHES:
            raise ParseError(
                f"unknown asm architecture '{arch_tok.value}' (known: x86_64)", arch_tok.span)
        stmt = rast.AsmStmt(span, arch=arch_tok.value, arch_span=arch_tok.span)

        if self._at(TokenType.LPAREN):
            self._advance()
            pinned = set()
            while True:
                self._parse_asm_clause(stmt, pinned)
                if not self._at(TokenType.COMMA):
                    break
                self._advance()
            self._expect(TokenType.RPAREN, "expected ',' or ')' in an asm clause list")

        self._expect(TokenType.COLON)
        self._expect(TokenType.NEWLINE)
        self._expect(TokenType.INDENT)
        while self._at(TokenType.ASM_LINE):
            tok = self._advance()
            stmt.lines.append((tok.value, tok.span))
            self._check_asm_label(tok)
            self._scan_asm_line(stmt, tok)
            if self._at(TokenType.NEWLINE):
                self._advance()
        if self._at(TokenType.DEDENT):
            self._advance()

        # An unpinned clause operand has no register but the one {name} picks.
        for o in stmt.operands:
            if o.in_clause and o.reg is None and o.text_span is None:
                raise ParseError(
                    f"asm operand '{o.name}' is in a clause but not in the text: "
                    "write {name} or pin it to a register", o.span)
        return stmt

    def _parse_asm_clause(self, stmt: rast.AsmStmt, pinned: set) -> None:
        """One clause of `stmt`'s list; `pinned` holds the registers pinned so far."""
        kind_tok = self._current()
        if kind_tok.type == TokenType.IN:
            kind = 'in'
        elif kind_tok.type == TokenType.IDENT:
            kind = kind_tok.value
        else:
            raise ParseError("expected an asm clause (in, out, inout or clobber)", kind_tok.span)
        if kind not in ('in', 'out', 'inout', 'clobber'):
            raise ParseError(
                f"unknown asm clause '{kind}' (in, out, inout or clobber)", kind_tok.span)
        self._advance()
        if stmt.first_clause is None:
            stmt.first_clause = kind_tok.span
        name_tok = self._expect(TokenType.IDENT, f"expected a name after '{kind}'")
        reg_tok = None
        if self._at(TokenType.COLON):
            self._advance()
            reg_tok = self._expect(TokenType.IDENT, "expected a register after ':'")
        if kind == 'clobber':
            if reg_tok is not None:
                raise ParseError(
                    f"'clobber' takes one register, not '{name_tok.value}: ...'", reg_tok.span)
            stmt.clobbers.append(_asm_reg(name_tok))
            return
        if any(o.name == name_tok.value for o in stmt.operands):
            raise ParseError(f"'{name_tok.value}' is named in two asm clauses", name_tok.span)
        reg = None
        if reg_tok is not None:
            reg = _asm_reg(reg_tok)
            if reg in pinned:
                raise ParseError(f"asm register '{reg_tok.value}' is pinned twice", reg_tok.span)
            pinned.add(reg)
        stmt.operands.append(rast.AsmOperand(
            name_tok.value, kind, name_tok.span, reg=reg, in_clause=True))

    @staticmethod
    def _check_asm_label(tok) -> None:
        """A named label at the start of an asm line (`loop:`, `.L1:`) is an
        error: only numeric local labels (`1:`) are allowed (§18.6, #1371)."""
        m = ASM_NAMED_LABEL.match(tok.value)
        if m:
            raise ParseError(
                f"named label '{m.group(1)}' in asm: use a numeric local label "
                "(1:, jumped to as 1b or 1f)", tok.span)

    @staticmethod
    def _scan_asm_line(stmt: rast.AsmStmt, tok) -> None:
        """The `{name}`s of an asm line: each name no operand has yet becomes
        an input (its span the name's, its text_span the `{`); each operand found is marked as in the text.  `{{` and `}}`
        are a literal brace.  A `{` that isn't closed, or isn't a name, is an
        error."""
        text, span = tok.value, tok.span
        i = 0
        while i < len(text):
            if text.startswith('{{', i) or text.startswith('}}', i):
                i += 2
                continue
            if text[i] != '{':
                i += 1
                continue
            at = Span(span.file, span.line, span.column + i, 1)
            m = ASM_OPERAND.match(text, i)
            if m is None:
                what = "is not closed" if '}' not in text[i + 1:] else "must be followed by a name and '}'"
                raise ParseError(f"'{{' in asm {what} (write '{{{{' for a literal '{{')", at)
            name = m.group(1)
            o = next((o for o in stmt.operands if o.name == name), None)
            if o is None:
                # Located at its name, as ritz1 locates the typed errors.
                o = rast.AsmOperand(name, 'in', Span(span.file, span.line, span.column + i + 1, len(name)))
                stmt.operands.append(o)
            if o.text_span is None:
                o.text_span = at
            i = m.end()

    def _check_naked_asm(self, body: rast.Block) -> None:
        """The [[naked]] rules (§18.6, §17.5): the body holds only asm
        blocks, and they take no clause and no `{name}`: there is no frame."""
        for stmt in body.stmts:
            if not isinstance(stmt, rast.AsmStmt):
                raise ParseError(
                    "a [[naked]] fn body may contain only asm blocks", stmt.span)
            if stmt.first_clause is not None:
                raise ParseError(
                    "an asm block in a [[naked]] fn takes no clauses", stmt.first_clause)
            for o in stmt.operands:
                if o.text_span is not None:
                    raise ParseError(
                        f"an asm block in a [[naked]] fn takes no {{name}}: '{o.name}' "
                        "has no frame to live in", o.text_span)
        if body.expr is not None:
            raise ParseError(
                "a [[naked]] fn body may contain only asm blocks", body.expr.span)

    def parse_unsafe(self) -> rast.UnsafeBlock:
        """Parse an unsafe block.

        Syntax:
            unsafe
                <statements>

        Example:
            unsafe
                let ptr = 0xB8000 as *u16
                *ptr = (0x0F << 8) | (char as u16)

        Unsafe blocks allow raw pointer operations that would normally
        require safety checks. This makes unsafe code explicit and auditable.
        """
        span = self._current().span
        self._expect(TokenType.UNSAFE)

        # Parse the block body (indented statements)
        body = self.parse_block()

        return rast.UnsafeBlock(span=span, body=body)

    # ========================================================================
    # Items (top-level)
    # ========================================================================

    def parse_param(self, impl_type: rast.Type = None) -> rast.Param:
        """Parse a function parameter.

        Legacy syntax:
            name: Type

        RERITZ syntax:
            name: Type     -> const borrow (CONST)
            name:& Type    -> mutable borrow (MUTABLE)
            name:= Type    -> move ownership (MOVE)

        In impl blocks, bare 'self' is allowed:
            self           -> self: ImplType (const borrow)
            self:&         -> self:& ImplType (mutable borrow)
        """
        span = self._current().span
        name_tok = self._expect(TokenType.IDENT)

        # Determine borrow semantics from the colon variant
        borrow = rast.Borrow.CONST  # Default

        if self._at(TokenType.COLON_AMP):
            self._advance()
            # Check for bare self:& (no type follows, only RPAREN or COMMA)
            if name_tok.value == 'self' and impl_type and self._at(TokenType.RPAREN, TokenType.COMMA):
                return rast.Param(span, name_tok.value, impl_type, borrow=rast.Borrow.MUTABLE)
            borrow = rast.Borrow.MUTABLE
        elif self._at(TokenType.COLON_EQ):
            self._advance()
            borrow = rast.Borrow.MOVE
        elif self._at(TokenType.COLON):
            self._advance()
        else:
            # No colon - check for bare 'self' in impl context
            if name_tok.value == 'self' and impl_type:
                return rast.Param(span, name_tok.value, impl_type, borrow=rast.Borrow.CONST)
            raise ParseError(f"Expected ':' after parameter name '{name_tok.value}'", span)

        param_type = self.parse_type()
        return rast.Param(span, name_tok.value, param_type, borrow=borrow)

    def parse_attrs(self) -> List[rast.Attr]:
        """Parse a list of attributes before an item.

        Syntax: [[attr]], [[attr, attr2]], [[attr("arg")]]
        """
        attrs = []

        # Parse [[attr]] syntax
        while self._at(TokenType.LBRACKET2):
            self._advance()  # consume [[
            # Parse comma-separated attributes
            if not self._at_double_rbracket():
                attrs.append(self._parse_single_attr())
                while self._at(TokenType.COMMA):
                    self._advance()
                    if self._at_double_rbracket():
                        break
                    attrs.append(self._parse_single_attr())
            self._expect_double_rbracket()
            self._skip_newlines()

        return attrs

    def _parse_single_attr(self) -> rast.Attr:
        """Parse a single attribute: name, name("arg", ...), or name = "value".

        Attributes are a closed set (LANGUAGE_SPEC §17, AGAST #1847): an
        unknown name, or a known one in the wrong form, is a located error.
        They used to be accepted and ignored, which is how `[[cfg(...)]]`
        sat in a test file meaning nothing.
        """
        attr = self._parse_single_attr_syntax()
        if attr.name not in ATTRS:
            raise ParseError(
                f"unknown attribute '{attr.name}' (known: {', '.join(sorted(ATTRS))})",
                attr.span)
        takes_value = ATTRS[attr.name][0]
        if attr.args:
            raise ParseError(f"attribute '{attr.name}' takes no arguments", attr.span)
        if takes_value and attr.value is None:
            raise ParseError(f"attribute '{attr.name}' needs a value: [[{attr.name} = \"...\"]]",
                             attr.span)
        if not takes_value and attr.value is not None:
            raise ParseError(f"attribute '{attr.name}' takes no value: [[{attr.name}]]",
                             attr.span)
        if attr.name == "callconv" and attr.value not in CALLCONVS:
            raise ParseError(
                f"unknown calling convention '{attr.value}' (known: {', '.join(CALLCONVS)})",
                attr.span)
        return attr

    def _check_attrs_apply(self, attrs: List[rast.Attr], kind: str) -> None:
        """Reject an attribute on an item kind it does not apply to (#1847)."""
        for attr in attrs:
            kinds = ATTRS[attr.name][1]
            if kind not in kinds:
                raise ParseError(
                    f"attribute '{attr.name}' applies to {' or '.join(kinds)} items, not {kind}",
                    attr.span)

    def _parse_single_attr_syntax(self) -> rast.Attr:
        name_tok = self._expect(TokenType.IDENT, "Expected attribute name")
        args = []
        value = None

        if self._at(TokenType.EQ):
            # Handle [[attr = "value"]] syntax
            self._advance()  # consume =
            if self._at(TokenType.STRING):
                value = self._advance().value
            else:
                raise SyntaxError(f"Expected string value after '=' in attribute, got {self._current().type}")
        elif self._at(TokenType.LPAREN):
            self._advance()
            if not self._at(TokenType.RPAREN):
                # Parse attribute arguments (strings for now)
                if self._at(TokenType.STRING):
                    args.append(self._advance().value)
                while self._at(TokenType.COMMA):
                    self._advance()
                    if self._at(TokenType.RPAREN):
                        break
                    if self._at(TokenType.STRING):
                        args.append(self._advance().value)
            self._expect(TokenType.RPAREN)

        return rast.Attr(name_tok.value, args, value, span=name_tok.span)

    def parse_fn(self, attrs: List[rast.Attr] = None, is_async: bool = False, is_pub: bool = False,
                 impl_type: rast.Type = None) -> rast.FnDef:
        """Parse a function definition.

        Args:
            impl_type: If parsing inside an impl block, the implementing type.
                       This allows bare 'self' parameter syntax.
        """
        if attrs is None:
            attrs = []
        self._check_attrs_apply(attrs, "fn")
        span = self._current().span
        self._expect(TokenType.FN)
        name_tok = self._expect(TokenType.IDENT)

        # Parse optional generic type parameters: fn foo<T, U>(...) or fn foo<T: Drop>(...)
        type_params, type_param_bounds = self._parse_type_params()

        self._expect(TokenType.LPAREN)
        self._skip_whitespace_tokens()  # Allow newline after (

        params = []
        if not self._at(TokenType.RPAREN):
            # First param may be 'self' which can use bare syntax in impl blocks
            params.append(self.parse_param(impl_type=impl_type))
            self._skip_whitespace_tokens()  # Allow newline after param
            while self._at(TokenType.COMMA):
                self._advance()
                self._skip_whitespace_tokens()  # Allow newline after comma
                if self._at(TokenType.RPAREN):
                    break
                # Subsequent params don't get impl_type (bare self only valid as first param)
                params.append(self.parse_param())
                self._skip_whitespace_tokens()  # Allow newline after param
        self._expect(TokenType.RPAREN)

        ret_type = None
        if self._at(TokenType.ARROW):
            self._advance()
            ret_type = self.parse_type()

        if self._at(TokenType.EQ) and self._peek_at(1, TokenType.EXTERN):
            # Declaration only (LANGUAGE_SPEC §5.3, AGAST #1900).
            self._advance()
            self._advance()
            if not self._at(TokenType.NEWLINE, TokenType.EOF, TokenType.DEDENT):
                raise ParseError(f"Expected end of line after '= extern', got "
                                 f"{self._current().type.name}", self._current().span)
            # Bodies the using module needs itself can't live elsewhere.
            name = name_tok.value
            if type_params:
                raise ParseError(f"generic fn '{name}' {DECL_REFUSED}: importers "
                                 f"instantiate its body", span)
            if is_async:
                raise ParseError(f"async fn '{name}' {DECL_REFUSED}: importers "
                                 f"transform its body", span)
            if any(a.name == "test" for a in attrs):
                raise ParseError(f"[[test]] fn '{name}' {DECL_REFUSED}: a test "
                                 f"needs its body", span)
            return rast.FnDef(span, name_tok.value, params, ret_type,
                              rast.Block(span, [], None), attrs,
                              is_async=is_async, is_pub=is_pub, is_decl=True)

        body = self.parse_block()
        if any(a.name == "naked" for a in attrs):
            # No prologue means no frame: the body is asm that returns by
            # itself. Anything else used to be dropped by the emitter in
            # silence (#1847).
            self._check_naked_asm(body)
        return rast.FnDef(span, name_tok.value, params, ret_type, body, attrs,
                          is_async=is_async, is_pub=is_pub,
                          type_params=type_params, type_param_bounds=type_param_bounds)

    def parse_extern_fn(self, is_pub: bool = False) -> rast.ExternFn:
        """Parse an extern function declaration."""
        span = self._current().span
        self._expect(TokenType.EXTERN)
        self._expect(TokenType.FN)
        name_tok = self._expect(TokenType.IDENT)
        self._expect(TokenType.LPAREN)
        self._skip_whitespace_tokens()  # Allow newline after (

        params = []
        varargs = False
        if not self._at(TokenType.RPAREN):
            # Check for varargs
            if self._at(TokenType.DOTDOT):
                varargs = True
                self._advance()
            else:
                params.append(self.parse_param())
                self._skip_whitespace_tokens()  # Allow newline after param
                while self._at(TokenType.COMMA):
                    self._advance()
                    self._skip_whitespace_tokens()  # Allow newline after comma
                    if self._at(TokenType.RPAREN):
                        break
                    if self._at(TokenType.DOTDOT):
                        varargs = True
                        self._advance()
                        break
                    params.append(self.parse_param())
                    self._skip_whitespace_tokens()  # Allow newline after param
        self._expect(TokenType.RPAREN)

        ret_type = None
        if self._at(TokenType.ARROW):
            self._advance()
            ret_type = self.parse_type()

        return rast.ExternFn(span, name_tok.value, params, ret_type, varargs, is_pub=is_pub)

    def parse_struct(self, attrs: List[rast.Attr] = None, is_pub: bool = False) -> rast.StructDef:
        """Parse a struct definition.

        Supports:
            struct Point           # Empty struct (unit struct)
                x: i32
                y: i32

            pub struct Empty       # Empty struct with no fields
        """
        if attrs is None:
            attrs = []
        self._check_attrs_apply(attrs, "struct")
        span = self._current().span
        self._expect(TokenType.STRUCT)
        name_tok = self._expect(TokenType.IDENT)

        # Parse optional generic type parameters: struct Pair<T> or struct Pair<T: Drop>
        type_params, type_param_bounds = self._parse_type_params()

        self._skip_newlines()

        # Check for empty struct (no indent = no fields)
        fields = []
        if self._at(TokenType.INDENT):
            self._advance()

            while not self._at(TokenType.DEDENT, TokenType.EOF):
                field_name = self._expect(TokenType.IDENT)
                # Support :& and := for struct fields
                # :& wraps the type in a RefType (mutable reference)
                # := is for move semantics (currently just parse normally)
                wrap_ref = False
                if self._at(TokenType.COLON_AMP):
                    self._advance()
                    wrap_ref = True
                elif self._at(TokenType.COLON_EQ):
                    self._advance()
                    # Move semantics - just parse the type normally for now
                elif self._at(TokenType.COLON):
                    self._advance()
                else:
                    raise ParseError(f"Expected ':' after field name '{field_name.value}'", field_name.span)
                field_type = self.parse_type()
                if wrap_ref:
                    field_type = rast.RefType(field_type.span, field_type, mutable=True)
                fields.append((field_name.value, field_type))
                self._skip_newlines()  # Skip newlines after struct field

            if self._at(TokenType.DEDENT):
                self._advance()

        return rast.StructDef(span, name_tok.value, fields,
                              type_params=type_params, type_param_bounds=type_param_bounds,
                              is_pub=is_pub, attrs=attrs)

    def parse_enum(self, is_pub: bool = False) -> rast.EnumDef:
        """Parse an enum definition.

        Supports generic enums: enum Option<T> or enum Option<T: Drop>
        """
        span = self._current().span
        self._expect(TokenType.ENUM)
        name_tok = self._expect(TokenType.IDENT)

        # Parse optional type parameters: <T> or <T, U> or <T: Drop>
        type_params, type_param_bounds = self._parse_type_params()

        # `enum E: u64` -- a representation type (LANGUAGE_SPEC §10.4).
        repr_type = None
        if self._at(TokenType.COLON) and not type_params:
            self._advance()
            repr_type = self.parse_type()

        self._skip_newlines()
        self._expect(TokenType.INDENT)

        variants = []
        while not self._at(TokenType.DEDENT, TokenType.EOF):
            var_span = self._current().span
            var_name = self._expect(TokenType.IDENT)
            var_fields = []
            var_field_names = []
            discriminant = None
            if self._at(TokenType.EQ):
                # `Read = 0`, `Fault = -14`: an explicit discriminant.
                self._advance()
                negative = self._at(TokenType.MINUS)
                if negative:
                    self._advance()
                discriminant = self._expect(TokenType.INT).value
                if negative:
                    discriminant = -discriminant
                self._skip_newlines()
            elif self._at(TokenType.LPAREN):
                # Tuple variant: Reload(i32), SetViewport(u32, u32)
                self._advance()
                if not self._at(TokenType.RPAREN):
                    var_fields.append(self.parse_type())
                    while self._at(TokenType.COMMA):
                        self._advance()
                        if self._at(TokenType.RPAREN):
                            break
                        var_fields.append(self.parse_type())
                self._expect(TokenType.RPAREN)
                self._skip_newlines()
            else:
                # Either a bare variant (Stop) or a struct variant, which is a
                # bare name followed by an indented block of `name: Type`
                # fields -- lexically the same shape as a struct body:
                #
                #     SetViewport
                #         width: u32
                #         height: u32
                #
                # The field names are recorded alongside the positional types;
                # the payload layout is identical to the equivalent tuple
                # variant. See docs/ENUM_VARIANTS.md.
                self._skip_newlines()
                if self._at(TokenType.INDENT):
                    self._advance()
                    while not self._at(TokenType.DEDENT, TokenType.EOF):
                        field_name = self._expect(TokenType.IDENT)
                        # `name:& T` is a borrow field, wrapped in a RefType
                        # exactly as in a struct body (#2040). ritz1 has no
                        # `:=` field form, so unlike struct bodies it is not
                        # accepted here.
                        wrap_ref = self._at(TokenType.COLON_AMP)
                        if not (wrap_ref or self._at(TokenType.COLON)):
                            raise ParseError(
                                f"Expected ':' after field name "
                                f"'{field_name.value}' in enum variant "
                                f"'{var_name.value}'",
                                field_name.span)
                        self._advance()
                        field_type = self.parse_type()
                        if wrap_ref:
                            field_type = rast.RefType(
                                field_type.span, field_type, mutable=True)
                        var_fields.append(field_type)
                        var_field_names.append(field_name.value)
                        self._skip_newlines()
                    if self._at(TokenType.DEDENT):
                        self._advance()

                    if not var_fields:
                        raise ParseError(
                            f"Enum variant '{var_name.value}' has an empty "
                            f"field block; omit the block for a bare variant",
                            var_span)

                    dupes = [n for n in set(var_field_names)
                             if var_field_names.count(n) > 1]
                    if dupes:
                        raise ParseError(
                            f"Duplicate field '{sorted(dupes)[0]}' in enum "
                            f"variant '{var_name.value}'",
                            var_span)

            variants.append(rast.Variant(var_span, var_name.value, var_fields,
                                         field_names=var_field_names,
                                         discriminant=discriminant))
            self._skip_newlines()  # Skip newlines after enum variant

        if self._at(TokenType.DEDENT):
            self._advance()

        enum_def = rast.EnumDef(span, name_tok.value, variants,
                                type_params=type_params, type_param_bounds=type_param_bounds,
                                is_pub=is_pub, repr=repr_type)
        _check_discriminants(enum_def)
        return enum_def

    def _expect_ident_or_keyword(self, msg: str = None) -> Token:
        """Consume an identifier or keyword token (for paths where keywords are valid)."""
        tok = self._current()
        # Accept IDENT or any keyword token
        if tok.type == TokenType.IDENT:
            return self._advance()
        # Keywords have their name as value
        if tok.type in KEYWORDS.values():
            return self._advance()
        if msg is None:
            msg = f"Expected identifier, got {tok.type.name}"
        raise ParseError(msg, tok.span)

    def parse_import(self, is_pub: bool = False) -> rast.Import:
        """Parse an import statement.

        Syntax variants:
            import ritzlib.sys              - all pub items to namespace
            import ritzlib.sys as sys       - qualified access via sys::item
            import ritzlib.sys { a, b }     - selective imports
            import ritzlib.sys { a } as x   - selective with alias
            pub import ritzlib.sys          - re-exports imported items
        """
        span = self._current().span
        self._expect(TokenType.IMPORT)

        # Allow keywords in import paths (e.g., ritzlib.heap)
        first_tok = self._expect_ident_or_keyword("Expected module name")
        path = [first_tok.value]
        while self._at(TokenType.DOT):
            self._advance()
            tok = self._expect_ident_or_keyword("Expected module name after '.'")
            path.append(tok.value)

        # Parse optional selective imports: { item1, item2 }
        # Supports multiline:
        #   import foo {
        #       item1,
        #       item2,
        #   }
        items = None
        if self._at(TokenType.LBRACE):
            self._advance()
            self._skip_whitespace_tokens()  # Allow newline after {
            items = []
            if not self._at(TokenType.RBRACE):
                tok = self._expect_ident_or_keyword("Expected item name")
                items.append(tok.value)
                self._skip_whitespace_tokens()  # Allow newline after item
                while self._at(TokenType.COMMA):
                    self._advance()
                    self._skip_whitespace_tokens()  # Allow newline after comma
                    if self._at(TokenType.RBRACE):
                        break  # trailing comma
                    tok = self._expect_ident_or_keyword("Expected item name")
                    items.append(tok.value)
                    self._skip_whitespace_tokens()  # Allow newline after item
            self._expect(TokenType.RBRACE, "Expected '}' after import items")
            # After multiline imports, skip any DEDENT that was generated
            # due to continuation indentation
            self._skip_whitespace_tokens()

        # Parse optional alias: as name
        alias = None
        if self._at(TokenType.AS):
            self._advance()
            alias_tok = self._expect(TokenType.IDENT, "Expected alias name after 'as'")
            alias = alias_tok.value

        return rast.Import(span, path, alias=alias, items=items, is_pub=is_pub)

    def parse_const(self, attrs: list = None, is_pub: bool = False) -> rast.ConstDef:
        """Parse a constant definition: const STDIN: i32 = 0."""
        self._check_attrs_apply(attrs or [], "const")
        span = self._current().span
        self._expect(TokenType.CONST)
        name = self._expect(TokenType.IDENT).value
        self._expect(TokenType.COLON)
        const_type = self.parse_type()
        self._expect(TokenType.EQ)
        value = self.parse_expr()
        return rast.ConstDef(span, name, const_type, value, is_pub=is_pub, attrs=attrs or [])

    def parse_var_def(self, is_pub: bool = False) -> rast.VarDef:
        """Parse a module-level variable: var counter: i32 = 0."""
        span = self._current().span
        self._expect(TokenType.VAR)
        name = self._expect(TokenType.IDENT).value

        var_type = None
        if self._at(TokenType.COLON):
            self._advance()
            var_type = self.parse_type()

        value = None
        eq_span = None
        if self._at(TokenType.EQ):
            eq_span = self._current().span
            self._advance()
            value = self.parse_expr()

        if var_type is None and value is None:
            raise ParseError("Module-level variable must have a type annotation or initializer", span)

        return rast.VarDef(span, name, var_type, value, is_pub=is_pub, eq_span=eq_span)

    def parse_extern_var(self, is_pub: bool = False) -> rast.VarDef:
        """`extern var NAME: T` (LANGUAGE_SPEC §5.3, AGAST #1879).

        A data symbol defined in another object, typically by the linker
        (`__bss_start`). It has a type and no initializer.
        """
        span = self._current().span
        self._expect(TokenType.EXTERN)
        self._expect(TokenType.VAR)
        name = self._expect(TokenType.IDENT).value
        self._expect(TokenType.COLON, "extern var needs a type: extern var NAME: T")
        var_type = self.parse_type()
        if self._at(TokenType.EQ):
            raise ParseError(f"extern var cannot have an initializer: '{name}' is "
                             "defined in another object", span)
        return rast.VarDef(span, name, var_type, None, is_pub=is_pub, is_extern=True)

    def parse_static_assert(self) -> rast.StaticAssert:
        """Parse static_assert(condition) or static_assert(condition, "message")."""
        span = self._current().span
        self._expect(TokenType.STATIC_ASSERT)
        self._expect(TokenType.LPAREN)
        condition = self.parse_expr()
        message = None
        if self._at(TokenType.COMMA):
            self._advance()
            msg_tok = self._expect(TokenType.STRING, "Expected string message")
            message = msg_tok.value
        self._expect(TokenType.RPAREN)
        return rast.StaticAssert(span, condition, message)

    def parse_type_alias(self, is_pub: bool = False) -> rast.TypeAlias:
        """Parse a type alias: type IntOrStr = i32 | *u8."""
        span = self._current().span
        self._expect(TokenType.TYPE)
        name = self._expect(TokenType.IDENT).value
        self._expect(TokenType.EQ)
        target = self.parse_type()
        return rast.TypeAlias(span, name, target, is_pub=is_pub)

    def parse_trait_method_sig(self) -> rast.TraitMethodSig:
        """Parse a method signature in a trait definition (no body).

        Example: fn print(self: *Self) -> i32

        Supports bare self syntax:
            fn method(self)       -> const borrow of Self
            fn method(self:&)     -> mutable borrow of Self
        """
        span = self._current().span
        self._expect(TokenType.FN)
        name_tok = self._expect(TokenType.IDENT)
        self._expect(TokenType.LPAREN)

        # Create a synthetic Self type for bare self handling
        self_type = rast.NamedType(span, "Self", [])

        params = []
        if not self._at(TokenType.RPAREN):
            params.append(self.parse_param(impl_type=self_type))
            while self._at(TokenType.COMMA):
                self._advance()
                if self._at(TokenType.RPAREN):
                    break
                params.append(self.parse_param(impl_type=self_type))
        self._expect(TokenType.RPAREN)

        ret_type = None
        if self._at(TokenType.ARROW):
            self._advance()
            ret_type = self.parse_type()

        if self._at(TokenType.EQ) and self._peek_at(1, TokenType.EXTERN):
            raise ParseError(
                f"trait method '{name_tok.value}' {DECL_REFUSED}: a trait method "
                f"is a signature already; drop '= extern'", span)

        return rast.TraitMethodSig(span, name_tok.value, params, ret_type)

    def parse_trait(self, is_pub: bool = False) -> rast.TraitDef:
        """Parse a trait definition.

        Example:
            trait Printable
                fn print(self: *Self) -> i32
        """
        span = self._current().span
        self._expect(TokenType.TRAIT)
        name_tok = self._expect(TokenType.IDENT)
        self._skip_newlines()
        self._expect(TokenType.INDENT)

        methods = []
        while not self._at(TokenType.DEDENT, TokenType.EOF):
            method = self.parse_trait_method_sig()
            methods.append(method)
            self._skip_newlines()

        if self._at(TokenType.DEDENT):
            self._advance()

        return rast.TraitDef(span, name_tok.value, methods, is_pub=is_pub)

    def parse_impl(self) -> rast.ImplBlock:
        """Parse an impl block.

        Note: impl blocks don't have visibility. Methods inside them can have pub.

        Examples:
            impl Printable for Point
                fn print(self: *Point) -> i32
                    ...

            impl Point
                fn new(x: i32, y: i32) -> Point
                    ...

            impl<T> Drop for Box<T>
                fn drop(self: *Box<T>)
                    ...

            impl<T: Drop> Container<T>
                fn cleanup(self: *Container<T>)
                    ...
        """
        span = self._current().span
        self._expect(TokenType.IMPL)

        # Check for impl<T, U, ...> or impl<T: Bound, U: Bound, ...> type parameters
        type_params, type_param_bounds = self._parse_type_params()

        first_tok = self._expect(TokenType.IDENT)
        first_name = first_tok.value

        trait_name = None
        type_name = first_name
        impl_type = None

        # Check for type args on the first identifier (e.g., Box<T> for inherent impl)
        if self._at(TokenType.LT):
            type_args = self._parse_type_args()
            impl_type = rast.NamedType(span, first_name, type_args)

        # Check for "impl Trait for Type" pattern
        if self._at(TokenType.FOR):
            self._advance()
            trait_name = first_name
            type_tok = self._expect(TokenType.IDENT)
            type_name = type_tok.value
            impl_type = None  # Reset - impl_type will be parsed next
            if trait_name in index_rules.TRAITS and type_name in index_rules.BUILT_IN:
                # `[]` on a Vec, Span or String keeps one meaning (§7.8).
                raise ParseError(index_rules.builtin_impl(trait_name, type_name),
                                 type_tok.span)

            # Check for type args on the implementing type (e.g., for Box<T>)
            if self._at(TokenType.LT):
                type_args = self._parse_type_args()
                impl_type = rast.NamedType(span, type_name, type_args)

        self._skip_newlines()
        self._expect(TokenType.INDENT)

        # Create self_type for bare 'self' parameter support
        # If impl_type is set (generic impl), use it; otherwise create simple NamedType
        self_type = impl_type if impl_type else rast.NamedType(span, type_name)

        methods = []
        while not self._at(TokenType.DEDENT, TokenType.EOF):
            # Parse any attributes on the method
            attrs = self.parse_attrs()
            # Check for pub fn in impl block
            method_is_pub = False
            if self._at(TokenType.PUB):
                method_is_pub = True
                self._advance()
            # Check for async fn in impl block
            is_async = False
            if self._at(TokenType.ASYNC):
                self._advance()
                is_async = True
            method = self.parse_fn(attrs, is_async=is_async, is_pub=method_is_pub, impl_type=self_type)
            # AGAST #2258: `Self` in an impl method's signature is the impl's
            # type. Nothing downstream resolved the name, so `self:= Self`
            # lowered as i8 and crashed the emitter, and MoveTypes didn't see
            # a `self: Self` as move-only. Spelled out here, every pass sees
            # `P` (or `Box<T>`), exactly as if the method had written it.
            spell_self = TypeSubstitution({'Self': self_type})
            for param in method.params:
                param.type = spell_self.apply(param.type)
            if method.ret_type is not None:
                method.ret_type = spell_self.apply(method.ret_type)
            # AGAST #1902: a method's own `<...>` is never instantiated (the
            # emitter erased T, e.g. to i8, and `b.m<i32>(x)` crashed), and
            # LANGUAGE_SPEC does not specify them. ritz1 rejects them too
            # (ast_helpers.ritz impl_block_new). The impl's params are fine.
            if method.type_params:
                raise ParseError(
                    f"method '{method.name}' of '{type_name}' has its own type "
                    f"parameters <{', '.join(method.type_params)}>; generic methods "
                    f"are not supported -- use a free generic fn",
                    method.span)
            if method.is_decl and type_params:
                raise ParseError(
                    f"method '{method.name}' of generic impl '{type_name}' "
                    f"{DECL_REFUSED}: importers instantiate its body",
                    method.span)
            methods.append(method)
            self._skip_newlines()

        if self._at(TokenType.DEDENT):
            self._advance()

        block = rast.ImplBlock(span, trait_name, type_name, methods, type_params, impl_type,
                               type_param_bounds=type_param_bounds)
        if trait_name is not None:
            block.trait_span = first_tok.span   # §7.7's impl errors are located there
        # Where the target's name is: "unknown type" is located there (#3264).
        block.type_span = type_tok.span if trait_name is not None else first_tok.span
        return block

    def parse_item(self) -> rast.Item:
        """Parse a top-level item."""
        # Parse any leading @attributes
        attrs = self.parse_attrs()

        # Check for 'pub' keyword (visibility marker)
        is_pub = False
        if self._at(TokenType.PUB):
            is_pub = True
            self._advance()

        # async fn
        if self._at(TokenType.ASYNC):
            self._advance()
            if not self._at(TokenType.FN):
                raise ParseError("Expected 'fn' after 'async'", self._current().span)
            return self.parse_fn(attrs, is_async=True, is_pub=is_pub)

        if self._at(TokenType.FN):
            return self.parse_fn(attrs, is_pub=is_pub)
        if self._at(TokenType.EXTERN) and self._peek_at(1, TokenType.VAR):
            if attrs:
                raise ParseError("Attributes not allowed on extern var", attrs[0].span)
            return self.parse_extern_var(is_pub=is_pub)
        if self._at(TokenType.EXTERN):
            self._check_attrs_apply(attrs, "extern fn")
            ext = self.parse_extern_fn(is_pub=is_pub)
            ext.callconv = _callconv_of(attrs)
            return ext
        if self._at(TokenType.STRUCT):
            return self.parse_struct(attrs, is_pub=is_pub)
        if self._at(TokenType.ENUM):
            if attrs:
                raise ParseError("Attributes not allowed on enums (yet)", self._current().span)
            return self.parse_enum(is_pub=is_pub)
        if self._at(TokenType.IMPORT):
            if attrs:
                raise ParseError("Attributes not allowed on imports", self._current().span)
            return self.parse_import(is_pub=is_pub)
        if self._at(TokenType.CONST):
            return self.parse_const(attrs=attrs, is_pub=is_pub)
        if self._at(TokenType.VAR):
            if attrs:
                raise ParseError("Attributes not allowed on module-level variables (yet)", self._current().span)
            return self.parse_var_def(is_pub=is_pub)
        if self._at(TokenType.TYPE):
            self._check_attrs_apply(attrs, "type")
            alias = self.parse_type_alias(is_pub=is_pub)
            callconv = _callconv_of(attrs)
            if attrs:
                # callconv is the only attribute a `type` takes: it is part of
                # the fn type, so a call through the alias uses it.
                if not isinstance(alias.target, rast.FnType):
                    raise ParseError(
                        f"attribute 'callconv' applies to fn-type aliases only; "
                        f"'{alias.name}' is not a fn type", attrs[0].span)
                alias.target.callconv = callconv
            return alias
        if self._at(TokenType.TRAIT):
            if attrs:
                raise ParseError("Attributes not allowed on traits (yet)", self._current().span)
            return self.parse_trait(is_pub=is_pub)
        if self._at(TokenType.IMPL):
            if attrs:
                raise ParseError("Attributes not allowed on impl blocks (yet)", self._current().span)
            if is_pub:
                raise ParseError("'pub' not allowed on impl blocks (use 'pub' on individual methods)", self._current().span)
            return self.parse_impl()
        if self._at(TokenType.STATIC_ASSERT):
            if attrs:
                raise ParseError("Attributes not allowed on static_assert", self._current().span)
            if is_pub:
                raise ParseError("'pub' not allowed on static_assert", self._current().span)
            return self.parse_static_assert()

        raise ParseError(f"Expected item, got {self._current().type.name}", self._current().span)

    def parse_module(self) -> rast.Module:
        """Parse a complete module (source file)."""
        span = self._current().span
        items = []

        self._skip_newlines()  # Skip leading newlines
        try:
            while not self._at(TokenType.EOF):
                items.append(self.parse_item())
                self._skip_newlines()  # Skip newlines between items
        except ParseError as e:
            # A bad unindent before the error is its cause.
            self._check_unmatched_indent(e.span.line)
            raise
        self._check_unmatched_indent(None)

        items.extend(_enum_from_fns(items, span.file))
        return rast.Module(span, items)


# ============================================================================
# Enum discriminants (LANGUAGE_SPEC §10.4, AGAST #1880)
# ============================================================================
#
# ritz1 enforces the same rules with the same messages (ast_helpers.ritz,
# enum_check_*), and generates the same `from` source (enum_from_source).

# Representation types and their value ranges.
INT_RANGES = {
    "i8": (-(1 << 7), (1 << 7) - 1), "i16": (-(1 << 15), (1 << 15) - 1),
    "i32": (-(1 << 31), (1 << 31) - 1), "i64": (-(1 << 63), (1 << 63) - 1),
    "u8": (0, (1 << 8) - 1), "u16": (0, (1 << 16) - 1),
    "u32": (0, (1 << 32) - 1), "u64": (0, (1 << 64) - 1),
}


def _repr_name(enum_def: rast.EnumDef) -> Optional[str]:
    """The representation type's name (`u64`), or None without one."""
    ty = enum_def.repr
    if ty is None:
        return None
    if isinstance(ty, rast.NamedType) and not ty.args:
        return ty.name
    return "?"


def _check_discriminants(enum_def: rast.EnumDef) -> None:
    """Reject what §10.4 forbids, located at the offending variant."""
    name = enum_def.name
    repr_name = _repr_name(enum_def)
    if repr_name is not None and repr_name not in INT_RANGES:
        raise ParseError(
            f"representation type of enum '{name}' must be an integer type",
            enum_def.span)
    for v in enum_def.variants:
        if repr_name is not None and v.fields:
            raise ParseError(
                f"variant '{v.name}' of enum '{name}' carries data, so the "
                f"enum cannot have a representation type", v.span)
        if repr_name is None and v.discriminant is not None:
            raise ParseError(
                f"discriminant of variant '{v.name}' needs a representation "
                f"type: write 'enum {name}: <integer type>'", v.span)
    if repr_name is None:
        return
    lo, hi = INT_RANGES[repr_name]
    seen = {}
    for v, d in zip(enum_def.variants, enum_def.discriminants()):
        if not lo <= d <= hi:
            raise ParseError(
                f"discriminant {d} of variant '{v.name}' does not fit enum "
                f"'{name}''s representation type {repr_name}", v.span)
        if d in seen:
            raise ParseError(
                f"variants '{seen[d]}' and '{v.name}' of enum '{name}' have "
                f"the same discriminant {d}", v.span)
        seen[d] = v.name


def enum_from_name(enum_name: str) -> str:
    """The fn `E.from(v)` calls (§10.4): generated, so not user-spellable
    in practice, and the same symbol in both compilers."""
    return f"{enum_name}__from"


def enum_from_source(enum_def: rast.EnumDef) -> str:
    """Ritz source of `E.from`: `Some(E.V)` for V's discriminant, else None."""
    name = enum_def.name
    pub = "pub " if enum_def.is_pub else ""
    lines = [f"{pub}fn {enum_from_name(name)}(v: {_repr_name(enum_def)}) -> Option<{name}>"]
    for v, d in zip(enum_def.variants, enum_def.discriminants()):
        lines.append(f"    if v == {d}")
        lines.append(f"        return Some({name}.{v.name})")
    lines.append("    return None")
    return "\n".join(lines) + "\n"


def _enum_from_fns(items: list, filename: str) -> List[rast.FnDef]:
    """`E.from` for each enum with a representation type, if this module
    imports ritzlib.option (its result type).  Parsed from generated source,
    which starts on the enum's line so any position in it points there.

    The fns are marked `generated`: they are not in the module's text, so
    its interface text omits them, and parsing that text regenerates them
    from the enum (ritz1 does the same).
    """
    if not any(isinstance(it, rast.Import) and it.path == ["ritzlib", "option"]
               and it.alias is None for it in items):
        return []
    out = []
    for it in items:
        if isinstance(it, rast.EnumDef) and it.repr is not None:
            src = "\n" * (it.span.line - 1) + enum_from_source(it)
            fn = Parser(Lexer(src, filename).tokenize()).parse_module().items[0]
            fn.generated = True
            out.append(fn)
    return out


def _callconv_of(attrs: List[rast.Attr]) -> Optional[str]:
    """The `[[callconv]]` value, or None for the C convention (also "c")."""
    for a in attrs:
        if a.name == "callconv" and a.value != "c":
            return a.value
    return None


def parse(source: str, filename: str = "<stdin>") -> rast.Module:
    """Convenience function to parse source code."""
    lexer = Lexer(source, filename)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    return parser.parse_module()
