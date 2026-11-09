"""AGAST #2526: `*f()`, `*(f() + i)` and `*(x as *S)` load the struct pointee.

With `struct D { a: i64, b: i64 }`, `var g_p: *D` and `fn gp() -> *D`, ritz1
compiled each of these to `load i64`, which clang rejects as soon as the value
meets a `%D` slot ("'%.N' defined with type 'i64' but expected '%D'"):

    let d: D = *(gp() + 1)
    let d: D = *gp()
    let d: D = *(g_p as *D)
    let d: D = *((g_p + 1) as *D)

deref_pointee_struct_name had no arm for a call or a cast, so the deref was
typed non-struct and fell through.  The same resolver sizes `+` on a `*S`
operand and types `*p = v` stores, so those are pinned here too.

Every program returns 7 only when the right element was read in full
(a + b = 3 + 4).  ritz0 is the oracle.
"""

import pytest

import test_ritz1_for_header as for_header

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]
EXPECTED = 7

PRELUDE = """\
struct D
    a: i64
    b: i64

var g_arr: [3]D
var g_p: *D = null

fn gp() -> *D
    return @g_arr[0]

fn at(i: i64) -> *D
    return @g_arr[0] + i

fn fill()
    g_arr[1].a = 3
    g_arr[1].b = 4
    g_p = @g_arr[0]

"""


def _main(body: str) -> str:
    lines = "\n".join("    " + ln for ln in body.strip("\n").split("\n"))
    return PRELUDE + "pub fn main() -> i32\n    fill()\n" + lines + "\n"


# The ticket's four shapes, then the neighbours the same arms cover.
LOADS = {
    "call_ptr_add": "let d: D = *(gp() + 1)\nreturn (d.a + d.b) as i32",
    "call": "let d: D = *at(1)\nreturn (d.a + d.b) as i32",
    "call_bare_gp": "let d: D = *gp()\nreturn (d.a + d.b + 7) as i32",
    "cast_global": "g_p = @g_arr[1]\nlet d: D = *(g_p as *D)\nreturn (d.a + d.b) as i32",
    "cast_of_sum": "let d: D = *((g_p + 1) as *D)\nreturn (d.a + d.b) as i32",
    # The cast names the stride of the `+` it heads.
    "sum_of_cast": "let d: D = *((g_p as *D) + 1)\nreturn (d.a + d.b) as i32",
    "cast_from_bytes": (
        "let raw: *u8 = @g_arr[1] as *u8\nlet d: D = *(raw as *D)\nreturn (d.a + d.b) as i32"
    ),
    "call_sub_chain": "let d: D = *(gp() + 2 - 1)\nreturn (d.a + d.b) as i32",
    # `(*X).f` reaches the field through emit_deref_operand_ptr.
    "call_member": "return ((*(gp() + 1)).a + (*at(1)).b) as i32",
    "cast_member": "g_p = @g_arr[1]\nreturn ((*(g_p as *D)).a + (*((g_p as *D) + 0)).b) as i32",
}

# `*p = v` through the same shapes stores the whole %D.
STORES = {
    "store_call": "var v: D\nv.a = 3\nv.b = 4\n*at(2) = v\nreturn (g_arr[2].a + g_arr[2].b) as i32",
    "store_call_ptr_add": (
        "var v: D\nv.a = 3\nv.b = 4\n*(gp() + 2) = v\nreturn (g_arr[2].a + g_arr[2].b) as i32"
    ),
    "store_cast": (
        "var v: D\nv.a = 3\nv.b = 4\n*((g_p + 2) as *D) = v\nreturn (g_arr[2].a + g_arr[2].b) as i32"
    ),
}

# Primitive pointees keep their width-specific loads: a call or cast to
# `*i32` must not start loading anything wider.  (`f() + k` / `(x as *i32)
# + k` on a primitive pointee still steps bytes on ritz1: AGAST #2540.)
CONTROLS = {
    "prim_call": (
        "var buf: [4]i32\nbuf[0] = 7\nbuf[1] = 9\nlet p: *i32 = @buf[0]\n"
        "return *ident(p)"
    ),
    "prim_cast": (
        "var buf: [4]i32\nbuf[1] = 7\nbuf[2] = 9\nlet raw: *u8 = @buf[1] as *u8\n"
        "return *(raw as *i32)"
    ),
}

IDENT_FN = """\
fn ident(p: *i32) -> *i32
    return p

"""

ALL = {
    **{k: _main(v) for k, v in LOADS.items()},
    **{k: _main(v) for k, v in STORES.items()},
    **{k: IDENT_FN + _main(v) for k, v in CONTROLS.items()},
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ALL))
def test_deref_of_call_or_cast_reads_the_struct(run_with, compiler, name):
    assert run_with(compiler, name, ALL[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
@pytest.mark.parametrize("name", ["call_ptr_add", "cast_of_sum", "sum_of_cast"])
def test_the_load_is_a_struct_stepped_by_its_size(compile_with, compiler, name):
    """The deref is a `load %D`; the `+` scales by sizeof(D) = 16."""
    comp, ll, _ = compile_with(compiler, name, ALL[name])
    assert comp.returncode == 0, comp.stdout + comp.stderr
    body = ll.read_text().split("@main(", 1)[1].split("\n}", 1)[0]
    assert "= load %D, ptr" in body, body
    assert "mul i64 " in body and ", 16\n" in body, body
