"""ENA signals through MSI-X; admin and RX waits sleep on it (AGAST #4581).

#3631 put the virtio waits on MSI-X; ENA still polled. drivers/ena/device.ritz
created every I/O CQ with ``msix_vector = 0`` and never enabled MSI-X on the
function, so the admin CQ / AENQ (which ENA signals on MSI-X entry 0, the
"management" vector) and the I/O CQs had no vector, and an admin command
spun on its completion until the TSC deadline. Now:

  * ena_init enables MSI-X on the ENA function (drivers/msix.ritz) with one
    IDT vector on entry 0 for admin + AENQ, unmasks the admin interrupt
    (ENA_REGS_INTR_MASK = 0), and one entry per I/O CQ: TX on entry 1, RX on
    entry 2, each named as the CQ's msix_vector in its CreateCQ;
  * ena_admin_wait_completion, with IF=1, sleeps on the management vector
    between checks of the admin CQ (drivers/irq_wait.ritz); with IF=0 (early
    boot) it polls and never hlts;
  * ena_wait_rx (reached by netdev_wait_rx) unmasks the RX CQ's interrupt
    and sleeps on its vector until a frame arrives.
Neither wait parks the process: the driver's queues have no lock across a
wait.

The host-compiled test builds the real driver and irq_wait.ritz against the
fake ENA of test_harland_ena_tx_buffers.py. In "irq-only" mode the fake
answers an admin doorbell, or delivers an RX frame, only while the CPU sleeps
in sti_hlt and only with the matching interrupt unmasked, so a driver that
spins, or forgets to unmask, times out. Exit codes name the failed claim.

QEMU has no ENA model: this test and the source ratchet below are the only
regular checks. The real one is the EC2 Nitro acceptance boot (#1851).
"""

import re

import pytest
from test_harland_ena_tx_buffers import KERNEL_SRC, _run

DEVICE = KERNEL_SRC / "drivers" / "ena" / "device.ritz"
NETDEV = KERNEL_SRC / "drivers" / "netdev.ritz"

MSIX_CHECKS = {
    1: "ena_init failed against the emulated device",
    2: "the ENA function did not get MSI-X",
    3: "MSI-X entry 0 (admin + AENQ) was not programmed with the management vector",
    4: "the admin interrupt was left masked (ENA_REGS_INTR_MASK != 0 after MSI-X on)",
    5: "the TX CQ was not created on MSI-X entry 1",
    6: "the RX CQ was not created on MSI-X entry 2",
    7: "the I/O CQ entries were not programmed with their own vectors",
    10: "with IF=1 an admin command answered by interrupt failed: the wait "
    "spun on the admin CQ instead of sleeping on the management vector",
    11: "the interrupt-driven admin command never slept in sti;hlt",
    12: "the management vector delivered no interrupt",
    13: "the admin wait parked the process",
    20: "with IF=0 an admin command slept in sti;hlt (boot code must poll)",
    21: "with IF=0 an admin command whose reply needs an interrupt did not "
    "time out without sleeping: boot code slept on the management vector",
    30: "ena_wait_rx did not wait with MSI-X on and IF=1",
    31: "the frame the RX interrupt announced was not received",
    32: "ena_wait_rx never slept in sti;hlt",
    33: "the RX CQ's vector delivered no interrupt (was its interrupt unmasked?)",
    34: "the RX wait parked the process",
    35: "ena_wait_rx slept with a frame already waiting",
    36: "the waiting frame was not received",
    37: "with IF=0 ena_wait_rx waited, or slept in sti;hlt",
}

