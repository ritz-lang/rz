#!/usr/bin/env bash
# Tests for run-gate.sh with systemd-run and systemctl stubbed out, so the gate
# runs in the foreground against a throwaway repo.  Run: bash test-run-gate.sh
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
T="$(mktemp -d)"; trap 'chmod -R u+rwx "$T"; rm -rf "$T"' EXIT
fails=0
ok()  { echo "ok   - $1"; }
bad() { echo "FAIL - $1"; fails=$((fails + 1)); }
check() { if eval "$1"; then ok "$2"; else bad "$2"; fi; }

# Stubs.  systemd-run runs the unit's command synchronously with its --setenv
# and --working-directory, and marks the unit active ($RZ_TEST_ACTIVE/<unit>)
# while it runs; systemctl is-active reads that mark.
mkdir -p "$T/bin" "$T/active"
export RZ_TEST_ACTIVE="$T/active"
cat > "$T/bin/systemd-run" <<'STUB'
#!/usr/bin/env bash
envs=(); wd=.; unit=
while [[ $# -gt 0 ]]; do
    case "$1" in
        --setenv=*) envs+=("${1#--setenv=}") ;;
        --working-directory=*) wd="${1#*=}" ;;
        --unit=*) unit="${1#*=}" ;;
        --*) ;;
        *) break ;;
    esac
    shift
done
touch "$RZ_TEST_ACTIVE/$unit"
(cd "$wd" && env "${envs[@]}" "$@"); rc=$?
rm -f "$RZ_TEST_ACTIVE/$unit"
exit $rc
STUB
cat > "$T/bin/systemctl" <<'STUB'
#!/usr/bin/env bash
[[ -n "${!#}" && -e "$RZ_TEST_ACTIVE/${!#}" ]] && exit 0
exit 3
STUB
chmod +x "$T/bin/systemd-run" "$T/bin/systemctl"
export PATH="$T/bin:$PATH"
export RZ_GATE_DIR="$T/gates" RZ_HOST_ENV="$T/no-host.env" RZ_GATE_SLOTS=1
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t

W="$T/wt"
git init -q "$W"; echo a > "$W/a"; git -C "$W" add a; git -C "$W" commit -qm init
SHA="$(git -C "$W" rev-parse HEAD)"; S12="${SHA:0:12}"
G="$HERE/run-gate.sh"
# A bounded run: a script that loops looking for a free log name fails, not hangs.
gate() { timeout 30 bash "$G" "$@"; }

# 1. Two runs of one SHA: two logs; the first run's verdict survives the second.
log1="$(RZ_GATE_CMD='echo first run; exit 2' gate "$W" t1)"
log2="$(RZ_GATE_CMD='echo second run; exit 0' gate "$W" t1)"
check '[[ -n "$log1" && -n "$log2" && "$log1" != "$log2" ]]' "two runs of one SHA name two logs"
check '[[ -f "$log1" && -f "$log2" ]]' "both logs exist"
check '[[ "$(ls "$RZ_GATE_DIR"/t1-"$S12"*.log | wc -l)" -eq 2 ]]' "the gate dir holds exactly two logs for the SHA"
check 'grep -qx "EXIT=2" "$log1" && grep -qx "first run" "$log1"' "first log keeps its output and EXIT=2"
check 'grep -qx "EXIT=0" "$log2" && ! grep -q "first run" "$log2"' "second log has only its own run"
check '[[ "$(grep -c "^EXIT=" "$log1")" -eq 1 && "$(grep -c "^EXIT=" "$log2")" -eq 1 ]]' "one EXIT line per log"
# 1b. The verdict trailer repeats the identity before EXIT=, so a reader whose
# header was truncated still names the unit and commit (AGAST #4430).
check '[[ "$(tail -3 "$log2" | tr "\n" " ")" == "UNIT=ritz-gate-t1 SHA=$SHA EXIT=0 " ]]' \
    "the log ends with a UNIT=/SHA= trailer then EXIT="

# 2. Names: <name>-<sha12>-<n>.log, so the REAP quote names one log and its SHA.
check '[[ "$(basename "$log1")" =~ ^t1-${S12}-[0-9]+\.log$ ]]' "log name is <name>-<sha12>-<n>.log"
check 'grep -qx "SHA=$SHA" "$log1" && grep -qx "SHA=$SHA" "$log2"' "each log records the full SHA"

# 3. An existing log is never truncated, whatever is already in the dir.
next="$RZ_GATE_DIR/t1-$S12-3.log"
printf 'KEEP ME\n' > "$next"
log3="$(RZ_GATE_CMD='exit 0' gate "$W" t1)"
check '[[ "$log3" != "$next" && "$(cat "$next")" == "KEEP ME" ]]' "a run never truncates an existing log"
check '[[ "$log3" != "$log1" && "$log3" != "$log2" ]]' "third run gets a third log"
check 'grep -qx "EXIT=2" "$log1"' "first log still intact after three runs"

# 4. --wait exit codes are unchanged: the gate's own code, 98, 99.
gate --wait "$log1" >/dev/null 2>&1; rc=$?
check '[[ $rc -eq 2 ]]' "--wait exits with a failed gate's code (2), got $rc"
gate --wait "$log2" >/dev/null 2>&1; rc=$?
check '[[ $rc -eq 0 ]]' "--wait exits 0 for a passing gate, got $rc"
nov="$RZ_GATE_DIR/noverdict.log"; printf 'UNIT=ritz-gate-x\nSHA=%s\n' "$SHA" > "$nov"
gate --wait "$nov" >/dev/null 2>&1; rc=$?
check '[[ $rc -eq 98 ]]' "--wait exits 98 for a unit that died without a verdict, got $rc"
logm="$(RZ_GATE_CMD='echo b > b && git add b && git commit -qm move' gate "$W" t2)"
gate --wait "$logm" >/dev/null 2>&1; rc=$?
check '[[ $rc -eq 99 ]]' "--wait exits 99 when HEAD moved, got $rc"
check '[[ "$(basename "$logm")" =~ ^t2-${S12}-[0-9]+\.log$ ]]' "log is named for the SHA gated, not the moved HEAD"

# 4b. A gate log truncated mid-run loses its header but keeps the identity in
# a trailer next to the verdict (AGAST #4430: an operator session truncated a
# live huburght log, and a valid EXIT=0 was refused for want of SHA=).  --wait
# reads the LAST UNIT=, so the trailer still names the unit.
tunit="ritz-gate-trunc-$S12"
trunc="$RZ_GATE_DIR/truncated-$S12.log"
printf 'ok Stage 1 output is identical with 1 and 8 jobs\nUNIT=%s\nSHA=%s\nEXIT=0\n' \
    "$tunit" "$SHA" > "$trunc"
out="$(gate --wait "$trunc" 2>&1)"; rc=$?
check '[[ $rc -eq 0 ]]' "--wait reports a truncated log's trailer verdict (EXIT=0, got $rc)"
# 4c. ... and finds its unit: the trailer is authoritative, so a stale first
# UNIT= doesn't make a dead gate report itself as headerless.
trunc2="$RZ_GATE_DIR/truncated-noexit-$S12.log"
printf 'UNIT=ritz-gate-stale\nok Stage 1 output is identical with 1 and 8 jobs\nUNIT=%s\nSHA=%s\n' \
    "$tunit" "$SHA" > "$trunc2"
out="$(gate --wait "$trunc2" 2>&1)"; rc=$?
check '[[ $rc -eq 98 && "$out" == *"GATE DIED WITHOUT A VERDICT: $tunit"* ]]' \
    "--wait finds the last UNIT= in a truncated log (rc=$rc)"
