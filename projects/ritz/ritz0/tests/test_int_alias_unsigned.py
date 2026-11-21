"""AGAST #3695: an integer type alias keeps its target's signedness.

`type NodeId = u32` is another name for `u32`. ritz0 tested signedness on the
written name (`_is_unsigned_type` looked for 'u8'..'u64' and saw 'NodeId'), so
an alias of an unsigned type was treated as signed:

    type NodeId = u32
    const NONE: NodeId = 0xFFFFFFFF
    NONE != 0xFFFFFFFF          # ritz0: `sext i32 -1 to i64` -> true
    let x: NodeId = 0xFFFFFFFF  # ritz0: "implicit narrowing ... `i64`"

Found when tempest started building (#3609): its test_document.ritz
`test_node_id_none_is_max` is exactly the first row.

ritz1 was right throughout, so it is the oracle. Each program returns 0, or the
number of the first check that failed. Every row's control is the same body
with the alias replaced by its target, which all compilers already accepted.
"""

import pytest

from test_ritz1_for_iterable import run_with  # noqa: F401  (fixture)

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

ALIASES = "type Id32 = u32\ntype Id8 = u8\ntype Id64 = u64\n\n"

CASES = {
    # A const typed through the alias zero-extends when it meets a literal.
    "const_compare": (
        "const NONE: Id32 = 0xFFFFFFFF\n\n"
        "pub fn main() -> i32\n"
        "    if NONE != 0xFFFFFFFF\n        return 1\n"
        "    if not (NONE > 1)\n        return 2\n    0\n"
    ),
    # A literal that fits the unsigned target is not a narrowing.
    "literal_init": (
        "pub fn main() -> i32\n"
        "    let x: Id32 = 0xFFFFFFFF\n"
        "    if x != 0xFFFFFFFF\n        return 1\n"
        "    let b: Id8 = 255\n"
        "    if b != 255\n        return 2\n    0\n"
    ),
    # Unsigned shift, compare and divide on a local of the alias type.
    "arith": (
        "pub fn main() -> i32\n"
        "    let w: Id64 = 0xFFFFFFFFFFFFFFF8 as Id64\n"
        "    if w >> 60 != 15\n        return 1\n"
        "    if not (w > 1)\n        return 2\n"
        "    if w % 10 != 8\n        return 3\n    0\n"
    ),
}


def _control(body: str) -> str:
    """The same body with each alias spelled as its target."""
    return body.replace("Id32", "u32").replace("Id8", "u8").replace("Id64", "u64")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CASES))
def test_alias_of_unsigned_is_unsigned(run_with, compiler, name):  # noqa: F811
    """`type A = uN` behaves as `uN` in compares, literal fit and arithmetic."""
    assert run_with(compiler, name, ALIASES + CASES[name]) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CASES))
def test_unaliased_control(run_with, compiler, name):  # noqa: F811
    """Control: the same programs written with the target type pass."""
    assert run_with(compiler, f"{name}_ctl", _control(CASES[name])) == 0
