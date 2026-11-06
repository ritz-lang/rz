"""
What a reference may not do to a by-value slot, and a value to a reference slot
(LANGUAGE_SPEC §13.2-13.4, LARB ruling R1, AGAST #2336, #2337).

The wording is shared: ritz1 prints the same strings (ownership.ritz), and
ritz0/test_ref_into_value.py and test_value_into_ref.py hold all three compilers
to them.
"""

# An `@T`, `@&T` or `*T` where a `T` goes. There's no implicit deref.
REF_INTO_VALUE = "a reference or pointer doesn't fit a by-value slot: write `*` to read through it"

# `@x` where a `T` goes: x already is one.
ADDR_INTO_VALUE = "`@x` doesn't fit a by-value slot: drop the `@`"

# A `T` where an `@T`, `@&T` or `*T` goes, `:&` params included. A reference is
# always written, and only a place into a `:&` param is borrowed for you.
VALUE_INTO_SHARED_REF = "a value doesn't fit a reference slot: write `@x` to borrow it"
VALUE_INTO_MUT_REF = "a value doesn't fit a reference slot: write `@&x` to borrow it"

# `@&h` of an `h: *C` where an `@&*D` goes. A `*C` can't be stored through it.
REF_TO_OTHER_POINTER = "a reference to one pointer type doesn't fit a reference to another"

# `*r`, `r.f`, `p[i]` or a by-value `self` of a move-only value, by value.
MOVE_OUT_OF_REF = "cannot move out of a reference"
