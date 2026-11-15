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

# `T.m(x)` where `m` takes `self`: a type isn't a receiver (AGAST #2292).
# ritz1 prints the same words, with the method's name (emitter_expr_call.ritz).
def static_call_of_self(method: str) -> str:
    return f"Static method call Type.method() but method '{method}' expects 'self' parameter"


# The receiver of a method whose `self` is a pointer to a pointer (`self: **C`),
# when it isn't a place one level short of `self` to borrow, or `self`'s type
# (LANGUAGE_SPEC §5.4, AGAST #2403): a call result, or a `C` for a `**C`.
RECEIVER_SHORT_OF_SELF = "a receiver of a pointer `self` must be a place one level short of it, or have its levels"

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


# A call's by-value result is no place (LARB R9, Aaron's ruling on AGAST #2518):
# a store into it is lost when the statement ends. `mk().x = 1`, `mk().n[1] = 3`,
# `mk().x += 1`.
STORE_INTO_TEMP = "a store into a call's temporary is lost: bind the call to a local first"

# `mk().bump()` with `self: @&T` or `self:& T`: R1 exception 4's auto-ref makes
# it the same store. A read-only method (`mk().get()`) is a read and stays.
MUT_SELF_ON_TEMP = "a method that writes `self` can't take a call's temporary: bind the call to a local first"

# `@mk()`, `@&mk()`, `@mk().f`, `@mk().n[1]` anywhere but directly as a call's
# argument, where the temporary lives until that call returns (AGAST #2518, #3050).
ADDR_OF_TEMP = "`@` of a call's temporary outlives it: bind the call to a local first, or pass it straight to a call"


# `x.m(...)` on a user type with no `m` in an `impl` for it (or a trait impl):
# method syntax reaches only impl methods, and the ritzlib types in the UFCS
# table (ufcs.py) until #3252. A free `foo_m` is not a method (Aaron's ruling
# on AGAST #3244). `free_call` is the call to write instead, when there is a
# free fn `<lowercased type>_<m>` to call. ritz1 prints the same words
# (emitter_expr_call.ritz, refuse_no_method).
def no_method(method: str, type_name: str, free_call: str | None = None) -> str:
    hint = f"declare it in `impl {type_name}`"
    if free_call:
        hint += f", or call `{free_call}`"
    return f"no method `{method}` on `{type_name}`: {hint}"
