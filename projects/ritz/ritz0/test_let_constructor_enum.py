#!/usr/bin/env python3
"""An unannotated `let` bound to a bare constructor is the enum it builds (AGAST #2430).

    fn main() -> i32
        let o = Some(5)
        match o
            Some(v) => v
            _ => 2

The local stayed the parser's default i64, so `Some(5)` had no enum to build,
lowered to `add i64 0, 0 ; variant w/ no enum ctx`, and `match o` read that zero:
exit 0, silently.

The enum is the fn's return type when that is one of the constructor's family
(`Some`/`None` an Option, `Ok`/`Err` a Result), as ritz0 does; otherwise the one the
payload names, as a scrutinee's (#2419): a literal is an `i64`, and a type argument
nothing gives is the same default. A payload ritz1 can't name is a located error.

Other shapes reached the `no enum ctx` fallback (an array literal, an if / match
expression's arms, `a[i] = Some(5)`, `o == None`): #2454.

The expected exit codes come from what each program says, not from a compiler.
ritz0 needs the specialization registered (#2433), so its rows carry _REGISTERED.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
RITZ1S = ["ritz1", "ritz1_selfhosted"]

_MAIN = "fn main() -> i32\n"
_U = "enum Slot\n    Holds(i32)\n    Vacant\n"
_P = "struct Pair\n    a: i32\n    b: i32\n"
_REGISTERED = "fn r0() -> Option<i64>\n    None\nfn r1() -> Result<i64, i64>\n    Ok(1)\n"


def _body(*lines, fn=_MAIN):
    return fn + "".join(f"    {line}\n" for line in lines)


def _bound(kw, ctor, *arms):
    """`kw o = ctor`, then main's value is `match o` over `arms`."""
    return _body(f"{kw} o = {ctor}", "match o", *(f"    {arm}" for arm in arms))


# Each constructor, through `let` and `var`.
BOUND = {}
for _kw in ("let", "var"):
    BOUND.update({
        f"{_kw}_some": (_bound(_kw, "Some(5)", "Some(v) => v", "_ => 2"), 5),
        f"{_kw}_some_none_arm_first": (_bound(_kw, "Some(5)", "None => 2", "Some(v) => v"), 5),
        f"{_kw}_none": (_bound(_kw, "None", "Some(v) => 1", "None => 3"), 3),
        f"{_kw}_ok": (_bound(_kw, "Ok(5)", "Ok(v) => v", "Err(e) => 2"), 5),
        f"{_kw}_err": (_bound(_kw, "Err(5)", "Ok(v) => 1", "Err(e) => e"), 5),
    })

# The payload's type is the enum's.
PAYLOADS = {
    "wider_than_i32": (_body("let x: i64 = 4294967301", "let o = Some(x)", "match o",
                             "    Some(v) => (v / 1073741824) as i32", "    _ => 2"), 4),
    "i32_local": (_body("let x: i32 = 5", "let o = Some(x)", "match o", "    Some(v) => v",
                        "    _ => 2"), 5),
    "u8_local": (_body("let x: u8 = 200", "let o = Some(x)", "match o",
                       "    Some(v) => v as i32", "    _ => 2"), 200),
    "string": (_body('let o = Ok("hello")', "match o", "    Ok(v) => v.len as i32",
                     "    _ => 2"), 5),
    "err_string": (_body('let o = Err("hello")', "match o", "    Err(e) => e.len as i32",
                         "    _ => 2"), 5),
    "float": (_body("let o = Some(2.5)", "match o", "    Some(v) => (v * 2.0) as i32",
                    "    _ => 2"), 5),
    "bool": (_body("let o = Some(true)", "match o", "    Some(v) => v as i32 + 4",
                   "    _ => 2"), 5),
    "struct": (_P + _body("let p = Pair { a: 2, b: 3 }", "let o = Some(p)", "match o",
                          "    Some(v) => v.a + v.b", "    _ => 2"), 5),
    "user_variant": (_U + _body("let o = Some(Holds(5))", "match o", "    Some(v) =>",
                                "        match v", "            Holds(w) => w",
                                "            Vacant => 3", "    _ => 2"), 5),
    # A nested constructor is its own enum's (#2435). Not on ritz0 yet (#3045).
    "nested_some": (_body("let o = Some(Some(5))", "match o", "    Some(v) =>",
                          "        match v", "            Some(w) => w as i32",
                          "            _ => 3", "    _ => 2"), 5),
    "nested_ok": (_body("var o = Ok(Err(5))", "match o", "    Ok(v) =>", "        match v",
                        "            Err(e) => e as i32", "            _ => 3", "    _ => 2"), 5),
}

