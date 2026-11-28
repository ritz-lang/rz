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

proc/waitset.ritz imports only proc/table.ritz and declares cap_irq_owner,
so the behaviour test compiles the real module into a host program with a
stand-in for it. The syscall's own boot-level
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

# The per-CPU hooks proc/table.ritz, fs/syscall.ritz and syscall/dispatch.ritz
# declare `extern` (AGAST #4879): the kernel's are arch/x86_64/percpu.ritz
# cpu_index and sync/idle.ritz cpu_kick_if_idle. One CPU here.
CPU_HOOKS = """
pub fn cpu_index() -> i32
    0

pub fn cpu_kick_if_idle(cpu: i32)
    return
"""

RITZ0_DIR = Path(__file__).resolve().parents[1]
RITZ_ROOT = RITZ0_DIR.parent
PROJECTS = RITZ_ROOT.parent
HARLAND = PROJECTS / "harland"
KERNEL_SRC = HARLAND / "kernel" / "src"
DRIVER = KERNEL_SRC / "syscall" / "runtime" / "driver.ritz"
MSIX = KERNEL_SRC / "drivers" / "msix.ritz"
SCHED = KERNEL_SRC / "proc" / "sched.ritz"
ENTRY = KERNEL_SRC / "syscall" / "runtime" / "entry.ritz"
CONSOLE = KERNEL_SRC / "tty" / "console.ritz"

# Tree path -> real source. driver_abi.wait (the WaitEvent layout and the
# event bits) is a leaf the kernel takes from the driver_abi package.
MODULES = {
    "syscall/errno.ritz": KERNEL_SRC / "syscall" / "errno.ritz",
    "proc/table.ritz": KERNEL_SRC / "proc" / "table.ritz",
    "driver_abi/wait.ritz": HARLAND / "driver_abi" / "src" / "wait.ritz",
    "proc/waitset.ritz": KERNEL_SRC / "proc" / "waitset.ritz",
}


def _compile(tmp_path, path, name, extra=()):
    ll = tmp_path / f"{name}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path / 'tree'}:{RITZ_ROOT}:{tmp_path}")
    proc = run_ritz0([str(path), "-o", str(ll), *extra], cwd=tmp_path, env=env, timeout=300)
    assert proc.returncode == 0 and ll.exists(), f"ritz0 rejected {name}:\n{proc.stdout}{proc.stderr}"
    return ll


def _run(tmp_path, src, hooks=CPU_HOOKS):
    """Compile the real proc/table.ritz and proc/waitset.ritz with `src`
    (and the CPU `hooks`), link, run."""
    tree = tmp_path / "tree"
    for rel, real in MODULES.items():
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_text(real.read_text())
    objs = [str(_compile(tmp_path, tree / rel, rel[:-5].replace("/", "_"), ("--no-runtime",)))
            for rel in MODULES]
    (tmp_path / "t.ritz").write_text(src + hooks)
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

# The kernel's is cap/table.ritz cap_irq_owner.
pub fn cap_irq_owner(object_id: u64) -> u32
    if object_id == OBJ_A
        return DRIVER as u32
    if object_id == OBJ_B
        return OTHER as u32
    0

fn park(slot: i32, reason: u8)
    let was: i32 = proc_current_slot()
    proc_set_current(slot)
    proc_block(reason, 0)
    proc_set_current(was)

fn parked(slot: i32, reason: u8) -> bool
    proc_state(slot) == PROC_BLOCKED and proc_at(slot).block == reason

