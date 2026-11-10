"""AGAST #2554: `q + k` on an `@&[N]T` walks rows of `[N]T`, as on `*[N]T`.

    fn f(q: @&[3]i32) -> i32
        let r = q + 0
        return r[1]                 # ritz0: 6

ritz1 wrote `inttoptr i64 %.3` for the add, but an `@&` value is a `ptr`, so
clang refused it ("'%.3' defined with type 'ptr' but expected 'i64'").  A
`*[N]T` or `@[N]T` value is an i64, and those were already right.  emit_binary's
pointer-arithmetic path now uses a `ptr` left operand as is.

Measured before the fix, scalar and struct T alike: every `@&` row failed at
clang (param, inferred local, annotated local); every `*` and `@` row was
already right.  The struct rows' T is 8 bytes, the scalar's 4, so a stride of
the element instead of the row reads a different value.

Each program returns x's element [K][1] (or its `.b`) through `r = q + K`, so
a wrong stride or a wrong base reads something else.  ritz0 is the oracle.
"""

import pytest

from test_ritz1_array_ptr_element import COMPILERS, run_with  # noqa: F401  (fixture)

_S = "struct S\n    a: i32\n    b: i32\n\n"

# The element type, how element [i][j] (or [j] when 1-D) gets v, and how
# an element is read back.  The struct is filled a field at a time: ritz1
# refuses a whole-struct store into a 2-D array (a separate limit).
ELEMS = {
    "scalar": ("i32", "    x{at} = {v}\n", "{e}"),
    "struct": ("S", "    x{at}.a = 1\n    x{at}.b = {v}\n", "{e}.b"),
}

# What r = q + K reads: x[K][1].
VALUES = {0: 6, 1: 9}

# How `q` comes to hold x's first row.  `{t}` is the element type.
#   param:TYPE           `fn f(q: TYPE)`, called with `f(@&x[0])` on a [2][3]T
#   local:TYPE=INIT      `let q: TYPE = INIT` in main, on a [2][3]T
#   flat:INIT            `let q = INIT` in main, on a 1-D [3]T: K = 0 only
#   local:=INIT          `let q = INIT` in main, on a [2][3]T
HOLDERS = {
    "ptr_param": "param:*[3]{t}",
    "ref_param": "param:@[3]{t}",
    "mut_ref_param": "param:@&[3]{t}",
    "ptr_local": "local:*[3]{t}=@x[0]",
    "ref_local": "local:@[3]{t}=@x[0]",
    "mut_ref_local": "local:@&[3]{t}=@&x[0]",
    "ref_inferred": "flat:@x",
    "mut_ref_inferred": "flat:@&x",
    "ref_inferred_row": "local:=@x[0]",
    "mut_ref_inferred_row": "local:=@&x[0]",
}

# AGAST #2555: an inferred `let q = @x[0]` on a 2-D array records no row type,
# so `q + 1` strides a byte and `r[1]` loads an i8 (silent), and a struct `r[1].b`
# is refused.  Annotated, it's right.
INFERRED_ROW = {"ref_inferred_row", "mut_ref_inferred_row"}

# AGAST #2556: an annotated `let q: *[3]S = @x[0]` on a 2-D struct array names
# no S, so `q + 1` has no row size (and `q[1].b` is refused too).  Loud.  The
# `@[3]S` / `@&[3]S` annotations and the scalar `*[3]i32` one are right.
STRUCT_PTR_ROW = {("struct", "ptr_local")}


def _fill(elem: str, flat: bool) -> str:
    t, store, _ = ELEMS[elem]
    if flat:
        out = f"    var x: [3]{t}\n"
        cells = [(f"[{j}]", VALUES[0] if j == 1 else 1) for j in range(3)]
    else:
        out = f"    var x: [2][3]{t}\n"
        cells = [(f"[{i}][{j}]", VALUES[i] if j == 1 else 1)
                 for i in range(2) for j in range(3)]
    for at, v in cells:
        out += store.format(at=at, v=v)
    return out


def _program(elem: str, holder: str, k: int) -> str:
    t, _, read = ELEMS[elem]
    walk = f"    let r = q + {k}\n    return " + read.format(e="r[1]") + "\n"
    kind, spec = HOLDERS[holder].split(":", 1)
    pre = _S if elem == "struct" else ""
    if kind == "param":
        return (pre + f"fn f(q: {spec.format(t=t)}) -> i32\n" + walk
                + "\npub fn main() -> i32\n" + _fill(elem, False)
                + "    return f(@&x[0])\n")
    if kind == "flat":
        decl = f"    let q = {spec}\n"
    else:
        ty, init = spec.split("=")
        decl = f"    let q{': ' + ty.format(t=t) if ty else ''} = {init}\n"
    return (pre + "pub fn main() -> i32\n" + _fill(elem, kind == "flat")
            + decl + walk)


CASES = [(e, h, k) for e in sorted(ELEMS) for h in sorted(HOLDERS)
         for k in sorted(VALUES) if not (HOLDERS[h].startswith("flat:") and k != 0)]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("elem,holder,k", CASES)
def test_reference_row_arith(request, run_with, elem, holder, k, compiler):
    if holder in INFERRED_ROW and compiler != "ritz0":
        request.applymarker(pytest.mark.xfail(strict=True, reason="AGAST #2555"))
    if (elem, holder) in STRUCT_PTR_ROW and compiler != "ritz0":
        request.applymarker(pytest.mark.xfail(strict=True, reason="AGAST #2556"))
    name = f"{elem}_{holder}_{k}"
    assert run_with(compiler, name, _program(elem, holder, k)) == VALUES[k]


# `q - k` shares the path: step back from the second row to the first.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("pty", ["*[3]i32", "@[3]i32", "@&[3]i32"])
def test_reference_row_sub(run_with, pty, compiler):
    program = (f"fn f(q: {pty}) -> i32\n    let r = q - 1\n    return r[1]\n"
               "\npub fn main() -> i32\n" + _fill("scalar", False)
               + "    return f(@&x[1])\n")
    assert run_with(compiler, "row_sub", program) == VALUES[0]