# 4d. A headerless, verdict-less log is a clear diagnostic, not an empty-unit
# liveness check that would misread a live gate as dead.
gone="$RZ_GATE_DIR/headerless-$S12.log"
printf 'ok Stage 1 output is identical with 1 and 8 jobs\n' > "$gone"
out="$(gate --wait "$gone" 2>&1)"; rc=$?
check '[[ $rc -eq 98 && "$out" == *"GATE LOG HAS NO UNIT="* ]]' \
    "a headerless, verdict-less log exits 98 with a clear diagnostic (rc=$rc)"

# 5. An unwritable gate dir fails at once instead of looping for a free name.
if [[ "$(id -u)" -ne 0 ]]; then
    git -C "$W" reset -q --hard "$SHA"
    mkdir -p "$T/ro"; chmod a-w "$T/ro"
    out="$(RZ_GATE_DIR="$T/ro" RZ_GATE_CMD='exit 0' gate "$W" t3 2>&1)"; rc=$?
    check '[[ $rc -ne 0 && $rc -ne 124 ]]' "unwritable gate dir is an error, not a hang (rc=$rc)"
    check '[[ -z "$(ls -A "$T/ro")" ]]' "nothing written to an unwritable gate dir"
else
    echo "skip - unwritable gate dir (running as root)"
fi

# 6. Train priority (AGAST #3317): a waiting train gate gets the next free
# slot ahead of a room gate, whichever polls first.  RZ_GATE_POLL makes the
# slot loop fast; B polls 10x as often as T, so without the priority B wins.
git -C "$W" reset -q --hard "$SHA"
export RZ_TEST_ORDER="$T/order" RZ_TEST_RELEASE="$T/release-a"
: > "$RZ_TEST_ORDER"
MARK="$RZ_GATE_DIR/.train-waiting"
# until <cond>: poll up to 10 s.
until_() { local i; for i in $(seq 1 100); do eval "$1" && return 0; sleep 0.1; done; return 1; }
logof() { ls "$RZ_GATE_DIR"/"$1"-*.log 2>/dev/null | head -1; }
# stop <log>: SIGTERM a unit's inner script and its children, as systemd's
# stop would.  A gate killed by `timeout` leaves its stubbed unit running.
stop() {
    local p
    for p in $(pgrep -u "$(id -u)" -x bash); do
        if tr '\0' '\n' 2>/dev/null < "/proc/$p/environ" | grep -qx "RZ_LOG=$1"; then
            pkill -TERM -P "$p"; kill -TERM "$p"
        fi
    done
}
hold='echo $RZ_TEST_NAME >> "$RZ_TEST_ORDER"; until [ -e "$RZ_TEST_RELEASE" ]; do sleep 0.1; done'
RZ_TEST_NAME=A RZ_GATE_POLL=0.1 RZ_GATE_CMD="$hold" gate "$W" pa >/dev/null &
until_ '[[ -n "$(logof pa)" ]] && grep -q "^SLOT=" "$(logof pa)"'
RZ_GATE_TRAIN=1 RZ_GATE_POLL=1 RZ_GATE_CMD='echo T >> "$RZ_TEST_ORDER"; ls -A "$RZ_DIR" > "$RZ_TEST_ORDER.during-t"' gate "$W" pt >/dev/null &
until_ '[[ -n "$(logof pt)" ]] && grep -q "^WAITING" "$(logof pt)"'
check '[[ "$(cat "$MARK" 2>/dev/null)" == ritz-gate-pt ]]' "a waiting train gate leaves a .train-waiting marker naming its unit"
# B ignores the reservation T leaves when it ends (AGAST #3427, section 14):
# this section is about who gets the slot first, not about how long B waits.
RZ_GATE_TRAIN_HOLD=0 RZ_GATE_POLL=0.1 RZ_GATE_CMD='echo B >> "$RZ_TEST_ORDER"' gate "$W" pb >/dev/null &
until_ '[[ -n "$(logof pb)" ]] && grep -q "^WAITING" "$(logof pb)"'
sleep 0.5
touch "$RZ_TEST_RELEASE"
wait
check '[[ "$(tr "\n" " " < "$RZ_TEST_ORDER")" == "A T B " ]]' "train gate T takes the freed slot before room gate B (order: $(tr '\n' ' ' < "$RZ_TEST_ORDER"))"
check 'grep -qx EXIT=0 "$(logof pt)" && grep -qx EXIT=0 "$(logof pb)"' "both queued gates still reach a verdict"
check '[[ -s "$RZ_TEST_ORDER.during-t" ]] && ! grep -qx .train-waiting "$RZ_TEST_ORDER.during-t"' "the train's marker is gone once it has its slot (not only at exit)"
check '[[ ! -e "$MARK" ]]' "no marker is left after the train gate ends"
rm -f "$RZ_GATE_DIR/.train-reserved"

# 7. A marker from a train unit that is still active holds room gates off...
echo ritz-gate-livetrain > "$MARK"; touch "$RZ_TEST_ACTIVE/ritz-gate-livetrain"
RZ_GATE_POLL=0.1 RZ_GATE_CMD='exit 0' timeout 3 bash "$G" "$W" pl >/dev/null; rc=$?
check '[[ $rc -eq 124 ]] && ! grep -q "^SLOT=" "$(logof pl)"' "a live train's marker keeps a room gate off a free slot (rc=$rc)"
stop "$(logof pl)"; until_ '[[ ! -e "$RZ_TEST_ACTIVE/ritz-gate-pl" ]]'
# ...but one left by a dead train unit does not.
rm -f "$RZ_TEST_ACTIVE/ritz-gate-livetrain"; echo ritz-gate-deadtrain > "$MARK"
RZ_GATE_POLL=0.1 RZ_GATE_CMD='exit 0' timeout 5 bash "$G" "$W" ps >/dev/null; rc=$?
check '[[ $rc -eq 0 ]] && grep -qx EXIT=0 "$(logof ps)"' "a stale marker from a dead train unit doesn't block a room gate (rc=$rc)"
rm -f "$MARK"

# 8. A train gate stopped while it waits removes its marker (systemd stop
# sends SIGTERM to the unit's processes).
rm -f "$RZ_TEST_RELEASE"
RZ_TEST_NAME=A RZ_GATE_POLL=0.1 RZ_GATE_CMD="$hold" gate "$W" qa >/dev/null &
until_ '[[ -n "$(logof qa)" ]] && grep -q "^SLOT=" "$(logof qa)"'
RZ_GATE_TRAIN=1 RZ_GATE_POLL=0.1 RZ_GATE_CMD='exit 0' gate "$W" qt >/dev/null 2>&1 &
until_ '[[ -e "$MARK" ]]'
stop "$(logof qt)"
until_ '[[ ! -e "$MARK" ]]'
check '[[ ! -e "$MARK" ]]' "a train gate stopped while waiting removes its marker"
touch "$RZ_TEST_RELEASE"
wait

# 9. FIFO (AGAST #3364): with the one slot held by H, room gates A, B, C ask
# for it in that order.  C polls 10x as often as A and B, so whichever-polls-
# first would hand it to C; the queue hands it out A, B, C.
Q="$RZ_GATE_DIR/.gate-queue"
rm -f "$RZ_TEST_RELEASE"; : > "$RZ_TEST_ORDER"
RZ_TEST_NAME=H RZ_GATE_POLL=0.1 RZ_GATE_CMD="$hold" gate "$W" fh >/dev/null &
until_ '[[ -n "$(logof fh)" ]] && grep -q "^SLOT=" "$(logof fh)"'
fifo='echo $RZ_TEST_NAME >> "$RZ_TEST_ORDER"; sleep 0.3'
for x in a b; do
    RZ_TEST_NAME=${x^^} RZ_GATE_POLL=1 RZ_GATE_CMD="$fifo" gate "$W" f$x >/dev/null &
    until_ "[[ -n \"\$(logof f$x)\" ]] && grep -q '^WAITING' \"\$(logof f$x)\""
