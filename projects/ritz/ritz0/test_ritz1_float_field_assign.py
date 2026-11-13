"""AGAST #2048: ritz1 stores into an f32 / f64 struct field at the field's
own width.

THE DEFECT

`p.x = 4.5` with `x: f32` / `x: f64` fell to the `store i64` default of both
field-assign paths in ritz1/src/emitter_stmt.ritz -- STMT_LOCAL_FIELD_ASSIGN
(`p.x = v` on a struct or pointer local) and emit_assign's EXPR_MEMBER arm
(`pp.x = v` on a pointer param, `o.p.x = v` nested) -- emitting
`store i64 %double`, which clang rejects.

The runtime behaviour is checked against ritz0 in
ritz0/test/test_issue_float_field_assign.ritz.  This file pins the IR: every
store into a float field is `float` / `double`, and an f64 value into an f32
field is fptrunc'd.
"""

import re
import subprocess

import fast_link
import pytest

SHAPE = """\
struct P
    x: {elem}
    tag: i32

struct O
    k: i32
    p: P

fn local_lit() -> {elem}
    var p: P
    p.x = 4.5
    p.x

fn local_var(v: {elem}) -> {elem}
    var p: P
    p.x = v
    p.x

fn ptr_param(pp: *P, v: {elem}) -> void
    pp.x = v

fn ptr_param_lit(pp: *P) -> void
    pp.x = 2.5

fn nested(v: {elem}) -> {elem}
    var o: O
    o.p.x = v
    o.p.x

fn nested_lit() -> {elem}
    var o: O
    o.p.x = 0.5
    o.p.x

pub fn main() -> i32
    return 0
"""

FNS = ("local_lit", "local_var", "ptr_param", "ptr_param_lit", "nested", "nested_lit")
LITERAL_FNS = ("local_lit", "ptr_param_lit", "nested_lit")


def _fn_ir(ll_text, name):
    body = ll_text.split(f" @{name}(", 1)[1]
    return body.split("\n}", 1)[0]


@pytest.mark.integration
@pytest.mark.parametrize("elem,llvm", [("f32", "float"), ("f64", "double")])
def test_float_field_assign_ir_stores_field_width(ritz1_bin, tmp_path, elem, llvm):
    src = tmp_path / f"ffa_{elem}.ritz"
    src.write_text(SHAPE.format(elem=elem))
    ll = tmp_path / f"ffa_{elem}.ll"
    proc = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(ll)], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    text = ll.read_text()
    for name in FNS:
        body = _fn_ir(text, name)
        # The store into the `x` field's GEP (`getelementptr %P, ..., i32 0`)
        # is float / double -- never `store i64`.
        geps = re.findall(r"(%\.\d+) = getelementptr %P, ptr %[\w.]+, i32 0, i32 0$", body, re.M)
        stores = [
            ln.strip()
            for ln in body.splitlines()
            if ln.lstrip().startswith("store ") and any(ln.endswith(f"ptr {g}") for g in geps)
        ]
        assert len(stores) == 1, (name, body)
        assert stores[0].startswith(f"store {llvm} "), (name, body)
        if elem == "f32" and name in LITERAL_FNS:
            # The f64 literal is narrowed for an f32 field.
            assert "fptrunc double" in body, (name, body)
    proc = fast_link.clang(
        ["clang", "-c", str(ll), "-o", str(tmp_path / "o.o")],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
