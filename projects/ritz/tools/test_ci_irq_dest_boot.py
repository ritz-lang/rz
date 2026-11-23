"""CI boots harland with an APIC ID 256 CPU and checks device-interrupt
destinations (AGAST #4233), without and with VT-d (#4316) or AMD-Vi (#4329)
interrupt remapping.

projects/harland/tools/test_irq_dest_boot.sh boots q35 + OVMF with the BSP at
APIC ID 0 and an AP at 256. The MSI and I/O APIC destination is 8 bits, so the
kernel must log APIC ID 256's device interrupts as going to the BSP, the I/O
APIC's IRQ 1 and IRQ 4 must read back as the BSP's ID, NVMe must still
deliver MSI-X interrupts and init's suite must pass. A second boot adds
-device intel-iommu,intremap=on,eim=on: remapping must come up in extended
interrupt mode, APIC ID 256 must keep its own interrupts and the I/O APIC
and NVMe entries must go through IRTEs aimed at the BSP. A third boot does
the same with -device amd-iommu,intremap=on,xtsup=on. These tests pin the
main.yml wiring and the script's verdicts against a stub QEMU.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ci_local  # noqa: E402

REPO = ci_local.REPO_ROOT
SCRIPT = "projects/harland/tools/test_irq_dest_boot.sh"
TIER1_SCRIPT = "projects/harland/tools/test_tier1_boot.sh"

# The QEMU stub writes $FAKE_SERIAL to the `-serial file:PATH` it was given
# and idles until killed; every argv goes to $STUB_LOG.
QEMU_STUB = r"""#!/usr/bin/env bash
echo "$@" >> "$STUB_LOG"
prev=""
for a in "$@"; do
    if [ "$prev" = "-serial" ]; then printf '%b' "$FAKE_SERIAL" > "${a#file:}"; fi
    prev="$a"