done
RZ_TEST_NAME=C RZ_GATE_POLL=0.1 RZ_GATE_CMD="$fifo" gate "$W" fc >/dev/null &
until_ '[[ -n "$(logof fc)" ]] && grep -q "^WAITING" "$(logof fc)"'
check '[[ "$(wc -l < "$Q" 2>/dev/null)" -eq 3 ]]' "three waiters, three queue entries"
check 'grep -q "^WAITING.*position 3" "$(logof fc)"' "the WAITING line logs the queue position"
sleep 0.5
touch "$RZ_TEST_RELEASE"
wait
check '[[ "$(tr "\n" " " < "$RZ_TEST_ORDER")" == "H A B C " ]]' "a freed slot goes to the longest waiter (order: $(tr '\n' ' ' < "$RZ_TEST_ORDER"))"
check '[[ -e "$Q" && ! -s "$Q" ]]' "the queue is empty once every gate has its slot"

# 10. A waiter killed outright (SIGKILL: no trap runs) is skipped, not waited on.
rm -f "$RZ_TEST_RELEASE"; : > "$RZ_TEST_ORDER"
RZ_TEST_NAME=H RZ_GATE_POLL=0.1 RZ_GATE_CMD="$hold" gate "$W" kh >/dev/null &
until_ '[[ -n "$(logof kh)" ]] && grep -q "^SLOT=" "$(logof kh)"'
RZ_TEST_NAME=A RZ_GATE_POLL=0.1 RZ_GATE_CMD="$fifo" gate "$W" ka >/dev/null 2>&1 &
until_ '[[ -n "$(logof ka)" ]] && grep -q "^WAITING" "$(logof ka)"'
RZ_TEST_NAME=B RZ_GATE_POLL=0.1 RZ_GATE_CMD="$fifo" gate "$W" kb >/dev/null &
until_ '[[ -n "$(logof kb)" ]] && grep -q "^WAITING" "$(logof kb)"'
check 'grep -q "^ritz-gate-ka " "$Q"' "the waiter to be killed is queued"
for p in $(pgrep -u "$(id -u)" -x bash); do
    tr '\0' '\n' 2>/dev/null < "/proc/$p/environ" | grep -qx "RZ_LOG=$(logof ka)" && kill -KILL "$p"
done
until_ '[[ ! -e "$RZ_TEST_ACTIVE/ritz-gate-ka" ]]'
touch "$RZ_TEST_RELEASE"
until_ 'grep -q "^EXIT=" "$(logof kb)"'
check 'grep -qx EXIT=0 "$(logof kb)" && [[ "$(tr "\n" " " < "$RZ_TEST_ORDER")" == "H B " ]]' "a killed waiter's entry is skipped (order: $(tr '\n' ' ' < "$RZ_TEST_ORDER"))"
check '! grep -q "^ritz-gate-ka " "$Q"' "the dead waiter's entry is pruned"
wait

# 11. A waiter stopped normally (SIGTERM) removes its own entry.
rm -f "$RZ_TEST_RELEASE"
RZ_TEST_NAME=H RZ_GATE_POLL=0.1 RZ_GATE_CMD="$hold" gate "$W" sh >/dev/null &
until_ '[[ -n "$(logof sh)" ]] && grep -q "^SLOT=" "$(logof sh)"'
RZ_GATE_POLL=0.1 RZ_GATE_CMD='exit 0' gate "$W" sw >/dev/null 2>&1 &
until_ 'grep -q "^ritz-gate-sw " "$Q"'
check 'grep -q "^ritz-gate-sw " "$Q"' "a waiting gate is queued"
stop "$(logof sw)"
until_ '! grep -q "^ritz-gate-sw " "$Q"'
check '! grep -q "^ritz-gate-sw " "$Q"' "a waiter stopped by SIGTERM removes its queue entry"
touch "$RZ_TEST_RELEASE"
wait

# 12. The queue keeps #3317's train priority: a train gate queued after room
# gate R still takes the freed slot first.
rm -f "$RZ_TEST_RELEASE"; : > "$RZ_TEST_ORDER"
RZ_TEST_NAME=H RZ_GATE_POLL=0.1 RZ_GATE_CMD="$hold" gate "$W" th >/dev/null &
until_ '[[ -n "$(logof th)" ]] && grep -q "^SLOT=" "$(logof th)"'
RZ_TEST_NAME=R RZ_GATE_TRAIN_HOLD=0 RZ_GATE_POLL=0.1 RZ_GATE_CMD="$fifo" gate "$W" tr >/dev/null &
until_ '[[ -n "$(logof tr)" ]] && grep -q "^WAITING" "$(logof tr)"'
RZ_TEST_NAME=T RZ_GATE_TRAIN=1 RZ_GATE_POLL=0.1 RZ_GATE_CMD="$fifo" gate "$W" tt >/dev/null &
until_ '[[ -n "$(logof tt)" ]] && grep -q "^WAITING" "$(logof tt)"'
check 'grep -q "^WAITING.*position 1 " "$(logof tt)"' "a train gate is first in line though a room gate queued before it"
touch "$RZ_TEST_RELEASE"
wait
check '[[ "$(tr "\n" " " < "$RZ_TEST_ORDER")" == "H T R " ]]' "a train gate queued after a room gate goes first (order: $(tr '\n' ' ' < "$RZ_TEST_ORDER"))"
rm -f "$RZ_GATE_DIR/.train-reserved"

# 13. RZ_GATE_AFTER is retired (AGAST #3970): the train's package tests it ran
# are test-all's job now (#3969).  A stale value in the environment is ignored.
la="$(RZ_GATE_CMD='echo main step' RZ_GATE_AFTER='echo after step; exit 5' gate "$W" t13a)"
check 'grep -qx "main step" "$la" && ! grep -qx "after step" "$la" && grep -qx EXIT=0 "$la"' "RZ_GATE_AFTER is ignored: it neither runs nor sets the verdict"
check '! grep -q "^CMD=.*after step" "$la"' "the logged CMD has no RZ_GATE_AFTER step"
lc="$(RZ_GATE_CMD='echo "PKG FAIL prism: exit 1, passes on base abc"; exit 1' gate "$W" t13c)"
gate --wait "$lc" > "$T/wait13" 2>&1
check 'grep -q "^PKG FAIL prism" "$T/wait13"' "--wait prints the PKG verdict lines"

