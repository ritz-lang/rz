"""netd's exit or fault, and its restart (AGAST #4745, ring plan T39,
harland docs/RING2_NET.md "Frame seat" and "Service binary and respawn",
docs/RING1_DRIVER.md "Shared object", "Service exit first").

When the registered ring-2 service exits or faults, the kernel invalidates
the address snapshot (NetAddr is NoDev), retires every shm object it held
(each app exchange and the frame object get PEER_CLOSE on the other
holder's latch, which wakes it), and unregisters it. It then restarts
/bin/netd at most three times per boot, 250 ms, 500 ms and 1 s after the
first three deaths: each replacement gets a new address page (its first
shared mapping, DRV_RING_BASE), a new frame object mapped before it runs,
with both indexes at 0, and the driver gets that object's handle as ATTACH
on its inbox. The fourth death starts nothing and is logged; NetAddr stays
NoDev.

The behaviour is tools/test_msix_boot.sh's vtd run, with the
\\harland\\netd-restart marker (its verdicts are host-tested in
projects/ritz/tools/test_ci_msix_boot.py). These checks pin the order and
the guards that run can't observe.
"""

import re
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).resolve().parents[1]
HARLAND = RITZ0_DIR.parent.parent / "harland"
KERNEL_SRC = HARLAND / "kernel" / "src"
MAIN = KERNEL_SRC / "main.ritz"
RING1 = KERNEL_SRC / "net" / "ring1.ritz"
NET_RT = KERNEL_SRC / "syscall" / "runtime" / "net.ritz"
PROCESS = KERNEL_SRC / "syscall" / "runtime" / "process.ritz"
PROC_TABLE = KERNEL_SRC / "proc" / "table.ritz"
DRIVER = HARLAND / "system" / "src" / "virtio_net.ritz"
LOADER = HARLAND / "boot" / "src" / "main.ritz"
HANDOFF = HARLAND / "boot_abi" / "src" / "handoff.ritz"


def _code(path):
    return "\n".join(l.split("#", 1)[0].rstrip() for l in path.read_text().splitlines())


def _fn_body(src, name):
    m = re.search(rf"^(?:pub )?fn {name}\(.*?(?=^\S)", src + "\nEND", re.M | re.S)
    assert m, f"no fn {name}"
    return m.group(0)


def _in_order(body, *needles):
    at = -1
    for n in needles:
        i = body.find(n, at + 1)
        assert i > at, f"{n!r} missing or out of order"
        at = i


@pytest.mark.unit
def test_the_budget_is_three_restarts_with_a_doubling_backoff():
    body = _fn_body(_code(NET_RT), "net_restart_backoff_ms")
    for ms in ("250", "500", "1000"):
        assert ms in body, ms
    assert re.search(r"^pub const NETD_RESTARTS: u32 = 3$", _code(NET_RT), re.M)
    assert "None" in body


@pytest.mark.unit
def test_a_death_invalidates_then_unregisters_the_service_and_its_frame_object():
    body = _fn_body(_code(NET_RT), "net_service_exited")
    _in_order(body, "addr_generation = LINK_SEQ_UNPUBLISHED", "net_addr_object = 0", "net_service = 0")
    # The dead service is no longer the frame object's consumer: no LINK
    # post reaches its pid.
    assert "net_frame_consumer == pid as u64" in body and "net_frame_register(0, 0)" in body


@pytest.mark.unit
def test_exit_retires_before_it_invalidates_and_restarts_last():
    """Apps and the driver see PEER_CLOSE (cap_retire_held_shm) and NetAddr
    is NoDev before any backoff starts; the restart runs after the dead
    service's address space is gone and before its slot is, on the kernel's
    page table: the backoff yields, and a switch back to the dying process
    loads its Proc.pml4."""
    body = _fn_body(_code(PROCESS), "sys_exit_impl")
    _in_order(body, "cap_retire_held_shm(", "cap_table_free_pid(", "net_service_exited(",
              "vmm_free_pml4(my_pml4)", "(*me).pml4 = g_kernel_pml4", "netd_restart(", "proc_exit_current(")
    assert "if was_service" in body


@pytest.mark.unit
def test_the_restart_waits_out_its_backoff_then_spawns_and_installs():
    body = _fn_body(_code(PROCESS), "netd_restart")
    _in_order(body, "net_service_death()", "net_restart_backoff_ms(", "budget spent",
              "netd_backoff(ms)", "net_restart_driver_pid()", 'process_spawn_program("/bin/netd")',
              "net_service_install(")
    # The backoff lets the other processes run (the dying context is not
    # preemptible) and sleeps when nothing else can.
    wait = _fn_body(_code(PROCESS), "netd_backoff")
    _in_order(wait, "deadline_after_us(ms * 1000)", "enable_interrupts()", "deadline_passed(",
              "sched_yield()", "sti_hlt()")
    # A replacement that could not be set up exits before it runs, as an
    # unregistered process: its death is not a service death.
    assert "process_mark_exit(" in body.split("net_service_install(")[1]


