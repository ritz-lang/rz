#!/usr/bin/env python3
"""An untyped `let` of an `Option<T>` / `Result<T, E>` field (AGAST #3620).

`let action = self.hotkey_triggered` with `hotkey_triggered:
Option<HotkeyAction>` is a copy of the field, an `Option$HotkeyAction` slot
as if annotated.

ritz1's untyped-`let` inference typed a struct field by `find_struct`, which
knows no tagged enum, so the slot stayed i64 and the init emitted
`store i64 %<%Option$HotkeyAction>`: clang refused prism's router.ritz, and
test_input lost all 13 tests.  The `?` arm (`let x = h.r?`, #2267) already
read a tagged-enum field by `is_tagged_enum_type`.

Each row takes the field, then clears it, so a slot aliasing the field
instead of copying it exits wrong.
"""

import pytest

from test_ref_into_value import COMPILERS
from test_table_rows import assert_runs

pytestmark = pytest.mark.integration

TYPES = """\
enum Act
    Xa
    Cu(u32)

struct R
    hk: Option<Act>
    n: Option<u32>
    res: Result<u32, i32>

impl R
    fn take(self:&) -> Option<Act>
        let action = self.hk
        self.hk = None
        action

fn act_code(o: Option<Act>) -> i32
    match o
        Some(inner) =>
            match inner
                Act.Cu(n) => n as i32
                _ => 3
        None => 1

"""


def _main(body):
    return (f"{TYPES}pub fn main() -> i32\n"
            f"    var r = R {{ hk: Some(Act.Cu(7)), n: Some(6), res: Ok(5) }}\n{body}")


# name: (program, exit code).
ROWS = {
    # prism's shape: a `self:&` method takes an Option<enum> field.
    "option_enum_field_through_self": (_main(
        "    let t = r.take()\n    if r.hk.is_some()\n        return 2\n    act_code(t)\n"), 7),
    # A local's Option<enum> field, cleared after.
    "option_enum_field_of_local": (_main(
        "    let t = r.hk\n    r.hk = None\n    act_code(t)\n"), 7),
    # A scalar payload.
    "option_scalar_field": (_main(
        "    let t = r.n\n    r.n = None\n    t.unwrap_or(1) as i32\n"), 6),
    # A Result field.
    "result_field": (_main(
        "    let t = r.res\n    r.res = Err(4)\n    match t\n"
        "        Ok(v) => v as i32\n        Err(e) => e\n"), 5),
}


@pytest.mark.parametrize("compiler", COMPILERS)
def test_let_of_tagged_enum_field(tmp_path, compiler):
    assert_runs(compiler, tmp_path, ROWS)
