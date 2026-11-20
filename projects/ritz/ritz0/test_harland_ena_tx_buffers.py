"""Every ENA I/O descriptor names a buffer inside its own arena (AGAST #4334).

drivers/ena/device.ritz kept eight 2 KB buffers for the TX arena
(``ENA_TX_BUFFER_COUNT = 8``) but computed a send's buffer from the 256-entry
TX ring's head:

    buf_idx = tx_sq.head                       # 0..255
    buf_addr = ena_tx_buffers + buf_idx * 2048

On Nitro the boot reached the TX burst (tools/postinit.ritz NET_TX_BURST=300,
four frames in flight per group), and the 9th send wrote its Ethernet frame
past the 16 KB arena. The frames spilled through the kernel's .bss: the kernel
log ring buffer held raw IPv4 bytes, icmp_seq/icmp_reply_seen (which sit 92
buffers along in the same build) produced "[icmp] Reply ... seq=21006", and at
head 103 the packet copy landed on the syscall stack's guard page and the
kernel panicked with a #PF inside ena_send.

The invariant: a descriptor the driver hands a device must name a buffer the
driver owns for that queue. The test compiles the real driver with stubs for
its hardware imports and a fake ENA admin queue in place of the NIC, then:

  * asks, for every one of the 256 TX ring slots, whether its buffer lies in
    the TX arena (today slots 8..255 do not);
  * checks an RX completion req_id that names no buffer is rejected rather
    than used as an out-of-range index;
  * sends 300 frames and asks the driver to check every submitted descriptor;
  * delivers one RX completion the emulated device posts.

Exit codes name the failed claim (CHECKS).
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link
from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ0_DIR = Path(__file__).resolve().parent
RITZ_ROOT = RITZ0_DIR.parent
KERNEL_SRC = RITZ_ROOT.parent / "harland" / "kernel" / "src"

# --- stand-ins for the driver's hardware imports ------------------------------

# device.ritz only prints; nothing here needs to reach a UART.
SERIAL_STUB = """\
pub struct StrView
    ptr: *u8
    len: i64

pub fn prints(s: StrView) -> i32
    return 0

pub fn serial_print_dec(value: u64) -> i32
    return 0

pub fn serial_print_hex(value: u64) -> i32
    return 0

pub fn serial_print_hex8(value: u8) -> i32
    return 0

pub fn serial_write_byte(value: u8) -> i32
    return 0
"""

# Barriers become the fake device's clock: every MMIO write is followed by
# memory_barrier(), so the emulated ENA gets to answer a doorbell.
IO_STUB = """\
import fakeena { on_barrier }

pub fn cpu_pause() -> i32
    return 0

pub fn memory_barrier() -> i32
    on_barrier()
    return 0

pub fn read_barrier() -> i32
    return 0

pub fn write_barrier() -> i32
    return 0
"""

# Deadlines advance one unit per poll: every wait in the driver terminates,
# and a device that answers on the first poll is seen at once.
TSC_STUB = """\
var g_now: u64 = 0

pub fn delay_us(us: u64)
    return

pub fn deadline_after_us(us: u64) -> u64
    return g_now + 1000

pub fn deadline_passed(deadline: u64) -> bool
    g_now = g_now + 1
    return g_now >= deadline
"""

# BAR0 points at the fake device's register file.
PCI_STUB = """\
import fakeena { mmio_base }

pub struct PciDevice
    bus: u8
    device: u8
    function: u8
    vendor_id: u16
    device_id: u16
    class_code: u8
    subclass: u8
    prog_if: u8
    revision: u8
    header_type: u8
    interrupt_line: u8
    interrupt_pin: u8
    bar: [6]u64
    bar_size: [6]u64
    bar_is_io: [6]u8
    bar_is_64bit: [6]u8

var g_dev: PciDevice

pub fn pci_find_ena() -> *PciDevice
    g_dev.bus = 0
    g_dev.device = 6
    g_dev.function = 0
    g_dev.bar[0] = mmio_base()
    g_dev.bar_size[0] = 4096
    g_dev.bar_is_io[0] = 0
    return @g_dev

