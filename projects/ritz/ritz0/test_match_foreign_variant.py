#!/usr/bin/env python3
"""A match arm can't name another enum's variant (AGAST #2431).

    fn main() -> i32
        let o: Option<i64> = Some(5)
        match o
            Ok(v) => 1
            _ => 2

ritz1 took the `Ok` arm, silently: it read `Ok`'s tag (0) off the Option and
exited 1.  ritz0 refused it, as `Unknown variant Ok in enum Option$i64`.  A bare
constructor scrutinee (#2419) did the same: `match Some(5)` with `Ok(v) => v`
gave 5.  User enums too: `Z(v)` of `enum B`, on an `A`, read A's first tag.

Now all three refuse it, at the arm, naming the enum by its declared name: the
mangled `Option$i64` / `Result$i32_i32` was ritz0's, and ritz1 spells it
`Result$i32$i32`.  A bare unit name of another enum is a binding, and R12
refuses that already (test_local_takes_module_name.py).

The first error agrees: a name reuse (binder_check, #2395) and a missing arm
(coverage, #2344) come before it, as on ritz0.  Every row runs on ritz0, ritz1
and ritz1_selfhosted.
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
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

_MAIN = "fn main() -> i32\n"
_AB = "enum A\n    X(i32)\n    Y\nenum B\n    Z(i32)\n    W\n"   # 6 lines
_LET_A = "    let a: A = A.X(5)\n"
_LET_O = "    let o: Option<i64> = Some(5)\n"


def _message(variant, enum):
    return f"Unknown variant {variant} in enum {enum}"


# name -> (source, line, col, variant, enum): the error is at the arm's pattern.
REFUSED = {
    # The ticket's two.
    "ok_on_a_typed_option": (
        _MAIN + _LET_O + "    match o\n        Ok(v) => 1\n        _ => 2\n",
        4, 9, "Ok", "Option"),
    "ok_on_a_bare_some": (
        _MAIN + "    match Some(5)\n        Ok(v) => v\n        _ => 2\n", 3, 9, "Ok", "Option"),
    "some_on_a_bare_ok": (
        _MAIN + "    match Ok(5)\n        Some(v) => v\n        _ => 2\n", 3, 9, "Some", "Result"),
    "err_on_a_bare_none": (
        _MAIN + "    match None\n        Err(e) => 1\n        _ => 2\n", 3, 9, "Err", "Option"),
    "after_an_own_arm": (
        _MAIN + _LET_O + "    match o\n        Some(v) => 1\n        Err(e) => 3\n        _ => 2\n",
        5, 9, "Err", "Option"),
    "wildcard_payload_on_a_result_param": (
        "fn f(r: Result<i32, i32>) -> i32\n    match r\n        Some(_) => 1\n        _ => 2\n"
        + _MAIN + "    f(Ok(1))\n", 3, 9, "Some", "Result"),
    "through_a_pointer": (
        "fn f(o: *Option<i32>) -> i32\n    match *o\n        Ok(v) => 1\n        _ => 2\n"
        + _MAIN + "    let o: Option<i32> = Some(1)\n    f(@o)\n", 3, 9, "Ok", "Option"),
    "a_nested_match": (
        _MAIN + _LET_O + "    match o\n        Some(v) =>\n            match o\n"
        "                Ok(w) => 1\n                _ => 2\n        _ => 3\n",
        6, 17, "Ok", "Option"),
    "as_a_statement": (
        _MAIN + _LET_O + "    var r: i32 = 0\n    match o\n        Ok(v) =>\n            r = 1\n"
        "        _ =>\n            r = 2\n    r\n", 5, 9, "Ok", "Option"),
    "a_lets_value": (
        _MAIN + _LET_O + "    let r: i32 = match o\n        Ok(v) => 1\n        _ => 2\n    r\n",
        4, 9, "Ok", "Option"),
    "in_a_generic_fn": (
        "fn f<T>(x: T, o: Option<i64>) -> i32\n    match o\n        Ok(v) => 1\n        _ => 2\n"
        + _MAIN + "    f<i32>(1, Some(5))\n", 3, 9, "Ok", "Option"),
    # User enums.
    "another_users_variant": (
        _AB + _MAIN + _LET_A + "    match a\n        Z(v) => v\n        _ => 2\n",
        10, 9, "Z", "A"),
    "another_users_variant_qualified": (
        _AB + _MAIN + _LET_A + "    match a\n        B.Z(v) => v\n        _ => 2\n",
        10, 9, "Z", "A"),
    "another_users_unit_qualified": (
        _AB + _MAIN + _LET_A + "    match a\n        B.W => 7\n        _ => 2\n",
        10, 9, "W", "A"),
    "a_users_variant_on_an_option": (
        _AB + _MAIN + "    let o: Option<i32> = Some(5)\n    match o\n        X(v) => v\n"
        "        _ => 2\n", 10, 9, "X", "Option"),
    "an_options_variant_on_a_user_enum": (
        _AB + _MAIN + _LET_A + "    match a\n        Some(v) => 1\n        _ => 2\n",
        10, 9, "Some", "A"),
    "a_users_variant_on_a_bare_user_ctor": (
        _AB + _MAIN + "    match X(5)\n        Z(v) => v\n        _ => 2\n", 9, 9, "Z", "A"),
    # No enum declares it. An integer field sits just before B's, which a
    # miss used to read (test_variant_payload_refused.py).
    "no_enums_variant": (
        "enum A\n    Last(i32)\nenum B\n    Y\nfn f(e: B) -> i32\n    match e\n"
        "        Nope(k) => 1\n        _ => 2\n" + _MAIN + "    f(B.Y)\n", 7, 9, "Nope", "B"),
    "an_options_variant_on_a_user_param": (
        _AB + "fn f(a: A) -> i32\n    match a\n        Ok(v) => 1\n        _ => 2\n"
        + _MAIN + "    f(A.Y)\n", 9, 9, "Ok", "A"),
}

# What still compiles, and what it gives.
KEPT = {
    "own_qualified": (_AB + _MAIN + _LET_A + "    match a\n        A.X(v) => v\n        A.Y => 2\n", 5),
    "own_unqualified": (_AB + _MAIN + _LET_A + "    match a\n        X(v) => v\n        Y => 2\n", 5),
    "option": (_MAIN + _LET_O + "    match o\n        Some(v) => v as i32\n        None => 2\n", 5),
    "result": (_MAIN + "    let r: Result<i32, i32> = Err(5)\n    match r\n        Ok(v) => 1\n"
               "        Err(e) => e\n", 5),
    "a_user_param_after_another_enums_match": (
        _AB + "fn f(a: A) -> i32\n    match a\n        X(v) => v\n        Y => 2\n"
        + _MAIN + "    let b: B = B.Z(1)\n    match b\n        Z(v) => f(A.X(4)) + v\n"
        "        W => 2\n", 5),
}


def _compile(request, compiler, tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        request.getfixturevalue("ritz1_bin")
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path, env=env,
                              capture_output=True, text=True, timeout=300)
    return proc, ll


def _located(compiler, out, line, col, message):
    """ritz1 says `error:` after the place; ritz0 doesn't."""
    sep = "" if compiler == "ritz0" else "error: "
    return re.findall(rf"unit\.ritz:{line}:{col}: {sep}{re.escape(message)}$", out, re.M)


