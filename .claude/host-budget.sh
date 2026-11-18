#!/usr/bin/env bash
#
# One machine budget for task rooms and the gate (AGAST #1811).
#
#   .claude/host-budget.sh <room>            install (idempotent); before `systemctl start`
#   .claude/host-budget.sh --verify <room>   check only, no writes
#   .claude/host-budget.sh --remove <room>   drop the room's drop-ins (reap)
#   .claude/host-budget.sh --room-memory <room> <high> <max>
#                                            raise/lower ONE room's caps (Aaron's OK)
#   .claude/host-budget.sh --clear-room-memory <room>
#                                            back to the per-room default
#
#   <room> is the adele room / unit instance, e.g. ritz-task-1811.
#
# Env overrides (tests): RZ_SYSTEMD_USER_DIR  (default ~/.config/systemd/user)
#                        RZ_SYSTEMD_CONTROL_DIR
#                                 (default $XDG_RUNTIME_DIR/systemd/user.control)
#                        RZ_HOST_ENV          (default ~/.config/rz/host.env)
#
# PER HOST (AGAST #2998): ~/.config/rz/host.env may set RZ_ROOMS_MEMORY_HIGH /
# RZ_ROOMS_MEMORY_MAX (the ritz-rooms.slice caps below) and RZ_GATE_SLOTS
# (run-gate.sh).  Format and rules: .claude/host-env.sh.  No file = the
# omegalisk defaults below, byte for byte.  --verify prints what is in effect.
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
GATE_SLOTS=1              # run-gate.sh's default; reported by --verify
CPU_FACTOR=measured       # the gate's default (AGAST #4172); reported by --verify
# The two ROOMS_ caps (and GATE_SLOTS) are omegalisk's: a host with more RAM
# overrides them in host.env.  huburght (47 GB, 6 rooms): 28G / 32G and 2
# gates; 32G rooms + 2 x 3.5G gates leaves ~8G for the host's own agents.
# 8G rooms + 3.5G gate leaves ~4G for rz, the other agents and page cache;
# the 4G of swap absorbs the overlap.  Page cache counts against these
# limits too, but the kernel reclaims it first.
# MemoryHigh < MemoryMax so a room slows down long before anything is killed.
# OOMPolicy=continue: the default (stop) would take the whole room, agent
# included, down when one compiler is OOM-killed inside the cap.
#
# PER-ROOM OVERRIDE (AGAST #3971): `--room-memory <room> <high> <max>` gives
# one room other caps, e.g. a survey that needs 12G.  `systemctl --user
# set-property --runtime` can NOT do this: it writes 50-MemoryHigh.conf /
# 50-MemoryMax.conf, which sort before 50-ritz-host-budget.conf, so the next
# daemon-reload (every --remove at a reap runs one) silently restores 5G.
# The override is a runtime drop-in, user.control/.../90-rz-room-memory.conf,
# which sorts after the budget file and so wins; it lives under /run, so a
# reboot drops it.  high <= max <= the ritz-rooms.slice MemoryMax: the slice
# cap is what protects the machine, and a room can never exceed it anyway.
ROOM_CPU_WEIGHT=20
GATE_CPU_WEIGHT=100
set -euo pipefail
# Borque's hostd runs this as a hook with a clean environment (AGAST #3722,
# .borque/profile.toml): maybe no HOME, PATH or XDG_RUNTIME_DIR.  Supply the
# standard ones; `systemctl --user` can't reach the user manager without the
# runtime dir.  Tests: projects/ritz/tools/test_borque_hooks.py.
: "${HOME:=$(getent passwd "$(id -u)" | cut -d: -f6)}"
: "${PATH:=/usr/local/bin:/usr/bin:/bin}"
: "${XDG_RUNTIME_DIR:=/run/user/$(id -u)}"
export HOME PATH XDG_RUNTIME_DIR
# shellcheck source=host-env.sh
source "$(dirname "${BASH_SOURCE[0]}")/host-env.sh"

UNITS="${RZ_SYSTEMD_USER_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user}"
CONTROL="${RZ_SYSTEMD_CONTROL_DIR:-$XDG_RUNTIME_DIR/systemd/user.control}"
MODE=install
case "${1:-}" in
    --verify) MODE=verify; shift ;;
    --remove) MODE=remove; shift ;;
    --room-memory) MODE=room-memory; shift ;;
    --clear-room-memory) MODE=clear-room-memory; shift ;;
