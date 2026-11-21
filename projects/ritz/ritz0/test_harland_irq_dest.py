"""Harland's device interrupts reach a CPU that can take them (AGAST #4233).

#4184 gave IPIs 32-bit x2APIC destinations, but device interrupts kept two
older assumptions:

- drivers/msix.ritz put `lapic_id() & 0xFF` in the MSI address's 8-bit
  destination, so a table entry set up on a CPU with APIC ID 256 went to
  APIC ID 0, 257 to 1, and so on.
- arch/x86_64/apic.ritz's ioapic_init sent IRQ 1 (keyboard) and IRQ 4 (COM1,
  the interactive console since #4254) to the literal APIC ID 0, not to the
  BSP, so on firmware whose BSP isn't APIC ID 0 they were lost.

The destination logic now lives in arch/x86_64/irq_dest.ritz (no imports, no
hardware): an ID is reachable below 255, or up to 0x7FFF with KVM's extended
destination ID (bits 11:5 of the MSI address, 55:49 of a redirection entry);
anything else goes to the BSP, or the first reachable CPU. The behaviour test
compiles it into a host program whose exit code names the failed claim. QEMU
always gives CPU 0 APIC ID 0, so a BSP that isn't APIC ID 0 can't be booted;
the source-level tests pin that ioapic_init and msix_set_entry route through
the BSP's ID and irq_dest. tools/test_irq_dest_boot.sh boots a CPU with APIC
ID 256.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ0_DIR = Path(__file__).resolve().parent
RITZ_ROOT = RITZ0_DIR.parent
KERNEL_SRC = RITZ_ROOT.parent / "harland" / "kernel" / "src"
IRQ_DEST = KERNEL_SRC / "arch" / "x86_64" / "irq_dest.ritz"
APIC = KERNEL_SRC / "arch" / "x86_64" / "apic.ritz"
MSIX = KERNEL_SRC / "drivers" / "msix.ritz"

PROGRAM = """\
import arch.x86_64.irq_dest

var ids: [4]u32

fn main() -> i32
    # 8-bit destinations: 0..254; 255 is broadcast, 256+ needs more bits
    if not irq_dest_reachable(0, false, false) or not irq_dest_reachable(254, false, false)
        return 1
    if irq_dest_reachable(255, false, false) or irq_dest_reachable(255, true, false)
        return 2
    if irq_dest_reachable(256, false, false) or irq_dest_reachable(0x7FFF, false, false)
        return 3
    # extended destination ID: up to 15 bits
    if not irq_dest_reachable(256, true, false) or not irq_dest_reachable(0x7FFF, true, false) or irq_dest_reachable(0x8000, true, false)
        return 4
    # MSI address: ID bits 7:0 in 19:12, bits 14:8 in 11:5
    if msi_addr_lo(0) != 0xFEE00000 or msi_addr_lo(5) != 0xFEE05000 or msi_addr_lo(254) != 0xFEEFE000
        return 5
    if msi_addr_lo(256) != 0xFEE00020 or msi_addr_lo(0x1234) != 0xFEE34240 or msi_addr_lo(0x7FFF) != 0xFEEFFFE0
        return 6
    if msi_addr_dest(msi_addr_lo(0x1234)) != 0x1234 or msi_addr_dest(msi_addr_lo(7)) != 7
        return 7
    # I/O APIC redirection entry, high dword: ID 7:0 in 31:24, 14:8 in 23:17
    if ioapic_rte_hi(0) != 0 or ioapic_rte_hi(3) != 0x03000000 or ioapic_rte_hi(256) != 0x00020000
        return 8
    if ioapic_rte_hi(0x1234) != 0x34240000 or ioapic_rte_dest(ioapic_rte_hi(0x7FFF)) != 0x7FFF
        return 9
    if ioapic_rte_dest(ioapic_rte_hi(3)) != 3
        return 10
    # picking: the wanted CPU if reachable
    ids[0] = 300
    ids[1] = 256
    ids[2] = 9
    ids[3] = 4
    if irq_dest_pick(4, 300, @ids[0], 4, false, false) != 4
        return 11
    # else the BSP (whatever its ID), not APIC ID 0 or the low byte
    if irq_dest_pick(256, 9, @ids[0], 4, false, false) != 9 or irq_dest_pick(257, 3, @ids[0], 4, false, false) != 3
        return 12
    # else the first reachable CPU in the list
    if irq_dest_pick(256, 300, @ids[0], 4, false, false) != 9
        return 13
    # with the extended destination ID, 256 takes its own
    if irq_dest_pick(256, 9, @ids[0], 4, true, false) != 256
        return 14
    # nothing reachable
    ids[2] = 255
    ids[3] = 511
    if irq_dest_pick(256, 300, @ids[0], 4, false, false) != IRQ_DEST_NONE
        return 15
    # KVM's signature and feature bit 15
    if not irq_ext_dest_from_cpuid(0x40000001, 0x4B4D564B, 0x564B4D56, 0x4D, 0x8000)
        return 16
    if irq_ext_dest_from_cpuid(0x40000001, 0x4B4D564B, 0x564B4D56, 0x4D, 0x7FFF)
        return 17
    if irq_ext_dest_from_cpuid(0x40000000, 0x4B4D564B, 0x564B4D56, 0x4D, 0x8000)
        return 18
    # Hyper-V ("Microsoft Hv") with the same bit set doesn't count
    if irq_ext_dest_from_cpuid(0x40000005, 0x7263694D, 0x666F736F, 0x76482074, 0x8000)
        return 19
    # interrupt remapping with 32-bit destinations (#4316): every ID but
    # x2APIC broadcast, 255 and past 0x7FFF included
    if not irq_dest_reachable(255, false, true) or not irq_dest_reachable(0x8000, false, true)
        return 20
    if not irq_dest_reachable(0xFFFFFFFE, true, true) or irq_dest_reachable(0xFFFFFFFF, true, true)
        return 21
    # with remapping, 256 and 511 take their own; nothing is rerouted
    if irq_dest_pick(256, 300, @ids[0], 4, false, true) != 256 or irq_dest_pick(511, 0, @ids[0], 4, false, true) != 511
        return 22
    0
