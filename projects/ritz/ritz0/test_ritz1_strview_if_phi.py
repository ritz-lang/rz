"""AGAST #2563: a tail `if` whose arms are string literals, in a `-> StrView`
fn, joins them with a `%StrView` phi.

THE DEFECT

    fn name(k: i32) -> StrView
        if k == 0
            "ab"
        else if k == 1
            "abc"
        else
            "abcd"

A bare `"..."` lowers to `%Span$u8` (#98).  #2559 typed a tail (statement)
`if`'s phi from its arms, so this one became `phi %"Span$u8"`, and the
implicit `ret %StrView` rejected it.  ritz0 compiles and runs it.

THE FIX

The statement-`if` (STMT_IF) arms follow the if-expression / match rule
(emit_match_arm_body, #1662): an arm whose value is the layout-equivalent
other half of the Span$u8 / StrView
pair is rebuilt with rebuild_layout_equiv in its own block, before its `br`.
The phi takes the fn's return type when that is StrView or Span$u8 (a tail
`if` feeds the implicit `ret`), else the then arm's type.

Matrix: arms (all literals; literal first, then the StrView param last;
the param first, then literals) x 2- / 3-arm chain x position (tail,
`let v = if`, `return if`), in a `-> StrView` fn.  ritz0 is the oracle.

Measured on the base (6af7496a): ritz1 broke on all 6 TAIL chains
(`-was_broken` ids), the ticket's program, and a non-tail statement `if`
over a literal and a StrView param (test_non_tail_mixed_arms).  The `let v = if` and `return if` forms are
if-expressions, which #1662 already typed StrView, and were fine.

Control: a `-> Span<u8>` fn whose arms are Span<u8> params keeps its
`%Span$u8` phi (tail / let / return, 2- / 3-arm) -- already fine, and the
StrView rule must not retype it.  A `"..."` arm in a `-> Span<u8>` fn is no
control: a literal is a StrView, and ritz0 itself emits IR clang rejects for
`fn f() -> Span<u8>` / `"ab"` (`ret {i8*, i64}`).
"""

import itertools

import pytest

from test_ritz1_builtin_struct_shadow import _run

# Arm i is a literal of length i + 2 ("ab", "abc", "abcd") or the param `p`
# (length 7).
LITS = ['"ab"', '"abc"', '"abcd"']

# Which arms are the param, per mix and chain length.
MIXES = {
    "all_lit": lambda n: set(),
    "lit_first": lambda n: {n - 1},  # literal leads, param last
    "lit_last": lambda n: {0},  # param leads, literal last
}

CHAINS = {"two_arm": 2, "three_arm": 3}
POSITIONS = ("tail", "let", "return")


def _arms(mix: str, n: int) -> list:
    params = MIXES[mix](n)
    return ["p" if i in params else LITS[i] for i in range(n)]


def _chain(n: int, arms: list, head: str) -> str:
    pad = "    "
    out = f"{pad}{head}if k == 0\n{pad}    {arms[0]}\n"
    if n == 3:
        out += f"{pad}else if k == 1\n{pad}    {arms[1]}\n"
    out += f"{pad}else\n{pad}    {arms[n - 1]}\n"
    return out


def _body(position: str, n: int, arms: list) -> str:
    if position == "tail":
        return _chain(n, arms, "")
    if position == "let":
        return _chain(n, arms, "let v = ") + "    v\n"
    return _chain(n, arms, "return ")


def _program(mix: str, chain: str, position: str) -> str:
    n = CHAINS[chain]
    return (
        "fn name(k: i32, p: StrView) -> StrView\n"
        + _body(position, n, _arms(mix, n))
        + """
pub fn main() -> i32
    let p: StrView = "ppppppp"
    let a = name(0, p)
    let b = name(1, p)
    let c = name(2, p)
    let first: u8 = *a.ptr
    var ok: i32 = 0
    if first == 112 or first == 97
        ok = 100
    return ok + (a.len as i32) + (b.len as i32) * 2 + (c.len as i32) * 8
"""
    )


