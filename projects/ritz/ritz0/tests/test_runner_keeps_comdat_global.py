"""The runner's `objcopy` must keep COMDAT members global (AGAST #3488).

The runner merges ritzunit's modules with `ld -r` and localizes everything but
`main`, so names the program also defines cannot clash. A `linkonce_odr`
generic instantiation is not one of those clashes: the runner object and a
shared dependency object may each hold a copy, the final link keeps one and
discards the other, and a reference from the runner's merged `.text` can only
reach the survivor if the name is global.

Localizing it instead fails the link. Integer-overflow traps grew `vec_push`
past LLVM's inlining threshold, so its `linkonce_odr` copy survived in the
runner: `rz test goliath` died with "`vec_push$u8' referenced in section
`.text` ... defined in discarded section". These tests pin the fix: weak
definitions stay global, strong ones are localized.
"""

import subprocess
import sys
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).parents[1].resolve()
sys.path.insert(0, str(RITZ0_DIR))

import test_runner  # noqa: E402

pytestmark = [pytest.mark.integration]

IR = """
define linkonce_odr i32 @"generic$i32"(i32 %"x")
{
entry:
  ret i32 %"x"
}

define i32 @"strong_one"(i32 %"x")
{
entry:
  ret i32 %"x"
}

define i32 @"main"(i32 %"argc", i8** %"argv")
{
entry:
  ret i32 0
}
"""


def _object(tmp_path):
    ll = tmp_path / "m.ll"
    ll.write_text(IR)
    obj = tmp_path / "m.o"
    result = subprocess.run(["clang", "-c", str(ll), "-o", str(obj)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return obj


def test_weak_definitions_are_kept_global(tmp_path):
    keep, error = test_runner._keep_global_symbols(str(_object(tmp_path)))
    assert error is None
    assert "main" in keep
    assert "generic$i32" in keep, keep


def test_strong_definitions_are_localized(tmp_path):
    keep, error = test_runner._keep_global_symbols(str(_object(tmp_path)))
    assert error is None
    assert "strong_one" not in keep, keep