esac
WANT=1
[[ "$MODE" == room-memory ]] && WANT=3
if [[ $# -ne $WANT ]]; then
    echo "usage: $0 [--verify|--remove|--clear-room-memory] <room>" >&2
    echo "       $0 --room-memory <room> <MemoryHigh> <MemoryMax>" >&2
    exit 2
fi
ROOM="$1"
# The name becomes a path and a unit instance: no '/', '@', spaces, no
# leading '-' or '.'.
if [[ ! "$ROOM" =~ ^[A-Za-z0-9_][A-Za-z0-9_.-]*$ ]]; then
    echo "error: bad room name: '$ROOM'" >&2
    exit 2
fi

if [[ "$MODE" == room-memory ]]; then
    OVR_HIGH="$2"
    OVR_MAX="$3"
    for v in "$OVR_HIGH" "$OVR_MAX"; do
        if [[ ! "$v" =~ ^[1-9][0-9]*[KMG]?$ ]]; then
            echo "error: --room-memory: '$v' is not a size like 12G" >&2
            exit 2
        fi
    done
fi

# --remove and --clear-room-memory need no values: a bad host.env must not
# block a reap, or lowering a room back to its default.
CONFIG_FROM="no host config, defaults"
if [[ "$MODE" != remove && "$MODE" != clear-room-memory ]]; then
    rz_host_env_load || exit 2
    if [[ -e "$RZ_HOST_ENV_FILE" ]]; then
        CONFIG_FROM="$RZ_HOST_ENV_FILE"
    fi
    ROOMS_MEMORY_HIGH="${HOST_ENV[RZ_ROOMS_MEMORY_HIGH]:-$ROOMS_MEMORY_HIGH}"
    ROOMS_MEMORY_MAX="${HOST_ENV[RZ_ROOMS_MEMORY_MAX]:-$ROOMS_MEMORY_MAX}"
    GATE_SLOTS="${HOST_ENV[RZ_GATE_SLOTS]:-$GATE_SLOTS}"
    CPU_FACTOR="${HOST_ENV[RZ_CPU_FACTOR]:-$CPU_FACTOR}"
    if (($(rz_size_bytes "$ROOMS_MEMORY_HIGH") > $(rz_size_bytes "$ROOMS_MEMORY_MAX"))); then
        echo "error: $RZ_HOST_ENV_FILE: rooms MemoryHigh=$ROOMS_MEMORY_HIGH is above" \
            "MemoryMax=$ROOMS_MEMORY_MAX" >&2
        exit 2
    fi
fi
IN_EFFECT="ritz-rooms.slice: MemoryHigh=$ROOMS_MEMORY_HIGH MemoryMax=$ROOMS_MEMORY_MAX;\
 gate slots=$GATE_SLOTS; cpu factor=$CPU_FACTOR; from $CONFIG_FROM"

DROPIN_DIR="$UNITS/adele-agent@$ROOM.service.d"
DROPIN="$DROPIN_DIR/50-ritz-host-budget.conf"
OVR_DIR="$CONTROL/adele-agent@$ROOM.service.d"
OVR="$OVR_DIR/90-rz-room-memory.conf"

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

# ovr_check HIGH MAX: prints why the pair is not allowed; returns 1 if so.
ovr_check() {
    if (($(rz_size_bytes "$1") > $(rz_size_bytes "$2"))); then
        echo "MemoryHigh=$1 is above MemoryMax=$2"
        return 1
    fi
    if (($(rz_size_bytes "$2") > $(rz_size_bytes "$ROOMS_MEMORY_MAX"))); then
        echo "MemoryMax=$2 is above the ritz-rooms.slice MemoryMax=$ROOMS_MEMORY_MAX"
        return 1
    fi
}

# drop_override: delete the room's override (and its dir, if now empty).
# Returns 0 if there was one.
drop_override() {
    [[ -e "$OVR" ]] || return 1
    rm -f "$OVR"
    rmdir "$OVR_DIR" 2>/dev/null || true
}

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
    OVR_NOTE=""
    if [[ -e "$OVR" ]]; then
        h="$(sed -n 's/^MemoryHigh=//p' "$OVR" | tail -n1)"
        m="$(sed -n 's/^MemoryMax=//p' "$OVR" | tail -n1)"
        if [[ ! "$h" =~ ^[1-9][0-9]*[KMG]?$ || ! "$m" =~ ^[1-9][0-9]*[KMG]?$ ]]; then
            why="unreadable MemoryHigh/MemoryMax"
        else
            why="$(ovr_check "$h" "$m")" && why=""
        fi
        if [[ -n "$why" ]]; then
            echo "BAD ROOM MEMORY OVERRIDE: $OVR: $why" >&2
            echo "run: $0 --clear-room-memory $ROOM (or --room-memory with new values)" >&2
            exit 1
        fi
        OVR_NOTE="; room override MemoryHigh=$h MemoryMax=$m from $OVR"
    fi
    echo "host budget OK for $ROOM ($IN_EFFECT$OVR_NOTE)"
    ;;
remove)
    reload=0
    if [[ -e "$DROPIN" ]]; then
        rm -f "$DROPIN"
        rmdir "$DROPIN_DIR" 2>/dev/null || true
        reload=1
    fi
    drop_override && reload=1
    [[ $reload -eq 1 ]] && systemctl --user daemon-reload
    echo "host budget removed for $ROOM (slices kept)"
    ;;
room-memory)
    if ! why="$(ovr_check "$OVR_HIGH" "$OVR_MAX")"; then
        echo "error: --room-memory $ROOM: $why ($IN_EFFECT)" >&2
        exit 2
    fi
    OVR_BODY="# Installed by .claude/host-budget.sh --room-memory (AGAST #3971). Runtime:
# gone at reboot.  Sorts after 50-ritz-host-budget.conf, so it survives
# daemon-reload.  Clear with: .claude/host-budget.sh --clear-room-memory $ROOM
[Service]
MemoryHigh=$OVR_HIGH
MemoryMax=$OVR_MAX"
    if ! current "$OVR" "$OVR_BODY"; then
        mkdir -p "$OVR_DIR"
        printf '%s\n' "$OVR_BODY" > "$OVR.tmp"
        mv -f "$OVR.tmp" "$OVR"
        systemctl --user daemon-reload
    fi
    echo "room memory for $ROOM: MemoryHigh=$OVR_HIGH MemoryMax=$OVR_MAX ($OVR; $IN_EFFECT)"
    ;;
clear-room-memory)
    drop_override && systemctl --user daemon-reload
    echo "room memory for $ROOM: per-room default (MemoryHigh=$ROOM_MEMORY_HIGH" \
        "MemoryMax=$ROOM_MEMORY_MAX)"
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
    echo "host budget OK for $ROOM (CPUWeight=$ROOM_CPU_WEIGHT," \
        "MemoryHigh=$ROOM_MEMORY_HIGH MemoryMax=$ROOM_MEMORY_MAX per room; $IN_EFFECT)"
    ;;
esac
