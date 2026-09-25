#!/usr/bin/env bash
#
# Run a room's verification gate so it cannot be killed, cannot overload the
# machine, and always ends in a verdict.
#
#   run-gate.sh <worktree> <name>      start the gate, print its log path
#   run-gate.sh --wait <log>           block until it ends; exit with its code
#
# Env overrides:
#   RZ_GATE_CMD    command run from <worktree>   (default: clean ci-local)
#   RZ_GATE_SLOTS  gates allowed at once         (default: 2)
#   RZ_GATE_DIR    where logs and slot locks go  (default: ~/dev/ritz-lang/gate-logs)
#
# Why each piece exists (rz-iterate):
#   * systemd-run: a Bash background job dies when the agent's next turn
#     starts (AGAST #1441).  Two #1436 gates died that way, silently.
#   * slots: 12 cores.  ci-local has 180 s timed tests; six concurrent gates
#     turn them into timeouts that look like regressions and are not.
#   * SHA in the log name, and the HEAD-moved check: the callback claims a
#     specific commit passed.  A gate that ran while HEAD moved proves nothing.
#   * EXIT line always written, and --wait reports a unit that died without
#     one (exit 98): "no verdict" must never read as "passed".
set -euo pipefail

GATES="${RZ_GATE_DIR:-$HOME/dev/ritz-lang/gate-logs}"

if [[ "${1:-}" == "--wait" ]]; then
    LOG="${2:?usage: $0 --wait <log>}"
    UNIT="$(sed -n 's/^UNIT=//p' "$LOG" | head -1)"
    while ! grep -q '^EXIT=' "$LOG"; do
        if ! systemctl --user is-active -q "$UNIT"; then
            sleep 2
            grep -q '^EXIT=' "$LOG" && break
            echo "GATE DIED WITHOUT A VERDICT: $UNIT ($LOG)" >&2
            exit 98
        fi
        sleep 15
    done
    rc="$(sed -n 's/^EXIT=//p' "$LOG" | tail -1)"
    grep -E '^(SHA|SLOT|EXIT)=|Stage [0-9]:|passed|FATAL' "$LOG" | tail -20
    exit "$rc"
fi

if [[ $# -ne 2 ]]; then
    echo "usage: $0 <worktree> <name>   |   $0 --wait <log>" >&2
    exit 2
fi

WT="$(cd "$1" && pwd -P)"
NAME="$2"
SLOTS="${RZ_GATE_SLOTS:-2}"
CMD="${RZ_GATE_CMD:-rm -rf projects/ritz/.regression && make -C projects/ritz ci-local}"
UNIT="ritz-gate-$NAME"

# Uncommitted tracked changes would be tested but not merged.
if ! git -C "$WT" diff --quiet HEAD; then
    echo "error: $WT has uncommitted tracked changes; commit first" >&2
    exit 1
fi
if systemctl --user is-active -q "$UNIT"; then
    echo "error: $UNIT is already running" >&2
    exit 1
fi

SHA="$(git -C "$WT" rev-parse HEAD)"
mkdir -p "$GATES"
LOG="$GATES/$NAME-${SHA:0:12}.log"
printf 'UNIT=%s\nSHA=%s\nCMD=%s\n' "$UNIT" "$SHA" "$CMD" > "$LOG"

# The inner script reads everything from the environment, so nothing here
# needs a second layer of quoting.
read -r -d '' INNER <<'EOF' || true
set -u
# Fail fast if the unit can't write: otherwise the slot loop below spins
# forever and never writes a verdict.  (Seen: an agent sandbox's /tmp is not
# the /tmp systemd units see.)  The unit ends with no EXIT line; --wait -> 98.
echo "WAITING for a gate slot $(date -Is)" >> "$RZ_LOG" || exit 97
while :; do
    for s in $(seq 0 $((RZ_SLOTS - 1))); do
        exec 9>"$RZ_DIR/.gate-slot-$s"
        if flock -n 9; then break 2; fi
    done
    sleep 20
done
echo "SLOT=$s START $(date -Is)" >> "$RZ_LOG"
bash -c "$RZ_CMD" >> "$RZ_LOG" 2>&1
rc=$?
now="$(git rev-parse HEAD)"
if [ "$now" != "$RZ_SHA" ]; then
    echo "HEAD MOVED during the gate: $RZ_SHA -> $now; result void" >> "$RZ_LOG"
    rc=99
fi
echo "EXIT=$rc" >> "$RZ_LOG"
EOF

systemd-run --user --quiet --unit="$UNIT" --collect --working-directory="$WT" \
    --setenv=PATH="$PATH" --setenv=HOME="$HOME" \
    --setenv=RZ_LOG="$LOG" --setenv=RZ_SHA="$SHA" --setenv=RZ_CMD="$CMD" \
    --setenv=RZ_SLOTS="$SLOTS" --setenv=RZ_DIR="$GATES" \
    /bin/bash -c "$INNER"

echo "$LOG"
