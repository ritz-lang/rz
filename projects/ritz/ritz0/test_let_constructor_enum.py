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
    "nested_some": _body("let o = Some(Some(5))", "0"),
    "nested_ok": _body("var o = Ok(Err(5))", "0"),
    "pointer_to_pointer": _body("var x: i32 = 5", "var p: *i32 = @x", "let q: **i32 = @p",
                                "let o = Some(q)", "0"),
    "borrow": _body("var x: i32 = 5", "let o = Some(@x)", "0"),
}

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
    subprocess.run(["clang", "-w", str(ll), *extra, "-o", str(exe), "-nostdlib"], check=True)
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
@pytest.mark.parametrize("ctor", ["Ok(5)", "Some(5)"])
def test_ritz1_leaves_a_users_variant_its_own_enum(request, tmp_path, compiler, ctor):
    """A user enum that declares `Ok` / `Some` keeps the slot (#1797): #2430 doesn't
    take it over.  Building that variant is its own bug (#2453): ritz1 builds it as
    the builtin with no enum, which since #2454 is the located refusal, not a zero."""
    variant = ctor.split("(")[0]
    source = f"enum E\n    {variant}(i32)\n    Bad\n" + _body(f"let x = {ctor}", "0")
    proc, ll = _ritz1(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, out[-800:]
    line = source.split("\n").index(f"    let x = {ctor}") + 1
    hits = re.findall(rf"unit\.ritz:{line}:13: {re.escape(_LOCATED)}$", out, re.M)
    assert len(hits) == 1, f"{compiler}: want one located refusal:\n{out[-800:]}"
    assert not ll.exists(), f"{compiler} wrote IR"


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
