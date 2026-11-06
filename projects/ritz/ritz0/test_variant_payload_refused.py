#!/usr/bin/env python3
"""A variant payload is bound, never tested (AGAST #2350; LANGUAGE_SPEC §8.2).

`_emit_enum_match` switches on the tag alone, so a pattern inside a variant can
only take the payload. Anything that reads as a test was dropped, and the arm took
every value of that variant:

    match o
        Some(0) => 1
        _ => 2          # f(Some(5)) gave 1

Compiling the test is #1291's decision tree. Until then ritz0 refuses it, at the
pattern. The expected exit codes below come from what each program says, not from
a compiler.

ritz1's grammar takes only a name there, so it refuses every literal with a parse
error, and #2405 holds the names that test.
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

_C = "enum C\n    R\n    G\n"
_P = "enum P\n    Two(i32, i32)\n    One(i32)\n    Z\n"
_V = "enum E\n    V\n        x: i32\n    W\n"
_HINT = " — bind it to a name, then test the name in the arm body"


def _opt(ty, pattern, arg):
    """`f(Some(arg))`, with `pattern` on line 3 of this text, payload at column 14."""
    return (f"fn f(o: Option<{ty}>) -> i32\n    match o\n        {pattern} => 1\n"
            f"        _ => 2\nfn main() -> i32\n    f(Some({arg}))\n")


# name -> (source, line, col, the pattern as shown, its variant)
LITERALS = {
    "int": (_opt("i32", "Some(0)", "5"), 3, 14, "0", "Some"),
    "int_equal_to_the_payload": (_opt("i32", "Some(5)", "5"), 3, 14, "5", "Some"),
    "bool_true": (_opt("bool", "Some(true)", "false"), 3, 14, "true", "Some"),
    "bool_false": (_opt("bool", "Some(false)", "true"), 3, 14, "false", "Some"),
    "string": (_opt("StrView", 'Some("a")', '"b"'), 3, 14, '"a"', "Some"),
    "second_field": (_P + "fn f(p: P) -> i32\n    match p\n        Two(a, 0) => a\n"
                     "        _ => 2\nfn main() -> i32\n    f(P.Two(1, 5))\n",
                     7, 16, "0", "Two"),
    "qualified_arm": (_P + "fn f(p: P) -> i32\n    match p\n        P.One(0) => 1\n"
                      "        _ => 2\nfn main() -> i32\n    f(P.One(5))\n",
                      7, 15, "0", "One"),
    "struct_variant": (_V + "fn f(e: E) -> i32\n    match e\n        V(0) => 1\n"
                       "        _ => 2\nfn main() -> i32\n    f(E.V(5))\n",
                       7, 11, "0", "V"),
    "result_err": ("fn f(r: Result<i32, i32>) -> i32\n    match r\n        Err(7) => 1\n"
                   "        _ => 2\nfn main() -> i32\n    f(Err(5))\n", 3, 13, "7", "Err"),
    "statement": ("fn main() -> i32\n    var r: i32 = 2\n    let o: Option<i32> = Some(5)\n"
                  "    match o\n        Some(0) => r = 1\n        _ => pass\n    r\n",
                  5, 14, "0", "Some"),
    "generic_fn": ("fn f<T>(o: Option<T>) -> i32\n    match o\n        Some(0) => 1\n"
                   "        _ => 2\nfn main() -> i32\n    let o: Option<i32> = Some(5)\n"
                   "    f<i32>(o)\n", 3, 14, "0", "Some"),
    "untyped_scrutinee": ("struct T\n    v: i32\nimpl T\n    fn o(self) -> Option<i32>\n"
                          "        Some(5)\nfn main() -> i32\n    let t = T { v: 1 }\n"
                          "    match t.o()\n        Some(0) => 1\n        _ => 2\n",
                          9, 14, "0", "Some"),
    "behind_a_covering_arm": ("fn f(o: Option<i32>) -> i32\n    match o\n        Some(0) => 1\n"
                              "        Some(v) => v\n        None => 2\n"
                              "fn main() -> i32\n    f(Some(5))\n", 3, 14, "0", "Some"),
    "more_fields_than_the_variant": (_opt("i32", "Some(a, 0)", "5"), 3, 17, "0", "Some"),
    "payload_on_a_bare_variant": (_P + "fn f(p: P) -> i32\n    match p\n        Z(0) => 1\n"
                                  "        _ => 2\nfn main() -> i32\n    f(P.Z)\n",
                                  7, 11, "0", "Z"),
}

# A type names no value here: `Some(bool)` took an `Option<i32>`'s every `Some`.
TYPES = {
    "matching_type": (_opt("i32", "Some(i32)", "5"), 3, 14, "i32", "Some"),
    "other_type": (_opt("i32", "Some(bool)", "5"), 3, 14, "bool", "Some"),
    "pointer_type": (_opt("*u8", "Some(*u8)", "null"), 3, 14, "*u8", "Some"),
}

# §8.2 makes these tests, though they look like bindings.
NAMES = {
    "const": ("const K: i32 = 0\n" + _opt("i32", "Some(K)", "5"), 4, 14, "K", "Some"),
    "const_declared_later": (_opt("i32", "Some(K)", "5") + "const K: i32 = 0\n",
                             3, 14, "K", "Some"),
    "const_on_a_bool_payload": ("const K: i32 = 0\n" + _opt("bool", "Some(K)", "true"),
                                4, 14, "K", "Some"),
    "variant": (_C + _opt("C", "Some(R)", "C.G"), 6, 14, "R", "Some"),
    "repr_enum_variant": ("enum D: u64\n    X = 0\n    Y = 1\n" + _opt("D", "Some(X)", "D.Y"),
                          6, 14, "X", "Some"),
    "builtin_variant": ("fn f(o: Option<Option<i32>>) -> i32\n    match o\n"
                        "        Some(None) => 1\n        _ => 2\n"
                        "fn main() -> i32\n    let i: Option<i32> = Some(1)\n    f(Some(i))\n",
                        3, 14, "None", "Some"),
}

REFUSED = {**LITERALS, **TYPES, **NAMES}

# name -> (source, exit code). Each is a binding or `_`, so each must still run.
KEPT = {
    "binding": ("fn f(o: Option<i32>) -> i32\n    match o\n        Some(v) => v\n"
                "        _ => 2\nfn main() -> i32\n    f(Some(5))\n", 5),
    "wildcard": (_opt("i32", "Some(_)", "5"), 1),
    "wildcard_on_none": ("fn f(o: Option<i32>) -> i32\n    match o\n        Some(_) => 1\n"
                         "        _ => 2\nfn main() -> i32\n    f(None)\n", 2),
    "two_bindings": (_P + "fn f(p: P) -> i32\n    match p\n        Two(a, b) => a * 10 + b\n"
                     "        _ => 2\nfn main() -> i32\n    f(P.Two(1, 5))\n", 15),
    "binding_and_wildcard": (_P + "fn f(p: P) -> i32\n    match p\n        Two(_, b) => b\n"
                             "        _ => 2\nfn main() -> i32\n    f(P.Two(1, 5))\n", 5),
    "struct_variant": (_V + "fn f(e: E) -> i32\n    match e\n        V(a) => a\n"
                       "        _ => 2\nfn main() -> i32\n    f(E.V(5))\n", 5),
    # Named like a variant, but of an enum this payload isn't.
    "named_like_another_enums_variant": (
        _C + "fn f(o: Option<i32>) -> i32\n    match o\n        Some(R) => R\n"
        "        _ => 2\nfn main() -> i32\n    f(Some(5))\n", 5),
    "named_like_another_enums_variant_on_an_enum": (
        _C + "enum D\n    X\n    Y\nfn f(o: Option<D>) -> i32\n    match o\n"
        "        Some(R) => 1\n        _ => 2\nfn main() -> i32\n    f(Some(D.Y))\n", 1),
    # A repr enum is no integer's type: `u64` doesn't make `X` a variant.
    "named_like_a_repr_enums_variant": (
        "enum D: u64\n    X = 0\n    Y = 1\nfn f(o: Option<u64>) -> i32\n    match o\n"
        "        Some(X) => X as i32\n        _ => 2\n"
        "fn main() -> i32\n    f(Some(5 as u64))\n", 5),
    # Constant patterns compare integers only (§8.2).
    "named_like_a_const_on_a_string": (
        "const K: i32 = 0\nfn f(o: Option<StrView>) -> i32\n    match o\n"
        "        Some(K) => 1\n        _ => 2\n"
        'fn main() -> i32\n    f(Some("abc"))\n', 1),
    # Top-level arms keep their own rules.
    "const_at_the_top_level": ("const K: i64 = 0\nfn main() -> i32\n    let n: i64 = 5\n"
                               "    match n\n        K => 1\n        _ => 2\n", 2),
    "variant_at_the_top_level": (_C + "fn main() -> i32\n    let c: C = C.G\n    match c\n"
                                 "        R => 1\n        _ => 2\n", 2),
}


def _ritz0(tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    return run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300), ll


def _ritz1(request, compiler, tmp_path, source):
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=300)
    return proc, ll


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_ritz0_refuses_a_payload_that_tests(tmp_path, name):
    source, line, col, shown, variant = REFUSED[name]
    proc, ll = _ritz0(tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"ritz0 accepted {name}:\n{out[-1500:]}"
    message = (f"a variant payload can only be bound, not tested: "
               f"'{shown}' in '{variant}(...)'{_HINT}")
    hits = re.findall(rf"unit\.ritz:{line}:{col}: {re.escape(message)}$", out, re.M)
    assert len(hits) == 1, f"{name}: want one {message!r}:\n{out[-1500:]}"
    assert not ll.exists(), f"ritz0 wrote IR for {name}"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(KEPT))
def test_ritz0_still_runs_a_payload_that_binds(tmp_path, name):
    source, code = KEPT[name]
    proc, ll = _ritz0(tmp_path, source)
    assert proc.returncode == 0, f"{name}:\n{(proc.stdout + proc.stderr)[-1500:]}"
    exe = tmp_path / "unit"
    subprocess.run(["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"], check=True)
    assert subprocess.run([str(exe)], timeout=60).returncode == code, name


@pytest.mark.integration
def test_a_nested_variant_keeps_its_own_message(tmp_path):
    """`Some(Some(x))` is #1291's, and says so."""
    proc, _ = _ritz0(tmp_path, _opt("Option<i32>", "Some(Some(x))", "None"))
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0 and "Nested variant patterns are not supported" in out, out


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted({**LITERALS, **TYPES}))
def test_ritz1_cannot_parse_a_payload_that_tests(request, tmp_path, compiler, name):
    """Goes red when ritz1 learns one, which must then refuse it or compile it."""
    proc, ll = _ritz1(request, compiler, tmp_path, REFUSED[name][0])
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0 and "Parse error" in out, f"{compiler}, {name}:\n{out[-800:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


@pytest.mark.integration
@pytest.mark.xfail(strict=True, reason="#2405: ritz1 binds a name that §8.2 makes a test")
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(NAMES))
def test_ritz1_refuses_a_name_that_tests(request, tmp_path, compiler, name):
    proc, ll = _ritz1(request, compiler, tmp_path, REFUSED[name][0])
    assert proc.returncode != 0, f"{compiler} accepted {name}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"