fn running(slot: i32) -> bool
    proc_state(slot) == PROC_RUNNING

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
    # The device's DMA domain (AGAST #4724): none until bound; a binding
    # names one object; an unregistered id binds nothing; re-registering
    # starts with none.
    if irq_object_domain(OBJ_A) != 0 or irq_object_bind_domain(OBJ_A + 1, 2) or irq_object_domain(OBJ_A + 1) != 0
        return 28
    if not irq_object_bind_domain(OBJ_A, 2) or irq_object_domain(OBJ_A) != 2 or irq_object_domain(OBJ_B) != 0
        return 28
    irq_object_unregister(OBJ_A)
    if irq_object_domain(OBJ_A) != 0 or not irq_object_register(OBJ_A, VEC_A) or irq_object_domain(OBJ_A) != 0
        return 29

    # The console on the wait set (#4829, a timed poll on fd 0): console
    # input wakes each slot watching it while parked on its wait set, and
    # no other.
    park(d, BLOCK_WAIT)
    waitset_watch_console(d)
    park(o, BLOCK_WAIT)
    waitset_console_ready()
    if not running(d)
        return 23
    if not parked(o, BLOCK_WAIT)
        return 24
    # A watcher blocked for anything else is not woken (the console's own
    # BLOCK_TTY readers are proc_wake's).
    park(d, BLOCK_TTY)
    waitset_console_ready()
    if not parked(d, BLOCK_TTY)
        return 25
    proc_wake(BLOCK_TTY)
    # Disarming ends the watch as well as the deadline.
    waitset_disarm(d)
    park(d, BLOCK_WAIT)
    waitset_console_ready()
    if not parked(d, BLOCK_WAIT)
        return 26
    # A watch with a deadline: the deadline wakes it with no input.
    waitset_watch_console(d)
    waitset_arm(d, 50)
    waitset_tick(50)
    if not running(d)
        return 27
    waitset_disarm(d)
    proc_wake_pid(OTHER, BLOCK_WAIT)
    0
"""


@pytest.mark.integration
def test_waitset_latch_wake_and_deadline(tmp_path):
    assert _run(tmp_path, WAITSET) == 0


# Shm latches, ShmNotify, the inbox and the collect step both waits share
# (AGAST #4727, RING1_DRIVER.md "Wait and notify"). Exit status: the number
# of the first claim that failed, 0 if all held.
SHM_WAIT = """\
import proc.table
import proc.waitset
import driver_abi.wait

const IRQ: u64 = 0xA0               # the driver's IRQ object
const FRAME: u64 = 7                # shm object ids: the frame object,
const APP1: u64 = 8                 # two app exchanges,
const APP2: u64 = 9
const LONE: u64 = 10                # and one only the driver holds
const DRIVER: u64 = 2
const SERVICE: u64 = 3
const APP: u64 = 4
const NOBODY: u64 = 9               # no process has this pid
# Handles are opaque to the wait set: it copies them into the records.
const H_IRQ: u64 = 0x100000000
const H_FRAME: u64 = 0x200000001
const H_LONE: u64 = 0x300000002
const H_APP1: u64 = 0x400000003
const H_APP2: u64 = 0x500000004

pub fn cap_irq_owner(object_id: u64) -> u32
    if object_id == IRQ
        return DRIVER as u32
    0

fn park(slot: i32)
    let was: i32 = proc_current_slot()
    proc_set_current(slot)
    proc_block(BLOCK_WAIT, 0)
    proc_set_current(was)

fn parked(slot: i32) -> bool
    proc_state(slot) == PROC_BLOCKED and proc_at(slot).block == BLOCK_WAIT

fn running(slot: i32) -> bool
    proc_state(slot) == PROC_RUNNING

fn is_posted(n: Notify) -> bool
    match n
        Notify.Posted => true
        _ => false

fn is_bad_bits(n: Notify) -> bool
    match n
        Notify.BadBits => true
        _ => false

fn is_no_peer(n: Notify) -> bool
    match n
        Notify.NoPeer => true
        _ => false

fn has(got: *Collected, i: u32, handle: u64, bits: u32) -> bool
    got.events[i as i32].handle == handle and got.events[i as i32].bits == bits

# The driver's wait: the IRQ, then the frame object and LONE.
fn driver_plan(frame_mask: u32) -> WaitPlan
    var plan: WaitPlan = wait_plan_irq(H_IRQ, IRQ)
    wait_plan_add(@plan, H_FRAME, FRAME, frame_mask)
    wait_plan_add(@plan, H_LONE, LONE, EVENT_DATA)
    plan

