#!/usr/bin/env python3
"""A fn with no declared return type must discard a non-i32 tail value.

AGAST #1321 (angelo cache.ritz `evict_lru`): a unit procedure whose tail
expression is `self.entries.pop()` — `vec_pop<CacheEntry>` returns the
popped element. The implicit-return path `_convert_type`d the struct to
i32, which silently no-ops on aggregates, and emitted

    ret %CacheEntry %v   ; in a function declared to return i32

-> invalid IR at link. With no `-> T` in the source, the tail expression
is evaluated for effect only; the value must be dropped, not returned.
"""

import subprocess
import sys

import pytest

from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration


def _compile(tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    return run_ritz0([str(src), "-o", str(tmp_path / "unit.ll"), "--no-runtime"])


STRUCT_TAIL_IN_UNIT_FN = """\
struct Entry
    n: i32

fn make() -> Entry
    Entry { n: 1 }

fn discard_tail()
    make()

fn main() -> i32
    discard_tail()
    0
"""


def test_unit_fn_discards_struct_tail(tmp_path):
    result = _compile(tmp_path, STRUCT_TAIL_IN_UNIT_FN)
    assert result.returncode == 0, (
        f"unit fn with struct tail failed to compile:\n{result.stderr}"
    )
    # The IR must actually be valid — before the fix the module contained
    # `ret %Entry` inside the i32 `discard_tail`, which only clang/llvm
    # parsing catches (ritz0 itself exits 0).
    verify = subprocess.run(
        [sys.executable, "-c",
         "import sys; import llvmlite.binding as llvm; "
         "llvm.parse_assembly(open(sys.argv[1]).read())",
         str(tmp_path / "unit.ll")],
        capture_output=True, text=True)
    assert verify.returncode == 0, f"invalid IR: {verify.stderr}"


# No return type is a procedure (LANGUAGE_SPEC §5.1): its tail is discarded
# (LARB R69), so a bare `41 + 1` there has no effect (LARB R64, AGAST #3491).
# This was a guard that ritz0 returned it as an implicit i32.
I32_TAIL_IN_UNIT_FN = """\
fn gives_back()
    41 + 1

fn main() -> i32
    gives_back()
    0
"""


def test_unit_fn_i32_tail_has_no_effect(tmp_path):
    result = _compile(tmp_path, I32_TAIL_IN_UNIT_FN)
    out = result.stdout + result.stderr
    assert result.returncode != 0, out
    assert "unit.ritz:2:5: error: statement has no effect: the value of `41 + 1` is discarded" in out, out
