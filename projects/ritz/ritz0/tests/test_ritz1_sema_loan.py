"""AGAST #3506: ritz1 checks §13.5's borrow conflicts on Sema (#1816).

THE CHANGE

LANGUAGE_SPEC §13.5's first rule (LARB R11 / R11a, AGAST #2438): while a
binding holds an `@T` of a place, or within one call's arguments, a mutable
borrow of an overlapping place is an error; while it holds an `@&T`, any
borrow is.  ritz1 tracked those loans in ref_check.ritz as the emitter
lowered each statement, and own_pop_scope ended them with each block.  Now
ref_loan.ritz runs from Sema's walk: Sema's own blocks end a loan, and each
place's steps are typed from Sema's scope.  ref_check's value checks stay on
the emitter for now: that is #3506's second half.

The rule's own words are test_borrow_conflict_all_compilers.py's and
test_for_holds_root_all_compilers.py's, on all three compilers.

THE TESTS

- A loan error now stops the compile before emission: the unsupported `for`
  iterable after it, an error only the emitter reports, is no longer
  printed.  Red on the base.
- REACH: one row per kind of binding the emitter typed and Sema types through
  its notes (a `:&` param, `self`, an inferred `let`, an element, a match
  payload, a free call lending `self`).  Each is refused at the same place,
  in the same words.  OPEN: what holds a pointer borrows nothing, so those
  stay accepted.
- The emitter tracks no loans: no RefLoan in ref_check, and ownership's
  blocks no longer end any.
"""

import re
from pathlib import Path

import pytest

from test_ref_into_value import _compile

RITZ_ROOT = Path(__file__).resolve().parents[2]
SRC = RITZ_ROOT / "ritz1" / "src"
COMPILERS = ["ritz1", "ritz1_selfhosted"]

