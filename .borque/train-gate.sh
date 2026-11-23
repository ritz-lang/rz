#!/usr/bin/env bash
#
# Borque's `train.gate` for ritz (.borque/profile.toml, AGAST #3722): gate a
# merge train's tip and BLOCK until the verdict, exiting with the gate's code.
#
#   .borque/train-gate.sh <train_worktree>
#
# The same gate `train.sh gate` starts: RZ_GATE_TRAIN=1 (train priority for the
# gate slot, #3317) and RZ_GATE_BASE=<base>, named "train".  Then run-gate.sh
# --wait, as verify.sh does.  No package-test step: the gate's test-all job
# tests every package (#3969, #3970).
#
# The base is `git merge-base HEAD origin/main` in the train worktree.  A
# train is cars stacked on origin/main as it was when the train was built, so
# that commit is the base, and it stays the base if origin/main has moved on
# since (train.sh keeps it in a state file instead, which Borque's trains
# don't have).
#
# Exit: the gate's code (0, 2, 98, 99) or run-gate.sh's start error; 64 for
# a path that isn't a git worktree with an origin/main.  A 124 wait slice
# (RZ_GATE_WAIT_SLICE, default 540 s) is waited again.
#
# Env: RZ_GATE_SCRIPT  run-gate.sh to use (tests; default: this checkout's)
# Tests: .borque/test-borque.sh.
set -uo pipefail
: "${HOME:=$(getent passwd "$(id -u)" | cut -d: -f6)}"
: "${PATH:=/usr/local/bin:/usr/bin:/bin}"
export HOME PATH

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
GATE="${RZ_GATE_SCRIPT:-$HERE/../.claude/skills/rz-iterate/run-gate.sh}"

if [[ $# -ne 1 ]]; then
    echo "usage: $0 <train_worktree>" >&2
    exit 64
fi
WT="$1"
if ! BASE="$(git -C "$WT" merge-base HEAD origin/main 2>/dev/null)"; then
    echo "error: $WT is not a git worktree with an origin/main" >&2
    exit 64
fi

LOG="$(RZ_GATE_TRAIN=1 RZ_GATE_BASE="$BASE" bash "$GATE" "$WT" train)" || exit $?
echo "LOG=$LOG"
while :; do
    timeout "${RZ_GATE_WAIT_SLICE:-540}" bash "$GATE" --wait "$LOG"
    rc=$?
    [[ $rc -eq 124 ]] || exit $rc
done
