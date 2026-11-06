"""
What a reference may not do to a by-value slot (LANGUAGE_SPEC §13.2-13.4,
LARB ruling R1, AGAST #2336).

The wording is shared: ritz1 prints the same strings (ownership.ritz), and
ritz0/test_ref_into_value.py holds all three compilers to them.
"""

# An `@T`, `@&T` or `*T` where a `T` goes. There's no implicit deref.
REF_INTO_VALUE = "a reference or pointer doesn't fit a by-value slot: write `*` to read through it"

# `@x` where a `T` goes: x already is one.
ADDR_INTO_VALUE = "`@x` doesn't fit a by-value slot: drop the `@`"

# `*r`, `r.f`, `p[i]` or a by-value `self` of a move-only value, by value.
MOVE_OUT_OF_REF = "cannot move out of a reference"
