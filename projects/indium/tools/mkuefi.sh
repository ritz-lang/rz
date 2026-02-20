#!/usr/bin/env bash
set -euo pipefail

# Build a UEFI boot disk image with explicit step logging/timing.
# Usage:
#   mkuefi.sh <image> <bootloader> <kernel> <startup_nsh>

if [[ $# -ne 4 ]]; then
    echo "usage: $0 <image> <bootloader> <kernel> <startup_nsh>" >&2
    exit 2
fi

IMAGE="$1"
BOOTLOADER="$2"
KERNEL="$3"
STARTUP_NSH="$4"

STEP_TIMEOUT="${UEFI_STEP_TIMEOUT:-120}"
TRACE="${UEFI_TRACE:-1}"

log() {
    echo "[mkuefi] $*"
}

run_step() {
    local label="$1"
    shift
    local start end
    start="$(date +%s)"
    log "start: ${label}"
    if [[ "${TRACE}" == "1" ]]; then
        log "cmd: $*"
    fi
    timeout "${STEP_TIMEOUT}s" "$@"
    end="$(date +%s)"
    log "done: ${label} (${end-start}s)"
}

run_step "zero image" dd if=/dev/zero of="${IMAGE}" bs=1M count=64
run_step "mkfs vfat" mkfs.vfat -F 32 -I "${IMAGE}"

run_step "mkdir EFI" env MTOOLS_SKIP_CHECK=1 mmd -i "${IMAGE}" ::/EFI
run_step "mkdir EFI/BOOT" env MTOOLS_SKIP_CHECK=1 mmd -i "${IMAGE}" ::/EFI/BOOT
run_step "mkdir harland" env MTOOLS_SKIP_CHECK=1 mmd -i "${IMAGE}" ::/harland

run_step "copy BOOTX64.EFI" env MTOOLS_SKIP_CHECK=1 mcopy -i "${IMAGE}" "${BOOTLOADER}" ::/EFI/BOOT/BOOTX64.EFI
run_step "copy kernel" env MTOOLS_SKIP_CHECK=1 mcopy -i "${IMAGE}" "${KERNEL}" ::/harland/kernel.elf
run_step "copy startup.nsh" env MTOOLS_SKIP_CHECK=1 mcopy -i "${IMAGE}" "${STARTUP_NSH}" ::/startup.nsh

log "created: ${IMAGE}"