# The bound value outside a match: passed, returned, reassigned, read twice.
USED = {
    "passed_to_a_fn": (
        "fn h(o: Option<i64>) -> i32\n    match o\n        Some(v) => v as i32\n"
        "        _ => 2\n" + _body("let o = Some(5)", "h(o)"), 5),
    "none_passed_to_a_fn": (
        "fn h(o: Option<i64>) -> i32\n    match o\n        Some(v) => 1\n"
        "        _ => 3\n" + _body("let o = None", "h(o)"), 3),
    "err_passed_to_a_fn": (
        "fn h(r: Result<i64, i64>) -> i32\n    match r\n        Ok(v) => 1\n"
        "        Err(e) => e as i32\n" + _body("var r = Err(5)", "h(r)"), 5),
    "returned_as_the_payloads_enum": (
        "fn f() -> Option<i64>\n    let o = Some(5)\n    o\n"
        + _body("match f()", "    Some(v) => v as i32", "    _ => 2"), 5),
    "returned_as_the_fns_enum": (
        "fn f() -> Option<i32>\n    let o = Some(5)\n    o\n"
        + _body("match f()", "    Some(v) => v", "    _ => 2"), 5),
    "none_returned_as_the_fns_enum": (
        "fn f() -> Option<i32>\n    let o = None\n    o\n"
        + _body("match f()", "    Some(v) => v", "    _ => 3"), 3),
    "err_returned_explicitly": (
        "fn f() -> Result<i32, i32>\n    var r = Err(5)\n    return r\n"
        + _body("match f()", "    Ok(v) => 1", "    Err(e) => e"), 5),
    "a_result_in_an_option_fn": (
        "fn f() -> Option<u8>\n    let r = Ok(5)\n    match r\n        Ok(v) => Some(v as u8)\n"
        "        Err(e) => None\n" + _body("match f()", "    Some(v) => v as i32", "    _ => 2"), 5),
    "an_option_in_a_result_fn": (
        "fn f() -> Result<i32, i32>\n    let o = None\n    match o\n        Some(v) => Err(1)\n"
        "        None => Ok(6)\n" + _body("match f()", "    Ok(v) => v", "    Err(e) => 2"), 6),
    "reassigned": (_body("var o = None", "o = Some(5)", "match o", "    Some(v) => v",
                         "    _ => 2"), 5),
    "copied": (_body("let o = Some(5)", "let p = o", "match p", "    Some(v) => v",
                     "    _ => 2"), 5),
    "matched_twice": (_body("let o = Some(2)", "var r: i32 = 0", "match o",
                            "    Some(v) =>", "        r = v", "    _ =>", "        r = 9",
                            "match o", "    Some(v) => r + v + 1", "    _ => 9"), 5),
    "two_payload_types": (_body("let x: u8 = 2", "let a = Some(x)", "let b = Some(3)",
                                "match a", "    Some(v) =>", "        match b",
                                "            Some(w) => v as i32 + w as i32",
                                "            _ => 8", "    _ => 9"), 5),
    "in_a_method": (
        "struct T\n    x: i32\nimpl T\n    fn m(self: *T) -> i32\n        let o = Some(self.x)\n"
        "        match o\n            Some(v) => v\n            _ => 2\n"
        + _body("let t = T { x: 5 }", "t.m()"), 5),
}

# Neither is a constructor's enum, so neither changes.
UNCHANGED = {
    # A local can't be named `None` (R12, #2407): test_local_takes_module_name.py.
    "const_none": ("const None: i32 = 3\n" + _body("let x = None", "x"), 3),
    "user_payload": (_U + _body("let o = Holds(5)", "match o", "    Holds(v) => v",
                                "    Vacant => 2"), 5),
    "user_unit": (_U + _body("let o = Vacant", "match o", "    Holds(v) => 1",
                             "    Vacant => 3"), 3),
    "typed_let": (_body("let o: Option<i32> = Some(5)", "match o", "    Some(v) => v",
                        "    _ => 2"), 5),
}