pub fn pci_enable_bus_master(dev: *PciDevice)
    return

pub fn pci_enable_memory(dev: *PciDevice)
    return
"""

# Page-aligned pages out of .bss, handed out consecutively.
PMM_STUB = """\
pub const PAGE_SIZE: u64 = 4096

var g_mem: [65536]u8
var g_next: u64 = 0

pub fn pmm_alloc_page() -> u64
    let base: u64 = @g_mem[0] as u64
    if g_next == 0
        g_next = (base + 4095) & (0xFFFFFFFFFFFFFFFF ^ 4095)
    if g_next + 4096 > base + 65536
        return 0
    let p: u64 = g_next
    g_next = g_next + 4096
    return p

pub fn pmm_free_page(addr: u64) -> i32
    return 0
"""

# Identity mapping, as on the kernel's low-memory direct map: a page's host
# address is the address handed to the device. The driver reaches MMIO and
# queue pages through the kernel half (AGAST #1878); here both windows are
# the identity, so the emulated device sees the addresses it expects.
VMM_STUB = """\
pub const PTE_WRITABLE: u64 = 2

pub fn vmm_virt_to_phys(vaddr: u64) -> u64
    return vaddr

pub fn vmm_map_page(virt: u64, phys: u64, flags: u64) -> i32
    return 0

pub fn vmm_map_mmio(paddr: u64, size: u64) -> u64
    return paddr

pub fn phys_to_virt(paddr: u64) -> u64
    return paddr
"""

# The emulated ENA. Its register file is BAR0; a doorbell write is followed by
# the io stub's memory_barrier, which is where it answers the admin command the
# driver just copied into the AQ. Responses are the subset ena_init asks for:
# device attributes, max queues, AENQ config, and the CQ/SQ create replies.
# It also models DEV_STS across a reset, and posts RX completions on request.
FAKEENA_STUB = """\
import drivers.ena.regs {
    ENA_REGS_AQ_BASE_LO_OFF, ENA_REGS_AQ_BASE_HI_OFF, ENA_REGS_AQ_CAPS_OFF,
    ENA_REGS_ACQ_BASE_LO_OFF, ENA_REGS_ACQ_BASE_HI_OFF, ENA_REGS_AQ_DB_OFF,
    ENA_REGS_DEV_CTL_OFF, ENA_REGS_DEV_STS_OFF,
    ENA_REGS_DEV_CTL_DEV_RESET_MASK, ENA_REGS_DEV_STS_READY_MASK,
    ENA_REGS_DEV_STS_RESET_IN_PROGRESS_MASK
}
import drivers.ena.admin {
    ENA_ADMIN_GET_FEATURE, ENA_ADMIN_SET_FEATURE, ENA_ADMIN_CREATE_CQ,
    ENA_ADMIN_CREATE_SQ, ENA_ADMIN_DEVICE_ATTRIBUTES, ENA_ADMIN_MAX_QUEUES_NUM,
    ENA_ADMIN_AENQ_CONFIG
}

var g_mmio: [4096]u8
var g_last_db: u32 = 0
var g_cq_idx: u32 = 0       # the driver's ACQ head, in lockstep
var g_cq_phase: u8 = 1
var g_next_cq: u16 = 0
var g_next_sq: u16 = 0
var g_rx_cq_base: u64 = 0
var g_rx_cq_depth: u16 = 0
var g_rx_cq_prod: u32 = 0
var g_rx_cq_phase: u8 = 1
# TX completions (#1851): one 8-byte entry per TX doorbell, in order, as the
# device writes them. The driver must reap them to reuse ring slots.
var g_tx_cq_base: u64 = 0
var g_tx_cq_depth: u16 = 0
var g_tx_cq_prod: u32 = 0
var g_tx_cq_phase: u8 = 1
var g_tx_db_off: u32 = 0
var g_last_tx_db: u32 = 0

pub fn mmio_base() -> u64
    return @g_mmio[0] as u64

fn rd32(off: u32) -> u32
    return *((mmio_base() + off as u64) as *u32)

fn wr32(off: u32, value: u32)
    *((mmio_base() + off as u64) as *u32) = value

