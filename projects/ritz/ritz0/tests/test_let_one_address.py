"""AGAST #2441, LARB R9: every binding has one address, `let` included.

A binding is a place with one address for as long as it lives, so `@x` is that
address every time, and a receiver taken by reference is `@x`: a `self: *T`
method on a `let` runs on the `let`, not on a copy.

A `let` can't be written directly, through `@&T` or `:&`, but a `*T` holding
`@x` isn't checked (§3.2), so a write through one reaches the `let`.

ritz0 kept a small `let` as an SSA value and spilled it to a fresh alloca at
every `@x`, so measured at 6e1d06e:

    let c; let p: *C = @c; let q: *C = @c; p == q   ritz0 false (0)
    let c; f(@c) with `f(p: *C)` writing p.x        ritz0 1: a copy changed
    let c; let p: *C = @c; p.x = 3; c.x             ritz0 1
    let n: i32 = 1; let p: *i32 = @n; *p = 3; n     ritz0 1
    let c; c.w() with `self: *C`                    ritz0 1

ritz1 and ritz1_selfhosted gave the answers below on every row already.
"""

import pytest

import test_ritz1_for_header as for_header

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

HEADER = """\
struct C
    x: i32
    y: i32

impl C
    fn w(self: *C)
        self.x = 3
    fn get(self: *C) -> i32
        return self.x

struct O
    c: C

fn f(p: *C)
    p.x = 3

fn peek(p: *C) -> i32
    return p.x

fn bump(p: *i32)
    *p = *p + 2

"""

LET_C = "    let c: C = C { x: 1, y: 7 }\n"

# The ticket's five rows, then the same rule in the positions they imply.
ROWS = {
    # Two `@c` are the same address.
    "two_at_are_equal": (LET_C + "    let p: *C = @c\n    let q: *C = @c\n"
                         "    if p == q\n        return 1\n    return 0\n", 1),
    # A callee writing through `*C` writes the `let`.
    "callee_writes_through": (LET_C + "    f(@c)\n    return c.x\n", 3),
    # A write through a `*C` holding `@c` reaches `c`.
    "write_through_ptr": (LET_C + "    let p: *C = @c\n    p.x = 3\n    return c.x\n", 3),
    # The same for a scalar `let`.
    "scalar_write_through_ptr": ("    let n: i32 = 1\n    let p: *i32 = @n\n"
                                 "    *p = 3\n    return n\n", 3),
    # A `self: *C` method runs on the `let`.
    "ptr_self_method": (LET_C + "    c.w()\n    return c.x\n", 3),
    # -- implied rows --
    # A receiver inside the `let` is inside its one address.
    "nested_receiver": ("    let o: O = O { c: C { x: 1, y: 7 } }\n    o.c.w()\n    return o.c.x\n", 3),
    # An untyped `let` too.
    "untyped_let": ("    let c = C { x: 1, y: 7 }\n    let p: *C = @c\n"
                    "    p.x = 3\n    return c.x\n", 3),
    # `@c.x` is inside `c`'s one address.
    "at_field": (LET_C + "    let p: *i32 = @c.x\n    *p = 3\n    return c.x\n", 3),
    "at_field_is_inside": (LET_C + "    let p: *C = @c\n    let q: *i32 = @c.y\n"
                           "    if q == @p.y\n        return 1\n    return 0\n", 1),
    # A scalar callee.
    "scalar_callee": ("    let n: i32 = 1\n    bump(@n)\n    bump(@n)\n    return n\n", 5),
    # A pointer-self read after the write sees it.
    "method_after_write": (LET_C + "    let p: *C = @c\n    p.x = 3\n    return c.get()\n", 3),
    # The `@c` comes after a read on a later iteration: that read sees the write.
    "loop_back_edge": ("    var i: i32 = 0\n    var sum: i32 = 0\n" + LET_C
                       + "    while i < 2\n        sum = sum + c.x\n"
                       "        let p: *C = @c\n        p.x = 3\n        i += 1\n"
                       "    return sum\n", 4),
    # A `let` bound in a branch, its address taken there.
    "in_a_branch": ("    var r: i32 = 0\n    if r == 0\n" + "    " + LET_C
                    + "        f(@c)\n        r = c.x\n    return r\n", 3),
    # Each iteration's `let` is a fresh binding, starting from its initialiser.
    "fresh_per_iteration": ("    var i: i32 = 0\n    var sum: i32 = 0\n    while i < 3\n"
                            "        let n: i32 = 1\n        bump(@n)\n"
                            "        sum = sum + n\n        i += 1\n    return sum\n", 9),
}

# Controls: a read-only use of `@x` leaves the `let` as it was.
CONTROLS = {
    "read_only_callee": (LET_C + "    let r = peek(@c)\n    return c.x + r\n", 2),
    "read_only_method": (LET_C + "    return c.get() + c.x\n", 2),
    "read_through_ptr": ("    let n: i32 = 4\n    let p: *i32 = @n\n    return *p + n\n", 8),
    "no_address_taken": (LET_C + "    return c.x + c.y\n", 8),
}


def _main(body: str) -> str:
    return f"{HEADER}fn main() -> i32\n{body}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(ROWS))
def test_a_let_has_one_address(run_with, row, compiler):
    body, want = ROWS[row]
    assert run_with(compiler, row, _main(body)) == want


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(CONTROLS))
def test_a_read_only_address_leaves_the_let(run_with, row, compiler):
    body, want = CONTROLS[row]
    assert run_with(compiler, row, _main(body)) == want


DROP = """\
var SEEN: i32 = 0

struct D
    x: i32

impl Drop for D
    fn drop(self: @&D)
        SEEN = SEEN + self.x

fn scope(write: bool)
    let d: D = D { x: 1 }
    let p: *D = @d
    if write
        p.x = 3

"""


# The `let`'s scope-end drop drops the one place, so it sees the write.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("write, want", [(True, 3), (False, 1)], ids=["written", "unwritten"])
def test_a_let_is_dropped_from_its_one_address(run_with, write, want, compiler):
    program = DROP + f"fn main() -> i32\n    scope({str(write).lower()})\n    return SEEN\n"
    assert run_with(compiler, f"drop_{write}", program) == want


# The checks on a `let` still hold: it can't be written directly, or through `@&`.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0"])
@pytest.mark.parametrize("body", [
    LET_C + "    let p: *C = @c\n    c.x = 3\n    return c.x\n",
    LET_C + "    let p: *C = @c\n    let q: @&C = @&c\n    return c.x\n",
    "    let n: i32 = 1\n    let p: *i32 = @n\n    n = 3\n    return n\n",
], ids=["direct_field", "at_mut", "direct_scalar"])
def test_a_let_with_its_address_taken_is_still_immutable(compile_with, body, compiler):
    comp, _, _ = compile_with(compiler, "immutable", _main(body))
    assert comp.returncode != 0
    assert "let" in (comp.stdout + comp.stderr)