RUNS = {**BOUND, **PAYLOADS, **USED, **UNCHANGED}

_LOCATED = "this constructor's type can't be inferred here: bind it with a typed `let` first"

# A payload ritz1 can't name: a located error at the constructor, never the zero.
UNNAMED = {
    "pointer_to_pointer": _body("var x: i32 = 5", "var p: *i32 = @x", "let q: **i32 = @p",
                                "let o = Some(q)", "0"),
    "borrow": _body("var x: i32 = 5", "let o = Some(@x)", "0"),
}

def _users(variant, *lines, fn=_MAIN, second=False):
    """`enum E` declaring `variant(i32)` (after `Bad` if `second`), then `lines`."""
    arms = ["Bad", f"{variant}(i32)"] if second else [f"{variant}(i32)", "Bad"]
    return "enum E\n" + "".join(f"    {a}\n" for a in arms) + _body(*lines, fn=fn)


def _match_e(variant):
    return ["match x", f"    {variant}(v) => v", "    Bad => 2"]


# A user enum declaring a builtin constructor's name (#2453).
USERS = {}
for _v in ("Ok", "Some"):
    USERS.update({
        f"{_v.lower()}_let": (_users(_v, f"let x = {_v}(5)", *_match_e(_v)), 5),
        f"{_v.lower()}_var": (_users(_v, f"var x = {_v}(5)", *_match_e(_v)), 5),
        f"{_v.lower()}_typed_let": (_users(_v, f"let x: E = {_v}(5)", *_match_e(_v)), 5),
        f"{_v.lower()}_not_the_first_variant": (
            _users(_v, f"let x = {_v}(5)", *_match_e(_v), second=True), 5),
        f"{_v.lower()}_argument": (
            "fn h(x: E) -> i32\n" + "".join(f"    {l}\n" for l in _match_e(_v))
            + _users(_v, f"h({_v}(5))"), 5),
    })
USERS.update({
    # In an Option-returning fn ritz1's slot is the user's enum (#1797) and ritz0's
    # the Option (#2513): the let must build whichever its slot is.
    "some_let_in_an_option_fn": (
        _users("Some", "let x = Some(5)", "var r: i32 = 2", "match x", "    Some(v) =>",
               "        r = v", "    _ =>", "        r = 3", "Some(r)",
               fn="fn g() -> Option<i32>\n")
        + _body("match g()", "    Some(v) => v", "    _ => 2"), 5),
    "typed_some_let_in_an_option_fn": (
        _users("Some", "let x: E = Some(5)", "var r: i32 = 2", "match x", "    Some(v) =>",
               "        r = v", "    _ =>", "        r = 3", "Some(r)",
               fn="fn g() -> Option<i32>\n")
        + _body("match g()", "    Some(v) => v", "    _ => 2"), 5),
    # The tail of an Option-returning fn is the builtin.
    "builtin_some_beside_a_users": (
        _users("Some", "Some(7)", fn="fn g() -> Option<i32>\n")
        + _body("match g()", "    Some(v) => v", "    _ => 2"), 7),
    # A builtin scrutinee's arms are the builtin's (#2512): the `Ok` arm named E,
    # so the match was "non-exhaustive: missing Bad".
    "builtin_ok_arm_beside_a_users": (
        _users("Ok", "let r: Result<i32, i32> = Ok(7)", "match r", "    Ok(v) => v",
               "    Err(e) => 2"), 7),
    "builtin_ok_arm_beside_a_users_second": (
        _users("Ok", "let r: Result<i32, i32> = Ok(7)", "match r", "    Ok(v) => v",
               "    Err(e) => 2", second=True), 7),
    "builtin_some_arm_beside_a_users": (
        _users("Some", "let o: Option<i32> = Some(7)", "match o", "    Some(v) => v",
               "    None => 2"), 7),
    "builtin_ok_param_beside_a_users": (
        "fn h(r: Result<i32, i32>) -> i32\n    match r\n        Ok(v) => v\n"
        "        Err(e) => 2\n" + _users("Ok", "h(Ok(7))"), 7),
    # An arm's value is the match's slot (#2512): `Some(v)` built E, so the
    # match's phi was an E over the `None` arm's Option.
    "builtin_some_arm_value_beside_a_users": (
        _users("Some", "let x = Some(5)", "match x", "    Some(v) => Some(v)",
               "    _ => None", fn="fn g() -> Option<i32>\n")
        + _body("match g()", "    Some(v) => v", "    _ => 2"), 5),
    "builtin_some_arm_value_from_an_option": (
        _users("Some", "let x: Option<i32> = Some(5)", "match x", "    Some(v) => Some(v)",
               "    _ => None", fn="fn g() -> Option<i32>\n")
        + _body("match g()", "    Some(v) => v", "    _ => 2"), 5),
    "builtin_ok_arm_value_beside_a_users": (
        _users("Ok", "let x: Result<i32, i32> = Ok(5)", "match x", "    Ok(v) => Ok(v)",
               "    Err(e) => Err(e)", fn="fn g() -> Result<i32, i32>\n")
        + _body("match g()", "    Ok(v) => v", "    Err(e) => 2"), 5),
    # The user's own arms beside them still name E.
    "users_ok_arm_value_in_a_result_fn": (
        _users("Ok", "let x: E = Ok(5)", "match x", "    Ok(v) => Ok(v)",
               "    Bad => Err(2)", fn="fn g() -> Result<i32, i32>\n")
        + _body("match g()", "    Ok(v) => v", "    Err(e) => 3"), 5),
})

