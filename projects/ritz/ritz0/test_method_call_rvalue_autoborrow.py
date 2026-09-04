#!/usr/bin/env python3
"""Auto-borrow of rvalue *arguments* in method calls (AGAST #1321).

Background
----------
Building angelo, ``discovery.ritz`` died with::

    TypeError: Type of #2 arg mismatch:
        %"struct.ritz_module_1.StrView"* != %"struct.ritz_module_1.StrView"

The failing construct was ``path.starts_with("~")``: ``starts_with`` declares
``prefix: @StrView`` (a borrow, LLVM pointer), and the string literal ``"~"``
produces a ``StrView`` *rvalue* — a value with no address.

The auto-borrow logic exists in two places with complementary behaviour:

* ``_emit_call`` triggers auto-borrow for RefType/mutable-borrow params and,
  when the argument is an rvalue, correctly spills it to a stack slot
  (``arg.tmp``) so its address can be passed.
* ``_emit_method_call`` triggered on the right condition (the callee's LLVM
  param type is a pointer) but, when ``_emit_lvalue_addr`` raised on an
  unaddressable argument, fell back to emitting the struct **by value** —
  which then failed ``builder.call``'s type check with the mismatch above.

This is the method-call sibling of the AGAST #1290 defect class (value passed
where the callee expects a pointer). The fix mirrors the receiver path and
``_emit_call``: spill the rvalue to an entry-block alloca and pass its
address, guarded on ``tmp_val.type == expected_type.pointee`` so genuinely
mismatched arguments still fail loudly.
"""

import subprocess
import sys
from pathlib import Path

RITZ0 = Path(__file__).resolve().parent / "ritz0.py"


def _compile(tmp_path: Path, source: str) -> subprocess.CompletedProcess:
    """Compile a standalone Ritz source, returning the completed process.

    ``--no-runtime`` keeps these free of any ``RITZ_PATH``/ritzlib dependency:
    the sources below import nothing, so the emitter is the only thing under
    test.
    """
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    return subprocess.run(
        [sys.executable, str(RITZ0), str(src),
         "-o", str(tmp_path / "unit.ll"), "--no-runtime"],
        capture_output=True,
        text=True,
    )


# The reduced shape of discovery.ritz's `path.starts_with("~")`: a method
# whose non-self parameter is a borrow (`@Pair`, LLVM pointer), called with an
# rvalue argument (a call result) that has no address to take.
RVALUE_ARG_TO_BORROW_PARAM = """\
pub struct Pair
    a: i32
    b: i32

impl Pair
    fn add_a(self: @Pair, other: @Pair) -> i32
        return self.a + other.a

fn make() -> Pair
    var p: Pair
    p.a = 1
    p.b = 2
    return p

fn main() -> i32
    var p: Pair
    p.a = 3
    p.b = 4
    if p.add_a(make()) == 4
        return 0
    return 1
"""


def test_rvalue_arg_to_pointer_param_compiles(tmp_path):
    """An rvalue argument to a `@T` method param must be spilled and borrowed.

    Before the fix this raised
    ``TypeError: Type of #2 arg mismatch: %"...Pair"* != %"...Pair"``
    because the fallback passed the struct by value.
    """
    result = _compile(tmp_path, RVALUE_ARG_TO_BORROW_PARAM)
    assert result.returncode == 0, (
        "rvalue argument to a pointer-typed method parameter failed to "
        f"compile:\n{result.stderr}"
    )
    assert "arg mismatch" not in result.stderr


def test_rvalue_arg_is_spilled_to_stack_slot(tmp_path):
    """The emitted IR must pass the spilled slot's address, not a value copy.

    Pins the mechanism (an ``arg.tmp`` alloca + store) so a future
    refactor that reverts to the by-value fallback — or silently bitcasts —
    fails here even if llvmlite's type check were ever relaxed.
    """
    result = _compile(tmp_path, RVALUE_ARG_TO_BORROW_PARAM)
    assert result.returncode == 0, result.stderr
    ir = (tmp_path / "unit.ll").read_text()
    assert "arg.tmp" in ir, "expected an arg.tmp spill slot in the emitted IR"


def test_genuinely_mismatched_arg_still_fails(tmp_path):
    """The spill is a borrow, not a cast: wrong-type args must still fail.

    Passing a ``StrView`` literal where an unrelated struct borrow is
    expected must not be silently spilled into a pointer of the wrong type.
    """
    result = _compile(tmp_path, """\
pub struct SV
    ptr: *u8
    len: i64

impl SV
    fn same_len(self: @SV, other: @SV) -> i32
        if self.len == other.len
            return 1
        return 0

fn main() -> i32
    var s: SV
    s.ptr = null
    s.len = 1
    if s.same_len("~") == 1
        return 0
    return 1
""")
    assert result.returncode != 0, (
        "StrView literal passed as @SV should not compile"
    )
