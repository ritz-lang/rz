"""AGAST #4011: ritz1 runs ref_check's slot checks on Sema (#1816, #3926's second half).

THE CHANGE

ref_check.ritz judged its slot checks as the emitter lowered each statement
(ref_check_stmt / ref_check_value, from the ownership hooks).  They run on Sema
now, in ref_value.ritz's walk with #3926's `@T` read-only and return-of-local
checks: a reference into a by-value slot and back (LANGUAGE_SPEC §13.2-13.4,
LARB R1, #2336 / #2337), `@x` or an `@T` into an `@&T` or `:&` slot (#2339 /
#2374), a `:&` param's referent (#2367), arrays (R5 / R42, #2343 / #3383 /
#3054), variant payloads, casts (#2370 / #2985), a call's temporary (#2518 /
#3050 / #3215) and `[v; n]` of a move-only v (#2963).

Types are ref_check's ref_ty_in, one copy over a RefEnv: on Sema each binding
carries an image of the LocalVar the emitter will make for it (RsNote.loc),
from its param or declaration, its initialiser, or Sema's own type of it.

The rules' own words are ref_rules.py's and array_rules.py's:
test_ref_into_value.py, test_value_into_ref.py, test_at_into_mut.py,
test_array_store_rule.py, test_call_temporary_place.py and their kin hold all
three compilers to them.

THE TESTS

- A slot error now stops the compile before emission: the unsupported `for`
  iterable after it, an error only the emitter reports, is no longer printed.
  Red on the base.
- REACH: one row per fact Sema had to learn, each refused at the same place in
  the same words as the emitter did.  OPEN: what the rules leave alone stays
  accepted.
- The emitter runs none of them, and their two entries are gone from
  tools/ritz1_emitter_checks.allow.
"""

import re
from pathlib import Path

import pytest

from test_ref_into_value import _compile

RITZ_ROOT = Path(__file__).resolve().parent.parent
SRC = RITZ_ROOT / "ritz1" / "src"
ALLOW = RITZ_ROOT / "tools" / "ritz1_emitter_checks.allow"
COMPILERS = ["ritz1", "ritz1_selfhosted"]
_FOUND = r"main\.ritz:(\d+:\d+): (?:error: )?(.*)"

SLOT_REF = "a reference or pointer doesn't fit a by-value slot: write `*` to read through it"
SLOT_ADDR = "`@x` doesn't fit a by-value slot: drop the `@`"
INTO_REF = "a value doesn't fit a reference slot: write `@x` to borrow it"
OTHER_TYPE = "a reference to one type doesn't fit a reference to another: cast it with `as`"
OTHER_PTR = "a reference to one pointer type doesn't fit a reference to another"
SHARED_INTO_MUT = "`@x` is shared and doesn't fit an `@&T` or `:&` slot: write `@&x`"
ARRAY_ELEM = "an array only fits a slot of the same element type: write a loop to convert it"
WHOLE_ARRAY = "a whole array is not a pointer: `@a[0]` points at its first element"
FILL = "`[v; n]` copies `v` into every element: a move-only value fills one, `[v; 1]`"
TEMP_STORE = "a store into a call's temporary is lost: bind the call to a local first"
TEMP_SELF = "a method that writes `self` can't take a call's temporary: bind the call to a local first"
TEMP_ADDR = ("`@` of a call's temporary outlives it: bind the call to a local first, "
             "or pass it straight to a call")
LENT_ESCAPE = ("this call returns a reference, and `@mk()` lends a temporary that's dropped when "
               "the call returns: bind it to a local first")

