#!/usr/bin/env python3
"""Implicit narrowing at an assignment, a call argument or a `return` (#1444).

#1393 made a narrowing `let`/`var` initialiser an error unless provably
lossless (test_implicit_narrowing.py pins that rule and its exemptions). The
same conversion elsewhere still truncated silently:

    fn r() -> i32
        return big()            # return
    n = big()                   # assignment, n: i32
    take(big())                 # argument, take(v: i32)

LANGUAGE_SPEC §7.5 now holds every one of them to the same rule. The
exemption (`_provable_int_range`) is shared and already pinned by
test_implicit_narrowing.py, so the rows here are sized to the ROUTES, not to
the exemption's shapes: one rejected row for each way a value reaches each
position (each has its own call to the check, or reaches the shared hook by
its own store), plus one accepted control per position so the check cannot
pass by rejecting every narrowing.
"""

import os
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.integration

PRELUDE = """\
enum Order
    Gray
    RGB

struct P
    x: i32

struct B
    pad: [64]i32
    v: u8

impl P
    fn make(v: i32) -> P
        return P { x: v }
    fn set(self:& P, v: i32)
        self.x = v

extern fn ext_take(v: i32) -> i32

var G: i32 = 0

fn big() -> i64
    return 4294967301

fn take(v: i32) -> i32
    return v

fn take_u8(v: u8) -> u8
    return v

fn take64(v: i64) -> i64
    return v

"""
# Lines of PRELUDE, so a test can assert the diagnostic's line number.
PRELUDE_LINES = PRELUDE.count("\n")


def _compile(tmp_path, body):
    src = tmp_path / "unit.ritz"
    src.write_text(PRELUDE + body)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return run_ritz0([str(src), "-o", str(tmp_path / "unit.ll"), "--no-runtime"],
                     env=env, timeout=300)


def _fn(stmts, ret="i32", tail="return 0"):
    """`stmts` in `fn f(...)`: its first line is line 2 of the function."""
    body = "".join(f"    {line}\n" for line in stmts.splitlines())
    tail = f"    {tail}\n" if tail else ""
    return f"fn f(x: i32, o: Order, k: u8) -> {ret}\n{body}{tail}"


# --------------------------------------------------------------------------
# Rejected: one row per route a narrowing value takes into its slot.
# --------------------------------------------------------------------------

REJECTED = {
    # return
    "return_stmt":          _fn("return big()", tail=""),
    "fn_tail_value":        _fn("big()", tail=""),
    "return_in_match_arm":  _fn("let n: i32 = match o\n"
                                "    Gray => return big()\n"
                                "    RGB => 1", tail="return n"),
    "return_unsigned_slot": _fn("return 0 - 1", ret="u8", tail=""),
    # assignment: each store route converts on its own
    "assign_local":         _fn("var n: i32 = 0\nn = big()"),
    "assign_global":        _fn("G = big()"),
    "assign_field":         _fn("var p = P { x: 0 }\np.x = big()"),
    "assign_index":         _fn("var a: [2]i32 = [0, 0]\na[1] = big()"),
    "assign_deref":         _fn("var n: i32 = 0\nlet p: *i32 = @n\n*p = big()"),
    "assign_compound":      _fn("var n: i32 = 0\nn += big()"),
    "assign_in_match_arm":  _fn("var n: i32 = 0\nmatch o\n"
                                "    Gray => n = big()\n"
                                "    RGB => n = 1"),
    "assign_unsigned_slot": _fn("var b: u8 = 0\nb = 0 - 1"),
    # call argument: each call route converts on its own
    "arg_direct":           _fn("take(big())"),
    "arg_fn_pointer":       _fn("let t = take\nt(big())"),
    "arg_extern":           _fn("ext_take(big())"),
    "arg_static_method":    _fn("let p = P.make(big())"),
    "arg_instance_method":  _fn("var p = P.make(1)\np.set(big())"),
    "arg_unsigned_slot":    _fn("take_u8(0 - 1)"),
    # struct literal field (#4157): a small literal is built as a value, a
    # large one (>= SRET_MIN_BYTES) in place, each converting its fields.
    "field_value_lit":      _fn("let p = P { x: big() }"),
    "field_in_place_lit":   _fn("var b = B { v: x }"),
    "field_unsigned_slot":  _fn("var b = B { v: 0 - 1 }"),
}


# --------------------------------------------------------------------------
# The diagnostic: names the slot and both types, suggests `as`, and points at
# the value. One per position, since each words its slot differently.
# --------------------------------------------------------------------------