_NONE_E = "enum E\n    Some(i32)\n    None\n"


def _users_none(*lines, fn=_MAIN):
    """`enum E` declaring `Some(i32)` and a unit `None`, then `lines`."""
    return _NONE_E + _body(*lines, fn=fn)


_MATCH_NONE = ["match x", "    Some(v) => v", "    None => 7"]
_H_NONE = "fn h(x: E) -> i32\n" + "".join(f"    {line}\n" for line in _MATCH_NONE)

# A user's unit `None` is its own variant where the slot is that enum, and the
# Option's where an Option slot names it (#2434).  ritz1 built every `None` as the
# Option's, so the user's had no Option to build: a located refusal.
USERS.update({
    "none_let": (_users_none("let x = None", *_MATCH_NONE), 7),
    "none_var": (_users_none("var x = None", *_MATCH_NONE), 7),
    "none_typed_let": (_users_none("let x: E = None", *_MATCH_NONE), 7),
    "none_argument": (_H_NONE + _users_none("h(None)"), 7),
    "none_returned": (
        _users_none("None", fn="fn g() -> E\n") + _body("let x = g()", *_MATCH_NONE), 7),
    "none_arm_value": (
        _users_none("match k", "    0 => None", "    _ => Some(5)", fn="fn g(k: i32) -> E\n")
        + _body("let x = g(0)", *_MATCH_NONE), 7),
    # The slot is E in an Option-returning fn: the arm's `None` is E's.
    "none_arm_value_in_an_option_fn": (
        _users_none("let x: E = match k", "    0 => None", "    _ => Some(5)", "match x",
                    "    None => Some(7)", "    _ => Some(3)", fn="fn g(k: i32) -> Option<i32>\n")
        + _body("match g(0)", "    Some(v) => v", "    _ => 2"), 7),
    "none_assigned": (_users_none("var x: E = Some(5)", "x = None", *_MATCH_NONE), 7),
    # In an Option-returning fn the let's slot is the user's enum, as `Some(5)`'s.
    "none_let_in_an_option_fn": (
        _users_none("let x = None", "var r: i32 = 2", "match x", "    None =>",
                    "        r = 7", "    _ =>", "        r = 3", "Some(r)",
                    fn="fn g() -> Option<i32>\n")
        + _body("match g()", "    Some(v) => v", "    _ => 2"), 7),
    # An Option slot keeps the Option's.
    "builtin_none_beside_a_users": (
        _users_none("None", fn="fn g() -> Option<i32>\n")
        + _body("match g()", "    Some(v) => v", "    None => 7"), 7),
    "builtin_none_let_beside_a_users": (
        _users_none("let o: Option<i32> = None", "match o", "    Some(v) => v",
                    "    None => 7"), 7),
    # An arm's value is the match's slot, as #2512's `Some(v)`: the phi was %E.
    "builtin_none_arm_value_beside_a_users": (
        _users_none("match k", "    0 => None", "    _ => Some(5)",
                    fn="fn g(k: i32) -> Option<i32>\n")
        + _body("match g(0)", "    Some(v) => v", "    None => 7"), 7),
    "builtin_none_param_beside_a_users": (
        "fn h(o: Option<i32>) -> i32\n    match o\n        Some(v) => v\n"
        "        None => 7\n" + _users_none("h(None)"), 7),
})

