"""AGAST #2365: indexing an aliased unsigned array read the element signed in ritz0.

    type A = [4]u8

    var b: A
    b[3] = 200
    if b[3] != 200      # ritz0: sext i8 -> -56, so this was true
        return 1

_infer_ritz_type's Index arm asked whether the indexed value's type was an
`ArrayType`, and `A` is a `NamedType` until its alias is resolved, so the element
type came back None and _infer_unsigned_expr said signed.  Compares, casts, `/`
and `>>` all went wrong.  No literal or store is involved: the element is
written one index at a time.

Each row is one way of naming the aliased array; each element has its top bit
set, so a sext changes the value, and every check has its own exit code.  All
three compilers run each row, so they stay in agreement.
"""

import pytest
from test_ref_into_value import COMPILERS, _run

# AGAST #2806: each test's rows share one compile per compiler (batching.py).
pytestmark = [pytest.mark.integration, pytest.mark.batched]

# element type -> (a value with its top bit set, that value // 2 == value >> 1)
TYPES = {
    "u8": ("201", "100"),
    "u32": ("3000000001", "1500000000"),
}

# source -> (declarations, the body of `f` up to the checks, the name indexed)
# `{t}` is the element type.  `f` fills elements 0..2 of `{e}` with 1, {v}, 2.
SOURCES = {
    # The ticket's program: a local of the alias type.
    "local": ("type A = [3]{t}\n\n", "fn f() -> i32\n    var b: A\n{FILL}", "b"),
    # A parameter of the alias type.
    "param": ("type A = [3]{t}\n\nfn g(b: A) -> i32\n{CHECKS}\n",
              "fn f() -> i32\n    var c: A\n{FILL_C}    return g(c)\n", None),
    # A global of the alias type.
    "global": ("type A = [3]{t}\n\nvar G: A\n\n", "fn f() -> i32\n{FILL_G}", "G"),
    # A struct field of the alias type: `h.b[1]`.
    "field": ("type A = [3]{t}\n\nstruct H\n    n: i64\n    b: A\n\n",
              "fn f() -> i32\n    var h: H\n{FILL_H}", "h.b"),
    # An alias of the alias: resolution has to follow the chain.
    "alias_of_alias": ("type A0 = [3]{t}\ntype A = A0\n\n", "fn f() -> i32\n    var b: A\n{FILL}", "b"),
}

_CHECKS = """\
    if {e}[1] != {v}
        return 1
    if {e}[1] < {e}[0]
        return 2
    if ({e}[1] as i64) != {v}
        return 3
    if {e}[1] / 2 != {h}
        return 4
    if {e}[1] >> 1 != {h}
        return 5
    let n: i64 = {e}[1] as i64
    if n <= 0
        return 6
    return 0
"""


def _fill(name: str, v: str) -> str:
    return f"    {name}[0] = 1\n    {name}[1] = {v}\n    {name}[2] = 2\n"


def _program(source: str, ty: str) -> str:
    v, h = TYPES[ty]
    decls, body, name = SOURCES[source]
    checks = _CHECKS.format(e=name or "b", v=v, h=h)
    decls = decls.replace("{t}", ty).replace("{CHECKS}", checks)
    body = (body.replace("{FILL}", _fill("b", v)).replace("{FILL_C}", _fill("c", v))
            .replace("{FILL_G}", _fill("G", v)).replace("{FILL_H}", _fill("h.b", v)))
    if name is not None:
        body += checks
    return f"{decls}{body}\npub fn main() -> i32\n    f()\n"


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ty", sorted(TYPES))
@pytest.mark.parametrize("source", sorted(SOURCES))
def test_an_aliased_unsigned_array_reads_unsigned(tmp_path, compiler, source, ty):
    assert _run(compiler, tmp_path, f"{source}_{ty}", _program(source, ty)) == 0


@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_aliased_signed_array_still_reads_signed(tmp_path, compiler):
    """i8 through the same alias still sign-extends: -55 stays -55."""
    program = (
        "type A = [3]i8\n\npub fn main() -> i32\n    var b: A\n    b[1] = -55\n"
        "    if b[1] != -55\n        return 1\n"
        "    if b[1] >= 0\n        return 2\n"
        "    if (b[1] as i64) != -55\n        return 3\n"
        "    return 0\n"
    )
    assert _run(compiler, tmp_path, "signed_control", program) == 0
