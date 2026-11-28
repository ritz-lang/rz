"""netd's exit or fault, and its restart (AGAST #4745, #4875, ring plan T39,
harland docs/RING2_NET.md "Drivers inside netd (D9)", "Frame seat" and
"Service binary and respawn", docs/RING1_DRIVER.md "Driver death").

Under D9 netd is the NIC's driver too: its exit or fault quiesces the NIC
first (driver_quiesce: MSI-X masked, virtio status 0 read back, its DMA out
of the domain, NetInfo NoDev), then invalidates the address snapshot
(NetAddr is NoDev), retires every shm object it held (each app exchange
gets DRIVER_GONE, which wakes it), and unregisters it. It then restarts
/bin/netd at most three times per boot, 250 ms, 500 ms and 1 s after the
first three deaths, and only onto a NIC whose quiesce left it fit (reset
read back, no quarantined run): each replacement gets what the first netd
got but the seat: a new IRQ-owner record with the MSI-X entries unmasked,
the MMIO windows, a new link page (its first shared mapping, DRV_RING_BASE,
with DriverBoot naming no frame object) and a new address page as ATTACH.
The fourth death starts nothing and is logged; NetAddr stays NoDev.

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
DRIVER_RT = KERNEL_SRC / "syscall" / "runtime" / "driver.ritz"
LOADER = HARLAND / "boot" / "src" / "main.ritz"
HANDOFF = HARLAND / "boot_abi" / "src" / "handoff.ritz"


def _code(path):
    return "\n".join(l.split("#", 1)[0].rstrip() for l in path.read_text().splitlines())


def _fn_body(src, name):
    m = re.search(rf"^(?:pub )?fn {name}(?:<[^>]*>)?\(.*?(?=^\S)", src + "\nEND", re.M | re.S)
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
    _in_order(body, "driver_quiesce(", "cap_retire_held_shm(", "cap_table_free_pid(", "net_service_exited(",
              "vmm_free_pml4(my_pml4)", "(*me).pml4 = g_kernel_pml4", "netd_restart(", "proc_exit_current(")
    assert "if was_service" in body


@pytest.mark.unit
def test_the_restart_waits_out_its_backoff_then_respawns():
    body = _fn_body(_code(PROCESS), "netd_restart")
    _in_order(body, "net_service_death()", "net_restart_backoff_ms(", "budget spent",
              "netd_backoff(ms)", "net_netd_respawn()")
    # The backoff lets the other processes run (the dying context is not
    # preemptible) and sleeps when nothing else can.
    wait = _fn_body(_code(PROCESS), "netd_backoff")
    _in_order(wait, "deadline_after_us(ms * 1000)", "enable_interrupts()", "deadline_passed(",
              "sched_yield()", "sti_hlt()")


@pytest.mark.unit
def test_a_respawn_takes_no_stdio_from_the_dying_netd():
    """The restart runs as the dying netd, whose fds are already released:
    a kernel spawn must not hand the child the running process's fds 0-2
    (#4955's inherit map made every respawn BadF, so netd never came back).
    process_spawn_program passes no map; spawn_child_begin hands over stdio
    only for Some(map)."""
    for name in ("process_spawn_program", "process_spawn_program_on", "spawn_image"):
        body = _fn_body(_code(PROCESS), name)
        assert "spawn_stdio_inherit()" not in body, name
        assert re.search(r"spawn_(?:process|child_begin)\(.*\bNone\)", body), name
    begin = _fn_body(_code(PROCESS), "spawn_child_begin")
    assert "stdio: Option<SpawnStdio>" in begin
    _in_order(begin, "match stdio", "Some(map)", "fs_process_give_stdio(child_pid, map)")






@pytest.mark.unit
def test_kernel_spawned_netd_leaves_no_zombie():
    """Nobody waits for netd: its exit frees its slot (MAX_PROCS is 8, and
    four deaths a boot would otherwise hold four)."""
    assert "proc_detach(" in _fn_body(_code(RING1), "ring1_spawn_netd")
    assert "proc_detach(" in _fn_body(_code(RING1), "net_netd_respawn")
    body = _fn_body(_code(PROC_TABLE), "proc_detach")
    assert "detached = 1" in body and "parent = -1" in body



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
              "net_addr_configured_by(pid)", "process_mark_exit(", "net_service_pid() != pid",
              "net_addr_snapshot()", "NETD_BUDGET_SETTLE_US", "net_addr_snapshot()")


# AGAST #4855: pid 1 killed restart 1 between its NetPublish and its
# "[netd] configured" line. netd's loop publishes, logs the lease, then
# parks in DrvIrqWait: the kill waits for this instance's own configured
# publish and for it to park after it, so the line is out first.
NETD = HARLAND / "system" / "src" / "netd.ritz"


@pytest.mark.unit
def test_netd_logs_its_lease_after_the_publish_and_before_it_parks():
    loop = _fn_body(_code(NETD), "serve").split("while true", 1)[1]
    _in_order(loop, "net_publish(g_addr)", "log_address(svc)", "wait_once(")



@pytest.mark.unit
def test_the_address_snapshot_remembers_its_publisher():
    publish = _fn_body(_code(NET_RT), "net_publish_for")
    _in_order(publish, "addr_publish_page(page)", "addr_publisher = pid")
    exited = _fn_body(_code(NET_RT), "net_service_exited")
    _in_order(exited, "disable_interrupts()", "addr_generation = LINK_SEQ_UNPUBLISHED",
              "addr_publisher = 0", "enable_interrupts()")
    by = _fn_body(_code(NET_RT), "net_addr_configured_by")
    assert "addr_publisher == pid" in by and "net_addr_configured()" in by


@pytest.mark.unit
def test_the_kill_waits_for_this_netds_lease_and_its_park():
    body = _fn_body(_code(RING1), "net_netd_restart_test")
    rnd = body.split("while round <= NETD_RESTARTS", 1)[1]
    _in_order(rnd, "pid = net_service_pid()", "net_addr_configured_by(pid)", "ring1_parked(pid as u64)",
              "[net-restart] killing netd pid", "process_mark_exit(pid as u64)")
    # Not any lease: the bare check would take a snapshot whatever published it.
    assert "net_addr_configured()" not in rnd


# D9 (#4875): what netd's respawn, the handoff and netd's drain must call, in
# order, and must not. One row per function: (why, file, fn or None for the
# whole file, calls in order, calls absent).
D9_RESTART_ROWS = (
    ("the NIC's fitness, then the spawn; the MSI-X entries unmasked and the device grants "
     "(with_seat false: no frame object); a replacement that could not be set up exits "
     "unregistered; the address page as ATTACH before the registration",
     RING1, "net_netd_respawn",
     ("drv_device_fit(ring1_obj)", 'process_spawn_program("/bin/netd")', "proc_detach(pid)",
      "drv_device_unmask(ring1_obj)", "ring1_grant_to(pid, ring1_obj, ring1_grant, false)",
      "process_mark_exit(pid)", "netd_service_page(pid)", "net_service_register(pid as u32)"),
     ("ring_seat_open", "net_frame_replace")),
    ("fitness is sticky: a quiesce that did not read status 0 back clears it",
     DRIVER_RT, "driver_quiesce", ("drv_devices[i].fit = drv_devices[i].fit and clean",), ()),
    ("a device is fit only with its reset read back and no run on dma_quarantine",
     DRIVER_RT, "quiesce_device", ("msix_mask_entries(", "reset_ok and quarantined == 0"), ()),
    ("the respawn asks the device record", DRIVER_RT, "drv_device_fit", ("drv_devices[slot].fit",), ()),
    ("a respawn unmasks what the quiesce masked", DRIVER_RT, "drv_device_unmask", ("msix_unmask_entries(",), ()),
    ("netd's death no longer disarms the restart: the driver's death is netd's",
     NET_RT, "net_driver_quiesced", (), ("net_restart",)),
    ("the restart is armed by a flag", NET_RT, "net_service_death", ("if not net_restart_on",), ()),
    ("the address page is granted, not mapped", NET_RT, "net_service_page",
     ("shm_create(1)", "CAP_RIGHT_PUBLISH"), ("shm_map(",)),
    ("a fresh ServiceBoot for each netd", NET_RT, "net_service_boot",
     ("seat_rx_read = 0", "seat_tx_write = 0"), ()),
    ("its handle is netd's first ATTACH", NET_RT, "net_service_attach_page",
     ("disable_interrupts()", "waitset_inbox_post(", "EVENT_ATTACH", "enable_interrupts()"), ()),
    ("the page is made, written and registered before it is attached", RING1, "netd_service_page",
     ("net_service_page(", "net_service_boot(", "net_addr_register(", "net_service_attach_page("), ()),
    ("no install path is left", NET_RT, None, (), ("net_service_install",)),
    ("the handoff spawns nothing and arms the restart after it", RING1, "net_seat_handoff",
     ("netd_service_page(pid)", "net_service_register(", "net_handoff_arm(", "ring_seat_handoff(",
      "seat -> netd pid ", "net_restart_arm()", "net_handoff_done()"),
     ("process_spawn_program",)),
    ("the handoff is the frame object's last use: netd drains it through its stack and drops it",
     HARLAND / "system" / "src" / "netd.ritz", "take_over",
     ("net_publish(g_addr)", "seat_hand_over<N>(", "cap_revoke(g_seat.handle)", "svc.set_link("), ()),
)


@pytest.mark.unit
def test_d9_respawn_handoff_and_drain_rows():
    for why, path, fn, ordered, absent in D9_RESTART_ROWS:
        body = _code(path) if fn is None else _fn_body(_code(path), fn)
        try:
            _in_order(body, *ordered)
        except AssertionError as e:
            raise AssertionError(f"{fn}: {why}: {e}") from None
        for a in absent:
            assert a not in body, f"{fn}: {why}: {a!r} present"
