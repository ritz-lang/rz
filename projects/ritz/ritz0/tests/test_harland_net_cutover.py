"""The virtio-net cutover: the ring-1 driver owns the NIC's queues on every
boot that translates DMA (AGAST #4735, RING1_DRIVER.md sections 8-9, ring
plan T29).

D7: the boot picks the owner, not a marker file. A boot with a virtio-net
and a translated DMA domain probes the NIC in the kernel (isolation, MSI-X
at the BSP, the windows recorded; no virtqueue, no DRIVER_OK), makes pid 1
(process_create_init), spawns /bin/virtio-net on pid 1's kernel stack,
yields to it until it parks with generation 2 published, and starts the
scheduler once, all before postinit_diagnostics and run_init. netdev_init
then skips virtio_net_init; net_stack_init finds the ring through the link
snapshot. An untranslated boot keeps virtio_net_init and spawns nothing.

The behaviour is tools/test_msix_boot.sh's vtd run (its verdicts are
host-tested in projects/ritz/tools/test_ci_msix_boot.py). These checks pin
the order and the guards that run can't observe.
"""

import re
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).resolve().parents[1]
HARLAND = RITZ0_DIR.parent.parent / "harland"
KERNEL_SRC = HARLAND / "kernel" / "src"
MAIN = KERNEL_SRC / "main.ritz"
RING1 = KERNEL_SRC / "net" / "ring1.ritz"
STACK = KERNEL_SRC / "net" / "stack.ritz"
NETDEV = KERNEL_SRC / "drivers" / "netdev.ritz"
VNET = KERNEL_SRC / "drivers" / "virtio" / "net.ritz"
PROCESS = KERNEL_SRC / "syscall" / "runtime" / "process.ritz"
POSTINIT = KERNEL_SRC / "postinit.ritz"
NVME = KERNEL_SRC / "drivers" / "nvme" / "nvme.ritz"
TABLE = KERNEL_SRC / "proc" / "table.ritz"
ERRNO = KERNEL_SRC / "syscall" / "errno.ritz"


def _code(path):
    return "\n".join(l.split("#", 1)[0].rstrip() for l in path.read_text().splitlines())


def _fn_body(src, name):
    m = re.search(rf"^(?:pub )?fn {name}\(.*?(?=^\S)", src + "\nEND", re.M | re.S)
    assert m, f"no fn {name}"
    return m.group(0)


@pytest.mark.unit
def test_netdev_init_leaves_a_ring1_nic_alone():
    """virtio_net_init runs only when the probe did not find the NIC on a
    translating boot: one owner per boot, never both."""
    body = _fn_body(_code(NETDEV), "netdev_init")
    guard = body.index("if not virtio_net_ring1_boot()")
    assert guard < body.index("virtio_net_init()")
    assert body.count("virtio_net_init()") == 1
    # ENA is still probed either way
    assert "ena_init()" in body


@pytest.mark.unit
def test_the_ring1_boot_is_chosen_by_translation_not_a_marker():
    probe = _fn_body(_code(VNET), "virtio_net_ring1_probe")
    assert "dma_translation_on()" in probe
    assert "net-selftest" not in probe and "boot_option" not in probe
    # it is the ring-1 boot from the moment the NIC is found on it
    assert probe.index("virtio_net_ring1 = true") < probe.index("vio_init_device_isolated(")


@pytest.mark.unit
def test_the_probe_arms_nothing_the_driver_owns():
    """The kernel isolates the NIC and programs MSI-X; it allocates no queue
    for the device and never sets DRIVER_OK (section 8, last paragraph)."""
    probe = _fn_body(_code(VNET), "virtio_net_ring1_probe")
    for forbidden in ("vio_device_ready(", "virtio_net_start_queue(", "virtq_add_buf(", "nic_pool_new("):
        assert forbidden not in probe, forbidden
    iso = probe.index("virtio_net_isolate(")
    assert iso < probe.index("net_ring1_allowed()") < probe.index("virtio_net_ring1_msix(")
    # legacy-only devices are not claimed
    assert probe.index("VIO_TRANSPORT_MMIO") < iso


