"""Harland AHCI completions on plain MSI, through interrupt remapping (AGAST #4885).

ich9-ahci and the X99's Intel HBA offer a single-message MSI capability (05h)
and no MSI-X. drivers/msix.ritz now programs plain MSI beside MSI-X
(msi_probe, msi_enable): one message, a vector from the MSI-X pool so
msix_dispatch counts it, and with interrupt remapping on the message names an
IRTE that carries the vector, destination and the function's requester ID.
The AHCI driver waits on that vector for a command issued with IF=1.

The register arithmetic (msi_cap.ritz) and the completion state
(ahci/regs.ritz) are host-tested in projects/harland/test. These source
pins hold the wiring no host test reaches: the IRTE path, the order of the
count sample and the CI write, and the interrupt-status clear order.
tools/test_ahci_boot.sh boots it on q35 and through intel-iommu,intremap=on.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RITZ0_DIR = Path(__file__).resolve().parents[1]
KERNEL_SRC = RITZ0_DIR.parent.parent / "harland" / "kernel" / "src"
MSIX = KERNEL_SRC / "drivers" / "msix.ritz"
MSI_CAP = KERNEL_SRC / "drivers" / "msi_cap.ritz"
AHCI = KERNEL_SRC / "drivers" / "ahci" / "ahci.ritz"
POSTINIT = KERNEL_SRC / "postinit.ritz"


def _code(path):
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines())


def _body(code, name):
    m = re.search(rf"^(?:pub\s+)?fn {name}\(.*?(?=^\S)", code + "\nEND", re.M | re.S)
    assert m, f"fn {name} not found"
    return m.group(0)


def _check_msi_cap_module_is_import_free():
    # Host-compiled by projects/harland/test/test_msi_cap.ritz.
    assert not re.search(r"^import\b", _code(MSI_CAP), re.M)


def _check_msi_enable_uses_an_irte_when_remapping_is_on():
    body = _body(_code(MSIX), "msi_enable")
    assert "ir_enabled()" in body, body
    assert re.search(r"ir_set\(\s*\w+\s*,\s*vector\s*,\s*dest\s*,\s*\w+\s*,\s*pci_dev_sid\(dev\)", body), \
        "the IRTE must carry the vector, destination and the function's requester ID"
    assert "ir_handle_msi(vector)" in body and "ir_msi_addr(" in body and "ir_msi_data(" in body, body
    # The destination goes through the reachable-CPU check, never an 8-bit encode.
    assert "irq_route_dest(" in body and "IRQ_DEST_NONE" in body
    assert "msi_addr_lo(dest)" in body and not re.search(r"<<\s*12", body)


def _check_msi_enable_writes_with_msi_off_and_enables_one_message():
    body = _body(_code(MSIX), "msi_enable")
    off = body.index("msi_ctrl_off(")
    on = body.index("msi_ctrl_one(")
    addr = body.index("MSI_CAP_ADDR_LO")
    assert off < addr < on, "address and data must be written while MSI is off"


def _check_ahci_samples_the_vector_count_before_ci():
    body = _body(_code(AHCI), "ahci_command")
    sample = body.index("seen = msix_vector_count(vec)")
    ci = body.index("AHCI_PX_CI), 1)")
    assert sample < ci, "an interrupt landing before the sample would be missed"
    assert "irq_wait_vector(vec, seen," in body
    # PxCI stays the ground truth: every wake re-reads it through ahci_cmd_state.
    assert "ahci_cmd_state(ahci_r32(bar, ahci_port_reg(port, AHCI_PX_CI))" in body
    assert "ahci_irq_waits(" in body


def _check_ahci_clears_port_status_before_global_is():
    body = _body(_code(AHCI), "ahci_ack")
    assert body.index("AHCI_PX_IS") < body.index("AHCI_REG_IS")


def _check_ahci_request_does_not_hold_irqs_off():
    # A spinlock held across the request would keep IF clear, so no command
    # could ever wait on the vector.
    body = _body(_code(AHCI), "ahci_disk_rw")
    assert "spin_lock(" not in body
    assert "ahci_disk_take(disk)" in body and "ahci_disk_give(disk)" in body


def _check_ahci_msi_comes_up_with_postinit_and_vector_last():
    code = _code(POSTINIT)
    assert "ahci_enable_msi()" in _body(code, "ahci_msi_check")
    diag = _body(code, "postinit_diagnostics")
    assert "ahci_msi_check()" in diag
    ctl = _body(_code(AHCI), "ahci_ctl_msi")
    assert ctl.index("AHCI_PX_IE") < ctl.index("ahci_ctls[c].vec = vector"), \
        "PxIE and GHC.IE go on before commands start waiting on the vector"
    assert ctl.index("AHCI_GHC_IE") < ctl.index("ahci_ctls[c].vec = vector")


# One table, one collected case: the suite's test budget counts cases, and
# these are rows of a single source-pin check, not separate behaviours.
CHECKS = (
    _check_msi_cap_module_is_import_free,
    _check_msi_enable_uses_an_irte_when_remapping_is_on,
    _check_msi_enable_writes_with_msi_off_and_enables_one_message,
    _check_ahci_samples_the_vector_count_before_ci,
    _check_ahci_clears_port_status_before_global_is,
    _check_ahci_request_does_not_hold_irqs_off,
    _check_ahci_msi_comes_up_with_postinit_and_vector_last,
)


def test_ahci_msi_source_pins():
    failures = []
    for check in CHECKS:
        try:
            check()
        except (AssertionError, ValueError) as e:
            failures.append(f"{check.__name__}: {e}")
    assert not failures, "\n".join(failures)
