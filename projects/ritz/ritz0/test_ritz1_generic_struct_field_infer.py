"""AGAST #4299: a field of a generic-struct local binds a generic call's T.

With `var b: Bag<Nope>`, `total(@b.v)` (`fn total<T>(x: @T)`) infers T = Nope
on ritz0.  ritz1's generic_infer typed `b.v` only through a concrete struct,
and `Bag$Nope` isn't one before monomorphize runs, so it said "can't infer
`T` for `total`".  gi_member_type now reads the field off the generic
template and substitutes the instance's args (a struct field `T`, a
primitive one, and the second param of a two-param generic).
"""

import pytest
from test_ritz1_builtin_struct_shadow import _run_pkg

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

HEAD = """\
struct Nope
    a: i64
    b: i64

struct Bag<T>
    v: T

struct Pair<K, V>
    k: K
    v: V

fn total<T>(x: @T) -> i64
    sizeof(T) as i64

fn size<T>(x: T) -> i64
    sizeof(T) as i64

"""

# name: main's body; each returns 0 when T bound to the field's type.
PROGRAMS = {
    # The briefing's program: a struct T through a generic-struct local.
    "struct_field": (
        "    var b: Bag<Nope>\n"
        "    b.v.a = 1\n"
        "    if total(@b.v) != 16\n"
        "        return 1\n"
        "    0\n"
    ),
    # A primitive T, by value and by reference.
    "prim_field": (
        "    var b: Bag<i32>\n"
        "    b.v = 7\n"
        "    if size(b.v) != 4 or total(@b.v) != 4\n"
        "        return 1\n"
        "    0\n"
    ),
    # A two-param generic: each field takes its own param's arg.
    "two_param": (
        "    var p: Pair<u8, Nope>\n"
        "    p.k = 1\n"
        "    if total(@p.v) != 16 or size(p.k) != 1\n"
        "        return 1\n"
        "    0\n"
    ),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_generic_struct_field_binds_t(tmp_path, compiler, name):
    program = HEAD + "pub fn main() -> i32\n" + PROGRAMS[name]
    assert _run_pkg(compiler, tmp_path, name, program) == 0
