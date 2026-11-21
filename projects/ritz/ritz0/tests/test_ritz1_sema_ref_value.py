"""AGAST #3926: ritz1 checks `@T` read-only and return-of-local on Sema (#1816).

THE CHANGE

ref_check.ritz judged its value checks as the emitter lowered each
statement.  This moves the half the walk itself judges onto Sema
(ref_value.ritz): a write, an `@&` or a `self: @&T` receiver through an `@T`
(LANGUAGE_SPEC §13.3, LARB R1, AGAST #2338 / #2374), and a reference to a
local leaving its fn (§13.5, LARB R2, AGAST #2340).  The slot checks followed
(#4011, test_ritz1_sema_ref_slot.py).  The place queries both sides need
(ref_view_in, ref_write_is_shared_in, ref_ty_in) are one copy over a RefEnv,
and what Sema's scope doesn't keep is noted per binding (ref_check's RsNote).

The rules' own words are ref_rules.py's: test_at_is_read_only.py,
test_at_into_mut.py and test_return_local_ref.py hold all three compilers to
them.

THE TESTS

- An error of either rule now stops the compile before emission: the
  unsupported `for` iterable after it, an error only the emitter reports, is
  no longer printed.  Red on the base.
- REACH: one row per type fact Sema had to learn, each refused at the same
  place in the same words as the emitter did.  OPEN: what the rules leave
  alone stays accepted.
- The emitter no longer runs either rule.
"""

import re
from pathlib import Path

import pytest

from test_ref_into_value import _compile

RITZ_ROOT = Path(__file__).resolve().parents[2]
SRC = RITZ_ROOT / "ritz1" / "src"
COMPILERS = ["ritz1", "ritz1_selfhosted"]
_FOUND = r"main\.ritz:(\d+:\d+): (?:error: )?(.*)"

WRITE = "cannot write through an `@T`: make it `@&T`"
BORROW = "cannot borrow through an `@T` as mutable: make it `@&T`"
INTO_MUT = "an `@T` doesn't fit an `@&T` slot: make it `@&T`"


def _returns(name):
    return f"cannot return a reference to local `{name}`: it ends with the fn"