DIAGNOSTICS = {
    # name: (body, line within f, column, slot words)
    "return": (_fn("return big()", tail=""), 2, 12, "`f` returns `i32`"),
    "assign": (_fn("var n: i32 = 0\nn = big()"), 3, 9, "`n` is `i32`"),
    "arg":    (_fn("let r = take(big())"), 2, 18, "argument 1 of `take` is `i32`"),
    "field":  (_fn("var p = P { x: 0 }\np.x = big()"), 3, 11, "`p.x` is `i32`"),
    # An async fn's result is lowered to a store into its future's
    # `__result`; the error names the fn, as a plain `return` does (#4166).
    "async_return": ("async fn f() -> i32\n    return big()\n", 2, 12, "`f` returns `i32`"),
    "async_tail":   ("async fn f() -> i32\n    big()\n", 2, 5, "`f` returns `i32`"),
    "async_return_after_await": ("async fn f() -> i32\n    let w = await one()\n    return big()\n\n"
                                 "async fn one() -> i32\n    1\n", 3, 12, "`f` returns `i32`"),
    "field_init": (_fn("let p = P { x: big() }"), 2, 20, "field `x` of `P` is `i32`"),
}


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(DIAGNOSTICS))
def test_diagnostic_names_slot_types_and_is_located(tmp_path, name):
    body, line, col, slot = DIAGNOSTICS[name]
    r = _compile(tmp_path, body)
    assert r.returncode != 0
    want = (f"unit.ritz:{PRELUDE_LINES + line}:{col}: implicit narrowing: {slot} "
            f"but this value has type `i64`")
    assert want in r.stderr, f"wanted {want!r}:\n{r.stderr[-1500:]}"
    assert "as i32" in r.stderr, r.stderr[-1500:]


# An async fn's `let v: T = await ...` is lowered to a store into its future,
# `*self.v = <poll result>`, whose value has no source position.  The error
# names the user's binding and points at its `let`, not at `*self.v` 0:0:0.
ASYNC_LET = ("async fn wide() -> i64\n    return big()\n\n"
             "async fn g() -> i32\n    let v: i32 = await wide()\n    v\n")


@pytest.mark.unit
def test_an_awaited_let_is_reported_at_the_let(tmp_path):
    r = _compile(tmp_path, ASYNC_LET)
    assert r.returncode != 0
    want = (f"unit.ritz:{PRELUDE_LINES + 5}:5: implicit narrowing: `v` is `i32` "
            f"but this value has type `i64`")
    assert want in r.stderr, f"wanted {want!r}:\n{r.stderr[-1500:]}"


# --------------------------------------------------------------------------
# Accepted: provably lossless, explicit, or not a narrowing at all.
# --------------------------------------------------------------------------

ACCEPTED = {
    # return
    "return_constant_fits":   _fn("return 8 + 4", tail=""),
    "return_mask":            _fn("return big() & 255", tail=""),
    "return_explicit_cast":   _fn("return big() as i32", tail=""),
    "tail_constant_into_u8":  _fn("200", ret="u8", tail=""),
    # assignment. `n = n + 1` is a literal taking n's type (LARB R21), so it
    # is an i32 sum and narrows nothing: the artifact #1444 warned about.
    "assign_literal_sum":     _fn("var n: i32 = 0\nn = n + 1\nn += 1"),
    "assign_unsigned_const":  _fn("var b: u8 = 0\nb = 200"),
    "assign_narrow_sum":      _fn("var b: u8 = 0\nb = k + 1"),
    "assign_mask":            _fn("var b: u8 = 0\nb = big() & 255"),
    "assign_explicit_cast":   _fn("var n: i32 = 0\nn = big() as i32\nG = big() as i32"),
    # call argument
    "arg_constant_fits":      _fn("take(7)\ntake_u8(200)"),
    "arg_mask":               _fn("take(big() & 255)"),
    "arg_explicit_cast":      _fn("take(big() as i32)\nP.make(big() as i32)"),
    "arg_widening":           _fn("take64(x)"),
    # struct literal field
    "field_constant_fits":    _fn("let p = P { x: 7 }\nvar b = B { v: 200 }"),
    "field_mask":             _fn("var b = B { v: x & 255 }"),
    "field_explicit_cast":    _fn("let p = P { x: big() as i32 }\nvar b = B { v: x as u8 }"),
    "field_widening":         _fn("let p = P { x: k }"),
    "field_if_literal_arm":   _fn("var b = B { v: if x > 0 then k else 0 }"),
    # #1396's literal context, which a `let` gets, at each position: the
    # literal takes the slot's width, so `8 << ...` shifts at i32.
    "return_literal_shift":   _fn("return 8 << (x & 3)", tail=""),
    "tail_literal_shift":     _fn("8 << (x & 3)", tail=""),
    "assign_literal_shift":   _fn("var n: i32 = 0\nn = n | (1 << x)"),
    "arg_literal_shift":      _fn("take(x | (1 << x))"),
    # An if/match merge is as wide as its widest arm, and a literal arm is
    # i64; narrowing it back to the i32 its other arm came from loses nothing.
    "return_if_literal_arm":  _fn("return if x <= 1 then 1 else x", tail=""),
    "tail_match_literal_arm": _fn("match o\n    Gray => 1\n    RGB => x", tail=""),
    "arg_if_literal_arm":     _fn("take(if x <= 1 then 1 else x)"),
    # `-1` and `0 - 1` are emitted as `sub 0, 1`, still a constant arm.
    "tail_match_negated_arm": _fn("match o\n    Gray => x\n    RGB => -1", tail=""),
    "let_match_constant_arm": _fn("let n: i32 = match o\n    Gray => x\n    RGB => 0 - 1",
                                  tail="return n"),
    # An `else if` chain is a merge whose arm is itself a merge: §7.5 judges
    # every arm, at any depth (`let` rejected this before #1444 too).
    "tail_else_if_chain":     _fn("if x == 1\n    1\nelse if x == 2\n    x\nelse\n    0", tail=""),
    "tail_else_if_literal_inner": _fn("if x == 1\n    x\nelse if x == 2\n    1\nelse\n    0", tail=""),
    "let_else_if_chain":      _fn("let n: i32 = if x == 1 then 1 else if x == 2 then x else 0",
                                  tail="return n"),
    # Not returned at all: a procedure's tail. An async fn's result is
    # checked at its declared type (R78), so an i64 one takes `big()` whole.
    "procedure_tail":         "fn f()\n    big()\n",
    "void_fn_tail":           "fn f() -> void\n    big()\n",
    "async_fn_result":        "async fn f() -> i64\n    return big()\n",
}

