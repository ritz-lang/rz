#!/usr/bin/env python3
"""Every bare constructor ritz1 builds has an enum, or is a located error (AGAST #2454).

`Some(5)`, `None`, `Ok(5)` or `Err(5)` with no enum to build lowered to

    %.N = add i64 0, 0  ; variant w/ no enum ctx

and ran on that zero.  #2430 fixed the untyped `let o = Some(5)`; these were left:

1. an array literal, `let a: [2]Option<i32> = [Some(5), None]`: exit 1 for 5;
2. an if expression's arms, `let o = if c then Some(5) else None`: exit 0 for 5;
3. a match expression's arms, under an untyped let: exit 0 for 5;
4. `a[i] = Some(5)` into an `[N]Option<T>`: exit 1 for 5;
5. `o == None` on an Option: compiled.  ritz0 refuses `==` on a payload enum;
6. `Some(5)` as a statement: its value is discarded, but it was still the fallback.

1 and 4 take the element's type, as a field (#2142) does.  2 and 3 take the enum
the arms build: the fn's return type when it is their family, as #2430's let does,
otherwise the one their payloads name (#2419): an Option's T from its first `Some`,
a Result's T and E from its first `Ok` and first `Err`, i64 where none gives one.
5 is ritz0's refusal.  6 builds the enum its payload names.

With every caller given one, the fallback is a located error: a constructor in an
`i64` slot is refused at the constructor, never stored as a zero.

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
_REGISTERED = "fn r0() -> Option<i64>\n    None\nfn r1() -> Result<i64, i64>\n    Ok(1)\n"


def _body(*lines, fn=_MAIN):
    return fn + "".join(f"    {line}\n" for line in lines)


def _match(scr, *arms):
    return [f"match {scr}", *(f"    {arm}" for arm in arms)]


_SOME = ("Some(v) => v", "_ => 2")
_NONE = ("Some(v) => 1", "None => 3")

# 1: an array literal's elements build the element's enum.
ARRAY_LITERAL = {
    "array_literal": (_body("let a: [2]Option<i32> = [Some(5), None]", *_match("a[0]", *_SOME)), 5),
    "array_literal_none": (_body("let a: [2]Option<i32> = [Some(5), None]",
                                 *_match("a[1]", *_NONE)), 3),
    "array_literal_none_first": (_body("var a: [2]Option<i32> = [None, Some(5)]",
                                       *_match("a[1]", *_SOME)), 5),
    "array_literal_result": (_body("let a: [2]Result<i32, i32> = [Err(5), Ok(1)]",
                                   *_match("a[0]", "Ok(v) => 1", "Err(e) => e")), 5),
    "array_literal_u8": (_body("let a: [2]Option<u8> = [None, Some(200)]",
                               *_match("a[1]", "Some(v) => v as i32", "_ => 2")), 200),
}

# 4: `a[i] = ctor` builds the element's enum: a local, a struct field and a global.
_W = "struct W\n    a: [2]Option<i32>\n"
_G = "var g: [2]Option<i32>\n"
INDEX_ASSIGN = {
    "index_assign": (_body("var a: [2]Option<i32>", "a[1] = Some(5)", *_match("a[1]", *_SOME)), 5),
    "index_assign_none": (_body("var a: [2]Option<i32> = [Some(1), Some(2)]", "a[0] = None",
                                *_match("a[0]", *_NONE)), 3),
    "index_assign_err": (_body("var a: [2]Result<i32, i32>", "a[1] = Err(5)",
                               *_match("a[1]", "Ok(v) => 1", "Err(e) => e")), 5),
    "field_index_assign": (_W + _body("var w: W", "w.a[1] = Some(5)",
                                      *_match("w.a[1]", *_SOME)), 5),
    "global_index_assign": (_G + _body("g[1] = Some(5)", *_match("g[1]", *_SOME)), 5),
    "field_index_assign_through_a_pointer": (
        _W + "fn set(w: *W)\n    w.a[1] = Some(5)\n"
        + _body("var w: W", "set(@w)", *_match("w.a[1]", *_SOME)), 5),
    "nested_field_index_assign": (
        _W + "struct V\n    w: W\n"
        + _body("var n: V", "n.w.a[1] = Some(5)", *_match("n.w.a[1]", *_SOME)), 5),
    # Not an index, but the same undeclared `%Option$i32`: a global's own type.
    "global_option": ("var h: Option<i32>\n" + _body("h = Some(5)", *_match("h", *_SOME)), 5),
}

# 2, 3: an if / match expression's arms build one enum, named by the arms.
ARMS = {
    "if_some": (_body("let o = if true then Some(5) else None", *_match("o", *_SOME)), 5),
    "if_none": (_body("let o = if false then Some(5) else None", *_match("o", *_NONE)), 3),
    "if_none_arm_first": (_body("let o = if false then None else Some(5)",
                                *_match("o", *_SOME)), 5),
    "if_else_if": (_body("let o = if false then None else if true then Some(5) else None",
                         *_match("o", *_SOME)), 5),
    "if_u8_payload": (_body("let x: u8 = 200", "let o = if true then Some(x) else None",
                            *_match("o", "Some(v) => v as i32", "_ => 2")), 200),
    "if_var": (_body("var o = if true then Some(5) else None", *_match("o", *_SOME)), 5),
    "if_ok": (_body("let r = if true then Ok(5) else Err(2)",
                    *_match("r", "Ok(v) => v as i32", "Err(e) => 2")), 5),
    # Err's payload names E, not the first arm's T.
    "if_err_names_its_own_payload": (
        _body('let r = if false then Ok(5) else Err("abc")',
              *_match("r", "Ok(v) => 1", "Err(e) => e.len as i32")), 3),
    "match_some": (_body("let o = match 1", "    1 => Some(5)", "    _ => None",
                         *_match("o", *_SOME)), 5),
    "match_none": (_body("let o = match 2", "    1 => Some(5)", "    _ => None",
                         *_match("o", *_NONE)), 3),
    "match_block_arm": (_body("let o = match 1", "    1 =>", "        let x: i64 = 4",
                              "        Some(x + 1)", "    _ => None", *_match("o", *_SOME)), 5),
    # The fn's return type is the arms' family: `o` is that enum, as #2430's let.
    "if_returned_as_the_fns_enum": (
        "fn f(c: i32) -> Option<i32>\n    let o = if c == 1 then Some(5) else None\n    o\n"
        + _body(*_match("f(1)", *_SOME)), 5),
}

# 6: a constructor statement builds the enum its payload names; the value is dropped.
STATEMENT = {
    "some_statement": (_body("Some(5)", "5"), 5),
    "ok_statement": (_body("Ok(5)", "5"), 5),
    # The fn's own enum, when it is the constructor's family.
    "tail_in_an_option_fn": ("fn f() -> Option<i32>\n    Some(5)\n"
                             + _body(*_match("f()", *_SOME)), 5),
    "branch_tail_in_an_option_fn": (
        "fn f(c: i32) -> Option<i32>\n    if c == 1\n        Some(5)\n    else\n        None\n"
        + _body(*_match("f(1)", *_SOME)), 5),
    "statement_in_a_result_fn": (
        "fn f() -> Result<i32, i32>\n    Some(5)\n    Ok(5)\n"
        + _body(*_match("f()", "Ok(v) => v", "Err(e) => 2")), 5),
}

RUNS = {**ARRAY_LITERAL, **INDEX_ASSIGN, **ARMS, **STATEMENT}

# 5: `==` / `!=` on an Option or a Result: ritz0's refusal, at the comparison.
_TAGS = "a variant carries a payload, so `==` would compare tags only; use `match` to test the variant"
EQ = {
    "eq_none": _body("let o: Option<i32> = Some(5)", "if o == None", "    return 2", "5"),
    "ne_none": _body("let o: Option<i32> = Some(5)", "if o != None", "    return 5", "2"),
    "none_eq": _body("let o: Option<i32> = Some(5)", "if None == o", "    return 2", "5"),
    "two_locals": _body("let o: Option<i32> = Some(5)", "let p: Option<i32> = None",
                        "if o == p", "    return 2", "5"),
    "result_eq_ok": _body("let r: Result<i32, i32> = Ok(5)", "if r == Ok(5)", "    return 2", "5"),
}

# Nothing names an enum: a located error at the constructor, never the zero.
_LOCATED = "this constructor's type can't be inferred here: bind it with a typed `let` first"
# Each row: the source, and the constructor the error is at.
NO_ENUM = {
    "some_into_i64": (_body("let x: i64 = Some(5)", "0"), "Some("),
    "none_into_i64": (_body("let x: i64 = None", "0"), "None"),
    "ok_into_i64_var": (_body("var x: i64 = Ok(5)", "0"), "Ok("),
    # Arms building an Option and a Result: at the first that differs.
    "arms_of_two_families": (_body("let o = if true then Some(5) else Ok(5)", "0"), "Ok("),
    # An arm's payload ritz1 can't name, as #2430's let.
    "arm_payload_unnamed": (_body("let o = if true then Some(Some(5)) else None", "0"), "Some("),
    "err_arm_payload_unnamed": (_body("let r = if true then Ok(1) else Err(Ok(5))", "0"), "Err("),
}
# A slot that is no enum: the #2142 refusal, now located too.
NON_ENUM_SLOT = {
    "array_of_i64": (_body("let a: [2]i64 = [Some(5), 1]", "0"), "Some("),
    "index_assign_i64": (_body("var a: [2]i64", "a[0] = None", "0"), "None"),
}

# An Err("abc") needs its own Result registered on ritz0 (#2433).
RITZ0_OWN_BUGS = {"if_err_names_its_own_payload"}
ON_RITZ0 = sorted(set(RUNS) - RITZ0_OWN_BUGS)


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


def _where(source, needle, offset=0):
    """1-based line and column of `needle`'s first occurrence, plus `offset`."""
    for line, text in enumerate(source.split("\n"), 1):
        if needle in text:
            return line, text.index(needle) + 1 + offset
    raise AssertionError(f"{needle!r} not in source")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_ritz1_builds_the_enum_the_slot_names(request, tmp_path, compiler, name):
    source, code = RUNS[name]
    proc, ll = _ritz1(request, compiler, tmp_path, source)
    assert proc.returncode == 0, f"{compiler}, {name}:\n{(proc.stdout + proc.stderr)[-800:]}"
    assert "no enum ctx" not in ll.read_text(), f"{compiler}, {name}: built a zero"
    assert _run(ll, tmp_path, str(RITZ_START)) == code, f"{compiler}, {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(EQ))
