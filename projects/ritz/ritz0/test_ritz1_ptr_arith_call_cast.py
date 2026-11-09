"""AGAST #2540: `f() + k` and `(x as *T) + k` stride by sizeof(T).

With `fn ident(p: *i32) -> *i32` and `buf: [4]i32`, ritz1 compiled

    *(ident(p) + 2)
    *((raw as *i32) + 2)

to a raw BYTE add (`+ 2`, not `+ 8`) and silently read the wrong element:
ptr_arith_elem_size had no arm for a call or a cast operand.  #2526 fixed the
struct-pointee version (deref_pointee_struct_name sizes a `*S` first); this
pins every primitive width.  ritz0 is the oracle.

Each program fills `buf` with 1, 2, 7, 4 and returns the element it reaches,
so it returns 7 only when the `+` stepped whole elements.  `i8` steps one byte
either way and is the control.
"""

import re

import pytest

import test_ritz1_for_header as for_header

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]
EXPECTED = 7

# element type -> (literal suffix, sizeof)
TYPES = {
    "i8": ("", 1),
    "i16": ("", 2),
    "i32": ("", 4),
    "i64": ("", 8),
    "f64": (".0", 8),
}

# How the pointer is reached, and the expression that should land on buf[2].
SHAPES = {
    "call_add": "*(ident(p) + 2)",
    "call_sub": "*(ident(@buf[3]) - 1)",
    "call_chain": "*(ident(p) + 3 - 1)",
    "cast_add": "*((raw as *{T}) + 2)",
    "cast_sub": "*((@buf[3] as *u8 as *{T}) - 1)",
    "cast_chain": "*((raw as *{T}) + 3 - 1)",
}


def _program(ty: str, shape: str) -> str:
    suffix, _ = TYPES[ty]
    expr = SHAPES[shape].replace("{T}", ty)
    fill = "\n".join(f"    buf[{i}] = {v}{suffix}" for i, v in enumerate((1, 2, 7, 4)))
    return (
        f"fn ident(p: *{ty}) -> *{ty}\n"
        "    return p\n"
        "\n"
        "pub fn main() -> i32\n"
        f"    var buf: [4]{ty}\n"
        f"{fill}\n"
        f"    let p: *{ty} = @buf[0]\n"
        "    let raw: *u8 = @buf[0] as *u8\n"
        f"    let v: {ty} = {expr}\n"
        "    return v as i32\n"
    )


CASES = [(ty, shape) for ty in TYPES for shape in SHAPES]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ty,shape", CASES)
def test_call_or_cast_operand_strides_by_element(run_with, compiler, ty, shape):
    name = f"{ty}_{shape}"
    assert run_with(compiler, name, _program(ty, shape)) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
@pytest.mark.parametrize("ty", ["i16", "i32", "f64"])
@pytest.mark.parametrize("shape", ["call_add", "cast_add"])
def test_the_offset_is_scaled_by_sizeof(compile_with, compiler, ty, shape):
    """The `+ 2` is a `mul i64 .., sizeof(T)` before the element GEP."""
    _, size = TYPES[ty]
    comp, ll, _ = compile_with(compiler, f"ir_{ty}_{shape}", _program(ty, shape))
    assert comp.returncode == 0, comp.stdout + comp.stderr
    body = ll.read_text().split("@main(", 1)[1].split("\n}", 1)[0]
    assert f", {size}\n" in body and "mul i64 " in body, body


LLVM = {"i16": "i16", "i32": "i32", "f64": "double"}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
@pytest.mark.parametrize("ty", sorted(LLVM))
@pytest.mark.parametrize("shape", ["call_bare", "call_add", "cast_add", "cast_chain"])
def test_the_load_is_the_element_width(compile_with, compiler, ty, shape):
    """`*f()` / `*(f() + k)` / `*((x as *T) + k)` load a T, never an i64.

    They loaded i64 for every T: an 8-byte read of a 2- or 4-byte element
    (past the end of the buffer at its last element), and clang rejected
    `store double` of the i64 for `*f64`.
    """
    shapes = {**SHAPES, "call_bare": "*ident(@buf[2])"}
    expr = shapes[shape].replace("{T}", ty)
    prog = _program(ty, "call_add").replace(SHAPES["call_add"], expr)
    comp, ll, _ = compile_with(compiler, f"ld_{ty}_{shape}", prog)
    assert comp.returncode == 0, comp.stdout + comp.stderr
    body = ll.read_text().split("@main(", 1)[1].split("\n}", 1)[0]
    # The deref loads through an `inttoptr` of the computed address; the
    # `p` / `raw` locals are i64 slots and load i64 legitimately.
    addrs = set(re.findall(r"(%\.\d+) = inttoptr i64 ", body))
    loads = re.findall(r"= load (\S+), ptr (%\.\d+)", body)
    derefs = [t for t, a in loads if a in addrs]
    assert derefs == [LLVM[ty]], body
