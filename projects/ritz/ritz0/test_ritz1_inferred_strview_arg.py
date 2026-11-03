"""Regression tests for AGAST #2103: an un-annotated string-literal local
passed to a StrView parameter.

    fn prints(s: StrView) ...
    let t = "xy\\n"
    prints(t)       # ritz1: call void @prints(%StrView %.5) where %.5 is
                    # %"Span$u8" -- clang rejects the IR

A bare `"..."` is lowered to the builtin `{ ptr, i64 }` pair.  Annotated
(`let t: StrView = ...`) locals were already right; an un-annotated local
was typed `Span$u8`, and the call-arg layout-equivalence coercion
(#168/#1643/#1662/#1669) did not rebuild it as `%StrView`.

Each program returns 42 when correct and a distinct small code naming the
check that failed otherwise.  ritz0 is the oracle; every case runs.
"""

import pytest

from test_ritz1_call_result_member import EXPECTED, _run

PRINTS = """\
fn prints(s: StrView) -> i64
    syscall3(1, 1, s.ptr as i64, s.len)
    s.len

fn first(s: StrView) -> u8
    *s.ptr

"""

PROGRAMS = {
    # The ticket's repro: `let` literal local to a StrView param.
    "let_literal_arg": PRINTS
    + """\
pub fn main() -> i32
    let t = "xy\\n"
    if prints(t) != 3
        return 1
    return 42
""",
    # Same through a `var`.
    "var_literal_arg": PRINTS
    + """\
pub fn main() -> i32
    var w = "hello"
    if prints(w) != 5
        return 1
    if first(w) != 104
        return 2
    return 42
""",
    # A `var` reassigned to another literal, then passed.
    "var_reassigned_arg": PRINTS
    + """\
pub fn main() -> i32
    var w = "ab"
    w = "abcd"
    if prints(w) != 4
        return 1
    return 42
""",
    # The local's own fields still read, and it passes twice.
    "let_literal_fields_and_args": PRINTS
    + """\
pub fn main() -> i32
    let t = "abc"
    if t.len != 3
        return 1
    if first(t) != 97
        return 2
    return (prints(t) + prints(t) + 36) as i32
""",
    # A non-first argument position.
    "second_arg": """\
fn pick(n: i64, s: StrView) -> i64
    n + s.len

pub fn main() -> i32
    let t = "abcde"
    return pick(37, t) as i32
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    assert _run("ritz0", tmp_path, name, PROGRAMS[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_inferred_strview_arg(ritz1_bin, tmp_path, name):
    assert _run("ritz1", tmp_path, name, PROGRAMS[name]) == EXPECTED