def test_ritz1_refuses_eq_on_a_payload_enum(request, tmp_path, compiler, name):
    source = EQ[name]
    proc, ll = _ritz1(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-800:]}"
    line, col = _where(source, "if ", 3)
    hits = re.findall(rf"unit\.ritz:{line}:{col}: .*{re.escape(_TAGS)}$", out, re.M)
    assert len(hits) == 1, f"{compiler}, {name}: want one located refusal:\n{out[-800:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name,message", [
    *((n, _LOCATED) for n in sorted(NO_ENUM)),
    *((n, "enum context") for n in sorted(NON_ENUM_SLOT)),
])
def test_ritz1_refuses_a_constructor_with_no_enum(request, tmp_path, compiler, name, message):
    source, ctor = {**NO_ENUM, **NON_ENUM_SLOT}[name]
    proc, ll = _ritz1(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-800:]}"
    line, col = _where(source, ctor)
    hits = re.findall(rf"unit\.ritz:{line}:{col}: .*{re.escape(message)}", out, re.M)
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


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(EQ))
def test_ritz0_refuses_eq_on_a_payload_enum(tmp_path, name):
    source = EQ[name]
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = run_ritz0([str(src), "-o", str(tmp_path / "unit.ll")], cwd=tmp_path, env=env,
                     timeout=300)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"ritz0 accepted {name}"
    line, col = _where(source, "if ", 3)
    assert re.search(rf"unit\.ritz:{line}:{col}: .*{re.escape(_TAGS)}", out), out[-800:]


@pytest.mark.integration
def test_ritz0_array_literal_needs_no_registration(tmp_path):
    """The element type materializes its own Option, as a typed let's does (#2509)."""
    source, code = ARRAY_LITERAL["array_literal"]
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-1500:]
    assert _run(ll, tmp_path) == code
