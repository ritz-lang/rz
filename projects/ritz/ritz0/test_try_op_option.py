#!/usr/bin/env python3
"""`?` on an `Option` yields the `Some` payload and propagates `None` (AGAST #4061).

LANGUAGE_SPEC §14.2 documented `?` for `Result` only, but ritz0 already
implemented it for `Option` and all three compilers agreed. #4061 settled
that by *specifying* the behaviour: `expr?` on `Option<T>` yields the payload,
and returns `None` from the enclosing function, which must itself return an
`Option`. These rows pin that behaviour end to end, so the spec cannot go back
to promising something the compilers do not do:

- `some_payload` — `find(3)?` is the `Some` payload, here doubled.
- `none_propagates` — `find(-1)?` returns `None` from `twice`; the doubled
  `Some` is never built.

Removing or mis-emitting the Option path (`_emit_try_op_option`) reddens the
matching row: a broken payload load fails `some_payload`, and a missing early
return fails `none_propagates`.
"""

import pytest

from test_ref_into_value import COMPILERS, _run

# AGAST #2806: each row shares one compile per compiler (batching.py).
pytestmark = [pytest.mark.integration, pytest.mark.batched]

OPT = """\
import ritzlib.option

fn find(x: i32) -> Option<i32>
    if x > 0
        return Some(x)
    None

fn twice(x: i32) -> Option<i32>
    let v = find(x)?
    Some(v + v)

"""


def _exit(cond):
    return f"pub fn main() -> i32\n    if {cond}\n        return 3\n    1\n"


# name: (program, exit code). The program exits 3 when the behaviour holds.
ROWS = {
    # `find(3)?` yields the Some payload, so twice(3) is Some(6).
    "some_payload": (OPT + _exit("twice(3).unwrap_or(-1) == 6"), 3),
    # `find(-1)?` returns None from twice; no Some is built.
    "none_propagates": (OPT + _exit("twice(-1).is_none()"), 3),
}


def _params(table):
    for row in table:
        for compiler in COMPILERS:
            yield pytest.param(row, compiler, id=f"{row}-{compiler}")


@pytest.mark.parametrize("row,compiler", list(_params(ROWS)))
def test_try_op_on_option(tmp_path, compiler, row):
    src, want = ROWS[row]
    assert _run(compiler, tmp_path, row, src) == want