def _len(arm: str) -> int:
    return 7 if arm == "p" else len(arm) - 2


def _expected(mix: str, chain: str) -> int:
    n = CHAINS[chain]
    arms = _arms(mix, n)
    picks = [arms[0], arms[1], arms[2]] if n == 3 else [arms[0], arms[1], arms[1]]
    return 100 + _len(picks[0]) + _len(picks[1]) * 2 + _len(picks[2]) * 8


MATRIX = [
    pytest.param(
        mix,
        chain,
        pos,
        id=f"{mix}-{chain}-{pos}" + ("-was_broken" if pos == "tail" else ""),
    )
    for mix, chain, pos in itertools.product(MIXES, CHAINS, POSITIONS)
]


@pytest.mark.integration
@pytest.mark.parametrize("mix,chain,position", MATRIX)
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_strview_if_chain(tmp_path, compiler, mix, chain, position):
    name = f"svp_{mix}_{chain}_{position}"
    program = _program(mix, chain, position)
    assert _run(compiler, tmp_path, name, program) == _expected(mix, chain)


def _span_program(chain: str, position: str) -> str:
    n = CHAINS[chain]
    return (
        "import ritzlib.span\n"
        "fn name(k: i32, a: Span<u8>, b: Span<u8>, c: Span<u8>) -> Span<u8>\n"
        + _body(position, n, ["a", "b", "c"][:n] if n == 3 else ["a", "c"])
        + """
pub fn main() -> i32
    let a = Span<u8> { ptr: c"ab", len: 2 }
    let b = Span<u8> { ptr: c"abc", len: 3 }
    let c = Span<u8> { ptr: c"abcd", len: 4 }
    let r0 = name(0, a, b, c)
    let r1 = name(1, a, b, c)
    let r2 = name(2, a, b, c)
    return (r0.len as i32) + (r1.len as i32) * 2 + (r2.len as i32) * 8
"""
    )


@pytest.mark.integration
@pytest.mark.parametrize("position", POSITIONS)
@pytest.mark.parametrize("chain", CHAINS)
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_span_control(tmp_path, compiler, chain, position):
    """A `-> Span<u8>` chain of Span<u8> params keeps its %Span$u8 phi."""
    name = f"svp_span_{chain}_{position}"
    expected = 2 + 3 * 2 + 4 * 8 if chain == "three_arm" else 2 + 4 * 2 + 4 * 8
    assert _run(compiler, tmp_path, name, _span_program(chain, position)) == expected


# The ticket's program, verbatim.
TICKET = """\
fn name(k: i32) -> StrView
    if k == 0
        "ab"
    else if k == 1
        "abc"
    else
        "abcd"
pub fn main() -> i32
    let a = name(0)
    let b = name(1)
    let c = name(2)
    return (a.len + b.len * 10 + c.len * 100) as i32 - 200
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_ticket(tmp_path, compiler):
    assert _run(compiler, tmp_path, "svp_ticket", TICKET) == 2 + 30 + 400 - 200


# A non-tail statement `if` over a literal and a StrView param, in a `-> i32`
# fn: its value is unused, but ritz1 still joins it with a phi, so the arms
# must agree.  The return type does not pick the type here; the else arm
# takes the then arm's (%Span$u8 for a literal, %StrView for the param).
NON_TAIL = """\
fn f(k: i32, p: StrView) -> i32
    if k == 0
        "ab"
    else
        p
    if k == 0
        p
    else
        "ab"
    k + 1
pub fn main() -> i32
    let p: StrView = "ppppppp"
    return f(0, p) + f(1, p) * 10
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_non_tail_mixed_arms(tmp_path, compiler):
    assert _run(compiler, tmp_path, "svp_non_tail", NON_TAIL) == 21
