"""AGAST #4529: module-level helper emitters must not drop the last fn's bindings.

THE DEFECT

The IR sink (`EmitterState.push_bytes`) runs `own_before_ret` at every `ret` so a fn's live owned bindings
drop there (#3508).  That state is per fn: `own_begin_fn` resets it at a fn's
start, and `own_end_fn` used to reset it at a fn's end.  #4463 deleted
`own_end_fn` as "vestigial" because `own_begin_fn` resets the same fields --
but the module-level helper emitters (sret copy/zero, print/format, the test
table, the platform hooks) are emitted *after* the functions and write their
own `ret` outside any fn body.  With no reset the last fn's live bindings were
still registered, so `own_before_ret` emitted their drop glue inside
`@__ritz_sret_copy`, referring to registers that do not exist in that
function:

    define internal void @__ritz_sret_copy(...) {
    ...
    done:
      %.9 = load i1, ptr %.5      ; %.5 is the previous fn's flag alloca
      call void @S_drop(ptr %.2) ; %.2 is its slot
      ret void
    }

clang then refuses the module: `use of undefined value '%.2'` (the ticket saw
`'%.146'` in iris).

THE FIX

`own_reset` forgets the last fn and `emit_module` calls it once, after the
last function/method and before the helper block.  The helper emitters live in
modules that do not import ownership (#3513), so the call belongs in
`emit_module`, which does; one reset before the block covers all of them.

THE TESTS

  * source shape: `own_end_fn` is gone and `own_reset` is exported.
  * behaviour: compiling a module whose last fn (an impl method ending in a
    tail expression, so its block is not marked dead) owns a live binding and
    which uses the sret helpers, ritz1's helper bodies carry no drop glue and
    clang accepts the IR.
"""

import re
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parents[2]
SRC = RITZ_ROOT / "ritz1" / "src"

# The last emitted fn owns `t`: `keep` ends in a tail expression, so
# own_after_stmt does not mark its outermost block dead and `t` is still live
# when the helpers are emitted.  `big_make` makes the sret helpers used (both
# @__ritz_sret_copy and @__ritz_sret_zero).
PROGRAM = """\
var D: i64 = 0

struct S
    x: i64

struct Big
    buf: [512]u8
    n: i32

impl Drop for S
    fn drop(self:& S)
        D = D + self.x

impl S
    fn keep(self:& S) -> i64
        var t: S = S { x: 1 }
        t.x

fn big_make(n: i32) -> Big
    var b: Big = Big { buf: [0; 512], n: n }
    return b

pub fn main() -> i32
    var s: S = S { x: 2 }
    var b: Big = big_make(3)
    let k: i64 = s.keep()
    return (k + b.n) as i32
"""

# Every define the module-level helper emitters write: sret copy/zero, the
# print/format/assert helpers, fmod, the test table and platform hooks.
HELPER_DEFINE = re.compile(r"^define\b.*?@(_start|__ritz_|ritz_platform_)([^(]*)")
# own_emit_ret_drop is the only writer of these labels: a helper carrying one
# dropped a binding that belongs to a fn.
RET_DROP_LABEL = re.compile(r"\bown\.[dn]\d+:")


def _helper_bodies(ir: str) -> dict[str, str]:
    """symbol -> body for each module-level helper define in `ir`."""
    bodies: dict[str, str] = {}
    current: str | None = None
    lines: list[str] = []
    for line in ir.splitlines():
        if current is None:
            m = HELPER_DEFINE.match(line)
            if m:
                current = "@" + m.group(1) + m.group(2)
                lines = [line]
        else:
            lines.append(line)
            if line == "}":
                bodies[current] = "\n".join(lines)
                current = None
    return bodies


@pytest.mark.unit
def test_own_end_fn_is_deleted_and_own_reset_exported():
    sources = {p.name: p.read_text() for p in sorted(SRC.glob("*.ritz"))}
    leftovers = [name for name, text in sources.items() if "own_end_fn" in text]
    assert not leftovers, (
        "own_end_fn survives (#4529 deletes it; own_begin_fn resets at each "
        f"fn start): {leftovers}")
    assert "pub fn own_reset(" in sources["ownership.ritz"], (
        "ownership.ritz does not export own_reset (#4529)")
    assert "own_reset(@s)" in sources["emitter.ritz"], (
        "emit_module does not call own_reset before the helper block (#4529)")


@pytest.mark.integration
def test_module_helpers_have_no_fn_drop_glue(ritz1_bin, tmp_path):
    src = tmp_path / "helpers.ritz"
    src.write_text(PROGRAM)
    ll = tmp_path / "helpers.ll"
    comp = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(ll)],
        cwd=tmp_path,
        env={"RITZ_PATH": str(RITZ_ROOT), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert comp.returncode == 0 and ll.exists(), (
        f"ritz1 failed to compile the helper program:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}")

    ir = ll.read_text()
    bodies = _helper_bodies(ir)
    assert any(k.startswith("@__ritz_sret_copy") for k in bodies), (
        "the program was expected to use the sret helper; IR shape changed")
    stale = {sym: sorted(set(RET_DROP_LABEL.findall(body)))
             for sym, body in bodies.items()
             if RET_DROP_LABEL.search(body)}
    assert not stale, (
        "module-level helper bodies carry a previous fn's drop glue (#4529):\n"
        + "\n".join(f"{sym}: {labs}" for sym, labs in sorted(stale.items())))

    check = subprocess.run(
        ["clang", "-c", "-Wno-override-module", str(ll), "-o", str(tmp_path / "h.o")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert check.returncode == 0, (
        "clang refused ritz1's IR (#4529: drop glue in a module helper):\n"
        f"{check.stderr[-3000:]}")
