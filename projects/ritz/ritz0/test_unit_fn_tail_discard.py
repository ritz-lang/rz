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


# Guard: an i32-valued tail in an undeclared-ret fn keeps returning it
# (existing programs rely on the implicit i32).
I32_TAIL_IN_UNIT_FN = """\
fn gives_back()
    41 + 1

fn main() -> i32
    gives_back() - 42
"""


def test_unit_fn_keeps_i32_tail(tmp_path):
    result = _compile(tmp_path, I32_TAIL_IN_UNIT_FN)
    assert result.returncode == 0, (
        f"i32-tail guard case failed:\n{result.stderr}"
    )