# name -> (the program, the error's line:col, its words); then an emitter-only error.
_FOR = "    var q: i32 = 3\n    for x in q\n        x\n"
STOPS = {
    "ref_into_value": ("struct C\n    x: i32\n\nfn f(p: @C)\n    let c: C = p\n" + _FOR, "5:16", SLOT_REF),
    "value_into_ref": ("struct C\n    x: i32\n\nfn g(r: @C) -> i32\n    r.x\n\nfn f(c: C)\n    g(c)\n" + _FOR,
                       "8:7", INTO_REF),
    "array_element": ("fn g(a: [2]i64) -> i64\n    a[0]\n\nfn f(a: [2]i32)\n    g(a)\n" + _FOR, "5:7", ARRAY_ELEM),
}

_C = ("struct C\n    x: i32\n\nstruct H\n    r: @C\n    m: @&C\n\nstruct P\n    p: *i32\n\n"
      "impl C\n    fn up(self: @&C)\n        self.x = 1\n\n")
# Line 15 is the first after _C.
_L = 15
_D = "struct D\n    x: i32\n\nimpl Drop for D\n    fn drop(self: @&D)\n        self.x = 0\n\n"
_MK = "fn mk() -> C\n    C { x: 1 }\n\n"
_BUMP = "fn g(q: @&i64)\n    *q = 1\n\n"

