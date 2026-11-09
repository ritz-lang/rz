"""`R.NotFound` is an `R`, even if another enum has a variant called `R` (AGAST #2534).

nexus has both of these:

    enum RepoError
        NotFound
    enum ServiceError
        NotFound
        RepoError(RepoError)

ritz0's checker typed the receiver `RepoError` as the variant
`ServiceError.RepoError`, so `let err = RepoError.NotFound` was a `ServiceError`.
#2368's exact-type rule then refused `@err` into `*RepoError`: "a reference to one
type doesn't fit a reference to another". ritz1 never made this mistake. Each row
runs on all three compilers and must exit 3.
"""

import pytest

from test_ref_into_value import COMPILERS, _run

pytestmark = pytest.mark.integration

# `R` is a variant of `S` as well as an enum, and `S` has a `NotFound` too.
PROGRAM = """\
enum R
    NotFound
    {other}

enum S
    NotFound
    Other(i32)
    R(R)

fn is_nf(e: {slot}) -> bool
    match *e
        R.NotFound => true
        _ => false

pub fn main() -> i32
    {bind} e = R.NotFound
    if is_nf({addr}e)
        return 3
    0
"""

ENUMS = {"plain": "Gone", "tagged": "Gone(i32)"}
# `@&e` needs a `var`; the others are the nexus shape, a `let`.
SLOTS = {"pointer": ("*R", "@", "let"), "shared": ("@R", "@", "let"), "mutable": ("@&R", "@&", "var")}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("slot", sorted(SLOTS))
@pytest.mark.parametrize("enum", sorted(ENUMS))
def test_an_enum_receiver_is_the_enum_not_a_variant(tmp_path, compiler, slot, enum):
    ty, addr, bind = SLOTS[slot]
    src = PROGRAM.format(other=ENUMS[enum], slot=ty, addr=addr, bind=bind)
    assert _run(compiler, tmp_path, f"{enum}_{slot}", src) == 3


# The variant itself still builds an `S`: `S.R(x)` fits `*S`.
VARIANT_STILL_WORKS = """\
enum R
    NotFound
    Gone

enum S
    NotFound
    R(R)

fn wrapped(s: *S) -> i32
    match *s
        S.R(r) => 3
        _ => 1

pub fn main() -> i32
    let s = S.R(R.Gone)
    wrapped(@s)
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_the_variant_named_like_an_enum_still_builds_its_own_enum(tmp_path, compiler):
    assert _run(compiler, tmp_path, "variant_still_works", VARIANT_STILL_WORKS) == 3
