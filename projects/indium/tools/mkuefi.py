#!/usr/bin/env python3
"""Build a UEFI boot disk image with explicit per-step timing/logging.

Usage:
  mkuefi.py <image> <bootloader> <kernel> <startup_nsh>
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path


def log(msg: str) -> None:
    print(f"[mkuefi] {msg}", flush=True)


def run_step(
    label: str,
    cmd: list[str],
    timeout_s: int,
    trace: bool,
    env: Mapping[str, str] | None = None,
) -> None:
    start = time.time()
    log(f"start: {label}")
    if trace:
        log("cmd: " + " ".join(cmd))
    subprocess.run(cmd, check=True, timeout=timeout_s, env=env)
    elapsed = int(time.time() - start)
    log(f"done: {label} ({elapsed}s)")


def create_zero_image(image: Path, size_mib: int, trace: bool) -> None:
    start = time.time()
    log("start: zero image")
    if trace:
        log(f"cmd: python-zero-fill of={image} size={size_mib}MiB")
    with image.open("wb") as fp:
        fp.truncate(size_mib * 1024 * 1024)
    elapsed = int(time.time() - start)
    log(f"done: zero image ({elapsed}s)")


def main() -> int:
    if len(sys.argv) != 5:
        print("usage: mkuefi.py <image> <bootloader> <kernel> <startup_nsh>", file=sys.stderr)
        return 2

    image = Path(sys.argv[1])
    bootloader = Path(sys.argv[2])
    kernel = Path(sys.argv[3])
    startup_nsh = Path(sys.argv[4])

    timeout_s = int(os.environ.get("UEFI_STEP_TIMEOUT", "120"))
    trace = os.environ.get("UEFI_TRACE", "1") == "1"

    mtools_env = os.environ.copy()
    mtools_env["MTOOLS_SKIP_CHECK"] = "1"

    create_zero_image(image, 64, trace)
    run_step("mkfs vfat", ["mkfs.vfat", "-F", "32", "-I", str(image)], timeout_s, trace)

    run_step("mkdir EFI", ["mmd", "-i", str(image), "::/EFI"], timeout_s, trace, env=mtools_env)
    run_step("mkdir EFI/BOOT", ["mmd", "-i", str(image), "::/EFI/BOOT"], timeout_s, trace, env=mtools_env)
    run_step("mkdir harland", ["mmd", "-i", str(image), "::/harland"], timeout_s, trace, env=mtools_env)

    run_step(
        "copy BOOTX64.EFI",
        ["mcopy", "-i", str(image), str(bootloader), "::/EFI/BOOT/BOOTX64.EFI"],
        timeout_s,
        trace,
        env=mtools_env,
    )
    run_step(
        "copy kernel",
        ["mcopy", "-i", str(image), str(kernel), "::/harland/kernel.elf"],
        timeout_s,
        trace,
        env=mtools_env,
    )
    run_step(
        "copy startup.nsh",
        ["mcopy", "-i", str(image), str(startup_nsh), "::/startup.nsh"],
        timeout_s,
        trace,
        env=mtools_env,
    )

    log(f"created: {image}")
    return 0


if __name__ == "__main__":
    # Keep mtools checks disabled for regular image files.
    os.environ.setdefault("MTOOLS_SKIP_CHECK", "1")
    raise SystemExit(main())
