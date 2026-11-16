#!/usr/bin/env bash
# run-gate.sh under the REAL `systemd-run --user` (AGAST #3567).  The stubbed
# test-run-gate.sh can't catch this class of bug: systemd unescapes and expands
# `$` in a unit's command line (`$$` -> `$`, `${x}` -> x from the unit's env),
# so the gate's inner script must never pass through it as argv text.
#
# Uses its own temp gate dir and unit names (ritz-gate-t3567-<rand>-*); never
# touches ~/dev/ritz-lang/gate-logs or other gates' units.
# Run: bash test-run-gate-systemd.sh   (skips if no user systemd)
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
if ! systemd-run --user --quiet --wait --collect /bin/true 2>/dev/null; then
    echo "skip - no usable systemd-run --user"; exit 0
fi
T="$(mktemp -d)"
ID="t3567-$RANDOM$RANDOM"
UNITS=()
cleanup() {
    local u
    for u in "${UNITS[@]}"; do systemctl --user stop "$u" 2>/dev/null; done
    rm -rf "$T"
}
trap cleanup EXIT
fails=0
ok()  { echo "ok   - $1"; }
bad() { echo "FAIL - $1"; fails=$((fails + 1)); }
check() { if eval "$1"; then ok "$2"; else bad "$2"; fi; }
# until_ <cond> [tenths]: poll up to 30 s by default.
until_() { local i; for i in $(seq 1 "${2:-300}"); do eval "$1" && return 0; sleep 0.1; done; return 1; }

export RZ_GATE_DIR="$T/gates" RZ_HOST_ENV="$T/no-host.env" RZ_GATE_SLOTS=1
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
W="$T/wt"
git init -q "$W"; echo a > "$W/a"; git -C "$W" add a; git -C "$W" commit -qm init
G="$HERE/run-gate.sh"
Q="$RZ_GATE_DIR/.gate-queue"
ORDER="$T/order"; RELEASE="$T/release"; : > "$ORDER"

# start <name> <poll> <cmd>: launch a real gate unit; prints its log path.
start() {
    UNITS+=("ritz-gate-$ID-$1")
    RZ_GATE_POLL="$2" RZ_GATE_CMD="$3" bash "$G" "$W" "$ID-$1"
}

# H holds the one slot until $RELEASE exists.  Then A queues, then B, which
# polls 10x as often: without a working FIFO, B grabs the freed slot first.
logh="$(start h 0.2 "echo H >> '$ORDER'; until [ -e '$RELEASE' ]; do sleep 0.1; done")"
check 'until_ "grep -q \"^SLOT=\" \"\$logh\""' "the holder gate takes the slot"
loga="$(start a 2 "echo A >> '$ORDER'")"
until_ 'grep -q "^WAITING" "$loga"'
logb="$(start b 0.2 "echo B >> '$ORDER'")"
until_ 'grep -q "^WAITING" "$logb"'
sleep 1   # let both waiters poll (and, if broken, prune each other) a few times

# Every queue line is "<unit> <pid> <train>" with a numeric, live pid.
mapfile -t lines < "$Q"
check '[[ ${#lines[@]} -eq 2 ]]' "two waiters, two queue entries (got ${#lines[@]}: ${lines[*]})"
for l in "${lines[@]}"; do
    read -r u p t <<< "$l"
    check '[[ "$p" =~ ^[0-9]+$ ]] && kill -0 "$p" 2>/dev/null' "queue entry '$l' has a numeric, live pid"
done
check '[[ "${lines[0]%% *}" == "ritz-gate-$ID-a" ]]' "the first waiter is still at the head of the queue"
check 'grep -q "^WAITING.*position 2" "$logb" && ! grep -q "^WAITING.*position 1" "$logb"' "the later waiter reports position 2, never 1"
check 'grep -q "^WAITING.*position 1" "$loga"' "the first waiter reports position 1"

touch "$RELEASE"
check 'until_ "grep -q \"^EXIT=\" \"\$logb\" && grep -q \"^EXIT=\" \"\$loga\""' "both waiters reach a verdict"
check '[[ "$(tr "\n" " " < "$ORDER")" == "H A B " ]]' "the freed slot goes to the first waiter (order: $(tr '\n' ' ' < "$ORDER"))"
check 'grep -qx EXIT=0 "$loga" && grep -qx EXIT=0 "$logb"' "both gates pass"
check '[[ ! -s "$Q" ]]' "the queue is empty afterwards"

# The train path under real systemd: the reservation (written via a
# $RES.<pid> temp file) is a timestamp and no temp file is left behind.
logt="$(RZ_GATE_TRAIN=1 start t 0.2 'exit 0')"
check 'until_ "grep -q \"^EXIT=\" \"\$logt\""' "a train gate reaches a verdict"
check '[[ "$(cat "$RZ_GATE_DIR/.train-reserved" 2>/dev/null)" =~ ^[0-9]+$ ]]' "the train gate's reservation is a timestamp"
check '[[ -z "$(ls -A "$RZ_GATE_DIR" | grep -E "^\.train-reserved\.")" ]]' "no reservation temp file is left behind"

check '[[ -z "$(ls "$RZ_GATE_DIR" | grep "\.unit\.sh$")" ]]' "each unit deletes its script file"

echo
[[ $fails -eq 0 ]] && { echo "all passed"; exit 0; }
echo "$fails failed"; exit 1