# 14. AGAST #3427: the train's reservation starts when its gate ENDS, not at
# `train.sh land` (30-60 s later: the coordinator reads the verdict first).
# Room gate R queues while train gate T1 holds the slot.  When T1 ends, R must
# not take the freed slot.  Two runs, one for each way out of the reservation:
# T1 passes and the next train gate T2 takes the slot, or T1 fails and the
# reservation expires (R's RZ_GATE_TRAIN_HOLD=2; no T2 comes).
RES="$RZ_GATE_DIR/.train-reserved"
for v in 0 1; do
    rm -f "$RZ_TEST_RELEASE" "$RES"; : > "$RZ_TEST_ORDER"
    RZ_TEST_NAME=T1 RZ_GATE_TRAIN=1 RZ_GATE_POLL=0.1 RZ_GATE_CMD="$hold; exit $v" gate "$W" r${v}t1 >/dev/null &
    until_ "[[ -n \"\$(logof r${v}t1)\" ]] && grep -q '^SLOT=' \"\$(logof r${v}t1)\""
    hold_s=600; [[ $v -eq 1 ]] && hold_s=2
    RZ_TEST_NAME=R RZ_GATE_TRAIN_HOLD=$hold_s RZ_GATE_POLL=0.1 RZ_GATE_CMD="$fifo" gate "$W" r${v}r >/dev/null &
    until_ "[[ -n \"\$(logof r${v}r)\" ]] && grep -q '^WAITING' \"\$(logof r${v}r)\""
    before="$(date +%s)"; touch "$RZ_TEST_RELEASE"
    until_ "grep -q '^EXIT=' \"\$(logof r${v}t1)\""
    sleep 0.5
    t="$(cat "$RES" 2>/dev/null)"
    check '[[ "$t" =~ ^[0-9]+$ ]] && (( t >= before && t <= $(date +%s) ))' "a train gate ending with EXIT=$v reserves the slot, stamped with the time (got '$t')"
    check '! grep -q "^SLOT=" "$(logof r${v}r)"' "after an EXIT=$v train gate, a room gate queued before it ended doesn't take the freed slot"
    check 'grep -q "reserved for the merge train" "$(logof r${v}r)"' "the room gate's log says the slot is reserved (EXIT=$v)"
    if [[ $v -eq 0 ]]; then
        RZ_TEST_NAME=T2 RZ_GATE_TRAIN=1 RZ_GATE_POLL=0.1 RZ_GATE_CMD="$fifo" gate "$W" r${v}t2 >/dev/null
        # T2 reserves the slot in turn as it ends; let R in, as expiry would.
        rm -f "$RES"
        want="T1 T2 R "
    else
        want="T1 R "
    fi
    wait
    check '[[ "$(tr "\n" " " < "$RZ_TEST_ORDER")" == "$want" ]]' "the room gate runs only after the next train gate or the reservation's expiry (EXIT=$v; order: $(tr '\n' ' ' < "$RZ_TEST_ORDER"))"
    check 'grep -qx EXIT=0 "$(logof r${v}r)"' "the held room gate still reaches a verdict (EXIT=$v)"
done
# A room gate's end reserves nothing: only trains have a next train.
rm -f "$RES"
RZ_GATE_CMD='exit 1' gate "$W" r2room >/dev/null
check '[[ ! -e "$RES" ]]' "a room gate's end doesn't reserve the slot"
# (Section 14 runs at the default RZ_GATE_STARVE, 45 min: with no long
# waiter, #3427's reservation still holds the room gate off.)

# 15. AGAST #3578: back-to-back trains starved room gates on one slot.  With
# RZ_GATE_STARVE=2, train T1 holds the slot, room gate R waits past the bound,
# and train T2 queues behind it.  R polls 10x slower than T2, and T1's
# reservation (600 s) would hold R, so only the bound gets R in before T2.
OVR="$RZ_GATE_DIR/.room-override"
export RZ_GATE_STARVE=2
rm -f "$RZ_TEST_RELEASE" "$RES" "$OVR"; : > "$RZ_TEST_ORDER"
RZ_TEST_NAME=T1 RZ_GATE_TRAIN=1 RZ_GATE_POLL=0.1 RZ_GATE_CMD="$hold" gate "$W" s1t1 >/dev/null &
until_ '[[ -n "$(logof s1t1)" ]] && grep -q "^SLOT=" "$(logof s1t1)"'
RZ_TEST_NAME=R RZ_GATE_POLL=1 RZ_GATE_CMD="$fifo" gate "$W" s1r >/dev/null &
until_ '[[ -n "$(logof s1r)" ]] && grep -q "^STARVED" "$(logof s1r)"'
check 'grep -q "^STARVED" "$(logof s1r)"' "a room gate waiting past RZ_GATE_STARVE logs STARVED"
RZ_TEST_NAME=T2 RZ_GATE_TRAIN=1 RZ_GATE_POLL=0.1 RZ_GATE_CMD="$fifo" gate "$W" s1t2 >/dev/null &
until_ '[[ -n "$(logof s1t2)" ]] && grep -q "^WAITING" "$(logof s1t2)"'
check 'grep -q "^WAITING.*position 2 " "$(logof s1t2)"' "a train gate counts a starved room gate ahead of it"
before="$(date +%s)"; touch "$RZ_TEST_RELEASE"
wait
check '[[ "$(tr "\n" " " < "$RZ_TEST_ORDER")" == "T1 R T2 " ]]' "a starved room gate takes the slot before the next train, despite the reservation (order: $(tr '\n' ' ' < "$RZ_TEST_ORDER"))"
t="$(cat "$OVR" 2>/dev/null)"
check '[[ "$t" =~ ^[0-9]+$ ]] && (( t >= before ))' "the starved room gate stamps .room-override as it takes the slot (got '$t')"
check 'grep -qx EXIT=0 "$(logof s1r)" && grep -qx EXIT=0 "$(logof s1t2)"' "the starved room gate and the next train both reach a verdict"

# 16. At most one room gate per bound goes ahead of trains: R1 and R2 both
# wait past it behind T1, then T2 queues.  R1 goes, its override restarts
# R2's clock, so T2 goes next and R2 after (by the bound again, as T2's
# reservation would otherwise hold it 600 s).
rm -f "$RZ_TEST_RELEASE" "$RES" "$OVR"; : > "$RZ_TEST_ORDER"
RZ_TEST_NAME=T1 RZ_GATE_TRAIN=1 RZ_GATE_POLL=0.1 RZ_GATE_CMD="$hold" gate "$W" s2t1 >/dev/null &
until_ '[[ -n "$(logof s2t1)" ]] && grep -q "^SLOT=" "$(logof s2t1)"'
for x in 1 2; do
    RZ_TEST_NAME=R$x RZ_GATE_POLL=0.1 RZ_GATE_CMD="$fifo" gate "$W" s2r$x >/dev/null &
    until_ "[[ -n \"\$(logof s2r$x)\" ]] && grep -q '^WAITING' \"\$(logof s2r$x)\""
done
until_ 'grep -q "^STARVED" "$(logof s2r1)"'; sleep 0.5
RZ_TEST_NAME=T2 RZ_GATE_TRAIN=1 RZ_GATE_POLL=0.1 RZ_GATE_CMD="$fifo" gate "$W" s2t2 >/dev/null &
until_ '[[ -n "$(logof s2t2)" ]] && grep -q "^WAITING" "$(logof s2t2)"'
touch "$RZ_TEST_RELEASE"
wait
check '[[ "$(tr "\n" " " < "$RZ_TEST_ORDER")" == "T1 R1 T2 R2 " ]]' "one starved room gate per bound, then the train (order: $(tr '\n' ' ' < "$RZ_TEST_ORDER"))"
check 'grep -qx EXIT=0 "$(logof s2r2)"' "the second room gate still reaches a verdict within the bound"
unset RZ_GATE_STARVE
rm -f "$RES" "$OVR"

