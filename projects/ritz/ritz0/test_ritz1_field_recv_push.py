"""AGAST #2562: ritz1 instantiates `vec_push$S` for `self.v.push(s)` in a
method with a bare `self:&` receiver.

THE DEFECT

    struct G
        v: Vec<S>
    impl G
        pub fn add(self:&, s: S)
            self.v.push(s)

ritz1 wrote `call i64 @Vec$S_push(ptr %.4, i64 %.5)` with `%.5` a `%S`, which
clang rejects (angelo shaper/types.ritz:100 GlyphRun.add_glyph).  That call
is the no-FnDef `Type_method` fallback of emit_expr_method, not the UFCS
newtype box (#2413, #2560): `vec_push$S` was never instantiated.

monomorph seeds its per-body local tracker from the params, so a field
receiver `x.v` resolves to `vec_<method>$T` (#1512).  A bare `self:&` has
no type name in its Param (the emitter takes it from the ImplBlock, and
impl_name_bare_self names only a by-value `self`), so `self` was untracked,
`self.v` unresolved and nothing registered `vec_push$S`.  Any other
`Vec<S>.push` in the module instantiated it and hid the bug.

THE MATRIX

receiver x pushed value x size, ritz0 as the oracle.  Each program pushes
into a Vec<S> through only that receiver, so nothing else instantiates
`vec_push$S`.

  * receiver: bare `self:&` (`self.v`), typed `self: @&G` (`self.v`),
    a `g: @&G` param (`g.v`), a local `var g: G = G {..}` (`g.v`;
    annotated, as ritz0 can't push through an inferred `var g = G {..}`)
  * value: a by-value `s: S` param, a local `let t = S {..}`, a struct
    literal, `*p` of a `p: @S` param
  * size: 8 bytes (fits an i64), 32 bytes

MEASURED ON c8bd3a8d

  * broken: every bare `self:&` row (8 cells).
  * already fine: the typed `self`, param and local receivers (24 cells).

THE FIX

monomorph's impl-method walk seeds a bare `self:&` as an `@&T` of the impl's
type, as it seeds a typed `self: @&T`.

Every program pushes twice with S.a == 4, then returns the stored a plus the
count, so each exits 6.
"""

import itertools

import pytest

from test_ritz1_builtin_struct_shadow import _run_pkg

SIZES = {
    "small": ("    a: i32\n    b: f32\n", "S { a: 4, b: 1.0 }"),
    "big": (
        "    a: i32\n    b: i64\n    c: i64\n    d: i64\n",
        "S { a: 4, b: 2, c: 3, d: 4 }",
    ),
}

# The pushed expression, and the body line(s) that set it up.
VALUES = {
    "param": ("s", ""),
    "local": ("t", "        let t = {lit}\n"),
    "literal": ("{lit}", ""),
    "deref": ("*p", ""),
}

# Each receiver's program: `{setup}` / `{val}` / `{lit}` filled per cell.
RECEIVERS = {
    "self_lent": (
        "impl G\n"
        "    pub fn add(self:&, s: S, p: @S)\n"
        "{setup}"
        "        self.v.push({val})\n"
        "        self.v.push({val})\n"
        "\n"
        "pub fn main() -> i32\n"
        "    var g = G {{ v: vec_new<S>() }}\n"
        "    let s = {lit}\n"
        "    g.add(s, @s)\n"
    ),
    "self_typed": (
        "impl G\n"
        "    pub fn add(self: @&G, s: S, p: @S)\n"
        "{setup}"
        "        self.v.push({val})\n"
        "        self.v.push({val})\n"
        "\n"
        "pub fn main() -> i32\n"
        "    var g = G {{ v: vec_new<S>() }}\n"
        "    let s = {lit}\n"
        "    g.add(s, @s)\n"
    ),
    "param": (
        "fn add(g: @&G, s: S, p: @S)\n"
        "{setup}"
        "    g.v.push({val})\n"
        "    g.v.push({val})\n"
        "\n"
        "pub fn main() -> i32\n"
        "    var g = G {{ v: vec_new<S>() }}\n"
        "    let s = {lit}\n"
        "    add(@&g, s, @s)\n"
    ),
    "local": (
        "fn build(s: S, p: @S) -> G\n"
        # Annotated: ritz0 can't push through an inferred `var g = G {..}`.
        "    var g: G = G {{ v: vec_new<S>() }}\n"
        "{setup}"
        "    g.v.push({val})\n"
        "    g.v.push({val})\n"
        "    return g\n"
        "\n"
        "pub fn main() -> i32\n"
        "    let s = {lit}\n"
        "    var g = build(s, @s)\n"
    ),
}

# Read back through a local copy of the Vec header: `g.v.get_ptr(0)` has no
# instantiation in ritz0, and `g.v[0].a` is #2564's path.
TAIL = "    let w: Vec<S> = g.v\n    return w[0].a + w.len as i32\n"


def _program(recv: str, value: str, size: str) -> str:
    fields, lit = SIZES[size]
    val, setup = VALUES[value]
    val = val.format(lit=lit)
    setup = setup.format(lit=lit)
    # A free fn / local body is one indent shallower than a method body.
    if recv in ("param", "local"):
        setup = setup.replace("        ", "    ", 1) if setup else ""
    body = RECEIVERS[recv].format(setup=setup, val=val, lit=lit)
    return (
        "import ritzlib.gvec\n\n"
        f"struct S\n{fields}\n"
        "struct G\n    v: Vec<S>\n\n" + body + TAIL
    )


CELLS = list(itertools.product(RECEIVERS, VALUES, SIZES))


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("recv,value,size", CELLS, ids=["-".join(c) for c in CELLS])
def test_field_receiver_push(compiler, recv, value, size, tmp_path):
    prog = _program(recv, value, size)
    assert _run_pkg(compiler, tmp_path, "frp", prog) == 6, prog
