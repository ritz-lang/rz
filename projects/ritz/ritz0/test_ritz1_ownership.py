"""ritz1's move check and drop insertion beyond the shared table (AGAST #2158).

test_ownership_free_count.py is the cross-compiler table for LANGUAGE_SPEC
§13.  This file covers the parts of ritz1/src/ownership.ritz that table does
not reach: drop flags for a binding moved on some paths only, the `if` merge
of the move check, assignment reviving a moved binding, a declaration with
no value, `for` loops, match-arm blocks, by-value method arguments, nested
drop glue, and a tail-expression move.

The use-after-move rejections also run through ritz0 and must report the
same diagnostic at the same location (goal 3: ritz1 rejects what ritz0
rejects, in ritz0's words).
"""

import re

import pytest

from test_ownership_free_count import PRELUDE, _compile, RITZ_START

RITZ1S = ("ritz1", "ritz1_selfhosted")

# name -> (program body, expected exit status).
CASES = {
    # Moved on one path only: the drop flag drops it on the other, once.
    "conditional_move": ("""\
fn f(x: i32)
    var t = make(1)
    if x > 0
        consume(t)

pub fn main() -> i32
    f(1)
    f(0)
    return DROPS
""", 2),

    # A move in an arm that returns doesn't count after the `if`.
    "move_in_returning_arm": ("""\
fn f(x: i32) -> i32
    var t = make(1)
    if x > 0
        return consume(t)
    return t.id

pub fn main() -> i32
    f(1)
    f(0)
    return DROPS
""", 2),

    # Assigning to a moved binding drops nothing and makes it an owner.
    "reassign_after_move": ("""\
fn f() -> i32
    var t = make(1)
    consume(t)
    t = make(2)
    return t.id * 10 + DROPS

pub fn main() -> i32
    let r = f()
    return r + DROPS * 100
""", 221),

    # `var t: T` holds no value: the first assignment drops nothing.
    "uninit_decl": ("""\
fn f() -> i32
    var t: Tracked
    t = make(5)
    return DROPS

pub fn main() -> i32
    let a = f()
    return a * 10 + DROPS
""", 1),

    # Iterations 0 and 1: one at the body's end, one on `break` -- both
    # before the loop is left, not at f's `return` (which would give 12).
    "for_break": ("""\
fn f() -> i32
    for i in 0..5
        var t = make(1)
        if i == 1
            break
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 22),

    # Moved every iteration: consume drops each one, the loop none.
    "move_in_loop": ("""\
fn f()
    var i = 0
    while i < 3
        var t = make(1)
        consume(t)
        i = i + 1

pub fn main() -> i32
    f()
    return DROPS
""", 3),

    # A match arm is a block: its binding drops after the arm's value.
    "match_arm_block": ("""\
fn f(x: i32) -> i32
    let v = match x
        1 =>
            var t = make(1)
            DROPS + 5
        _ => 0
    return v * 10 + DROPS

pub fn main() -> i32
    return f(1)
""", 51),

    # A by-value method argument moves into the method.
    "method_arg_move": ("""\
struct Sink
    n: i32

impl Sink
    fn take(self: @&Sink, t: Tracked) -> i32
        return t.id

fn f() -> i32
    var s = Sink { n: 0 }
    var t = make(3)
    s.take(t)
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 11),

    # Own drop first, then the fields in declaration order: 9, 1, 2.
    "nested_glue_order": ("""\
struct Pair
    a: Tracked
    b: Tracked

impl Drop for Pair
    fn drop(self: @&Pair)
        ORDER = ORDER * 10 + 9

fn f()
    var p = Pair { a: make(1), b: make(2) }

pub fn main() -> i32
    f()
    return ORDER - 900
""", 12),

    # A tail expression moves its binding out, like `return t`.
    "tail_move_out": ("""\
fn build() -> Tracked
    var t = make(1)
    t

fn f() -> i32
    var u = build()
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 1),
}

# name -> program body.  Each is rejected by ritz0 and ritz1 alike.
REJECTS = {
    # Moved in both arms (neither returns): moved after the `if`.
    "moved_in_both_arms": """\
pub fn main() -> i32
    var t = make(1)
    if DROPS == 0
        consume(t)
    else
        var u = t
    return t.id
""",

    # Moved in the then-arm of an `if` with no else: moved after it.
    "moved_in_then_arm": """\
pub fn main() -> i32
    var t = make(1)
    if DROPS == 0
        consume(t)
    return t.id
""",

    "borrow_after_move": """\
fn peek(t: @Tracked) -> i32
    return t.id

pub fn main() -> i32
    var t = make(1)
    consume(t)
    return peek(@t)
""",

    "moved_twice_in_one_call": """\
fn both(a: Tracked, b: Tracked) -> i32
    return a.id + b.id

pub fn main() -> i32
    var t = make(1)
    return both(t, t)
""",
}

# `F:L:C: <message>` from either compiler's ownership diagnostic.
DIAG = re.compile(r"(\S+:\d+:\d+): (?:error: )?((?:use of moved value|cannot borrow)\b.*)")


def _run(compiler, tmp_path, body):
    src = tmp_path / "main.ritz"
    src.write_text(PRELUDE + body)
    ll = tmp_path / "main.ll"
    return src, ll, _compile(compiler, src, ll, tmp_path)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_drop_count(request, tmp_path, compiler, name):
    import subprocess
    request.getfixturevalue("ritz1_bin")
    body, expected = CASES[name]
    _, ll, comp = _run(compiler, tmp_path, body)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = tmp_path / "main"
    link = subprocess.run(["clang", str(RITZ_START), str(ll), "-o", str(exe), "-nostdlib"],
                          cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-2000:]}"
    rc = subprocess.run([str(exe)], capture_output=True, timeout=60).returncode
    assert rc == expected, f"{compiler} {name}: exit {rc}, spec says {expected}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(REJECTS))
def test_ritz1_rejects_like_ritz0(request, tmp_path, compiler, name):
    request.getfixturevalue("ritz1_bin")
    body = REJECTS[name]
    _, _, ref = _run("ritz0", tmp_path, body)
    want = DIAG.findall(ref.stdout + ref.stderr)
    assert ref.returncode != 0 and want, f"ritz0 accepted {name}:\n{ref.stderr[-1000:]}"
    _, _, comp = _run(compiler, tmp_path, body)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted {name}:\n{out[-1000:]}"
    assert DIAG.findall(out) == want, out[-2000:]
