"""The generated token_new must keep the token's source pointer (AGAST #3888).

It took `pos: i64`, dropped it, and set `start: null`, so only tokens that
went through lexer.ritz's lexer_token (which patched `start` afterwards) said
where they were; INDENT, DEDENT, EOF and lexer_fail's errors kept null.
token_new now takes the pointer itself.  ritz1/test/test_lexer.ritz
checks the lexer's tokens; this checks the generator emits that shape.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
GRAMMAR = RITZ_ROOT / "grammars" / "ritz1.grammar"
sys.path.insert(0, str(RITZ_ROOT / "tools"))

from ritzgen_py.grammar_parser import parse_grammar_file
from ritzgen_py.ritz_generator import RitzGenerator

pytestmark = pytest.mark.unit


def _token_new() -> str:
    tokens = RitzGenerator(parse_grammar_file(str(GRAMMAR))).generate_tokens()
    head = "pub fn token_new("
    i = tokens.index(head)
    end = tokens.find("\n\n", i)
    return tokens[i : end if end != -1 else len(tokens)]


def test_token_new_takes_the_source_pointer():
    fn = _token_new()
    sig = fn.splitlines()[0]
    # AGAST #4449: the (pointer, len) parameter pair is a StrView, so the
    # generated signature no longer carries a raw `*u8, len: i32` pair.
    # AGAST #4773: Token's own `start` + `len` fields are one `text: StrView`,
    # so the view is stored whole, not split back into a pointer and a length.
    assert (
        sig
        == "pub fn token_new(kind: i32, text: StrView, line: i64, col: i64) -> Token"
    )
    assert "        text: text," in fn
    assert "start" not in fn
    assert "pos" not in fn


def test_token_text_is_one_strview():
    # AGAST #4773: no `*u8` + `i32` text pair left on Token.
    tokens = RitzGenerator(parse_grammar_file(str(GRAMMAR))).generate_tokens()
    i = tokens.index("struct Token\n")
    struct = tokens[i : tokens.find("\n\n", i)]
    assert "    text: StrView" in struct
    assert "    string_val: StrView" in struct
    assert "*u8" not in struct
    assert "_len" not in struct
