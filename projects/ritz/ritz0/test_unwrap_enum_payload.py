#!/usr/bin/env python3
"""`.unwrap()` / `.unwrap_or(d)` of an `Option<E>`, E a user enum (AGAST #3620).

`match router.handle_key_down(k).unwrap()` with `-> Option<HotkeyAction>`: the
payload is the enum's own `%E` aggregate, as `Some(x)` builds it (#2100).

ritz1's unwrap intrinsic loaded a struct payload as its `%S` (#2594) but any
other payload as an i64, so a user enum (one with a payload variant or
unit-only, both aggregates) was `store %E <i64>` and clang refused it.
An untyped `let a = o.unwrap()` stayed an i64 slot, so `match a` was "a
variant pattern needs an enum scrutinee".  prism's test_input lost all 13
tests to it.

One row per place the payload lands: a match, a call argument, an untyped
`let`, `unwrap_or`'s select, and a unit-only enum.
"""

import pytest

from test_row_table import assert_runs
from test_ref_into_value import COMPILERS

pytestmark = pytest.mark.integration

TYPES = """\
enum Act
    Xa
    Yb
    Cu(u32)

enum U
    P
    Q

fn pick(k: i32) -> Option<Act>
    if k == 1
        return Some(Act.Cu(5))
    None

fn pu() -> Option<U>
    Some(U.Q)

fn code(a: Act) -> i32
    match a
        Act.Cu(n) => n as i32
        Act.Yb => 2
        _ => 3

"""


def _main(body):
    return f"{TYPES}pub fn main() -> i32\n{body}"


# name: (program, exit code).
ROWS = {
    "match_on_unwrap": (_main(
        "    match pick(1).unwrap()\n        Act.Cu(n) => n as i32\n        _ => 2\n"), 5),
    "unwrap_as_argument": (_main("    code(pick(1).unwrap())\n"), 5),
    "untyped_let_of_unwrap": (_main(
        "    let a = pick(1).unwrap()\n    code(a)\n"), 5),
    "unwrap_or_default": (_main("    code(pick(0).unwrap_or(Act.Yb))\n"), 2),
    "unit_only_enum": (_main(
        "    let u = pu().unwrap()\n    match u\n        U.Q => 7\n        _ => 2\n"), 7),
}


@pytest.mark.parametrize("compiler", COMPILERS)
def test_unwrap_enum_payload(tmp_path, compiler):
    assert_runs(compiler, tmp_path, ROWS)