# 15. AGAST #3559: the gate tests the commit, not the worktree.  #3455's
# smoke_stack/core.py matched .gitignore's `core.*`, sat untracked in the
# room's worktree, and the gate passed a SHA that was missing it.  Here
# main.py imports helper.py, which .gitignore ignores, so only the worktree
# has it.
V="$T/wt15"
git init -q "$V"
printf 'helper.py\n' > "$V/.gitignore"
printf 'import helper\nprint(helper.X)\n' > "$V/main.py"
printf 'X = "from helper"\n' > "$V/helper.py"
printf 'scratch\n' > "$V/notes.ritz"   # untracked, not ignored
git -C "$V" add .gitignore main.py; git -C "$V" commit -qm "helper is ignored"
l15="$(RZ_GATE_CMD='python3 -B main.py' gate "$V" t15a)"
check 'grep -qx EXIT=1 "$l15"' "a commit missing an ignored module it imports fails the gate ($(grep '^EXIT=' "$l15"))"
check 'grep -q "No module named .helper." "$l15"' "the failure is the missing module, as CI would see it"
check 'grep -q "^NOT IN COMMIT helper.py (ignored: .gitignore:1:helper.py)" "$l15"' "the log names the ignored file and the rule that hides it"
check 'grep -q "^NOT IN COMMIT notes.ritz (untracked)" "$l15"' "the log names an untracked source file too"
gate --wait "$l15" > "$T/wait15" 2>&1
check 'grep -q "^NOT IN COMMIT helper.py" "$T/wait15"' "--wait prints the NOT IN COMMIT lines"
check '[[ "$(git -C "$V" worktree list | wc -l)" -eq 1 ]]' "the gate's checkout is removed after the gate"
check '[[ -z "$(ls -A "$RZ_GATE_DIR/.trees" 2>/dev/null)" ]]' "no checkout dir is left in the gate dir"
# The same tree, with helper.py committed: passes, from a checkout of the SHA.
git -C "$V" add -f helper.py; git -C "$V" commit -qm "commit helper"
S15="$(git -C "$V" rev-parse HEAD)"
l15="$(RZ_GATE_CMD='python3 -B main.py && pwd -P > "$RZ_TEST_ORDER.pwd" && git rev-parse HEAD > "$RZ_TEST_ORDER.head"' gate "$V" t15b)"
check 'grep -qx EXIT=0 "$l15" && grep -qx "from helper" "$l15"' "the same code with the module committed passes"
check '! grep -q "^NOT IN COMMIT helper.py" "$l15"' "a committed file is not reported"
check '[[ "$(cat "$RZ_TEST_ORDER.pwd")" != "$(cd "$V" && pwd -P)" ]]' "the command ran outside the room's worktree"
check '[[ "$(cat "$RZ_TEST_ORDER.head")" == "$S15" ]]' "the command ran on a checkout of the gated SHA"
# Section 4's commit moves the checkout's HEAD; one in the room's worktree
# during the gate still voids it too.
l15="$(RZ_GATE_CMD="git -C '$V' commit --allow-empty -qm move" gate "$V" t15m)"
gate --wait "$l15" >/dev/null 2>&1; rc=$?
check '[[ $rc -eq 99 ]] && grep -q "^HEAD MOVED during the gate" "$l15"' "--wait exits 99 when the room's HEAD moved, got $rc"
git -C "$V" reset -q --hard "$S15"
# A checkout left by a unit killed outright (no trap) doesn't block the next gate.
mkdir -p "$RZ_GATE_DIR/.trees/ritz-gate-t15c/stale"
l15="$(RZ_GATE_CMD='test ! -e stale' gate "$V" t15c)"
check 'grep -qx EXIT=0 "$l15"' "a stale checkout from a killed gate is replaced ($(grep '^EXIT=' "$l15"))"
check '[[ ! -e "$RZ_GATE_DIR/.trees/ritz-gate-t15c" ]]' "and removed afterwards"

# 16. The repo's .gitignore ignores core dumps, not sources named core
# (AGAST #3559: `core.*` hid smoke_stack/core.py from #3455's commit).
R="$(git -C "$HERE" rev-parse --show-toplevel)"
ign() { git -C "$R" check-ignore -q --no-index -- "$1"; }
for p in core projects/x/core core.1234 projects/x/core.98765; do
    check 'ign "$p"' ".gitignore ignores the core dump $p"
done
for p in projects/ritz/tools/smoke_stack/core.py projects/x/core.ritz projects/x/core.toml projects/x/core/mod.ritz; do
    check '! ign "$p"' ".gitignore doesn't ignore the source $p"
done

# 17. The gate's own exec-able TMPDIR (AGAST #3704): bangerang's /tmp is
# noexec, so every gate failed running what smoke built there.
git -C "$W" reset -q --hard "$SHA"
GT="$RZ_GATE_DIR/.trees/ritz-gate-t17.tmp"
cmd17='echo "$TMPDIR" > "$RZ_TEST_ORDER.tmpdir"
python3 -c "import tempfile; print(tempfile.gettempdir())" > "$RZ_TEST_ORDER.pytmp"
x="$(mktemp)" && printf "#!/bin/sh\necho ran-from-tmp\n" > "$x" && chmod +x "$x" && "$x"'
l17="$(RZ_GATE_CMD="$cmd17" gate "$W" t17)"
check 'grep -qx EXIT=0 "$l17" && grep -qx ran-from-tmp "$l17"' "the command runs a binary from its TMPDIR ($(grep '^EXIT=' "$l17"))"
check '[[ "$(cat "$RZ_TEST_ORDER.tmpdir")" == "$GT" ]]' "the command's TMPDIR is <gate dir>/.trees/<unit>.tmp (got $(cat "$RZ_TEST_ORDER.tmpdir"))"
check '[[ "$(cat "$RZ_TEST_ORDER.pytmp")" == "$GT" ]]' "python's tempfile (and so pytest's tmp_path) follows it"
check '[[ "$(grep -c "^TMPDIR=" "$l17")" -eq 1 ]] && sed "/^WAITING/q" "$l17" | grep -qx "TMPDIR=$GT"' "the log names the TMPDIR once, in its header (before WAITING)"
check '[[ ! -e "$GT" ]]' "the gate's TMPDIR is removed afterwards"
# AGAST #4274: some tests leave a dir with no read/search permission (mode
# 000), as pytest basetemps on bangerang did; `chmod -R u+w` can't descend
# into one, so the dir and the TMPDIR around it survived the gate.
l17="$(RZ_GATE_CMD='mkdir -p "$TMPDIR/pytest-of-u/pytest-0/t/noread" && touch "$TMPDIR/pytest-of-u/pytest-0/t/noread/f" && chmod 000 "$TMPDIR/pytest-of-u/pytest-0/t/noread" "$TMPDIR/pytest-of-u/pytest-0/t"' gate "$W" t17)"
check 'grep -qx EXIT=0 "$l17"' "a command leaving a mode-000 dir in its TMPDIR passes ($(grep '^EXIT=' "$l17"))"
check '[[ ! -e "$GT" ]]' "and the TMPDIR is removed anyway, mode-000 dirs and all"
# The probe is the one smoke uses, called on the gate's dir before any step.
cat > "$T/bin/probe-ok" <<'STUB'
#!/usr/bin/env bash
echo "$*" > "$RZ_TEST_ORDER.probe-args"; [[ -d "$2" && -w "$2" ]]
STUB
cat > "$T/bin/probe-noexec" <<'STUB'
#!/usr/bin/env bash
echo "SETUP ERROR: TMPDIR $2 can't run binaries: stub noexec"; exit 3
STUB
chmod +x "$T/bin/probe-ok" "$T/bin/probe-noexec"
l17="$(RZ_GATE_PROBE="$T/bin/probe-ok" RZ_GATE_CMD='exit 0' gate "$W" t17)"
check '[[ "$(cat "$RZ_TEST_ORDER.probe-args")" == "probe $GT" ]]' "the probe is asked about the gate's TMPDIR, which exists by then"
check 'grep -qx EXIT=0 "$l17"' "a passing probe lets the command run"
real="$(cd "$HERE/../../.." && pwd -P)/projects/ritz/tools/exec_tmpdir.py"
check '[[ -x "$real" ]] && "$real" probe "$T"' "the default probe is the repo's tools/exec_tmpdir.py, and it passes here"
# A TMPDIR that can't run a file: SETUP ERROR naming it, and nothing runs.
rm -f "$RZ_TEST_ORDER.ran17"
l17="$(RZ_GATE_PROBE="$T/bin/probe-noexec" RZ_GATE_CMD='touch "$RZ_TEST_ORDER.ran17"' gate "$W" t17)"
gate --wait "$l17" > "$T/wait17" 2>&1; rc=$?
check '[[ $rc -eq 2 ]]' "--wait exits 2 when the TMPDIR fails the probe, got $rc"
check 'grep -q "^SETUP ERROR: the gate.s TMPDIR $GT can.t run binaries" "$l17"' "the log says SETUP ERROR and names the dir"
check 'grep -q "^SETUP ERROR" "$T/wait17"' "--wait prints the SETUP ERROR line"
check '[[ ! -e "$RZ_TEST_ORDER.ran17" ]]' "the command never ran"
check '[[ ! -e "$GT" && ! -e "$RZ_GATE_DIR/.trees/ritz-gate-t17" ]]' "the TMPDIR and checkout are removed after a SETUP ERROR"
# One left by a unit killed outright (no trap) is cleared, read-only or not.
mkdir -p "$GT/stale/ro"; chmod a-w "$GT/stale/ro" "$GT/stale"
l17="$(RZ_GATE_CMD='test ! -e "$TMPDIR/stale"' gate "$W" t17)"
check 'grep -qx EXIT=0 "$l17"' "a stale TMPDIR from a killed gate is replaced ($(grep '^EXIT=' "$l17"))"
check '[[ ! -e "$GT" ]]' "and removed afterwards"

