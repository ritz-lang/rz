#!/usr/bin/env python3
"""Auto-borrow of rvalue arguments to `*T` PtrType params in plain calls (AGAST #1290).

This is the `_emit_call` arm of the two-sited auto-borrow defect. The sibling
site, `_emit_method_call`, is pinned by test_method_call_rvalue_autoborrow.py
(AGAST #1321). The two holes were complementary:

* `_emit_call` had the rvalue-spill machinery, but its trigger predicate only
  fired for RefType params and mutable borrows — a `*T` PtrType param with an
  rvalue argument fell through to the by-value branch and died in
  `_convert_type` with::

      TypeError: Type of #N arg mismatch:
          %"struct.M.Point2D"* != %"struct.M.Point2D"

  This is the `vec_get$Point2D` shape from #1290: a call-result (rvalue)
  passed where the callee expects a pointer-to-struct.

The fix extends the trigger predicate only: a `*T` param whose pointee is the
argument's own (non-pointer) named type routes through the existing
borrow/spill branch. `*u8` params keep the String/StrView coercion path —
the pointee there never matches the argument's named struct type.
"""

import subprocess
import sys
from pathlib import Path

RITZ0 = Path(__file__).resolve().parent / "ritz0.py"


def _compile(tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    return subprocess.run(
        [sys.executable, str(RITZ0), str(src),
         "-o", str(tmp_path / "unit.ll"), "--no-runtime"],
        capture_output=True,
        text=True,
    )


# The reduced #1290 shape: a function-call result (rvalue, no address) passed
# to a parameter declared `*Point2D`.
RVALUE_TO_PTR_PARAM = """\
pub struct Point2D
    x: i32
    y: i32

fn make() -> Point2D
    return Point2D { x: 7, y: 2 }

fn get_x(p: *Point2D) -> i32
    return p.x

fn main() -> i32
    return get_x(make())
"""


def test_rvalue_arg_to_ptr_param(tmp_path):
    """A call-result argument to a `*T` param must be spilled and borrowed."""
    result = _compile(tmp_path, RVALUE_TO_PTR_PARAM)
    assert result.returncode == 0, (
        "rvalue argument to *T PtrType parameter failed to compile:\n"
        f"{result.stderr}"
    )


# Explicit address-of must keep working — the predicate must not double-borrow.
ADDR_OF_TO_PTR_PARAM = """\
pub struct Point2D
    x: i32
    y: i32

fn get_x(p: *Point2D) -> i32
    return p.x

fn main() -> i32
    var pt: Point2D = Point2D { x: 7, y: 2 }
    return get_x(@pt)
"""


def test_addr_of_arg_to_ptr_param_still_works(tmp_path):
    """`f(@x)` where the param is `*T` must not be borrowed a second time."""
    result = _compile(tmp_path, ADDR_OF_TO_PTR_PARAM)
    assert result.returncode == 0, (
        "explicit address-of argument to *T parameter regressed:\n"
        f"{result.stderr}"
    )


# `*u8` params must keep the coercion path: the pointee (u8) never equals the
# argument's named struct type, so the new predicate must not capture this.
CSTR_TO_U8_PTR_PARAM = """\
fn first(s: *u8) -> u8
    return s[0]

fn main() -> i32
    return first(c"hi") as i32
"""


def test_u8_ptr_param_keeps_coercion_path(tmp_path):
    """c-string literal to a `*u8` param must still take the coercion path."""
    result = _compile(tmp_path, CSTR_TO_U8_PTR_PARAM)
    assert result.returncode == 0, (
        "c-string to *u8 parameter regressed:\n"
        f"{result.stderr}"
    )
