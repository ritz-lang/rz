#!/usr/bin/env bash
# Tests for run-gate.sh with systemd-run and systemctl stubbed out, so the gate
# runs in the foreground against a throwaway repo.  Run: bash test-run-gate.sh
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
T="$(mktemp -d)"; trap 'chmod -R u+w "$T"; rm -rf "$T"' EXIT
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
RZ_GATE_POLL=0.1 RZ_GATE_CMD='echo B >> "$RZ_TEST_ORDER"' gate "$W" pb >/dev/null &
until_ '[[ -n "$(logof pb)" ]] && grep -q "^WAITING" "$(logof pb)"'
sleep 0.5
touch "$RZ_TEST_RELEASE"
wait
check '[[ "$(tr "\n" " " < "$RZ_TEST_ORDER")" == "A T B " ]]' "train gate T takes the freed slot before room gate B (order: $(tr '\n' ' ' < "$RZ_TEST_ORDER"))"
check 'grep -qx EXIT=0 "$(logof pt)" && grep -qx EXIT=0 "$(logof pb)"' "both queued gates still reach a verdict"
check '[[ -s "$RZ_TEST_ORDER.during-t" ]] && ! grep -qx .train-waiting "$RZ_TEST_ORDER.during-t"' "the train's marker is gone once it has its slot (not only at exit)"
check '[[ ! -e "$MARK" ]]' "no marker is left after the train gate ends"

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

echo
[[ $fails -eq 0 ]] && { echo "all passed"; exit 0; }
echo "$fails failed"; exit 1