# 18. The diff base (AGAST #4027): ci-local --diff-base skips the ritz0 step
#     when nothing since the base can reach it.  No origin/main and no
#     RZ_GATE_BASE: no base, so the default command passes none (step runs).
#     Built from the default CMD, so unset RZ_GATE_CMD and read the header only.
base_of() { grep '^BASE=' "$1" | head -1 | cut -d= -f2; }
cmd_of() { grep '^CMD=' "$1" | head -1; }
gate_hdr() { env -u RZ_GATE_CMD timeout 30 bash "$G" "$@"; }
# The default CMD would run make; give the stub tree a make that records argv.
cat > "$T/bin/make" <<'STUB'
#!/usr/bin/env bash
echo "make $*" >> "$RZ_TEST_ORDER.make"
STUB
chmod +x "$T/bin/make"
W18="$T/wt18"
git init -q "$W18"; echo a > "$W18/a"; git -C "$W18" add a; git -C "$W18" commit -qm init
B18="$(git -C "$W18" rev-parse HEAD)"
echo b > "$W18/b"; git -C "$W18" add b; git -C "$W18" commit -qm two
rm -f "$RZ_TEST_ORDER.make"
l18="$(gate_hdr "$W18" t18)"
check '[[ -z "$(base_of "$l18")" ]] && grep -qx "BASE=" "$l18"' "no origin/main, no RZ_GATE_BASE: an empty BASE= line"
check '! cmd_of "$l18" | grep -q -- --diff-base' "and no --diff-base in the command"
check 'grep -q "ci-local ARGS=--fail-fast --skip Smoke --job build-all" "$RZ_TEST_ORDER.make"' "make ci-local ran without --diff-base"
# A room gate: its merge-base with origin/main.
git -C "$W18" update-ref refs/remotes/origin/main "$B18"
rm -f "$RZ_TEST_ORDER.make"
l18="$(gate_hdr "$W18" t18)"
check '[[ "$(base_of "$l18")" == "$B18" ]]' "a room gate's base is its merge-base with origin/main"
check 'grep -q -- "--diff-base $B18 --job build-all" "$RZ_TEST_ORDER.make"' "and ci-local gets --diff-base <that sha>"
# A train: RZ_GATE_BASE wins, resolved to a full sha.
rm -f "$RZ_TEST_ORDER.make"
l18="$(RZ_GATE_BASE=HEAD gate_hdr "$W18" t18)"
H18="$(git -C "$W18" rev-parse HEAD)"
check '[[ "$(base_of "$l18")" == "$H18" ]]' "RZ_GATE_BASE wins, resolved to a full sha"
# A base that doesn't resolve is dropped, not passed on: the step runs.
rm -f "$RZ_TEST_ORDER.make"
l18="$(RZ_GATE_BASE=no-such-rev gate_hdr "$W18" t18)"
check '[[ -z "$(base_of "$l18")" ]] && ! grep -q -- --diff-base "$RZ_TEST_ORDER.make"' "an unresolvable RZ_GATE_BASE is dropped"
rm -f "$T/bin/make"

# AGAST #4138: host.env's RZ_TEST_BUDGET_SCALE reaches the gate's command as
# RZ_TEST_BUDGET_SCALE (main.yml hands it to the budget check alone), never
# as RITZ_TEST_BUDGET_SCALE, which pytest would inherit.  Logged in the header.
probe='echo "SCALE=[${RZ_TEST_BUDGET_SCALE:-}] RITZ=[${RITZ_TEST_BUDGET_SCALE:-}]"'
l19="$(RZ_GATE_CMD="$probe" gate "$W" t19)"
check 'grep -qx "SCALE=\[\] RITZ=\[\]" "$l19" && grep -qx "BUDGET_SCALE=" "$l19"' "no host.env key: the command sees no scale"
printf 'RZ_GATE_SLOTS=1\nRZ_TEST_BUDGET_SCALE=1.5\n' > "$T/scale.env"
l19="$(RZ_HOST_ENV="$T/scale.env" RZ_GATE_CMD="$probe" gate "$W" t19)"
check 'grep -qx "SCALE=\[1.5\] RITZ=\[\]" "$l19"' "host.env's scale reaches the command as RZ_TEST_BUDGET_SCALE only"
check 'grep -qx "BUDGET_SCALE=1.5" "$l19"' "the log header names the scale"
l19="$(RZ_HOST_ENV="$T/scale.env" RZ_TEST_BUDGET_SCALE=2 RZ_GATE_CMD="$probe" gate "$W" t19)"
check 'grep -qx "SCALE=\[2\] RITZ=\[\]" "$l19"' "RZ_TEST_BUDGET_SCALE in the caller's env overrides host.env"
out="$(RZ_TEST_BUDGET_SCALE=fast RZ_GATE_CMD="$probe" gate "$W" t19 2>&1)"; rc=$?
check '[[ $rc -eq 2 ]] && [[ "$out" == *RZ_TEST_BUDGET_SCALE* ]]' "a malformed override is refused (rc=$rc)"
printf 'RZ_TEST_BUDGET_SCALE=0\n' > "$T/scale0.env"
out="$(RZ_HOST_ENV="$T/scale0.env" RZ_GATE_CMD="$probe" gate "$W" t19 2>&1)"; rc=$?
check '[[ $rc -eq 2 ]] && [[ "$out" == *host.env* || "$out" == *scale0.env* ]]' "a zero scale in host.env is refused (rc=$rc)"

# AGAST #4172: host.env's RZ_CPU_FACTOR (a host's fixed CPU factor) reaches the
# gate's command as RZ_CPU_FACTOR (main.yml hands it to cpu_calibrate.py as
# --factor, never to pytest); the caller's env overrides the file.  The header
# says where the factor comes from.
probe='echo "FACTOR=[${RZ_CPU_FACTOR:-}]"'
l20="$(RZ_GATE_CMD="$probe" gate "$W" t20)"
check 'grep -qx "FACTOR=\[\]" "$l20" && grep -qx "CPU_FACTOR=(measured)" "$l20"' "no RZ_CPU_FACTOR: the command sees none and the header says measured"
printf 'RZ_GATE_SLOTS=1\nRZ_CPU_FACTOR=1.67\n' > "$T/factor.env"
l20="$(RZ_HOST_ENV="$T/factor.env" RZ_GATE_CMD="$probe" gate "$W" t20)"
check 'grep -qx "FACTOR=\[1.67\]" "$l20" && grep -qx "CPU_FACTOR=1.67 (host.env)" "$l20"' "host.env's factor reaches the command and the header"
l20="$(RZ_HOST_ENV="$T/factor.env" RZ_CPU_FACTOR=2 RZ_GATE_CMD="$probe" gate "$W" t20)"
check 'grep -qx "FACTOR=\[2\]" "$l20" && grep -qx "CPU_FACTOR=2 (environment)" "$l20"' "RZ_CPU_FACTOR in the caller's env overrides host.env"
out="$(RZ_CPU_FACTOR=1e3 RZ_GATE_CMD="$probe" gate "$W" t20 2>&1)"; rc=$?
check '[[ $rc -eq 2 ]] && [[ "$out" == *RZ_CPU_FACTOR* ]]' "a malformed factor override is refused (rc=$rc)"

