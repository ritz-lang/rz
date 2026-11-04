"""ritz1's move check and drop insertion beyond the shared table (AGAST #2158).

test_ownership_free_count.py is the cross-compiler table for LANGUAGE_SPEC
§13.  This file covers the parts of ritz1/src/ownership.ritz that table does
not reach: drop flags for a binding moved on some paths only, the `if` merge
of the move check, assignment reviving a moved binding, a declaration with
no value, `for` loops, match-arm blocks, by-value method arguments, nested
drop glue, and a tail-expression move; (AGAST #2165) array and enum drop
glue, temporaries, and moves of an outer binding inside a loop; and (AGAST
#2168) moves out of a field and the merge of match / if-expression arms.

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

    # AGAST #2165 from here on.  An array field's elements drop with the
    # struct, in index order.
    "array_field": ("""\
struct Bag
    n: i32
    ts: [2]Tracked

fn f()
    var b = Bag { n: 0, ts: [make(1), make(2)] }

pub fn main() -> i32
    f()
    return ORDER
""", 12),

    # Reassigning an array drops the old elements: 2 then, 2 more at the end.
    "array_reassign": ("""\
fn f() -> i32
    var a: [2]Tracked = [make(1), make(2)]
    a = [make(3), make(4)]
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 24),

    # A moved array is dropped by its new owner only.
    "array_moved": ("""\
fn f()
    var a: [2]Tracked = [make(1), make(2)]
    var b = a

pub fn main() -> i32
    f()
    return DROPS
""", 2),

    # An enum field drops its payload with the struct.
    "enum_in_struct": ("""\
enum Slot
    Full(Tracked)
    Empty

struct Box2
    s: Slot
    n: i32

fn f()
    var b = Box2 { s: Slot.Full(make(7)), n: 1 }

pub fn main() -> i32
    f()
    return ORDER
""", 7),

    # A moved enum drops once, in its new owner.
    "enum_moved": ("""\
enum Slot
    Full(Tracked)
    Empty

fn f()
    var s = Slot.Full(make(1))
    var u = s

pub fn main() -> i32
    f()
    return DROPS
""", 1),

    # Result drops its Err payload too.
    "result_err_payload": ("""\
import ritzlib.result

fn f(ok: i32)
    var r: Result<i32, Tracked> = Ok(1)
    if ok == 0
        r = Err(make(3))

pub fn main() -> i32
    f(1)
    f(0)
    return ORDER
""", 3),

    # A temporary whose field is read drops at the end of the statement.
    "temporary_member": ("""\
fn f() -> i32
    let n = make(4).id
    return DROPS * 10 + n

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 15),

    # Passed by value, a call result moves into the callee: no temporary.
    "temporary_moved_into_callee": ("""\
fn f() -> i32
    consume(make(1))
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 11),

    # A condition's temporary drops once the condition is evaluated, before
    # the arm runs (ritz0 #2161).
    "temporary_in_if_cond": ("""\
fn peek(t: @Tracked) -> i32
    return t.id

fn f() -> i32
    var r = 0
    if peek(make(1)) == 1
        r = DROPS
    return r * 10 + DROPS

pub fn main() -> i32
    return f()
""", 11),

    # ...on every evaluation of a `while` condition: ids 0, 1, 2 and 3.
    "temporary_in_while_cond": ("""\
fn peek(t: @Tracked) -> i32
    return t.id

fn f() -> i32
    var i = 0
    while peek(make(i)) < 3
        i = i + 1
    return DROPS

pub fn main() -> i32
    return f()
""", 4),

    # A move inside a loop that leaves by `return` is fine.
    "loop_move_then_return": ("""\
fn f() -> i32
    var t = make(1)
    while true
        return consume(t)
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1),

    # Moved and reassigned on every path round a `for` loop.
    "for_loop_move_reassigned": ("""\
fn f()
    var t = make(0)
    for i in 0..3
        consume(t)
        t = make(1)

pub fn main() -> i32
    f()
    return DROPS
""", 4),

    # AGAST #2168's field-move drop counts are in test_ownership_free_count.py
    # (shared with ritz0 since AGAST #2171).

    # Match arms start from the state before the match (ritz0 #2161): t
    # moved in arm 1 is still usable in arm 2.  f(1) drops it in consume,
    # f(0) at the scope end.
    "match_arm_moves_independent": ("""\
fn f(x: i32) -> i32
    var t = make(1)
    let v = match x
        1 => consume(t)
        _ => t.id
    return v

pub fn main() -> i32
    f(1)
    f(0)
    return DROPS
""", 2),

    # The same for a match statement with block arms.
    "match_stmt_arm_moves_independent": ("""\
fn f(x: i32)
    var t = make(1)
    match x
        1 =>
            consume(t)
        _ =>
            var u = t

pub fn main() -> i32
    f(1)
    f(0)
    return DROPS
""", 2),

    # An if-expression's else-arm starts from the state before the `if`
    # too: f(1) drops t in consume, f(0) at the scope end.
    "if_expr_arm_moves_independent": ("""\
fn f(x: i32) -> i32
    var t = make(1)
    let v: i32 = if x > 0
        consume(t)
    else
        t.id
    return v

pub fn main() -> i32
    f(1)
    f(0)
    return DROPS
""", 2),

    # An arm that returns takes its move with it.
    "match_arm_returns_move": ("""\
fn f(x: i32) -> i32
    var t = make(1)
    match x
        1 =>
            return consume(t)
        _ =>
            pass
    return t.id

pub fn main() -> i32
    f(1)
    f(0)
    return DROPS
""", 2),
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

    # AGAST #2165: the second iteration reaches the move with t moved.
    "move_outer_in_loop": """\
pub fn main() -> i32
    var t = make(1)
    var i = 0
    while i < 2
        consume(t)
        i = i + 1
    return 0
""",

    "move_in_for_loop": """\
pub fn main() -> i32
    var t = make(1)
    for i in 0..2
        var n = i
        consume(t)
    return 0
""",

    # Moved on one branch only, never reassigned: still moved at the head.
    "move_in_loop_branch": """\
pub fn main() -> i32
    var t = make(1)
    var i = 0
    while i < 3
        i = i + 1
        if i == 2
            consume(t)
    return 0
""",

    # Used (not moved) before the move: the error is at the first use.
    "use_before_move_in_loop": """\
pub fn main() -> i32
    var t = make(1)
    var i = 0
    while i < 2
        i = i + t.id
        consume(t)
    return 0
""",

    # An inner loop's move of a binding outer to both loops.
    "move_in_nested_loop": """\
pub fn main() -> i32
    var t = make(1)
    var i = 0
    while i < 2
        i = i + 1
        var j = 0
        while j < 1
            j = j + 1
        consume(t)
    return 0
""",

    "move_in_loop_continue": """\
pub fn main() -> i32
    var t = make(1)
    var i = 0
    while i < 2
        i = i + 1
        if i == 1
            consume(t)
            continue
        t = make(2)
    return 0
""",

    # The else-arm's assignment doesn't revive t on the then-arm's path.
    "move_in_loop_else_assigns": """\
pub fn main() -> i32
    var t = make(1)
    var i = 0
    while i < 2
        i = i + 1
        if i == 1
            i = i + 0
        else
            t = make(2)
        consume(t)
    return 0
""",

    # An assignment on a path that returns doesn't count after the `if`.
    "move_in_loop_arm_returns": """\
pub fn main() -> i32
    var t = make(1)
    var i = 0
    while i < 2
        i = i + 1
        if i == 5
            t = make(2)
            return 0
        consume(t)
    return 0
""",

    # A use inside an inner loop is checked against the outer loop's head.
    "use_in_inner_loop": """\
pub fn main() -> i32
    var t = make(1)
    var i = 0
    while i < 2
        i = i + 1
        var j = 0
        while j < 1
            j = j + t.id
        consume(t)
    return 0
""",

    # The loop may not run: moved before it, moved after it.
    "moved_before_loop_reassigned_in_it": """\
pub fn main() -> i32
    var t = make(1)
    consume(t)
    var i = 0
    while i < 1
        i = i + 1
        t = make(2)
    return t.id
""",

    "borrow_in_loop": """\
fn peek(t: @Tracked) -> i32
    return t.id

pub fn main() -> i32
    var t = make(1)
    var i = 0
    while i < 2
        i = i + peek(@t)
        consume(t)
    return 0
""",

    # AGAST #2168 from here on: match arms merge like `if` arms (ritz0
    # #2161).  Moved in an arm that falls through: moved after the match.
    "moved_in_match_arm": """\
pub fn main() -> i32
    var t = make(1)
    match DROPS
        0 =>
            consume(t)
        _ =>
            pass
    return t.id
""",

    "moved_in_match_expr_arm": """\
pub fn main() -> i32
    var t = make(1)
    let v = match DROPS
        0 => consume(t)
        _ => 0
    return t.id + v
""",

    # Arm 1 re-assigns t, arm 2 moves it: an iteration through arm 2 reaches
    # the head with t moved, so the next one's arm 2 uses a moved value.
    # The loop's shadow state must flow through the match merge.
    "move_in_loop_match_arm": """\
pub fn main() -> i32
    var t = make(1)
    var i = 0
    while i < 3
        i = i + 1
        match i
            1 =>
                t = make(2)
            _ =>
                consume(t)
    return 0
""",
}

# AGAST #2168: moves out of a field, ritz0's since AGAST #2171.  Every
# compiler must report exactly this: name -> (program body, message).
FIELD_REJECTS = {
    "field_used_after_move": ("""\
pub fn main() -> i32
    var h = Holder { t: make(1), n: 2 }
    var u = h.t
    return h.t.id
""", "main.ritz:35:12: error: use of moved value: `h.t` (moved at main.ritz:34:13)"),

    "whole_after_field_move": ("""\
pub fn main() -> i32
    var h = Holder { t: make(1), n: 2 }
    consume(h.t)
    var g = h
    return 0
""", "main.ritz:35:13: error: use of moved value: `h.t` (moved at main.ritz:34:13)"),

    "borrow_after_field_move": ("""\
fn peek(h: @Holder) -> i32
    return h.n

pub fn main() -> i32
    var h = Holder { t: make(1), n: 2 }
    consume(h.t)
    return peek(@h)
""", "main.ritz:38:17: error: cannot borrow `h` - `h.t` has been moved"),

    "field_move_in_loop": ("""\
pub fn main() -> i32
    var h = Holder { t: make(1), n: 2 }
    var i = 0
    while i < 2
        consume(h.t)
        i = i + 1
    return 0
""", "main.ritz:36:17: error: use of moved value: `h.t` (moved at main.ritz:36:17)"),

    # A `continue` reaches the head with h.t moved.
    "field_move_in_loop_continue": ("""\
pub fn main() -> i32
    var h = Holder { t: make(1), n: 2 }
    var i = 0
    while i < 2
        i = i + 1
        if i == 1
            consume(h.t)
            continue
        h.t = make(2)
    return 0
""", "main.ritz:38:21: error: use of moved value: `h.t` (moved at main.ritz:38:21)"),

    # Re-assigned before its second move, h.t is owned there: only the
    # first move (reached with h.t moved by the previous iteration) errs.
    "field_move_in_loop_after_reassign": ("""\
pub fn main() -> i32
    var h = Holder { t: make(1), n: 2 }
    var i = 0
    while i < 2
        consume(h.t)
        h.t = make(2)
        consume(h.t)
        i = i + 1
    return 0
""", "main.ritz:36:17: error: use of moved value: `h.t` (moved at main.ritz:38:17)"),

    "field_moved_in_match_arm": ("""\
pub fn main() -> i32
    var h = Holder { t: make(1), n: 2 }
    match DROPS
        0 =>
            consume(h.t)
        _ =>
            pass
    return h.t.id
""", "main.ritz:39:12: error: use of moved value: `h.t` (moved at main.ritz:36:21)"),

    # AGAST #2171: moved in the `then` branch, so moved after the `if`.
    "field_moved_in_if": ("""\
pub fn main() -> i32
    var h = Holder { t: make(1), n: 2 }
    if DROPS == 0
        consume(h.t)
    return h.t.id
""", "main.ritz:36:12: error: use of moved value: `h.t` (moved at main.ritz:35:17)"),

    # ...and with an `else` that doesn't move it.
    "field_moved_in_if_else": ("""\
pub fn main() -> i32
    var h = Holder { t: make(1), n: 2 }
    if DROPS == 0
        consume(h.t)
    else
        h.n = 3
    return h.t.id
""", "main.ritz:38:12: error: use of moved value: `h.t` (moved at main.ritz:35:17)"),

    # Moving a field out of a type with its own drop would leave that drop
    # a half-moved value (as in Rust, E0509).
    "field_move_from_drop_type": ("""\
struct Pair
    a: Tracked
    n: i32

impl Drop for Pair
    fn drop(self: @&Pair)
        ORDER = 9

pub fn main() -> i32
    var p = Pair { a: make(1), n: 0 }
    consume(p.a)
    return 0
""", "main.ritz:42:13: error: cannot move out of `p.a`: `Pair` implements Drop"),
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


# `F:L:C: [error: ]<message>` from either compiler, its file names the
# temp path's (ritz0 prints `Ownership error: F:L:C: <message>`).
FIELD_DIAG = re.compile(r"(\S*main\.ritz:\d+:\d+): (?:error: )?"
                        r"((?:use of moved value|cannot borrow|cannot move out)\b.*)")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ("ritz0",) + RITZ1S)
@pytest.mark.parametrize("name", sorted(FIELD_REJECTS))
def test_rejects_field_move(request, tmp_path, compiler, name):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    body, want = FIELD_REJECTS[name]
    _, _, comp = _run(compiler, tmp_path, body)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted {name}:\n{out[-1000:]}"
    assert "Traceback" not in out, out[-2000:]
    # Exactly this diagnostic, once.
    got = [re.sub(r"\S*main\.ritz", "main.ritz", f"{loc}: error: {msg}")
           for loc, msg in FIELD_DIAG.findall(out)]
    assert got == [want], out[-2000:]
