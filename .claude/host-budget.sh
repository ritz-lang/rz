#!/usr/bin/env bash
#
# One machine budget for task rooms and the gate (AGAST #1811).
#
#   .claude/host-budget.sh <room>            install (idempotent); before `systemctl start`
#   .claude/host-budget.sh --verify <room>   check only, no writes
#   .claude/host-budget.sh --remove <room>   drop the room's drop-in (reap)
#
#   <room> is the adele room / unit instance, e.g. ritz-task-1811.
#
# Env override (tests): RZ_SYSTEMD_USER_DIR   (default ~/.config/systemd/user)
#
# ---------------------------------------------------------------------------
# WHY
# ---------------------------------------------------------------------------
# The gate's wall time doubled in a week (21 -> 44-54 min; the pure-Python
# tools-unit suite 45 s -> 75-107 s) with no code to blame: task rooms were
# building and testing unthrottled next to it on the 12-core / 15 GB WSL VM.
# run-gate.sh's slot serialises gates against gates only.  Aaron chose option
# (b): rooms run deprioritised under a memory cap, the gate runs at full
# weight in its own slice.  No shared slot semaphore (it would add queueing).
#
# ---------------------------------------------------------------------------
# WHAT IT INSTALLS (user manager, cgroup v2; cpu+memory are delegated)
# ---------------------------------------------------------------------------
#   user@1000.service/
#     app.slice/ ...              other agents, rz, unchanged          CPUWeight 100
#     ritz.slice/                 implicit parent (dash = nesting)     CPUWeight 100
#       ritz-gate.slice/          run-gate.sh --slice=ritz-gate.slice  CPUWeight 100
#       ritz-rooms.slice/         every ritz task room                 CPUWeight  20
#         adele-agent@ritz-task-N.service    MemoryHigh/MemoryMax per room
#
# CPU weight is only compared between SIBLINGS.  That is why the gate and the
# rooms must share a parent: a room at CPUWeight=20 inside
# app-adele\x2dagent.slice would only lose to the other agents, and the gate
# in app.slice would be weighed against that whole slice (100 vs 100), not
# against the rooms.  systemd nests `ritz-gate.slice` and `ritz-rooms.slice`
# under `ritz.slice` (measured: the gate's cgroup is
# user@1000.service/ritz.slice/ritz-gate.slice/ritz-gate-<name>.service), so
# under contention the gate gets 100/120 of ritz's share, 5x a room's.
#
# ---------------------------------------------------------------------------
# PER ROOM, NOT PER COMMAND
# ---------------------------------------------------------------------------
# A per-command wrapper (`systemd-run --scope ... make`) only throttles the
# commands that remember to use it; an agent that runs `make` or `pytest`
# directly bypasses it.  A drop-in on the room's own unit moves the whole room
# (agent, shells, compilers, tests) into ritz-rooms.slice: everything it runs
# inherits the cgroup.  Escaping takes a deliberate `systemd-run --user`.
#
# It has to be one drop-in per instance: systemd's dash-prefix drop-ins
# (`foo-.service.d`) do NOT match template instances.  Measured on systemd
# 259: `budgetprobe@ritz-task-.service.d/` left `budgetprobe@ritz-task-9`
# with DropInPaths= empty.  And `adele-agent@.service.d/` would also cap the
# non-ritz agents.
#
# The drop-in takes effect when the unit (re)starts.  Run this before
# `systemctl --user start adele-agent@<room>.service`.
#
# ---------------------------------------------------------------------------
# THE NUMBERS (measured; see AGAST #1811 for the run)
# ---------------------------------------------------------------------------
# VM: 15.6 GiB RAM + 4 GiB swap.  Idle agent (claude + adele) ~0.2-0.7 GiB.
# Room cgroup peaks seen: rz 4.5 GiB, rz-larb 4.2 GiB (agent + a full build).
# Clean `make ci-local` in its own cgroup, 2026-10-25 (RC=0, 3040 s wall
# under contention): memory.peak 3496 MB, of which anon 3174 MB (regression
# Stage 3); swap peak 0.  So a room running a full ci-local itself needs
# ~3.2 GiB + its ~0.6 GiB agent: a 4G hard cap would OOM it, hence 5G.
GATE_PEAK_MB=3500         # gate memory.peak above, rounded up
ROOM_MEMORY_HIGH=3500M    # above this a room is throttled and reclaimed to swap
ROOM_MEMORY_MAX=5G        # hard cap: the kernel OOM-kills inside the room only
ROOMS_MEMORY_HIGH=7G      # all rooms together: 2 rooms at their soft limit
ROOMS_MEMORY_MAX=8G       # all rooms together, however many are running
# 8G rooms + 3.5G gate leaves ~4G for rz, the other agents and page cache;
# the 4G of swap absorbs the overlap.  Page cache counts against these
# limits too, but the kernel reclaims it first.
# MemoryHigh < MemoryMax so a room slows down long before anything is killed.
# OOMPolicy=continue: the default (stop) would take the whole room, agent
# included, down when one compiler is OOM-killed inside the cap.
ROOM_CPU_WEIGHT=20
GATE_CPU_WEIGHT=100
set -euo pipefail

