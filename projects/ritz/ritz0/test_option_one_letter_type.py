#!/usr/bin/env python3
"""`Option<P>` over a type with a one-letter name is declared (AGAST #2432, #2420).

    struct P
        a: i32
    fn main() -> i32
        let o: Option<P> = Some(P { a: 5 })
        match o
            Some(v) => v.a
            _ => 2

ritz1 skipped `%Option$P = type ...` because a one-capital suffix looked like the
raw template placeholder `Option$T`, so clang said `Cannot allocate unsized type`.
With `enum C` and `fn f(o: Option<C>)` it said `invalid type for function
argument` (#2420). Whether `P` is a type is what the module declares, not how long
its name is.
"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
RITZ1S = ["ritz1", "ritz1_selfhosted"]

_STRUCT = "struct P\n    a: i32\n"
_ENUM = "enum C\n    Has(i32)\n    Empty\n"
_MAIN = "fn main() -> i32\n"
_READ_P = "        Some(v) => v.a\n        _ => 2\n"
_READ_C = ("        Some(v) =>\n            match v\n                Has(w) => w\n"
           "                Empty => 3\n        _ => 2\n")

CASES = {
    # The payload is a struct named by one letter.
    "struct_local": (_STRUCT + _MAIN + "    let o: Option<P> = Some(P { a: 5 })\n"
                     "    match o\n" + _READ_P, 5),
    "struct_param": (_STRUCT + "fn f(o: Option<P>) -> i32\n    match o\n" + _READ_P
                     + _MAIN + "    f(Some(P { a: 5 }))\n", 5),
    "struct_return": (_STRUCT + "fn g() -> Option<P>\n    Some(P { a: 5 })\n"
                      + _MAIN + "    match g()\n" + _READ_P, 5),
    # The payload is an enum named by one letter (#2420).
    "enum_local": (_ENUM + _MAIN + "    let o: Option<C> = Some(C.Has(5))\n"
                   "    match o\n" + _READ_C, 5),
    "enum_param": (_ENUM + "fn f(o: Option<C>) -> i32\n    match o\n" + _READ_C
                   + _MAIN + "    f(Some(C.Has(5)))\n", 5),
    "enum_return": (_ENUM + "fn g() -> Option<C>\n    Some(C.Has(5))\n"
                    + _MAIN + "    match g()\n" + _READ_C, 5),
    "enum_none": (_ENUM + "fn f(o: Option<C>) -> i32\n    match o\n" + _READ_C
                  + _MAIN + "    f(None)\n", 2),
}


def _compile(request, compiler, tmp_path, source):
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


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_declares_option_over_a_one_letter_type(request, tmp_path, compiler, name):
    source, code = CASES[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    assert proc.returncode == 0, f"{compiler}, {name}:\n{(proc.stdout + proc.stderr)[-800:]}"
    exe = tmp_path / "unit"
    cc = subprocess.run(["clang", "-w", str(ll), str(RITZ_START), "-o", str(exe), "-nostdlib"],
                        capture_output=True, text=True)
    assert cc.returncode == 0, f"{compiler}, {name}: clang rejected the IR:\n{cc.stderr[-800:]}"
    assert subprocess.run([str(exe)], timeout=60).returncode == code, f"{compiler}, {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("decl", ["P", "C"])
def test_ritz1_declares_it_once(request, tmp_path, compiler, decl):
    source = ({"P": _STRUCT, "C": _ENUM}[decl] + f"fn g() -> Option<{decl}>\n    None\n"
              + f"fn h(o: Option<{decl}>) -> i32\n    0\n" + _MAIN
              + f"    let o: Option<{decl}> = g()\n    h(o)\n")
    proc, ll = _compile(request, compiler, tmp_path, source)
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-800:]
    ir = ll.read_text()
    assert ir.count(f"\n%Option${decl} = type ") == 1, ir[:1500]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_ritz1_still_skips_a_type_parameter(request, tmp_path, compiler):
    # A generic fn's own `T` names no type, so there is no `%Option$T` to declare:
    # it's the placeholder the one-letter check was for. (That it leaks into a
    # specialization at all is #2418.)
    source = ("fn f<T>(o: Option<T>) -> i32\n    0\n" + _MAIN
              + "    let o: Option<i32> = None\n    f<i32>(o)\n")
    proc, ll = _compile(request, compiler, tmp_path, source)
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-800:]
    assert "\n%Option$T = type " not in ll.read_text()