"""

CLAIMS = {1: "IDs 0..254 reachable", 2: "255 is broadcast", 3: "256+ needs ext dest",
          4: "ext dest reaches 15 bits", 5: "MSI addr low IDs", 6: "MSI addr ext bits 11:5",
          7: "MSI addr round trip", 8: "RTE hi low IDs", 9: "RTE hi ext bits 23:17",
          10: "RTE round trip", 11: "pick wanted", 12: "pick BSP", 13: "pick first reachable",
          14: "pick ext dest", 15: "pick none", 16: "KVM ext dest bit", 17: "KVM without bit",
          18: "KVM leaf missing", 19: "non-KVM signature",
          20: "IR reaches 255 and 15+ bits", 21: "IR x2APIC broadcast", 22: "pick with IR"}


@pytest.mark.integration
def test_irq_dest_selection_and_encoding(tmp_path):
    tree = tmp_path / "tree" / "arch" / "x86_64"
    tree.mkdir(parents=True)
    (tree / "irq_dest.ritz").write_text(IRQ_DEST.read_text())
    (tmp_path / "t.ritz").write_text(PROGRAM)
    env = dict(os.environ, RITZ_PATH=f"{tmp_path / 'tree'}:{RITZ_ROOT}:{tmp_path}")
    objs = []
    for src, name, extra in [(tmp_path / "t.ritz", "t", ()),
                             (tree / "irq_dest.ritz", "irq_dest", ("--no-runtime",))]:
        ll = tmp_path / f"{name}.ll"
        proc = run_ritz0([str(src), "-o", str(ll), *extra], cwd=tmp_path, env=env, timeout=300)
        assert proc.returncode == 0 and ll.exists(), f"ritz0 rejected {name}:\n{proc.stdout}{proc.stderr}"
        objs.append(str(ll))
    exe = tmp_path / "t"
    link = subprocess.run(["clang", "-Wno-override-module", *objs, "-o", str(exe), "-nostdlib", "-no-pie"],
                          capture_output=True, text=True)
    assert link.returncode == 0, link.stderr[-3000:]
    rc = subprocess.run([str(exe)], capture_output=True, timeout=60).returncode
    assert rc == 0, f"exit {rc}: {CLAIMS.get(rc, 'crash')}"


# --- source level: the kernel routes through irq_dest and the BSP's ID ---------

def _code(path):
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines())


def _body(code, name):
    m = re.search(rf"^(?:pub\s+)?fn {name}\(.*?(?=^\S)", code + "\nEND", re.M | re.S)
    assert m, f"fn {name} not found"
    return m.group(0)


@pytest.mark.unit
def test_irq_dest_module_is_import_free():
    assert not re.search(r"^import\b", _code(IRQ_DEST), re.M), "irq_dest.ritz must stay import-free (host-compiled)"


@pytest.mark.unit
def test_msix_entry_targets_a_reachable_cpu():
    code = _code(MSIX)
    # msix_set_entry aims at the current CPU by delegating to the function
    # that takes an explicit destination (AGAST #4220: per-CPU vectors).
    entry = _body(code, "msix_set_entry")
    assert re.search(r"msix_set_entry_to\([^)]*lapic_id\(\)", entry), entry
    body = _body(code, "msix_set_entry_to")
    assert "& 0xFF" not in body, "msix_set_entry still truncates the APIC ID to 8 bits"
    assert not re.search(r"<<\s*12", body), "msix_set_entry still encodes the address itself"
    # the destination is picked for the CPU the entry is meant for
    m = re.search(r"let (\w+): u32 = want", body)
    assert m and re.search(rf"irq_route_dest\(\s*{m.group(1)}\s*\)", body), body
    assert "msi_addr_lo(" in body, body
    assert "IRQ_DEST_NONE" in body, "msix_set_entry ignores 'no reachable CPU'"


@pytest.mark.unit
def test_ioapic_routes_to_the_bsp_not_apic_id_0():
    code = _code(APIC)
    init = _body(code, "ioapic_init")
    # IRQ 1 and IRQ 4 are unmasked to a computed destination, not a literal
    for irq, vec in (("1", "33"), ("4", "36")):
        m = re.search(rf"ioapic_set_irq\(\s*{irq}\s*,\s*{vec}\s*,\s*([^,]+),\s*false\s*\)", init)
        assert m, f"IRQ {irq} isn't unmasked in ioapic_init"
        assert not re.fullmatch(r"\d+", m.group(1).strip()), f"IRQ {irq} goes to literal APIC ID {m.group(1)}"
    assert re.search(r"irq_route_dest\(\s*bsp_apic_id\s*\)", init), init
    set_irq = _body(code, "ioapic_set_irq")
    assert re.search(r"dest_apic:\s*u32", set_irq), "ioapic_set_irq still takes an 8-bit destination"
    assert "ioapic_rte_hi(" in set_irq, set_irq
    # bsp_apic_id is known before the I/O APIC is set up (ap_boot_all is later)
    select = _body(code, "apic_select_mode")
    assert re.search(r"bsp_apic_id\s*=\s*lapic_id\(\)", select), select
    for init_fn in ("apic_init_with_mb", "apic_init_from_bootinfo"):
        b = _body(code, init_fn)
        assert b.index("apic_select_mode()") < b.index("ioapic_init()"), init_fn
