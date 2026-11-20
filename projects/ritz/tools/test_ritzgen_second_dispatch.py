"""Second-token (LL(2)) dispatch in the generated parser (AGAST #4378).

#4374 guards every alternative by the FIRST set of the terminal it can begin
with.  That cannot separate alternatives that share a first token: 7 of
primary_expr's alternatives start with IDENT, 4 of postfix_op's with LT.  Each
still runs in turn, and each re-parses the shared prefix before failing.

The generator now also compares the token after the first one (`la2`) where
the grammar determines it, so an alternative whose second token cannot match
is skipped.  The skip must record what the skipped alternative would have
expected: not its FIRST set at start_pos (that is only right when the first
token misses too), but its SECOND set at start_pos + 1.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RITZ_ROOT / "tools"))

from ritzgen_py.grammar_parser import parse_grammar_file
from ritzgen_py.ritz_generator import HAND_WRITTEN_TOKEN_IDS, RitzGenerator

pytestmark = pytest.mark.unit


def _parser(tmp_path: Path, rules: str) -> str:
    """Generate parser source for a grammar whose rules are `rules`."""
    g = tmp_path / "g.grammar"
    g.write_text("%grammar\n" + rules)
    return RitzGenerator(parse_grammar_file(str(g))).generate_parser()


def _fn(src: str, rule: str) -> str:
    """The generated parse_<rule> function, from its signature to the next one."""
    head = f"fn parse_{rule}("
    i = src.index(head)
    j = src.find("\nfn ", i + 1)
    return src[i : j if j != -1 else len(src)]


def _bits(names: tuple[str, ...]) -> str:
    b = [0, 0, 0]
    for name in names:
        tid = HAND_WRITTEN_TOKEN_IDS[name]
        b[tid // 64] |= 1 << (tid % 64)
    return f"{b[0]} as u64, {b[1]} as u64, {b[2]} as u64"


def test_helpers_exist(tmp_path):
    """p_peek2 reads the token after the lookahead; p_record_second records at +1.

    p_record_second walks the failure position exactly as the flat parser
    would have: it consumes the first terminal, fails at the second, and
    restores p.pos afterwards.
    """
    src = _parser(
        tmp_path,
        """
op -> i32
    : IDENT PLUS { 1 }
    | IDENT MINUS { 2 }
    ;
""",
    )
    assert "fn p_peek2(p: *Parser) -> i32" in src
    assert "let i: i32 = p.pos + 1" in src
    head = src.index("fn p_record_second(")
    body = src[head : src.index("\n\n", head)]
    assert "p.pos = p.pos + 1" in body, body
    # The flat parser consumed the first terminal before failing at the
    # second, so p.max_pos (the dropped-item report's position) advanced too.
    assert "if p.pos > p.max_pos" in body, body
    assert "p.max_pos = p.pos" in body, body
    assert "p_record_first(p, b0, b1, b2)" in body, body
    assert "p.pos = save" in body, body


def test_colliding_first_sets_compare_the_second_token(tmp_path):
    """Two IDENT alternatives are separated by the token after the IDENT."""
    fn = _fn(
        _parser(
            tmp_path,
            """
op -> i32
    : IDENT PLUS { 1 }
    | IDENT MINUS { 2 }
    | NUMBER { 3 }
    ;
""",
        ),
        "op",
    )
    assert "let la2: i32 = p_peek2(p)" in fn, fn
    assert "if la == TOK_IDENT and la2 == TOK_PLUS" in fn, fn
    assert "if la == TOK_IDENT and la2 == TOK_MINUS" in fn, fn
    # NUMBER is a unique FIRST set, so LL(1) already separates it: no la2.
    assert "if la == TOK_NUMBER\n" in fn, fn


def test_skip_records_second_at_the_next_position(tmp_path):
    """A first-token match with a second-token miss records the SECOND set.

    The flat parser would have consumed the first terminal and failed at the
    second, so the located "expected one of: ..." is raised one position past
    start_pos.  Recording the FIRST set (or the second set at start_pos) would
    move or change the diagnostic.
    """
    fn = _fn(
        _parser(
            tmp_path,
            """
