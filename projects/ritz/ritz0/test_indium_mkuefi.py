"""indium builds its UEFI boot disk with tools/mkuefi.py, never dd (AGAST #2748, from #1844).

The `$(UEFI_DISK)` recipe in projects/indium/Makefile and harland's
boot/test.sh zero-filled images with `dd if=/dev/zero`. On origin/harland-main
those dd steps hung the image build and the boot test (24879891), so the branch
replaced them: indium's disk comes from tools/mkuefi.py (sparse truncate +
mkfs.vfat + mtools, each step logged and time-limited) and test.sh uses
truncate/cp.

These tests pin that down:

* mkuefi.py builds a FAT image holding BOOTX64.EFI, harland/kernel.elf and
  startup.nsh byte-for-byte, without running dd;
* a failed step exits non-zero and leaves no image behind, so make cannot
  mistake a half-built disk for an up-to-date one;
* mkfs.vfat is found in /usr/sbin or /sbin when they are not on PATH (the
  usual case for a non-root shell);
* the Makefile recipe and test.sh no longer call dd.
"""

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).resolve().parent
PROJECTS = RITZ0_DIR.parent.parent
MKUEFI = PROJECTS / "indium" / "tools" / "mkuefi.py"
INDIUM_MAKEFILE = PROJECTS / "indium" / "Makefile"
HARLAND_BOOT_TEST = PROJECTS / "harland" / "boot" / "test.sh"


def _have(tool):
    return shutil.which(tool) or any(Path(d, tool).exists() for d in ("/usr/sbin", "/sbin"))


needs_tools = pytest.mark.skipif(
    not (_have("mkfs.vfat") and shutil.which("mcopy") and shutil.which("mdir")),
    reason="mkfs.vfat / mtools not installed",
)


def _inputs(tmp_path):
    boot = tmp_path / "BOOTX64.EFI"
    kernel = tmp_path / "kernel.elf"
    nsh = tmp_path / "startup.nsh"
    boot.write_bytes(b"MZ" + os.urandom(4096))
    kernel.write_bytes(b"\x7fELF" + os.urandom(70000))
    nsh.write_text("@echo -off\nFS0:\\EFI\\BOOT\\BOOTX64.EFI\n")
    return boot, kernel, nsh


def _spy_bin(tmp_path):
    """A PATH dir whose `dd` records that it ran and fails."""
    spy = tmp_path / "spybin"
    spy.mkdir()
    dd = spy / "dd"
    dd.write_text(f"#!/bin/sh\necho called >> {tmp_path / 'dd_called'}\nexit 1\n")
    dd.chmod(dd.stat().st_mode | stat.S_IEXEC)
    return spy


def _run(args, tmp_path, path_dirs):
    env = dict(os.environ, PATH=os.pathsep.join(str(d) for d in path_dirs), MTOOLS_SKIP_CHECK="1")
    return subprocess.run(
        [sys.executable, str(MKUEFI), *map(str, args)],
        capture_output=True, text=True, timeout=120, env=env,
    )


def _mtools_path():
    """PATH holding mtools but NOT the sbin dirs (mkfs.vfat must be found by fallback)."""
    dirs = []
    for tool in ("mcopy", "mmd", "mdir"):
        d = Path(shutil.which(tool)).parent
        if d not in dirs:
            dirs.append(d)
    return [d for d in dirs if d.name != "sbin"]


@pytest.mark.integration
@needs_tools
def test_builds_image_with_all_three_files_and_no_dd(tmp_path):
    boot, kernel, nsh = _inputs(tmp_path)
    image = tmp_path / "out" / "uefi.img"
    image.parent.mkdir()
    spy = _spy_bin(tmp_path)

    r = _run([image, boot, kernel, nsh], tmp_path, [spy, *_mtools_path(), Path("/bin"), Path("/usr/bin")])
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (tmp_path / "dd_called").exists(), "mkuefi.py ran dd"
    assert image.stat().st_size == 64 * 1024 * 1024

    for src, dst in ((boot, "::/EFI/BOOT/BOOTX64.EFI"), (kernel, "::/harland/kernel.elf"), (nsh, "::/startup.nsh")):
        out = tmp_path / ("copy_" + src.name)
        subprocess.run(["mcopy", "-n", "-i", str(image), dst, str(out)], check=True,
                       env=dict(os.environ, MTOOLS_SKIP_CHECK="1"), timeout=60)
        assert out.read_bytes() == src.read_bytes(), f"{dst} differs from {src.name}"


