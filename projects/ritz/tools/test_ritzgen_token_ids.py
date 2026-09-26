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
