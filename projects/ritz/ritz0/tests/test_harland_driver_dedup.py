"""Harland's duplicated driver/kernel code is collapsed to one copy (AGAST #1884).

LARB v4 review/4/harland.md M4/M5 listed copy-pasted clusters. Several were
already folded by the time #1884 ran (vq_submit's fence, ENA on io.ritz's
barriers, virtio-net on virtio/common, one spawn path, one PD-fill loop).
This file pins the rest, at source level:

* virtio-blk: virtio_blk_read and virtio_blk_write were 100-line twins that
  differed in the request type, the data descriptor's WRITE flag and which way
  the bounce copy goes. One virtio_blk_rw builds and submits the request; the
  two public names are wrappers over it.
* APIC: apic_init_with_mb and apic_init_from_bootinfo differed only in the
  ACPI call. The LAPIC/IOAPIC/PIC bring-up after it is one function.
* User stack: alloc_user_stack's two unwind loops and free_user_stack were
  three copies of "unmap and free N pages" that sys_mmap_impl's rollback
  already had. All four use the one helper.

Behaviour is unchanged by construction. test_harland_virtio_blk_timeout.py
runs both blk paths on a host-compiled fake device; the OVMF Tier-1 boot
(tools/test_tier1_boot.sh) is the runtime check of the rest.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RITZ0_DIR = Path(__file__).resolve().parents[1]
KERNEL_SRC = RITZ0_DIR.parents[1] / "harland" / "kernel" / "src"
BLK = KERNEL_SRC / "drivers" / "virtio" / "blk.ritz"
APIC = KERNEL_SRC / "arch" / "x86_64" / "apic.ritz"
MEMORY = KERNEL_SRC / "syscall" / "runtime" / "memory.ritz"


def _bodies(path):
    """{fn name: body text}, comments stripped. A body runs to the next top-level line."""
    code = [line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines()]
    bodies, name = {}, None
    for line in code:
        m = re.match(r"^(?:pub\s+)?fn\s+(\w+)\s*\(", line)
        if m:
            name = m.group(1)
            bodies[name] = []
        elif line and not line[0].isspace():
            name = None
        elif name:
            bodies[name].append(line)
    return {k: "\n".join(v) for k, v in bodies.items()}


def _callers(bodies, callee):
    return sorted(n for n, b in bodies.items() if re.search(rf"\b{callee}\s*\(", b))


def test_one_virtio_blk_request_path():
    b = _bodies(BLK)
    assert "virtio_blk_rw" in b, "blk.ritz has no virtio_blk_rw"
    assert _callers(b, "vq_submit") == ["virtio_blk_rw"], \
        f"virtio-blk requests are built in more than one place: {_callers(b, 'vq_submit')}"
    for wrapper in ("virtio_blk_read", "virtio_blk_write"):
        body = [ln for ln in b[wrapper].splitlines() if ln.strip()]
        assert len(body) == 1 and "virtio_blk_rw(" in body[0], \
            f"{wrapper} is not a one-line wrapper over virtio_blk_rw:\n{b[wrapper]}"


def test_one_apic_bring_up():
    b = _bodies(APIC)
    for step in ("apic_map_registers", "apic_select_mode", "ioapic_init", "pic_disable"):
        callers = _callers(b, step)
        assert len(callers) == 1 and callers[0] not in ("apic_init_with_mb", "apic_init_from_bootinfo"), \
            f"{step} is called from {callers}: the bring-up after ACPI is not shared"
    shared = _callers(b, "ioapic_init")[0]
    for entry in ("apic_init_with_mb", "apic_init_from_bootinfo"):
        assert re.search(rf"\b{shared}\s*\(", b[entry]), f"{entry} does not call {shared}"


def test_one_unmap_and_free_loop():
    b = _bodies(MEMORY)
    # sys_munmap_impl unmaps arbitrary user pages one at a time, with its own
    # accounting; every rollback/teardown goes through the one helper.
    loops = [n for n in _callers(b, "vmm_unmap_page") if n != "sys_munmap_impl"]
    assert len(loops) == 1, f"unmap-and-free is open-coded in {loops}"
    helper = loops[0]
    for user in ("alloc_user_stack", "free_user_stack", "sys_mmap_impl"):
        assert re.search(rf"\b{helper}\s*\(", b[user]), f"{user} does not call {helper}"