UNITS="${RZ_SYSTEMD_USER_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user}"
MODE=install
case "${1:-}" in
    --verify) MODE=verify; shift ;;
    --remove) MODE=remove; shift ;;
esac
if [[ $# -ne 1 ]]; then
    echo "usage: $0 [--verify|--remove] <room>" >&2
    exit 2
fi
ROOM="$1"
# The name becomes a path and a unit instance: no '/', '@', spaces, no
# leading '-' or '.'.
if [[ ! "$ROOM" =~ ^[A-Za-z0-9_][A-Za-z0-9_.-]*$ ]]; then
    echo "error: bad room name: '$ROOM'" >&2
    exit 2
fi

DROPIN_DIR="$UNITS/adele-agent@$ROOM.service.d"
DROPIN="$DROPIN_DIR/50-ritz-host-budget.conf"

ROOMS_SLICE_BODY="# Installed by .claude/host-budget.sh (AGAST #1811). Do not edit by hand.
[Unit]
Description=ritz task rooms: deprioritised, memory-capped

[Slice]
CPUWeight=$ROOM_CPU_WEIGHT
MemoryHigh=$ROOMS_MEMORY_HIGH
MemoryMax=$ROOMS_MEMORY_MAX"

GATE_SLICE_BODY="# Installed by .claude/host-budget.sh (AGAST #1811). Do not edit by hand.
[Unit]
Description=ritz verification gate (run-gate.sh): full CPU weight, no memory cap

[Slice]
CPUWeight=$GATE_CPU_WEIGHT"

DROPIN_BODY="# Installed by .claude/host-budget.sh (AGAST #1811). Do not edit by hand.
# Removed on reap with: .claude/host-budget.sh --remove $ROOM
[Service]
Slice=ritz-rooms.slice
MemoryHigh=$ROOM_MEMORY_HIGH
MemoryMax=$ROOM_MEMORY_MAX
OOMPolicy=continue"

# path:body pairs, compared byte for byte.
FILES=("$UNITS/ritz-rooms.slice" "$UNITS/ritz-gate.slice" "$DROPIN")
BODIES=("$ROOMS_SLICE_BODY" "$GATE_SLICE_BODY" "$DROPIN_BODY")

current() { [[ -f "$1" ]] && [[ "$(cat "$1")" == "$2" ]]; }

case "$MODE" in
verify)
    bad=0
    for i in "${!FILES[@]}"; do
        if ! current "${FILES[$i]}" "${BODIES[$i]}"; then
            echo "MISSING OR STALE: ${FILES[$i]}" >&2
            bad=1
        fi
    done
    if [[ $bad -ne 0 ]]; then
        echo "run: $0 $ROOM" >&2
        exit 1
    fi
    echo "host budget OK for $ROOM"
    ;;
remove)
    if [[ -e "$DROPIN" ]]; then
        rm -f "$DROPIN"
        rmdir "$DROPIN_DIR" 2>/dev/null || true
        systemctl --user daemon-reload
    fi
    echo "host budget removed for $ROOM (slices kept)"
    ;;
install)
    changed=0
    for i in "${!FILES[@]}"; do
        if ! current "${FILES[$i]}" "${BODIES[$i]}"; then
            mkdir -p "$(dirname "${FILES[$i]}")"
            printf '%s\n' "${BODIES[$i]}" > "${FILES[$i]}.tmp"
            mv -f "${FILES[$i]}.tmp" "${FILES[$i]}"
            changed=1
        fi
    done
    [[ $changed -eq 1 ]] && systemctl --user daemon-reload
    echo "host budget OK for $ROOM (ritz-rooms.slice: CPUWeight=$ROOM_CPU_WEIGHT," \
        "MemoryHigh=$ROOM_MEMORY_HIGH MemoryMax=$ROOM_MEMORY_MAX per room)"
    ;;
esac