ON_RITZ0 = sorted(BOUND) + ["i32_local", "passed_to_a_fn", "returned_as_the_fns_enum",
                            "none_returned_as_the_fns_enum"]


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


def _run(ll, tmp_path, *extra):
    exe = tmp_path / "unit"
    fast_link.clang(["clang", "-w", str(ll), *extra, "-o", str(exe), "-nostdlib"], check=True)
    return subprocess.run([str(exe)], timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_ritz1_binds_the_enum_the_constructor_built(request, tmp_path, compiler, name):
    source, code = RUNS[name]
    proc, ll = _ritz1(request, compiler, tmp_path, source)
    assert proc.returncode == 0, f"{compiler}, {name}:\n{(proc.stdout + proc.stderr)[-800:]}"
    assert "no enum ctx" not in ll.read_text(), f"{compiler}, {name}: bound a zero"
    assert _run(ll, tmp_path, str(RITZ_START)) == code, f"{compiler}, {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("ctor,enum", [
    ("Some(5)", "Option$i64"),
    ("None", "Option$i64"),
    ("Ok(5)", "Result$i64$i64"),
    ("Err(5)", "Result$i64$i64"),
    ('Ok("x")', "Result$StrView$i64"),
    ("Some(2.5)", "Option$f64"),
])
def test_ritz1_types_the_local_by_the_payload(request, tmp_path, compiler, ctor, enum):
    proc, ll = _ritz1(request, compiler, tmp_path, _body(f"let o = {ctor}", "0"))
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-800:]
    ir = ll.read_text()
    assert re.search(rf"= alloca %{re.escape(enum)}\b", ir), ir[-1500:]
    assert len(re.findall(rf"^%{re.escape(enum)} = type ", ir, re.M)) == 1, ir[:800]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(USERS))
def test_ritz1_builds_a_users_variant_as_its_own_enum(request, tmp_path, compiler, name):
    """A user enum that declares `Ok` / `Some` keeps the slot (#1797) and builds it
    (#2453): ritz1 sent the call to the builtin path, which had no enum (the zero,
    then #2454's located refusal).  An Option / Result slot keeps the builtin, and
    so does an Option / Result scrutinee's arm and an arm value that slot built
    (#2512)."""
    source, code = USERS[name]
    proc, ll = _ritz1(request, compiler, tmp_path, source)
    assert proc.returncode == 0, f"{compiler}, {name}:\n{(proc.stdout + proc.stderr)[-800:]}"
    assert "constructor with no enum" not in ll.read_text(), f"{compiler}, {name}"
    assert _run(ll, tmp_path, str(RITZ_START)) == code, f"{compiler}, {name}"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(USERS))
def test_ritz0_builds_a_users_variant_the_same(tmp_path, name):
    source, code = USERS[name]
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    assert proc.returncode == 0, f"{name}:\n{(proc.stdout + proc.stderr)[-1500:]}"
    assert _run(ll, tmp_path) == code, name


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(UNNAMED))
def test_ritz1_refuses_a_bound_payload_it_cannot_name(request, tmp_path, compiler, name):
    source = UNNAMED[name]
    proc, ll = _ritz1(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-800:]}"
    lines = source.split("\n")
    line = next(i for i, text in enumerate(lines, 1) if " o = " in text)
    col = lines[line - 1].index("= ") + 3
    hits = re.findall(rf"unit\.ritz:{line}:{col}: {re.escape(_LOCATED)}$", out, re.M)
    assert len(hits) == 1, f"{compiler}, {name}: want one located refusal:\n{out[-800:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


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
    assert _run(ll, tmp_path) == code, name
