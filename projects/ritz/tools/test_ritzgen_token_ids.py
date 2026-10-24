"""The ritz1 generator must refuse a grammar token it has no token ID for.

Before AGAST #1475 a token missing from HAND_WRITTEN_TOKEN_IDS was dropped
from tokens.ritz and lexer_setup_gen.ritz without a word, while parser.ritz
still referenced TOK_<NAME>. Adding `TYPE = "type"` to the grammar hit
exactly that: regen "succeeded" and the build then failed far from the
cause.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RITZ_ROOT = Path(__file__).resolve().parent.parent
GEN = RITZ_ROOT / "tools" / "ritzgen_py" / "ritz_generator.py"
GRAMMAR = RITZ_ROOT / "grammars" / "ritz1.grammar"

sys.path.insert(0, str(GEN.parent.parent))

from ritzgen_py.grammar_parser import parse_grammar_file  # noqa: E402
from ritzgen_py.ritz_generator import unmapped_tokens  # noqa: E402


def test_ritz1_grammar_has_an_id_for_every_token():
    assert unmapped_tokens(parse_grammar_file(str(GRAMMAR))) == []


def test_generator_fails_on_a_token_with_no_id(tmp_path):
    grammar = GRAMMAR.read_text().replace(
        'TYPE        = "type"\n', 'TYPE        = "type"\nBOGUSKW     = "bogus"\n', 1
    )
    assert "BOGUSKW" in grammar
    g = tmp_path / "g.grammar"
    g.write_text(grammar)
    out = tmp_path / "out"
    proc = subprocess.run(
        [sys.executable, str(GEN), str(g), "--monolithic", "--output-dir", str(out)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode != 0
    assert "BOGUSKW" in proc.stderr
    assert not (out / "parser.ritz").exists()


def test_tokens_ritz_defines_every_grammar_token():
    """AGAST #1530: generate_tokens grouped IDs by hardcoded ranges and
    silently dropped any outside them (DOTDOTEQ = 103 fell past 95-102), so
    tokens.ritz lacked TOK_DOTDOTEQ while the parser and lexer used it."""
    from ritzgen_py.ritz_generator import RitzGenerator

    grammar = parse_grammar_file(str(GRAMMAR))
    tokens = RitzGenerator(grammar).generate_tokens()
    missing = [t.name for t in grammar.tokens if f"const TOK_{t.name}: i32 =" not in tokens]
    assert missing == []


def test_generate_tokens_fails_on_an_ungrouped_id(monkeypatch):
    import pytest

    from ritzgen_py import ritz_generator

    ids = dict(ritz_generator.HAND_WRITTEN_TOKEN_IDS, DOTDOTEQ=200)
    monkeypatch.setattr(ritz_generator, "HAND_WRITTEN_TOKEN_IDS", ids)
    gen = ritz_generator.RitzGenerator(parse_grammar_file(str(GRAMMAR)))
    with pytest.raises(ValueError, match="DOTDOTEQ"):
        gen.generate_tokens()
