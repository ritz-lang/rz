"""AGAST #1954: ritz1 reads `x.f[i]` of a `[N]f32` / `[N]f64` struct field as a
float value, and stores `x.f[i] = v` at the field's float width.

THE DEFECT

emit_expr_index's struct-field arm failed closed for a `[N]f32` field and
bit-loaded a `[N]f64` element as `i64` while a compare over it wanted a
`double` (`fcmp oeq double %i64reg`, rejected by clang).  The element store
failed closed for f32 and stored `i64` for f64.

The runtime behaviour is checked against ritz0 in
ritz0/test/test_issue_struct_float_field_index.ritz.  This file pins the IR:
every GEP, load and store of the element is `float` / `double`, the element
is returned / compared without an integer detour, and an f64 value stored
into an f32 slot is fptrunc'd.
"""

import re
import subprocess

import pytest

SHAPE = """\
struct S
    lead: i32
    a: [3]{elem}
    tail: i64

fn ld(s: *S, i: i64) -> {elem}
    s.a[i]

fn st(s: *S, v: {elem}) -> void
    s.a[1] = v

fn lit(s: *S) -> void
    s.a[0] = 2.5

fn cmp(s: *S) -> i32
    if s.a[2] == s.a[0]
        return 1
    return 0

pub fn main() -> i32
    return 0
"""


def _fn_ir(ll_text, name):
    body = ll_text.split(f" @{name}(", 1)[1]
    return body.split("\n}", 1)[0]


@pytest.mark.integration
@pytest.mark.parametrize("elem,llvm", [("f32", "float"), ("f64", "double")])
def test_struct_float_field_index_ir(ritz1_bin, tmp_path, elem, llvm):
    src = tmp_path / f"sffi_{elem}.ritz"
    src.write_text(SHAPE.format(elem=elem))
    ll = tmp_path / f"sffi_{elem}.ll"
    proc = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(ll)], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    text = ll.read_text()
    ld, st, lit, cmp = (_fn_ir(text, n) for n in ("ld", "st", "lit", "cmp"))
    for body in (ld, st, lit, cmp):
        assert f"getelementptr [3 x {llvm}], ptr" in body, body
    # Reads: the element loads at its own width and is used as-is.
    gep = re.search(r"(%\.\d+) = getelementptr \[3 x", ld).group(1)
    loads = [ln.strip() for ln in ld.splitlines() if ln.endswith(f"ptr {gep}")]
    assert len(loads) == 1 and f"= load {llvm}, ptr" in loads[0], ld
    assert f"ret {llvm} " in ld and "bitcast" not in ld, ld
    assert cmp.count(f"load {llvm}, ptr") == 2, cmp
    assert f"fcmp oeq {llvm} " in cmp, cmp
    # Stores: exactly one store into the GEP'd element, at the float width.
    for body in (st, lit):
        gep = re.search(r"(%\.\d+) = getelementptr \[3 x", body).group(1)
        stores = [ln for ln in body.splitlines() if ln.endswith(f"ptr {gep}")]
        assert len(stores) == 1 and stores[0].lstrip().startswith(f"store {llvm} "), (
            body
        )
    if elem == "f32":
        # The f64 literal is narrowed for an f32 slot.
        assert "fptrunc double" in lit, lit
    proc = subprocess.run(
        ["clang", "-c", str(ll), "-o", str(tmp_path / "o.o")],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
