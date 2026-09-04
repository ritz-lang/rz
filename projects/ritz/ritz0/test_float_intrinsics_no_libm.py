#!/usr/bin/env python3
"""float .floor()/.ceil()/.round() must not require libm (AGAST #1321).

Ritz links no libc. `llvm.floor.f32` & friends lower to `floorf`/`ceilf`/
`roundf` *libcalls* on baseline x86-64 (no SSE4.1 assumed), so angelo's
rasterizer died at link with `undefined reference to floorf` — the first
corpus user of these methods (zero prior usage; the intrinsic path had
never survived to a link).

The emitter now lowers them inline (fptosi/sitofp + select), valid for
|x| < 2^63 which covers coordinate math. `.abs()` stays on `llvm.fabs`
(lowered to an and-mask, never a libcall).
"""

import subprocess
import sys
from pathlib import Path

RITZ0 = Path(__file__).resolve().parent / "ritz0.py"


def _compile(tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    return subprocess.run(
        [sys.executable, str(RITZ0), str(src),
         "-o", str(tmp_path / "unit.ll"), "--no-runtime"],
        capture_output=True,
        text=True,
    )


FLOAT_METHODS = """\
fn main() -> i32
    let a: f32 = 2.5
    let b: f64 = -2.5
    let r = a.floor() + a.ceil() + a.round()
    let s = b.floor() + b.ceil() + b.round()
    let t = b.abs()
    if r > 0.0 and s < 0.0 and t > 0.0
        0
    else
        1
"""


def test_floor_ceil_round_emit_no_intrinsic_libcalls(tmp_path):
    result = _compile(tmp_path, FLOAT_METHODS)
    assert result.returncode == 0, (
        f"float method fixture failed to compile:\n{result.stderr}"
    )
    ll = (tmp_path / "unit.ll").read_text()
    for bad in ("llvm.floor", "llvm.ceil", "llvm.round"):
        assert bad not in ll, (
            f"{bad} intrinsic still emitted — lowers to a libm libcall "
            "on baseline x86-64 and ritz links no libc"
        )
    # fabs is fine: it lowers to an and-mask, not a libcall.
    verify = subprocess.run(
        [sys.executable, "-c",
         "import sys; import llvmlite.binding as llvm; "
         "llvm.parse_assembly(open(sys.argv[1]).read())",
         str(tmp_path / "unit.ll")],
        capture_output=True, text=True)
    assert verify.returncode == 0, f"invalid IR: {verify.stderr}"