# The merge exemption judges every arm: one wide arm is still a narrowing.
REJECTED["return_if_wide_arm"] = _fn("return if x <= 1 then big() else x", tail="")
REJECTED["arg_if_wide_arm"] = _fn("take(if x <= 1 then big() else x)")
REJECTED["tail_else_if_wide_arm"] = _fn("if x == 1\n    1\nelse if x == 2\n    big()\nelse\n    0",
                                       tail="")
REJECTED["tail_match_unfitting_arm"] = _fn("match o\n    Gray => x\n    RGB => 0 - 4294967296",
                                          tail="")
# Arm by arm applies to a merge written AT the slot. A merge bound to a name is
# that name's type (§7.5: an unannotated local is its initialiser's, an i64
# here), whether the `let` keeps it as an SSA value or a `var` stores it, and
# however the name is read back -- directly or as an arm of a later merge.
# (The `let` forms were accepted by #1444's first cut, which found the bound
# phi by identity; AGAST #1688 pins the unannotated one against ritz1 too.)
_BOUND = "{kw} a{ann} = if x > 0 then x else 0\n"
REJECTED["let_bound_merge_read_back"] = _fn(
    _BOUND.format(kw="let", ann="") + "let n: i32 = a")
REJECTED["var_bound_merge_read_back"] = _fn(
    _BOUND.format(kw="var", ann="") + "let n: i32 = a")
REJECTED["let_i64_bound_merge_read_back"] = _fn(
    _BOUND.format(kw="let", ann=": i64") + "let n: i32 = a")
REJECTED["let_bound_merge_as_arm"] = _fn(
    _BOUND.format(kw="let", ann="") + "return if x > 5 then a else 0", tail="")


# Collected here, after every `REJECTED[...] = ` above: `sorted(REJECTED)` is
# taken when the decorator runs, and the merge rows were once added below it
# and never ran.
@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(REJECTED))
def test_unprovable_narrowing_is_rejected(tmp_path, name):
    r = _compile(tmp_path, REJECTED[name])
    assert r.returncode != 0, f"{name} compiled; it narrows without proof:\n{REJECTED[name]}"
    # The diagnostic itself: a compiler crash through the check must not count.
    assert "implicit narrowing:" in r.stderr and "Traceback" not in r.stderr, (
        f"{name}: rejected, but not by the narrowing diagnostic:\n{r.stderr[-1500:]}")


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_provably_lossless_or_explicit_is_accepted(tmp_path, name):
    r = _compile(tmp_path, ACCEPTED[name])
    assert r.returncode == 0, f"{name} was rejected:\n{ACCEPTED[name]}\n{r.stderr[-1500:]}"