fn rd_addr(lo_off: u32, hi_off: u32) -> u64
    let lo: u64 = rd32(lo_off) as u64
    let hi: u64 = rd32(hi_off) as u64
    return ((hi & 0xFFFFFFFF) << 32) | lo

fn zero(dst: u64, n: u32)
    var i: u32 = 0
    while i < n
        *((dst + i as u64) as *u8) = 0
        i = i + 1

# Answer the command the driver has just pushed and doorbelled.
fn service()
    let sq: u64 = rd_addr(ENA_REGS_AQ_BASE_LO_OFF, ENA_REGS_AQ_BASE_HI_OFF)
    let cq: u64 = rd_addr(ENA_REGS_ACQ_BASE_LO_OFF, ENA_REGS_ACQ_BASE_HI_OFF)
    let depth: u32 = rd32(ENA_REGS_AQ_CAPS_OFF) & 0xFFFF
    if sq == 0 or depth == 0
        return
    let db: u32 = rd32(ENA_REGS_AQ_DB_OFF)
    let idx: u32 = (db + depth - 1) % depth
    let cmd: u64 = sq + (idx as u64) * 64
    let opcode: u8 = *((cmd + 2) as *u8)
    let cmd_id: u16 = *(cmd as *u16)
    let cqe: u64 = cq + (g_cq_idx as u64) * 64
    zero(cqe, 64)
    *(cqe as *u16) = cmd_id
    *((cqe + 2) as *u8) = 0              # ENA_ADMIN_SUCCESS
    *((cqe + 3) as *u8) = g_cq_phase
    *((cqe + 4) as *u16) = 0
    *((cqe + 6) as *u16) = idx as u16

    if opcode == ENA_ADMIN_GET_FEATURE
        let fid: u8 = *((cmd + 17) as *u8)
        if fid == ENA_ADMIN_DEVICE_ATTRIBUTES
            *((cqe + 32) as *u8) = 0x02
            *((cqe + 33) as *u8) = 0x00
            *((cqe + 34) as *u8) = 0x00
            *((cqe + 35) as *u8) = 0x00
            *((cqe + 36) as *u8) = 0x00
            *((cqe + 37) as *u8) = 0x01
            *((cqe + 40) as *u32) = 9000
        else if fid == ENA_ADMIN_MAX_QUEUES_NUM
            *((cqe + 8) as *u32) = 8
            *((cqe + 12) as *u32) = 256
            *((cqe + 16) as *u32) = 8
            *((cqe + 20) as *u32) = 256
        else if fid == ENA_ADMIN_AENQ_CONFIG
            *((cqe + 8) as *u32) = 0x1F
    else if opcode == ENA_ADMIN_CREATE_CQ
        let caps2: u8 = *((cmd + 5) as *u8)
        let cq_depth: u16 = *((cmd + 6) as *u16)
        # cq_ba_lo at offset 12, cq_ba_hi at 16
        let lo: u64 = *((cmd + 12) as *u32) as u64
        let hi: u64 = *((cmd + 16) as *u16) as u64
        let ba: u64 = (hi << 32) | lo
        let hw: u16 = g_next_cq
        g_next_cq = g_next_cq + 1
        *((cqe + 8) as *u16) = hw
        *((cqe + 10) as *u16) = cq_depth
        *((cqe + 12) as *u32) = 0
        *((cqe + 16) as *u32) = 0x400 + hw as u32
        *((cqe + 20) as *u32) = 0x500 + hw as u32
        if (caps2 & 0x1F) == 4
            g_rx_cq_base = ba
            g_rx_cq_depth = cq_depth
        else if (caps2 & 0x1F) == 2
            g_tx_cq_base = ba
            g_tx_cq_depth = cq_depth
    else if opcode == ENA_ADMIN_CREATE_SQ
        let identity: u8 = *((cmd + 4) as *u8)
        let direction: u8 = (identity >> 5) & 7
        let hw: u16 = g_next_sq
        g_next_sq = g_next_sq + 1
        *((cqe + 8) as *u16) = hw
        *((cqe + 10) as *u16) = 0
        if direction == 1
            *((cqe + 12) as *u32) = 0x100
            g_tx_db_off = 0x100
        else
            *((cqe + 12) as *u32) = 0x200
        *((cqe + 16) as *u32) = 0
        *((cqe + 20) as *u32) = 0

    g_cq_idx = g_cq_idx + 1
    if g_cq_idx >= depth
        g_cq_idx = 0
        g_cq_phase = g_cq_phase ^ 1