STOPS_BEFORE_EMIT = """\
struct C
    x: i32
    y: i32

fn bump(p: @&i32)
    *p = *p + 1

fn main() -> i32
    var c: C
    c.x = 1
    c.y = 2
    let p = @c.x
    bump(@&c.x)
    var q: i32 = 3
    for x in q
        c.y = 2
    *p
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_loan_error_stops_the_compile_before_emission(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_loan", STOPS_BEFORE_EMIT)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    assert found == [("13:10", "cannot borrow `c.x` as mutable - `c.x` is already borrowed as immutable")], \
        f"{compiler}:\n{out}"
    assert "for` iterable" not in out, f"{compiler} went on to emit:\n{out}"


_C = ("struct C\n    x: i32\n    y: i32\n\n"
      "impl C\n    fn up(self: @&C)\n        self.x = self.x + 1\n\n"
      "    fn lend_up(self:& C)\n        self.x = self.x + 1\n\n"
      "fn bump(p: @&i32)\n    *p = *p + 1\n\n"
      "fn mk() -> C\n    C { x: 1, y: 2 }\n\n")
# Line 18 is the first after _C.
_L = 18


def _conflict(place, held, how="immutable", verb="borrow", mut=True):
    if verb == "assign":
        return f"cannot assign to `{place}` - `{held}` is already borrowed as {how}"
    kind = "mutable" if mut else "immutable"
    return f"cannot borrow `{place}` as {kind} - `{held}` is already borrowed as {how}"


# name -> (the program after _C, the error's line:col counted from _L, its words)
REACH = {
    # A `c:& C` param reads as a `C`: SemaVar.lent.
    "lent_param": ("fn f(c:& C) -> i32\n    let p = @c.x\n    bump(@&c.x)\n    *p\n\n"
                   "fn main() -> i32\n    var c: C = mk()\n    f(c)\n",
                   "3:10", _conflict("c.x", "c.x")),
    # A by-value `self` in an impl reads as the impl's struct.
    "self_by_value": ("impl C\n    fn get(self) -> i32\n        let p = @self.x\n"
                      "        bump(@&self.x)\n        *p\n\n"
                      "fn main() -> i32\n    var c: C = mk()\n    c.get()\n",
                      "4:14", _conflict("self.x", "self.x")),
    # A bare `self:&` likewise.
    "self_lent": ("impl C\n    fn get(self:&) -> i32\n        let p = @self.x\n"
                  "        bump(@&self.x)\n        *p\n\n"
                  "fn main() -> i32\n    var c: C = mk()\n    c.get()\n",
                  "4:14", _conflict("self.x", "self.x")),
    # An inferred `var` of a call's struct: let_check's note.
    "inferred_var": ("fn main() -> i32\n    var c = mk()\n    let p = @c.x\n    bump(@&c.x)\n    *p\n",
                     "4:10", _conflict("c.x", "c.x")),
    # Any two indexes are one place: an element of an array of structs.
    "array_element": ("fn main() -> i32\n    var cs: [2]C\n    cs[0] = mk()\n    let p = @cs[0].x\n"
                      "    bump(@&cs[1].x)\n    *p\n",
                      "5:10", _conflict("cs[_].x", "cs[_].x")),
    # A match payload binding: deref_field's note (SemaVar.recv).
    "match_payload": ("enum E\n    A(C)\n    B\n\n"
                      "fn main() -> i32\n    let e = E.A(mk())\n    match e\n        E.A(c) =>\n"
                      "            let p = @c.y\n            c.up()\n            *p\n        E.B => 0\n",
                      "10:13", _conflict("c", "c.y")),
    # A free call of a `self:& C` method lends its receiver (AGAST #3278).
    "free_call_lends_self": ("fn main() -> i32\n    var c: C = mk()\n    let p = @c\n"
                             "    C_lend_up(c)\n    (*p).x\n",
                             "4:15", _conflict("c", "c")),
    # A match arm's value: its call's arguments, with the arm's binding.
    "arm_value": ("enum E\n    A(C)\n    B\n\nfn both(a: @&i32, b: @i32) -> i32\n    *a + *b\n\n"
                  "fn main() -> i32\n    var e = E.A(mk())\n    let r: i32 = match e\n"
                  "        E.A(d) => both(@&d.x, @d.x)\n        E.B => 0\n    r\n",
                  "11:31", _conflict("d.x", "d.x", how="mutable", mut=False)),
    # A place passed bare into a `:&` param is lent until the call's
    # arguments are done.
    "bare_into_lent_then_borrow": ("fn g(a:& i32, b: @i32) -> i32\n    a + *b\n\n"
                                   "fn main() -> i32\n    var c: C = mk()\n    g(c.x, @c.x)\n",
                                   "6:12", _conflict("c.x", "c.x", how="mutable", mut=False)),
    # A write into a place an `@&` holds.
    "write_member": ("fn main() -> i32\n    var c: C = mk()\n    let p = @&c.x\n    c.x = 3\n    *p\n",
                     "4:5", _conflict("c.x", "c.x", how="mutable", verb="assign")),
}

# name -> the program after _C: a pointer step, or `@x` held in a `*T`,
# borrows nothing.
OPEN = {
    "through_a_pointer": ("fn f(q: *C) -> i32\n    let p = @q.x\n    bump(@&q.x)\n    *p\n\n"
                          "fn main() -> i32\n    var c: C = mk()\n    f(@c)\n"),
    "held_in_a_raw_pointer": ("fn main() -> i32\n    var c: C = mk()\n    let p: *i32 = @c.x\n"
                              "    bump(@&c.x)\n    *p\n"),
    "self_pointer": ("impl C\n    fn get(self: @&C) -> i32\n        let p = @self.x\n"
                     "        bump(@&self.x)\n        *p\n\n"
                     "fn main() -> i32\n    var c: C = mk()\n    c.get()\n"),
    # A match arm is a block: what its `let` holds ends with it.
    "arm_ends_the_loan": ("enum F\n    A(i32)\n    B\n\nfn main() -> i32\n    var c: C = mk()\n"
                          "    let e = F.A(1)\n    match e\n        F.A(n) =>\n            let p = @c.x\n"
                          "            c.y = *p + n\n        F.B => c.y = 0\n    bump(@&c.x)\n    c.x\n"),
    "block_ends_the_loan": ("fn main() -> i32\n    var c: C = mk()\n    if c.y > 0\n"
                            "        let p = @c.x\n        c.y = *p\n    bump(@&c.x)\n    c.x\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_loans_reach_each_binding_the_emitter_typed(request, tmp_path, compiler):
    # One table test per compiler (docs/TESTING.md, "What a ritz0 pytest case
    # costs"): a failure still names its own row.
    request.getfixturevalue("ritz1_bin")
    bad = []
    for name, (body, at, words) in sorted(REACH.items()):
        comp, ll, _ = _compile(compiler, tmp_path, name, _C + body)
        out = comp.stdout + comp.stderr
        line, col = (int(n) for n in at.split(":"))
        want = [(f"{_L + line - 1}:{col}", words)]
        found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
        if comp.returncode == 0 or found != want:
            bad.append(f"{name}: wanted {want}, got:\n{out}")
    for name, body in sorted(OPEN.items()):
        comp, ll, _ = _compile(compiler, tmp_path, "open_" + name, _C + body)
        if comp.returncode != 0 or not ll.exists():
            bad.append(f"open {name}: refused:\n{comp.stdout + comp.stderr}")
    assert not bad, f"{compiler}:\n" + "\n".join(bad)


@pytest.mark.unit
def test_the_emitter_tracks_no_loans():
    ref = (SRC / "ref_check.ritz").read_text()
    assert "RefLoan" not in ref, "ref_check.ritz still tracks loans: ref_loan.ritz does, on Sema"
    own = (SRC / "ownership.ritz").read_text()
    assert "ref_loans_" not in own, "ownership's blocks still end loans: Sema's blocks do"
    walk = (SRC / "sema_walk.ritz").read_text()
    assert "ref_loan_check_stmt" in walk, "sema_walk runs the loan check"
