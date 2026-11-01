"""AGAST #2025: a `let` of a large struct lives in one slot; borrowing it
reuses that slot.

THE DEFECT

`let` bindings were SSA values (self.params), so every `@b` re-materialised
the value: a fresh `b.addr` alloca at the borrow site, filled by
`store %Big %v`. The #1732 store peephole turned that into a byte copy only
when the producing load sat earlier in the same block. A borrow in any
later block (an `assert`'s pass block, a loop body) emitted a first-class
store of the whole struct. At 100 KB, clang -O2 hung and -O0 segfaulted in
X86 ISel. That was spire's Request/Response tests (#2018), which used
`var` as a workaround.

THE FIX

A `let` whose type takes the sret path (_sret_struct_type: a named struct of
at least SRET_MIN_BYTES) is bound like a by-value byval param (#1739): one
entry-block slot, filled by retargeting the sret call into it or by a #1732
copy, and bound in self.locals. Borrows return that slot. Field reads GEP
into it. No first-class %Big value is stored. It is still immutable:
assigning to it is rejected.

Every clang run here is bounded (RLIMIT_AS + timeout).
"""

import os
import re
import resource
import signal
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ0_DIR = Path(__file__).resolve().parent
RITZ_ROOT = RITZ0_DIR.parent

CLANG_TIMEOUT_S = 60
CLANG_MEM_BYTES = 2 * 1024 * 1024 * 1024


def _limit_mem() -> None:
    resource.setrlimit(resource.RLIMIT_AS, (CLANG_MEM_BYTES, CLANG_MEM_BYTES))


def _ritz0(tmp_path: Path, program: str, *extra: str):
    src = tmp_path / "prog.ritz"
    src.write_text(program)
    ll = tmp_path / "prog.ll"
    r = run_ritz0([str(src), "-o", str(ll), *extra], cwd=tmp_path,
                  env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)), timeout=300)
    return r, ll


