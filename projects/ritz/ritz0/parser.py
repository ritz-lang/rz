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

from typing import List, Optional, Callable
from tokens import Token, TokenType, Span, KEYWORDS
from lexer import Lexer, LexerError
import ritz_ast as rast


class ParseError(Exception):
    """Parser error with source location."""
    def __init__(self, message: str, span: Span):
        self.message = message
        self.span = span
        super().__init__(f"{span}: {message}")


class Parser:
    """
    Parser for Ritz source code.

    Uses recursive descent for statements/items and Pratt parsing for expressions.
    """

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

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
            if msg is None:
                msg = f"Expected {type.name}, got {tok.type.name}"
            raise ParseError(msg, tok.span)
        return self._advance()

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
            if not self._peek_at(1, TokenType.IDENT, TokenType.STAR, TokenType.AMP,
                                  TokenType.LBRACKET, TokenType.FN, TokenType.GT,
                                  TokenType.AT, TokenType.AT_AMP, TokenType.LPAREN):
                return type_args  # Not type args, leave < for expression parser

            self._advance()  # consume <
            if not self._at(TokenType.GT):
                type_args.append(self.parse_type())
                while self._at(TokenType.COMMA):
                    self._advance()
                    if self._at(TokenType.GT):
                        break  # trailing comma
                    type_args.append(self.parse_type())
            self._expect(TokenType.GT, "Expected '>' after type arguments")
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

        # Save position for backtracking
        saved_pos = self.pos

        try:
            self._advance()  # consume <

            type_args = []
            if not self._at(TokenType.GT):
                type_args.append(self.parse_type())
                while self._at(TokenType.COMMA):
                    self._advance()
                    if self._at(TokenType.GT):
                        break
                    type_args.append(self.parse_type())

            if not self._at(TokenType.GT):
                # Not a valid type arg list
                self.pos = saved_pos
                return []

            self._advance()  # consume >

            # Check if followed by ( or { - this confirms it's type args
            if self._at(TokenType.LPAREN, TokenType.LBRACE):
                return type_args

            # Not followed by ( or {, could be comparison
            # Backtrack and let expression parser handle it
            self.pos = saved_pos
            return []

        except ParseError:
            # Failed to parse as type args, backtrack
            self.pos = saved_pos
            return []

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
        """Parse a type expression, including union types (A | B | C).

        Args:
            allow_type_args: If False, don't parse generic type arguments.
                This is used in cast expressions (as) to avoid ambiguity
                with comparison operators.
        """
        first_type = self._parse_type_primary(allow_type_args)

        # Check for union: T | U | V
        if self._at(TokenType.PIPE):
            span = first_type.span
            variants = [first_type]
            while self._at(TokenType.PIPE):
                self._advance()
                variants.append(self._parse_type_primary(allow_type_args))
            return rast.UnionType(span, variants)

        return first_type

    def _parse_type_primary(self, allow_type_args: bool = True) -> rast.Type:
        """Parse a primary type (non-union)."""
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
                        # Slice type [T] where T was an identifier
                        return rast.SliceType(span, rast.NamedType(ident.span, ident.value))
                else:
                    # More complex expression after IDENT (e.g., SIZE * 2)
                    self.pos = saved_pos
                    size_expr = self._parse_array_size_expr()
                    self._expect(TokenType.RBRACKET)
                    inner = self._parse_type_primary(allow_type_args)
                    return rast.ArrayType(span, size_expr, inner)
            else:
                # Slice type: [T]
                inner = self.parse_type()
                self._expect(TokenType.RBRACKET)
                return rast.SliceType(span, inner)

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
                ret = self.parse_type()
            return rast.FnType(span, params, ret)

        # Trait object type: dyn Trait or dyn Trait<Args>
        if self._at(TokenType.DYN):
            self._advance()
            trait_name_tok = self._expect(TokenType.IDENT, "Expected trait name after 'dyn'")
            trait_name = trait_name_tok.value
            # Generic args: dyn Iterator<Item=i32>
            args = self._parse_type_args() if allow_type_args else []
            return rast.DynType(span, trait_name, args)

        # Named type (possibly with generics)
        name_tok = self._expect(TokenType.IDENT, "Expected type name")
        name = name_tok.value

        # Handle qualified names:
        #   ritzlib.fmt.print  - module path (dots)
        #   sys::SomeType      - namespace access (::)
        while self._at(TokenType.DOT):
            self._advance()
            next_tok = self._expect(TokenType.IDENT)
            name = f"{name}.{next_tok.value}"

        # Handle namespace qualifier: alias::Type
        if self._at(TokenType.COLONCOLON):
            self._advance()
            qualified_name = self._expect(TokenType.IDENT, "Expected type name after '::'").value
            name = f"{name}::{qualified_name}"

        # Generic args: Type<Arg1, Arg2>
        # Skip type args parsing in cast context to avoid ambiguity with comparisons
        args = self._parse_type_args() if allow_type_args else []

        return rast.NamedType(span, name, args)

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
        TokenType.DOTDOT: 11,    # ..
        TokenType.DOTDOTEQ: 11,  # ..=
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

            if op_tok.type == TokenType.AS:
                # Cast expression: expr as Type
                # Don't allow type args to avoid ambiguity: `x as i64 < y`
                # should parse as (x as i64) < y, not x as i64<y>
                target_type = self.parse_type(allow_type_args=False)
                left = rast.Cast(left.span, left, target_type)
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
                args = []
                if not self._at(TokenType.RPAREN):
                    args.append(self.parse_expr())
                    while self._at(TokenType.COMMA):
                        self._advance()
                        if self._at(TokenType.RPAREN):
                            break  # trailing comma
                        args.append(self.parse_expr())
                self._expect(TokenType.RPAREN)
                expr = rast.Call(expr.span, expr, args, type_args=type_args)

            elif self._at(TokenType.LBRACKET):
                # Index or Slice: a[i] or a[start:end] or a[:end] or a[start:]
                self._advance()

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
                        expr = rast.Index(expr.span, expr, first)

            elif self._at(TokenType.DOT):
                # Field access, tuple field access, or method call
                self._advance()
                # Check for tuple field access: expr.0, expr.1, etc.
                if self._at(TokenType.INT):
                    field_tok = self._advance()
                    field_name = str(field_tok.value)
                    expr = rast.Field(expr.span, expr, field_name)
                else:
                    field_tok = self._expect(TokenType.IDENT)
                    if self._at(TokenType.LPAREN):
                        # Method call
                        self._advance()
                        args = []
                        if not self._at(TokenType.RPAREN):
                            args.append(self.parse_expr())
                            while self._at(TokenType.COMMA):
                                self._advance()
                                if self._at(TokenType.RPAREN):
                                    break
                                args.append(self.parse_expr())
                        self._expect(TokenType.RPAREN)
                        expr = rast.MethodCall(expr.span, expr, field_tok.value, args)
                    else:
                        expr = rast.Field(expr.span, expr, field_tok.value)

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

        # Integer literal
        if self._at(TokenType.INT):
            self._advance()
            return rast.IntLit(span, tok.value)

        # Float literal
        if self._at(TokenType.FLOAT):
            self._advance()
            return rast.FloatLit(span, tok.value)

        # String literal
        if self._at(TokenType.STRING):
            self._advance()
            return rast.StringLit(span, tok.value)

        # C-string literal: c"..."
        if self._at(TokenType.CSTRING):
            self._advance()
            return rast.CStringLit(span, tok.value)

        # Span string literal: s"..."
        if self._at(TokenType.SPAN_STRING):
            self._advance()
            return rast.SpanStringLit(span, tok.value)

        # Interpolated string literal
        if self._at(TokenType.INTERP_STRING):
            self._advance()
            parts, expr_strs = tok.value
            # Parse each expression string
            exprs = []
            for expr_str in expr_strs:
                expr = self._parse_interp_expr(expr_str, span)
                exprs.append(expr)
            return rast.InterpString(span, parts, exprs)

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

    def parse_match(self) -> rast.Match:
        """Parse a match expression."""
        span = self._current().span
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

        guard = None
        if self._at(TokenType.IF):
            self._advance()
            guard = self.parse_expr()

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

        # Type pattern for pointer types: *T, *mut T, **u8, etc.
        if self._at(TokenType.STAR):
            ty = self._parse_type_primary()
            return rast.TypePattern(span, ty)

        # Type pattern for reference types: &T, &mut T
        if self._at(TokenType.AMP):
            ty = self._parse_type_primary()
            return rast.TypePattern(span, ty)

        # Identifier or variant pattern
        if self._at(TokenType.IDENT):
            name = self._current().value

            # Check if this looks like a primitive type name for type pattern
            # Primitive types: i8, i16, i32, i64, u8, u16, u32, u64, bool
            if name in ('i8', 'i16', 'i32', 'i64', 'u8', 'u16', 'u32', 'u64', 'bool'):
                ty = self._parse_type_primary()
                return rast.TypePattern(span, ty)

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
            param_type = self.parse_type()
        return rast.ClosureParam(name_tok.value, param_type)

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
            # Optional message: assert x, "error message"
            if self._at(TokenType.COMMA):
                self._advance()
                if self._at(TokenType.STRING):
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
            return rast.ForStmt(span, var_tok.value, iter_expr, body)

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
            return rast.AssignStmt(span, expr, value)

        return rast.ExprStmt(span, expr)

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
            while not self._at(TokenType.RPAREN):
                name_tok = self._expect(TokenType.IDENT)
                names.append(name_tok.value)
                if self._at(TokenType.COMMA):
                    self._advance()
                else:
                    break
            self._expect(TokenType.RPAREN)
            self._expect(TokenType.EQ)
            value = self.parse_expr()
            return rast.LetTupleStmt(span, names, value)

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

        return rast.LetStmt(span, name_tok.value, type_ann, value)

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

        return rast.VarStmt(span, name_tok.value, type_ann, value)

    def parse_asm(self) -> rast.AsmStmt:
        """Parse an inline assembly statement.

        Syntax:
            asm <arch>:
                <assembly line 1>
                <assembly line 2>
                ...

        Example:
            asm x86_64:
                mov dx, {port}
                out dx, al

        Operands are referenced as {name} in the assembly template.
        """
        import re

        span = self._current().span
        self._expect(TokenType.ASM)

        # Expect architecture identifier (e.g., x86_64, aarch64)
        arch_tok = self._expect(TokenType.IDENT)
        arch = arch_tok.value

        # Expect colon after architecture
        self._expect(TokenType.COLON)

        # Now we need to parse the indented block of assembly lines
        # The assembly is raw text, not Ritz expressions
        self._expect(TokenType.NEWLINE)
        self._expect(TokenType.INDENT)

        # Collect assembly lines until DEDENT
        asm_lines = []
        while not self._at(TokenType.DEDENT, TokenType.EOF):
            # Read tokens until NEWLINE, reconstructing the line
            line_parts = []
            while not self._at(TokenType.NEWLINE, TokenType.DEDENT, TokenType.EOF):
                tok = self._advance()
                # Preserve the token's text representation
                if tok.type == TokenType.IDENT:
                    line_parts.append(tok.value)
                elif tok.type == TokenType.INT:
                    line_parts.append(str(tok.value))
                elif tok.type == TokenType.STRING:
                    line_parts.append(f'"{tok.value}"')
                elif tok.type == TokenType.LBRACE:
                    line_parts.append('{')
                elif tok.type == TokenType.RBRACE:
                    line_parts.append('}')
                elif tok.type == TokenType.COMMA:
                    line_parts.append(',')
                elif tok.type == TokenType.COLON:
                    line_parts.append(':')
                elif tok.type == TokenType.LBRACKET:
                    line_parts.append('[')
                elif tok.type == TokenType.RBRACKET:
                    line_parts.append(']')
                elif tok.type == TokenType.PLUS:
                    line_parts.append('+')
                elif tok.type == TokenType.MINUS:
                    line_parts.append('-')
                elif tok.type == TokenType.STAR:
                    line_parts.append('*')
                elif tok.type == TokenType.AT:
                    line_parts.append('@')
                elif tok.type == TokenType.PERCENT:
                    line_parts.append('%')
                elif tok.type == TokenType.DOLLAR:
                    line_parts.append('$')
                elif tok.type == TokenType.DOT:
                    line_parts.append('.')
                else:
                    # For other tokens, use the value or type name
                    if tok.value is not None:
                        line_parts.append(str(tok.value))

            if line_parts:
                # Join with spaces, but handle special cases
                line = ' '.join(line_parts)
                # Clean up spacing around punctuation
                line = re.sub(r'\s*,\s*', ', ', line)
                line = re.sub(r'\s*:\s*', ':', line)
                line = re.sub(r'\{\s*', '{', line)
                line = re.sub(r'\s*\}', '}', line)
                line = re.sub(r'\[\s*', '[', line)
                line = re.sub(r'\s*\]', ']', line)
                # Remove space after dot for assembly labels (e.g., .spin, .Llabel)
                line = re.sub(r'\.\s+', '.', line)
                # Remove space after $ for AT&T immediate values (e.g., $3, $0xFF)
                line = re.sub(r'\$\s+', '$', line)
                # Remove space after % for AT&T registers (e.g., %rax)
                line = re.sub(r'%\s+', '%', line)
                asm_lines.append(line)

            # Consume newline if present
            if self._at(TokenType.NEWLINE):
                self._advance()

        # Consume DEDENT
        if self._at(TokenType.DEDENT):
            self._advance()

        # Join lines into template
        template = '\n'.join(asm_lines)

        # Extract operands from {name} placeholders
        operand_names = re.findall(r'\{(\w+)\}', template)
        operands = []
        seen = set()
        for name in operand_names:
            if name not in seen:
                seen.add(name)
                # Create operand - we'll resolve the actual expressions later
                # For now, create a placeholder that references the variable
                operands.append(rast.AsmOperand(
                    name=name,
                    constraint="r",  # Default to register constraint
                    expr=rast.Ident(span, name),
                    is_output=False  # Will be determined by emitter
                ))

        return rast.AsmStmt(
            span=span,
            arch=arch,
            template=template,
            operands=operands,
            clobbers=[],  # TODO: parse clobber list syntax
            volatile=True
        )

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
        """Parse a single attribute: name, name("arg", ...), or name = "value"."""
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

        return rast.Attr(name_tok.value, args, value)

    def parse_fn(self, attrs: List[rast.Attr] = None, is_async: bool = False, is_pub: bool = False,
                 impl_type: rast.Type = None) -> rast.FnDef:
        """Parse a function definition.

        Args:
            impl_type: If parsing inside an impl block, the implementing type.
                       This allows bare 'self' parameter syntax.
        """
        if attrs is None:
            attrs = []
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

        body = self.parse_block()
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

        self._skip_newlines()
        self._expect(TokenType.INDENT)

        variants = []
        while not self._at(TokenType.DEDENT, TokenType.EOF):
            var_span = self._current().span
            var_name = self._expect(TokenType.IDENT)
            var_fields = []
            if self._at(TokenType.LPAREN):
                self._advance()
                if not self._at(TokenType.RPAREN):
                    var_fields.append(self.parse_type())
                    while self._at(TokenType.COMMA):
                        self._advance()
                        if self._at(TokenType.RPAREN):
                            break
                        var_fields.append(self.parse_type())
                self._expect(TokenType.RPAREN)
            variants.append(rast.Variant(var_span, var_name.value, var_fields))
            self._skip_newlines()  # Skip newlines after enum variant

        if self._at(TokenType.DEDENT):
            self._advance()

        return rast.EnumDef(span, name_tok.value, variants,
                            type_params=type_params, type_param_bounds=type_param_bounds, is_pub=is_pub)

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
        if self._at(TokenType.EQ):
            self._advance()
            value = self.parse_expr()

        # Module-level vars must have a type or initializer for type inference
        if var_type is None and value is None:
            raise ParseError("Module-level variable must have a type annotation or initializer", span)

        return rast.VarDef(span, name, var_type, value, is_pub=is_pub)

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

        first_name = self._expect(TokenType.IDENT).value

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
            type_name = self._expect(TokenType.IDENT).value
            impl_type = None  # Reset - impl_type will be parsed next

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
            methods.append(method)
            self._skip_newlines()

        if self._at(TokenType.DEDENT):
            self._advance()

        return rast.ImplBlock(span, trait_name, type_name, methods, type_params, impl_type,
                              type_param_bounds=type_param_bounds)

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
        if self._at(TokenType.EXTERN):
            if attrs:
                raise ParseError("Attributes not allowed on extern functions", self._current().span)
            return self.parse_extern_fn(is_pub=is_pub)
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
            if attrs:
                raise ParseError("Attributes not allowed on type aliases (yet)", self._current().span)
            return self.parse_type_alias(is_pub=is_pub)
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
        while not self._at(TokenType.EOF):
            items.append(self.parse_item())
            self._skip_newlines()  # Skip newlines between items

        return rast.Module(span, items)


def parse(source: str, filename: str = "<stdin>") -> rast.Module:
    """Convenience function to parse source code."""
    lexer = Lexer(source, filename)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    return parser.parse_module()
