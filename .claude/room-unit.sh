#!/usr/bin/env bash
#
# Run a short-lived systemd unit from a task room WITHOUT leaving the room.
#
#   bash .claude/room-unit.sh [options] -- <command> [args...]
#   bash .claude/room-unit.sh restart-self
#
# A room (adele-agent@ritz-task-<id>.service) runs under a 5G memory cap in
# ritz-rooms.slice (#1811).  A direct `systemd-run --user make ...` starts a
# sibling unit with no cap of its own, so the build leaves the room.  The
# room's settings (.claude/provision-room.sh) therefore DENY every direct
# systemd-run spelling, and tests that need a real unit come through here
# (AGAST #3568).
#
# Every unit started here is pinned:
#   --user --wait --collect               ends when the command does
#   --slice=ritz-rooms.slice              never a different slice
#   MemoryMax=1G CPUWeight=20             its own small cap, room CPU weight
#   RuntimeMaxSec=900                     short-lived, by force
#   PrivateTmp=yes + JoinsNamespaceOf=<this room's unit>
#                                         the command sees the ROOM's /tmp.
#                                         Without it, /tmp files a test unit
#                                         writes never appear to the room.
#
# Options accepted (anything else exits 2 and runs nothing):
#   -q|--quiet  -P|--pipe  --wait  --collect|-G   (the last two are pinned anyway)
#   --unit=NAME | -u NAME          NAME: [A-Za-z0-9_.-], no unit-type suffix
#   --setenv=K=V | -E K=V
#   -p|--property  KEY=VALUE       KEY: StandardInput, StandardOutput,
#                                  StandardError, WorkingDirectory, Environment;
#                                  no file:/append:/truncate: under /tmp (the
#                                  manager opens those in the HOST's /tmp)
#   `--` then the command.  Required: options and command never mix.
#
# restart-self: the briefing's self-restart (a rejected MCP token).  Restarts
# the unit this process runs in, 15s from now, and nothing else.
#
# Tests: projects/ritz/tools/test_provision_room.py.  ROOM_UNIT_DRY_RUN=1
# prints the argv instead of running it; ROOM_UNIT_CGROUP_FILE replaces
# /proc/self/cgroup.
set -euo pipefail

die() { echo "room-unit.sh: $*" >&2; exit 2; }

# The room unit this process runs in, from its cgroup path rather than an
# environment variable a caller could set.  Not in a room unit: refuse.
room_unit() {
    local cg; cg="$(cat "${ROOM_UNIT_CGROUP_FILE:-/proc/self/cgroup}")"
    [[ "$cg" =~ /ritz-rooms\.slice/(adele-agent@[A-Za-z0-9_.-]+\.service)(/|$) ]] \
        || die "not running inside a room unit (adele-agent@*.service in ritz-rooms.slice)"
    printf '%s\n' "${BASH_REMATCH[1]}"
}

run() {
    if [[ -n "${ROOM_UNIT_DRY_RUN:-}" ]]; then
        printf '%s\n' "$@"
    else
        exec "$@"
    fi
}

if [[ "${1:-}" == restart-self ]]; then
    [[ $# -eq 1 ]] || die "restart-self takes no arguments: it only restarts its own unit"
    UNIT="$(room_unit)"
    run systemd-run --user --on-active=15 systemctl --user restart "$UNIT"
    exit 0
fi

USER_ARGS=()
prop() {
    case "${1%%=*}" in
        StandardInput|StandardOutput|StandardError|WorkingDirectory|Environment)
            [[ "$1" == *=* ]] || die "property needs KEY=VALUE: $1"
            # The MANAGER opens file:/append:/truncate: targets, in the host's
            # /tmp, not the room's: the file never appears to the room.
            [[ "${1#*=}" =~ ^(file|append|truncate):/(var/)?tmp/ ]] \
                && die "${1%%=*} under /tmp lands in the HOST's /tmp, not the room's: use --pipe, or redirect inside the command (bash -c '... > /tmp/x')"
            USER_ARGS+=("--property=$1") ;;
        *) die "property not allowed: ${1%%=*} (only StandardInput/Output/Error, WorkingDirectory, Environment)" ;;
    esac
}
unit_name() {
    [[ "$1" =~ ^[A-Za-z0-9_][A-Za-z0-9_.-]*$ ]] || die "bad unit name: $1"
    [[ "$1" =~ \.(slice|scope|socket|timer|path|target|mount|swap|automount|device)$ ]] \
        && die "unit name must be a plain service name: $1"
    USER_ARGS+=("--unit=$1")
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --) shift; break ;;
        -q|--quiet|-P|--pipe) USER_ARGS+=("$1") ;;
        --wait|--collect|-G) ;;   # pinned below
        --unit=*) unit_name "${1#--unit=}" ;;
        -u|--unit) [[ $# -ge 2 ]] || die "$1 needs a value"; unit_name "$2"; shift ;;
        --setenv=*) USER_ARGS+=("$1") ;;
        -E|--setenv) [[ $# -ge 2 ]] || die "$1 needs a value"; USER_ARGS+=("--setenv=$2"); shift ;;
        --property=*) prop "${1#--property=}" ;;
        -p|--property) [[ $# -ge 2 ]] || die "$1 needs a value"; prop "$2"; shift ;;
        *) die "option not allowed: $1 (and the command goes after --)" ;;
    esac
    shift
done
[[ $# -gt 0 ]] || die "no command: usage: room-unit.sh [options] -- <command> [args...]"

UNIT="$(room_unit)"
run systemd-run --user --wait --collect \
    --slice=ritz-rooms.slice \
    --property=MemoryMax=1G \
    --property=CPUWeight=20 \
    --property=RuntimeMaxSec=900 \
    --property=PrivateTmp=yes \
    "--property=JoinsNamespaceOf=$UNIT" \
    "${USER_ARGS[@]}" \
    -- "$@"
