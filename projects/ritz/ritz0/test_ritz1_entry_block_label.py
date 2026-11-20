"""AGAST #1335 / #3526: a fn's entry block never inherits the previous fn's label.

THE DEFECT (#1335)

`label_counter` restarts at 0 for every fn, so ritz1's block labels are only
unique within a fn.  emit_fn and emit_impl_method did not reset
`current_label`, so a value produced in a fn's entry block was tagged by
set_last_expr with the label of the PREVIOUS fn's last block.  When that label
collided with a real block of the current fn, `last_expr_here` there reported
the entry-block value as "defined here".  The fix sets
`current_label = ENTRY_BLOCK_LABEL` (-1, never a real label) at both
boundaries (ritz1/src/emitter.ritz).

WHY THIS IS AN IR TEST, NOT AN EXAMPLE (#3526)

examples/tier1_basics/93_fn_boundary_label guarded this with a run, and went
vacuous: #1429/#2236 made a `-> T` fn that can fall off its end an error, and a
trailing expression emits its own `ret`.  The implicit-return tail now reads
`last_expr_here` only after a tail `if`/`match`; one whose arms yield values
leaves a fresh phi, so the stale pair is reachable only when every arm
`return`s and the merge block is dead.  With the resets removed, ritz1 compiled
all 1150 `.ritz` files in the repo that it compiles to byte-identical IR, and
the one difference this file provokes is in that dead block: `ret i64 <the
entry-block value>` where the fix gives `unreachable`.  No run can see it; the
IR can.

`prev_*` ends in the merge block of an if-without-else (L2), the same label as
`d*`'s merge block after an if/else whose arms both return.  Each `d*` makes
an entry-block value first.  One fn and one method, one per reset.
"""

import os
import re
import subprocess

import pytest
import test_ir

from test_ritz1_builtin_struct_shadow import RITZ_ROOT

pytestmark = pytest.mark.integration

PROGRAM = """\
fn entry_value() -> i64
    7

fn prev_fn(c: i64) -> i64
    var r: i64 = 1
    if c > 0
        r = 2
    r

fn d_fn(c: i64) -> i64
    entry_value()
    if c > 0
        return 1
    else
        return 2

struct S
    v: i64

impl S
    fn prev_m(self, c: i64) -> i64
        var r: i64 = self.v
        if c > 0
            r = 2
        r

    fn d_m(self, c: i64) -> i64
        entry_value()
        if c > 0
            return 1
        else
            return 2

pub fn main() -> i32
    let s: S = S { v: 1 }
    return (d_fn(1) + s.prev_m(0) + s.d_m(0) + prev_fn(0)) as i32
"""


def _fn_bodies(ir: str) -> dict:
    """Map each defined fn's name to its body text."""
    return {
        test_ir.strip(m.group(1)): m.group(2)
        for m in re.finditer(r"^define [^@]*@(\w+)\(.*?\{\n(.*?)^\}", ir, re.M | re.S)
    }


def test_dead_merge_after_returning_arms_is_unreachable(ritz1_bin, tmp_path):
    src = tmp_path / "main.ritz"
    src.write_text(PROGRAM)
    ll = tmp_path / "main.ll"
    proc = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(ll)],
        cwd=tmp_path,
        env=dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}"),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0 and ll.exists(), (proc.stdout + proc.stderr)[-2000:]
    bodies = _fn_bodies(ll.read_text())
    checked = []
    for name, body in bodies.items():
        if not (name == "d_fn" or name.endswith("d_m")):
            continue
        checked.append(name)
        # The entry block's only value is the entry_value() call.
        entry = re.search(rf"(%\.\d+) = call i64 {test_ir.symbol('entry_value')}\(\)", body)
        assert entry, f"{name}: no entry_value() call:\n{body}"
        tail = body.rstrip().splitlines()[-1].strip()
        assert tail == "unreachable", (
            f"{name}: the merge after two returning arms is dead and must be "
            f"`unreachable`; `{tail}` returns an entry-block value through a "
            f"label inherited from the previous fn (AGAST #1335):\n{body}"
        )
    # One per reset: emit_fn's and emit_impl_method's.
    assert sorted(checked) == ["S_d_m", "d_fn"], f"found {sorted(bodies)}"
