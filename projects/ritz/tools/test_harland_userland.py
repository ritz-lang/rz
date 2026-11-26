#!/usr/bin/env python3
"""One harland userland (AGAST #1871).

Harland is the kernel; indium is the distribution and owns every userspace
program and image tool.  Before #1871:

  * harland/user was a stale second copy of indium/user (22 shared file
    names), still built by harland/build.py;
  * `sys_open(path, flags)` was redefined in four userland files, each
    passing strlen, because ritzlib defined it for linux only;
  * rzsh kept main_linux.ritz and main_harland.ritz, imported by nothing
    since os.ritz's [[target_os]] split replaced them;
  * harland/tools and indium/tools held diverged copies of mkimage.py,
    mkiso.sh and mkboot.sh;
  * `cp ... 2>/dev/null || true` in indium's Makefile and tools let an
    image build without rzsh.

These tests pin each of those.  The mkiso.sh cases run the real script
against fake packages, a fake `rz` and fake grub-mkrescue/qemu-img, so they
cost a few shell processes and no compiler run.

Run with:
    python3 -m pytest projects/ritz/tools/test_harland_userland.py -q
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import tarfile
from pathlib import Path

import pytest

# git grep and real mkiso.sh runs spawn processes (AGAST #1805).
pytestmark = pytest.mark.integration

REPO = Path(__file__).resolve().parents[3]
PROJECTS = REPO / "projects"
HARLAND = PROJECTS / "harland"
INDIUM = PROJECTS / "indium"
RZSH = PROJECTS / "rzsh"
SYS_RITZ = PROJECTS / "ritz" / "ritzlib" / "sys.ritz"
MKISO = INDIUM / "tools" / "mkiso.sh"


def git_grep(*args: str) -> list[str]:
    out = subprocess.run(
        ["git", "grep", "-n", *args], cwd=REPO, capture_output=True, text=True
    )
    assert out.returncode in (0, 1), out.stderr
    return out.stdout.splitlines()


# --- one sys_open: ritzlib's -----------------------------------------------------


def test_no_userland_sys_open():
    """Acceptance (a), over code: only ritzlib (and the kernel's own handler)
    defines sys_open.  Markdown quoting a definition is not one."""
    hits = git_grep(
        "-E",
        r"^(pub )?fn sys_(open|close)\(",
        "--",
        "projects/*.ritz",
        ":!projects/ritz/ritzlib",
        ":!projects/harland/kernel",
        ":!*archive*",
        ":!projects/ritz/ritz1/bootstrap_ritzlib",
    )
    assert not hits, "sys_open/sys_close redefined outside ritzlib:\n" + "\n".join(hits)


def _harland_fns(src: str) -> dict[str, str]:
    """{name: body} of each fn a harland build of ritzlib/sys.ritz sees."""
    fns = {}
    lines = src.splitlines()
    attr = None
    for i, line in enumerate(lines):
        a = re.match(r'^\[\[target_os\s*=\s*"(\w+)"\]\]', line)
        if a:
            attr = a.group(1)
            continue
        m = re.match(r"^pub fn (\w+)\(", line)
        if m and attr in (None, "harland"):
            body = [line]
            for nxt in lines[i + 1 :]:
                if nxt and not nxt[0].isspace():
                    break
                body.append(nxt)
            fns[m.group(1)] = "\n".join(body)
        if line.strip() and not line.startswith("#") and not line.startswith("["):
            attr = None
    return fns


def test_ritzlib_has_harland_sys_open_and_close():
    """Harland's open takes (path, path_len, flags, mode): the wrapper passes
    the length (and 0644, AGAST #4832), so callers keep the (path, flags)
    signature linux has."""
    fns = _harland_fns(SYS_RITZ.read_text())
    assert "sys_open" in fns and "sys_close" in fns, sorted(fns)
    assert re.search(r"syscall4\(SYS_OPEN, path as i64, \w+, flags as i64, 420\)", fns["sys_open"]), (
        fns["sys_open"]
    )
    assert "syscall1(SYS_CLOSE, fd as i64)" in fns["sys_close"], fns["sys_close"]


# What libharland no longer exports: ritzlib.sys owns them.
MOVED_TO_RITZLIB = {
    "sys_open",
    "sys_close",
    "O_RDONLY",
    "O_WRONLY",
    "O_RDWR",
    "O_CREAT",
    "O_TRUNC",
    "O_APPEND",
}


def test_no_program_imports_open_from_libharland():
    """A user program that lands after #1871 still importing sys_open or an
    O_* flag from libharland (as #2761's heap_grow_child did) fails here by
    name, rather than as `PKG FAIL indium` deep in the workspace build."""
    bad = []
    for hit in git_grep("-E", r"^import libharland \{", "--", "projects/*.ritz"):
        names = re.search(r"\{(.*)\}", hit).group(1)
        moved = MOVED_TO_RITZLIB & {n.strip() for n in names.split(",")}
        if moved:
            bad.append(f"{hit}  <- import {sorted(moved)} from ritzlib.sys")
    assert not bad, "\n".join(bad)


# --- one userland: indium's ------------------------------------------------------


def test_harland_has_no_userland():
    """Acceptance (b): harland/user and its second build system are both
    gone; indium owns userspace and the Makefile uses `rz build`."""
    assert not (HARLAND / "user").exists()
    assert not (HARLAND / "build.py").exists()
    assert not (HARLAND / "ritz").exists()


def test_rzsh_dead_mains_deleted():
    """Acceptance (b): os.ritz's [[target_os]] split replaced them."""
    for name in ("main_linux.ritz", "main_harland.ritz"):
        assert not (RZSH / "src" / name).exists(), name


def test_one_copy_of_the_image_tools():
    """indium owns the image tools; harland keeps none of its own."""
    for name in ("mkimage.py", "mkiso.sh", "mkboot.sh"):
        assert (INDIUM / "tools" / name).is_file(), name
        assert not (HARLAND / "tools" / name).exists(), f"harland/tools/{name}"
    refs = git_grep(r"harland/tools/mk\(image\|iso\|boot\)", "--", "projects", ":!*archive*", ":!projects/larb")
    assert not refs, "\n".join(refs)


def test_indium_image_build_swallows_no_errors():
    """Acceptance (c): no `|| true` in indium's Makefile or tools."""
    hits = git_grep("|| true", "--", "projects/indium/Makefile", "projects/indium/tools")
    assert not hits, "\n".join(hits)


# --- a missing binary fails the image build --------------------------------------


def _exe(path: Path, body: str) -> None:
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


@pytest.fixture
def fake_world(tmp_path: Path):
    """A packages root with one ELF per initramfs package, a fake `rz` that
    logs and fails for any package named in $FAIL_PKGS, and fake
    grub-mkrescue / qemu-img on PATH."""
    pkgs_root = tmp_path / "pkgs"
    pkgs = [
        ln.split("#", 1)[0].strip()
        for ln in (INDIUM / "initramfs.pkgs").read_text().splitlines()
        if ln.split("#", 1)[0].strip()
    ]
    assert "rzsh" in pkgs, pkgs
    for pkg in pkgs:
        d = pkgs_root / pkg / "build" / "debug"
        d.mkdir(parents=True)
        (d / f"{pkg}.elf").write_bytes(b"\x7fELF fake")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    log = tmp_path / "rz.log"
    rz = bindir / "rz"
    _exe(rz, f'echo "$*" >> {log}\nfor p in $FAIL_PKGS; do [ "$2" = "$p" ] && exit 1; done\nexit 0\n')
    # grub-mkrescue -o ISO ...: write the ISO it was asked for.
    _exe(bindir / "grub-mkrescue", 'echo iso > "$2"\n')
    # qemu-img convert ... SRC DST: write DST.
    _exe(bindir / "qemu-img", 'for a; do last=$a; done; echo qcow2 > "$last"\n')
    kernel = tmp_path / "harland.elf"
    kernel.write_bytes(b"\x7fELF kernel")
    build = tmp_path / "build"
    env = dict(
        os.environ,
        PATH=f"{bindir}:{os.environ['PATH']}",
        RZ_CLI=str(rz),
        PKGS_ROOT=str(pkgs_root),
        KERNEL_ELF=str(kernel),
        BUILD_DIR=str(build),
        FAIL_PKGS="",
    )
    return {"env": env, "log": log, "pkgs_root": pkgs_root, "build": build, "pkgs": pkgs}


def _mkiso(world) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(MKISO)], env=world["env"], capture_output=True, text=True, timeout=120
    )


def test_mkiso_builds_with_every_package(fake_world):
    """Control: with every package built, the harness reaches the ISO, so the
    failures below fail for the reason they name."""
    r = _mkiso(fake_world)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (fake_world["build"] / "indium.iso").is_file()
    staged = sorted(p.name for p in (fake_world["build"] / "initramfs-bin").iterdir())
    assert staged == sorted(f"{p}.elf" for p in fake_world["pkgs"])


def test_mkiso_loads_the_initramfs_as_a_multiboot2_module(fake_world):
    """AGAST #4258: the ISO carries the raw TAR and GRUB loads it with
    module2 after the kernel, so it boots with no virtio-blk disk."""
    r = _mkiso(fake_world)
    assert r.returncode == 0, r.stdout + r.stderr
    isodir = fake_world["build"] / "isodir" / "boot"
    tar = isodir / "initramfs.tar"
    assert tar.is_file() and tarfile.is_tarfile(tar)
    cfg = (isodir / "grub" / "grub.cfg").read_text()
    lines = [ln.strip() for ln in cfg.splitlines()]
    assert "module2 /boot/initramfs.tar" in lines
    assert lines.index("multiboot2 /boot/harland.elf") < lines.index(
        "module2 /boot/initramfs.tar"
    ) < lines.index("boot")


def test_mkiso_fails_when_rzsh_fails_to_build(fake_world):
    fake_world["env"]["FAIL_PKGS"] = "rzsh"
    r = _mkiso(fake_world)
    assert r.returncode != 0, r.stdout + r.stderr
    assert "build rzsh" in fake_world["log"].read_text()
    assert not (fake_world["build"] / "indium.iso").exists()


def test_mkiso_fails_when_rzsh_builds_no_elf(fake_world):
    (fake_world["pkgs_root"] / "rzsh" / "build" / "debug" / "rzsh.elf").unlink()
    r = _mkiso(fake_world)
    assert r.returncode != 0, r.stdout + r.stderr
    assert "build rzsh" in fake_world["log"].read_text()
    assert not (fake_world["build"] / "indium.iso").exists()