@pytest.mark.unit
def test_no_restart_without_a_surviving_driver():
    """Driver death is not this path: netd exits on DRIVER_GONE and the
    kernel starts no replacement for it (RING1_DRIVER.md "Driver exit first")."""
    death = _fn_body(_code(NET_RT), "net_service_death")
    assert "net_restart_driver == 0" in death
    quiesced = _fn_body(_code(NET_RT), "net_driver_quiesced")
    assert "net_restart_driver = 0" in quiesced


@pytest.mark.unit
def test_the_replacement_is_set_up_before_it_runs():
    """Its address page is its first shared mapping (netd checks ShmMap
    returns DRV_RING_BASE); the new frame object maps after it, ATTACH goes
    to the driver, and the ServiceBoot names both with the seat indexes at 0.
    Only then is it the registered service."""
    body = _fn_body(_code(NET_RT), "net_service_install")
    _in_order(body, "net_service_page(", "net_frame_replace(", "net_service_boot(",
              "net_addr_register(", "net_service_register(")
    page = _fn_body(_code(NET_RT), "net_service_page")
    _in_order(page, "shm_create(1)", "CAP_RIGHT_PUBLISH", "shm_map(", "DRV_RING_BASE")
    boot = _fn_body(_code(NET_RT), "net_service_boot")
    assert "seat_rx_read = 0" in boot and "seat_tx_write = 0" in boot
    replace = _fn_body(_code(NET_RT), "net_frame_replace")
    _in_order(replace, "shm_create(", "shm_map(service_pid", "EVENT_ATTACH", "net_frame_register(")


@pytest.mark.unit
def test_the_replacement_frame_object_is_a_whole_frame_region():
    body = _fn_body(_code(NET_RT), "net_service_install")
    assert "FRAME_REGION_SIZE / PAGE_SIZE" in body


@pytest.mark.unit
def test_the_first_netd_uses_the_same_setup_and_arms_the_restart_after_the_handoff():
    grant = _fn_body(_code(RING1), "netd_grant_to")
    _in_order(grant, "cap_kernel_grant(", "net_service_page(", "net_service_boot(")
    handoff = _fn_body(_code(RING1), "net_seat_handoff")
    _in_order(handoff, "ring_seat_handoff(", "seat -> netd pid ", "net_restart_arm(", "net_handoff_done()")


@pytest.mark.unit
def test_kernel_spawned_netd_leaves_no_zombie():
    """Nobody waits for netd: its exit frees its slot (MAX_PROCS is 8, and
    four deaths a boot would otherwise hold four)."""
    assert "proc_detach(" in _fn_body(_code(RING1), "net_seat_handoff")
    assert "proc_detach(" in _fn_body(_code(PROCESS), "netd_restart")
    body = _fn_body(_code(PROC_TABLE), "proc_detach")
    assert "detached = 1" in body and "parent = -1" in body


@pytest.mark.unit
def test_the_driver_logs_the_detach_and_the_new_attach():
    attach = _fn_body(_code(DRIVER), "attach")
    ok = attach.split("Ok(va) =>")[1].split("Err(")[0]
    assert "SpscProducer.new(" in ok and "SpscConsumer.new(" in ok
    assert "[virtio-net] ATTACH: frame object mapped, both indexes at 0" in DRIVER.read_text()
    assert "[virtio-net] PEER_CLOSE: frame object detached" in DRIVER.read_text()


@pytest.mark.unit
def test_the_restart_test_is_a_boot_option_run_before_init():
    assert re.search(r"^pub const HARLAND_BOOT_FLAG_NETD_RESTART: u32 = 16$", _code(HANDOFF), re.M)
    assert "\\\\harland\\\\netd-restart" in LOADER.read_text()
    tail = _fn_body(_code(MAIN), "kernel_tail")
    _in_order(tail, "net_seat_handoff()", "net_netd_restart_test(boot_option(HARLAND_BOOT_FLAG_NETD_RESTART))",
              "run_init()")


@pytest.mark.unit
def test_the_restart_test_kills_after_each_lease_and_checks_nodev():
    body = _fn_body(_code(RING1), "net_netd_restart_test")
    _in_order(body, "if not enabled", "net_restart_armed()", "while round <= NETD_RESTARTS",
              "net_addr_configured()", "process_mark_exit(", "net_service_pid() != pid",
              "net_addr_snapshot()", "NETD_BUDGET_SETTLE_US", "net_addr_snapshot()")
