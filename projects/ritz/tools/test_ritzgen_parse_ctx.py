"""The parser's per-compile state is a ParseCtx the Parser carries (AGAST #4623).

ast_helpers.ritz kept 86 module globals of parse state (attribute bits, the
`let` latch, the trait / enum / tuple registries, ...).  Every grammar action
already receives `p: *Parser`, so the generated parser_init takes the compile's
one `ctx: *ParseCtx` and stores it in `p.ctx`; an action reaches the state
through `p.ctx`, and a helper without a Parser takes `ctx` as a parameter.
One ParseCtx outlives every Parser of a compile (each imported file gets its
own Parser), which is why it is a struct of its own rather than Parser fields.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
GRAMMAR = RITZ_ROOT / "grammars" / "ritz1.grammar"
SRC = RITZ_ROOT / "ritz1" / "src"
sys.path.insert(0, str(RITZ_ROOT / "tools"))

from ritzgen_py.grammar_parser import parse_grammar_file
from ritzgen_py.ritz_generator import RitzGenerator

pytestmark = pytest.mark.unit


def _parser_init() -> str:
    gen = RitzGenerator(parse_grammar_file(str(GRAMMAR))).generate_parser()
    i = gen.index("pub fn parser_init(")
    end = gen.find("\n\n", i)
    return gen[i:end]


def _struct(path: Path, name: str) -> str:
    text = path.read_text()
    m = re.search(rf"^(pub )?struct {name}\n((?:[ \t].*\n|\n)*?)(?=\S)", text, re.M)
    assert m, f"struct {name} not found in {path.name}"
    return m.group(2)


def test_parser_init_takes_the_parse_ctx():
    fn = _parser_init()
    assert fn.splitlines()[0] == (
        "pub fn parser_init(p: *Parser, ctx: *ParseCtx, tokens: *Token, "
        "count: i32, arena_ptr: *u8)"
    )
    assert "    p.ctx = ctx" in fn


def test_parser_carries_the_parse_ctx():
    assert re.search(r"^\s+ctx: \*ParseCtx\b", _struct(SRC / "ast.ritz", "Parser"), re.M)


def test_parse_ctx_is_one_struct_in_ast():
    # ast.ritz declares it beside Parser, so Parser's field resolves without
    # ast importing ast_helpers.
    assert "struct ParseCtx" in (SRC / "ast.ritz").read_text()
    assert "struct ParseCtx" not in (SRC / "ast_helpers.ritz").read_text()


@pytest.mark.parametrize(
    "owner,field",
    [
        ("sema.ritz", "Sema"),
        ("monomorph.ritz", "MonoCtx"),
    ],
)
def test_passes_hold_the_parse_ctx(owner, field):
    # Sema and monomorph read the parse-time registries (enum_find,
    # tuple_reg_lookup, ...) through their own state, not a global; the
    # emitter through s.mono (EmitterState's field count is frozen, #1816).
    assert re.search(r"^\s+pctx: \*ParseCtx\b", _struct(SRC / owner, field), re.M)