MSIX_PROGRAM = """\
import drivers.ena.device {
    EnaDevice, ena_init, ena_get_device, ena_admin_exec, ena_poll, ena_wait_rx,
    ena_msix_enabled, ena_msix_vector
}
import drivers.ena.admin {
    EnaAdminAqEntry, EnaAdminAcqEntry, EnaAdminGetFeatureCmd,
    ENA_ADMIN_GET_FEATURE, ENA_ADMIN_MAX_QUEUES_NUM
}
import fakeena {
    fake_msix_present, fake_msix_entry_vector, fake_msix_count, fake_cq_msix_vector,
    fake_admin_intr_mask, fake_admin_irq_only, fake_rx_on_irq, post_rx_complete
}
import io { fake_cpu_set_if, fake_cpu_halts, fake_waitq_parks }

var g_cmd: EnaAdminGetFeatureCmd
var g_out: [64]u8

fn build_get_max_queues() -> *EnaAdminAqEntry
    var i: u64 = 0
    while i < 64
        *((@g_cmd as u64 + i) as *u8) = 0
        i = i + 1
    g_cmd.common_desc.opcode = ENA_ADMIN_GET_FEATURE
    g_cmd.feature_id = ENA_ADMIN_MAX_QUEUES_NUM
    @g_cmd as *EnaAdminAqEntry

fn main() -> i32
    fake_msix_present(true)
    if ena_init() != 0
        return 1
    let dev: *EnaDevice = ena_get_device()
    let none: **EnaAdminAcqEntry = 0 as **EnaAdminAcqEntry

    # Setup: entry 0 for admin + AENQ, unmasked; one entry per I/O CQ.
    if not ena_msix_enabled()
        return 2
    let mgmt: u8 = fake_msix_entry_vector(0)
    if mgmt == 0 or mgmt != ena_msix_vector(0)
        return 3
    if fake_admin_intr_mask() != 0
        return 4
    if fake_cq_msix_vector(0) != 1
        return 5
    if fake_cq_msix_vector(1) != 2
        return 6
    let txv: u8 = fake_msix_entry_vector(1)
    let rxv: u8 = fake_msix_entry_vector(2)
    if txv == 0 or rxv == 0 or txv == mgmt or rxv == mgmt or txv == rxv
        return 7
    if rxv != ena_msix_vector(2)
        return 7

    # Admin command with IF=1, answered only by interrupt: the wait sleeps.
    fake_cpu_set_if(true)
    fake_admin_irq_only(true)
    var halts: u64 = fake_cpu_halts()
    if ena_admin_exec(dev, build_get_max_queues(), none) != 0
        return 10
    if fake_cpu_halts() == halts
        return 11
    if fake_msix_count(mgmt) == 0
        return 12
    if fake_waitq_parks() != 0
        return 13

    # IF=0 (boot): the admin wait polls; the device answers a doorbell at once.
    fake_admin_irq_only(false)
    fake_cpu_set_if(false)
    halts = fake_cpu_halts()
    if ena_admin_exec(dev, build_get_max_queues(), none) != 0
        return 20
    if fake_cpu_halts() != halts
        return 20
    # ... even when the reply would come only by interrupt: it times out.
    fake_admin_irq_only(true)
    if ena_admin_exec(dev, build_get_max_queues(), none) != -1
        return 21
    if fake_cpu_halts() != halts
        return 21
    fake_admin_irq_only(false)

    # RX wait: the frame arrives by interrupt, once the RX CQ is unmasked.
    fake_cpu_set_if(true)
    fake_rx_on_irq(3, 8)
    halts = fake_cpu_halts()
    if not ena_wait_rx()
        return 30
    if ena_poll(@g_out[0], 64) != 8
        return 31
    if fake_cpu_halts() == halts
        return 32
    if fake_msix_count(rxv) == 0
        return 33
    if fake_waitq_parks() != 0
        return 34

    # A frame already waiting: return at once, without sleeping.
    post_rx_complete(4, 8)
    halts = fake_cpu_halts()
    if not ena_wait_rx()
        return 35
    if fake_cpu_halts() != halts
        return 35
    if ena_poll(@g_out[0], 64) != 8
        return 36

    # IF=0: no wait at all; the caller delays instead.
    fake_cpu_set_if(false)
    halts = fake_cpu_halts()
    if ena_wait_rx()
        return 37
    if fake_cpu_halts() != halts
        return 37
    0
"""

POLL_CHECKS = {
    1: "ena_init failed against an emulated device without MSI-X",
    2: "a device without MSI-X reports it enabled",
    3: "a device without MSI-X has a management vector",
    4: "without MSI-X an I/O CQ was created with a vector other than 0",
    5: "without MSI-X an admin command with IF=1 failed (it must poll)",
    6: "without MSI-X an admin command slept in sti;hlt",
    7: "without MSI-X ena_wait_rx waited (the caller must delay instead)",
}