# 21. Reserved train slots (AGAST #4031): RZ_TRAIN_SLOTS of a host's slots
# (the top ones) only train gates take; room gates get the rest.  2 slots, 1
# reserved: slot 1 is the train's, slot 0 everyone's.
export RZ_GATE_SLOTS=2 RZ_TRAIN_SLOTS=1 RZ_GATE_POLL=0.1
slotof() { sed -n 's/^SLOT=\([0-9]*\) .*/\1/p' "$1"; }
rm -f "$RZ_TEST_RELEASE" "$RES" "$MARK"; : > "$RZ_TEST_ORDER"
# 21a. A train gate on an idle host takes its reserved slot, not slot 0.
l20="$(RZ_GATE_TRAIN=1 RZ_GATE_CMD='exit 0' gate "$W" v1t)"
check '[[ "$(slotof "$l20")" == 1 ]]' "a train gate takes a reserved slot first (SLOT=$(slotof "$l20"))"
rm -f "$RES"
# 21b. Room gate A holds slot 0; room gate B can't take the free reserved slot.
RZ_TEST_NAME=A RZ_GATE_CMD="$hold" gate "$W" v2a >/dev/null &
until_ '[[ -n "$(logof v2a)" ]] && grep -q "^SLOT=" "$(logof v2a)"'
check '[[ "$(slotof "$(logof v2a)")" == 0 ]]' "a room gate takes a general slot"
RZ_GATE_CMD='exit 0' timeout 3 bash "$G" "$W" v2b >/dev/null; rc=$?
check '[[ $rc -eq 124 ]] && ! grep -q "^SLOT=" "$(logof v2b)"' "a room gate can't take a reserved slot, though it is free (rc=$rc)"
stop "$(logof v2b)"; until_ '[[ ! -e "$RZ_TEST_ACTIVE/ritz-gate-v2b" ]]'
# ...but a train gate takes it at once, while A still runs.
l20="$(RZ_GATE_TRAIN=1 RZ_GATE_CMD='exit 0' timeout 10 bash "$G" "$W" v2t)"; rc=$?
check '[[ $rc -eq 0 && "$(slotof "$l20")" == 1 ]] && grep -qx EXIT=0 "$l20"' "a train gate takes the reserved slot while room gates fill the rest (rc=$rc)"
# 21c. A host with reserved slots ignores .train-reserved: the next train has
# its own slot, so the time reservation would only idle the general ones.
date +%s > "$RES"
touch "$RZ_TEST_RELEASE"; wait
l20="$(RZ_GATE_CMD='exit 0' timeout 10 bash "$G" "$W" v3r)"; rc=$?
check '[[ $rc -eq 0 && "$(slotof "$l20")" == 0 ]]' "a room gate ignores .train-reserved on a host with reserved train slots (rc=$rc)"
# 21d. A train gate may also take a free general slot: T1 holds the reserved
# one, T2 takes slot 0.
rm -f "$RZ_TEST_RELEASE" "$RES"
RZ_TEST_NAME=T1 RZ_GATE_TRAIN=1 RZ_GATE_CMD="$hold" gate "$W" v4a >/dev/null &
until_ '[[ -n "$(logof v4a)" ]] && grep -q "^SLOT=" "$(logof v4a)"'
l20="$(RZ_GATE_TRAIN=1 RZ_GATE_CMD='exit 0' timeout 10 bash "$G" "$W" v4b)"; rc=$?
check '[[ $rc -eq 0 && "$(slotof "$l20")" == 0 ]]' "a train gate takes a free general slot when its reserved ones are full (rc=$rc)"
touch "$RZ_TEST_RELEASE"; wait
# 21e. A starved room gate still can't take a reserved slot.
rm -f "$RZ_TEST_RELEASE" "$RES" "$OVR"
RZ_TEST_NAME=A RZ_GATE_CMD="$hold" gate "$W" v5a >/dev/null &
until_ '[[ -n "$(logof v5a)" ]] && grep -q "^SLOT=" "$(logof v5a)"'
RZ_GATE_STARVE=0 RZ_GATE_CMD='exit 0' timeout 3 bash "$G" "$W" v5r >/dev/null; rc=$?
check '[[ $rc -eq 124 ]] && grep -q "^STARVED" "$(logof v5r)" && ! grep -q "^SLOT=" "$(logof v5r)"' "a starved room gate still can't take a reserved slot (rc=$rc)"
stop "$(logof v5r)"; until_ '[[ ! -e "$RZ_TEST_ACTIVE/ritz-gate-v5r" ]]'
touch "$RZ_TEST_RELEASE"; wait
rm -f "$RES" "$OVR" "$MARK"
# 21f. Validation: not below the slot count, or not a number, refuses.
out="$(RZ_TRAIN_SLOTS=2 RZ_GATE_CMD='exit 0' gate "$W" v6 2>&1)"; rc=$?
check '[[ $rc -eq 2 && "$out" == *"must be below RZ_GATE_SLOTS"* ]]' "RZ_TRAIN_SLOTS >= RZ_GATE_SLOTS is refused (rc=$rc)"
out="$(RZ_TRAIN_SLOTS=x RZ_GATE_CMD='exit 0' gate "$W" v6 2>&1)"; rc=$?
check '[[ $rc -eq 2 && "$out" == *RZ_TRAIN_SLOTS* ]]' "a malformed RZ_TRAIN_SLOTS is refused (rc=$rc)"
printf 'RZ_GATE_SLOTS=6\nRZ_TRAIN_SLOTS=2\n' > "$T/train.env"
l20="$(env -u RZ_GATE_SLOTS -u RZ_TRAIN_SLOTS RZ_HOST_ENV="$T/train.env" RZ_GATE_TRAIN=1 RZ_GATE_CMD="exit 0" timeout 30 bash "$G" "$W" v6)"
check '[[ "$(slotof "$l20")" == 5 ]] && grep -qx "SLOTS=6 TRAIN_SLOTS=2" "$l20"' "host.env's RZ_TRAIN_SLOTS=2 of 6 is read and logged (SLOT=$(slotof "$l20"))"
printf 'RZ_TRAIN_SLOTS=-1\n' > "$T/bad.env"
out="$(env -u RZ_GATE_SLOTS -u RZ_TRAIN_SLOTS RZ_HOST_ENV="$T/bad.env" RZ_GATE_CMD="exit 0" timeout 30 bash "$G" "$W" v6 2>&1)"; rc=$?
check '[[ $rc -eq 2 && "$out" == *bad.env* ]]' "host.env's malformed RZ_TRAIN_SLOTS is refused (rc=$rc)"
# 21g. rz_train_free: free slots a train gate could take, minus queued trains.
free() { (source "$HERE/../../host-env.sh"; rz_train_free "$RZ_GATE_DIR"); }
check '[[ "$(free)" == 2 ]]' "rz_train_free: an idle 2-slot host has 2 ($(free))"
exec 7>>"$RZ_GATE_DIR/.gate-slot-0"; flock -n 7
check '[[ "$(free)" == 1 ]]' "rz_train_free: a room gate on slot 0 leaves the reserved one ($(free))"
exec 6>>"$RZ_GATE_DIR/.gate-slot-1"; flock -n 6
check '[[ "$(free)" == 0 ]]' "rz_train_free: every slot held is 0 ($(free))"
exec 6>&-
sleep 300 & qp=$!
echo "ritz-gate-q $qp 1 $(date +%s)" > "$Q"
check '[[ "$(free)" == 0 ]]' "rz_train_free: a queued live train gate claims the free slot ($(free))"
echo "ritz-gate-q $qp 0 $(date +%s)" > "$Q"
check '[[ "$(free)" == 1 ]]' "rz_train_free: a queued room gate doesn't ($(free))"
kill $qp; wait $qp 2>/dev/null; : > "$Q"; exec 7>&-
check '[[ "$(RZ_TRAIN_SLOTS=5 free 2>/dev/null)" == 0 ]]' "rz_train_free: a bad slot config is 0"
unset RZ_TRAIN_SLOTS RZ_GATE_POLL; export RZ_GATE_SLOTS=1