@pytest.mark.unit
def test_msix_is_refused_unless_every_entry_is_routed_to_the_bsp():
    msix = _fn_body(_code(VNET), "virtio_net_ring1_msix")
    assert "let bsp: u32 = lapic_id()" in msix
    assert "msix_set_entry_to(@virtio_net_msix, e, vector, bsp) != 0 or msix_entry_dest(@virtio_net_msix, e) != bsp" in msix
    assert "return None" in msix and "return 0" not in msix


@pytest.mark.unit
def test_net_stack_init_prefers_a_netdevice_then_the_published_ring():
    body = _fn_body(_code(STACK), "net_stack_init")
    dev = body.index("if dev_count > 0")
    ring = body.index("if ring_driver_published()")
    assert dev < ring < body.index('"[net] No network devices found!')
    dev_branch = body[dev:ring]
    assert "net_via_ring = false" in dev_branch
    ring_branch = body[ring:]
    assert "net_via_ring = true" in ring_branch and "net_device = 0 as *NetDevice" in ring_branch
    assert ring_branch.index("return 0") < ring_branch.index("return -1")


@pytest.mark.unit
def test_kernel_main_runs_steps_1_to_4_before_the_diagnostics_and_init():
    main = _fn_body(_code(MAIN), "kernel_main")
    assert main.index("boot_process_tests()") < main.index("net_ring1_boot(kernel_tail)")
    assert "postinit_diagnostics(" not in main and "run_init()" not in main
    tail = _fn_body(_code(MAIN), "kernel_tail")
    assert tail.index("net_ring1_spawn()") < tail.index("postinit_diagnostics(") < tail.index("run_init()")


@pytest.mark.unit
def test_boot_runs_the_tail_on_pid_1s_stack_only_when_prepare_made_pid_1():
    """Step 1, then the tail on pid 1's kernel stack: the driver's page
    table lacks the boot stack. Without pid 1 the tail runs where it is."""
    body = _fn_body(_code(RING1), "net_ring1_boot")
    prep = body.index("net_ring1_prepare()")
    switch = body.index("kstack_call(tail as u64, kstack_top(proc_current_slot()))")
    assert prep < switch < body.index("        tail()")


@pytest.mark.unit
def test_run_init_keeps_an_existing_pid_1_and_the_driver():
    """No table reset (it would free the driver's slot) and no second
    sched_start when pid 1 already exists."""
    body = _fn_body(_code(MAIN), "run_init")
    guard = body.index("if proc_current() == 0 as *Proc")
    assert guard < body.index("process_enter_init()") < body.index("jump_to_userspace(")
    assert "proc_table_reset" not in body and "sched_start" not in body


@pytest.mark.unit
def test_prepare_makes_pid_1_only_after_the_probe_hands_the_nic_over():
    body = _fn_body(_code(RING1), "net_ring1_prepare")
    assert body.index("virtio_net_ring1_probe()") < body.index("process_create_init()")
    assert "None => return false" in body
    assert "sched_start" not in body


@pytest.mark.unit
def test_spawn_grants_before_the_driver_runs_and_starts_the_scheduler_once():
    body = _fn_body(_code(RING1), "net_ring1_spawn")
    assert "sched_is_running()" in body.split("\n", 2)[1]     # a second call does nothing
    obj = body.index("ring1_device_object(g)")
    spawn = body.index('process_spawn_program("/bin/virtio-net")')
    grant = body.index("ring1_grant_to(pid, obj, g)")
    yields = body.index("sched_yield()\n        yields = yields + 1")
    start = body.index("sched_start(proc_current_slot())")
    assert obj < spawn < grant < yields < start
    assert body.count("sched_start(") == 1


