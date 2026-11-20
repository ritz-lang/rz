#!/usr/bin/env python3
"""
ritz_generator.py - Generate Ritz source files from grammar

Reads a .grammar file and generates:
1. tokens.ritz     - Token kind constants + Token struct
2. parser_core.ritz - Core parser helpers (p_peek, p_advance, parser_init)
3. parser_toplevel.ritz - Module-level parsing (fn_def, struct_def, etc.)
4. parser_stmt.ritz - Statement parsing (if, while, let, var, assign)
5. parser_expr.ritz - Expression parsing (binary, unary, postfix, primary)
6. parser_type.ritz - Type parsing (type_spec, generic_params)
7. ast_helpers.ritz - AST node constructor stubs
8. lexer_scan_gen.ritz - Direct-coded keyword and operator scanner

THIS FILE IS THE GENERATOR - the output files are auto-generated Ritz code.

The parser is split into modules to keep each file under 500 lines.
"""

import sys
import re
import os
from typing import List, Dict, Set, Optional, Tuple

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


# Rule categorization for modular parser output
# Map grammar token IDs to hand-written tokens.ritz IDs
# The hand-written tokens.ritz uses specific ID ranges, the grammar uses sequential IDs.
# We need the generated code to use the hand-written token ID scheme.
HAND_WRITTEN_TOKEN_IDS = {
    # Built-in
    'EOF': 0, 'ERROR': 1, 'SKIP': 2, 'NEWLINE': 3, 'INDENT': 4, 'DEDENT': 5,
    # Keywords
    'FN': 10, 'PUB': 11, 'EXTERN': 12, 'LET': 13, 'VAR': 14, 'RETURN': 15,
    'IF': 16, 'ELSE': 17, 'WHILE': 18, 'BREAK': 19, 'CONTINUE': 20,
    'CONST': 21, 'STRUCT': 22, 'IMPORT': 23, 'AS': 24, 'NIL': 25,
    'IMPL': 26, 'FOR': 27, 'TRAIT': 28, 'ENUM': 29, 'MATCH': 30,
    'DEFER': 31, 'LOOP': 32, 'UNSAFE': 33, 'IN': 34,
    'AND': 35, 'OR': 36, 'NOT': 37, 'TRUE': 38, 'FALSE': 39,
    'NULL': 40, 'SELF': 41, 'MUT': 42, 'ASSERT': 44, 'FLOAT': 45,  # 43 was PASS: an IDENT now (#3320)
    'TYPE': 46, 'THEN': 47,
    'ASM': 48,  # inline assembly, LANGUAGE_SPEC §18.6 (AGAST #3394)
    'ASYNC': 49, 'AWAIT': 60,  # parsed, then refused until AGAST #3814 (#1456)
    'HEAP': 61,  # `heap e`, lowered to __heap_new (AGAST #3934)
    # Type keywords
    'I8': 50, 'I16': 51, 'I32': 52, 'I64': 53,
    'U8': 54, 'U16': 55, 'U32': 56, 'U64': 57,
    'BOOL': 58, 'VOID': 59,
    # Operators
    'PLUS': 70, 'MINUS': 71, 'STAR': 72, 'SLASH': 73, 'PERCENT': 74,
    'AMP': 75, 'PIPE': 76, 'CARET': 77, 'TILDE': 78, 'AT': 79,
    'BANG': 80, 'QUESTION': 81, 'SHL': 82, 'SHR': 83,
    'ANDAND': 91, 'OROR': 92,
    # Comparison
    'EQ': 85, 'NE': 86, 'LT': 87, 'GT': 88, 'LE': 89, 'GE': 90,
    # Assignment/arrows
    'ASSIGN': 95, 'PLUS_EQ': 96, 'MINUS_EQ': 97, 'STAR_EQ': 98, 'SLASH_EQ': 99,
    'ARROW': 100, 'FAT_ARROW': 101, 'DOTDOT': 102, 'DOTDOTEQ': 103,  # AGAST #1530
    # Delimiters
    'LPAREN': 110, 'RPAREN': 111, 'LBRACKET': 112, 'RBRACKET': 113,
    'LBRACE': 114, 'RBRACE': 115,
    # Punctuation
    'DOT': 120, 'COMMA': 121, 'COLON': 122, 'SEMICOLON': 123,
    'HASH': 124, 'DBLBRACKET_L': 125, 'DBLBRACKET_R': 126,
    'LBRACKET2': 125, 'RBRACKET2': 126,  # Aliases for double bracket
    'COLON_AMP': 127,  # `:&`, the borrow sigil (AGAST #1565)
    'COLON_EQ': 128,  # `:=`, the move sigil (AGAST #3911)
    # Literals
    'IDENT': 130, 'NUMBER': 131, 'STRING': 132, 'CSTRING': 133,
    'SSTRING': 134, 'CHAR': 135,
    # One raw line of an `asm` block's body (AGAST #3394).  No pattern: the
    # lexer makes it in its asm body mode (lexer.ritz lexer_asm_line).
    'ASM_LINE': 136,
    # Whitespace
    'WHITESPACE': 140, 'COMMENT': 141,
}


