#!/usr/bin/env python3
"""CI must boot harland on q35 and check the polled AHCI probe (AGAST #4882).

projects/harland/tools/test_ahci_boot.sh boots under OVMF with no virtio-blk
and no NVMe. Two ide-hd disks on ich9-ahci must log IDENTIFY with the sector
counts the script created. A second step attaches no ide-hd; the empty
controller must log one summary and no per-port line. A missing tool is a
SETUP ERROR (exit 3). Every failed check is exit 1.

Run with:
    python3 -m pytest projects/ritz/tools/test_ci_ahci_boot.py -q
"""

from __future__ import annotations

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
AHCI_SCRIPT = "projects/harland/tools/test_ahci_boot.sh"
NVME_SCRIPT = "projects/harland/tools/test_nvme_boot.sh"

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

ROOT_LINE = (
    "[ahci] 00:1f.2 port 0: QEMU HARDDISK harland-root, 2048 sectors, "
    "512-byte sectors, write cache\n"
)
DATA_LINE = (
    "[ahci] 00:1f.2 port 1: QEMU HARDDISK harland-data, 8192 sectors, "
    "512-byte sectors, write cache\n"
)
SUMMARY = "[ahci] 00:1f.2: 2 disks\n"
IDENTIFY = ROOT_LINE + DATA_LINE + SUMMARY
EMPTY = "[ahci] 00:1f.2: 0 disks\n"


def _build_all() -> list[dict]:
    return yaml.safe_load(ci_local.WORKFLOW.read_text())["jobs"]["build-all"]["steps"]


def _indices(steps: list[dict], script: str) -> list[int]:
    return [i for i, s in enumerate(steps) if script in str(s.get("run", ""))]


def test_ahci_boot_runs_after_nvme_and_before_the_log_upload():
    assert (REPO / AHCI_SCRIPT).is_file()
    steps = _build_all()
    ahci = _indices(steps, AHCI_SCRIPT)
    nvme = _indices(steps, NVME_SCRIPT)
    assert len(ahci) == 2
    assert nvme and min(ahci) > max(nvme)
    uploads = [i for i, s in enumerate(steps) if "upload-artifact" in str(s.get("uses", ""))]
    assert uploads and min(uploads) > max(ahci)


def test_ahci_steps_are_real_gates_with_timeouts():
    steps = _build_all()
    runs = [steps[i] for i in _indices(steps, AHCI_SCRIPT)]
    assert len(runs) == 2
    assert any("AHCI_EMPTY=1" in s["run"] for s in runs)
    assert any("AHCI_EMPTY" not in s["run"] for s in runs)
    for step in runs:
        assert "continue-on-error" not in step
        assert "|| true" not in step["run"]
        assert step.get("timeout-minutes")
        assert "boot-logs" in step["run"]
    parsed = [s for s in ci_local.load_steps() if AHCI_SCRIPT in s.run]
    assert len(parsed) == 2 and not any(s.is_setup for s in parsed)


def test_the_boot_uses_ide_hd_on_q35_without_virtio_blk():
    text = (REPO / AHCI_SCRIPT).read_text()
    cmd = text.split("qemu-system-x86_64", 1)[1]
    assert "-machine q35" in cmd
    assert "-nodefaults" in cmd
    assert "virtio-blk" not in cmd
    assert "ide-hd,drive=root,bus=ide.0,serial=harland-root" in text
    assert "ide-hd,drive=data,bus=ide.1,serial=harland-data" in text
    assert "usb-storage" in text


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "repo"
    tools = root / "projects" / "harland" / "tools"
    tools.mkdir(parents=True)
    shutil.copy(REPO / AHCI_SCRIPT, tools / "test_ahci_boot.sh")
    (tools / "mkinitramfs.py").write_text(MKINITRAMFS_STUB)
    for rel in (
        "projects/harland/build/debug/harland.elf",
        "projects/harland/build/debug/BOOTX64.EFI",
    ):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x7fELF")
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    ovmf = tmp_path / "OVMF_CODE.fd"
    ovmf.write_bytes(b"")
    return {
        "root": root,
        "script": tools / "test_ahci_boot.sh",
        "stubs": stubs,
        "ovmf": ovmf,
        "tmp": tmp_path,
    }


def _stub(stubs: Path, name: str, body: str) -> None:
    p = stubs / name
    p.write_text(body)
    p.chmod(0o755)


def _run(tree, serial: str = "", *, qemu=True, env_extra=None) -> subprocess.CompletedProcess:
    stubs = tree["stubs"]
    if qemu:
        _stub(stubs, "qemu-system-x86_64", QEMU_STUB)
        path = f"{stubs}{os.pathsep}{os.environ['PATH']}"
    else:
        for tool in ("dirname", "python3"):
            os.symlink(shutil.which(tool), stubs / tool)
        path = str(stubs)
    env = {
        "PATH": path,
        "HOME": str(tree["tmp"]),
        "SKIP_BUILD": "1",
        "BOOT_TIMEOUT": "3",
        "OVMF_CODE": str(tree["ovmf"]),
        "STUB_LOG": str(tree["tmp"] / "stub.log"),
        "FAKE_SERIAL": serial,
        **(env_extra or {}),
    }
    return subprocess.run(
        ["/bin/bash", str(tree["script"])],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.mark.integration
def test_missing_qemu_is_a_setup_error(tree):
    r = _run(tree, qemu=False)
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr
    assert "SETUP ERROR" in r.stderr and "qemu-system-x86_64" in r.stderr


@pytest.mark.integration
def test_identify_lines_pass(tree):
    r = _run(tree, IDENTIFY)
    assert r.returncode == 0, r.stdout + r.stderr
    argv = (tree["tmp"] / "stub.log").read_text()
    assert "q35" in argv
    assert "-nodefaults" in argv
    assert "virtio-blk" not in argv
    assert "serial=harland-root" in argv
    assert "serial=harland-data" in argv
    assert argv.index("harland-root") < argv.index("harland-data")


@pytest.mark.integration
def test_wrong_sector_count_fails(tree):
    bad = ROOT_LINE.replace("2048", "2047") + DATA_LINE + SUMMARY
    r = _run(tree, bad)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL: port 0" in r.stdout


@pytest.mark.integration
def test_exception_fails(tree):
    r = _run(tree, "EXCEPTION: #GP\n" + IDENTIFY)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL: kernel exception" in r.stdout


@pytest.mark.integration
def test_empty_controller_passes_with_no_port_line(tree):
    r = _run(tree, EMPTY, env_extra={"AHCI_EMPTY": "1"})
    assert r.returncode == 0, r.stdout + r.stderr
    argv = (tree["tmp"] / "stub.log").read_text()
    assert "ide-hd" not in argv


@pytest.mark.integration
def test_empty_controller_fails_when_a_port_line_is_logged(tree):
    r = _run(tree, "[ahci] 00:1f.2 port 2: ATAPI, skipped\n" + EMPTY,
             env_extra={"AHCI_EMPTY": "1"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL: empty controller logged a port line" in r.stdout