op -> i32
    : IDENT PLUS { 1 }
    | IDENT MINUS { 2 }
    ;
""",
        ),
        "op",
    )
    # The miss path branches on the first token: first miss -> FIRST at start,
    # second miss -> SECOND one past start.
    assert f"if la == TOK_IDENT\n            p_record_second(p, {_bits(('PLUS',))})" in fn, fn
    assert f"if la == TOK_IDENT\n            p_record_second(p, {_bits(('MINUS',))})" in fn, fn
    assert f"p_record_first(p, {_bits(('IDENT',))})" in fn, fn


def test_nullable_second_token_falls_back_to_the_first_guard(tmp_path):
    """When the alternative can end (or match empty) after its first token,
    the second token is unconstrained: keep the LL(1) guard."""
    fn = _fn(
        _parser(
            tmp_path,
            """
one -> i32
    : IDENT opt { 1 }
    | IDENT PLUS { 2 }
    ;
opt -> i32
    : NUMBER { 0 }
    | { 0 }
    ;
""",
        ),
        "one",
    )
    assert "la2 == TOK_PLUS" in fn, fn
    assert "la2 == TOK_NUMBER" not in fn, fn
    # The nullable-tail alternative is still skipped on a FIRST miss only.
    assert "if la == TOK_IDENT\n" in fn, fn


def test_multi_token_second_set_uses_the_bitset(tmp_path):
    fn = _fn(
        _parser(
            tmp_path,
            """
outer2 -> i32
    : IDENT inner { 1 }
    | IDENT PLUS { 2 }
    ;
inner -> i32
    : LPAREN { 0 }
    | LBRACKET { 0 }
    ;
""",
        ),
        "outer2",
    )
    assert (
        f"if la == TOK_IDENT and p_first_has(la2, {_bits(('LPAREN', 'LBRACKET'))}) != 0"
        in fn
    ), fn


def test_unique_first_set_gets_no_second_check(tmp_path):
    """LL(2) is only worth emitting where FIRST sets collide."""
    fn = _fn(
        _parser(
            tmp_path,
            """
one2 -> i32
    : LPAREN args2 RPAREN { 1 }
    | NUMBER { 2 }
    ;
args2 -> i32
    : IDENT { 0 }
    ;
""",
        ),
        "one2",
    )
    assert "la2 ==" not in fn, fn
    assert "let la2" not in fn, fn


def test_fallible_nullable_prefix_gets_no_second_check(tmp_path):
    """A leading nonterminal may fail or consume before the first terminal.

    `closure_ahead` is zero-width but fails when the `|` follows a type, so
    the flat parser would *not* consume the `|` before failing; recording a
    second-token miss one position on would move the diagnostic past it
    (measured: `fn f() -> i64 | bool` reported `unexpected 'bool'` at 1:17
    instead of the `A | B` refusal at the `|`).
    """
    fn = _fn(
        _parser(
            tmp_path,
            """
closure_ahead -> i32
    : { 0 }
    ;
pipe_two -> i32
    : closure_ahead PIPE PIPE { 1 }
    | closure_ahead PIPE IDENT { 2 }
    ;
""",
        ),
        "pipe_two",
    )
    assert "la2" not in fn, fn
    assert fn.count("if la == TOK_PIPE\n") == 2, fn


def test_assign_stmt_drops_the_assign_pos_wrapper():
    """The zero-width assign_pos call is replaced by the rule's own start_pos.

    assign_pos(p) returns p.pos, and both lvalue alternatives begin at the
    assign_stmt's start, so the wrapper call buys nothing; stmt_assign_lvalue
    is handed start_pos directly.  This is the left-factoring half of #4378:
    one fewer parse call on every assignment attempt.
    """
    gen = RitzGenerator(parse_grammar_file(str(RITZ_ROOT / "grammars" / "ritz1.grammar")))
    src = gen.generate_parser()
    fn = _fn(src, "assign_stmt")
    assert "parse_assign_pos(" not in fn, fn
    assert "stmt_assign_lvalue(p, start_pos, " in fn, fn
    assert "fn parse_assign_pos(" not in src
