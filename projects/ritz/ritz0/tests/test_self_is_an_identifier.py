"""AGAST #3331: `self` names a fn, a struct field and a `for` variable.

THE DEFECT

    fn self(x: i32) -> i32
        x + 1
    struct G
        self: i32          # also G { self: 4 }, g.self
    for self in 0..4

ritz0 compiles and runs all three.  ritz1 and ritz1_selfhosted:
`1:4: unexpected 'self'` (fn), `2:5: unexpected 'self'` (field),
`9:9: unexpected 'self'` (for).  docs/LANGUAGE_SPEC.md says `self` is not a
keyword, but ritz1 lexes it as SELF, and only param, let/var and reads
accepted SELF.

THE FIX

ritz1's grammar has a `name` rule (IDENT | SELF) for a fn's name, a struct
field's declaration, a struct literal's field init, a `.member` and a `for`
variable.  `self` stays a SELF token (unlike `pass`, #3320), so the receiver
forms (`self`, `self: @T`, `self:&`) are the separate param alternatives they
were; the last row pins them.

Each program returns 0, or the number of the first check that failed, on all
three compilers.  ritz0 is the oracle: every program passes there too.
"""

import pytest

import test_ritz1_for_header as for_header

pytestmark = pytest.mark.batched

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

PROGRAMS = {
    # The ticket's fn, and a `pub fn self`, called.
    "fn_name": """\
fn self(x: i32) -> i32
    x + 1

pub fn self_pub() -> i32
    return self(2) - 3

pub fn main() -> i32
    if self(2) != 3
        return 1
    if self_pub() != 0
        return 2
    return 0
""",
    # A field named `self`: declared, initialised in a literal, read, and
    # written through a value and a pointer.
    "field": """\
struct G
    self: i32
    other: i32

fn bump(g: *G)
    g.self = g.self + 1

pub fn main() -> i32
    var g: G = G { self: 4, other: 1 }
    if g.self != 4
        return 1
    bump(@g)
    if g.self != 5
        return 2
    g.self += 2
    if g.self != 7
        return 3
    if g.other != 1
        return 4
    return 0
""",
    # A `for` variable named `self`, over each range form.
    "for_var": """\
pub fn main() -> i32
    var sum: i32 = 0
    for self in 0..4
        sum += self as i32
    if sum != 6
        return 1
    for self in 0..=4
        sum += self as i32
    if sum != 16
        return 2
    return 0
""",
    # The receivers are unchanged, and a method's `self` reaches a field
    # named `self`: `self.self`.
    "receivers": """\
struct P
    self: i32
    y: i32

impl P
    fn get(self) -> i32
        return self.self + self.y

    fn bump(self:& P)
        self.self += 10

    fn lent(self:&)
        self.y += 1

fn free(self: @P) -> i32
    return self.self

pub fn main() -> i32
    var p: P = P { self: 1, y: 2 }
    if p.get() != 3
        return 1
    p.bump()
    if p.self != 11
        return 2
    p.lent()
    if p.y != 3
        return 3
    if free(@p) != 11
        return 4
    return 0
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
@pytest.mark.parametrize("compiler", COMPILERS)
def test_self_as_identifier_runs(run_with, compiler, name):
    assert run_with(compiler, name, PROGRAMS[name]) == 0
