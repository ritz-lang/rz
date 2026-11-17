"""Float `%` lowers to `frem` on every compiler (AGAST #3798).

ritz1's float binop dispatch (emitter_expr_arith.ritz, emit_expr_binary) had
fadd/fsub/fmul/fdiv but no arm for OP_MOD, so `x % y` on floats fell through to
`fadd`: `2.0 % 3.0` gave 5.0.  ritz0 has always emitted `frem`.

This checks the IR, not a run: on x86-64 LLVM lowers a non-constant `frem` to
a libm `fmod`/`fmodf` call, and Ritz links no libc, so `x % y` on float
parameters does not link on any compiler yet (AGAST #3817).  Each function is
its own check: `%` at f64, at f32, and mixed in both orders (the f32 is
fpext'd, AGAST #1965) must each be an `frem` at the op's width, and no `fadd`.
"""

import re

import pytest

from test_ref_into_value import COMPILERS, _compile

pytestmark = pytest.mark.integration

SRC = """\
fn rem_f64(x: f64, y: f64) -> f64
    return x % y

fn rem_f32(x: f32, y: f32) -> f32
    return x % y

fn rem_f32_f64(y: f32, x: f64) -> f64
    return y % x

fn rem_f64_f32(y: f32, x: f64) -> f64
    return x % y

pub fn main() -> i32
    return 0
"""

WANT = {"rem_f64": "double", "rem_f32": "float", "rem_f32_f64": "double", "rem_f64_f32": "double"}


def _bodies(ir):
    """{function name: its IR body}, for every function defined in `ir`."""
    found = re.finditer(r'^define [^@]*@"?(\w+)"?\(.*?^}', ir, re.M | re.S)
    return {m.group(1): m.group(0) for m in found}


@pytest.mark.parametrize("compiler", COMPILERS)
def test_float_rem_is_frem(tmp_path, compiler):
    comp, ll, _ = _compile(compiler, tmp_path, "rem", SRC)
    assert comp.returncode == 0 and ll.exists(), comp.stdout + comp.stderr
    bodies = _bodies(ll.read_text())
    bad = [f"{name}: wanted `frem {ty}` and no fadd, got:\n{bodies.get(name)}"
           for name, ty in WANT.items()
           if name not in bodies or f"frem {ty} " not in bodies[name] or "fadd" in bodies[name]]
    assert not bad, f"{compiler}:\n" + "\n".join(bad)