# Grammar tokens the lexer makes itself, never by matching a pattern.
SCANNER_SKIP_TOKENS = frozenset({'EOF', 'ERROR', 'SKIP', 'NEWLINE', 'INDENT', 'DEDENT', 'ASM_LINE'})

# The regex tokens ritz1/src/lexer.ritz scans by hand, exactly as the
# grammar spells them (AGAST #1821).  The generator refuses any other
# pattern: a changed regex needs its scan_* function changed with it.
SCANNED_REGEX_TOKENS = {
    'IDENT': r'[a-zA-Z_][a-zA-Z0-9_]*',             # lexer_scan_ident
    'NUMBER': r'0x[0-9a-fA-F]+|0b[01]+|[0-9]+',     # lexer_scan_number
    'FLOAT': r'[0-9]+\.[0-9]+([eE][+-]?[0-9]+)?|[0-9]+[eE][+-]?[0-9]+',  # lexer_scan_number
    'STRING': r'"([^"\\]|\\.)*"',                 # lexer_scan_string
    'CHAR': r"'([^'\\]|\\.|\\x[^'\n]*)'",         # lexer_scan_char
    'CSTRING': r'c"([^"\\]|\\.)*"',               # lexer_scan_string
    'WHITESPACE': r'[ \t\r]+',                      # lexer_next_token
    'COMMENT': r'#[^\n]*',                          # lexer_skip_comment
}

# Bytes lexer_next_token dispatches on before it tries an operator: an
# operator starting with one could never be lexed.
SCANNER_DISPATCHED_CHARS = '"\'#$ \t\r\n'


# Rules whose parse_<rule>() other ritz1 files call (parser_api, main, ...).
# They're `pub`; every other parse_<rule>() is private to the generated parser
# (AGAST #3414, LARB R45a: a fn called from another file must be `pub`).
PUBLIC_RULES = frozenset({'module', 'expr'})


def unmapped_tokens(grammar: Grammar) -> List[str]:
    """Grammar tokens that have no ritz1 token ID (and so can't be lexed)."""
    return [t.name for t in grammar.tokens if t.name not in HAND_WRITTEN_TOKEN_IDS]


