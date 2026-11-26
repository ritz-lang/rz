"""DrvIrqWait's wait set and per-object IRQ latch (AGAST #4719, RING1_DRIVER.md §4).

A driver process parks in DrvIrqWait (220) on its own wait set, not on the
shared BLOCK_IRQ queue. proc/waitset.ritz holds what that needs:

* one IRQ object per CAP_TYPE_IRQ object id, with `latched` (bumped by the
  MSI-X path for the vector bound to that object only, or by a kernel post)
  and `seen` (set to `latched` when a wait returns the IRQ record);
* a latch wakes only the object's owner (cap_irq_owner), and only while it
  is parked on its wait set (BLOCK_WAIT): a parked BLOCK_IRQ waiter, or an
  owner of another object, stays parked;
* a per-process deadline that sched_tick's waitset_tick wakes once it has
  passed, without touching the shared LAPIC watchdog.

proc/waitset.ritz imports only proc/table.ritz and declares cap_irq_owner
and lapic_is_bsp, so the behaviour test compiles the real module into a
host program with stand-ins for those two. The syscall's own boot-level
proof is the drv-irq-wait boot test (postinit.ritz), and the ring-3 refusal
is indium's drv_refuse_test Tier-1 program.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link
from ritz0_inproc import run_ritz0

RITZ0_DIR = Path(__file__).resolve().parents[1]
RITZ_ROOT = RITZ0_DIR.parent
PROJECTS = RITZ_ROOT.parent
HARLAND = PROJECTS / "harland"
KERNEL_SRC = HARLAND / "kernel" / "src"
DRIVER = KERNEL_SRC / "syscall" / "runtime" / "driver.ritz"
MSIX = KERNEL_SRC / "drivers" / "msix.ritz"
SCHED = KERNEL_SRC / "proc" / "sched.ritz"
ENTRY = KERNEL_SRC / "syscall" / "runtime" / "entry.ritz"

MODULES = ["syscall/errno.ritz", "proc/table.ritz", "proc/waitset.ritz"]


def _compile(tmp_path, path, name, extra=()):
    ll = tmp_path / f"{name}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path / 'tree'}:{RITZ_ROOT}:{tmp_path}")
    proc = run_ritz0([str(path), "-o", str(ll), *extra], cwd=tmp_path, env=env, timeout=300)
    assert proc.returncode == 0 and ll.exists(), f"ritz0 rejected {name}:\n{proc.stdout}{proc.stderr}"
    return ll


def _run(tmp_path, src):
    """Compile the real proc/table.ritz and proc/waitset.ritz with `src`, link, run."""
    tree = tmp_path / "tree"
    for rel in MODULES:
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_text((KERNEL_SRC / rel).read_text())
    objs = [str(_compile(tmp_path, tree / rel, rel[:-5].replace("/", "_"), ("--no-runtime",)))
            for rel in MODULES]
    (tmp_path / "t.ritz").write_text(src)
    objs.insert(0, str(_compile(tmp_path, tmp_path / "t.ritz", "t")))
    exe = tmp_path / "t"
    link = fast_link.clang(["clang", "-Wno-override-module", *objs, "-o", str(exe),
                            "-nostdlib", "-no-pie"], capture_output=True, text=True)
    assert link.returncode == 0, f"link failed:\n{link.stderr[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60, check=False).returncode


# Exit status: the number of the first claim that failed, 0 if all held.
WAITSET = """\
import proc.table
import proc.waitset

const OBJ_A: u64 = 0xA0
const OBJ_B: u64 = 0xB0
const VEC_A: u8 = 64
const DRIVER: u64 = 2               # slot 1 owns A
const OTHER: u64 = 3                # slot 2 owns B

# The kernel's are cap/table.ritz cap_irq_owner and apic.ritz lapic_is_bsp.
pub fn cap_irq_owner(object_id: u64) -> u32
    if object_id == OBJ_A
        return DRIVER as u32
    if object_id == OBJ_B
        return OTHER as u32
    0

pub fn lapic_is_bsp() -> bool
    true

fn park(slot: i32, reason: u8)
    let was: i32 = proc_current_slot()
    proc_set_current(slot)
    proc_block(reason, 0)
    proc_set_current(was)

fn parked(slot: i32, reason: u8) -> bool
    proc_at(slot).state == PROC_BLOCKED and proc_at(slot).block == reason

fn running(slot: i32) -> bool
    proc_at(slot).state == PROC_RUNNING