fn post_tx_complete()
    if g_tx_cq_base == 0 or g_tx_cq_depth == 0
        return
    let cqe: u64 = g_tx_cq_base + (g_tx_cq_prod as u64) * 8
    zero(cqe, 8)
    *(cqe as *u16) = g_tx_cq_prod as u16
    *((cqe + 2) as *u8) = 0
    *((cqe + 3) as *u8) = g_tx_cq_phase
    g_tx_cq_prod = g_tx_cq_prod + 1
    if g_tx_cq_prod >= g_tx_cq_depth as u32
        g_tx_cq_prod = 0
        g_tx_cq_phase = g_tx_cq_phase ^ 1

pub fn on_barrier() -> i32
    let sq: u64 = rd_addr(ENA_REGS_AQ_BASE_LO_OFF, ENA_REGS_AQ_BASE_HI_OFF)
    if sq != 0
        let db: u32 = rd32(ENA_REGS_AQ_DB_OFF)
        if db != g_last_db
            g_last_db = db
            service()
    # A TX doorbell completes the descriptor just submitted.
    if g_tx_cq_base != 0 and g_tx_db_off != 0
        let tdb: u32 = rd32(g_tx_db_off)
        if tdb != g_last_tx_db
            g_last_tx_db = tdb
            post_tx_complete()
    let ctl: u32 = rd32(ENA_REGS_DEV_CTL_OFF)
    if (ctl & ENA_REGS_DEV_CTL_DEV_RESET_MASK) != 0
        wr32(ENA_REGS_DEV_STS_OFF, ENA_REGS_DEV_STS_RESET_IN_PROGRESS_MASK)
    else
        wr32(ENA_REGS_DEV_STS_OFF, ENA_REGS_DEV_STS_READY_MASK)
    return 0

# Post an RX completion the way the device would: status phase bit, then
# length (offset 4) and req_id (offset 6) of the 16-byte base descriptor.
pub fn post_rx_complete(req_id: u16, length: u16) -> i32
    if g_rx_cq_base == 0 or g_rx_cq_depth == 0
        return -1
    let cqe: u64 = g_rx_cq_base + (g_rx_cq_prod as u64) * 16
    zero(cqe, 16)
    let status: u32 = (g_rx_cq_phase as u32) << 24
    *(cqe as *u32) = status
    *((cqe + 4) as *u16) = length
    *((cqe + 6) as *u16) = req_id
    g_rx_cq_prod = g_rx_cq_prod + 1
    if g_rx_cq_prod >= g_rx_cq_depth as u32
        g_rx_cq_prod = 0
        g_rx_cq_phase = g_rx_cq_phase ^ 1
    return 0
"""

STUBS = {
    "serial.ritz": SERIAL_STUB,
    "io.ritz": IO_STUB,
    "arch/x86_64/tsc.ritz": TSC_STUB,
    "drivers/pci.ritz": PCI_STUB,
    "mm/pmm.ritz": PMM_STUB,
    "mm/vmm.ritz": VMM_STUB,
    "fakeena.ritz": FAKEENA_STUB,
}
REAL = [
    "drivers/ena/device.ritz",
    "drivers/ena/admin.ritz",
    "drivers/ena/regs.ritz",
    "drivers/ena/io_desc.ritz",
]

# Exit code -> the claim that failed.
CHECKS = {
    1: "ena_init failed against the emulated device",
    10: "a TX ring slot's buffer lies outside the TX arena (the arena has "
    "8 buffers for a 256-entry ring)",
    11: "an RX buffer lies outside the RX arena",
    12: "a completion req_id that names no buffer was accepted as an index",
    13: "a valid completion req_id did not map to its buffer",
    14: "a posted RX completion was not delivered",
    15: "ena_send failed",
    16: "a submitted TX descriptor names a buffer outside the TX arena",
    17: "an RX completion whose req_id names no buffer was delivered",
    18: "TX completions were not reaped: the ring filled with uncompleted slots",
}

PROGRAM = """\
import drivers.ena.device {
    ena_init, ena_send, ena_poll,
    ena_tx_buffer_owned, ena_rx_buffer_owned, ena_rx_req_to_buf_index,
    ena_check_io_buffers, ena_tx_outstanding
}
import fakeena { post_rx_complete }

