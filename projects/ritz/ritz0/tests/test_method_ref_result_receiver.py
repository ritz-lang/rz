#!/usr/bin/env python3
"""A method returning `@T` / `@&T` / `*T` names the next receiver (AGAST #4457).

`assert not comp.damage_tracker().has_damage()`: `damage_tracker` returns
`@&DamageTracker`, so `has_damage` dispatches on the pointed-to struct.  ritz1
typed a method call's receiver from a struct or `*S` return only
(`sbk_receiver`'s EXPR_METHOD arm in bool_check.ritz), so the outer call's
receiver was untyped and `not` was refused with "operand of `not` must be
bool, and ritz1 cannot tell that it is".  A free fn returning a reference
already worked: it reaches the arm's fallback, which does ask Sema.

Each row is a form a reader can fail on its own.  The running rows say what the
program must exit with; the `not` / `or` rows ask `no_q`, whose answer is no, so
a test that the reference is ever read can't pass by answering yes every time.
`assert` belongs to a `[[test]]` function, so that row only compiles and exits 0.
"""

import pytest

from test_ref_into_value import COMPILERS
from test_table_rows import assert_runs

pytestmark = pytest.mark.integration

TYPES = """\
struct D
    ok: bool
    v: i32

impl D
    pub fn ok_q(self) -> bool
        self.ok
    pub fn no_q(self) -> bool
        self.ok == false
    pub fn get(self) -> i32
        self.v
    pub fn twice(self) -> i32
        self.v * 2
    pub fn shared(self: @D) -> @D
        self
    pub fn borrowed(self: @&D) -> @&D
        self
    pub fn pointer(self: *D) -> *D
        self

fn mk() -> D
    D { ok: true, v: 3 }

"""

# name: callable on a call's temporary.  `@&D` is refused there by another
# rule ("a method that writes `self` can't take a call's temporary"), so
# `borrowed` gets the local receiver only; that local row is the prism case.
RETURNS = {"shared": True, "borrowed": False, "pointer": True}


def _run_row(recv, name):
    """A `main` body reading the reference-returning call's result."""
    return {
        # A bool method on the reference's result, as an `if` condition.
        "if": (f"    if {recv}.{name}().ok_q()\n        return 7\n    1\n", 7),
        # ... under `not`: the reported operands.
        "not": (f"    if not {recv}.{name}().no_q()\n        return 7\n    1\n", 7),
        # ... on both sides of `and` / `or`.
        "and": (f"    if {recv}.{name}().ok_q() and {recv}.{name}().get() == 3\n"
                f"        return 7\n    1\n", 7),
        "or": (f"    if {recv}.{name}().no_q() or {recv}.{name}().ok_q()\n"
               f"        return 7\n    1\n", 7),
        # A field read straight off the reference (`t.m().b`).
        "field": (f"    if {recv}.{name}().ok\n        return 7\n    1\n", 7),
        # A method call on the reference (`c.m().m2()`).
        "chained_call": (f"    {recv}.{name}().twice()\n", 6),
    }


def _assert_row(recv, name, lead):
    """`assert` is only allowed in a [[test]] function; it need only compile."""
    return (f"[[test]]\nfn row() -> i32\n{lead}    assert {recv}.{name}().ok_q()\n"
            f"    0\n\npub fn main() -> i32\n    0\n", 0)


# name: (program, exit code).
ROWS = {}
for _name, _on_temporary in RETURNS.items():
    for _local in ([False, True] if _on_temporary else [True]):
        _recv = "d" if _local else "mk()"
        _lead = "    var d = mk()\n" if _local else ""
        _where = "local" if _local else "call"
        for _row, (_body, _want) in _run_row(_recv, _name).items():
            ROWS[f"{_where}_{_name}_{_row}"] = (
                f"{TYPES}pub fn main() -> i32\n{_lead}{_body}", _want)
        _body, _want = _assert_row(_recv, _name, _lead)
        ROWS[f"{_where}_{_name}_assert"] = (f"{TYPES}{_body}", _want)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_method_ref_result_is_a_receiver(tmp_path, compiler):
    assert_runs(compiler, tmp_path, ROWS)
