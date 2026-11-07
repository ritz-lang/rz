#!/usr/bin/env python3
"""A bare constructor is a match scrutinee like any other (AGAST #2419).

    match Some(5)
        Some(v) => v
        _ => 2

`Some(5)` names no enum, so ritz1 found none, lowered it to `add i64 0, 0` and
matched on that zero: exit 0, silently. `None` took the `Some` arm and `Err(5)` the
`Ok` arm, since their tags were read from the same zero.

The enum comes from the payload, so it can't depend on what else the module says:
`Some(5)` is `Option<i64>` (a literal is an `i64`, LANGUAGE_SPEC §4), and a type
argument nothing gives, as in `None` or `Ok(5)`'s `E`, is the same default. The
enclosing fn or `let` has no say: the scrutinee isn't its value.

The expected exit codes come from what each program says, not from a compiler.
ritz0 reuses a specialization the module already registered and has none to reuse
without one (#2433), so its rows carry _REGISTERED.

A nested match is an arm's tail, which is its value (#2429). The types are `Pair`
and `Slot` because `Option<P>` is never declared (#2432).
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
RITZ1S = ["ritz1", "ritz1_selfhosted"]

_MAIN = "fn main() -> i32\n"
_U = "enum Slot\n    Holds(i32)\n    Vacant\n"
_P = "struct Pair\n    a: i32\n    b: i32\n"
_T = (_P + "struct T\n    x: i32\n    f: f32\n    q: *i32\nimpl T\n    fn n(self: *T) -> i32\n"
      "        5\n    fn u(self: *T) -> u8\n        200\n    fn m(self: *T) -> Pair\n"
      "        Pair { a: 2, b: 3 }\n")
_T_LOCAL = "var i: i32 = 5\nlet t = T { x: 5, f: 2.5, q: @i }"
_REGISTERED = "fn r0() -> Option<i64>\n    None\nfn r1() -> Result<i64, i64>\n    Ok(1)\n"


def _on(scrutinee, *arms, before=""):
    """`match scrutinee` with `arms`, as main's value, after `before`'s statements."""
    lines = [f"    {line}\n" for line in before.split("\n") if line]
    return (_MAIN + "".join(lines) + f"    match {scrutinee}\n"
            + "".join(f"        {arm}\n" for arm in arms))


# Each of the four, whichever arm comes first.
VARIANTS = {
    "some": (_on("Some(5)", "Some(v) => v", "_ => 2"), 5),
    "some_both_arms": (_on("Some(5)", "Some(v) => v", "None => 2"), 5),
    "some_after_none": (_on("Some(5)", "None => 2", "Some(v) => v"), 5),
    "none": (_on("None", "Some(v) => 1", "None => 3"), 3),
    "none_by_wildcard": (_on("None", "Some(v) => 1", "_ => 3"), 3),
    "ok": (_on("Ok(5)", "Ok(v) => v", "Err(e) => 2"), 5),
    "ok_by_wildcard": (_on("Ok(5)", "Ok(v) => v", "_ => 2"), 5),
    "err": (_on("Err(5)", "Ok(v) => 1", "Err(e) => e"), 5),
    "err_after_wildcard_arm": (_on("Err(5)", "Err(e) => e", "_ => 1"), 5),
    "in_parens": (_on("(Some(5))", "Some(v) => v", "_ => 2"), 5),
    "borrowed": (_on("@Some(5)", "Some(v) => v", "_ => 2"), 5),
    "as_a_statement": (_MAIN + "    var r: i32 = 0\n    match Some(5)\n        Some(v) =>\n"
                       "            r = v\n        _ =>\n            r = 2\n    r\n", 5),
    # None of these read the value, so they ran before.
    "only_a_wildcard": (_on("Some(5)", "_ => 7"), 7),
    "none_only_a_wildcard": (_on("None", "_ => 3"), 3),
    "a_name_takes_it": (_on("Some(5)", "x => 7"), 7),
}

# The payload's type is the enum's: each would lose its value in the wrong one.
PAYLOADS = {
    "wider_than_i32": (_on("Some(x)", "Some(v) => (v / 1073741824) as i32", "_ => 2",
                           before="let x: i64 = 4294967301"), 4),
    "i32_local": (_on("Some(x)", "Some(v) => v", "_ => 2", before="let x: i32 = 5"), 5),
    "negative_i32": (_on("Some(x)", "Some(v) => (0 - v) as i32", "_ => 2",
                         before="let x: i32 = -5"), 5),
    "u8_local": (_on("Some(x)", "Some(v) => v as i32", "_ => 2", before="let x: u8 = 200"), 200),
    "call": ("fn g() -> i32\n    5\n" + _on("Some(g())", "Some(v) => v", "_ => 2"), 5),
    "err_call": ("fn g() -> i32\n    5\n" + _on("Err(g())", "Err(e) => e", "_ => 2"), 5),
    "sum": (_on("Some(x + 1)", "Some(v) => v", "_ => 2", before="let x: i32 = 4"), 5),
    "bool": (_on("Some(true)", "Some(v) => v as i32 + 4", "_ => 2"), 5),
    "float": (_on("Some(2.5)", "Some(v) => (v * 2.0) as i32", "_ => 2"), 5),
    "string": (_on('Some("hello")', "Some(v) => v.len as i32", "_ => 2"), 5),
    "ok_string": (_on('Ok("hello")', "Ok(v) => v.len as i32", "_ => 2"), 5),
    "err_string": (_on('Err("hello")', "Err(e) => e.len as i32", "_ => 2"), 5),
    "struct": (_P + _on("Some(p)", "Some(v) => v.a + v.b", "_ => 2",
                        before="let p = Pair { a: 2, b: 3 }"), 5),
    "struct_literal": (_P + _on("Some(Pair { a: 2, b: 3 })", "Some(v) => v.a + v.b", "_ => 2"), 5),
    "struct_call": (_P + "fn g() -> Pair\n    Pair { a: 2, b: 3 }\n"
                    + _on("Some(g())", "Some(v) => v.a + v.b", "_ => 2"), 5),
    "struct_field": (_P + "struct H\n    p: Pair\n"
                     + _on("Some(h.p)", "Some(v) => v.a + v.b", "_ => 2",
                           before="let h = H { p: Pair { a: 2, b: 3 } }"), 5),
    "pointer": (_on("Some(p)", "Some(v) => *v", "_ => 2",
                    before="var x: i32 = 5\nlet p: *i32 = @x"), 5),
    "pointer_to_struct": (_P + _on("Some(q)", "Some(v) => (v == q) as i32 + 4", "_ => 2",
                                   before="var p = Pair { a: 2, b: 3 }\nlet q: *Pair = @p"), 5),
    "method_i32": (_T + _on("Some(t.n())", "Some(v) => v", "_ => 2", before=_T_LOCAL), 5),
    "method_u8": (_T + _on("Some(t.u())", "Some(v) => v as i32", "_ => 2", before=_T_LOCAL), 200),
    "field_i32": (_T + _on("Some(t.x)", "Some(v) => v", "_ => 2", before=_T_LOCAL), 5),
    "field_f32": (_T + _on("Some(t.f)", "Some(v) => (v * 2.0) as i32", "_ => 2",
                           before=_T_LOCAL), 5),
    "element": (_on("Some(a[1])", "Some(v) => v", "_ => 2", before="var a: [2]i32\na[1] = 5"), 5),
    "deref": (_on("Some(*p)", "Some(v) => v", "_ => 2",
                  before="var x: i32 = 5\nlet p: *i32 = @x"), 5),
    "char": (_on("Some('a')", "Some(v) => v as i32", "_ => 2"), 97),
    "const": ("const K: i32 = 5\n" + _on("Some(K)", "Some(v) => v", "_ => 2"), 5),
    "c_string": (_on('Some(c"hello")', "Some(v) => (*v) as i32", "_ => 2"), 104),
    "strview_local": (_on("Some(x)", "Some(v) => v.len as i32", "_ => 2",
                          before='let x: StrView = "hello"'), 5),
    "u16_local": (_on("Some(x)", "Some(v) => v as i32", "_ => 2", before="let x: u16 = 60000"),
                  60000 % 256),
    "f32_local": (_on("Some(x)", "Some(v) => (v * 2.0) as i32", "_ => 2",
                      before="let x: f32 = 2.5"), 5),
    "comparison": (_on("Some(x == 5)", "Some(v) => v as i32 + 4", "_ => 2",
                       before="let x: i32 = 5"), 5),
    "bool_local": (_on("Some(x)", "Some(v) => v as i32 + 4", "_ => 2",
                       before="let x: bool = true"), 5),
    "if_expression": (_on("Some(if x > 1 then 5 else 6)", "Some(v) => v", "_ => 2",
                          before="let x: i32 = 2"), 5),
    "struct_param": (_P + "fn f(p: Pair) -> i32\n    match Some(p)\n        Some(v) => v.a + v.b\n"
                     "        _ => 2\n" + _MAIN + "    f(Pair { a: 2, b: 3 })\n", 5),
    "user_variant": (_U + _MAIN + "    match Some(Holds(5))\n        Some(v) =>\n"
                  "            match v\n                Holds(w) => w\n                Vacant => 3\n"
                  "        _ => 2\n", 5),
    "user_unit_variant": (_U + _MAIN + "    match Some(Vacant)\n        Some(v) =>\n"
                  "            match v\n                Holds(w) => 1\n                Vacant => 3\n"
                  "        _ => 2\n", 3),
    "qualified_variant": (_U + _MAIN + "    match Some(Slot.Holds(5))\n        Some(v) =>\n"
                  "            match v\n                Holds(w) => w\n                Vacant => 3\n"
                  "        _ => 2\n", 5),
    "user_enum_local": (_U + _MAIN + "    let u: Slot = Slot.Holds(5)\n    match Some(u)\n        Some(v) =>\n"
                  "            match v\n                Holds(w) => w\n                Vacant => 3\n"
                  "        _ => 2\n", 5),
}

# The enum around the match is another one, and the scrutinee isn't its value.
AROUND = {
    "fn_returns_that_option": (
        "fn f() -> Option<i32>\n    match Some(5)\n        Some(v) => Some(v as i32 + 1)\n"
        "        _ => None\n" + _on("f()", "Some(v) => v", "_ => 2"), 6),
    "fn_returns_another_option": (
        "fn f() -> Option<u8>\n    match Some(500)\n        Some(v) => Some((v / 100) as u8)\n"
        "        _ => None\n" + _on("f()", "Some(v) => v as i32", "_ => 2"), 5),
    "fn_returns_a_result": (
        "fn f() -> Result<i32, i32>\n    match Some(5)\n        Some(v) => Ok(v as i32 + 1)\n"
        "        _ => Err(1)\n" + _on("f()", "Ok(v) => v", "Err(e) => 2"), 6),
    "none_in_a_result_fn": (
        "fn f() -> Result<i32, i32>\n    match None\n        Some(v) => Err(1)\n"
        "        None => Ok(6)\n" + _on("f()", "Ok(v) => v", "Err(e) => 2"), 6),
    "ok_in_a_result_fn": (
        "fn f() -> Result<i32, i32>\n    match Ok(5)\n        Ok(v) => Ok(v as i32 + 1)\n"
        "        Err(e) => Err(1)\n" + _on("f()", "Ok(v) => v", "Err(e) => 2"), 6),
    "typed_let_of_a_result": (
        _MAIN + "    let r: Result<i32, i32> = match Some(5)\n        Some(v) => Ok(v as i32)\n"
        "        _ => Err(1)\n    match r\n        Ok(v) => v\n        Err(e) => 2\n", 5),
    "inside_a_call_argument": (
        "fn h(o: Option<i32>, n: i64) -> i32\n    n as i32\n" + _MAIN
        + "    let n: i64 = 5\n    h(None, n)\n", 5),
    "nested_match": (
        _MAIN + "    match Some(5)\n        Some(v) =>\n"
        "            match Err(v)\n                Err(e) => e as i32\n"
        "                _ => 3\n        _ => 2\n", 5),
    "two_payload_types_in_one_fn": (
        _MAIN + "    let x: u8 = 2\n    var r: i32 = 0\n    match Some(x)\n"
        "        Some(v) =>\n            r = v as i32\n        _ =>\n            r = 9\n"
        "    match Some(3)\n        Some(v) =>\n            r = r + v as i32\n"
        "        _ =>\n            r = 9\n    r\n", 5),
    "in_a_generic_fn": (
        "fn f<T>(x: T) -> i32\n    match Some(x)\n        Some(v) => 5\n        _ => 2\n"
        + _MAIN + "    f<i32>(1)\n", 5),
    "in_a_method": (
        "struct T\n    x: i32\nimpl T\n    fn m(self: *T) -> i32\n        match Some(self.x)\n"
        "            Some(v) => v\n            _ => 2\n"
        + _on("t.m()", "5 => 5", "_ => 2", before="let t = T { x: 5 }"), 5),
}

# A user's unit variant, unqualified, is the same case.
USER = {
    "user_unit": (_U + _on("Vacant", "Holds(v) => 1", "Vacant => 3"), 3),
    "user_unit_first": (_U + _on("Vacant", "Vacant => 3", "Holds(v) => 1"), 3),
    "user_unit_by_wildcard": (_U + _on("Vacant", "Holds(v) => 1", "_ => 3"), 3),
    "user_unit_borrowed": (_U + _on("@Vacant", "Holds(v) => 1", "Vacant => 3"), 3),
    # These ran, and must still.
    "user_payload": (_U + _on("Holds(5)", "Holds(v) => v", "Vacant => 2"), 5),
    "user_qualified": (_U + _on("Slot.Holds(5)", "Holds(v) => v", "Vacant => 2"), 5),
    "user_qualified_unit": (_U + _on("Slot.Vacant", "Holds(v) => 1", "Vacant => 3"), 3),
}

# `None` is a name first.
SHADOWED = {
    "const_none": ("const None: i32 = 3\n" + _on("None", "3 => 3", "_ => 1"), 3),
    "local_none": (_on("None", "3 => 3", "_ => 1", before="let None: i32 = 3"), 3),
    "global_none": ("var None: i32\n" + _on("None", "0 => 3", "_ => 1"), 3),
}

RUNS = {**VARIANTS, **PAYLOADS, **AROUND, **USER, **SHADOWED}

# What a scrutinee refuses is what any Option's does: (source, line, col, message).
_LOCATED = "this constructor's type can't be inferred here: bind it with a typed `let` first"
REFUSED = {
    "missing_none": (_on("Some(5)", "Some(v) => v"), 2, 5,
                     "error: non-exhaustive match: missing None"),
    "missing_some": (_on("None", "None => 3"), 2, 5,
                     "error: non-exhaustive match: missing Some"),
    "missing_err": (_on("Ok(5)", "Ok(v) => v"), 2, 5,
                    "error: non-exhaustive match: missing Err"),
    "missing_ok": (_on("Err(5)", "Err(e) => e"), 2, 5,
                   "error: non-exhaustive match: missing Ok"),
}

# A payload ritz1 can't name, or build: never the zero it used to match on. A nested
# constructor runs once it can be built at all (#2435).
UNNAMED = {
    "nested_some": _on("Some(Some(5))", "Some(v) => 1", "_ => 2"),
    "nested_none": _on("Some(None)", "Some(v) => 1", "_ => 2"),
    "nested_ok": _on("Ok(Err(5))", "Ok(v) => 1", "_ => 2"),
    "pointer_to_pointer": _on("Some(q)", "Some(v) => 1", "_ => 2",
                              before="var x: i32 = 5\nvar p: *i32 = @x\nlet q: **i32 = @p"),
    "method_struct": _T + _on("Some(t.m())", "Some(v) => 7", "_ => 2", before=_T_LOCAL),
    "element_struct": _P + _on("Some(a[1])", "Some(v) => 7", "_ => 2", before="var a: [2]Pair"),
    "deref_struct": _P + _on("Some(*p)", "Some(v) => 7", "_ => 2",
                             before="var x = Pair { a: 2, b: 3 }\nlet p: *Pair = @x"),
    "global_struct": _P + "var G: Pair\n" + _on("Some(G)", "Some(v) => 7", "_ => 2"),
    "pointer_field": _T + _on("Some(t.q)", "Some(v) => 7", "_ => 2", before=_T_LOCAL),
    "pointer_call": "fn g() -> *i32\n    null\n" + _on("Some(g())", "Some(v) => 7", "_ => 2"),
    "borrow": _on("Some(@x)", "Some(v) => 7", "_ => 2", before="var x: i32 = 5"),
    "null": _on("Some(null)", "Some(v) => 7", "_ => 2"),
    "array": _on("Some(a)", "Some(v) => 7", "_ => 2", before="var a: [2]i32"),
}

# A user's `None` is that enum's, which emit_expr_ident can't build (#2434). Refused,
# as it was: read as the Option's it took `Yes(v)`, on the shared tag.
USERS_NONE = {
    "one_enum": "enum Mine\n    Yes(i32)\n    None\n" + _on("None", "Yes(v) => 1", "None => 3"),
    "two_enums": "enum A1\n    Yes(i32)\n    None\nenum B1\n    Nay\n    None\n"
                 + _on("None", "Yes(v) => 1", "_ => 3"),
}

# The match owns what it built, as it owns a call's value (#2174): one drop, whichever
# arm takes it. `DROPS` is main's exit code. ritz0 leaks each constructor here (#2433).
_OWN = ("var DROPS: i32 = 0\nstruct Tracked\n    id: i32\nimpl Drop for Tracked\n"
        "    fn drop(self: @&Tracked)\n        DROPS = DROPS + 1\n"
        "fn make(i: i32) -> Tracked\n    Tracked { id: i }\n"
        "fn eat(t: Tracked) -> i32\n    t.id\n"
        "fn mk() -> Option<Tracked>\n    Some(make(1))\n"
        "enum Full1\n    Full(Tracked)\n    Empty\n")


def _dropped(*body):
    return (_OWN + "fn go() -> i32\n" + "".join(f"    {line}\n" for line in body)
            + _MAIN + "    go()\n    DROPS\n")


def _arms(scrutinee, *arms):
    return ("match " + scrutinee, *(f"    {arm}" for arm in arms))


OWNED = {
    "bound": (_dropped(*_arms("Some(make(1))", "Some(v) => v.id", "_ => 2")), 1),
    "wildcard": (_dropped(*_arms("Some(make(1))", "_ => 2")), 1),
    "a_name": (_dropped(*_arms("Some(make(1))", "x => 2")), 1),
    "other_arm_first": (_dropped(*_arms("Some(make(1))", "None => 2", "Some(v) => 3")), 1),
    "arm_consumes": (_dropped(*_arms("Some(make(1))", "Some(v) => eat(v)", "_ => 2")), 1),
    "moved_local_bound": (_dropped("let t = make(1)",
                                   *_arms("Some(t)", "Some(v) => v.id", "_ => 2")), 1),
    "moved_local_wildcard": (_dropped("let t = make(1)", *_arms("Some(t)", "_ => 2")), 1),
    "ok_bound": (_dropped(*_arms("Ok(make(1))", "Ok(v) => v.id", "Err(e) => 2")), 1),
    "ok_wildcard": (_dropped(*_arms("Ok(make(1))", "_ => 2")), 1),
    "err_bound": (_dropped(*_arms("Err(make(1))", "Err(e) => e.id", "_ => 2")), 1),
    "err_wildcard": (_dropped(*_arms("Err(make(1))", "_ => 2")), 1),
    "returning_arm": (_dropped(*_arms("Some(make(1))", "Some(v) =>", "    return 1", "_ =>",
                                      "    return 2")), 1),
    "borrowed": (_dropped(*_arms("@Some(make(1))", "_ => 2")), 1),
    "none_holds_nothing": (_dropped(*_arms("None", "Some(v) => 1", "None => 2")), 0),
    "user_ctor_bound": (_dropped(*_arms("Full(make(1))", "Full(v) => v.id", "Empty => 2")), 1),
    "user_ctor_wildcard": (_dropped(*_arms("Full(make(1))", "_ => 2")), 1),
    "qualified_wildcard": (_dropped(*_arms("Full1.Full(make(1))", "_ => 2")), 1),
    # What it's held to.
    "a_call": (_dropped(*_arms("mk()", "_ => 2")), 1),
    "a_typed_local": (_dropped("let o: Option<Tracked> = Some(make(1))",
                               *_arms("o", "_ => 2")), 1),
}

# ritz0 runs these once the module has registered the specialization.
ON_RITZ0 = sorted(set(VARIANTS) - {"as_a_statement"}) + [
    "user_unit", "user_payload", "user_qualified", "user_qualified_unit", "wider_than_i32",
    "call", "err_call"]


def _ritz1(request, compiler, tmp_path, source):
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=300)
    return proc, ll


def _run_ritz1(ll, tmp_path):
    exe = tmp_path / "unit"
    subprocess.run(["clang", "-w", str(ll), str(RITZ_START), "-o", str(exe), "-nostdlib"],
                   check=True)
    return subprocess.run([str(exe)], timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_ritz1_matches_on_what_the_scrutinee_built(request, tmp_path, compiler, name):
    source, code = RUNS[name]
    proc, ll = _ritz1(request, compiler, tmp_path, source)
    assert proc.returncode == 0, f"{compiler}, {name}:\n{(proc.stdout + proc.stderr)[-800:]}"
    assert "no enum ctx" not in ll.read_text(), f"{compiler}, {name}: matched on a zero"
    assert _run_ritz1(ll, tmp_path) == code, f"{compiler}, {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(OWNED))
def test_ritz1_drops_what_the_scrutinee_built_once(request, tmp_path, compiler, name):
    source, drops = OWNED[name]
    proc, ll = _ritz1(request, compiler, tmp_path, source)
    assert proc.returncode == 0, f"{compiler}, {name}:\n{(proc.stdout + proc.stderr)[-800:]}"
    assert _run_ritz1(ll, tmp_path) == drops, f"{compiler}, {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_ritz1_moves_a_local_into_the_scrutinee(request, tmp_path, compiler):
    source = _dropped("let t = make(1)", *_arms("Some(t)", "_ => 2"), "t.id")
    proc, ll = _ritz1(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0 and "use of moved value: `t`" in out, out[-800:]
    assert not ll.exists()


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("scrutinee,arm,enum", [
    ("Some(5)", "Some(v)", "Option$i64"),
    ("None", "Some(v)", "Option$i64"),
    ("Ok(5)", "Ok(v)", "Result$i64$i64"),
    ("Err(5)", "Ok(v)", "Result$i64$i64"),
    ('Ok("x")', "Ok(v)", "Result$StrView$i64"),
    ('Err("x")', "Ok(v)", "Result$i64$StrView"),
    ("Some(2.5)", "Some(v)", "Option$f64"),
    ("Some(true)", "Some(v)", "Option$bool"),
])
def test_ritz1_names_the_enum_by_the_payload_alone(request, tmp_path, compiler, scrutinee,
                                                   arm, enum):
    # A fn whose return type says otherwise, as it did to the constructor.
    source = (f"fn f() -> Option<u8>\n    match {scrutinee}\n        {arm} => None\n"
              "        _ => None\n" + _MAIN + "    0\n")
    proc, ll = _ritz1(request, compiler, tmp_path, source)
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-800:]
    ir = ll.read_text()
    assert f'alloca %{enum}  ; match scrut spill' in ir, ir[-1500:]
    # Declared once, and only because the match spelled it.
    assert len(re.findall(rf"^%{re.escape(enum)} = type ", ir, re.M)) == 1, ir[:800]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_ritz1_declares_an_enum_the_module_also_names_once(request, tmp_path, compiler):
    source = ("fn g() -> Option<i64>\n    None\n" + _on("Some(5)", "Some(v) => v", "_ => 2"))
    proc, ll = _ritz1(request, compiler, tmp_path, source)
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-800:]
    assert len(re.findall(r"^%Option\$i64 = type ", ll.read_text(), re.M)) == 1
    assert _run_ritz1(ll, tmp_path) == 5


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_ritz1_holds_a_constructor_scrutinee_to_coverage(request, tmp_path, compiler, name):
    source, line, col, message = REFUSED[name]
    proc, ll = _ritz1(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-800:]}"
    hits = re.findall(rf"unit\.ritz:{line}:{col}: {re.escape(message)}$", out, re.M)
    assert len(hits) == 1, f"{compiler}, {name}: want one {message!r}:\n{out[-800:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(UNNAMED))
def test_ritz1_refuses_a_payload_it_cannot_name(request, tmp_path, compiler, name):
    proc, ll = _ritz1(request, compiler, tmp_path, UNNAMED[name])
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-800:]}"
    line = UNNAMED[name].split("\n").index(next(
        text for text in UNNAMED[name].split("\n") if text.startswith("    match "))) + 1
    hits = re.findall(rf"unit\.ritz:{line}:\d+: {re.escape(_LOCATED)}$", out, re.M)
    assert len(hits) == 1, f"{compiler}, {name}: want one located refusal:\n{out[-800:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(USERS_NONE))
def test_ritz1_never_reads_a_users_none_as_the_options(request, tmp_path, compiler, name):
    proc, ll = _ritz1(request, compiler, tmp_path, USERS_NONE[name])
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-800:]}"
    assert "cannot take address of match scrutinee" in out, out[-800:]
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("source", [
    pytest.param(_on("Some(5)", "Ok(v) => v", "_ => 2"), id="ok_arm_on_an_option"),
    pytest.param(_on("Ok(5)", "Some(v) => v", "_ => 2"), id="some_arm_on_a_result"),
])
def test_ritz1_treats_a_foreign_arm_as_on_any_option(request, tmp_path, compiler, source):
    """The arm reads as it does on a typed local: `o`, below, is the same enum (#2431)."""
    typed = source.replace("match Some(5)", "match o").replace("match Ok(5)", "match o")
    ty = "Option<i64>" if "Some(5)" in source else "Result<i64, i64>"
    ctor = "Some(5)" if "Some(5)" in source else "Ok(5)"
    typed = typed.replace(_MAIN, f"{_MAIN}    let o: {ty} = {ctor}\n")
    bare, _ = _ritz1(request, compiler, tmp_path, source)
    named, _ = _ritz1(request, compiler, tmp_path, typed)
    assert (bare.returncode == 0) == (named.returncode == 0), (bare.stderr, named.stderr)


@pytest.mark.integration
@pytest.mark.parametrize("name", ON_RITZ0)
def test_ritz0_gives_each_row_the_same_answer(tmp_path, name):
    source, code = RUNS[name]
    src = tmp_path / "unit.ritz"
    src.write_text(_REGISTERED + source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    assert proc.returncode == 0, f"{name}:\n{(proc.stdout + proc.stderr)[-1500:]}"
    exe = tmp_path / "unit"
    subprocess.run(["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"], check=True)
    assert subprocess.run([str(exe)], timeout=60).returncode == code, name
