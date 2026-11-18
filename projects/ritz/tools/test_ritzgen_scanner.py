"""ritzgen's direct-coded scanner for ritz1 (AGAST #1821).

ritz1 used to rebuild a regex NFA from the grammar's token definitions for
every file it lexed. Now the generator emits lexer_scan_gen.ritz once: a
keyword lookup and an operator matcher for the literal tokens, while the
regex tokens are scanned by hand in ritz1/src/lexer.ritz. These tests pin
the contract between the two: every literal token is emitted, and a grammar
the hand-written scanner does not implement is refused, never generated into
a lexer that silently lexes something else.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
GRAMMAR = RITZ_ROOT / "grammars" / "ritz1.grammar"

sys.path.insert(0, str(RITZ_ROOT / "tools"))

from ritzgen_py.grammar_parser import parse_grammar_file
from ritzgen_py.ritz_generator import SCANNER_SKIP_TOKENS, RitzGenerator


def _scan_source(tmp_path: Path, grammar_text: str) -> str:
    g = tmp_path / "g.grammar"
    g.write_text(grammar_text)
    return RitzGenerator(parse_grammar_file(str(g))).generate_lexer_scan()


def _edit(old: str, new: str) -> str:
    text = GRAMMAR.read_text()
    assert old in text, f"grammar no longer contains {old!r}"
    return text.replace(old, new, 1)


def test_every_literal_token_is_emitted(tmp_path):
    """Each keyword and operator of the grammar is a `return TOK_<NAME>` in the
    scanner: one missing would never be lexed.  NEWLINE and the like are made
    by the lexer itself."""
    grammar = parse_grammar_file(str(GRAMMAR))
    src = RitzGenerator(grammar).generate_lexer_scan()
    returned = set(re.findall(r"return TOK_(\w+)", src))
    literals = {
        t.name for t in grammar.tokens if t.is_literal and t.pattern
    } - SCANNER_SKIP_TOKENS
    assert literals and literals <= returned, sorted(literals - returned)


def test_keyword_lookup_compares_the_whole_word(tmp_path):
    """`lexer_keyword` checks length first, so `fn` never matches `fnord`."""
    src = _scan_source(tmp_path, GRAMMAR.read_text())
    assert re.search(
        r'    if n == 2\n(?:.*\n)*?        if c0 == 102 and lexer_same\(p, c"fn", 2\) == 1\n'
        r"            return TOK_FN",
        src,
    )


def test_operator_matcher_tries_longer_operators_first(tmp_path):
    """`..=` is tried inside `..`, inside `.`: the longest match wins."""
    src = _scan_source(tmp_path, GRAMMAR.read_text())
    dot = src.index("    if c0 == 46  # .\n")
    dotdot = src.index("# ..\n", dot)
    dotdoteq = src.index("# ..=\n", dotdot)
    assert dot < dotdot < dotdoteq < src.index("return TOK_DOTDOT\n", dot)


def test_a_changed_regex_token_is_refused(tmp_path):
    """IDENT is scanned by hand; a grammar widening it must fail loudly."""
    text = _edit(
        "IDENT      = /[a-zA-Z_][a-zA-Z0-9_]*/",
        "IDENT      = /[a-zA-Z_$][a-zA-Z0-9_$]*/",
    )
    with pytest.raises(ValueError, match="IDENT"):
        _scan_source(tmp_path, text)


def test_an_operator_the_lexer_dispatches_away_from_is_refused(tmp_path):
    """`#` starts a comment before any operator is tried, so `#!` could never
    be lexed."""
    text = _edit('QUESTION    = "?"\n', 'QUESTION    = "#!"\n')
    with pytest.raises(ValueError, match="QUESTION"):
        _scan_source(tmp_path, text)