POLL_PROGRAM = """\
import drivers.ena.device {
    EnaDevice, ena_init, ena_get_device, ena_admin_exec, ena_wait_rx,
    ena_msix_enabled, ena_msix_vector
}
import drivers.ena.admin {
    EnaAdminAqEntry, EnaAdminAcqEntry, EnaAdminGetFeatureCmd,
    ENA_ADMIN_GET_FEATURE, ENA_ADMIN_MAX_QUEUES_NUM
}
import fakeena { fake_cq_msix_vector }
import io { fake_cpu_set_if, fake_cpu_halts }

var g_cmd: EnaAdminGetFeatureCmd

fn main() -> i32
    if ena_init() != 0
        return 1
    if ena_msix_enabled()
        return 2
    if ena_msix_vector(0) != 0
        return 3
    if fake_cq_msix_vector(0) != 0 or fake_cq_msix_vector(1) != 0
        return 4
    fake_cpu_set_if(true)
    var i: u64 = 0
    while i < 64
        *((@g_cmd as u64 + i) as *u8) = 0
        i = i + 1
    g_cmd.common_desc.opcode = ENA_ADMIN_GET_FEATURE
    g_cmd.feature_id = ENA_ADMIN_MAX_QUEUES_NUM
    if ena_admin_exec(ena_get_device(), @g_cmd as *EnaAdminAqEntry, 0 as **EnaAdminAcqEntry) != 0
        return 5
    if fake_cpu_halts() != 0
        return 6
    if ena_wait_rx()
        return 7
    0
"""


@pytest.mark.integration
def test_ena_msix_vectors_and_interrupt_driven_waits(tmp_path):
    rc = _run(tmp_path, MSIX_PROGRAM)
    assert rc == 0, f"check {rc}: {MSIX_CHECKS.get(rc, 'crashed or unknown exit code')}"


@pytest.mark.integration
def test_ena_without_msix_still_polls(tmp_path):
    rc = _run(tmp_path, POLL_PROGRAM)
    assert rc == 0, f"check {rc}: {POLL_CHECKS.get(rc, 'crashed or unknown exit code')}"


# --- source ratchet -------------------------------------------------------------

FN_HEADER = re.compile(r"^(?:pub )?fn (\w+)\(", re.MULTILINE)


def _body(text, name):
    """Body of fn `name`, comments stripped."""
    headers = list(FN_HEADER.finditer(text))
    for i, h in enumerate(headers):
        if h.group(1) == name:
            end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
            body = text[h.end() : end]
            return "\n".join(line.split("#", 1)[0] for line in body.splitlines())
    raise AssertionError(f"fn {name} not found")


@pytest.mark.unit
def test_ena_create_cq_names_a_real_vector():
    body = _body(DEVICE.read_text(), "ena_create_cq")
    assert not re.search(r"msix_vector\s*=\s*0\b", body), (
        "ena_create_cq hard-codes msix_vector = 0: an I/O CQ must name its own "
        "MSI-X entry (AGAST #4581)"
    )


@pytest.mark.unit
@pytest.mark.parametrize("fn", ["ena_admin_wait_completion", "ena_wait_rx"])
def test_ena_waits_sleep_on_their_vector_without_parking(fn):
    body = _body(DEVICE.read_text(), fn)
    calls = re.findall(r"\birq_wait_vector\(([^)]*)\)", body)
    assert calls, f"{fn} does not sleep via irq_wait_vector (AGAST #4581)"
    for args in calls:
        assert args.split(",")[4].strip() == "false", (
            f"{fn} may park the process: the ENA queues have no lock across a wait"
        )


@pytest.mark.unit
def test_netdev_wait_rx_reaches_ena():
    body = _body(NETDEV.read_text(), "netdev_wait_rx")
    assert re.search(r"NETDEV_TYPE_ENA[\s\S]*\bena_wait_rx\(\)", body), (
        "netdev_wait_rx does not dispatch an ENA device to ena_wait_rx (AGAST #4581)"
    )
