"""AGAST #3507: ritz1's move check runs on Sema, not the emitter (#1816).

THE CHANGE

LANGUAGE_SPEC §13: using a move-only binding by value moves it, and a later
use is a located error; a value behind a reference, in an array element or in
a global can't be moved out; a deferred statement is checked at each exit it
runs on.  ritz1 ran all of it in ownership.ritz as the emitter lowered each
statement (own_check_stmt / own_check_tail / own_check_arm, the
own_begin_fn / own_pop_scope move state, and own_check_lent_read /
own_check_lent_value_stmt where a `:&` param's referent was read).  Now
own_check.ritz runs it from Sema's walk, with the same flow (if / arm merges,
loop shadows, deferred statements replayed at every exit, match ownership),
and the emitter keeps only drop insertion.  Which bindings own a move-only
value reaches the emitter as FnDef.own_binds, which gives exactly those a drop
flag.

ritz0's twin is move_checker.py; the rules' own tests (test_move_checker.py,
test_ritz1_ownership.py, test_ownership_free_count.py,
test_defer_all_compilers.py, test_move_out_through_index.py, ...) hold all
three compilers to them.

THE TESTS

- A move error now stops the compile before emission: an error only the
  emitter reports, after it, is no longer printed.  Red on the base.
- REACH: one row per kind of binding or read the emitter typed from its
  LocalVar and Sema types otherwise (an enum constructor's `let`, a payload
  through a pointer, a nameless tuple and its fields, `c?`, a `:&` param read
  by value, `*@self`, `*a`, a deferred statement at the fn's end, an element
  of a Span).  Each is refused at the same place, in the same words.
- OPEN: what moves nothing stays accepted: a `*T` element of a Vec, a `:&`
  param as a discarded arm's value.
- The emitter tracks nothing and reports nothing: ownership.ritz keeps no move
  state, and its drop flags follow Sema's annotation.
"""

import re
from pathlib import Path

import pytest

from test_ref_into_value import _compile

RITZ_ROOT = Path(__file__).resolve().parent.parent
SRC = RITZ_ROOT / "ritz1" / "src"
COMPILERS = ["ritz1", "ritz1_selfhosted"]

STOPS_BEFORE_EMIT = """\
struct T
    id: i32

impl Drop for T
    fn drop(self: @&T)
        let x: i32 = self.id

fn eat(t: T) -> i32
    t.id

fn main() -> i32
    let t = T { id: 1 }
    eat(t)
    eat(t)
    var q: i32 = 3
    for x in q
        q = 2
    0
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_move_error_stops_the_compile_before_emission(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_own", STOPS_BEFORE_EMIT)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    assert found == [("14:9", "use of moved value: `t` (moved at {}:13:9)".format(_path(out)))], \
        f"{compiler}:\n{out}"
    assert "for` iterable" not in out, f"{compiler} went on to emit:\n{out}"


def _path(out):
    """The file the "moved at" location names (the compiled main.ritz)."""
    m = re.search(r"(\S*main\.ritz):\d+:\d+: ", out)
    return m.group(1) if m else "main.ritz"


_PRELUDE = """\
import ritzlib.span
import ritzlib.gvec
import ritzlib.result

var DROPS: i32 = 0

struct Tracked
    id: i32

impl Drop for Tracked
    fn drop(self: @&Tracked)
        DROPS = DROPS + 1

impl Tracked
    fn burn(self: Tracked) -> i32
        self.id

struct H
    t: Tracked
    n: i32

enum Slot
    Full(Tracked)
    Empty

fn make(i: i32) -> Tracked
    Tracked { id: i }

fn consume(t: Tracked) -> i32
    t.id

fn look(t: @Tracked) -> i32
    t.id

fn note(d: i32) -> i32
    0

fn try_make(i: i32) -> Result<Tracked, i32>
    Ok(make(i))

impl Tracked
    fn try_new(i: i32) -> Result<Tracked, i32>
        Ok(make(i))

