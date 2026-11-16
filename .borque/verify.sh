#!/usr/bin/env bash
#
# Borque's `verify` for ritz (.borque/profile.toml, AGAST #3722): gate a room's
# HEAD and BLOCK until the verdict, exiting with the gate's own code.
#
#   .borque/verify.sh <worktree> <room>      e.g. ... ritz-task-3722
#
# run-gate.sh starts the gate detached and prints its log; --wait blocks on
# that log.  The gate is named after the task id (3722), as a room names it
# by hand, so its log is <gate dir>/3722-<sha12>-<n>.log.
#
# Exit: the gate's code (0 pass, 2 fail, 98 no verdict, 99 HEAD moved), or
# run-gate.sh's own start error; 64 for a room name without a task id.  Each
# --wait runs under `timeout RZ_GATE_WAIT_SLICE` (default 540 s, as rooms
# wait by hand); a slice that times out (124) is waited again, never returned.
#
# Env: RZ_GATE_SCRIPT  run-gate.sh to use (tests; default: this checkout's)
# Tests: .borque/test-borque.sh.
set -uo pipefail
: "${HOME:=$(getent passwd "$(id -u)" | cut -d: -f6)}"
: "${PATH:=/usr/local/bin:/usr/bin:/bin}"
export HOME PATH

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
GATE="${RZ_GATE_SCRIPT:-$HERE/../.claude/skills/rz-iterate/run-gate.sh}"

if [[ $# -ne 2 ]]; then
    echo "usage: $0 <worktree> <room>" >&2
    exit 64
fi
WT="$1" ROOM="$2"
if [[ ! "$ROOM" =~ ^ritz-task-([0-9]+)$ ]]; then
    echo "error: room '$ROOM' is not ritz-task-<id>" >&2
    exit 64
fi
ID="${BASH_REMATCH[1]}"

LOG="$(bash "$GATE" "$WT" "$ID")" || exit $?
echo "LOG=$LOG"
while :; do
    timeout "${RZ_GATE_WAIT_SLICE:-540}" bash "$GATE" --wait "$LOG"
    rc=$?
    [[ $rc -eq 124 ]] || exit $rc
done