fn main() -> i32
    proc_table_reset()
    proc_enter_init(0)
    let d: i32 = proc_new_child()
    proc_start(d)
    let s: i32 = proc_new_child()
    proc_start(s)
    let a: i32 = proc_new_child()
    proc_start(a)
    if proc_at(d).pid != DRIVER or proc_at(s).pid != SERVICE or proc_at(a).pid != APP
        return 100
    if not irq_object_register(IRQ, IRQ_NO_VECTOR)
        return 101

    # One latch per (object, holding pid), made when the handle is
    # inserted: a second insert of the same pair adds none, so one drop
    # ends it.
    if not shm_latch_create(LONE, DRIVER) or not shm_latch_create(LONE, DRIVER)
        return 1
    shm_latch_drop(LONE, DRIVER)
    if shm_latch_held(LONE, DRIVER)
        return 2
    if not shm_latch_create(LONE, DRIVER) or not shm_latch_create(FRAME, DRIVER) or not shm_latch_create(FRAME, SERVICE)
        return 3
    if not shm_latch_create(APP1, SERVICE) or not shm_latch_create(APP1, APP)
        return 4
    if not shm_latch_create(APP2, SERVICE) or not shm_latch_create(APP2, APP)
        return 5

    # ShmNotify with no other holder: NoDev, nothing posted.
    if not is_no_peer(shm_notify(LONE, DRIVER, EVENT_DATA)) or shm_latch_bits(LONE, DRIVER) != 0
        return 6
    # Userspace may post DATA and SPACE only: zero, a kernel bit, a mix
    # holding one, and the reserved bit are refused, and the peer's latch
    # (and so its attachment) is untouched.
    if not is_bad_bits(shm_notify(APP1, APP, EVENT_PEER_CLOSE))
        return 7
    if not is_bad_bits(shm_notify(APP1, APP, EVENT_DATA | EVENT_DRIVER_GONE))
        return 8
    if not is_bad_bits(shm_notify(APP1, APP, 0)) or not is_bad_bits(shm_notify(APP1, APP, EVENT_RESERVED_32))
        return 9
    if shm_latch_bits(APP1, SERVICE) != 0 or not shm_latch_held(APP1, SERVICE)
        return 10

    # A TX notify before the driver parks lands on the driver's latch (it has
    # mapped nothing; the latch is the handle's), not the notifier's.
    if not is_posted(shm_notify(FRAME, SERVICE, EVENT_DATA))
        return 11
    if shm_latch_bits(FRAME, DRIVER) != EVENT_DATA or shm_latch_bits(FRAME, SERVICE) != 0
        return 12
    # The driver's next wait copies it without parking, and the IRQ is cold:
    # the IRQ flag is clear (DrvIrqWait returns 2), one record, latch cleared.
    var plan: WaitPlan = driver_plan(EVENT_DATA)
    # The eventcount sleeper's re-check (#4879) sees it and takes nothing.
    if not waitset_pending(@plan, DRIVER) or shm_latch_bits(FRAME, DRIVER) != EVENT_DATA
        return 80
    var got: Collected = waitset_collect(@plan, DRIVER, 8)
    if got.count != 1 or got.irq or not has(@got, 0, H_FRAME, EVENT_DATA)
        return 13
    if shm_latch_bits(FRAME, DRIVER) != 0
        return 14
    # Nothing hot: an empty collection (the wait parks or returns 1).
    got = waitset_collect(@plan, DRIVER, 8)
    if got.count != 0 or got.irq
        return 15
    if waitset_pending(@plan, DRIVER)
        return 81

    # A notify wakes the peer parked on its wait set, and only it.
    park(d)
    park(s)
    shm_notify(FRAME, SERVICE, EVENT_DATA)
    if not running(d) or not parked(s)
        return 16
    proc_wake_pid(SERVICE, BLOCK_WAIT)

    # out_cap 2 with four hot sources: the IRQ record first, then the frame
    # object's; LONE's kernel post and the inbox record stay for the next
    # wait, which returns them without the IRQ.
    irq_object_latch(IRQ)
    if not shm_latch_post(LONE, DRIVER, EVENT_PEER_CLOSE)
        return 17
    if not waitset_inbox_post(DRIVER, 0x77, EVENT_ATTACH)
        return 18
    got = waitset_collect(@plan, DRIVER, 2)
    if got.count != 2 or not got.irq
        return 19
    if not has(@got, 0, H_IRQ, EVENT_DATA) or not has(@got, 1, H_FRAME, EVENT_DATA)
        return 20
    if shm_latch_bits(LONE, DRIVER) != EVENT_PEER_CLOSE or waitset_inbox_len(DRIVER) != 1
        return 21
    # A kernel bit is copied whatever the mask (LONE's lists DATA only).
    got = waitset_collect(@plan, DRIVER, 8)
    if got.count != 2 or got.irq
        return 22
    if not has(@got, 0, H_LONE, EVENT_PEER_CLOSE) or not has(@got, 1, 0x77, EVENT_ATTACH)
        return 23
    if shm_latch_bits(LONE, DRIVER) != 0 or waitset_inbox_len(DRIVER) != 0
        return 24

    # The mask picks among DATA and SPACE: an unlisted bit stays latched
    # and is copied (only it) once the mask names it.
    shm_notify(FRAME, SERVICE, EVENT_SPACE)
    got = waitset_collect(@plan, DRIVER, 8)
    if got.count != 0 or shm_latch_bits(FRAME, DRIVER) != EVENT_SPACE
        return 25
    var spaced: WaitPlan = driver_plan(EVENT_DATA | EVENT_SPACE)
    got = waitset_collect(@spaced, DRIVER, 8)
    if got.count != 1 or not has(@got, 0, H_FRAME, EVENT_SPACE)
        return 26

    # One service wait returns every hot source, in the caller's order, then
    # the inbox in queue order. SPACE, outside the frame's mask, stays.
    shm_notify(APP2, APP, EVENT_DATA)
    shm_notify(APP1, APP, EVENT_DATA)
    shm_notify(FRAME, DRIVER, EVENT_DATA | EVENT_SPACE)
    waitset_inbox_post(SERVICE, 0x81, EVENT_ATTACH)
    waitset_inbox_post(SERVICE, 0x82, EVENT_ATTACH)
    var svc: WaitPlan = wait_plan_new()
    wait_plan_add(@svc, H_FRAME, FRAME, EVENT_DATA)
    wait_plan_add(@svc, H_APP1, APP1, EVENT_DATA)
    wait_plan_add(@svc, H_APP2, APP2, EVENT_DATA)
    got = waitset_collect(@svc, SERVICE, 8)
    if got.count != 5 or got.irq
        return 27
    if not has(@got, 0, H_FRAME, EVENT_DATA) or not has(@got, 1, H_APP1, EVENT_DATA) or not has(@got, 2, H_APP2, EVENT_DATA)
        return 28
    if not has(@got, 3, 0x81, EVENT_ATTACH) or not has(@got, 4, 0x82, EVENT_ATTACH)
        return 29
    if shm_latch_bits(FRAME, SERVICE) != EVENT_SPACE
        return 30

    # Retire's kernel post (#4729): PEER_CLOSE or DRIVER_GONE lands on every
    # other holder's latch, never the poster's own, and wakes a parked
    # holder. A kernel bit is not BadBits here. With no other holder it
    # posts nothing.
    park(s)
    if not shm_latch_post_peers(APP1, APP, EVENT_PEER_CLOSE)
        return 41
    if shm_latch_bits(APP1, SERVICE) != EVENT_PEER_CLOSE or shm_latch_bits(APP1, APP) != 0 or not running(s)
        return 42
    if shm_latch_post_peers(LONE, DRIVER, EVENT_DRIVER_GONE) or shm_latch_bits(LONE, DRIVER) != 0
        return 43
    # A listed source reports it whatever the mask, and the copy clears it.
    var closed: WaitPlan = wait_plan_new()
    wait_plan_add(@closed, H_APP1, APP1, EVENT_SPACE)
    got = waitset_collect(@closed, SERVICE, 1)
    if got.count != 1 or not has(@got, 0, H_APP1, EVENT_PEER_CLOSE) or shm_latch_bits(APP1, SERVICE) != 0
        return 44

    # The inbox holds eight records: a ninth is refused. A wait with no
    # sources copies them in order, as many as fit; the rest stay queued.
    var h: u64 = 1
    while h <= 8
        if not waitset_inbox_post(SERVICE, h, EVENT_ATTACH)
            return 31
        h = h + 1
    if waitset_inbox_post(SERVICE, 9, EVENT_ATTACH) or waitset_inbox_len(SERVICE) != 8
        return 32
    var empty: WaitPlan = wait_plan_new()
    got = waitset_collect(@empty, SERVICE, 3)
    if got.count != 3 or not has(@got, 0, 1, EVENT_ATTACH) or not has(@got, 2, 3, EVENT_ATTACH)
        return 33
    got = waitset_collect(@empty, SERVICE, 8)
    if got.count != 5 or not has(@got, 0, 4, EVENT_ATTACH) or not has(@got, 4, 8, EVENT_ATTACH)
        return 34

    # Kernel posts wake a parked holder too: a latch post and an inbox post.
    park(d)
    shm_latch_post(FRAME, DRIVER, EVENT_LINK)
    if not running(d)
        return 35
    park(s)
    waitset_inbox_post(SERVICE, 0x90, EVENT_ATTACH)
    if not running(s)
        return 36
    # A post to a pid with no latch or no process lands nowhere.
    if shm_latch_post(FRAME, APP, EVENT_LINK) or waitset_inbox_post(NOBODY, 1, EVENT_ATTACH)
        return 37

    # A process that drops its last handle has no latch: notifying the
    # object it shared finds no other holder.
    shm_latch_drop(LONE, DRIVER)
    shm_latch_drop(FRAME, DRIVER)
    if not is_no_peer(shm_notify(FRAME, SERVICE, EVENT_DATA))
        return 38
    # Exit forgets every latch and the inbox of that pid, and no other.
    waitset_forget_pid(SERVICE)
    if shm_latch_held(APP1, SERVICE) or shm_latch_held(APP2, SERVICE) or waitset_inbox_len(SERVICE) != 0
        return 39
    if not shm_latch_held(APP1, APP) or not is_no_peer(shm_notify(APP1, APP, EVENT_DATA))
        return 40
    0
