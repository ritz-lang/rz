#!/usr/bin/env python3
"""A struct or enum-variant field has no `:=` form; all three compilers refuse
it at the `:=` (LANGUAGE_SPEC §13.2, AGAST #4062, #4456).

`name:= T` and `self:= T` are by-value *parameter* modifiers and stay
accepted; a field is written `pos: i64`.  Before #4456 ritz0 parsed
`pos:= i64` as a silent no-op, and its enum-variant reader blamed the field
name, so the three compilers disagreed.

Every row runs on ritz0, ritz1 and ritz1_selfhosted, and all three must report
the same `line:col: message`.
"""

import pytest

from test_ref_into_value import COMPILERS, _assert_refused, _run

pytestmark = pytest.mark.integration

# `^` marks the `:=`, where the error lands.
REFUSALS = {
    "struct_field": (
        "struct S\n"
        "    pos^:= i64\n"
        "\n"
        "fn main() -> i32\n"
        "    0\n",
        "unexpected ':='"),
    "enum_variant_field": (
        "enum E\n"
        "    V\n"
        "        pos^:= i64\n"
        "\n"
        "fn main() -> i32\n"
        "    0\n",
        "unexpected ':='"),
}

# The KEEP-ALIVE: parameter `:=` is a feature and must still parse.
POSITIVES = {
    "move_param": (
        "struct R\n"
        "    x: i64\n"
        "\n"
        "fn take(r:= R) -> i64\n"
        "    r.x\n"
        "\n"
        "fn main() -> i32\n"
        "    let r = R { x: 0 }\n"
        "    take(r) as i32\n"),
    "move_receiver": (
        "struct R\n"
        "    x: i64\n"
        "\n"
        "impl R\n"
        "    fn get(self:= R) -> i64\n"
        "        self.x\n"
        "\n"
        "fn main() -> i32\n"
        "    let r = R { x: 0 }\n"
        "    r.get() as i32\n"),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSALS))
def test_colon_eq_field_is_refused(compiler, tmp_path, name):
    marked, message = REFUSALS[name]
    _assert_refused(compiler, tmp_path, name, marked, message)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(POSITIVES))
def test_colon_eq_parameter_still_parses(compiler, tmp_path, name):
    assert _run(compiler, tmp_path, name, POSITIVES[name]) == 0
