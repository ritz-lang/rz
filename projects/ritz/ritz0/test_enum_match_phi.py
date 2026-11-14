#!/usr/bin/env python3
"""A `match` whose arms are enum values merges at the enum's type (AGAST #3205).

ritz1 / ritz1_selfhosted typed the merge phi `i64` over `%A` values in two
cases, and clang rejected the module:

* a qualified unit-variant arm (`0 => A.V`): emit_expr_member builds a `%A`,
  but nothing typed the arm, so the phi stayed i64.  Tail, typed and untyped
  `let` all broke.
* every arm leaves by `return` (`0 => return A.V`) in a `-> A` fn: no arm has
  a value, so the phi was `i64` zeros, and the fn's `ret %A` named it.  The
  return type is the phi's type then, for any struct-returning fn.

ritz0 is the oracle: every row runs to the same exit code on all three.
LARB R19 (#3040) makes `match` the way from an integer to an enum, so the
first row is that idiom.  Data-carrying arms (`A.V(7)`) already typed the
phi; their rows guard it with a unit arm first, and with `return` arms.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

_A = "enum A\n    V\n    P\n"
_AD = "enum A\n    V(i32)\n    P\n"
_MAIN_A = "fn main() -> i32\n    let a = to_a(1)\n    a as i32 + 40\n"
_MAIN_AD = ("fn main() -> i32\n    match to_a(1)\n        A.V(x) => x + 40\n"
            "        A.P => 2\n")


def _to_a(arm0, arm1, enum=_A, main=_MAIN_A):
    return (enum + "fn to_a(n: i32) -> A\n    match n\n"
            f"        0 => {arm0}\n        _ => {arm1}\n" + main)


def _let(decl, n):
    return (_A + f"fn main() -> i32\n    let n: i32 = {n}\n    {decl} = match n\n"
            "        0 => A.V\n        _ => A.P\n    a as i32 + 40\n")


# name -> (source, exit code)
CASES = {
    # Qualified unit-variant arms: the arm is typed as its enum.
    "tail_unit_arms": (_to_a("A.V", "A.P"), 41),
    "typed_let_unit_arms": (_let("let a: A", 1), 41),
    "untyped_let_unit_arms": (_let("let a", 0), 40),
    # Every arm returns: the phi takes the fn's return type.
    "return_unit_arms": (_to_a("return A.V", "return A.P"), 41),
    "return_data_arms": (_to_a("return A.V(7)", "return A.P", _AD, _MAIN_AD), 2),
    "return_struct_arms": (
        "struct S\n    x: i32\nfn mk(n: i32) -> S\n    match n\n"
        "        0 => return S { x: 7 }\n        _ => return S { x: 41 }\n"
        "fn main() -> i32\n    mk(1).x\n", 41),
    # A method's tail is emitted apart from a fn's.
    "method_return_arms": (
        _A + "struct K\n    k: i32\nimpl K\n    fn to_a(self: @K, n: i32) -> A\n"
        "        match n\n            0 => return A.V\n            _ => return A.P\n"
        "fn main() -> i32\n    let k: K = K { k: 0 }\n    let a = k.to_a(1)\n"
        "    a as i32 + 40\n", 41),
    # Mixed, and data-carrying with a unit arm first.
    "return_then_unit_arm": (_to_a("return A.V", "A.P"), 41),
    "unit_then_data_arm": (_to_a("A.P", "A.V(n + 6)", _AD, _MAIN_AD), 47),
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


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CASES))
def test_enum_valued_match_merges_at_enum_type(request, tmp_path, compiler, name):
    source, code = CASES[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    assert proc.returncode == 0, f"{compiler}, {name}:\n{(proc.stdout + proc.stderr)[-800:]}"
    exe = tmp_path / "unit"
    # ritz0 writes its own `_start`; ritz1 links the runtime's.
    start = [] if compiler == "ritz0" else [str(RITZ_START)]
    link = fast_link.clang(["clang", "-w", str(ll), *start, "-o", str(exe), "-nostdlib"],
                           capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}, {name}: clang rejected the IR:\n{link.stderr[-800:]}"
    assert subprocess.run([str(exe)], timeout=60).returncode == code, f"{compiler}, {name}"