# 22. No run-gate scratch in the worktree it tests (AGAST #4420).  A caller
# kept the log's path in an untracked `.gate-log-name` at the worktree root so
# a later turn could --wait; at teardown `adele room rm` refused the dirty
# worktree until it was moved by hand.  A gate now removes it on every exit
# path, so `git status --porcelain` is the same before and after.
V22="$T/wt22"
git init -q "$V22"; echo a > "$V22/a"; git -C "$V22" add a; git -C "$V22" commit -qm init
clean22() { [[ -z "$(git -C "$V22" status --porcelain)" ]]; }
# Section 21f's train gate reserved the slot as it ended (#3427): a room gate
# with no reserved train slots would wait out RZ_GATE_TRAIN_HOLD.
rm -f "$RES" "$MARK" "$OVR"
printf 'gate-logs/22-scratch-1.log\n' > "$V22/.gate-log-name"
check '! clean22' "the caller's scratch dirties the worktree before the gate"
l22="$(RZ_GATE_CMD='exit 0' gate "$V22" t22p)"
check 'grep -qx EXIT=0 "$l22"' "a passing gate still passes"
check '[[ ! -e "$V22/.gate-log-name" ]]' "a passing gate removes the caller's scratch"
check 'clean22' "the worktree is unchanged after a passing gate"
printf 'gate-logs/22-scratch-2.log\n' > "$V22/.gate-log-name"
l22="$(RZ_GATE_CMD='exit 2' gate "$V22" t22f)"
check 'grep -qx EXIT=2 "$l22"' "a failing gate still fails"
check '[[ ! -e "$V22/.gate-log-name" ]]' "a failing gate removes the scratch too"
check 'clean22' "the worktree is unchanged after a failing gate"
# The `timeout 540` around a --wait (exit 124) is the one path where the unit
# may still be running: the wait itself must clean before it dies.
printf 'gate-logs/22-scratch-3.log\n' > "$V22/.gate-log-name"
W22="$RZ_GATE_DIR/t22-still-running.log"
printf 'UNIT=ritz-gate-t22w\nSHA=%s\nWT=%s\n' "$(git -C "$V22" rev-parse HEAD)" "$V22" > "$W22"
touch "$RZ_TEST_ACTIVE/ritz-gate-t22w"
timeout 2 bash "$G" --wait "$W22" >/dev/null 2>&1; rc=$?
rm -f "$RZ_TEST_ACTIVE/ritz-gate-t22w"
check '[[ $rc -eq 124 ]]' "--wait killed by timeout exits 124, got $rc"
check '[[ ! -e "$V22/.gate-log-name" ]]' "a timed-out --wait removes the scratch"
check 'clean22' "the worktree is unchanged after a timed-out --wait"
# A *tracked* .gate-log-name is the caller's content, never deleted.
printf 'x\n' > "$V22/.gate-log-name"
git -C "$V22" add .gate-log-name; git -C "$V22" commit -qm keep
l22="$(RZ_GATE_CMD='exit 0' gate "$V22" t22k)"
check '[[ -e "$V22/.gate-log-name" ]]' "a tracked .gate-log-name is left alone"
check 'clean22' "and the tracked worktree stays unchanged"

# 23. A venv that doesn't match the commit's requirements.lock (AGAST #4583)
# is a SETUP ERROR, not a test failure: the command never runs.  The fake
# venv's python3 is the real one with a site dir of hand-made dist-infos: a
# pin installed under its other spelling (rzfake_a), one at the wrong version
# (rzfake-b), one missing (rzfake-missing), one right (rzfake-c).
fakedist() {   # fakedist <site> <name> <version>
    mkdir -p "$1/$2-$3.dist-info"
    printf 'Metadata-Version: 2.1\nName: %s\nVersion: %s\n' "$2" "$3" > "$1/$2-$3.dist-info/METADATA"
}
realpy="$(command -v python3)"
mkdir -p "$T/venv23/bin"
printf '#!/bin/sh\nPYTHONPATH="%s" exec "%s" "$@"\n' "$T/site23" "$realpy" > "$T/venv23/bin/python3"
chmod +x "$T/venv23/bin/python3"
fakedist "$T/site23" rzfake_a 1.0; fakedist "$T/site23" rzfake-b 1.9; fakedist "$T/site23" rzfake-c 3.0
V23="$T/wt23"
git init -q "$V23"; mkdir -p "$V23/projects/ritz"
printf '# a comment\nrzfake-a==1.0\nrzfake-b==2.0   # wrong version\n\nrzfake-missing==1.0\nrzfake-c==3.0\n' \
    > "$V23/projects/ritz/requirements.lock"
git -C "$V23" add -A; git -C "$V23" commit -qm lock
rm -f "$RZ_TEST_ORDER.ran23"
l23="$(PATH="$T/venv23/bin:$PATH" RZ_GATE_CMD='touch "$RZ_TEST_ORDER.ran23"' gate "$V23" t23)"
gate --wait "$l23" > "$T/wait23" 2>&1; rc=$?
check '[[ $rc -eq 2 ]]' "--wait exits 2 when the venv doesn't match the lock, got $rc"
check 'grep -q "^SETUP ERROR: this host.s python3 ($T/venv23/bin/python3) does not match projects/ritz/requirements.lock" "$l23"' \
    "the log says SETUP ERROR and names the python3"
check 'grep -q "rzfake-b==2.0 (installed 1.9)" "$l23"' "it names the pin at the wrong version"
check 'grep -q "rzfake-missing==1.0 (not installed)" "$l23"' "it names the missing pin"
check '! grep -q "rzfake-a==\|rzfake-c==" "$l23"' "it names no pin that matches (rzfake_a is rzfake-a, PEP 503)"
check 'grep -q "pip install -r projects/ritz/requirements.lock" "$l23"' "it says how to fix the venv"
check 'grep -q "^SETUP ERROR: this host" "$T/wait23"' "--wait prints the SETUP ERROR line"
check '[[ ! -e "$RZ_TEST_ORDER.ran23" ]]' "the command never ran on the stale venv"
# Synced: the gate runs.
rm -rf "$T/site23/rzfake-b-1.9.dist-info"; fakedist "$T/site23" rzfake-b 2.0; fakedist "$T/site23" rzfake_missing 1.0
l23="$(PATH="$T/venv23/bin:$PATH" RZ_GATE_CMD='touch "$RZ_TEST_ORDER.ran23"' gate "$V23" t23)"
check 'grep -qx EXIT=0 "$l23" && [[ -e "$RZ_TEST_ORDER.ran23" ]]' "a venv that matches the lock runs the command"
# A commit with no lock (every gate above) checks nothing: the same stale
# venv still runs a lockless tree.
rm -rf "$T/site23/rzfake-b-2.0.dist-info"
l23="$(PATH="$T/venv23/bin:$PATH" RZ_GATE_CMD='exit 0' gate "$W" t23n)"
check 'grep -qx EXIT=0 "$l23" && ! grep -q "^SETUP ERROR" "$l23"' "a commit without requirements.lock checks nothing"

echo
[[ $fails -eq 0 ]] && { echo "all passed"; exit 0; }
echo "$fails failed"; exit 1
