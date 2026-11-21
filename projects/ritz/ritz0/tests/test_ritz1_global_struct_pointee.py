"""AGAST #1554: a global `*S` / `@S` / `@&S` names its pointee S.

A module-level pointer keeps S in GlobalVarDef.pointee_type_name (#1908);
type_name names only a by-value `var g: S`.  Readers that asked type_name
about a pointer global were told nothing:

* `g_hp.items + 1` through a `*H` global (`items: *D`) strode 1 byte and ran,
  returning garbage (SILENT); `*(g_hp.items + 1)` loaded i64 into a %D slot
* `*g` on an `@D` / `@&D` global loaded i64, and `g.a` was
  "unhandled EXPR_MEMBER"
* `sizeof(*g_p)` / `sizeof(g_p[0])` could not determine the type

#2359 fixed the ticket's own repro (`*(g_p + 1)`) and the stride of `g_p + i`;
they are pinned here on all three compilers.  `:&` is a parameter mode only
(LANGUAGE_SPEC §13.4), so `@&D` is the global form of a mutable borrow.

Every program returns 7 only when the right D was reached and read in full
(a = 3, b = 4).  ritz0 is the oracle.
"""

import pytest

import test_ritz1_for_header as for_header

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

PRELUDE = "struct D\n    a: i64\n    b: i64\n\nstruct H\n    items: *D\n    n: i64\n\n"

# `arr[k]` holds a = 3, b = 4; the rest is zeroed.
def _arr(n: int, k: int) -> str:
    return f"    var arr: [{n}]D\n    arr[{k}].a = 3\n    arr[{k}].b = 4\n"


SHAPES = {
    # The ticket's repro (#2359).
    "ptr_deref_add": ("var g_p: *D = null\n", _arr(2, 1)
                      + "    g_p = @arr[0]\n    let d: D = *(g_p + 1)\n    return (d.a + d.b) as i32\n"),
    # `g + i` strides sizeof(D), chained and subtracted.
    "ptr_stride": ("var g_p: *D = null\n", _arr(3, 2)
                   + "    g_p = @arr[0]\n    let q: *D = (g_p + 1) + 1\n    let r: *D = (g_p + 3) - 1\n"
                   + "    return (q.a + r.b) as i32\n"),
    # A struct-pointer field reached through a `*H` global.
    "ptr_global_field_deref": ("var g_hp: *H = null\n", _arr(2, 1)
                               + "    var h: H\n    h.items = @arr[0]\n    g_hp = @h\n"
                               + "    let d: D = *(g_hp.items + 1)\n    return (d.a + d.b) as i32\n"),
    "ptr_global_field_stride": ("var g_hp: *H = null\n", _arr(2, 1)
                                + "    var h: H\n    h.items = @arr[0]\n    g_hp = @h\n"
                                + "    let q: *D = g_hp.items + 1\n    return (q.a + q.b) as i32\n"),
    # ... and through a by-value `H` global, which already worked.
    "struct_global_field_deref": ("var g_h: H\n", _arr(2, 1)
                                  + "    g_h.items = @arr[0]\n"
                                  + "    let d: D = *(g_h.items + 1)\n    return (d.a + d.b) as i32\n"),
    # Reference globals.
    "ref_global_deref": ("var g_r: @D\n", _arr(1, 0)
                         + "    g_r = @arr[0]\n    let d: D = *g_r\n    return (d.a + d.b) as i32\n"),
    "ref_global_member": ("var g_r: @D\n", _arr(1, 0)
                          + "    g_r = @arr[0]\n    return (g_r.a + g_r.b) as i32\n"),
    "mut_ref_global_deref": ("var g_m: @&D\n", _arr(1, 0)
                             + "    g_m = @&arr[0]\n    let d: D = *g_m\n    return (d.a + d.b) as i32\n"),
    "mut_ref_global_member_store": ("var g_m: @&D\n", "    var x: D\n    g_m = @&x\n"
                                    + "    g_m.a = 3\n    g_m.b = 4\n    return (x.a + x.b) as i32\n"),
    # sizeof(D) = 16; 16 - 9 = 7.
    "sizeof_pointee": ("var g_p: *D = null\nvar g_r: @D\n",
                       "    return ((sizeof(*g_p) + sizeof(g_p[0]) + sizeof(*g_r)) - 41) as i32\n"),
}


def _program(shape: str) -> str:
    globals_, body = SHAPES[shape]
    return PRELUDE + globals_ + "\npub fn main() -> i32\n" + body


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_global_struct_pointee(run_with, compiler, shape):
    assert run_with(compiler, shape, _program(shape)) == 7