class RitzGenerator:
    """Generate Ritz source files from grammar."""

    def __init__(self, grammar: Grammar):
        self.grammar = grammar
        self.output: List[str] = []
        self.rule_map: Dict[str, GrammarRule] = {r.name: r for r in grammar.rules}

    def _emit(self, line: str = ''):
        """Emit a line of Ritz code."""
        self.output.append(line)

    def _reset(self):
        self.output = []

    def _get_output(self) -> str:
        return '\n'.join(self.output)

    # =========================================================================
    # Token generation
    # =========================================================================

    def generate_tokens(self) -> str:
        """Generate tokens.ritz with constants and Token struct."""
        self._reset()
        self._emit('# Generated by ritzgen - Token definitions')
        self._emit('#')
        self._emit('# This is auto-generated code. Do not edit.')
        self._emit('')

        # Built-in token types
        self._emit('# Built-in token types')
        builtins = ['EOF', 'ERROR', 'SKIP', 'NEWLINE', 'INDENT', 'DEDENT']
        for name in builtins:
            tid = HAND_WRITTEN_TOKEN_IDS[name]
            self._emit(f'const TOK_{name}: i32 = {tid}')
        self._emit('')

        # User-defined tokens - collect all grammar tokens with known IDs,
        # sorted by ID, grouped by ID range
        all_user_toks = []
        for tok in self.grammar.tokens:
            if tok.name in builtins:
                continue
            tid = HAND_WRITTEN_TOKEN_IDS.get(tok.name)
            if tid is not None:
                all_user_toks.append((tid, tok.name))
        all_user_toks.sort()

        # Group by ID range with labels
        groups = [
            (10, 49, 'Keywords'),
            (50, 59, 'Type keywords'),
            (60, 69, 'Keywords (10-49 is full)'),
            (70, 84, 'Operators'),
            (85, 92, 'Comparison operators'),
            (95, 109, 'Assignment, arrows and ranges'),
            (110, 115, 'Delimiters'),
            (120, 128, 'Punctuation'),
            (130, 136, 'Identifiers and literals'),
            (140, 141, 'Whitespace'),
        ]

        # AGAST #1530: an ID outside every group used to vanish from
        # tokens.ritz without a word (DOTDOTEQ = 103 did), while parser.ritz
        # and lexer_setup_gen.ritz still referenced TOK_<NAME>.
        ungrouped = [name for tid, name in all_user_toks
                     if not any(lo <= tid <= hi for lo, hi, _ in groups)]
        if ungrouped:
            raise ValueError(
                f"token ID(s) outside every tokens.ritz group: {', '.join(ungrouped)}. "
                "Widen a group in RitzGenerator.generate_tokens."
            )

        for lo, hi, label in groups:
            toks_in_group = [(tid, name) for tid, name in all_user_toks if lo <= tid <= hi]
            if not toks_in_group:
                continue
            self._emit(f'# {label}')
            for tid, name in toks_in_group:
                self._emit(f'const TOK_{name}: i32 = {tid}')
            self._emit('')

        # AGAST #1819: kind -> printable spelling, for the "expected ..." half
        # of a located parse error.  Generated here so it cannot drift from
        # the %tokens section; regex tokens get a word, literals their text.
        FRIENDLY = {
            'EOF': 'end of file',
            'NEWLINE': 'end of line',
            'INDENT': 'indent',
            'DEDENT': 'dedent',
            'ERROR': 'token',
            'SKIP': 'token',
            'IDENT': 'identifier',
            'NUMBER': 'number',
            'FLOAT': 'number',
            'INT': 'number',
            'STRING': 'string',
            'CSTRING': 'c string',
            'CHAR': 'character',
            'ASM_LINE': 'asm text',
        }
        self._emit('')
        self._emit('# AGAST #1819: the spelling of a token kind, for diagnostics.')
        self._emit('pub fn tok_display_name(kind: i32) -> *u8')
        for tid, name in [(HAND_WRITTEN_TOKEN_IDS[b], b) for b in builtins]:
            self._emit(f'    if kind == TOK_{name}')
            self._emit(f'        return c"{FRIENDLY[name]}"')
        for tid, name in all_user_toks:
            tok = next(t for t in self.grammar.tokens if t.name == name)
            if tok.is_skip:
                continue
            if tok.is_literal:
                text = tok.pattern
            else:
                text = FRIENDLY.get(name, name.lower().replace('_', ' '))
            self._emit(f'    if kind == TOK_{name}')
            self._emit(f'        return c"{text}"')
        self._emit('    return c"token"')

        # Token struct
        self._emit('# Token structure')
        self._emit('struct Token')
        self._emit('    kind: i32')
        self._emit('    start: *u8')
        self._emit('    len: i32')
        self._emit('    line: i32')
        self._emit('    col: i32')
        self._emit('    # Extended fields for string content')
        self._emit('    string_val: *u8')
        self._emit('    string_len: i32')
        self._emit('')

        # token_new function
        # It takes the token's source pointer, not an offset it would have no
        # source to add to: it used to take `pos`, drop it and leave `start`
        # null for every token the lexer did not patch (AGAST #3888).
        self._emit('# A Token of `kind` whose `len` bytes start at `start` in the source')
        self._emit('# (zero-length layout and EOF tokens point at the byte they stand on).')
        self._emit('pub fn token_new(kind: i32, start: *u8, len: i32, line: i64, col: i64) -> Token')
        self._emit('    Token {')
        self._emit('        kind: kind,')
        self._emit('        start: start,')
        self._emit('        len: len,')
        self._emit('        line: line as i32,')
        self._emit('        col: col as i32,')
        self._emit('        string_val: null,')
        self._emit('        string_len: 0')
        self._emit('    }')

        return self._get_output()

    # =========================================================================
    # Parser generation
    # =========================================================================

    def generate_parser(self) -> str:
        """Generate parser.ritz with recursive descent parser functions.

        The monolithic single-file output is the only shape ritz1 consumes;
        the modular split (parser_core/toplevel/stmt/expr/type) was dead and
        was deleted with the rest of the dead generator paths (AGAST #1819).
        """
        self._reset()
        self._emit('# Generated by ritzgen - Ritz recursive descent parser')
        self._emit('#')
        self._emit('# This is auto-generated code. Do not edit.')
        self._emit('')

        # Imports
        self._emit('# Import dependencies')
        self._emit('import ast')
        self._emit('import ast_helpers')
        self._emit('import tokens_gen')
        self._emit('')

        # Parser helper functions
        self._emit('# Parser helper functions')
        self._emit('')
        self._generate_parser_init()
        self._emit('')
        self._generate_parser_helpers()
        self._emit('')

        # Generate parse functions for each rule
        for rule in self.grammar.rules:
            self._generate_parse_function(rule)
            self._emit('')

        return self._get_output()

    def _generate_parser_init(self):
        self._emit('pub fn parser_init(p: *Parser, tokens: *Token, count: i32, arena_ptr: *u8)')
        self._emit('    p.tokens = tokens')
        self._emit('    p.token_count = count')
        self._emit('    p.pos = 0')
        self._emit('    p.error = 0')
        self._emit('    p.error_msg = null')
        self._emit('    p.heap_base = arena_ptr')
        self._emit('    p.heap_offset = 0')
        self._emit('    p.module = null')
        self._emit('    # Initialize all remaining Parser fields to prevent garbage values')
        self._emit('    p.last_type_name = null')
        self._emit('    p.last_type_name_len = 0')
        self._emit('    p.last_pointee_type = 0')
        self._emit('    p.last_array_size = 0')
        self._emit('    p.last_array_elem_type = 0')
        self._emit('    p.last_array_elem_type_name = null')
        self._emit('    p.last_array_elem_type_name_len = 0')
        self._emit('    p.fn_return_type_name = null')
        self._emit('    p.fn_return_type_name_len = 0')
        self._emit('    p.last_call_type_suffix = null')
        self._emit('    p.last_call_type_suffix_len = 0')
        self._emit('    p.last_ref_inner_type = 0')
        self._emit('    p.last_inner_ref = 0')  # AGAST #2399
        self._emit('    p.var_inner_ref = 0')
        self._emit('    # Conditional-compilation skip flag. MUST be zeroed — if left')
        self._emit('    # garbage we drop every parsed item and produce an empty module.')
        self._emit('    # Symptom: with RITZ_PATH set (different heap layout), the first')
        self._emit('    # parsed fn lands on a non-zero skip_item and silently disappears,')
        self._emit('    # leaving callers with extern declarations only at link time.')
        self._emit('    p.skip_item = 0')
        self._emit('    # AGAST #1671: fn-type signature side channel (see ast.ritz).')
        self._emit('    p.last_fn_sig = null')
        self._emit('    p.last_fn_sig_pos = -1')
        self._emit('    p.var_fn_sig = null')
        # AGAST #2943: furthest token reached, for dropped-item diagnostics.
        self._emit('    p.max_pos = 0')
        # AGAST #1819: farthest expected-token failure; -1 = none yet.
        self._emit('    p.fail_pos = -1')
        self._emit('    p.fail_b0 = 0 as u64')
        self._emit('    p.fail_b1 = 0 as u64')
        self._emit('    p.fail_b2 = 0 as u64')

    def _generate_parser_helpers(self):
        self._emit('pub fn p_peek(p: *Parser) -> i32')
        self._emit('    if p.pos >= p.token_count')
        self._emit('        return TOK_EOF')
        self._emit('    return (p.tokens + p.pos).kind')
        self._emit('')
        self._emit('pub fn p_advance(p: *Parser) -> i32')
        self._emit('    let k: i32 = p_peek(p)')
        self._emit('    if p.pos < p.token_count')
        self._emit('        p.pos = p.pos + 1')
        # AGAST #2943: record how far the parse got.  Backtracking rewinds
        # p.pos, not this, so a failed item can be reported where its
        # deepest attempt stopped rather than at the item's first token.
        self._emit('        if p.pos > p.max_pos')
        self._emit('            p.max_pos = p.pos')
        self._emit('    return k')
        self._emit('')
        self._emit('fn p_expect(p: *Parser, kind: i32) -> i32')
        # AGAST #1819: once an alternative has failed, every later expectation
        # in its sequence is a no-op.  That is what lets the emitter drop the
        # per-symbol `if p.error == 0` nesting: the parse functions return at
        # entry and this returns before consuming or recording a failure, so
        # the consumed-prefix and the recorded farthest failure are identical
        # to the nested form.
        self._emit('    if p.error != 0')
        self._emit('        return 0')
        self._emit('    if p_peek(p) == kind')
        self._emit('        p_advance(p)')
        self._emit('        return 1')
        # AGAST #1819: remember what a failure here wanted, at the farthest
        # token the parse reached, for the located "expected ..." list.
        self._emit('    p_record_fail(p, kind)')
        self._emit('    p.error = 1')
        self._emit('    return 0')
        self._emit('')
        # AGAST #1819: the backtracking reset between alternatives, one call
        # instead of two emitted lines per alternative.
        self._emit('fn p_rewind(p: *Parser, start_pos: i32)')
        self._emit('    p.pos = start_pos')
        self._emit('    p.error = 0')
        self._emit('')
        # AGAST #1819: expect-and-capture in one call.  The unread form stays
        # p_expect, so a terminal costs one emitted line either way.
        self._emit('fn p_take(p: *Parser, kind: i32) -> Token')
        self._emit('    let t: Token = p_current_token(p)')
        self._emit('    if p.error != 0')
        self._emit('        return t')
        self._emit('    if t.kind == kind')
        self._emit('        p_advance(p)')
        self._emit('        return t')
        self._emit('    p_record_fail(p, kind)')
        self._emit('    p.error = 1')
        self._emit('    return t')
        self._emit('')
        self._emit('fn p_current_token(p: *Parser) -> Token')
        self._emit('    if p.pos >= p.token_count')
        self._emit('        var eof: Token')
        self._emit('        eof.kind = TOK_EOF')
        self._emit('        eof.start = null')
        self._emit('        eof.len = 0')
        self._emit('        eof.line = 0')
        self._emit('        eof.col = 0')
        self._emit('        return eof')
        self._emit('    return *(p.tokens + p.pos)')

    def _get_return_type(self, rule: GrammarRule) -> str:
        """Get the Ritz return type for a rule."""
        if rule.return_type:
            return rule.return_type
        # Rules with no explicit return type that are "void-like"
        # Check if all alts are side-effect-only (actions that don't return)
        return 'i32'

    def _get_default_return(self, rule: GrammarRule) -> str:
        """Get the default null/zero return for a rule's type."""
        rt = self._get_return_type(rule)
        if rt.startswith('*'):
            return 'null'
        elif rt == 'Token':
            return 'p_current_token(p)'  # Return a dummy token
        elif rt == 'i32':
            return '0'
        return 'null'

    def _symbol_type(self, sym: GrammarSymbol, rule_context: str) -> str:
        """Determine the Ritz type for a parsed symbol result."""
        base_name = sym.name
        if base_name.isupper():
            # Terminal — always Token
            return 'Token'
        # Nonterminal — look up the rule
        if base_name in self.rule_map:
            r = self.rule_map[base_name]
            if r.return_type:
                return r.return_type
        return 'i32'

    def _symbol_default(self, sym: GrammarSymbol) -> str:
        """Get the default/null value for a symbol type."""
        ty = self._symbol_type(sym, '')
        if ty.startswith('*'):
            return 'null'
        elif ty == 'Token':
            return 'p_current_token(p)'
        return '0'

    def _is_nullable_rule(self, rule_name: str) -> bool:
        """Check if a rule can match empty (has an epsilon/empty alternative)."""
        if rule_name not in self.rule_map:
            return False
        rule = self.rule_map[rule_name]
        for alt in rule.alternatives:
            if len(alt.symbols) == 0:
                return True
        return False

    def _generate_parse_function(self, rule: GrammarRule):
        """Generate a parse_<name>() function for one grammar rule."""
        rt = self._get_return_type(rule)
        default_ret = self._get_default_return(rule)

        vis = 'pub ' if rule.name in PUBLIC_RULES else ''
        self._emit(f'{vis}fn parse_{rule.name}(p: *Parser) -> {rt}')
        # AGAST #1819: a call made after an earlier symbol in the sequence has
        # already failed must do nothing -- not consume, not record, not build.
        # The caller used to arrange that with `if p.error == 0` around every
        # symbol; one guard here replaces all of them.
        self._emit('    if p.error != 0')
        self._emit(f'        return {default_ret}')
        self._emit(f'    let start_pos: i32 = p.pos')

        for alt_idx, alt in enumerate(rule.alternatives):
            if alt_idx > 0:
                # Reset for next alternative
                self._emit('    p_rewind(p, start_pos)')

            self._generate_alternative(rule, alt, alt_idx, default_ret)

        # AGAST #1819: every failed alternative used to restore p.pos as it
        # went; now the restore happens just before the next alternative, so
        # the last one needs it here.  Only p.pos: p.error stays set, which is
        # what the caller (and the recovery block below) must see.
        if len(rule.alternatives) > 1:
            self._emit('    p.pos = start_pos')

        # Recovery directive: when all alternatives failed and we're not
        # at EOF, skip forward to the next "anchor" token from the rule's
        # recovery set, clear the error, and return.  For i32-returning
        # rules (typical: `item`) we return 1 to signal "progress made"
        # so the enclosing star/plus loop in the caller continues.
        # For other return types we return the default (null / 0).
        recovery_tokens = self.grammar.recovery.get(rule.name)
        if recovery_tokens:
            recovery_ret = '1' if rt == 'i32' else default_ret
            self._emit('')
            self._emit('    # Recovery: report the failure, skip to the next anchor token,')
            self._emit('    # then report progress so the enclosing loop keeps going.')
            self._emit('    # parser_report_dropped_item records the drop; the rule that')
            self._emit('    # closes the enclosing loop turns it into a hard parse error, so')
            self._emit('    # skipped input can never yield a silently partial parse tree.')
            self._emit('    if p.pos < p.token_count and p_peek(p) != TOK_EOF')
            self._emit('        parser_report_dropped_item(p)')
            self._emit('        p.pos = p.pos + 1')
            self._emit('        while p.pos < p.token_count')
            self._emit('            let t: Token = p_current_token(p)')
            for tok in recovery_tokens:
                self._emit(f'            if t.kind == TOK_{tok}')
                self._emit('                break')
            self._emit('            p.pos = p.pos + 1')
            self._emit('        p.error = 0')
            self._emit(f'        return {recovery_ret}')

        # Final return.  The old `if p.error == 0 / return X / return X` pair
        # returned the same value on both paths (AGAST #1819).
        self._emit(f'    return {default_ret}')

    def _generate_alternative(self, rule: GrammarRule, alt: GrammarAlt,
                              alt_idx: int, default_ret: str):
        """Generate code for one alternative of a grammar rule.

        Follows the exact pattern from ritz1_archive/src/parser_gen.ritz:

        For a single-alt rule like fn_def (FN IDENT generic_params? ...):
            result_1 = p_current_token(p)
            if p_expect(p, TOK_FN) == 0
                p.error = 1
            if p.error == 0
                result_2 = p_current_token(p)
                if p_expect(p, TOK_IDENT) == 0
                    p.error = 1
            result_3 = null
            if p.error == 0
                result_3 = parse_generic_params(p)  # optional
                p.error = 0
            ...
            if p.error == 0
                return <action>

        For a multi-alt rule like params:
            result_a1_1 = parse_param(p)
            if p.error != 0
                p.pos = start_pos
            if p.error == 0
                result_a1_2 = p_current_token(p)
                if p_expect(p, TOK_COMMA) == 0
                    p.error = 1
                    p.pos = start_pos
            ...
        """
        is_multi_alt = len(rule.alternatives) > 1

        # Determine if this is a void-action rule (like item)
        is_void_action_rule = (
            alt.action and
            rule.return_type is None and
            self._action_is_void_call(alt.action)
        )

        # Variable prefix: multi-alt uses result_aN_ to avoid redeclaration
        prefix = f'result_a{alt_idx+1}_' if is_multi_alt else 'result_'

        symbols = alt.symbols

        # AGAST #1819: capture only what the action reads.  A token capture
        # is a 40-byte Token copy and two emitted lines; 69% of them used to
        # be dead.  `$N` in the action is the only way a symbol is read, so
        # anything else is parsed for its side effects and discarded.
        used = {int(n) for n in re.findall(r'\$(\d+)', alt.action or '')}
        if (alt.action is None and len(symbols) == 1
                and symbols[0].kind == SymbolKind.NONTERMINAL):
            used.add(1)  # the pass-through `return result_1` reads it

        def is_used(i):
            return (i + 1) in used

        # AGAST #1819: a flat sequence, not a nest of `if p.error == 0`
        # blocks.  p_expect is a no-op once p.error is set and every parse
        # function returns at entry, so a failed symbol leaves the rest of
        # the sequence inert.  That removes 3-4 emitted lines per symbol and
        # makes the consumed prefix and recorded failure identical.
        for i, sym in enumerate(symbols):
            var_name = f'{prefix}{i+1}'
            read = is_used(i)

            if sym.kind == SymbolKind.TERMINAL:
                if read:
                    self._emit(f'    let {var_name}: Token = p_take(p, TOK_{sym.name})')
                else:
                    self._emit(f'    p_expect(p, TOK_{sym.name})')

            elif sym.kind == SymbolKind.NONTERMINAL:
                call = f'parse_{sym.name}(p)'
                if read:
                    var_type = self._symbol_type(sym, rule.name)
                    self._emit(f'    let {var_name}: {var_type} = {call}')
                else:
                    self._emit(f'    {call}')

            elif sym.kind == SymbolKind.OPTIONAL:
                sym_type = self._symbol_type(sym, rule.name)
                if read:
                    self._emit(f'    var {var_name}: {sym_type} = '
                               f'{self._symbol_default(sym)}')
                if sym.name.isupper():
                    # Optional terminal — peek-based.  Guarded so an earlier
                    # failure is not turned into a successful optional.
                    if read:
                        self._emit(f'    if p.error == 0 and p_peek(p) == TOK_{sym.name}')
                        self._emit(f'        {var_name} = p_current_token(p)')
                        self._emit(f'        p_advance(p)')
                    else:
                        self._emit(f'    if p.error == 0 and p_peek(p) == TOK_{sym.name}')
                        self._emit(f'        p_advance(p)')
                else:
                    # Optional nonterminal — parse and reset error
                    self._emit(f'    if p.error == 0')
                    if read:
                        self._emit(f'        {var_name} = parse_{sym.name}(p)  # optional')
                    else:
                        self._emit(f'        parse_{sym.name}(p)  # optional')
                    self._emit(f'        p.error = 0')

            elif sym.kind == SymbolKind.STAR:
                # Zero or more.  `p.error == 0` in the condition keeps a
                # failed alternative from consuming anything here.
                if sym.name.isupper():
                    self._emit(f'    while p.error == 0 and p_peek(p) == TOK_{sym.name}')
                    self._emit(f'        p_advance(p)')
                else:
                    self._emit(f'    while p.error == 0')
                    # AGAST #1819: a dropped-item diagnostic is about the item
                    # that just failed, not about a deeper speculative failure
                    # left behind by one that parsed.
                    if sym.name in self.grammar.recovery:
                        self._emit(f'        p_clear_fail(p)')
                    self._emit(f'        if parse_{sym.name}(p) == 0')
                    self._emit(f'            p.error = 0')
                    self._emit(f'            break')

        # Handle action
        if alt.action:
            action_code = self._translate_action(alt.action, prefix, symbols)

            if is_void_action_rule:
                # Void action (e.g., module_add_fn) — side effect only
                self._emit(f'    if p.error == 0')
                self._emit(f'        {action_code}')
                # For item-like rules, check progress.  `p.error == 0` is
                # part of the test because a failed alternative no longer
                # rewinds before this point (AGAST #1819); without it a
                # callee that consumed before failing would look like
                # progress and the item would vanish.
                if is_multi_alt:
                    self._emit(f'    if p.error == 0 and p.pos > start_pos')
                    self._emit(f'        return 1')
            else:
                # Return-type action
                self._emit(f'    if p.error == 0')
                self._emit(f'        return {action_code}')
        elif len(symbols) == 1 and symbols[0].kind == SymbolKind.NONTERMINAL:
            # Single nonterminal, pass-through (e.g., stmt -> let_stmt)
            var_name = f'{prefix}1'
            self._emit(f'    if p.error == 0')
            self._emit(f'        return {var_name}')

    def _action_is_void_call(self, action: str) -> bool:
        """Check if action is a void function call (e.g. module_add_fn(...))."""
        action = action.strip()
        void_prefixes = ['module_add_']
        for pfx in void_prefixes:
            if action.startswith(pfx):
                return True
        return False

    def _translate_action(self, action: str, prefix: str, symbols: List[GrammarSymbol]) -> str:
        """Translate a semantic action from grammar syntax to Ritz code.

        $N references become result_N (or result_aN_N for multi-alt)
        $N.start, $N.len etc. become result_N.start, result_N.len
        p.module stays as-is
        null → null
        0 as *Type → 0 as *Type (stays as-is)
        """
        result = action.strip()

        # Replace $N.field references first (before bare $N)
        def replace_dollar_field(m):
            n = int(m.group(1))
            field = m.group(2)
            return f'{prefix}{n}.{field}'

        result = re.sub(r'\$(\d+)\.(\w+(?:\.\w+)*)', replace_dollar_field, result)

        # Replace bare $N references
        def replace_dollar(m):
            n = int(m.group(1))
            return f'{prefix}{n}'

        result = re.sub(r'\$(\d+)', replace_dollar, result)

        # Clean up: 0 as *Foo → null
        result = result.replace('0 as *StructField', 'null')
        result = result.replace('0 as *Stmt', 'null')
        result = result.replace('0 as *Expr', 'null')
        result = result.replace('0 as *ImportPath', 'null')
        result = result.replace('0 as *BinaryOp', 'null')
        result = result.replace('0 as *CastTail', 'null')
        result = result.replace('0 as *PostfixOp', 'null')
        result = result.replace('0 as *FieldInit', 'null')
        result = result.replace('0 as *FnDef', 'null')
        result = result.replace('0 as *u8', 'null')

        return result

    # =========================================================================
    # AST helpers generation
    # =========================================================================

    # =========================================================================
    # Lexer scanner generation (AGAST #1821)
    # =========================================================================
    #
    # ritz1 used to rebuild a regex NFA from these token definitions for every
    # file it lexed (557 KB of stack each) and simulate it by recursive
    # backtracking.  Now the generator does the work once: the literal tokens
    # become two direct-coded functions, and the regex tokens are checked
    # against the hand-written scanners in lexer.ritz that implement them.

    def _scanner_tokens(self):
        """Split the grammar's lexable tokens into (keywords, operators).

        Each is a list of (text, token name) in grammar order.  A literal is a
        keyword if it is shaped like an identifier (scan_ident looks it up),
        else an operator (lexer_operator matches it).  Raises ValueError for
        a token the scanner could never produce, rather than generating a
        lexer that silently never returns it.
        """
        keywords, operators = [], []
        for tok in self.grammar.tokens:
            if tok.name in SCANNER_SKIP_TOKENS:
                continue
            if HAND_WRITTEN_TOKEN_IDS.get(tok.name) is None or not tok.pattern:
                continue
            if not tok.is_literal:
                want = SCANNED_REGEX_TOKENS.get(tok.name)
                if want != tok.pattern:
                    raise ValueError(
                        f"token {tok.name} = /{tok.pattern}/: ritz1's scanner has no "
                        f"code for this pattern (it implements {sorted(SCANNED_REGEX_TOKENS)} "
                        "as written in SCANNED_REGEX_TOKENS). Change the scan_* function "
                        "in ritz1/src/lexer.ritz and SCANNED_REGEX_TOKENS together."
                    )
                continue
            text = tok.pattern
            if re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*', text):
                keywords.append((text, tok.name))
            elif text[0] in SCANNER_DISPATCHED_CHARS or text[0].isalnum() or text[0] == '_' \
                    or not all(33 <= ord(c) <= 126 for c in text):
                raise ValueError(
                    f"token {tok.name} = \"{text}\": an operator must be printable ASCII "
                    "punctuation, and must not start with a byte ritz1's lexer dispatches "
                    f"before matching operators ({SCANNER_DISPATCHED_CHARS!r})"
                )
            else:
                operators.append((text, tok.name))
        return keywords, operators

    def _emit_operator_node(self, node, depth: int, indent: str):
        """Emit the longest-match test for one operator trie node.

        The node's children are tried first, each nested `if` returning
        only on a full operator, so a child that leads nowhere falls through
        to this node's own token: the longest operator wins.
        """
        for ch in sorted(node['next']):
            child = node['next'][ch]
            if depth == 0:
                test = f'c0 == {ord(ch)}'
            else:
                test = f'avail > {depth} and lexer_byte(p, {depth}) == {ord(ch)}'
            self._emit(f'{indent}if {test}  # {child["text"]}')
            self._emit_operator_node(child, depth + 1, indent + '    ')
        if node['tok'] is not None:
            self._emit(f'{indent}*out_len = {depth}')
            self._emit(f'{indent}return TOK_{node["tok"]}')

    def generate_lexer_scan(self) -> str:
        """Generate lexer_scan_gen.ritz: keyword lookup and operator matcher."""
        keywords, operators = self._scanner_tokens()
        self._reset()
        self._emit('# Generated by ritzgen - Lexer scanner (AGAST #1821)')
        self._emit('#')
        self._emit('# This is auto-generated code. Do not edit.')
        self._emit('#')
        self._emit("# The grammar's literal tokens, direct-coded.  Its regex tokens (IDENT,")
        self._emit('# NUMBER, FLOAT, STRING, CHAR, CSTRING, WHITESPACE, COMMENT) are')
        self._emit("# scanned by hand in lexer.ritz; the generator refuses a grammar")
        self._emit('# whose patterns differ from the ones those functions implement.')
        self._emit('')
        self._emit('import tokens_gen')
        self._emit('')
        self._emit('# Byte k of p, 0-255.')
        self._emit('fn lexer_byte(p: *u8, k: i64) -> i32')
        self._emit('    ((*(p + k)) as i32) & 255')
        self._emit('')
        self._emit('# 1 if the n bytes at p are those of the NUL-terminated `word`.')
        self._emit('fn lexer_same(p: *u8, word: *u8, n: i64) -> i32')
        self._emit('    var k: i64 = 1')
        self._emit('    while k < n')
        self._emit('        if *(p + k) != *(word + k)')
        self._emit('            return 0')
        self._emit('        k = k + 1')
        self._emit('    1')
        self._emit('')
        # Keywords: by length, then first byte, then the rest.
        self._emit('# The keyword spelled by the identifier p[0..n), or TOK_IDENT.  A keyword')
        self._emit('# and an identifier of the same text are the same length, and the')
        self._emit('# keyword wins: `fn` is TOK_FN, `fnx` an identifier.')
        self._emit('pub fn lexer_keyword(p: *u8, n: i64) -> i32')
        self._emit('    let c0: i32 = lexer_byte(p, 0)')
        by_len: dict[int, list[tuple[str, str]]] = {}
        for text, name in keywords:
            by_len.setdefault(len(text), []).append((text, name))
        for n in sorted(by_len):
            self._emit(f'    if n == {n}')
            for text, name in sorted(by_len[n]):
                if n == 1:
                    self._emit(f'        if c0 == {ord(text[0])}')
                else:
                    self._emit(f'        if c0 == {ord(text[0])} and lexer_same(p, c"{text}", {n}) == 1')
                self._emit(f'            return TOK_{name}')
            self._emit('        return TOK_IDENT')
        self._emit('    TOK_IDENT')
        self._emit('')
        # Operators: a trie, longest match.
        root = {'next': {}, 'tok': None, 'text': ''}
        for text, name in operators:
            node = root
            for ch in text:
                node = node['next'].setdefault(ch, {'next': {}, 'tok': None, 'text': node['text'] + ch})
            if node['tok'] is not None:
                raise ValueError(f'tokens {node["tok"]} and {name} are both "{text}"')
            node['tok'] = name
        self._emit('# The longest operator at p, of the `avail` bytes left: its kind, with its')
        self._emit('# length in *out_len; -1 if none starts there.')
        self._emit('pub fn lexer_operator(p: *u8, avail: i64, out_len: *i32) -> i32')
        self._emit('    *out_len = 0')
        self._emit('    if avail <= 0')
        self._emit('        return -1')
        self._emit('    let c0: i32 = lexer_byte(p, 0)')
        self._emit_operator_node(root, 0, '    ')
        self._emit('    -1')
        return self._get_output()


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Generate Ritz source from grammar')
    parser.add_argument('grammar_file', help='Path to .grammar file')
    parser.add_argument('--output-dir', default='.',
                        help='Output directory for generated files')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--monolithic', action='store_true',
                        help='Generate the single parser.ritz ritz1 consumes '
                             '(kept so existing callers spell the mode)')

    args = parser.parse_args()

    grammar = parse_grammar_file(args.grammar_file)

    # A grammar token with no entry in HAND_WRITTEN_TOKEN_IDS used to be
    # dropped from tokens.ritz and lexer_setup_gen.ritz without a word, while
    # parser.ritz still referenced TOK_<NAME>: the lexer never produced it and
    # the build failed far from the cause (hit adding TYPE for AGAST #1475).
    unmapped = unmapped_tokens(grammar)
    if unmapped:
        print(f"error: grammar token(s) with no ID in HAND_WRITTEN_TOKEN_IDS: "
              f"{', '.join(unmapped)}. Add them to tools/ritzgen_py/ritz_generator.py.",
              file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"Loaded {len(grammar.tokens)} tokens, {len(grammar.rules)} rules",
              file=sys.stderr)

    gen = RitzGenerator(grammar)

    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    # Generate tokens.ritz
    tokens_code = gen.generate_tokens()
    tokens_path = os.path.join(output_dir, 'tokens.ritz')
    with open(tokens_path, 'w') as f:
        f.write(tokens_code + '\n')
    print(f"Generated {tokens_path}")

    # Generate parser files.  The monolithic single file is the only shape
    # ritz1 consumes; the modular split and the ast_helpers stub were dead
    # paths and were deleted (AGAST #1819).
    parser_code = gen.generate_parser()
    parser_path = os.path.join(output_dir, 'parser.ritz')
    with open(parser_path, 'w') as f:
        f.write(parser_code + '\n')
    print(f"Generated {parser_path}")

    # Generate lexer_scan_gen.ritz
    lexer_code = gen.generate_lexer_scan()
    lexer_path = os.path.join(output_dir, 'lexer_scan_gen.ritz')
    with open(lexer_path, 'w') as f:
        f.write(lexer_code + '\n')
    print(f"Generated {lexer_path}")


if __name__ == '__main__':
    main()
