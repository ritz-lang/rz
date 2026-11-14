#!/usr/bin/env python3
"""`p == "lit"` / `p != "lit"` with `p` a pointer is a located refusal (AGAST #2514).

A bare literal is a StrView (`{ptr, i64}`), so the comparison was a pointer
against an aggregate: ritz0 wrote an `icmp` clang rejects, and ritz1 /
ritz1_selfhosted refused it as "struct type 'Span$u8'" with no hint.

Ruling (Aaron, 2026-11-14): refuse, don't lower the literal to `*u8`.  A `*u8`
is not necessarily a string; strings are compared with string functions, so
the refusal names streq from ritzlib.str.  The literal may be on either side.

What still compiles: a `*u8` slot taking a literal (`let p: *u8 = "lit"`, an
argument), and a pointer compared with a pointer or null.
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
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]


def _main(*lines, pre=""):
    return pre + "fn main() -> i32\n" + "".join(f"    {line}\n" for line in lines)


_S = "struct S\n    p: *u8\n"

# Refused at the comparison's left operand, the token after `if `.
REFUSED = {
    "local_ne_lit": _main('let p: *u8 = c"x"', 'if p != "y"', "    return 5", "2"),
    "lit_eq_local": _main('let p: *u8 = c"x"', 'if "x" == p', "    return 5", "2"),
    "param": 'fn f(p: *u8) -> i32\n    if p == "x"\n        return 5\n    2\n'
             + _main('f(c"x")'),
    "field": _main('let s: S = S { p: c"x" }', 'if s.p == "x"', "    return 5", "2", pre=_S),
    "call_result": 'fn g() -> *u8\n    c"x"\n' + _main('if g() != "x"', "    return 5", "2"),
}

# Still compiles, and runs to the code the program says.
KEPT = {
    "let_slot": (_main('let p: *u8 = "x"', "if *p == 120", "    return 5", "2"), 5),
    "arg_slot": ('fn f(p: *u8) -> i32\n    if *p == 121\n        return 5\n    2\n'
                 + _main('f("y")'), 5),
    "pointer_eq_pointer": (_main('let p: *u8 = c"x"', "let q: *u8 = p", "if p == q",
                                 "    return 5", "2"), 5),
    "pointer_ne_null": (_main('let p: *u8 = c"x"', "if p != null", "    return 5", "2"), 5),
}


def _compile(request, compiler, tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        return run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300), ll
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=300)
    return proc, ll


def _refusal(source):
    for line, text in enumerate(source.split("\n"), 1):
        if "if " in text:
            col = text.index("if ") + 4
            op = "!=" if " != " in text else "=="
            break
    return (rf"unit\.ritz:{line}:{col}: .*'{re.escape(op)}' is not supported between a"
            rf" pointer and a string literal — a \*u8 is not necessarily a string;"
            rf" compare it with streq\(p, c\"\.\.\.\"\) from ritzlib\.str$")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_pointer_eq_string_literal_is_refused(request, tmp_path, compiler, name):
    source = REFUSED[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-800:]}"
    hits = re.findall(_refusal(source), out, re.M)
    assert len(hits) == 1, f"{compiler}, {name}: want one located refusal:\n{out[-800:]}"
    # ritz1's #2510 struct refusal must not fire as well.
    assert "struct type" not in out, f"{compiler}, {name}:\n{out[-800:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(KEPT))
def test_pointer_slots_and_compares_still_compile(request, tmp_path, compiler, name):
    source, code = KEPT[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    assert proc.returncode == 0, f"{compiler}, {name}:\n{(proc.stdout + proc.stderr)[-800:]}"
    exe = tmp_path / "unit"
    # ritz0 writes its own `_start`; ritz1 links the runtime's.
    start = [] if compiler == "ritz0" else [str(RITZ_START)]
    fast_link.clang(["clang", "-w", str(ll), *start, "-o", str(exe), "-nostdlib"], check=True)
    assert subprocess.run([str(exe)], timeout=60).returncode == code, f"{compiler}, {name}"
