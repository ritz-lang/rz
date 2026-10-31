"""AGAST #1970: ritz1 declares and indexes a global `[N]f32` / `[N]f64` as
`[N x float]` / `[N x double]`.

THE DEFECT

global_array_elem_llvm (emitter_core.ritz) had no float case: the global was
declared `[N x i64]`, `g[i] = 2.5` emitted `store i64 %double` and `g[i]`
loaded an i64 into a double slot -- clang rejects the IR.

The runtime behaviour is checked against ritz0 in
ritz0/test/test_issue_global_float_array.ritz.  This file pins the IR itself:
the declaration, every GEP, load and store are `float` / `double`, and an
f64 value stored into an f32 element is fptrunc'd.
"""

import re
import subprocess

import pytest

SHAPE = """\
var g: [3]{elem}

fn st(v: {elem}) -> void
    g[1] = v

fn ld() -> {elem}
    g[1]

fn lit() -> void
    g[0] = 2.5

pub fn main() -> i32
    return 0
"""


def _fn_ir(ll_text, name):
    body = ll_text.split(f" @{name}(", 1)[1]
    return body.split("\n}", 1)[0]


@pytest.mark.integration
@pytest.mark.parametrize("elem,llvm", [("f32", "float"), ("f64", "double")])
def test_global_float_array_ir_uses_float_elements(ritz1_bin, tmp_path, elem, llvm):
    src = tmp_path / f"gfa_{elem}.ritz"
    src.write_text(SHAPE.format(elem=elem))
    ll = tmp_path / f"gfa_{elem}.ll"
    proc = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(ll)], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    text = ll.read_text()
    assert f"@g = weak_odr global [3 x {llvm}] zeroinitializer" in text, text
    st, ld, lit = (_fn_ir(text, n) for n in ("st", "ld", "lit"))
    for body in (st, ld, lit):
        assert f"getelementptr [3 x {llvm}], ptr @g" in body, body
        assert "[3 x i64]" not in body, body
    # The value stored into the GEP'd element is a float / double.
    for body in (st, lit):
        gep = re.search(r"(%\.\d+) = getelementptr", body).group(1)
        stores = [ln for ln in body.splitlines() if ln.endswith(f"ptr {gep}")]
        assert len(stores) == 1 and stores[0].lstrip().startswith(f"store {llvm} "), (
            body
        )
    assert f"load {llvm}, ptr" in ld and "load i64" not in ld, ld
    assert f"ret {llvm} " in ld, ld
    if elem == "f32":
        # The f64 literal is narrowed for an f32 slot.
        assert "fptrunc double" in lit, lit
    proc = subprocess.run(
        ["clang", "-c", str(ll), "-o", str(tmp_path / "o.o")],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
