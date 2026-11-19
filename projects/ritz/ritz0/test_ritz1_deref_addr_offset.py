"""AGAST #4249: `*(@a[0] + i)` reads and writes one element on ritz1.

`get_expr_type`'s OP_DEREF arm typed a `ptr + offset` operand only when
the base was an identifier, a member or `*pp`; an `@a[0]` / `@x` base fell
to the TYPE_I64 default.  So `*(@out[0] + i) == 10` with `out: [N]u8`
loaded 8 bytes and matched a newline only when the next seven were zero:
21_ls's test_ls_one_per_line counted one line of `ls -1` output for six.
A store through the same shape wrote eight bytes over the neighbours.
The base's inline pointee (inline_deref_scalar_pointee, AGAST #2119) is
what `*@a[i]` already loaded; the offset form now uses it too.

`@x.buf[0] + i` with `buf: [N]T` a struct field also stepped `i` bytes, not
`i` elements: index_elem_size had no member arm (`field_and_sub`).
"""

import pytest
from test_ritz1_builtin_struct_shadow import _run_pkg

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

HEAD = """\
struct W
    buf: [4]u32

"""

# name: main's body; each returns 0 when every element access is one element.
PROGRAMS = {
    # The 21_ls loop: u8 elements, a newline count over the buffer.
    "u8_count": (
        "    var out: [8]u8\n"
        "    out[0] = 97\n"
        "    out[1] = 10\n"
        "    out[2] = 98\n"
        "    out[3] = 10\n"
        "    out[4] = 99\n"
        "    out[5] = 10\n"
        "    var i: i64 = 0\n"
        "    var nl: i64 = 0\n"
        "    while i < 6\n"
        "        if *(@out[0] + i) == 10\n"
        "            nl += 1\n"
        "        i += 1\n"
        "    if nl != 3\n"
        "        return 1\n"
        "    0\n"
    ),
    # A store writes one byte, leaving its neighbour.
    "u8_store": (
        "    var out: [4]u8\n"
        "    out[1] = 10\n"
        "    out[2] = 98\n"
        "    let i: i64 = 1\n"
        "    *(@out[0] + i) = 11\n"
        "    if out[1] != 11 or out[2] != 98\n"
        "        return 1\n"
        "    0\n"
    ),
    # u32 elements: a value above i32's range, read and written.
    "u32": (
        "    var w: [4]u32\n"
        "    w[1] = 4000000000\n"
        "    w[2] = 7\n"
        "    let i: i64 = 1\n"
        "    if *(@w[0] + i) != 4000000000\n"
        "        return 1\n"
        "    *(@w[0] + 2) = 9\n"
        "    if w[2] != 9 or w[1] != 4000000000\n"
        "        return 2\n"
        "    0\n"
    ),
    # A struct field's array, and a negative i16 through `-`.
    "field_and_sub": (
        "    var x: W = W { buf: [1, 2, 3, 4] }\n"
        "    let i: i64 = 1\n"
        "    if *(@x.buf[0] + i) != 2\n"
        "        return 1\n"
        "    var h: [3]i16\n"
        "    h[0] = 1\n"
        "    h[1] = -2\n"
        "    h[2] = 3\n"
        "    if *(@h[2] - i) != -2\n"
        "        return 2\n"
        "    0\n"
    ),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_deref_addr_offset_is_one_element(tmp_path, compiler, name):
    program = HEAD + "pub fn main() -> i32\n" + PROGRAMS[name]
    assert _run_pkg(compiler, tmp_path, name, program) == 0
