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

# `@x` or `@&x` where an `@U`, `@&U` or `*U` of another `U` goes: the reference
# would be reinterpreted. Exactly the same type, not the same width (Aaron's
# ruling on AGAST #2368): `@&u32` doesn't fit `@&i32` either.
REF_TO_OTHER_TYPE = "a reference to one type doesn't fit a reference to another: cast it with `as`"

# `*r`, `r.f`, `p[i]` or a by-value `self` of a move-only value, by value.
MOVE_OUT_OF_REF = "cannot move out of a reference"

# `fn drop(self)`: its own `self` would drop when it returned, and call it again.
DROP_BY_VALUE = "`drop` can't take `self` by value: it would drop itself: write `self: @&T`"

# `p.f = v`, `p[i] = v` or `*p = v` through an `@T`, or a chain of fields from one.
WRITE_THROUGH_SHARED = "cannot write through an `@T`: make it `@&T`"

# An `@T` where an `@&T` goes: a value, or a receiver of a `self: @&T` method.
SHARED_INTO_MUT = "an `@T` doesn't fit an `@&T` slot: make it `@&T`"

# `@&x` of a place behind an `@T`, or `@x` of one where an `@&T` or `:&` goes.
BORROW_THROUGH_SHARED = "cannot borrow through an `@T` as mutable: make it `@&T`"

# `@x` where an `@&T` or `:&` goes: `@x` is shared, and mutation is written
# (LANGUAGE_SPEC §13.3, Aaron's ruling on AGAST #2339).
ADDR_INTO_MUT = "`@x` is shared and doesn't fit an `@&T` or `:&` slot: write `@&x`"

# A return or tail that definitely refers to a local root (LANGUAGE_SPEC §13.5,
# LARB ruling R2, AGAST #2340). `name` is the root, however it was reached.
def returns_local(name: str) -> str:
    return f"cannot return a reference to local `{name}`: it ends with the fn"


# `@x` of a `let`'s own storage where an `@&T` or `:&` goes: the emitter's wording
# for `@&x` of one, since both ask for the same thing.
def let_into_mut(name: str) -> str:
    return f"cannot borrow `let` binding `{name}` as mutable; declare it `var`"