var g_frame: [64]u8
var g_out: [64]u8

fn main() -> i32
    if ena_init() != 0
        return 1

    # A TX ring slot may be rewritten only after the frame it held is on the
    # wire, and it must always name a buffer inside the TX arena.
    var slot: u32 = 0
    while slot < 256
        if not ena_tx_buffer_owned(slot)
            return 10
        slot = slot + 1

    var ridx: u32 = 0
    while ridx < 8
        if not ena_rx_buffer_owned(ridx)
            return 11
        ridx = ridx + 1

    # A completion is untrusted input: req_id outside the arena names no buffer.
    if ena_rx_req_to_buf_index(256) != -1
        return 12
    if ena_rx_req_to_buf_index(3) != 3
        return 13

    # One RX completion for a buffer we do own is delivered and re-submitted.
    if post_rx_complete(3, 8) != 0
        return 14
    if ena_poll(@g_out[0], 64) != 8
        return 14

    # A completion naming no buffer must be dropped, not indexed into the arena.
    if post_rx_complete(2000, 8) != 0
        return 17
    if ena_poll(@g_out[0], 64) != 0
        return 17

    # More frames than the 256-entry ring holds, as the boot's TX burst.
    var n: u32 = 0
    while n < 300
        var i: i32 = 0
        while i < 64
            g_frame[i] = ((n + i as u32) & 0xFF) as u8
            i = i + 1
        if ena_send(@g_frame[0], 64) != 0
            return 15
        n = n + 1

    if ena_check_io_buffers() != 0
        return 16

    # 300 sends into a 256-slot ring only work if completions are reaped:
    # an unreaping driver leaves ~255 slots outstanding here (#1851).
    if ena_tx_outstanding() > 2
        return 18
    0
"""

MODULES = list(STUBS) + REAL


def _compile(tmp_path, path, name, extra=()):
    ll = tmp_path / f"{name}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path / 'tree'}:{RITZ_ROOT}:{tmp_path}")
    proc = run_ritz0(
        [str(path), "-o", str(ll), *extra], cwd=tmp_path, env=env, timeout=300
    )
    assert proc.returncode == 0 and ll.exists(), (
        f"ritz0 rejected {name}:\n{proc.stdout}{proc.stderr}"
    )
    return ll


def _run(tmp_path, src):
    """Compile the stub tree plus the real driver, link the program, run it."""
    tree = tmp_path / "tree"
    sources = dict(STUBS)
    for rel in REAL:
        sources[rel] = (KERNEL_SRC / rel).read_text()
    for rel, text in sources.items():
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_text(text)
    objs = [
        str(
            _compile(
                tmp_path, tree / rel, rel[:-5].replace("/", "_"), ("--no-runtime",)
            )
        )
        for rel in MODULES
    ]
    (tmp_path / "t.ritz").write_text(src)
    objs.insert(0, str(_compile(tmp_path, tmp_path / "t.ritz", "t")))
    exe = tmp_path / "t"
    link = fast_link.clang(
        [
            "clang",
            "-Wno-override-module",
            *objs,
            "-o",
            str(exe),
            "-nostdlib",
            "-no-pie",
        ],
        capture_output=True,
        text=True,
    )
    assert link.returncode == 0, f"link failed:\n{link.stderr[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


def test_ena_descriptors_name_buffers_the_driver_owns(tmp_path):
    rc = _run(tmp_path, PROGRAM)
    assert rc == 0, f"check {rc}: {CHECKS.get(rc, 'crashed or unknown exit code')}"
