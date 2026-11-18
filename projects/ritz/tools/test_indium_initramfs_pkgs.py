#!/usr/bin/env python3
"""One list of the packages in indium's initramfs (AGAST #2759).

init's Tier-1 suite spawns binaries from several packages: indium's own,
rzsh, and prism's hello_gfx.  `make -C projects/indium run-uefi` packed
indium's build/debug only, so hello_gfx was missing and the suite reported
"hello_gfx ... FAIL (spawn error)", while harland/tools/test_tier1_boot.sh,
which kept its own USER_PKGS list, passed.

The package list now lives in projects/indium/initramfs.pkgs.  These tests
pin it:

  * every /bin/NAME that init.ritz spawns is a [[bin]] of a listed package;
  * every consumer (indium's Makefile and tools/mkiso.sh, harland's
    test_tier1_boot.sh, test_boot.sh and boot/test.sh) reads the file and keeps no list
    of its own;
  * `make -n build/initramfs.tar` builds and stages exactly the listed
    packages, and packs the staged directory.

Run with:
    python3 -m pytest projects/ritz/tools/test_indium_initramfs_pkgs.py -q
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
PROJECTS = REPO / "projects"
INDIUM = PROJECTS / "indium"
PKGS_FILE = INDIUM / "initramfs.pkgs"
CONSUMERS = (
    INDIUM / "Makefile",
    INDIUM / "tools" / "mkiso.sh",
    PROJECTS / "harland" / "tools" / "test_tier1_boot.sh",
    PROJECTS / "harland" / "tools" / "test_boot.sh",
    PROJECTS / "harland" / "boot" / "test.sh",
)


def read_pkgs() -> list[str]:
    """Packages in initramfs.pkgs: one per line, `#` starts a comment."""
    pkgs = []
    for line in PKGS_FILE.read_text().splitlines():
        pkgs.extend(line.split("#", 1)[0].split())
    return pkgs


def package_bins(pkg: str) -> set[str]:
    manifest = tomllib.loads((PROJECTS / pkg / "ritz.toml").read_text())
    return {b["name"] for b in manifest.get("bin", [])}


def test_pkgs_file_lists_real_packages():
    pkgs = read_pkgs()
    assert pkgs, f"{PKGS_FILE} lists no packages"
    assert len(pkgs) == len(set(pkgs)), f"duplicate package in {PKGS_FILE}: {pkgs}"
    for pkg in pkgs:
        assert (PROJECTS / pkg / "ritz.toml").is_file(), (
            f"{pkg}: no projects/{pkg}/ritz.toml"
        )


def test_every_binary_init_spawns_is_packed():
    """The #2759 bug: init spawns /bin/hello_gfx, which only prism builds."""
    spawned = set(
        re.findall(
            r'c"/bin/([A-Za-z0-9_.]+)"', (INDIUM / "user" / "init.ritz").read_text()
        )
    )
    assert "hello_gfx" in spawned and "rzsh" in spawned, spawned
    packed: set[str] = set()
    for pkg in read_pkgs():
        packed |= package_bins(pkg)
    missing = sorted(spawned - packed)
    assert not missing, (
        f"init.ritz spawns {missing}, built by no package in {PKGS_FILE.name}"
    )


@pytest.mark.parametrize("consumer", CONSUMERS, ids=lambda p: p.name)
def test_consumers_read_the_shared_list(consumer: Path):
    # Code only: a comment naming initramfs.pkgs is not a read of it.
    code = "\n".join(
        ln
        for ln in consumer.read_text().splitlines()
        if not ln.lstrip().startswith("#")
    )
    # Each consumer strips comments with sed, the reader read_pkgs() mirrors.
    assert re.search(r"\bsed\b[^\n]*initramfs\.pkgs", code), (
        f"{consumer} does not read initramfs.pkgs"
    )
    # No list of its own: no USER_PKGS="..." literal, no `for x in <names>`
    # loop over listed packages, no hand-written `rz build <pkg>` for a listed
    # package other than the consumer's own.
    assert not re.search(r'USER_PKGS="[a-z]', code), f"{consumer} hardcodes USER_PKGS"
    own = consumer.relative_to(PROJECTS).parts[0]
    for pkg in read_pkgs():
        assert not re.search(rf"\bfor\s+\w+\s+in\s+[^;$]*\b{pkg}\b", code), (
            f"{consumer} loops over its own list"
        )
        if pkg == own:
            continue
        assert not re.search(rf"\brz\S*\s+build\s+{pkg}\b", code), (
            f"{consumer} builds {pkg} by hand"
        )


@pytest.mark.skipif(shutil.which("make") is None, reason="make not installed")
def test_make_initramfs_builds_and_packs_the_listed_packages():
    out = subprocess.run(
        ["make", "-n", "-C", str(INDIUM), "-B", "build/initramfs.tar"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    # Exactly the listed packages are built and staged...
    loops = re.findall(r"for pkg in ([^;]*);", out)
    assert len(loops) == 1, out
    assert loops[0].split() == read_pkgs(), out
    assert re.search(r"rz build \$pkg\b", out), out
    # ...and the tar is packed from the staging dir, not indium's build/debug.
    pack = [
        ln for ln in out.splitlines() if "mkinitramfs.py" in ln or "--bin-dir" in ln
    ]
    assert any("build/initramfs-bin" in ln for ln in pack), out
    assert not any("build/debug" in ln for ln in pack), out