done
sleep 30
"""
MKINITRAMFS_STUB = """import sys
out = sys.argv[sys.argv.index("--output") + 1]
open(out, "wb").close()
"""

X2APIC = r"      LAPIC mode: x2APIC\n"
DEST_8BIT = r"      Device interrupt destinations: 8-bit (APIC IDs up to 254; no interrupt remapping or extended destination ID)\n"
DEST_EXT = r"      Device interrupt destinations: extended destination ID (APIC IDs up to 32767)\n"


def ioapic(irq1: int, irq4: int) -> str:
    return rf"      I/O APIC: IRQ 1 -> APIC ID {irq1}, IRQ 4 -> APIC ID {irq4}\n"


def bsp(n: int) -> str:
    return rf"    BSP APIC ID: {n}\n"


APS = r"  [OK] Boot APs (1 APs started)\n"
REROUTE_256 = (r"    [irq] APIC ID 256: device interrupts -> APIC ID 0 (MSI addr FEE00000): "
               r"beyond the 8-bit MSI/I/O APIC destination; no interrupt remapping or extended destination ID\n")
NVME = (r"[msix] nvme harland-irq: MSI-X on, vectors admin=64 io=65\n"
        r"[msix] nvme interrupts: 3, commands waited: 2, completions without one: 0\n")
SUITE = r"  ALL TESTS PASSED\n"

PASSED = X2APIC + DEST_8BIT + ioapic(0, 0) + bsp(0) + APS + REROUTE_256 + NVME + SUITE

IR_ON = r"      Interrupt remapping: VT-d on, 1 unit(s), table at 3DE000, 32-bit x2APIC destinations (EIM)\n"
DEST_IR = r"      Device interrupt destinations: interrupt remapping (32-bit APIC IDs)\n"
IOAPIC_IR = r"      I/O APIC: IRQ 1 -> APIC ID 0, IRQ 4 -> APIC ID 0 (remapped: IRTE 1, 4)\n"
NVME_IR = NVME.replace("io=65\\n", "io=65 (IRTE 192, 193 -> APIC ID 0, 0)\\n", 1)
# #4339: the AP's own I/O vector, set up through an IRTE aimed at APIC ID 256
AP_IR = (r"[msix] nvme AP 256: nsid 1: LBA 32568-32767 fnv1a=2166136261, waited=1, interrupted=1, "
         r"IRTE 194 -> APIC ID 256\n")
# #4339: a level-triggered pin. VT-d keeps the vector in the entry, so the
# LAPIC's EOI broadcast clears it; AMD-Vi puts the IRTE handle there.
LEVEL_VTD = r"      I/O APIC: level pin 23: entry vector 55 for vector 55, broadcast EOI\n"
LEVEL_AMD = r"      I/O APIC: level pin 23: entry vector 23 for vector 55, directed EOI\n"
VTD_PASSED = X2APIC + IR_ON + DEST_IR + IOAPIC_IR + LEVEL_VTD + bsp(0) + APS + NVME_IR + AP_IR + SUITE

AMD_ON = r"      Interrupt remapping: AMD-Vi on, 1 unit(s), device table at 3DB000, 32-bit x2APIC destinations (GA, XT)\n"
AMDVI_PASSED = VTD_PASSED.replace(IR_ON, AMD_ON).replace(LEVEL_VTD, LEVEL_AMD)


def _build_all() -> list[dict]:
    return yaml.safe_load(ci_local.WORKFLOW.read_text())["jobs"]["build-all"]["steps"]


def _step_index(steps: list[dict], script: str) -> int:
    hits = [i for i, s in enumerate(steps) if script in str(s.get("run", ""))]
    assert len(hits) == 1, f"want exactly one build-all step running {script}, got {hits}"
    return hits[0]


@pytest.mark.unit
def test_irq_dest_boot_runs_after_the_tier1_boot_and_before_the_log_upload():
    steps = _build_all()
    i = _step_index(steps, SCRIPT)
    assert i > _step_index(steps, TIER1_SCRIPT)
    uploads = [j for j, s in enumerate(steps) if "upload-artifact" in str(s.get("uses", ""))]
    assert uploads and min(uploads) > i, "irq-dest.log must be uploaded too"
    step = steps[i]
    assert "continue-on-error" not in step and "|| true" not in step["run"]
    assert step.get("timeout-minutes") and "boot-logs" in step["run"]
    assert "SKIP_BUILD" not in step["run"]


@pytest.mark.unit
def test_the_machine_has_an_apic_id_256_cpu():
    text = (REPO / SCRIPT).read_text()
    assert 'machine="q35"' in text and '-machine "$machine"' in text and "+x2apic" in text
    assert "-smp 1,sockets=2,cores=200,maxcpus=400" in text
    assert "socket-id=1,core-id=0,thread-id=0" in text


@pytest.mark.unit
def test_the_vtd_boot_has_an_iommu_with_32_bit_remapping():
    text = (REPO / SCRIPT).read_text()
    assert "-device intel-iommu,intremap=on,eim=on" in text
    # KVM needs the split irqchip for the IOMMU's interrupt remapping
    assert 'machine="q35,kernel-irqchip=split"' in text
    assert 'IRQ_DEST_BOOTS:-plain vtd amdvi' in text, "CI must run every boot by default"


@pytest.mark.unit
def test_the_amdvi_boot_has_an_amd_iommu_with_x2apic_remapping():
    text = (REPO / SCRIPT).read_text()
    assert "-device amd-iommu,intremap=on,xtsup=on" in text
    # KVM needs the split irqchip for either IOMMU
    assert '[ "$name" != plain ] && machine="q35,kernel-irqchip=split"' in text


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "repo"
    tools = root / "projects" / "harland" / "tools"
    tools.mkdir(parents=True)
    shutil.copy(REPO / SCRIPT, tools / "test_irq_dest_boot.sh")
    (tools / "mkinitramfs.py").write_text(MKINITRAMFS_STUB)
    for rel in ("projects/harland/build/debug/harland.elf",
                "projects/harland/build/debug/BOOTX64.EFI",
                "projects/indium/build/debug/init.elf"):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x7fELF")
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    ovmf = tmp_path / "OVMF_CODE.fd"
    ovmf.write_bytes(b"")
    q = stubs / "qemu-system-x86_64"
    q.write_text(QEMU_STUB)
    q.chmod(0o755)
    return {"script": tools / "test_irq_dest_boot.sh", "stubs": stubs, "ovmf": ovmf, "tmp": tmp_path}


def _run(tree, serial: str, boots: str = "plain") -> subprocess.CompletedProcess:
    env = {
        "IRQ_DEST_BOOTS": boots,
        "PATH": f"{tree['stubs']}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(tree["tmp"]),
        "TMPDIR": str(tree["tmp"]),
        "SKIP_BUILD": "1",
        "BOOT_TIMEOUT": "3",
        "OVMF_CODE": str(tree["ovmf"]),
        "STUB_LOG": str(tree["tmp"] / "stub.log"),
        "FAKE_SERIAL": serial,
    }
    return subprocess.run(["/bin/bash", str(tree["script"])], env=env,
                          capture_output=True, text=True, timeout=60)


@pytest.mark.integration
def test_a_good_boot_passes(tree):
    r = _run(tree, PASSED)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS: [plain] APIC ID 256's device interrupts go to the BSP" in r.stdout


@pytest.mark.integration
def test_a_good_vtd_boot_passes(tree):
    r = _run(tree, VTD_PASSED, "vtd")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS: [vtd] APIC ID 256 takes its own device interrupts (interrupt remapping)" in r.stdout
    argv = (tree["tmp"] / "stub.log").read_text()
    assert "intel-iommu,intremap=on,eim=on" in argv


@pytest.mark.integration
def test_both_boots_run_by_default(tree):
    r = _run(tree, PASSED, "plain vtd")
    # one fake serial for both: plain passes, vtd fails, so the run fails
    assert r.returncode == 1 and "PASS: [plain] init Tier-1 suite" in r.stdout and "FAIL: [vtd]" in r.stdout
    argv = (tree["tmp"] / "stub.log").read_text().splitlines()
    assert len(argv) == 2 and "intel-iommu" not in argv[0] and "intel-iommu" in argv[1]


@pytest.mark.integration
def test_a_good_amdvi_boot_passes(tree):
    r = _run(tree, AMDVI_PASSED, "amdvi")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS: [amdvi] AMD-Vi interrupt remapping on with 32-bit destinations (GA, XT)" in r.stdout
    assert "PASS: [amdvi] APIC ID 256 takes its own device interrupts (interrupt remapping)" in r.stdout
    argv = (tree["tmp"] / "stub.log").read_text()
    assert "amd-iommu,intremap=on,xtsup=on" in argv and "intel-iommu" not in argv


@pytest.mark.integration
def test_the_vtd_line_does_not_pass_an_amdvi_boot(tree):
    # each vendor's boot must see its own IOMMU come up
    r = _run(tree, VTD_PASSED, "amdvi")
    assert r.returncode == 1 and "FAIL: [amdvi] interrupt remapping is not on" in r.stdout, r.stdout
    r = _run(tree, AMDVI_PASSED, "vtd")
    assert r.returncode == 1 and "FAIL: [vtd] interrupt remapping is not on" in r.stdout, r.stdout


@pytest.mark.integration
@pytest.mark.parametrize("serial, why", [
    (AMDVI_PASSED.replace(AMD_ON, r"      Interrupt remapping: off (no DMAR or IVRS table)\n"), "interrupt remapping is not on"),
    (AMDVI_PASSED.replace(AMD_ON, AMD_ON.replace("32-bit x2APIC destinations (GA, XT)", "8-bit xAPIC destinations (GA)")),
     "interrupt remapping is not on"),
    (AMDVI_PASSED + REROUTE_256, "rerouted though interrupt remapping reaches it"),
    (AMDVI_PASSED.replace(IOAPIC_IR, ioapic(0, 0)), "not in the remappable format"),
    (AMDVI_PASSED.replace(NVME_IR, NVME), "NVMe MSI-X entries are not in the remappable format"),
    (AMDVI_PASSED.replace("-> APIC ID 0, 0)", "-> APIC ID 0, 256)"), "want \"(IRTE 192, 193 -> APIC ID 0, 0)\""),
    # #4339: the AP's IRTE, and an interrupt delivered through it
    (AMDVI_PASSED.replace(AP_IR, ""), "no NVMe read on APIC ID 256"),
    (AMDVI_PASSED.replace("IRTE 194 -> APIC ID 256", "IRTE 194 -> APIC ID 0"), "IRTE aimed at APIC ID 0, want 256"),
    (AMDVI_PASSED.replace(", IRTE 194 -> APIC ID 256", ""), "not set up through an IRTE"),
    (AMDVI_PASSED.replace("waited=1, interrupted=1", "waited=1, interrupted=0"), "interrupted=0"),
    # #4339: level pins under AMD-Vi need the directed EOI
    (AMDVI_PASSED.replace(LEVEL_AMD, LEVEL_AMD.replace("directed", "broadcast")), "want directed EOI"),
    (AMDVI_PASSED.replace(LEVEL_AMD, ""), "no level pin set up"),
])
def test_a_bad_amdvi_boot_fails(tree, serial, why):
    r = _run(tree, serial, "amdvi")
    assert r.returncode == 1, r.stdout + r.stderr
    assert why in r.stdout, r.stdout


@pytest.mark.integration
@pytest.mark.parametrize("serial, why", [
    (VTD_PASSED.replace(IR_ON, r"      Interrupt remapping: off (no DMAR table)\n"), "interrupt remapping is not on"),
    (VTD_PASSED.replace(IR_ON, IR_ON.replace("32-bit x2APIC destinations (EIM)", "8-bit xAPIC destinations")),
     "interrupt remapping is not on"),
    (VTD_PASSED.replace(DEST_IR, DEST_8BIT), "not 32-bit through remapping"),
    (VTD_PASSED + REROUTE_256, "rerouted though interrupt remapping reaches it"),
    (VTD_PASSED.replace(IOAPIC_IR, ioapic(0, 0)), "not in the remappable format"),
    (VTD_PASSED.replace(NVME_IR, NVME), "NVMe MSI-X entries are not in the remappable format"),
    (VTD_PASSED.replace("-> APIC ID 0, 0)", "-> APIC ID 0, 256)"), "want \"(IRTE 192, 193 -> APIC ID 0, 0)\""),
    (VTD_PASSED.replace("(IRTE 192, 193", "(IRTE 64, 65"), "want"),
    (VTD_PASSED.replace("interrupts: 3,", "interrupts: 0,"), "counter is 0"),
    (VTD_PASSED.replace("IRTE 194 -> APIC ID 256", "IRTE 194 -> APIC ID 0"), "IRTE aimed at APIC ID 0, want 256"),
    (VTD_PASSED.replace(LEVEL_VTD, LEVEL_AMD), "want broadcast EOI"),
])
def test_a_bad_vtd_boot_fails(tree, serial, why):
    r = _run(tree, serial, "vtd")
    assert r.returncode == 1, r.stdout + r.stderr
    assert why in r.stdout, r.stdout


@pytest.mark.integration
def test_an_unknown_boot_is_a_setup_error(tree):
    r = _run(tree, PASSED, "plain nope")
    assert r.returncode == 3 and "unknown boot" in r.stderr


@pytest.mark.integration
def test_with_the_extended_destination_id_256_keeps_its_own(tree):
    r = _run(tree, PASSED.replace(DEST_8BIT, DEST_EXT).replace(REROUTE_256, ""))
    assert r.returncode == 0, r.stdout + r.stderr
    r = _run(tree, PASSED.replace(DEST_8BIT, DEST_EXT))
    assert r.returncode == 1 and "rerouted though the extended destination ID" in r.stdout


@pytest.mark.integration
@pytest.mark.parametrize("serial, why", [
    (PASSED.replace(ioapic(0, 0), ioapic(0, 0)).replace(bsp(0), bsp(5)), "not to the BSP (5)"),
    (PASSED.replace(ioapic(0, 0), ioapic(0, 3)), "IRQ 4 to 3"),
    (PASSED.replace(ioapic(0, 0), ""), "no I/O APIC routing read back"),
    (PASSED.replace(REROUTE_256, ""), "[irq] APIC ID 256: device interrupts -> APIC ID 0"),
    (PASSED.replace(REROUTE_256, REROUTE_256.replace("APIC ID 0 (", "APIC ID 1 (")), "[irq] APIC ID 256"),
    (PASSED.replace(APS, r"  [OK] Boot APs (0 APs started)\n"), "did not start"),
    (PASSED.replace(X2APIC, ""), "not in x2APIC mode"),
    (PASSED.replace("interrupts: 3,", "interrupts: 0,"), "counter is 0"),
    (PASSED.replace("without one: 0", "without one: 2"), "arrived without an interrupt"),
    (PASSED.replace(SUITE, ""), "did not report ALL TESTS PASSED"),
    (PASSED + r"KERNEL PANIC\n", "kernel exception"),
])
def test_a_bad_boot_fails(tree, serial, why):
    r = _run(tree, serial)
    assert r.returncode == 1, r.stdout + r.stderr
    assert why in r.stdout, r.stdout