fn eat_slot(s: Slot) -> i32
    0

"""

# name -> (the row's fns, then each error as (line in the row, col, words)).
# "{at:L:C}" in the words is the row's line L, column C.
REACH = {
    # `var s = E.V(x)`: Sema's scope types the user enum the image can't.
    "enum_constructor_let": (
        "fn r_enum() -> i32\n    var s = Slot.Full(make(1))\n    match s\n        Full(t) =>\n"
        "            let k = consume(t) + consume(t)\n        Empty =>\n            let z = 0\n    0\n",
        [(5, 42, "use of moved value: `t` (moved at {at:5:29})")]),
    # `var s = E.V`, a unit variant, is the enum too (AGAST #4251).
    "enum_unit_variant_let": (
        "fn r_enum_unit() -> i32\n    var s = Slot.Empty\n    return eat_slot(s) + eat_slot(s)\n",
        [(3, 35, "use of moved value: `s` (moved at {at:3:21})")]),
    # `match *p` owns nothing: its payload is lent (AGAST #2178).
    "payload_through_a_pointer": (
        "fn r_lent_payload(p: *Slot) -> i32\n    match *p\n        Full(t) => return consume(t)\n"
        "        Empty => return 0\n",
        [(3, 35, "cannot move out of a reference")]),
    # A nameless tuple's field, copied out and moved twice (AGAST #3005).
    "tuple_field_copy": (
        "fn r_tuple_copy() -> i32\n    var p = (make(1), 2)\n    var x = p.0\n"
        "    return consume(x) + consume(x)\n",
        [(4, 33, "use of moved value: `x` (moved at {at:4:20})")]),
    "tuple_field_twice": (
        "fn r_tuple_twice() -> i32\n    var p = (make(1), 2)\n    return consume(p.0) + consume(p.0)\n",
        [(3, 35, "use of moved value: `p.0` (moved at {at:3:20})")]),
    # `let (a, b) = p` moves p (AGAST #3033).
    "tuple_destructure": (
        "fn r_tuple_let() -> i32\n    var p = (make(1), 2)\n    let (a, b) = p\n    return look(@p.0)\n",
        [(4, 18, "use of moved value: `p` (moved at {at:3:18})")]),
    # `c?` of a Result carrying a move-only struct (AGAST #3974).
    "try_binding": (
        "fn r_try() -> Result<i32, i32>\n    var t = try_make(1)?\n"
        "    let k = consume(t) + consume(t)\n    return Ok(k)\n",
        [(3, 34, "use of moved value: `t` (moved at {at:3:21})")]),
    # `T.f()?` of a static method (AGAST #4251).
    "try_static_method": (
        "fn r_try_static() -> Result<i32, i32>\n    var t = Tracked.try_new(1)?\n"
        "    let k = consume(t) + consume(t)\n    return Ok(k)\n",
        [(3, 34, "use of moved value: `t` (moved at {at:3:21})")]),
    # A `:&` param read by value (AGAST #2250): a `let`, a return.
    "lent_param_let": (
        "fn r_lent_let(t:& Tracked) -> i32\n    var x = t\n    0\n",
        [(2, 13, "cannot move out of a reference")]),
    "lent_param_return": (
        "fn r_lent_ret(t:& Tracked) -> Tracked\n    return t\n",
        [(2, 12, "cannot move out of a reference")]),
    # `*@self` reads it too (AGAST #2286), and `*a` a `a:& [N]T` (#2290).
    "lent_self_deref": (
        "impl Tracked\n    fn r_self(self:& Tracked) -> i32\n        let d: Tracked = *@self\n"
        "        return d.id\n",
        [(3, 26, "cannot move out of a reference"), (3, 28, "cannot move out of a reference")]),
    "lent_array_deref": (
        "fn r_lent_array(a:& [2]Tracked) -> i32\n    let b: [2]Tracked = *a\n    0\n",
        [(2, 26, "cannot move out of a reference")]),
    # The fn's own `ret` runs its deferred statements (AGAST #1625).
    "defer_at_the_end": (
        "fn r_defer() -> i32\n    let a = make(1)\n    defer note(a.id)\n    consume(a)\n    0\n",
        [(3, 5, "`a` may be moved before the deferred statement runs")]),
    # `p[i].f` of a Span: f of the element's struct (AGAST #2444).
    "span_element_field": (
        "fn r_span(p: @&Span<H>) -> i32\n    p[1].t.burn()\n",
        [(2, 5, "cannot move out of a reference")]),
}

OPEN = {
    # A `*T` element of a Vec is a pointer, not the T (AGAST #2444).
    "vec_of_pointers": "fn o_vec(p: @Vec<*Tracked>) -> i32\n    let q: *Tracked = p[1]\n    q.id\n",
    # A discarded match's arm reads no referent (AGAST #3028).
    "discarded_arm": ("fn o_discard(t:& Tracked, k: i32)\n    match k\n        0 => t\n        _ => pass\n"
                      "    let z: i32 = k\n"),
}


def _program(rows):
    """The prelude and every row; each row's first line, 1-based."""
    src = _PRELUDE
    starts = {}
    for name, body in rows:
        starts[name] = src.count("\n") + 1
        src += body + "\n"
    return src + "pub fn main() -> i32\n    0\n", starts


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_the_move_check_reaches_each_binding_the_emitter_typed(request, tmp_path, compiler):
    # One program per compiler (docs/TESTING.md, "What a ritz0 pytest case
    # costs"): each row is its own fn, and a failure names its row.
    request.getfixturevalue("ritz1_bin")
    src, starts = _program([(n, body) for n, (body, _) in sorted(REACH.items())])
    comp, ll, _ = _compile(compiler, tmp_path, "reach", src)
    out = comp.stdout + comp.stderr
    path = _path(out)
    found = re.findall(r"main\.ritz:(\d+):(\d+): (?:error: )?(.*)", out)
    found = [(int(line), int(col), words) for line, col, words in found]
    bad = []
    for name, (_, errors) in sorted(REACH.items()):
        base = starts[name] - 1

        def at(m, base=base):
            line, col = m.group(1).split(":")
            return f"{path}:{base + int(line)}:{col}"

        want = [(base + line, col, re.sub(r"\{at:(\d+:\d+)\}", at, words)) for line, col, words in errors]
        got = [f for f in found if starts[name] <= f[0] < starts[name] + REACH[name][0].count("\n")]
        if got != want:
            bad.append(f"{name}: wanted {want}, got {got}")
    assert comp.returncode != 0, f"{compiler} accepted it:\n{out}"
    assert not bad, f"{compiler}:\n" + "\n".join(bad) + f"\n--- output:\n{out}"
    src, _ = _program(sorted(OPEN.items()))
    comp, ll, _ = _compile(compiler, tmp_path, "open", src)
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused:\n{comp.stdout + comp.stderr}"


@pytest.mark.unit
def test_the_emitter_tracks_no_moves():
    own = (SRC / "ownership.ritz").read_text()
    for word in ("use of moved value", "cannot move out", "may be moved before",
                 "fmoved", "fshadow", "own_snapshot", "OWN_EV_", "own_check_"):
        assert word not in own, f"ownership.ritz still has {word!r}: the move check is own_check.ritz's"
    assert "own_annotated(loc.name)" in own, "own_register gives a drop flag only to what Sema annotated"
    walk = (SRC / "sema_walk.ritz").read_text()
    assert "own_check_stmt(sm, st," in walk, "sema_walk runs the move check"
    ast = (SRC / "ast.ritz").read_text()
    assert "own_binds: *OwnedBinds" in ast, "FnDef carries Sema's owned bindings"
    allow = (RITZ_ROOT / "tools" / "ritz1_emitter_checks.allow").read_text()
    assert "ownership.ritz:" not in allow, "ownership's checks are off the emitter"
