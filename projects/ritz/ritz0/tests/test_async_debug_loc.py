"""AGAST #3800: the calls an `await` lowers to carry a !dbg location.

ritz0 emits DWARF for every fn, and LLVM's verifier requires every inlinable
call in a fn with debug info to have a !dbg location.  async_transform_v2
built the statements of an await's states with a line-0 dummy span, so the
emitter's per-statement `_set_debug_loc` never fired in `go_poll`: the
future's constructor call (`fetch(x)`) and its poll (`fetch_poll(@fut)`)
had no location.  The verifier then warned "inlinable function call in a
function with debug info must have a !dbg location", and llvmlite's
`verify()` kept the module but DROPPED ALL ITS DEBUG INFO ("ignoring invalid
debug info"): no line info for anything under -g.  The doc gate's IR check
(#1358) is what saw it.

Each row is a separate path through `lower_await`: an awaited async fn's
call (constructor and poll), a unit async fn's, a hand-written poll source,
and `await` in a sync fn (the emitter's own poll loop, which already had a
location: a guard).  The test parses and verifies the IR, then asserts the
debug info survived: `llvm.dbg.cu` is gone from a module whose debug info
was stripped.

ritz0 only: ritz1 has no async fns.
"""

from __future__ import annotations

from pathlib import Path

import llvmlite.binding as llvm
import pytest

pytestmark = pytest.mark.integration

_FETCH = "async fn fetch(x: i32) -> i32\n    x\n\n"
_MAIN = "fn main() -> i32\n    0\n"

# name -> program
ROWS = {
    # The ticket's block (docs/LANGUAGE_SPEC.md, "async fn").
    "async_call": _FETCH + "async fn go(x: i32) -> i32\n    await fetch(x)\n\n" + _MAIN,
    # A unit async fn: the poll state with no result to deliver.
    "unit_async_call": ("async fn tick(x: i32)\n    pass\n\n"
                        "async fn go(x: i32)\n    await tick(x)\n\n" + _MAIN),
    # A hand-written poll source: an ordinary call polled until not -1, in
    # the `__poll_k` let the lowering synthesises.
    "poll_source": ("fn ready(x: i32) -> i32\n    x\n\n"
                    "async fn go(x: i32) -> i32\n    await ready(x)\n\n" + _MAIN),
    # `await` in a sync fn: the emitter's poll loop.  Already located.
    "sync_await": _FETCH + "fn main() -> i32\n    await fetch(3)\n",
}


@pytest.mark.parametrize("name", list(ROWS))
def test_await_calls_keep_debug_info(name, tmp_path: Path, run_ritz0):
    src = tmp_path / f"{name}.ritz"
    src.write_text(ROWS[name])
    out = tmp_path / f"{name}.ll"
    proc = run_ritz0([str(src), "-o", str(out)], cwd=tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    ir = out.read_text()
    assert "!llvm.dbg.cu" in ir, "ritz0 emitted no debug info at all"

    module = llvm.parse_assembly(ir)
    module.verify()
    # The verifier strips a module's debug info when any inlinable call in
    # a fn with a DISubprogram lacks a !dbg location.
    assert "!llvm.dbg.cu" in str(module), (
        f"LLVM stripped the debug info of {name}: a call has no !dbg location")