def _first(out):
    return next(line for line in out.splitlines() if "unit.ritz:" in line)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_an_arm_cant_name_another_enums_variant(request, tmp_path, compiler, name):
    source, line, col, variant, enum = REFUSED[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-1500:]}"
    message = _message(variant, enum)
    hits = _located(compiler, out, line, col, message)
    assert len(hits) == 1, f"{compiler}, {name}: want one {message!r} at {line}:{col}:\n{out[-1500:]}"
    assert message in _first(out), f"{compiler}, {name}: not the first error:\n{out[-1500:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(KEPT))
def test_an_arm_of_the_scrutinees_enum_still_runs(request, tmp_path, compiler, name):
    source, code = KEPT[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    assert proc.returncode == 0, f"{compiler}, {name}:\n{(proc.stdout + proc.stderr)[-1500:]}"
    exe = tmp_path / "unit"
    link = ["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link.insert(3, str(RITZ_START))
    subprocess.run(link, check=True)
    assert subprocess.run([str(exe)], timeout=60).returncode == code, f"{compiler}, {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_missing_arm_comes_first(request, tmp_path, compiler):
    """Coverage is judged first, as on ritz0: `None` is missing, and `Ok` is foreign."""
    source = _MAIN + _LET_O + "    match o\n        Ok(v) => 1\n        Some(v) => 2\n"
    proc, _ = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0
    assert "non-exhaustive match: missing None" in _first(out), out[-1500:]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_name_reuse_comes_first(request, tmp_path, compiler):
    """binder_check judges names before any match (#2395): `v` is reused, `Ok` foreign."""
    source = (_MAIN + "    let v: i64 = 1\n" + _LET_O + "    match o\n        Ok(v) => 1\n"
              "        _ => 2\n")
    proc, _ = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0
    assert "a local can't reuse a name bound earlier in its fn: 'v'" in _first(out), out[-1500:]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
def test_ritz1_judges_arms_only_by_the_scrutinees_enum(request, tmp_path, compiler):
    """An enum ritz1 guessed from an arm is no judge of the arms.

    ritz1 can't type `n as B`, so it takes the enum the first arm names: `V` is
    A's too, and A's is found first.  That guess must not call B's `Q` foreign.
    ritz0 refuses the cast itself, so this one is ritz1's alone.
    """
    source = ("enum A\n    V\n    P\nenum B\n    V\n    Q(i32)\n" + _MAIN
              + "    let n: i32 = 1\n    match n as B\n        V => 1\n        Q(x) => 5\n")
    proc, _ = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert "Unknown variant" not in out, out[-1500:]
