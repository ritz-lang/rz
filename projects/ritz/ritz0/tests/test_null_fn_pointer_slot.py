#!/usr/bin/env python3
"""`null` fits a fn-pointer slot (LANGUAGE_SPEC §5.5, AGAST #3601).

§3.2 makes `null` a null pointer and §5.5 lowers a fn pointer to an opaque
`ptr`, so storing and testing a null handler is ordinary code (ritzlib async,
valet's router).  Both compilers accept it; ritz0's typing pass said
"cannot assign null to fn() -> i32" and "cannot compare fn() -> i32 with null".

`_types_compatible` lets `null` meet a `*T`/`&T`; a `fn(...)` type is the
third pointer-shaped slot.  One program covers every way the rule is reached
(assign, `!=` / `==` either side, a call argument, a `let` annotation, a
return); the control keeps `null` out of a non-pointer slot.
"""

import os
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parents[2]

ACCEPTED = """\
struct H
    cb: fn() -> i32

fn take(cb: fn() -> i32) -> i32
    if cb == null
        return 0
    1

fn none() -> fn() -> i32
    return null

fn main() -> i32
    var h: H
    h.cb = null
    if h.cb != null
        return 1
    if null != h.cb
        return 2
    let f: fn() -> i32 = null
    if f != null
        return 3
    if none() != null
        return 4
    take(null)
"""


def _check(tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return run_ritz0([str(src), "-o", str(tmp_path / "unit.ll"), "--no-runtime",
                      "--check-names"], env=env, timeout=300)


def test_null_fits_fn_pointer_slots(tmp_path):
    r = _check(tmp_path, ACCEPTED)
    out = r.stdout + r.stderr
    assert r.returncode == 0 and "Type error" not in out, out[-2000:]


def test_null_still_refused_by_a_non_pointer_slot(tmp_path):
    r = _check(tmp_path, """\
fn main() -> i32
    var n: i32 = 0
    n = null
    n
""")
    out = r.stdout + r.stderr
    assert r.returncode != 0 and "cannot assign null to i32" in out, out[-2000:]