# name -> (the program, the error's line:col, its words); then an emitter-only error.
STOPS = {
    "write": ("struct C\n    x: i32\n\nfn f(p: @C)\n    p.x = 3\n    var q: i32 = 3\n"
              "    for x in q\n        p.x\n", "5:5", WRITE),
    "return_local": ("struct C\n    x: i32\n\nfn f() -> @C\n    let c = C { x: 1 }\n"
                     "    var q: i32 = 3\n    for x in q\n        c.x\n    @c\n", "9:5", _returns("c")),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_error_stops_the_compile_before_emission(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    bad = []
    for name, (body, at, words) in sorted(STOPS.items()):
        comp, ll, _ = _compile(compiler, tmp_path, name, body + "\npub fn main() -> i32\n    0\n")
        out = comp.stdout + comp.stderr
        found = re.findall(_FOUND, out)
        if comp.returncode == 0 or ll.exists() or found != [(at, words)] or "for` iterable" in out:
            bad.append(f"{name}: wanted only {at}: {words}, got:\n{out}")
    assert not bad, f"{compiler}:\n" + "\n".join(bad)


_C = ("struct C\n    x: i32\n\nstruct H\n    r: @C\n    m: @&C\n\n"
      "impl C\n    fn up(self: @&C)\n        self.x = 1\n\n")
# Line 12 is the first after _C.
_L = 12

# name -> (the program after _C, the error's line:col counted from _L, its words)
REACH = {
    # An un-annotated `let p = @d` is an `@C` (RsNote.ref_kind).
    "inferred_let": ("fn f(d: C)\n    let p = @d\n    p.x = 3\n", "3:5", WRITE),
    # So is one copied from an `@C` field, a `*C` by now with a flag.
    "let_from_field": ("fn f(h: H)\n    let p = h.r\n    p.x = 3\n", "3:5", WRITE),
    # An element through an `@[2]C`'s `p#` view (sema_view_elem).
    "element_field": ("fn f(p: @[2]C)\n    p[1].x = 3\n", "2:5", WRITE),
    # And through a declared local's.
    "declared_element_field": ("fn f(p: @[2]C)\n    let q: @[2]C = p\n    q[1].x = 3\n", "3:5", WRITE),
    # ...and of an un-annotated `let` that holds one (SemaVar.index_elem, #3985).
    "inferred_element_field": ("fn f(p: @[2]C)\n    let q = p\n    q[1].x = 3\n", "3:5", WRITE),
    "inferred_addr_element_field": ("fn f(a: [2]C)\n    let q = @a\n    q[1].x = 3\n", "3:5", WRITE),
    # `*p` of an `@[3]i32` is its `[3]i32` (RsNote.arr_elem).
    "deref_element": ("fn f(p: @[3]i32)\n    (*p)[1] = 7\n", "2:6", WRITE),
    # `*r` of an `@@C`, held as an `@*C`, is the `@C` it was (RsNote.inner_ref).
    "ref_to_ref": ("fn f(r: @@C)\n    (*r).x = 3\n", "2:6", WRITE),
    # A match payload of an `@C` variant binds as an `@C` (RsNote.ref_kind).
    "match_payload": ("enum E\n    S(@C)\n    N\n\nfn f(e: E) -> i32\n    match e\n"
                      "        E.S(v) => v.x = 6\n        _ => 0\n    0\n", "7:19", WRITE),
    "borrow": ("fn bump(q: @&i32)\n    *q = 1\n\nfn f(p: @C)\n    bump(@&p.x)\n", "5:10", BORROW),
    "receiver": ("fn f(h: @H)\n    h.r.up()\n", "2:5", INTO_MUT),
    # An element of a Span reached through an `@`: its method is the element's.
    "span_element_receiver": ("fn f(p: @Span<C>)\n    p[1].up()\n", "2:5", INTO_MUT),
    "mutable_behind_shared": ("fn f(h: @H)\n    h.m.x = 3\n", "2:5", WRITE),
    # A binding keeps the root it refers to (RsNote.root).
    "return_held": ("fn f() -> @C\n    let c = C { x: 1 }\n    let p = @c\n    p\n", "4:5", _returns("c")),
    "return_each_arm": ("fn f(b: bool) -> @C\n    let c = C { x: 1 }\n    if b\n        @c\n"
                        "    else\n        C { x: 2 }.me()\n\nimpl C\n    fn me(self:&) -> @C\n        @self\n",
                        "4:9", _returns("c")),
    "return_call": ("fn id(r: @C) -> @C\n    r\n\nfn f() -> @C\n    let c = C { x: 1 }\n    return id(@c)\n",
                    "6:12", _returns("c")),
    # A by-value `self` is a local root (#2393).
    "return_self_by_value": ("impl C\n    fn me(self) -> @i32\n        @self.x\n", "3:9", _returns("self")),
}

# name -> the program after _C, accepted.
OPEN = {
    "through_a_pointer": "fn f(p: *C)\n    p.x = 3\n",
    "through_a_mutable_ref": "fn f(p: @&C)\n    p.x = 3\n",
    # `@q` of a `*C` is an `@*C`: `.` reaches C through the `*` last.
    "ref_to_a_pointer": "fn f(q: *C)\n    let p = @q\n    p.x = 3\n",
    # What a `:&` param or `self:&` names is the caller's.
    "lent_param": "fn f(c:& C) -> @C\n    @c\n",
    "lent_self": "impl C\n    fn mine(self:&) -> @i32\n        @self.x\n",
    # A `var` written again no longer definitely refers to its first root.
    "var_rewritten": ("fn f(g: @C) -> @C\n    var c = C { x: 1 }\n    var p = @c\n    p = g\n    p\n"),
    # ...and a loop can reach that write before the return.
    "var_written_in_a_loop": ("fn f(g: @C) -> @C\n    var c = C { x: 1 }\n    var p = @c\n    var i = 0\n"
                              "    while i < 2\n        if i == 1\n            return p\n"
                              "        p = g\n        i = i + 1\n    g\n"),
    # `@&x` into an `@&T` param may be written through: it no longer counts.
    "lent_to_a_call": ("fn reset(q: @&@C, g: @C)\n    *q = g\n\n"
                       "fn f(g: @C) -> @C\n    var c = C { x: 1 }\n    var p = @c\n    reset(@&p, g)\n    p\n"),
    # So may a bare place passed to a `:&` param.
    "lent_bare_to_a_call": ("fn reset(q:& *C, g: *C)\n    q = g\n\n"
                            "fn f(g: *C) -> *C\n    var c = C { x: 1 }\n    var p: *C = @c\n    reset(p, g)\n    p\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_the_rules_reach_each_fact_sema_learned(request, tmp_path, compiler):
    # One table test per compiler (docs/TESTING.md, "What a ritz0 pytest case
    # costs"): a failure still names its own row.
    request.getfixturevalue("ritz1_bin")
    tail = "\npub fn main() -> i32\n    0\n"
    bad = []
    for name, (body, at, words) in sorted(REACH.items()):
        comp, ll, _ = _compile(compiler, tmp_path, name, _C + body + tail)
        out = comp.stdout + comp.stderr
        line, col = (int(n) for n in at.split(":"))
        want = [(f"{_L + line - 1}:{col}", words)]
        found = re.findall(_FOUND, out)
        if comp.returncode == 0 or found != want:
            bad.append(f"{name}: wanted {want}, got:\n{out}")
    for name, body in sorted(OPEN.items()):
        comp, ll, _ = _compile(compiler, tmp_path, "open_" + name, _C + body + tail)
        if comp.returncode != 0 or not ll.exists():
            bad.append(f"open {name}: refused:\n{comp.stdout + comp.stderr}")
    assert not bad, f"{compiler}:\n" + "\n".join(bad)


@pytest.mark.unit
def test_the_emitter_runs_neither_rule():
    ref = (SRC / "ref_check.ritz").read_text()
    for gone in ("fn ref_check_write", "fn ref_check_receiver", "fn ref_referent", "REF_DECL_ROOT",
                 "fn ref_check_return"):
        assert gone not in ref, f"ref_check.ritz still has {gone}: ref_value.ritz runs it, on Sema"
    core = (SRC / "emitter_core.ritz").read_text()
    assert "ref_root" not in core, "LocalVar still keeps ref_root: Sema's RsNote does"
    # AGAST #3985: a `p#` view's element is SemaVar.index_elem's, not a second copy.
    assert "fn rv_view_elem" not in (SRC / "ref_value.ritz").read_text()
    assert "    elem: i32" not in ref, "RsNote still keeps a `p#` view's elem: SemaVar.index_elem has it"
    walk = (SRC / "sema_walk.ritz").read_text()
    for hook in ("ref_value_begin_fn", "ref_value_check_stmt", "ref_value_check_value", "ref_value_after"):
        assert hook in walk, f"sema_walk doesn't call {hook}"