"""


@pytest.mark.integration
def test_shm_latches_notify_inbox_and_collect(tmp_path):
    assert _run(tmp_path, SHM_WAIT) == 0


# Wakes across CPUs (AGAST #4881, SMP_USER.md §4 "Consequences"): a post
# made on an AP wakes a waiter parked on the BSP with the CAS, and kicks the
# BSP if it idles, for each of the wait set's three kinds of post. The hooks
# let the program say which CPU it runs on, and record the kicks.
SMP_HOOKS = """
var host_cpu: i32 = 0
var kicked_cpu: i32 = -1
var kicks: i32 = 0

pub fn cpu_index() -> i32
    host_cpu

pub fn cpu_kick_if_idle(cpu: i32)
    kicked_cpu = cpu
    kicks = kicks + 1
"""

WAKE_FROM_AP = """\
import proc.table
import proc.waitset
import driver_abi.wait { EVENT_DATA }

const IRQ: u64 = 0x10
const SHM: u64 = 0x20
const DRIVER: u64 = 2
const PEER: u64 = 3
const AP: i32 = 3

pub fn cap_irq_owner(object_id: u64) -> u32
    if object_id == IRQ
        return DRIVER as u32
    0

# Park `slot` on its wait set, as the BSP: it is homed there.
fn park(slot: i32)
    host_cpu = 0
    let was: i32 = proc_current_slot()
    proc_set_current(slot)
    proc_block(BLOCK_WAIT, 0)
    proc_set_current(was)

