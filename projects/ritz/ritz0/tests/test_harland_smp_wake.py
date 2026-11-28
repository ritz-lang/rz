"""Wakes, waits and grants across CPUs (AGAST #4881, docs/SMP_USER.md §2, §4).

Slice 2 of #4881 drops the BSP-only gates and adds CAP_INSERT:

* proc/waitq.ritz parks any CPU's current process and wakes BLOCK_IRQ
  waiters from any CPU (the lock-free CAS and kick of proc/table.ritz);
  proc/waitset.ritz's wakes are tested by behaviour in
  test_harland_waitset.py.
* A grant into a process's table runs on the CPU that process is on: the
  BSP posts CAP_INSERT and waits for CAP_INSERT_DONE with the handle, and
  the AP writes its own table at its next safe point.
* A CPU waiting for a reply keeps a FORWARD or RETURN that arrives meanwhile
  as the move it is (counted), never as a dropped stray.
* The shm detach sweep edits BSP-owned rows and may post UNMAP and wait, so
  only the BSP runs it: a wait on an AP leaves it to the BSP, whose idle
  loop runs it too.

The boot-level proof is the smp-user boot test's cross-CPU wake line
(syscall/runtime/smp_user.ritz, tools/test_tier1_boot.sh).
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

HARLAND = Path(__file__).resolve().parents[3] / "harland"
SRC = HARLAND / "kernel" / "src"
WAITQ = SRC / "proc" / "waitq.ritz"
CAP_TABLE = SRC / "cap" / "table.ritz"
MBOX = SRC / "sync" / "mbox.ritz"
TLB = SRC / "mm" / "tlb.ritz"
APCALL = SRC / "arch" / "x86_64" / "apcall.ritz"
DRIVER = SRC / "syscall" / "runtime" / "driver.ritz"
SCHED = SRC / "proc" / "sched.ritz"
SHM = SRC / "mm" / "shm.ritz"
SMP_USER = SRC / "syscall" / "runtime" / "smp_user.ritz"
STUB = HARLAND / "kernel" / "smp_user_stub.s"


def _code(path):
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines())


def _body(code, name):
    m = re.search(rf"^(?:pub\s+)?fn {name}\(.*?(?=^\S)", code + "\nEND", re.M | re.S)
    assert m, f"fn {name} not found"
    return m.group(0)


def test_waitq_parks_and_wakes_on_any_cpu():
    code = _code(WAITQ)
    assert "lapic_is_bsp" not in code
    assert _body(code, "waitq_can_park").split("\n", 1)[1].strip() == "proc_current() != 0 as *Proc"
    assert _body(code, "waitq_wake_irq").split("\n", 1)[1].strip() == "proc_wake(BLOCK_IRQ)"


def test_cap_insert_is_a_mailbox_request_and_reply():
    code = _code(MBOX)
    assert re.search(r"pub const MBOX_CAP_INSERT: u32 = 11\b", code)
    assert re.search(r"pub const MBOX_CAP_INSERT_DONE: u32 = 12\b", code)
    assert "extern fn cap_insert_serve(pid: u64, cap_type: u32, rights: u32, object_id: u64) -> u64" in code
    handle = _body(code, "mbox_handle")
    branch = handle[handle.index("msg.kind == MBOX_CAP_INSERT"):]
    branch = branch[:branch.index("else")]
    assert "cap_insert_serve(msg.pid" in branch and "mbox_msg(MBOX_CAP_INSERT_DONE)" in branch
    assert "mbox_post(msg.from as i32" in branch, branch


def test_a_grant_is_written_by_the_cpu_its_process_is_on():
    code = _code(CAP_TABLE)
    insert = _body(code, "cap_table_insert")
    # The latch first (BSP-owned), then the owner: here, or a CAP_INSERT.
    assert insert.index("shm_latch_create(") < insert.index("proc_on_cpu(")
    assert "insert_remote(" in insert and "table_put(" in insert
    remote = _body(code, "insert_remote")
    assert remote.index("mbox_post(") < remote.index("mbox_wait_reply(MBOX_CAP_INSERT_DONE")
    # Only the BSP waits on another CPU (SMP_USER.md §2 "No deadlock").
    assert "PROC_BSP_CPU" in _body(code, "cap_table_insert")
    serve = _body(code, "cap_insert_serve")
    assert "table_put(" in serve and "shm_latch_create" not in serve
    # The IRQ grant claims first and releases on a refused insert: it never
    # removes from a table on another CPU.
    grant = _body(code, "cap_kernel_grant")
    assert "cap_table_remove" not in grant
    assert grant.index("irq_owner_claim(") < grant.index("cap_table_insert(")
    assert "irq_owner_release(" in grant


def test_a_reply_wait_keeps_the_moves_it_meets():
    code = _code(MBOX)
    aside = _body(code, "mbox_set_aside")
    assert "MBOX_FORWARD" in aside and "MBOX_RETURN" in aside and "mbox_drop_stray(" in aside
    wait = _body(code, "mbox_wait_reply")
    assert "mbox_set_aside(" in wait and "mbox_drop_stray(" in wait
    # The existing reply waits set other kinds aside too.
    for path, name in ((TLB, "tlb_next_reply"), (APCALL, "ap_wait_reply")):
        body = _body(_code(path), name)
        assert "mbox_set_aside(" in body, (path, body)


def test_only_the_bsp_sweeps_the_detach_timeout():
    wait = _body(_code(DRIVER), "wait_collect")
    assert re.search(r"if cpu_index\(\) == PROC_BSP_CPU\n\s+shm_detach_expired\(\)", wait), wait
    idle = _body(_code(SCHED), "sched_idle_main")
    assert re.search(r"if cpu == PROC_BSP_CPU\n\s+shm_detach_expired\(\)", idle), idle
    assert idle.index("shm_detach_expired()") < idle.index("cpu_idle_begin()")
    due = _body(_code(SHM), "shm_detach_wake_due")
    assert "proc_on_cpu(" in due and "PROC_BSP_CPU" in due


def test_the_boot_test_wakes_across_cpus_both_ways():
    code = _code(SMP_USER)
    wake = _body(code, "cross_wake")
    # The AP process's handle reaches it by CAP_INSERT, after it started.
    assert wake.index("wake_spawn(") < wake.index("cap_kernel_grant(")
    assert "cap_inserts_served_count(" in wake
    assert "cross-CPU wake OK: woken on cpu " in SMP_USER.read_text()
    stub = _code(STUB)
    assert "SYS_SHM_WAIT" in stub and "SYS_SHM_NOTIFY" in stub