@pytest.mark.unit
def test_the_frame_object_is_the_drivers_first_mapping_and_the_record_is_written():
    body = _fn_body(_code(RING1), "ring1_grant_to")
    seat = body.index("ring_seat_open(pid)")
    for later in ("CAP_TYPE_IRQ", "shm_create(1)", "CAP_TYPE_MMIO", "driver_boot_at("):
        assert seat < body.index(later), later
    assert "CAP_RIGHT_PUBLISH" in body and "net_link_register(link_obj)" in body
    assert "boot.magic = DRIVER_BOOT_MAGIC" in body
    assert "i < DRIVER_BOOT_WINDOWS" in body


@pytest.mark.unit
def test_the_device_object_is_bound_to_the_domain_and_recorded_for_quiesce():
    body = _fn_body(_code(RING1), "ring1_device_object")
    assert body.index("irq_object_register(obj, g.vector)") < body.index("irq_object_bind_domain(obj, g.dom)")
    assert "drv_device_bind(obj, g.status_va, g.msix_table_va, MSIX_ENTRIES)" in body


@pytest.mark.unit
def test_a_kernel_spawned_program_inherits_no_capabilities():
    body = _fn_body(_code(PROCESS), "process_spawn_program")
    assert "errno_result(spawn_process(path, 0, 0, false))" in body
    assert "spawn_child_begin(parent_pid, inherit_caps)" in _fn_body(_code(PROCESS), "spawn_process")
    # sys_spawn's children still inherit
    assert "spawn_process(path, argc, argv_bytes, true)" in _fn_body(_code(PROCESS), "spawn_and_block")


@pytest.mark.unit
def test_the_tx_burst_yields_to_the_driver_after_each_group():
    body = _fn_body(_code(POSTINIT), "network_tx_burst")
    group = body.index("sent = sent + group_sent")
    after = body[group:]
    assert after.index("if ring\n            sched_yield()") < after.index("while icmp_distinct_reply_count()")
    # on the ring a poll waits for a frame (the driver runs); no fixed delay
    assert "if ring\n                burst_poll(true)\n            else\n                net_poll()\n                delay_us(50)" in after
    assert body.index("if ring\n        enable_interrupts()") < group
    assert "net_wait_rx(deadline_after_us(NET_BURST_WAIT_US))" in _fn_body(_code(POSTINIT), "burst_poll")


@pytest.mark.unit
def test_the_ring_owner_logs_its_parks_not_rx_halts():
    body = _fn_body(_code(POSTINIT), "network_dhcp_ping")
    ring = body.index("if net_on_ring()")
    assert ring < body.index("drv_irq_wait_park_count()") < body.index("else if virtio_net_msix_enabled()")
    assert "match virtio_net_ring1_vector()\n                Some(v) => klog_dec(msix_vector_count(v))" in body


@pytest.mark.unit
def test_the_nvme_idle_probe_never_parks():
    """With pid 1 made before the diagnostics, a parking wait would idle in
    sched_block, not in the hlt the probe counts."""
    body = _fn_body(_code(NVME), "nvme_irq_idle_probe")
    assert "irq_wait_vector(vec, msix_vector_count(vec), NVME_IRQ_WATCHDOG_TICKS, 1, false, @halts)" in body


@pytest.mark.unit
def test_the_driver_is_one_of_eight_procs():
    assert re.search(r"^pub const MAX_PROCS: i32 = 8$", TABLE.read_text(), re.M)


@pytest.mark.unit
def test_errno_result_takes_only_a_positive_code_for_a_value():
    """A pid is above zero: 0, or a code no Errno names, is Errno.Inval,
    never Ok, so a failed spawn cannot be taken for pid 0 (REVIEW.md A5)."""
    body = _fn_body(_code(ERRNO), "errno_result")
    assert body.index("if raw > 0\n        return Ok(raw as u64)") < body.index("match Errno.from(raw)")
    assert "None => Err(Errno.Inval)" in body
