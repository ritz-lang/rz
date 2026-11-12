"""AGAST #2791: `vec_as_ptr<E>(@v) + i` strides by sizeof(E).

ritz1 compiled `*(vec_as_ptr<*u8>(@v) + i)` to `add i64 %base, %i` with no
`mul`: monomorph left a `-> *T` at T = *u8 as a `*T` named "T", no stride
lookup resolved "T", and ptr_arith_elem_size's 0 ("not a pointer") made the
`+ i` a raw BYTE offset.  #2790's rzrz built execve's argv this way and got
EFAULT.  ritz0 is the oracle.

The return is now recorded as the `**U` it is, as a written `-> **U` is, and
`let p = f()` on either types p as `let p: **U` does (it was an i64, so
`*(p + i)` silently loaded the wrong pointer).  A call known to return a
pointer whose element size is still unknown is a located error, never a byte
add.

Each program reads the element at index 2 through the call's result, so it
returns 7 only when the `+` stepped whole elements.
"""

import pytest

import test_ritz1_for_header as for_header

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

S = "struct S\n    a: i64\n    b: i32\n\nfn mk(b: i32) -> S\n    var s: S\n    s.a = 0\n    s.b = b\n    return s\n\n"

# pointee -> (prelude, element type, three pushed values, read the element as an i32)
POINTEES = {
    "ptr_u8": ("", "*u8", ('c"1"', 'c"2"', 'c"7"'), "(*{x})[0] as i32 - 48"),
    "i64": ("", "i64", ("1", "2", "7"), "*{x} as i32"),
    "struct": (S, "S", ("mk(1)", "mk(2)", "mk(7)"), "(*{x}).b"),
}

# How the element at index 2 is reached from the call.
SHAPES = {
    "add": ("", "(vec_as_ptr<{E}>(@v) + i)"),
    "chain": ("", "(vec_as_ptr<{E}>(@v) + 3 - 1)"),
    "let": ("    let p = vec_as_ptr<{E}>(@v)\n", "(p + i)"),
}


def _program(pointee: str, shape: str) -> str:
    prelude, elem, values, read = POINTEES[pointee]
    pre, x = (part.replace("{E}", elem) for part in SHAPES[shape])
    pushes = "".join(f"    vec_push<{elem}>(@&v, {val})\n" for val in values)
    return (
        for_header.GVEC + prelude
        + "pub fn main() -> i32\n"
        + f"    var v: Vec<{elem}> = vec_new<{elem}>()\n"
        + pushes
        + "    let i: i64 = 2\n"
        + pre
        + f"    return {read.replace('{x}', x)}\n"
    )


# A `**u8` from a written `-> **u8` and from `vec_as_ptr<**u8>` (T = **u8,
# a `***u8` return), each read through a let-inferred local and a bare call.
DEEPER = (
    for_header.GVEC
    + "fn f(p: **u8) -> **u8\n    return p\n\n"
    + "pub fn main() -> i32\n"
    + "    var a: [3]*u8\n    a[0] = c\"1\"\n    a[1] = c\"2\"\n    a[2] = c\"7\"\n"
    + "    let i: i64 = 2\n"
    + "    let pp = f(@a[0])\n"
    + "    var v: Vec<**u8> = vec_new<**u8>()\n"
    + "    vec_push<**u8>(@&v, @a[0])\n    vec_push<**u8>(@&v, @a[1])\n    vec_push<**u8>(@&v, @a[2])\n"
    + "    let q = vec_as_ptr<**u8>(@v)\n"
    + "    var t: i32 = *(*(pp + i)) as i32 - 48\n"
    + "    t = t + (**(*(q + i)) as i32 - 48) * 3\n"
    + "    t = t + (**(*(vec_as_ptr<**u8>(@v) + 1)) as i32 - 48) * 30\n"
    + "    return t\n"
)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("pointee", sorted(POINTEES))
@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_generic_call_operand_strides_by_element(run_with, compiler, pointee, shape):
    assert run_with(compiler, f"{pointee}_{shape}", _program(pointee, shape)) == 7


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_ptr_ptr_call_results_stride_by_pointer(run_with, compiler):
    assert run_with(compiler, "deeper", DEEPER) == 88


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
def test_unknown_element_size_is_a_located_error(compile_with, compiler):
    """`get() + i` with `get() -> *Opaque` was a silent raw byte add."""
    prog = ("extern fn get() -> *Opaque\n\npub fn main() -> i32\n    let i: i64 = 1\n"
            "    let p: i64 = (get() + i) as i64\n    return 0\n")
    comp, ll, _ = compile_with(compiler, "opaque", prog)
    assert comp.returncode != 0
    assert "5:19: error: ritz1 cannot emit: pointer arithmetic: element size of pointee unknown for 'get'" in comp.stderr
