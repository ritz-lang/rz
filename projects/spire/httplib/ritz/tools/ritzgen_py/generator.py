#!/usr/bin/env python3
"""
generator.py - Generate Python parser from Ritz grammar

Reads a .grammar file and generates:
1. Token constants
2. Lexer class
3. Recursive descent parser class

The generated code integrates with existing emitter_llvmlite.py for code generation.
"""

import sys
import re
from typing import List, Dict, Set, Optional
try:
    from .grammar_parser import (
        Grammar, GrammarRule, GrammarAlt, GrammarSymbol,
        SymbolKind, TokenDef, parse_grammar_file
    )
except ImportError:
    from grammar_parser import (
        Grammar, GrammarRule, GrammarAlt, GrammarSymbol,
        SymbolKind, TokenDef, parse_grammar_file
    )


class PythonGenerator:
    """Generate Python lexer and parser from grammar."""

    def __init__(self, grammar: Grammar):
        self.grammar = grammar
        self.indent = 0
        self.output: List[str] = []
        self.rule_map: Dict[str, GrammarRule] = {r.name: r for r in grammar.rules}

    def generate(self) -> str:
        """Generate complete Python parser module."""
        self._emit_header()
        self._emit_imports()
        self._emit_token_constants()
        self._emit_lexer()
        self._emit_parser()
        return '\n'.join(self.output)

    def _emit(self, line: str = ''):
        """Emit a line with current indentation."""
        if line:
            self.output.append('    ' * self.indent + line)
        else:
            self.output.append('')

    def _emit_header(self):
        self._emit('"""')
        self._emit('parser_gen.py - Generated Ritz Parser')
        self._emit('')
        self._emit('THIS FILE IS AUTO-GENERATED - DO NOT EDIT')
        self._emit('Generated from grammars/ritz.grammar by tools/ritzgen_py')
        self._emit('"""')
        self._emit()

    def _emit_imports(self):
        self._emit('import re')
        self._emit('from dataclasses import dataclass, field')
        self._emit('from typing import List, Optional, Any, Tuple')
        self._emit('from enum import IntEnum, auto')
        self._emit()

    def _emit_token_constants(self):
        self._emit('# Token types')
        self._emit('class TokenType(IntEnum):')
        self.indent += 1

        for tok in self.grammar.tokens:
            self._emit(f'{tok.name} = {tok.token_id}')

        self.indent -= 1
        self._emit()

        # Token names for debugging
        self._emit('TOKEN_NAMES = {')
        self.indent += 1
        for tok in self.grammar.tokens:
            self._emit(f'TokenType.{tok.name}: "{tok.name}",')
        self.indent -= 1
        self._emit('}')
        self._emit()

    def _emit_lexer(self):
        self._emit('@dataclass')
        self._emit('class Token:')
        self.indent += 1
        self._emit('kind: TokenType')
        self._emit('value: str')
        self._emit('line: int')
        self._emit('col: int')
        self._emit('start: int = 0')
        self._emit('end: int = 0')
        self.indent -= 1
        self._emit()

        self._emit('class Lexer:')
        self.indent += 1
        self._emit('"""Tokenize Ritz source code."""')
        self._emit()

        # Token patterns (keywords and operators must come before identifiers)
        self._emit('# Token patterns - order matters!')
        self._emit('KEYWORDS = {')
        self.indent += 1
        for tok in self.grammar.tokens:
            if tok.is_literal and tok.pattern and tok.name not in ('NEWLINE', 'INDENT', 'DEDENT', 'EOF', 'ERROR', 'SKIP'):
                # Check if it looks like a keyword (alphabetic)
                if tok.pattern.isalpha() or tok.pattern.startswith('&mut'):
                    self._emit(f'"{tok.pattern}": TokenType.{tok.name},')
        self.indent -= 1
        self._emit('}')
        self._emit()

        self._emit('OPERATORS = [')
        self.indent += 1
        # Sort by length (longest first) for proper matching
        ops = []
        for tok in self.grammar.tokens:
            if tok.is_literal and tok.pattern and not tok.pattern.isalpha() and tok.name not in ('NEWLINE', 'INDENT', 'DEDENT', 'EOF', 'ERROR', 'SKIP'):
                if tok.pattern not in ('&mut',):  # &mut is in keywords
                    ops.append((tok.pattern, tok.name))
        ops.sort(key=lambda x: -len(x[0]))
        for pattern, name in ops:
            self._emit(f'("{self._escape_string(pattern)}", TokenType.{name}),')
        self.indent -= 1
        self._emit(']')
        self._emit()

        # Regex patterns
        self._emit('REGEX_PATTERNS = [')
        self.indent += 1
        for tok in self.grammar.tokens:
            if not tok.is_literal and tok.pattern:
                # Use repr() to properly escape the pattern
                escaped = tok.pattern.replace('\\', '\\\\').replace('"', '\\"')
                self._emit(f'(re.compile(r"{escaped}"), TokenType.{tok.name}),')
        self.indent -= 1
        self._emit(']')
        self._emit()

        # Lexer __init__
        self._emit('def __init__(self, source: str):')
        self.indent += 1
        self._emit('self.source = source')
        self._emit('self.pos = 0')
        self._emit('self.line = 1')
        self._emit('self.col = 1')
        self._emit('self.indent_stack = [0]')
        self._emit('self.pending_tokens: List[Token] = []')
        self._emit('self.at_line_start = True')
        self.indent -= 1
        self._emit()

        # _make_token helper
        self._emit('def _make_token(self, kind: TokenType, value: str, start: int) -> Token:')
        self.indent += 1
        self._emit('return Token(kind, value, self.line, self.col, start, self.pos)')
        self.indent -= 1
        self._emit()

        # _advance helper
        self._emit('def _advance(self, n: int = 1):')
        self.indent += 1
        self._emit('for _ in range(n):')
        self.indent += 1
        self._emit('if self.pos < len(self.source):')
        self.indent += 1
        self._emit('if self.source[self.pos] == "\\n":')
        self.indent += 1
        self._emit('self.line += 1')
        self._emit('self.col = 1')
        self.indent -= 1
        self._emit('else:')
        self.indent += 1
        self._emit('self.col += 1')
        self.indent -= 1
        self._emit('self.pos += 1')
        self.indent -= 1
        self.indent -= 1
        self.indent -= 1
        self._emit()

        # _skip_whitespace helper
        self._emit('def _skip_whitespace(self) -> bool:')
        self.indent += 1
        self._emit('"""Skip whitespace (not newlines). Returns True if any skipped."""')
        self._emit('skipped = False')
        self._emit('while self.pos < len(self.source) and self.source[self.pos] in " \\t\\r":')
        self.indent += 1
        self._emit('self._advance()')
        self._emit('skipped = True')
        self.indent -= 1
        self._emit('return skipped')
        self.indent -= 1
        self._emit()

        # _handle_indent helper
        self._emit('def _handle_indent(self):')
        self.indent += 1
        self._emit('"""Handle indentation at line start."""')
        self._emit('if not self.at_line_start:')
        self.indent += 1
        self._emit('return')
        self.indent -= 1
        self._emit('self.at_line_start = False')
        self._emit()
        self._emit('# Count leading spaces')
        self._emit('indent = 0')
        self._emit('while self.pos + indent < len(self.source) and self.source[self.pos + indent] == " ":')
        self.indent += 1
        self._emit('indent += 1')
        self.indent -= 1
        self._emit()
        self._emit('# Check what comes after the indentation')
        self._emit('rest = self.pos + indent')
        self._emit('if rest >= len(self.source):')
        self.indent += 1
        self._emit('return  # End of file')
        self.indent -= 1
        self._emit()
        self._emit('# If this is a blank line or comment-only line, skip it entirely')
        self._emit('if self.source[rest] == "\\n" or self.source[rest] == "#":')
        self.indent += 1
        self._emit('# Skip to end of line')
        self._emit('self.pos = rest')
        self._emit('if self.source[self.pos] == "#":')
        self.indent += 1
        self._emit('while self.pos < len(self.source) and self.source[self.pos] != "\\n":')
        self.indent += 1
        self._emit('self.pos += 1')
        self.indent -= 1
        self.indent -= 1
        self._emit('# Skip the newline')
        self._emit('if self.pos < len(self.source) and self.source[self.pos] == "\\n":')
        self.indent += 1
        self._emit('self.pos += 1')
        self._emit('self.line += 1')
        self.indent -= 1
        self._emit('self.at_line_start = True')
        self._emit('return  # Will retry on next call')
        self.indent -= 1
        self._emit()
        self._emit('current_indent = self.indent_stack[-1]')
        self._emit()
        self._emit('if indent > current_indent:')
        self.indent += 1
        self._emit('self.indent_stack.append(indent)')
        self._emit('self.pending_tokens.append(Token(TokenType.INDENT, "", self.line, self.col, self.pos, self.pos))')
        self.indent -= 1
        self._emit('elif indent < current_indent:')
        self.indent += 1
        self._emit('while self.indent_stack and self.indent_stack[-1] > indent:')
        self.indent += 1
        self._emit('self.indent_stack.pop()')
        self._emit('self.pending_tokens.append(Token(TokenType.DEDENT, "", self.line, self.col, self.pos, self.pos))')
        self.indent -= 1
        self.indent -= 1
        self.indent -= 1
        self._emit()

        # Main next_token method
        self._emit('def next_token(self) -> Token:')
        self.indent += 1
        self._emit('"""Return the next token."""')
        self._emit()
        self._emit('# Return pending tokens first (INDENT/DEDENT)')
        self._emit('if self.pending_tokens:')
        self.indent += 1
        self._emit('return self.pending_tokens.pop(0)')
        self.indent -= 1
        self._emit()
        self._emit('# Handle indentation at line start (loop to handle blank lines)')
        self._emit('while self.at_line_start:')
        self.indent += 1
        self._emit('self._handle_indent()')
        self._emit('if self.pending_tokens:')
        self.indent += 1
        self._emit('return self.pending_tokens.pop(0)')
        self.indent -= 1
        self.indent -= 1
        self._emit()
        self._emit('# Skip whitespace (not newlines)')
        self._emit('self._skip_whitespace()')
        self._emit()
        self._emit('# Check for EOF')
        self._emit('if self.pos >= len(self.source):')
        self.indent += 1
        self._emit('# Emit remaining DEDENTs')
        self._emit('while len(self.indent_stack) > 1:')
        self.indent += 1
        self._emit('self.indent_stack.pop()')
        self._emit('self.pending_tokens.append(Token(TokenType.DEDENT, "", self.line, self.col, self.pos, self.pos))')
        self.indent -= 1
        self._emit('if self.pending_tokens:')
        self.indent += 1
        self._emit('return self.pending_tokens.pop(0)')
        self.indent -= 1
        self._emit('return Token(TokenType.EOF, "", self.line, self.col, self.pos, self.pos)')
        self.indent -= 1
        self._emit()
        self._emit('start = self.pos')
        self._emit('start_col = self.col')
        self._emit()
        self._emit('# Check for comment')
        self._emit('if self.source[self.pos] == "#":')
        self.indent += 1
        self._emit('while self.pos < len(self.source) and self.source[self.pos] != "\\n":')
        self.indent += 1
        self._emit('self._advance()')
        self.indent -= 1
        self._emit('return self.next_token()  # Skip comment and get next')
        self.indent -= 1
        self._emit()
        self._emit('# Check for newline')
        self._emit('if self.source[self.pos] == "\\n":')
        self.indent += 1
        self._emit('self._advance()')
        self._emit('self.at_line_start = True')
        self._emit('return Token(TokenType.NEWLINE, "\\n", self.line - 1, start_col, start, self.pos)')
        self.indent -= 1
        self._emit()
        self._emit('# Check for string literals')
        self._emit("if self.source[self.pos] in '\"\\'':")
        self.indent += 1
        self._emit('return self._lex_string()')
        self.indent -= 1
        self._emit()
        self._emit('# Check for prefixed strings (c"...", s"...")')
        self._emit('if self.pos + 1 < len(self.source) and self.source[self.pos] in "cs" and self.source[self.pos + 1] == \'"\':')
        self.indent += 1
        self._emit('return self._lex_string()')
        self.indent -= 1
        self._emit()
        self._emit('# Check for operators (longest match first)')
        self._emit('for op, kind in self.OPERATORS:')
        self.indent += 1
        self._emit('if self.source[self.pos:self.pos+len(op)] == op:')
        self.indent += 1
        self._emit('self._advance(len(op))')
        self._emit('return Token(kind, op, self.line, start_col, start, self.pos)')
        self.indent -= 1
        self.indent -= 1
        self._emit()
        self._emit('# Check for identifiers and keywords')
        self._emit('if self.source[self.pos].isalpha() or self.source[self.pos] == "_":')
        self.indent += 1
        self._emit('return self._lex_identifier()')
        self.indent -= 1
        self._emit()
        self._emit('# Check for numbers')
        self._emit('if self.source[self.pos].isdigit():')
        self.indent += 1
        self._emit('return self._lex_number()')
        self.indent -= 1
        self._emit()
        self._emit('# Unknown character')
        self._emit('char = self.source[self.pos]')
        self._emit('self._advance()')
        self._emit('return Token(TokenType.ERROR, char, self.line, start_col, start, self.pos)')
        self.indent -= 1
        self._emit()

        # _lex_identifier
        self._emit('def _lex_identifier(self) -> Token:')
        self.indent += 1
        self._emit('start = self.pos')
        self._emit('start_col = self.col')
        self._emit('while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == "_"):')
        self.indent += 1
        self._emit('self._advance()')
        self.indent -= 1
        self._emit('value = self.source[start:self.pos]')
        self._emit('kind = self.KEYWORDS.get(value, TokenType.IDENT)')
        self._emit('return Token(kind, value, self.line, start_col, start, self.pos)')
        self.indent -= 1
        self._emit()

        # _lex_number
        self._emit('def _lex_number(self) -> Token:')
        self.indent += 1
        self._emit('start = self.pos')
        self._emit('start_col = self.col')
        self._emit()
        self._emit('# Check for hex/binary')
        self._emit('if self.source[self.pos] == "0" and self.pos + 1 < len(self.source):')
        self.indent += 1
        self._emit('if self.source[self.pos + 1] == "x":')
        self.indent += 1
        self._emit('self._advance(2)')
        self._emit('while self.pos < len(self.source) and self.source[self.pos] in "0123456789abcdefABCDEF":')
        self.indent += 1
        self._emit('self._advance()')
        self.indent -= 1
        self._emit('return Token(TokenType.HEX_NUMBER, self.source[start:self.pos], self.line, start_col, start, self.pos)')
        self.indent -= 1
        self._emit('elif self.source[self.pos + 1] == "b":')
        self.indent += 1
        self._emit('self._advance(2)')
        self._emit('while self.pos < len(self.source) and self.source[self.pos] in "01":')
        self.indent += 1
        self._emit('self._advance()')
        self.indent -= 1
        self._emit('return Token(TokenType.BIN_NUMBER, self.source[start:self.pos], self.line, start_col, start, self.pos)')
        self.indent -= 1
        self.indent -= 1
        self._emit()
        self._emit('# Decimal number')
        self._emit('while self.pos < len(self.source) and self.source[self.pos].isdigit():')
        self.indent += 1
        self._emit('self._advance()')
        self.indent -= 1
        self._emit()
        self._emit('# Check for float')
        self._emit('if self.pos < len(self.source) and self.source[self.pos] == ".":')
        self.indent += 1
        self._emit('if self.pos + 1 < len(self.source) and self.source[self.pos + 1].isdigit():')
        self.indent += 1
        self._emit('self._advance()  # skip .')
        self._emit('while self.pos < len(self.source) and self.source[self.pos].isdigit():')
        self.indent += 1
        self._emit('self._advance()')
        self.indent -= 1
        self._emit('return Token(TokenType.FLOAT, self.source[start:self.pos], self.line, start_col, start, self.pos)')
        self.indent -= 1
        self.indent -= 1
        self._emit()
        self._emit('return Token(TokenType.NUMBER, self.source[start:self.pos], self.line, start_col, start, self.pos)')
        self.indent -= 1
        self._emit()

        # _lex_string
        self._emit('def _lex_string(self) -> Token:')
        self.indent += 1
        self._emit('start = self.pos')
        self._emit('start_col = self.col')
        self._emit()
        self._emit('# Handle prefix')
        self._emit('if self.source[self.pos] in "cs":')
        self.indent += 1
        self._emit('self._advance()')
        self.indent -= 1
        self._emit()
        self._emit('quote = self.source[self.pos]')
        self._emit('self._advance()')
        self._emit()
        self._emit('while self.pos < len(self.source):')
        self.indent += 1
        self._emit('if self.source[self.pos] == "\\\\":')
        self.indent += 1
        self._emit('self._advance(2)  # skip escape')
        self.indent -= 1
        self._emit('elif self.source[self.pos] == quote:')
        self.indent += 1
        self._emit('self._advance()')
        self._emit('break')
        self.indent -= 1
        self._emit('else:')
        self.indent += 1
        self._emit('self._advance()')
        self.indent -= 1
        self.indent -= 1
        self._emit()
        self._emit('value = self.source[start:self.pos]')
        self._emit('kind = TokenType.CHAR if quote == "\\\'" else TokenType.STRING')
        self._emit('return Token(kind, value, self.line, start_col, start, self.pos)')
        self.indent -= 1
        self._emit()

        # tokenize method
        self._emit('def tokenize(self) -> List[Token]:')
        self.indent += 1
        self._emit('"""Tokenize entire source, return list of tokens."""')
        self._emit('tokens = []')
        self._emit('while True:')
        self.indent += 1
        self._emit('tok = self.next_token()')
        self._emit('tokens.append(tok)')
        self._emit('if tok.kind == TokenType.EOF:')
        self.indent += 1
        self._emit('break')
        self.indent -= 1
        self.indent -= 1
        self._emit('return tokens')
        self.indent -= 1

        self.indent -= 1  # End Lexer class
        self._emit()

    def _emit_parser(self):
        self._emit('class ParseError(Exception):')
        self.indent += 1
        self._emit('"""Parser error with location info."""')
        self._emit('def __init__(self, msg: str, token: Token):')
        self.indent += 1
        self._emit('self.msg = msg')
        self._emit('self.token = token')
        self._emit('super().__init__(f"{token.line}:{token.col}: {msg}")')
        self.indent -= 1
        self.indent -= 1
        self._emit()

        self._emit('class Parser:')
        self.indent += 1
        self._emit('"""Recursive descent parser for Ritz."""')
        self._emit()

        # __init__
        self._emit('def __init__(self, tokens: List[Token]):')
        self.indent += 1
        self._emit('self.tokens = tokens')
        self._emit('self.pos = 0')
        self.indent -= 1
        self._emit()

        # Helper methods
        self._emit('def _peek(self) -> Token:')
        self.indent += 1
        self._emit('if self.pos < len(self.tokens):')
        self.indent += 1
        self._emit('return self.tokens[self.pos]')
        self.indent -= 1
        self._emit('return self.tokens[-1]  # EOF')
        self.indent -= 1
        self._emit()

        self._emit('def _advance(self) -> Token:')
        self.indent += 1
        self._emit('tok = self._peek()')
        self._emit('if self.pos < len(self.tokens) - 1:')
        self.indent += 1
        self._emit('self.pos += 1')
        self.indent -= 1
        self._emit('return tok')
        self.indent -= 1
        self._emit()

        self._emit('def _check(self, kind: TokenType) -> bool:')
        self.indent += 1
        self._emit('return self._peek().kind == kind')
        self.indent -= 1
        self._emit()

        self._emit('def _match(self, *kinds: TokenType) -> Optional[Token]:')
        self.indent += 1
        self._emit('if self._peek().kind in kinds:')
        self.indent += 1
        self._emit('return self._advance()')
        self.indent -= 1
        self._emit('return None')
        self.indent -= 1
        self._emit()

        self._emit('def _expect(self, kind: TokenType) -> Token:')
        self.indent += 1
        self._emit('tok = self._peek()')
        self._emit('if tok.kind != kind:')
        self.indent += 1
        self._emit('raise ParseError(f"expected {TOKEN_NAMES[kind]}, got {TOKEN_NAMES[tok.kind]}", tok)')
        self.indent -= 1
        self._emit('return self._advance()')
        self.indent -= 1
        self._emit()

        # Generate parse methods for each rule
        for rule in self.grammar.rules:
            self._emit_parse_method(rule)

        self.indent -= 1  # End Parser class

    def _is_left_recursive(self, rule: GrammarRule) -> bool:
        """Check if a rule has left-recursive alternatives."""
        for alt in rule.alternatives:
            if alt.symbols and alt.symbols[0].name == rule.name:
                return True
        return False

    def _is_binary_expr_rule(self, rule: GrammarRule) -> Optional[str]:
        """
        Check if rule is a binary expression rule of the form:
            rule : base OP rule | base

        Returns the base nonterminal name if true, None otherwise.
        These rules can be optimized to parse the base once, then check operators.
        """
        if len(rule.alternatives) < 2:
            return None

        # Check that last alternative is just the base nonterminal
        last_alt = rule.alternatives[-1]
        if len(last_alt.symbols) != 1:
            return None
        if last_alt.symbols[0].name.isupper():  # Must be nonterminal, not terminal
            return None

        base_name = last_alt.symbols[0].name

        # Check that all other alternatives are: base OP rule
        for alt in rule.alternatives[:-1]:
            if len(alt.symbols) != 3:
                return None
            # First must be the base nonterminal
            if alt.symbols[0].name != base_name:
                return None
            # Second must be a terminal (operator)
            if not alt.symbols[1].name.isupper():
                return None
            # Third must be this rule (right-recursive)
            if alt.symbols[2].name != rule.name:
                return None

        return base_name

    def _is_optional_suffix_rule(self, rule: GrammarRule) -> Optional[tuple]:
        """
        Check if rule is an optional suffix rule of the form:
            rule : base SUFFIX... | base

        Where SUFFIX... is one or more additional symbols.
        Returns (base_name, suffix_symbols) if true, None otherwise.

        Example: cast_expr : unary_expr AS type | unary_expr
        Example: try_expr : postfix_expr QUESTION | postfix_expr
        """
        if len(rule.alternatives) != 2:
            return None

        first_alt = rule.alternatives[0]
        second_alt = rule.alternatives[1]

        # Second alternative must be just a single nonterminal (the base)
        if len(second_alt.symbols) != 1:
            return None
        if second_alt.symbols[0].name.isupper():  # Must be nonterminal
            return None

        base_name = second_alt.symbols[0].name

        # First alternative must start with the same base
        if len(first_alt.symbols) < 2:
            return None
        if first_alt.symbols[0].name != base_name:
            return None

        # Return base name and the suffix symbols (everything after base)
        suffix_symbols = first_alt.symbols[1:]
        return (base_name, suffix_symbols, first_alt.action)

    def _emit_parse_method(self, rule: GrammarRule):
        """Generate a parse method for a grammar rule."""
        return_type = rule.return_type or 'Any'
        # Map Ritz types to Python types
        if return_type.startswith('*'):
            return_type = 'Any'  # Pointer types become Any
        elif return_type in ('i32', 'i64', 'u8', 'u64'):
            return_type = 'int'
        elif return_type == 'bool':
            return_type = 'bool'

        # Check for left recursion
        if self._is_left_recursive(rule):
            self._emit_left_recursive_method(rule, return_type)
            return

        # Check for binary expression rules (base OP rule | base)
        base_name = self._is_binary_expr_rule(rule)
        if base_name:
            self._emit_binary_expr_method(rule, return_type, base_name)
            return

        # Check for optional suffix rules (base SUFFIX | base)
        suffix_info = self._is_optional_suffix_rule(rule)
        if suffix_info:
            self._emit_optional_suffix_method(rule, return_type, suffix_info)
            return

        self._emit(f'def parse_{rule.name}(self) -> Optional[{return_type}]:')
        self.indent += 1
        self._emit(f'"""Parse rule: {rule.name}"""')
        self._emit('start_pos = self.pos')
        self._emit()

        for i, alt in enumerate(rule.alternatives):
            if i > 0:
                self._emit('# Try next alternative')
                self._emit('self.pos = start_pos')
                self._emit()

            self._emit(f'# Alternative {i + 1}')
            self._emit('try:')
            self.indent += 1

            # Generate code for each symbol
            result_vars = []
            for j, sym in enumerate(alt.symbols):
                var_name = f'result_{j + 1}'
                result_vars.append(var_name)
                self._emit_symbol_parse(sym, var_name)

            # Handle semantic action or return result
            if alt.action:
                action = self._translate_action(alt.action, result_vars, rule.name)
                self._emit(f'return {action}')
            elif len(result_vars) == 1:
                self._emit(f'return {result_vars[0]}')
            elif len(result_vars) > 1:
                # Multiple symbols - return a dict with all of them
                items = ', '.join(f'"{i}": {v}' for i, v in enumerate(result_vars))
                self._emit(f'return {{"_rule": "{rule.name}", {items}}}')
            else:
                self._emit('return None')

            self.indent -= 1
            self._emit('except ParseError:')
            self.indent += 1
            self._emit('self.pos = start_pos')
            self.indent -= 1
            self._emit()

        self._emit('return None')
        self.indent -= 1
        self._emit()

    def _emit_left_recursive_method(self, rule: GrammarRule, return_type: str):
        """Generate a parse method for a left-recursive rule using iteration."""
        self._emit(f'def parse_{rule.name}(self) -> Optional[{return_type}]:')
        self.indent += 1
        self._emit(f'"""Parse rule: {rule.name} (left-recursion eliminated)"""')
        self._emit()

        # Separate base cases (non-left-recursive) from recursive cases
        base_alts = []
        recursive_alts = []
        for alt in rule.alternatives:
            if alt.symbols and alt.symbols[0].name == rule.name:
                recursive_alts.append(alt)
            else:
                base_alts.append(alt)

        # First, parse a base case
        self._emit('# Parse base case')
        self._emit('start_pos = self.pos')
        self._emit('result = None')
        self._emit()

        for i, alt in enumerate(base_alts):
            if i > 0:
                self._emit('if result is None:')
                self.indent += 1
                self._emit('self.pos = start_pos')

            self._emit('try:')
            self.indent += 1

            result_vars = []
            for j, sym in enumerate(alt.symbols):
                var_name = f'base_{j + 1}'
                result_vars.append(var_name)
                self._emit_symbol_parse(sym, var_name)

            if len(result_vars) == 1:
                self._emit(f'result = {result_vars[0]}')
            elif len(result_vars) > 1:
                # Multiple symbols - return a dict with all of them
                items = ', '.join(f'"{i}": {v}' for i, v in enumerate(result_vars))
                self._emit(f'result = {{"_rule": "{rule.name}", {items}}}')

            self.indent -= 1
            self._emit('except ParseError:')
            self.indent += 1
            self._emit('pass')
            self.indent -= 1

            if i > 0:
                self.indent -= 1

        self._emit()
        self._emit('if result is None:')
        self.indent += 1
        self._emit('return None')
        self.indent -= 1
        self._emit()

        # Then, parse recursive suffixes in a loop
        if recursive_alts:
            self._emit('# Parse recursive suffixes')
            self._emit('while True:')
            self.indent += 1
            self._emit('suffix_pos = self.pos')
            self._emit('matched = False')
            self._emit()

            for i, alt in enumerate(recursive_alts):
                # Skip the first symbol (the left-recursive reference)
                suffix_symbols = alt.symbols[1:]

                if i > 0:
                    self._emit('if not matched:')
                    self.indent += 1
                    self._emit('self.pos = suffix_pos')

                self._emit('try:')
                self.indent += 1

                result_vars = ['result']  # The left-recursive part
                for j, sym in enumerate(suffix_symbols):
                    var_name = f'suffix_{j + 1}'
                    result_vars.append(var_name)
                    self._emit_symbol_parse(sym, var_name)

                # Build the result
                items = ', '.join(f'"{i}": {v}' for i, v in enumerate(result_vars))
                self._emit(f'result = {{"_rule": "{rule.name}", {items}}}')
                self._emit('matched = True')

                self.indent -= 1
                self._emit('except ParseError:')
                self.indent += 1
                self._emit('pass')
                self.indent -= 1

                if i > 0:
                    self.indent -= 1

            self._emit()
            self._emit('if not matched:')
            self.indent += 1
            self._emit('self.pos = suffix_pos')
            self._emit('break')
            self.indent -= 1

            self.indent -= 1

        self._emit()
        self._emit('return result')
        self.indent -= 1
        self._emit()

    def _emit_binary_expr_method(self, rule: GrammarRule, return_type: str, base_name: str):
        """
        Generate optimized parsing for binary expression rules.

        Instead of:
            try: parse_base(); expect(OP1); parse_rule()
            except: reset
            try: parse_base(); expect(OP2); parse_rule()  # re-parses base!
            except: reset
            try: parse_base(); return  # re-parses base again!
            except: reset

        Generate:
            left = parse_base()
            if left is None: return None
            op = match(OP1, OP2, ...)
            if op is None: return left  # no operator, return base as-is
            right = parse_rule()  # recursive call
            if right is None: error
            return (left, op, right)
        """
        self._emit(f'def parse_{rule.name}(self) -> Optional[{return_type}]:')
        self.indent += 1
        self._emit(f'"""Parse rule: {rule.name} (binary expression, optimized)"""')
        self._emit()

        # Parse the base/left operand once
        self._emit(f'# Parse left operand ({base_name})')
        self._emit(f'left = self.parse_{base_name}()')
        self._emit('if left is None:')
        self.indent += 1
        self._emit('return None')
        self.indent -= 1
        self._emit()

        # Collect all operators from the non-fallback alternatives
        operators = []
        for alt in rule.alternatives[:-1]:
            op_name = alt.symbols[1].name
            operators.append(op_name)

        # Try to match any of the operators
        op_list = ', '.join(f'TokenType.{op}' for op in operators)
        self._emit('# Check for operator')
        self._emit(f'op = self._match({op_list})')
        self._emit('if op is None:')
        self.indent += 1
        self._emit('return left  # No operator, just return base')
        self.indent -= 1
        self._emit()

        # Parse the right operand (recursive)
        self._emit(f'# Parse right operand ({rule.name})')
        self._emit(f'right = self.parse_{rule.name}()')
        self._emit('if right is None:')
        self.indent += 1
        self._emit(f'raise ParseError("expected {rule.name} after operator", self._peek())')
        self.indent -= 1
        self._emit()

        # Return the binary expression
        self._emit(f'return {{"_rule": "{rule.name}", "left": left, "op": op, "right": right}}')
        self.indent -= 1
        self._emit()

    def _emit_optional_suffix_method(self, rule: GrammarRule, return_type: str, suffix_info: tuple):
        """
        Generate optimized parsing for optional suffix rules.

        Instead of:
            try: parse_base(); expect(SUFFIX)  # parses base
            except: reset
            try: parse_base(); return  # re-parses base!
            except: reset

        Generate:
            base = parse_base()
            if base is None: return None
            # Try to match suffix
            if peek() matches first suffix token:
                parse rest of suffix
                return (base, suffix)
            return base
        """
        base_name, suffix_symbols, action = suffix_info

        self._emit(f'def parse_{rule.name}(self) -> Optional[{return_type}]:')
        self.indent += 1
        self._emit(f'"""Parse rule: {rule.name} (optional suffix, optimized)"""')
        self._emit()

        # Parse the base once
        self._emit(f'# Parse base ({base_name})')
        self._emit(f'base = self.parse_{base_name}()')
        self._emit('if base is None:')
        self.indent += 1
        self._emit('return None')
        self.indent -= 1
        self._emit()

        # Check if first suffix symbol (must be a terminal) is present
        first_suffix = suffix_symbols[0]
        if first_suffix.name.isupper():  # Terminal
            self._emit(f'# Try to match suffix starting with {first_suffix.name}')
            self._emit(f'suffix_tok = self._match(TokenType.{first_suffix.name})')
            self._emit('if suffix_tok is not None:')
            self.indent += 1

            # Parse remaining suffix symbols
            result_vars = ['base', 'suffix_tok']
            for i, sym in enumerate(suffix_symbols[1:]):
                var_name = f'suffix_{i + 2}'
                result_vars.append(var_name)
                self._emit_symbol_parse(sym, var_name)

            # Return combined result
            items = ', '.join(f'"{i}": {v}' for i, v in enumerate(result_vars))
            self._emit(f'return {{"_rule": "{rule.name}", {items}}}')
            self.indent -= 1
            self._emit()
        else:
            # First suffix is a nonterminal - can't easily peek, use try/except
            self._emit('# Try to parse optional suffix')
            self._emit('suffix_pos = self.pos')
            self._emit('try:')
            self.indent += 1
            result_vars = ['base']
            for i, sym in enumerate(suffix_symbols):
                var_name = f'suffix_{i + 1}'
                result_vars.append(var_name)
                self._emit_symbol_parse(sym, var_name)
            items = ', '.join(f'"{i}": {v}' for i, v in enumerate(result_vars))
            self._emit(f'return {{"_rule": "{rule.name}", {items}}}')
            self.indent -= 1
            self._emit('except ParseError:')
            self.indent += 1
            self._emit('self.pos = suffix_pos')
            self.indent -= 1
            self._emit()

        # Return just the base if suffix didn't match
        self._emit('return base')
        self.indent -= 1
        self._emit()

    def _is_nullable_rule(self, rule_name: str) -> bool:
        """Check if a rule can match empty (has an epsilon/empty alternative)."""
        if rule_name not in self.rule_map:
            return False
        rule = self.rule_map[rule_name]
        for alt in rule.alternatives:
            if len(alt.symbols) == 0:
                return True
        return False

    def _emit_symbol_parse(self, sym: GrammarSymbol, var_name: str):
        """Emit code to parse a symbol."""
        if sym.kind == SymbolKind.TERMINAL:
            self._emit(f'{var_name} = self._expect(TokenType.{sym.name})')

        elif sym.kind == SymbolKind.NONTERMINAL:
            self._emit(f'{var_name} = self.parse_{sym.name}()')
            # Don't raise error if the rule is nullable (can match empty)
            if not self._is_nullable_rule(sym.name):
                self._emit(f'if {var_name} is None:')
                self.indent += 1
                self._emit(f'raise ParseError("expected {sym.name}", self._peek())')
                self.indent -= 1

        elif sym.kind == SymbolKind.OPTIONAL:
            if sym.name.isupper():
                self._emit(f'{var_name} = self._match(TokenType.{sym.name})')
            else:
                self._emit(f'{var_name} = self.parse_{sym.name}()')

        elif sym.kind == SymbolKind.STAR:
            self._emit(f'{var_name} = []')
            self._emit('while True:')
            self.indent += 1
            if sym.name.isupper():
                self._emit(f'item = self._match(TokenType.{sym.name})')
            else:
                self._emit(f'item = self.parse_{sym.name}()')
            self._emit('if item is None:')
            self.indent += 1
            self._emit('break')
            self.indent -= 1
            self._emit(f'{var_name}.append(item)')
            self.indent -= 1

        elif sym.kind == SymbolKind.PLUS:
            # At least one required
            if sym.name.isupper():
                self._emit(f'first = self._expect(TokenType.{sym.name})')
            else:
                self._emit(f'first = self.parse_{sym.name}()')
                self._emit('if first is None:')
                self.indent += 1
                self._emit(f'raise ParseError("expected {sym.name}", self._peek())')
                self.indent -= 1
            self._emit(f'{var_name} = [first]')
            self._emit('while True:')
            self.indent += 1
            if sym.name.isupper():
                self._emit(f'item = self._match(TokenType.{sym.name})')
            else:
                self._emit(f'item = self.parse_{sym.name}()')
            self._emit('if item is None:')
            self.indent += 1
            self._emit('break')
            self.indent -= 1
            self._emit(f'{var_name}.append(item)')
            self.indent -= 1

    def _translate_action(self, action: str, result_vars: List[str], rule_name: str) -> str:
        """Translate semantic action to Python code."""
        # For now, ignore the Ritz semantic actions and return a dict/tuple
        # The semantic actions in the grammar are for Ritz code generation,
        # not Python. We'll build AST nodes differently.

        # If action is just $N, return that directly
        if action.strip().startswith('$') and action.strip()[1:].isdigit():
            idx = int(action.strip()[1:]) - 1
            if idx < len(result_vars):
                return result_vars[idx]

        # Otherwise, return a dict with all results
        if len(result_vars) == 0:
            return 'None'
        elif len(result_vars) == 1:
            return result_vars[0]
        else:
            items = ', '.join(f'"{i}": {v}' for i, v in enumerate(result_vars))
            return f'{{"_rule": "{rule_name}", {items}}}'

    def _escape_string(self, s: str) -> str:
        """Escape a string for Python source."""
        return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m tools.ritzgen_py.generator <grammar_file>", file=sys.stderr)
        sys.exit(1)

    grammar_file = sys.argv[1]
    verbose = '--verbose' in sys.argv

    grammar = parse_grammar_file(grammar_file)

    if verbose:
        print(f"# Loaded {len(grammar.tokens)} tokens, {len(grammar.rules)} rules", file=sys.stderr)

    generator = PythonGenerator(grammar)
    output = generator.generate()
    print(output)


if __name__ == '__main__':
    main()
