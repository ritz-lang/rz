"""Which integers convert implicitly into a float slot, and the words for a
refusal (LANGUAGE_SPEC §7.5, AGAST #2945).

A non-literal integer converts implicitly only when every value of its type is
exact in the float: f64 has a 53-bit significand, f32 a 24-bit one.  Anything
else needs an explicit `as`.  ritz1's float_slot.ritz has the same table and
prints the same words.
"""

# Float type name -> the widest integer, in bits, every value of which it holds.
EXACT_BITS = {'f64': 32, 'f32': 16}


def is_exact(bits: int, float_name: str) -> bool:
    """Is every `bits`-wide integer exact in `float_name`?"""
    return bits <= EXACT_BITS[float_name]


def int_into_float_inexact(src: str, dst: str) -> str:
    return (f"implicit conversion from `{src}` to `{dst}` can lose precision: "
            f"write `<expr> as {dst}`")


def mixed_float_compare(left: str, right: str) -> str:
    """An f32 compared with an f64 (§7.2, AGAST #3607): neither precision is
    the obvious one, so the writer picks it.  ritz1's float_compare.ritz
    prints the same words."""
    return (f"cannot compare `{left}` with `{right}`: "
            f"write `as` to choose the precision")


def f64_into_f32() -> str:
    """A non-literal f64 into an f32 slot (§7.5 "Float narrowing", LARB R70,
    AGAST #3802): the same words as an inexact integer."""
    return int_into_float_inexact('f64', 'f32')