fn main() -> i32
    proc_table_reset()
    proc_enter_init(0)
    let d: i32 = proc_new_child()
    proc_start(d)
    let o: i32 = proc_new_child()
    proc_start(o)
    if proc_at(d).pid != DRIVER or proc_at(o).pid != OTHER
        return 100

    if not irq_object_register(OBJ_A, VEC_A) or not irq_object_register(OBJ_B, IRQ_NO_VECTOR)
        return 101
    if not irq_object_known(OBJ_A) or irq_object_known(OBJ_A + 1)
        return 22
    # One object per id.
    if irq_object_register(OBJ_A, VEC_A)
        return 1
    if irq_object_take(OBJ_A)
        return 2

    # An MSI-X on another vector latches nothing and wakes nobody.
    park(d, BLOCK_WAIT)
    park(o, BLOCK_WAIT)
    irq_object_fire_vector(VEC_A as u64 + 1)
    if not parked(d, BLOCK_WAIT) or irq_object_take(OBJ_A)
        return 3
    # A's vector latches A and wakes A's owner only.
    irq_object_fire_vector(VEC_A as u64)
    if not running(d)
        return 4
    if not parked(o, BLOCK_WAIT)
        return 5
    # Taking it sets seen = latched: the same interrupt is returned once.
    if not irq_object_take(OBJ_A)
        return 6
    if irq_object_take(OBJ_A)
        return 7

    # A kernel post on B wakes B's owner and leaves A cold.
    irq_object_latch(OBJ_B)
    if not running(o) or irq_object_take(OBJ_A)
        return 8
    if not irq_object_take(OBJ_B)
        return 9

    # An interrupt before the park is not lost: the latch holds it.
    irq_object_latch(OBJ_A)
    if not running(d)
        return 10
    if not irq_object_take(OBJ_A)
        return 11

    # A latch does not wake its owner out of another wait (the shared
    # BLOCK_IRQ queue, a child wait): it is not parked on its wait set.
    park(d, BLOCK_IRQ)
    irq_object_latch(OBJ_A)
    if not parked(d, BLOCK_IRQ)
        return 12
    proc_wake(BLOCK_IRQ)
    if not irq_object_take(OBJ_A)
        return 13

    # Deadlines: the tick wakes the wait set whose deadline has passed, and
    # no other.
    park(d, BLOCK_WAIT)
    waitset_arm(d, 100)
    park(o, BLOCK_WAIT)
    waitset_arm(o, 1000)
    waitset_tick(99)
    if not parked(d, BLOCK_WAIT) or not parked(o, BLOCK_WAIT)
        return 14
    waitset_tick(100)
    if not running(d)
        return 15
    if not parked(o, BLOCK_WAIT)
        return 16
    # A disarmed set is not woken, however late.
    waitset_disarm(o)
    waitset_tick(0xFFFFFFFFFFFFFFFF)
    if not parked(o, BLOCK_WAIT)
        return 17
    # An armed deadline wakes only a wait-set park: not another block.
    proc_wake_pid(OTHER, BLOCK_WAIT)
    park(o, BLOCK_TTY)
    waitset_arm(o, 1)
    waitset_tick(2)
    if not parked(o, BLOCK_TTY)
        return 18
    waitset_disarm(o)
    proc_wake(BLOCK_TTY)

    # An unregistered object latches nothing.
    irq_object_unregister(OBJ_A)
    if irq_object_known(OBJ_A) or irq_object_latch(OBJ_A)
        return 19
    if irq_object_take(OBJ_A)
        return 20
    # Its id can be registered again, cold.
    if not irq_object_register(OBJ_A, VEC_A) or irq_object_take(OBJ_A)
        return 21
    0
"""


@pytest.mark.integration
def test_waitset_latch_wake_and_deadline(tmp_path):
    assert _run(tmp_path, WAITSET) == 0


def _fn_body(src, name):
    m = re.search(rf"^(?:pub )?fn {name}\(.*?(?=^\S)", src, re.M | re.S)
    assert m, f"no fn {name}"
    return m.group(0)


def test_drv_irq_wait_does_not_touch_the_shared_watchdog():
    """The deadline lives on the wait set: DrvIrqWait never arms or stops the
    LAPIC watchdog irq_wait_vector shares, and never parks on BLOCK_IRQ."""
    src = DRIVER.read_text()
    code = "\n".join(line.split("#", 1)[0] for line in src.splitlines())
    for banned in ("lapic_watchdog", "BLOCK_IRQ", "waitq_park", "irq_wait_vector"):
        assert banned not in code, f"driver.ritz uses {banned}"
    assert "BLOCK_WAIT" in code and "sched_block" in code


def test_msix_dispatch_latches_the_vectors_object():
    """msix_dispatch counts the vector and then latches that vector's IRQ
    object, before irq_handler's waitq_wake_irq and EOI."""
    body = _fn_body(MSIX.read_text(), "msix_dispatch")
    assert "irq_object_fire_vector(vector)" in body, body


def test_sched_tick_expires_wait_set_deadlines():
    body = _fn_body(SCHED.read_text(), "sched_tick")
    assert "waitset_tick(" in body, body


def test_entry_registers_drv_irq_wait():
    src = ENTRY.read_text()
    assert "syscall_register(Syscall.DrvIrqWait, sys_drv_irq_wait_handler)" in src