fn woken_by_ap(slot: i32) -> bool
    let ok: bool = proc_state(slot) == PROC_RUNNING and kicked_cpu == PROC_BSP_CPU and kicks == 1
    kicks = 0
    kicked_cpu = -1
    host_cpu = 0
    ok

fn main() -> i32
    proc_table_reset()
    proc_enter_init(0)
    let d: i32 = proc_new_child()
    proc_start(d)
    let p: i32 = proc_new_child()
    proc_start(p)
    if proc_at(d).pid != DRIVER or proc_at(p).pid != PEER
        return 100
    if not irq_object_register(IRQ, IRQ_NO_VECTOR)
        return 101
    if not shm_latch_create(SHM, DRIVER) or not shm_latch_create(SHM, PEER)
        return 102
    kicks = 0

    # A ShmNotify on the AP wakes the BSP's waiter, and kicks the BSP.
    park(d)
    host_cpu = AP
    shm_notify(SHM, PEER, EVENT_DATA)
    if not woken_by_ap(d)
        return 1
    # An IRQ object latched on the AP (an MSI-X aimed there) wakes its owner.
    park(d)
    host_cpu = AP
    irq_object_latch(IRQ)
    if not woken_by_ap(d)
        return 2
    # A kernel inbox post made on the AP wakes the process it is for.
    park(d)
    host_cpu = AP
    waitset_inbox_post(DRIVER, 0x55, EVENT_DATA)
    if not woken_by_ap(d)
        return 3
    0
