"""AGAST #2093: a pointer never lands in a float `let` / `var` (LARB R1, R4).

With `let p: *u8 = c"x"`, ritz0 accepted `let a: f64 = p` (rc 0, a pointer
bound as an f64), and `let a: f64 = if c then p else 1.5` emitted
`phi i8* [..], [0x3ff8...]`, which clang rejects. The match-arm form was
refused, but by a generic "no single value type" message.

ritz0 now refuses every form with one located error, at the pointer value:
"cannot use a pointer as a float" (LANGUAGE_SPEC §7.5). The bool half of this
ticket was already done: "cannot use bool as a float" (test_bool_type.py).

Every form runs through all three compilers, held to ritz0's located words:
one `<file>:<line>:<col>: cannot use a pointer as a float` line (ritz1 puts
`error: ` before the message, as diag.ritz does), and no IR written.  Before
AGAST #3626 ritz1 had none: the plain let / var compiled (rc 0, then clang
rejected the IR), and the if / match arms were refused unlocated ("ritz1
cannot emit: match arm yields a non-numeric value ...").
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"

MESSAGE = "cannot use a pointer as a float"

# name -> (source, line, col of the pointer value)
FORMS = {
    "let_plain": ("fn main() -> i32\n"
                  "    let p: *u8 = c\"x\"\n"
                  "    let a: f64 = p\n"
                  "    return a as i32\n", 3, 18),
    "var_f32_plain": ("fn main() -> i32\n"
                      "    let p: *u8 = c\"x\"\n"
                      "    var a: f32 = p\n"
                      "    return a as i32\n", 3, 18),
    "if_arm": ("fn f(n: i64) -> i32\n"
               "    let p: *u8 = c\"x\"\n"
               "    let a: f64 = if n > 2 then p else 1.5\n"
               "    return a as i32\n\n"
               "fn main() -> i32\n"
               "    return f(1)\n", 3, 32),
    "match_arm": ("fn f(n: i64) -> i32\n"
                  "    let p: *u8 = c\"x\"\n"
                  "    let a: f64 = match n\n"
                  "        0 => p\n"
                  "        _ => 1.5\n"
                  "    return a as i32\n\n"
                  "fn main() -> i32\n"
                  "    return f(1)\n", 4, 14),
    # The pointer after the float arm: the slot's type is fixed before either.
    "if_else_arm": ("fn f(n: i64) -> i32\n"
                    "    let p: *u8 = c\"x\"\n"
                    "    let a: f64 = if n > 2 then 1.5 else p\n"
                    "    return a as i32\n\n"
                    "fn main() -> i32\n"
                    "    return f(1)\n", 3, 41),
    # AGAST #3892: no float slot, but an arm is a float: the pointer arm is
    # refused on either side of it (ritz1 called the pointer-first form an
    # "integer" arm), as LARB R43 refuses an integer arm.
    "noslot_if_else": ("fn f(n: i64) -> i32\n"
                       "    let p: *u8 = c\"x\"\n"
                       "    let a = if n > 2 then 1.5 else p\n"
                       "    return a as i32\n\n"
                       "fn main() -> i32\n"
                       "    return f(1)\n", 3, 36),
    "noslot_if_then": ("fn f(n: i64) -> i32\n"
                       "    let p: *u8 = c\"x\"\n"
                       "    let a = if n > 2 then p else 1.5\n"
                       "    return a as i32\n\n"
                       "fn main() -> i32\n"
                       "    return f(1)\n", 3, 27),
    # AGAST #3892: an arm's own pointer `let`, its tail, with no float arm
    # beside it: read off the `let`, which is out of scope at the slot.
    "arm_block_local": ("fn f(n: i64) -> i32\n"
                        "    let a: f64 = match n\n"
                        "        0 =>\n"
                        "            let q: *u8 = c\"x\"\n"
                        "            q\n"
                        "        _ => 2\n"
                        "    return a as i32\n\n"
                        "fn main() -> i32\n"
                        "    return f(1)\n", 5, 13),
    # AGAST #3892: every float slot Sema visits, not only a let's: a return.
    "return_slot": ("fn g(p: *u8) -> f64\n"
                    "    p\n\n"
                    "fn main() -> i32\n"
                    "    return g(c\"x\") as i32\n", 2, 5),
    # AGAST #4199: ritz0's other no-slot merge (a match) and its other
    # return paths (a statement, and a `return` arm), each its own check.
    "noslot_match": ("fn f(n: i64) -> i32\n"
                     "    let p: *u8 = c\"x\"\n"
                     "    let a = match n\n"
                     "        0 => 1.5\n"
                     "        _ => p\n"
                     "    return a as i32\n\n"
                     "fn main() -> i32\n"
                     "    return f(1)\n", 5, 14),
    # Used or not: a statement if, with no value to type, is refused too.
    "noslot_stmt_if": ("fn h() -> f64\n"
                       "    1.5\n\n"
                       "fn q() -> *u8\n"
                       "    c\"x\"\n\n"
                       "fn f(n: i64) -> i32\n"
                       "    if n > 2 then h() else q()\n"
                       "    0\n\n"
                       "fn main() -> i32\n"
                       "    return f(1)\n", 8, 28),
    "return_stmt": ("fn g(p: *u8) -> f64\n"
                    "    return p\n\n"
                    "fn main() -> i32\n"
                    "    return g(c\"x\") as i32\n", 2, 12),
    "return_arm": ("fn g(n: i64, p: *u8) -> f64\n"
                   "    match n\n"
                   "        0 => return p\n"
                   "        _ => 1.5\n\n"
                   "fn main() -> i32\n"
                   "    return g(1, c\"x\") as i32\n", 3, 21),
}

# ritz1 and ritz1_selfhosted: forms with no located refusal yet (none since
# AGAST #3626).
RITZ1_GAPS = {}

# ritz0: forms it doesn't refuse yet (none since AGAST #4199, which refused
# the no-slot merges and returns that compiled to IR clang rejects).
RITZ0_GAPS = {}


def _compile(compiler, tmp_path, source):
    src = tmp_path / "bad.ritz"
    src.write_text(source)
    ll = tmp_path / "bad.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        return run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    return subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=300)


def _assert_refused(compiler, tmp_path, name):
    source, line, col = FORMS[name]
    proc = _compile(compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, out
    hits = re.findall(rf"bad\.ritz:{line}:{col}: (?:error: )?{re.escape(MESSAGE)}$", out, re.M)
    assert len(hits) == 1, out
    # Said once, at the pointer: not again at the `if` / `match` holding it.
    assert out.count(MESSAGE) == 1, out
    assert not (tmp_path / "bad.ll").exists(), f"{compiler} wrote IR for {name}"


def _ritz0_params():
    for name in FORMS:
        marks = ()
        if name in RITZ0_GAPS:
            marks = pytest.mark.xfail(strict=True, reason=RITZ0_GAPS[name])
        yield pytest.param(name, id=name, marks=marks)


@pytest.mark.integration
@pytest.mark.parametrize("name", list(_ritz0_params()))
def test_ritz0_refuses_pointer_into_float(tmp_path, name):
    _assert_refused("ritz0", tmp_path, name)


def _ritz1_params():
    for compiler in ("ritz1", "ritz1_selfhosted"):
        for name in FORMS:
            marks = ()
            if name in RITZ1_GAPS:
                marks = pytest.mark.xfail(strict=True, reason=RITZ1_GAPS[name])
            yield pytest.param(compiler, name, id=f"{compiler}-{name}", marks=marks)


@pytest.mark.integration
@pytest.mark.parametrize("compiler,name", list(_ritz1_params()))
def test_ritz1_refuses_pointer_into_float(request, tmp_path, compiler, name):
    request.getfixturevalue("ritz1_bin")
    _assert_refused(compiler, tmp_path, name)
