"""AGAST #2560: ritz1 passes `*p` (p an `@S` / `@&S` / `*S`) into a
by-value struct param as the struct, not boxed as an i64.

THE DEFECT

    fn go(p: @P) -> i32
        var v: Vec<P> = vec_new<P>()
        v.push(*p)

`v.push(...)` lowers through the UFCS / generic-spec cascade
(emit_ufcs_call, emitter_expr_call.ritz) to `vec_push$P(@&v, item: P)`. Its
scalar->newtype box asks get_expr_type, which reports `*p` as i64, so it
wrote `store i64 %.6, ptr %.7` with `%.6` a `%P`, which clang rejects
(angelo raster/bezier.ritz:122). The instance-method cascade
(emit_expr_method) already skips the box for a `*r` of a struct pointer, so
`h.put(*p)` was fine.

THE MATRIX

pointer form x where p lives x consumer x size, ritz0 as the oracle:

  * pointer form: `@S`, `@&S`, `*S`
  * where: a param of `go`, or a local in `go` holding `@s` / `@&s`
  * consumer: `Vec<S>.push` (UFCS spec) or a user method `h.put(S)`
  * size: 8 bytes (fits an i64), 32 bytes, 280 bytes (byval)

MEASURED ON 5fb6e9bd

  * broken: `Vec<S>.push(*p)` with p an `@S` or `@&S`, param or local, for
    the 8- and 32-byte S.
  * already fine: every `*S` row (get_expr_type types a raw-pointer deref
    as the struct), every user-method row (emit_expr_method's `*r` guard),
    and the 280-byte S (byval; the box skips it).

THE FIX

emit_ufcs_call's box guard skips a `*p` whose pointee is a struct
(deref_pointee_struct_name), as emit_expr_method's already does.

Every program pushes/puts `*p` twice with p.x == 4, then returns the stored
x plus the count, so each exits 6.
"""

import itertools

import pytest

from test_ritz1_builtin_struct_shadow import _run_pkg

SIZES = {
    "small": ("    x: i32\n    y: f32\n", "S { x: 4, y: 1.0 }"),
    "big": (
        "    x: i32\n    b: i64\n    c: i64\n    d: i64\n",
        "S { x: 4, b: 2, c: 3, d: 4 }",
    ),
    "huge": (
        "    x: i32\n" + "".join(f"    p{i}: i64\n" for i in range(34)),
        "S { x: 4, " + ", ".join(f"p{i}: {i}" for i in range(34)) + " }",
    ),
}

# (param/local type, how main/go takes the address)
FORMS = {
    "ref": ("@S", "@s"),
    "mut_ref": ("@&S", "@&s"),
    "raw_ptr": ("*S", "@s"),
}

CONSUMERS = {
    "vec_push": (
        "    var v: Vec<S> = vec_new<S>()\n"
        "    v.push(*p)\n"
        "    v.push(*p)\n"
        "    let q: *S = v.get_ptr(0)\n"
        "    return q.x + v.len() as i32\n"
    ),
    "method": (
        "    var h = H { n: 0, c: 0 }\n"
        "    h.put(*p)\n"
        "    h.put(*p)\n"
        "    return h.n / 2 + h.c\n"
    ),
}


def _program(size: str, form: str, where: str, consumer: str) -> str:
    fields, init = SIZES[size]
    ptype, addr = FORMS[form]
    body = CONSUMERS[consumer]
    if where == "param":
        go = f"fn go(p: {ptype}) -> i32\n" + body
        call = f"    return go({addr})\n"
    else:
        go = f"fn go() -> i32\n    var s = {init}\n    let p: {ptype} = {addr}\n" + body
        call = "    return go()\n"
    return (
        "import ritzlib.gvec\n\n"
        f"struct S\n{fields}\n"
        "struct H\n    n: i32\n    c: i32\n\n"
        "impl H\n"
        "    pub fn put(self:&, p: S)\n"
        "        self.n = self.n + p.x\n"
        "        self.c = self.c + 1\n\n"
        + go
        + "\npub fn main() -> i32\n"
        + f"    var s = {init}\n"
        + call
    )


# The eight rows that produced invalid IR on 5fb6e9bd.
WAS_BROKEN = {
    (size, form, where, "vec_push")
    for size in ("small", "big")
    for form in ("ref", "mut_ref")
    for where in ("param", "local")
}

MATRIX = [
    pytest.param(
        size,
        form,
        where,
        cons,
        id=f"{size}-{form}-{where}-into-{cons}"
        + ("-was_broken" if (size, form, where, cons) in WAS_BROKEN else ""),
    )
    for size, form, where, cons in itertools.product(
        SIZES, FORMS, ("param", "local"), CONSUMERS
    )
]


@pytest.mark.integration
@pytest.mark.parametrize("size,form,where,consumer", MATRIX)
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_deref_struct_ptr_as_by_value_arg(
    tmp_path, compiler, size, form, where, consumer
):
    name = f"dsa_{size}_{form}_{where}_{consumer}"
    assert (
        _run_pkg(compiler, tmp_path, name, _program(size, form, where, consumer)) == 6
    )


# Control: `*q` of an `@i64` into a single-field struct (`Vec<M>.push`, M a
# newtype over i64) must still take the newtype box. Only a struct pointee
# skips it, so a guard that skipped every deref fails this and not the matrix.
NEWTYPE = """\
import ritzlib.gvec

struct M
    v: i64

fn go(q: @i64) -> i32
    var v: Vec<M> = vec_new<M>()
    v.push(*q)
    v.push(5)
    let r: *M = v.get_ptr(0)
    return r.v as i32 + v.len() as i32

pub fn main() -> i32
    let x: i64 = 4
    return go(@x)
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_deref_scalar_ptr_into_newtype_still_boxed(tmp_path, compiler):
    assert _run_pkg(compiler, tmp_path, "dsa_newtype", NEWTYPE) == 6