"""


@pytest.mark.integration
def test_a_post_on_an_ap_wakes_a_waiter_on_the_bsp(tmp_path):
    """No BSP-only gate is left in the wait set (AGAST #4881): a ShmNotify,
    an IRQ latch and an inbox post made on an AP each wake the waiter parked
    on the BSP (the CAS) and kick its CPU."""
    assert _run(tmp_path, WAKE_FROM_AP, SMP_HOOKS) == 0
    assert "lapic_is_bsp" not in (KERNEL_SRC / "proc" / "waitset.ritz").read_text()


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
    # The BSP's tick, for every slot (#4881: an AP's tick only preempts).
    assert "if cpu == PROC_BSP_CPU\n        sched_tick_global(from_user)" in _fn_body(SCHED.read_text(), "sched_tick")
    body = _fn_body(SCHED.read_text(), "sched_tick_global")
    assert "waitset_tick(" in body, body


def test_entry_registers_drv_irq_wait():
    src = ENTRY.read_text()
    assert "syscall_register(Syscall.DrvIrqWait, sys_drv_irq_wait_handler)" in src


def test_console_input_wakes_console_watchers():
    """#4829: console input (COM1's receive interrupt, and since #4888 every
    keyboard, all through tty_console_input) wakes the BLOCK_TTY readers and
    the wait sets watching the console (a timed poll on fd 0)."""
    body = _fn_body(CONSOLE.read_text(), "tty_console_input")
    assert "proc_wake(BLOCK_TTY)" in body and "waitset_console_ready()" in body, body


def test_entry_registers_poll():
    src = ENTRY.read_text()
    assert "syscall_register(Syscall.Poll, sys_poll_handler)" in src


PROCESS = KERNEL_SRC / "syscall" / "runtime" / "process.ritz"


def test_sched_tick_runs_the_detach_timeout_only_over_user_code():
    """#4729: SHM_DETACH_TIMEOUT_MS unmaps a peer from the tick, but only a
    tick that interrupted CPL 3: the PMM and vmm_unmap_page_in are not
    reentrant, so a tick over kernel code only wakes the parked holders."""
    body = _fn_body(SCHED.read_text(), "sched_tick_global")
    assert "if from_user\n        shm_detach_expired()" in body, body
    assert "shm_detach_wake_due()" in body, body


def test_wait_runs_the_detach_timeout_before_it_collects():
    """A holder parked in a wait sweeps before it collects, so no wait
    returns to user with a mapping the timeout should have taken."""
    body = _fn_body(DRIVER.read_text(), "wait_collect")
    assert body.index("shm_detach_expired()") < body.index("waitset_collect("), body


def test_exit_retires_held_objects_before_freeing_the_table():
    """App, service or driver exit retires each shm object it held (posting
    PEER_CLOSE, or DRIVER_GONE for an IRQ owner) before its capability table,
    latches and mappings go."""
    body = _fn_body(PROCESS.read_text(), "sys_exit_impl")
    assert "cap_retire_held_shm(me.pid as u32)" in body, body
    assert body.index("cap_retire_held_shm(") < body.index("cap_table_free_pid("), body