# name -> (the program after _C, the error's line:col counted from _L, its words)
REACH = {
    # A param's image: an `@C` is a pointer, a `c:& C` reads as its C.
    "param_ref_into_value": ("fn f(p: @C)\n    let c: C = p\n", "2:16", SLOT_REF),
    "lent_param_into_ref": ("fn g(r: @C) -> i32\n    r.x\n\nfn f(c:& C)\n    g(c)\n", "5:7", INTO_REF),
    # A bool is held in an i64 slot, and is still a bool: declared, a param, inferred.
    "bool_local_referent": (_BUMP + "fn f()\n    var b: bool = true\n    g(@&b)\n", "6:7", OTHER_TYPE),
    "bool_param_referent": (_BUMP + "fn f(b: bool)\n    g(@&b)\n", "5:7", OTHER_TYPE),
    "inferred_bool_copy": (_BUMP + "fn f(b: bool)\n    var c = b\n    g(@&c)\n", "6:7", OTHER_TYPE),
    "inferred_bool": (_BUMP + "fn f(n: i32)\n    var b = n > 0\n    g(@&b)\n", "6:7", OTHER_TYPE),
    # An array param's element; an `a:& [2]i32` binds as the array; `@a`'s size.
    "array_param_element": ("fn g(a: [2]i64) -> i64\n    a[0]\n\nfn f(a: [2]i32)\n    g(a)\n", "5:7", ARRAY_ELEM),
    "lent_array_bare": ("fn g(p: *[2]i32) -> i32\n    0\n\nfn f(a:& [2]i32)\n    g(a)\n", "5:7", INTO_REF),
    "lent_array_referent": ("fn g(p: *[3]i32)\n    0\n\nfn f(a:& [2]i32)\n    g(@a)\n", "5:7", OTHER_TYPE),
    "array_referent_size": ("fn g(p: *[2][3]i32)\n    0\n\nfn f(a: [6]i32)\n    g(@a)\n", "5:7", OTHER_TYPE),
    # An un-annotated `let`: its initialiser's type, or the reference its view makes it.
    "inferred_let_from_call": ("fn pick(p: *C) -> *C\n    p\n\nfn f(d: *C)\n    let p = pick(d)\n    let c: C = p\n",
                               "6:16", SLOT_REF),
    "inferred_ref_view": ("fn f(d: C)\n    let p = @d\n    let c: C = p\n", "3:16", SLOT_REF),
    # A `for` variable is Sema's own type of it.
    "for_variable": ("fn f(cs: [2]C)\n    for c in cs\n        let q: @i32 = @c\n", "3:23", OTHER_TYPE),
    # A declared `**C` local's slot, and an `@*i64` param's U.
    "ptr_ptr_slot": ("fn f(q: *C)\n    var pp: **C = @q\n    pp = q\n", "3:10", INTO_REF),
    "ref_ptr_pointee": ("fn f(q: @*i64)\n    let r: @*i32 = q\n", "2:20", OTHER_PTR),
    # A `*i32` field's pointee; `@C` fields as lower_ref_fields will make them.
    "member_pointee": ("fn f(s: P)\n    let x: i32 = s.p\n", "2:18", SLOT_REF),
    "ref_field_read": ("fn f(h: H)\n    let c: C = h.r\n", "2:16", SLOT_REF),
    "struct_field_slot": ("fn f(c: C)\n    let h = H { r: c, m: @&c }\n", "2:20", INTO_REF),
    "member_assign_slot": ("fn f(h: @&H, c: C)\n    h.r = c\n", "2:11", INTO_REF),
    # Option<C>'s payload, by Sema's struct map.
    "variant_payload": ("fn f(p: @C) -> Option<C>\n    Some(p)\n", "2:10", SLOT_REF),
    # Arrays: a literal's length, a whole array into a pointer.
    "assign_literal_length": ("fn f()\n    var a: [3]i32 = [1, 2, 3]\n    a = [1, 2]\n", "3:9",
                              "an array literal of 2 elements for a `[3]i32`"),
    "whole_array_into_pointer": ("fn g(p: *i32)\n    *p = 1\n\nfn f()\n    var a: [2]i32 = [1, 2]\n    g(a)\n",
                                 "6:7", WHOLE_ARRAY),
    # `@x` into an `@&T`, and of a `let`.
    "shared_into_mut_param": ("fn g(q: @&C)\n    q.x = 1\n\nfn f()\n    var c = C { x: 1 }\n    g(@c)\n",
                              "6:7", SHARED_INTO_MUT),
    "let_into_mut_param": ("fn g(q: @&C)\n    q.x = 1\n\nfn f()\n    let c = C { x: 1 }\n    g(@c)\n", "6:7",
                           "cannot borrow `let` binding `c` as mutable; declare it `var`"),
    # The slot check speaks before return-of-local at the same place (rv_slot_refuses is gone).
    "return_slot_first": ("fn f() -> @&C\n    var c = C { x: 1 }\n    @c\n", "3:5", SHARED_INTO_MUT),
    # Move-only, by the module's `impl Drop`.
    "fill_move_only": (_D + "fn f(d: D)\n    let a = [d; 2]\n", "9:13", FILL),
    "cast_move_only": (_D + "fn f(r: @D) -> D\n    r as D\n", "9:5", SLOT_REF),
    "cast_value_to_ref": ("fn f(c: C)\n    let p = c as *C\n", "2:13", INTO_REF),
    # A call's temporary.
    "temp_store": (_MK + "fn f()\n    mk().x = 2\n", "5:5", TEMP_STORE),
    "temp_receiver": (_MK + "fn f()\n    mk().up()\n", "5:5", TEMP_SELF),
    "temp_addr": (_MK + "fn f()\n    let p = @mk()\n", "5:13", TEMP_ADDR),
    "lent_escape": ("fn id(r: @C) -> @C\n    r\n\n" + _MK + "fn f() -> i32\n    id(@mk()).x\n", "8:8", LENT_ESCAPE),
    # An impl's lent `self` is a pointer to the impl's type (emit_impl_method).
    "impl_self": ("fn h(p: C) -> i32\n    p.x\n\nimpl C\n    fn g(self:&) -> i32\n        h(@self)\n",
                  "6:11", SLOT_ADDR),
    # A local holding a fn calls it: `let f = mb` (inferred_fn_sig).
    "fn_local": ("fn mb(c: @&C) -> i32\n    c.x\n\nfn f() -> i32\n    var c = C { x: 1 }\n    let g = mb\n    g(@c)\n",
                 "7:7", SHARED_INTO_MUT),
    # `let q = @&x[0]` of a `[2][2][3]i64` is a plane pointer (#2570): `*q` is its `[2][3]i64`.
    "plane_pointer": ("fn f()\n    var x: [2][2][3]i64 = [ [ [0; 3]; 2]; 2]\n    let q = @&x[0]\n    *q = [ [1, 2, 3]]\n",
                      "4:10", "an array literal of 1 element for a `[2][3]i64`"),
}

