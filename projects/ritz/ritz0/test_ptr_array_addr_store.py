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
