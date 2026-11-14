"""AGAST #3036: `a[i] = @&n` into a `[N]*T` array: ritz1 emitted IR clang refuses.

    pub fn main() -> i32
        var n: i32 = 1
        var a: [2]*i32       # a global `var a: [2]*i32` too
        a[0] = @&n
        return 0

ritz1 wrote `inttoptr i64 %.1 to ptr` where `%.1` is n's alloca, already a
`ptr`, and clang refused the module ("defined with type 'ptr' but expected
'i64'").  Going through a pointer local (`var p: *i32 = @&n` / `a[0] = p`)
worked; ritz0 ran it.

Each row stores an address into a pointer array, then reads the element back
and writes through it, so a store of the wrong address (or of a copy) changes
the exit code.  Rows: local / global array, `@&n` / `@n`, scalar / struct
pointee.  All three compilers run each row, so they stay in agreement.

AGAST #3170: the same store into a `[N]*T` struct field (local, global, via
`@&H`) and through a `**T` field (`h.f[i] = @&n`).
"""

import pytest
from test_ref_into_value import COMPILERS, _run

# AGAST #2806: each test's rows share one compile per compiler (batching.py).
pytestmark = [pytest.mark.integration, pytest.mark.batched]

_STRUCT = "struct S\n    v: i32\n\n"

# pointee -> (declarations, the local's declaration, element type, how to read/write it)
POINTEES = {
    "scalar": ("", "    var n: i32 = 1\n", "*i32", "*{e}"),
    "struct": (_STRUCT, "    var n = S { v: 1 }\n", "*S", "{e}.v"),
}

# How the address is taken.
ADDRS = {"mut": "@&n", "shared": "@n"}


def _program(where: str, pointee: str, addr: str) -> str:
    decls, local, ty, place = POINTEES[pointee]
    arr = "a" if where == "local" else "G"
    if where == "global":
        decls += f"var G: [2]{ty}\n\n"
    body = local
    if where == "local":
        body += f"    var a: [2]{ty}\n"
    body += f"    {arr}[1] = {ADDRS[addr]}\n"
    # Read the element back through the array.
    body += f"    if {place.format(e=f'{arr}[1]')} != 1\n        return 1\n"
    # Write through a copy of the stored pointer: it must reach `n`.
    body += f"    let p: {ty} = {arr}[1]\n"
    body += f"    {place.format(e='p')} = 7\n"
    body += f"    if {place.format(e='n') if pointee == 'struct' else 'n'} != 7\n        return 2\n"
    body += "    return 0\n"
    return f"{decls}fn f() -> i32\n{body}\npub fn main() -> i32\n    f()\n"


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("addr", sorted(ADDRS))
@pytest.mark.parametrize("pointee", sorted(POINTEES))
@pytest.mark.parametrize("where", ["global", "local"])
def test_an_address_stored_into_a_pointer_array(tmp_path, compiler, where, pointee, addr):
    name = f"{where}_{pointee}_{addr}"
    assert _run(compiler, tmp_path, name, _program(where, pointee, addr)) == 0


# AGAST #3170: the same store into a `[N]*T` FIELD of a struct: a local
# struct, a global one, and one reached through an `@&H` reference.  ritz1
# narrowed the element with inttoptr there too (emit_field_array_elem_store).
FIELD_PLACES = {
    "local": ("", "    var h: H\n", "h"),
    "global": ("var GH: H\n\n", "", "GH"),
    "ref": ("", "    var h: H\n    let r: @&H = @&h\n", "r"),
}


def _field_program(where: str, pointee: str, addr: str) -> str:
    decls, local, ty, place = POINTEES[pointee]
    gdecl, holder, base = FIELD_PLACES[where]
    decls += f"struct H\n    a: [2]{ty}\n\n" + gdecl
    elem = f"{base}.a[1]"
    body = local + holder
    body += f"    {elem} = {ADDRS[addr]}\n"
    body += f"    if {place.format(e=elem)} != 1\n        return 1\n"
    body += f"    let p: {ty} = {elem}\n"
    body += f"    {place.format(e='p')} = 7\n"
    body += f"    if {place.format(e='n') if pointee == 'struct' else 'n'} != 7\n        return 2\n"
    body += "    return 0\n"
    return f"{decls}fn f() -> i32\n{body}\npub fn main() -> i32\n    f()\n"


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("addr", sorted(ADDRS))
@pytest.mark.parametrize("pointee", sorted(POINTEES))
@pytest.mark.parametrize("where", sorted(FIELD_PLACES))
def test_an_address_stored_into_a_pointer_array_field(tmp_path, compiler, where, pointee, addr):
    name = f"field_{where}_{pointee}_{addr}"
    assert _run(compiler, tmp_path, name, _field_program(where, pointee, addr)) == 0


def _ptr_field_program(pointee: str, addr: str) -> str:
    """`h.f[1] = @&n` where `f: **T` points into a local `[2]*T` (#3170)."""
    decls, local, ty, place = POINTEES[pointee]
    decls += f"struct P\n    f: *{ty}\n\n"
    body = local + f"    var a: [2]{ty}\n    var h: P\n    h.f = @a[0]\n"
    body += f"    h.f[1] = {ADDRS[addr]}\n"
    body += f"    if {place.format(e='a[1]')} != 1\n        return 1\n"
    body += f"    let p: {ty} = h.f[1]\n"
    body += f"    {place.format(e='p')} = 7\n"
    body += f"    if {place.format(e='n') if pointee == 'struct' else 'n'} != 7\n        return 2\n"
    body += "    return 0\n"
    return f"{decls}fn f() -> i32\n{body}\npub fn main() -> i32\n    f()\n"


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("addr", sorted(ADDRS))
@pytest.mark.parametrize("pointee", sorted(POINTEES))
def test_an_address_stored_through_a_pointer_to_pointer_field(tmp_path, compiler, pointee, addr):
    name = f"ptrfield_{pointee}_{addr}"
    assert _run(compiler, tmp_path, name, _ptr_field_program(pointee, addr)) == 0
