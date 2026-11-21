#!/usr/bin/env python3
"""A method called on another method call's struct result (AGAST #3620).

`Color.red().is_opaque()` and `c.me().is_zero()`: the receiver is itself a
method call (a static one, `T.f()`, or one on a value), and its declared
`-> S` return names the impl the outer call dispatches on.

ritz1 typed a method call's receiver from a local, a global, a type name, a
free call, a struct literal or a field, never from another method call.  The
emitter's own dispatch managed the chain, but every checker that asks "what
does this call return" (`method_recv_type_name`) got nothing back:
`assert Color.transparent().is_transparent()` was "assert condition must be
bool, and ritz1 cannot tell that it is", and
`let c = Color.red().with_alpha(128)` left `c` untyped, so `c.r` was
"unhandled EXPR_MEMBER".  prism's test_color lost all 15 tests to it.
The same gap hid `.unwrap()`'s payload, which has no FnDef to name it:
`router.focused_window().unwrap().raw()` was "cannot determine receiver
type for method call" (prism's test_input).

One row per form a reader can fail on its own; each exits with what it means.
"""

import pytest

from test_ref_into_value import COMPILERS
from test_table_rows import assert_runs

pytestmark = pytest.mark.integration

TYPES = """\
struct C
    a: u8
    b: i32

impl C
    pub fn zero() -> C
        C { a: 0, b: 5 }
    pub fn me(self) -> C
        self
    pub fn with_b(self, b: i32) -> C
        C { a: self.a, b: b }
    pub fn is_zero(self) -> bool
        self.a == 0
    pub fn get_b(self) -> i32
        self.b

fn mk() -> C
    C { a: 1, b: 9 }

fn some_c() -> Option<C>
    Some(C { a: 2, b: 3 })

struct H
    oc: Option<C>

impl H
    pub fn get(self) -> Option<C>
        self.oc

"""


def _main(body):
    return f"{TYPES}pub fn main() -> i32\n{body}"


# name: (program, exit code).
ROWS = {
    # A bool method on a static call's result, as an `if` condition.
    "static_then_bool_in_if": (_main(
        "    if C.zero().is_zero()\n        return 7\n    1\n"), 7),
    # ... under `not`, on a value method's result.
    "chain_then_bool_under_not": (_main(
        "    if not mk().me().is_zero()\n        return 7\n    1\n"), 7),
    # A bool method on a value method's result (no static call involved).
    "value_chain_then_bool": (_main(
        "    let c = mk()\n    if c.me().is_zero()\n        return 1\n    7\n"), 7),
    # An untyped `let` of a static call's chained result: the local is a C.
    "untyped_let_of_static_chain": (_main(
        "    let c = C.zero().with_b(42)\n    c.b\n"), 42),
    # An untyped `let` of a value chain, then a method on it.
    "untyped_let_of_value_chain": (_main(
        "    let c = mk().me()\n    c.get_b()\n"), 9),
    # A method on `.unwrap()` of a method's `Option<C>` (prism's
    # `router.focused_window().unwrap().raw()`): unwrap has no FnDef, its
    # payload names the impl.
    "method_on_unwrap_of_method": (_main(
        "    let h = H { oc: Some(C.zero()) }\n    h.get().unwrap().get_b()\n"), 5),
    # ... of a free call's.
    "method_on_unwrap_of_call": (_main(
        "    some_c().unwrap().get_b()\n"), 3),
}


@pytest.mark.parametrize("compiler", COMPILERS)
def test_method_on_method_result(tmp_path, compiler):
    assert_runs(compiler, tmp_path, ROWS)