def _ritz0_ll(tmp_path: Path, program: str, *extra: str) -> str:
    r, ll = _ritz0(tmp_path, program, *extra)
    assert r.returncode == 0 and ll.exists(), (
        f"ritz0 failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return ll.read_text()


def _fn_body(ir: str, fn: str) -> str:
    lines = ir.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("define") and f'@"{fn}"(' in line:
            end = lines.index("}", i)
            return "\n".join(lines[i:end + 1])
    raise AssertionError(f"no define for @{fn}")


def _blocks(body: str) -> list:
    """[(label, [instruction lines])] for a function body; entry first."""
    blocks, cur = [], None
    for line in body.splitlines()[1:-1]:
        m = re.match(r'^"?([\w.$-]+)"?:', line)
        if m:
            cur = (m.group(1), [])
            blocks.append(cur)
        elif line.strip() and cur is not None:
            cur[1].append(line.strip())
    return blocks


BIG_TY = r'%"struct\.[\w.]+\.Big"'

# The ticket's repro: `let` from an sret call, borrowed in two asserts. The
# second borrow is in the first assert's pass block.
REPRO = """\
struct Big
    data: [100000]u8
    n: i64

fn big_new() -> Big
    var b: Big
    b.n = 7
    return b

fn big_n(b: *Big) -> i64
    return b.n

[[test]]
fn test_let_big() -> i32
    let b: Big = big_new()
    assert big_n(@b) == 7
    assert big_n(@b) == 7
    0
"""

# Annotated and inferred lets, from an sret call and from a `var` (a copy),
# borrowed in later blocks: an `if` arm and a loop body.
PROGRAM = """\
struct Big
    data: [100000]u8
    n: i64

fn big_new(n: i64) -> Big
    var b: Big
    b.n = n
    b.data[99999] = 5
    return b

fn big_n(b: *Big) -> i64
    return b.n

fn big_tail(b: *Big) -> i64
    return b.data[99999] as i64

fn main() -> i32
    let b: Big = big_new(7)
    let d = big_new(2)
    var total: i64 = 0
    if big_n(@b) == 7
        total = total + big_n(@b)
    var i: i64 = 0
    while i < 3
        total = total + big_tail(@b) + big_n(@d)
        i = i + 1
    var src: Big = big_new(4)
    let c: Big = src
    if c.n == 4
        total = total + big_n(@c)
    return total as i32
"""
# 7 (if arm) + 3 * (5 + 2) (loop) + 4 (c, copied out of a `var`)
PROGRAM_EXIT = 32


def _assert_no_fca_store(body: str) -> None:
    stores = [ln for ln in body.splitlines()
              if re.search(rf'\bstore {BIG_TY} ', ln)]
    assert not stores, (
        "borrowing a `let` Big stored a first-class %Big:\n" + "\n".join(stores))


@pytest.mark.integration
@pytest.mark.unit
def test_repro_borrows_reuse_the_let_slot(tmp_path):
    ir = _ritz0_ll(tmp_path, REPRO, "--no-runtime")
    body = _fn_body(ir, "test_let_big")
    _assert_no_fca_store(body)
    loads = [ln for ln in body.splitlines() if re.search(rf'= load {BIG_TY}, ', ln)]
    assert not loads, "the sret result was loaded as a first-class %Big:\n" + "\n".join(loads)
    slots = re.findall(rf'(%"[^"]+") = alloca {BIG_TY}', body)
    assert len(slots) == 1, f"want one %Big slot for `b`, got {slots}:\n{body}"
    calls = re.findall(rf'call i64 @"big_n"\({BIG_TY}\* (%"[^"]+")\)', body)
    assert calls == [slots[0]] * 2, (
        f"both borrows must pass the let's slot {slots[0]}, got {calls}:\n{body}")
    assert re.search(rf'call void @"big_new"\({BIG_TY}\* sret\({BIG_TY}\) {re.escape(slots[0])}\)',
                     body), f"big_new() must write straight into the slot:\n{body}"


@pytest.mark.integration
@pytest.mark.unit
def test_borrows_in_later_blocks_store_no_first_class_value(tmp_path):
    body = _fn_body(_ritz0_ll(tmp_path, PROGRAM, "--no-runtime"), "main")
    _assert_no_fca_store(body)
    # Every alloca in the entry block: a borrow in the loop must not grow
    # the stack on each iteration.
    blocks = _blocks(body)
    stray = [(lbl, ln) for lbl, insts in blocks[1:] for ln in insts if " = alloca " in ln]
    assert not stray, f"allocas outside the entry block: {stray}"


@pytest.mark.integration
@pytest.mark.unit
def test_assigning_a_large_let_is_rejected(tmp_path):
    prog = PROGRAM.replace("    var total: i64 = 0\n",
                           "    b = big_new(1)\n    var total: i64 = 0\n")
    r, _ = _ritz0(tmp_path, prog, "--no-runtime")
    out = r.stdout + r.stderr
    assert r.returncode != 0, "assignment to a `let` binding compiled"
    assert "`let` binding `b`" in out, out[-2000:]


SHADOW = """\
struct Big
    data: [1000]u8
    n: i64

fn big_new(n: i64) -> Big
    var b: Big
    b.n = n
    return b

fn main() -> i32
    let b: Big = big_new(1)
    let k: i64 = b.n
    var b: Big = big_new(2)
    b = big_new(9)
    return (b.n + k) as i32
"""


@pytest.mark.integration
@pytest.mark.unit
def test_var_shadowing_a_large_let_is_assignable(tmp_path):
    # Immutability belongs to the `let`'s slot, not to the name.
    body = _fn_body(_ritz0_ll(tmp_path, SHADOW, "--no-runtime"), "main")
    assert re.search(r'call void @"big_new"\([^\n]*, i64 9\)', body), (
        f"`b = big_new(9)` was not emitted:\n{body}")


@pytest.mark.integration
@pytest.mark.parametrize("opt", ["-O0", "-O2"])
def test_program_runs_correctly(tmp_path, opt):
    _ritz0_ll(tmp_path, PROGRAM)
    exe = tmp_path / "prog"
    try:
        link = subprocess.run(
            ["clang", opt, "-nostdlib", "-Wno-override-module",
             str(tmp_path / "prog.ll"), "-o", str(exe)],
            capture_output=True, text=True, timeout=CLANG_TIMEOUT_S,
            preexec_fn=_limit_mem)
    except subprocess.TimeoutExpired:
        pytest.fail(f"clang {opt} exceeded {CLANG_TIMEOUT_S}s")
    assert link.returncode == 0, link.stderr[-2000:]
    run = subprocess.run([str(exe)], capture_output=True, timeout=60)
    assert run.returncode == PROGRAM_EXIT, f"exit {run.returncode}, want {PROGRAM_EXIT}"


@pytest.mark.integration
def test_repro_test_mode_passes_quickly(tmp_path):
    src = tmp_path / "big.ritz"
    src.write_text(REPRO)
    # Own session, so a hung clang is killed with ritz0 rather than orphaned.
    p = subprocess.Popen(
        ["python3", str(RITZ0_DIR / "ritz0.py"), "--test", str(src)],
        cwd=tmp_path, env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        start_new_session=True)
    try:
        out, _ = p.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        p.communicate()
        pytest.fail("ritz0 --test on the #2025 repro exceeded 120s (clang hang)")
    assert p.returncode == 0, out[-2000:]
    assert "1 passed, 0 failed" in out, out[-2000:]