# name -> the program after _C, accepted.
OPEN = {
    # `C_bump(d)` of a `self:& C` lends d (lent_self_call_view, #3278).
    "lent_self_call": "impl C\n    fn bump(self:& C)\n        self.x = 2\n\nfn f(c: C)\n    var d = c\n    C_bump(d)\n",
    "for_ref": "fn f(cs: [2]C) -> i32\n    var n: i32 = 0\n    for c in cs\n        let q: @C = @c\n        n = n + q.x\n    n\n",
    "through_a_pointer": "fn f(p: *C) -> i32\n    let q: *C = p\n    q.x\n",
    "mutable_into_mutable": "fn g(q: @&C)\n    q.x = 1\n\nfn f(p: @&C)\n    g(p)\n",
    "array_of_its_type": "fn g(a: [2]i32) -> i32\n    a[0]\n\nfn f(a: [2]i32) -> i32\n    g(a)\n",
    "temp_lent_to_a_call": _MK + "fn g(c: @C) -> i32\n    c.x\n\nfn f() -> i32\n    g(@mk())\n",
    # `h.r[1]` through an `@&[3]i32` field is an element through a pointer to an
    # array (index_through's base_array_view): what it is isn't vouched for.
    "element_through_a_field": "struct F\n    r: @&[3]i32\n\nfn f(h: *F)\n    let e: @&i32 = @&h.r[1]\n    *e = 7\n",
    # ...and so is `q[1]` of a `let q = h(p)` holding the `*[3]i32` h returns.
    "element_through_a_returned_pointer": ("fn h(p: *[3]i32) -> *[3]i32\n    p\n\n"
                                           "fn f(p: *[3]i32)\n    let q = h(p)\n    let e: @&i32 = @&q[1]\n    *e = 7\n"),
    # As the emitter binds it, an `@C` match payload goes unread (bool_note_binding's
    # bk_unsure).  ritz0 refuses it: AGAST #4143.
    "pointer_payload_unread": ("enum E\n    S(@C)\n    N\n\nfn take(c: C) -> i32\n    c.x\n\n"
                               "fn f(e: E) -> i32\n    match e\n        E.S(v) => take(v)\n        _ => 0\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_slot_error_stops_the_compile_before_emission(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    bad = []
    for name, (body, at, words) in sorted(STOPS.items()):
        comp, ll, _ = _compile(compiler, tmp_path, name, body + "\npub fn main() -> i32\n    0\n")
        out = comp.stdout + comp.stderr
        found = re.findall(_FOUND, out)
        if comp.returncode == 0 or ll.exists() or found != [(at, words)] or "for` iterable" in out:
            bad.append(f"{name}: wanted only {at}: {words}, got:\n{out}")
    assert not bad, f"{compiler}:\n" + "\n".join(bad)


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
def test_the_emitter_runs_none_of_them():
    ref = (SRC / "ref_check.ritz").read_text()
    for gone in ("fn ref_check_stmt", "fn ref_check_value", "fn ref_into(", "fn ref_walk(", "fn ref_landed",
                 "REF_TAILS", "fn ref_array_into_pointer_at"):
        assert gone not in ref, f"ref_check.ritz still has {gone}: ref_value.ritz runs it, on Sema"
    own = (SRC / "ownership.ritz").read_text()
    for hook in ("ref_check_stmt(", "ref_check_value("):
        assert hook not in own, f"ownership.ritz's hooks still call {hook}"
    value = (SRC / "ref_value.ritz").read_text()
    assert "rv_slot_refuses" not in value, "return-of-local still stands aside for an emitter check"
    allow = ALLOW.read_text()
    for entry in ("ref_check.ritz:ref_check_stmt", "ref_check.ritz:ref_check_value"):
        assert entry not in allow, f"{entry} is still in {ALLOW.name}"