@pytest.mark.integration
@needs_tools
def test_failed_step_leaves_no_image(tmp_path):
    """mkfs and mmd succeed, then mcopy fails: the image is half built at that point."""
    boot, kernel, nsh = _inputs(tmp_path)
    image = tmp_path / "out" / "uefi.img"
    image.parent.mkdir()
    spy = tmp_path / "failbin"
    spy.mkdir()
    mcopy = spy / "mcopy"
    mcopy.write_text("#!/bin/sh\necho 'mcopy: disk full' >&2\nexit 1\n")
    mcopy.chmod(mcopy.stat().st_mode | stat.S_IEXEC)

    r = _run([image, boot, kernel, nsh], tmp_path, [spy, *_mtools_path(), Path("/bin"), Path("/usr/bin")])
    assert r.returncode != 0
    assert "start: mkfs vfat" in r.stdout, "failure came before the image existed:\n" + r.stdout
    assert not image.exists(), "a half-built image was left for make to treat as up to date"
    assert list(image.parent.iterdir()) == [], "temporary image left behind"


@pytest.mark.integration
@needs_tools
def test_killed_build_leaves_no_image(tmp_path):
    """SIGKILL mid-build (make's timeout, Ctrl-C twice) runs no cleanup; the
    image must still not appear under its real name."""
    boot, kernel, nsh = _inputs(tmp_path)
    image = tmp_path / "out" / "uefi.img"
    image.parent.mkdir()
    spy = tmp_path / "hangbin"
    spy.mkdir()
    mcopy = spy / "mcopy"
    mcopy.write_text("#!/bin/sh\nsleep 60\n")
    mcopy.chmod(mcopy.stat().st_mode | stat.S_IEXEC)

    env = dict(os.environ, MTOOLS_SKIP_CHECK="1",
               PATH=os.pathsep.join(map(str, [spy, *_mtools_path(), "/bin", "/usr/bin"])))
    p = subprocess.Popen([sys.executable, str(MKUEFI), str(image), str(boot), str(kernel), str(nsh)],
                         stdout=subprocess.PIPE, text=True, env=env, start_new_session=True)
    try:
        for line in p.stdout:
            if "start: copy BOOTX64.EFI" in line:
                break
        else:
            pytest.fail("mkuefi.py never reached the copy step")
        os.killpg(p.pid, 9)
        p.wait(timeout=10)
    finally:
        if p.poll() is None:
            os.killpg(p.pid, 9)
    assert not image.exists(), "a killed build left a half-written image under the real name"


@pytest.mark.integration
@needs_tools
def test_missing_input_fails(tmp_path):
    boot, _kernel, nsh = _inputs(tmp_path)
    image = tmp_path / "uefi.img"
    r = _run([image, boot, tmp_path / "no_such_kernel.elf", nsh], tmp_path,
             [*_mtools_path(), Path("/bin"), Path("/usr/bin")])
    assert r.returncode == 1
    assert "no_such_kernel.elf" in r.stdout
    assert not image.exists()


@pytest.mark.integration
def test_usage_error(tmp_path):
    r = _run(["only-one-arg"], tmp_path, [Path("/bin"), Path("/usr/bin")])
    assert r.returncode == 2
    assert "usage" in r.stderr


def _recipe(makefile_text, target):
    lines = makefile_text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith(target + ":"))
    body = []
    for l in lines[start + 1:]:
        if not l.startswith("\t"):
            break
        body.append(l)
    return "\n".join(body)


def test_indium_uefi_disk_recipe_uses_mkuefi_not_dd():
    recipe = _recipe(INDIUM_MAKEFILE.read_text(), "$(UEFI_DISK)")
    assert "tools/mkuefi.py" in recipe
    assert "dd " not in recipe and "mkfs.vfat" not in recipe and "mcopy" not in recipe


def test_harland_boot_test_has_no_dd():
    code = [l for l in HARLAND_BOOT_TEST.read_text().splitlines() if not l.lstrip().startswith("#")]
    hits = [l for l in code if l.lstrip().startswith("dd ") or " dd if=" in l]
    assert not hits, "boot/test.sh still calls dd:\n" + "\n".join(hits)
