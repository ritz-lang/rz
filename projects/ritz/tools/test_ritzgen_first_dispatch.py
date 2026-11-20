"""FIRST-set dispatch in the generated parser (AGAST #4374).

#1819's flat alternatives parse in turn and rewind, so a rule with N
alternatives costs up to N failed attempts per decision.  The generator now
guards each alternative with the FIRST set of the tokens it can begin with,
so a failed attempt is skipped from the lookahead.

These tests pin the shape of that emission.  The one that matters most is
`test_no_alternative_matched_fails_the_rule`: an all-guarded rule reaches the
end of its function only after every alternative failed, and it must leave
p.error set.  When it did not, parse_postfix_ops (whose every alternative is
guarded) returned "success, no tokens consumed"; its caller recursed until
the stack died.
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


def test_no_alternative_matched_fails_the_rule(tmp_path):
    """An all-guarded rule whose last guard misses must still fail.

    The last alternative's guard failing leaves nothing between it and the
    end of the function except the rewind that cleared p.error.  Returning
    success there made parse_postfix_ops recurse forever (AGAST #4374).
    """
    fn = _fn(
        _parser(
            tmp_path,
            """
op -> i32
    : IDENT PLUS { 1 }
    | NUMBER PLUS { 2 }
    ;
""",
        ),
        "op",
    )
    tail = fn[fn.index("p.pos = start_pos") :]
    assert "p.error = 1" in tail, fn
    # The miss records what trying every alternative would have expected.
    assert f"p_record_first(p, {_bits(('IDENT', 'NUMBER'))})" in tail, fn
    # ... unconditionally: a `matched` flag tracked tries, not successes.
    assert "if matched" not in fn


def test_skipped_alternative_records_its_first_set(tmp_path):
    """A guard miss must still contribute to `expected one of: ...`.

    Trying the alternative in the flat parser failed at its first terminal and
    recorded it.  Skipping it from the lookahead skips that p_expect, so the
    generator must record the FIRST set itself.  Measured before this: the
    archived ritz1_old tokens.ritz reported `expected dedent` where the flat
    parser said `expected one of: dedent, self, identifier`.
    """
    fn = _fn(
        _parser(
            tmp_path,
            """
one -> i32
    : IDENT { 1 }
    | NUMBER { 2 }
    ;
""",
        ),
        "one",
    )
    assert f"else\n        p_record_first(p, {_bits(('IDENT',))})" in fn, fn
    assert f"else\n        p_record_first(p, {_bits(('NUMBER',))})" in fn, fn


def test_record_first_ors_the_bits_instead_of_walking_kinds(tmp_path):
    """The skip path is the hot one; recording must not cost 192 lookups.

    p_record_first used to loop k in 0..192 calling p_record_fail, which
    undid the point of skipping.  It now ORs the 3x u64 words directly under
    p_record_fail's own furthest-position rule (AGAST #1819).
    """
    src = _parser(
        tmp_path,
        """
op -> i32
    : IDENT PLUS { 1 }
    | NUMBER PLUS { 2 }
    ;
""",
    )
    head = src.index("fn p_record_first(")
    body = src[head : src.index("\n\n", head)]
    assert "while" not in body, body
    assert "p.fail_b0 = p.fail_b0 | b0" in body, body
    assert "if p.pos < p.fail_pos" in body, body


def test_single_token_first_set_compares_the_lookahead_directly(tmp_path):
    fn = _fn(
        _parser(
            tmp_path,
            """
one -> i32
    : IDENT { 1 }
    | NUMBER { 2 }
    ;
""",
        ),
        "one",
    )
    assert "if la == TOK_IDENT" in fn
    assert "if la == TOK_NUMBER" in fn
    assert "p_first_has(la," not in fn


def test_multi_token_first_set_uses_the_bitset(tmp_path):
    """`inner` can start with either token, so the guard is a set test."""
    fn = _fn(
        _parser(
            tmp_path,
            """
outer -> i32
    : inner PLUS { 1 }
    | LPAREN RPAREN { 2 }
    ;
inner -> i32
    : IDENT { 1 }
    | NUMBER { 2 }
    ;
""",
        ),
        "outer",
    )
    assert f"p_first_has(la, {_bits(('IDENT', 'NUMBER'))})" in fn
    assert "if la == TOK_LPAREN" in fn


def test_nullable_alternative_is_never_guarded(tmp_path):
    """The empty alternative must always run: it is a legitimate success."""
    fn = _fn(
        _parser(
            tmp_path,
            """
opt -> i32
    : IDENT PLUS { 1 }
    | { 2 }
    ;
""",
        ),
        "opt",
    )
    assert fn.count("if la ==") == 1
    # No synthesized miss at the end: the unguarded alternative always runs.
    tail = fn[fn.rindex("p_rewind(p, start_pos)") :]
    assert "p_record_first" not in tail
    assert "p.error = 1" not in tail
    # The empty alternative returns its action without a lookahead test.
    assert "return 2" in tail


def test_opaque_nullable_prefix_is_not_dispatchable(tmp_path):
    """A nullable rule's own action may run on a miss, so it stays unguarded.

    `zap` is nullable and not one of the transparent prefixes: its action
    runs even when the token after it does not match, so the alternative
    cannot be skipped from the lookahead.  `assign_pos` is transparent and
    is dispatched like its tail.
    """
    src = _parser(
        tmp_path,
        """
zap -> i32
    : { 0 }
    ;
pq -> i32
    : zap IDENT { 1 }
    | NUMBER { 2 }
    ;
ag -> i32
    : assign_pos IDENT { 1 }
    | NUMBER { 2 }
    ;
assign_pos -> i32
    : { 0 }
    ;
""",
    )
    pq = _fn(src, "pq")
    assert pq.index("parse_zap(p)") < pq.index("if la =="), pq
    assert pq.count("if la ==") == 1, pq
    ag = _fn(src, "ag")
    assert ag.index("if la ==") < ag.index("parse_assign_pos(p)"), ag
