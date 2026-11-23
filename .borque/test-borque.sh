#!/usr/bin/env bash
# Tests for .borque/ (AGAST #3722): the profile parses with Borque's own
# validator, and verify.sh / train-gate.sh block and return the gate's code.
#
#   bash .borque/test-borque.sh
#
# Part 1 stubs run-gate.sh itself (RZ_GATE_SCRIPT) to pin the wrappers'
# contract: argv, env, exit codes, the 124 retry.  Part 2 runs the real
# run-gate.sh with systemd stubbed and RZ_GATE_CMD as the gate, the way
# .claude/skills/rz-iterate/test-run-gate.sh does.  Part 3 parses the profile
# with `hostd.profile.parse(text, "ritz")` from a borque checkout (BORQUE_DIR,
# else ~/dev/nevelis/borque); without one it says SKIP and why.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO="$(cd "$HERE/.." && pwd -P)"
T="$(mktemp -d)"; trap 'chmod -R u+w "$T"; rm -rf "$T"' EXIT
fails=0
ok()  { echo "ok   - $1"; }
bad() { echo "FAIL - $1"; fails=$((fails + 1)); }
check() { if eval "$1"; then ok "$2"; else bad "$2"; fi; }
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
V="$HERE/verify.sh"
TG="$HERE/train-gate.sh"
# Bounded: a wrapper that loops forever fails here, it doesn't hang.
run() { timeout 60 bash "$@"; }

# A throwaway repo shaped like a train: origin/main is the base, HEAD is a
# commit on top of it.  $1 = the path the car touches.
make_train() {
    local w="$1" touched="$2"
    git init -q "$w"
    mkdir -p "$w/projects/ritz" "$w/projects/pkg"
    printf '[workspace]\n' > "$w/ritz.toml"
    printf '[package]\nname = "ritz"\n' > "$w/projects/ritz/ritz.toml"
    printf '[package]\nname = "pkg"\n' > "$w/projects/pkg/ritz.toml"
    echo a > "$w/projects/ritz/a.ritz"; echo a > "$w/projects/pkg/a.ritz"
    git -C "$w" add -A; git -C "$w" commit -qm base
    git -C "$w" update-ref refs/remotes/origin/main HEAD
    echo b >> "$w/$touched"; git -C "$w" commit -qam car
}

# --- Part 1: a stub run-gate.sh ----------------------------------------------
# Start: records argv and the env the wrappers set, prints a log path.
# --wait: pops its exit code from $STUB_CODES (one per line); "sleep" sleeps
# past the wrapper's wait slice once instead, so a real timeout is exercised.
STUB="$T/run-gate-stub.sh"
cat > "$STUB" <<'STUB'
#!/usr/bin/env bash
if [[ "$1" == "--wait" ]]; then
    echo "wait $2" >> "$STUB_CALLS"
    code="$(head -1 "$STUB_CODES")"; sed -i 1d "$STUB_CODES"
    if [[ "$code" == sleep ]]; then sleep 30; exit 0; fi
    echo "EXIT=$code"
    exit "$code"
fi
printf 'start wt=%s name=%s train=%s after=%s base=%s\n' "$1" "$2" \
    "${RZ_GATE_TRAIN-unset}" "${RZ_GATE_AFTER-unset}" "${RZ_GATE_BASE-unset}" >> "$STUB_CALLS"
[[ -n "${STUB_START_FAIL:-}" ]] && { echo "error: start failed" >&2; exit "$STUB_START_FAIL"; }
echo "$STUB_LOGDIR/$2-0123456789ab-1.log"
STUB
chmod +x "$STUB"
export STUB_CALLS="$T/calls" STUB_CODES="$T/codes" STUB_LOGDIR="$T/logs"
codes() { : > "$STUB_CALLS"; printf '%s\n' "$@" > "$STUB_CODES"; }
starts() { grep -c '^start ' "$STUB_CALLS"; }
waits() { grep -c '^wait ' "$STUB_CALLS"; }
export RZ_GATE_WAIT_SLICE=2

W="$T/room"; make_train "$W" projects/ritz/a.ritz

# verify.sh: the gate's own code comes back, whatever it is.
for want in 0 2 98 99; do
    codes "$want"
    out="$(RZ_GATE_SCRIPT="$STUB" run "$V" "$W" ritz-task-3722 2>&1)"; rc=$?
    check '[[ $rc -eq $want ]]' "verify.sh exits with the gate's code $want, got $rc"
done
check 'grep -q "^start wt=$W name=3722 " "$STUB_CALLS"' "verify.sh names the gate after the task id (3722), in the room's worktree"
check 'grep -q "train=unset after=unset base=unset" "$STUB_CALLS"' "verify.sh is a room gate: no RZ_GATE_TRAIN, no RZ_GATE_AFTER"
check '[[ "$(sed -n 2p "$STUB_CALLS")" == "wait $STUB_LOGDIR/3722-0123456789ab-1.log" ]]' "verify.sh waits on the log that start printed"
check 'grep -q "3722-0123456789ab-1.log" <<<"$out"' "verify.sh prints the log path"

# A wait slice that times out (124) is retried, never returned.
codes 124 124 2
RZ_GATE_SCRIPT="$STUB" run "$V" "$W" ritz-task-3722 >/dev/null 2>&1; rc=$?
check '[[ $rc -eq 2 && $(waits) -eq 3 && $(starts) -eq 1 ]]' "verify.sh retries the wait on 124 and returns the verdict (rc=$rc, waits=$(waits), starts=$(starts))"
codes sleep 0
RZ_GATE_SCRIPT="$STUB" run "$V" "$W" ritz-task-3722 >/dev/null 2>&1; rc=$?
check '[[ $rc -eq 0 && $(waits) -eq 2 ]]' "verify.sh bounds each wait by RZ_GATE_WAIT_SLICE and waits again (rc=$rc, waits=$(waits))"

# A gate that never started: its error, no wait.
codes 0
STUB_START_FAIL=1 RZ_GATE_SCRIPT="$STUB" run "$V" "$W" ritz-task-3722 >/dev/null 2>&1; rc=$?
check '[[ $rc -eq 1 && $(waits) -eq 0 ]]' "verify.sh returns run-gate.sh's start error and doesn't wait (rc=$rc)"

# A room whose name holds no task id: refused before any gate starts.
for room in ritz-task- other-3722 ritz-task-12x ""; do
    codes 0
    RZ_GATE_SCRIPT="$STUB" run "$V" "$W" "$room" >/dev/null 2>&1; rc=$?
    check '[[ $rc -ne 0 && $(starts) -eq 0 ]]' "verify.sh refuses room '$room' without starting a gate (rc=$rc)"
done
codes 0
RZ_GATE_SCRIPT="$STUB" run "$V" "$W" >/dev/null 2>&1; rc=$?
check '[[ $rc -ne 0 && $(starts) -eq 0 ]]' "verify.sh refuses a missing room argument (rc=$rc)"

# train-gate.sh: what `train.sh gate` sets.  No package-test step (AGAST
# #3970): the gate's test-all job tests every package (#3969), so a car
# touching a package gates as a compiler-only one does.
TP="$T/train-pkg"; make_train "$TP" projects/pkg/a.ritz
BASE="$(git -C "$TP" rev-parse origin/main)"
codes 0
RZ_GATE_SCRIPT="$STUB" run "$TG" "$TP" >/dev/null 2>&1; rc=$?
check '[[ $rc -eq 0 ]]' "train-gate.sh exits 0 for a passing gate, got $rc"
check '[[ "$(head -1 "$STUB_CALLS")" == "start wt=$TP name=train train=1 after=unset base=$BASE" ]]' \
    "train-gate.sh: RZ_GATE_TRAIN=1, name train, no RZ_GATE_AFTER, RZ_GATE_BASE=<merge-base with origin/main>"
# The base is the merge-base, so an origin/main that moved on since the
# train was built still gives the train's own base.
git -C "$TP" checkout -q -b moved "$BASE"; echo c > "$TP/later"; git -C "$TP" add later
git -C "$TP" commit -qm later; git -C "$TP" update-ref refs/remotes/origin/main HEAD
git -C "$TP" checkout -q -; codes 0
RZ_GATE_SCRIPT="$STUB" run "$TG" "$TP" >/dev/null 2>&1
check 'grep -q "base=$BASE\$" "$STUB_CALLS"' "train-gate.sh: the base is the train's, even after origin/main moves on"

for want in 2 98 99; do
    codes "$want"
    RZ_GATE_SCRIPT="$STUB" run "$TG" "$TP" >/dev/null 2>&1; rc=$?
    check '[[ $rc -eq $want ]]' "train-gate.sh exits with the gate's code $want, got $rc"
done
codes 124 0
RZ_GATE_SCRIPT="$STUB" run "$TG" "$TP" >/dev/null 2>&1; rc=$?
check '[[ $rc -eq 0 && $(waits) -eq 2 ]]' "train-gate.sh retries the wait on 124 (rc=$rc, waits=$(waits))"
codes 0
RZ_GATE_SCRIPT="$STUB" run "$TG" "$T/nonexistent" >/dev/null 2>&1; rc=$?
check '[[ $rc -ne 0 && $(starts) -eq 0 ]]' "train-gate.sh refuses a path that is not a git worktree (rc=$rc)"
NB="$T/no-origin"; git init -q "$NB"; git -C "$NB" commit -q --allow-empty -m x; codes 0
RZ_GATE_SCRIPT="$STUB" run "$TG" "$NB" >/dev/null 2>&1; rc=$?
check '[[ $rc -ne 0 && $(starts) -eq 0 ]]' "train-gate.sh refuses a worktree without origin/main (rc=$rc)"

# --- Part 2: the real run-gate.sh, systemd stubbed ---------------------------
# Same stubs as test-run-gate.sh: systemd-run runs the unit synchronously.
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
(
    export PATH="$T/bin:$PATH" RZ_GATE_DIR="$T/gates" RZ_HOST_ENV="$T/no-host.env" RZ_GATE_SLOTS=1
    unset RZ_GATE_SCRIPT
    S12="$(git -C "$W" rev-parse --short=12 HEAD)"
    out="$(RZ_GATE_CMD='echo gated; exit 0' run "$V" "$W" ritz-task-3722 2>&1)"; rc=$?
    check '[[ $rc -eq 0 ]]' "real gate: verify.sh exits 0 for a passing gate, got $rc"
    check '[[ -f "$RZ_GATE_DIR/3722-$S12-1.log" ]] && grep -qx EXIT=0 "$RZ_GATE_DIR/3722-$S12-1.log"' "real gate: log 3722-<sha12>-1.log holds EXIT=0"
    RZ_GATE_CMD='exit 2' run "$V" "$W" ritz-task-3722 >/dev/null 2>&1; rc=$?
    check '[[ $rc -eq 2 ]]' "real gate: verify.sh exits 2 for a failing gate, got $rc"

    # No package-test step after the gate command (AGAST #3970): a train
    # touching a package passes or fails on the gate command alone.
    T12="$(git -C "$TP" rev-parse --short=12 HEAD)"
    RZ_PKG_TEST=false RZ_GATE_CMD='exit 0' run "$TG" "$TP" >/dev/null 2>&1; rc=$?
    check '[[ $rc -eq 0 ]] && ! grep -q "Train package tests" "$RZ_GATE_DIR/train-$T12-1.log"' "real gate: train-gate.sh runs no package tests after the gate (rc=$rc)"
    RZ_GATE_CMD='exit 2' run "$TG" "$TP" >/dev/null 2>&1; rc=$?
    check '[[ $rc -eq 2 ]]' "real gate: train-gate.sh exits 2 when the gate command fails, got $rc"
    exit "$fails"
); fails=$((fails + $?))

# --- Part 3: the profile, with Borque's validator ----------------------------
P="$HERE/profile.toml"
BQ="${BORQUE_DIR:-$HOME/dev/nevelis/borque}"
if [[ -f "$BQ/hostd/profile.py" ]]; then
    out="$(cd "$BQ" && python3 -c '
import sys
from hostd import profile
p = profile.parse(open(sys.argv[1], "rb").read(), "ritz")
print(p["verify"]); print(p["train"]["gate"])
' "$P" 2>&1)"; rc=$?
    check '[[ $rc -eq 0 ]]' "profile.toml parses with hostd.profile.parse(text, \"ritz\") ($BQ): ${out//$'\n'/ | }"
else
    echo "SKIP - profile parse: no borque checkout at $BQ (set BORQUE_DIR; nevelis/borque is private, so CI has none)"
fi

# What the profile must say, read with tomllib (no borque needed).
out="$(python3 - "$P" "$REPO" <<'PY' 2>&1
import os, shlex, sys, tomllib
p = tomllib.load(open(sys.argv[1], "rb"))
repo = sys.argv[2]
want = {
    "project": "ritz",
    "room_prefix": "ritz-task-",
    "verify": ".borque/verify.sh {worktree} {room}",
    "hooks.provision": ".claude/provision-room.sh {worktree}",
    "hooks.budget": ".claude/host-budget.sh {room}",
    "hooks.teardown": [".claude/host-budget.sh --remove {room}",
                       ".claude/provision-room.sh --remove {worktree}"],
    "train.gate": ".borque/train-gate.sh {train_worktree}",
    "train.room_gate_equals_train_gate": False,
    "train.max_cars": 12,
    "deploy.paths": [],
}
bad = []
for key, value in want.items():
    node = p
    for part in key.split("."):
        node = node.get(part) if isinstance(node, dict) else None
    if node != value:
        bad.append(f"{key}={node!r}, want {value!r}")
# Only names hostd's probe reports (borque design §7.4): any other key
# matches no host, so the project could never be placed.
probed = {"git", "github-auth", "agast", "adele", "adele-oauth", "python", "pytest",
          "node", "npm", "docker", "llvm", "lld", "linger", "claude", "disk"}
for cap in p.get("needs", []):
    if cap not in probed and not cap.startswith(("llvm", "git-ssh.", "mirror.")):
        bad.append(f"needs: {cap} is not a probe capability")
if not 0 < p.get("reserve_mem_gib", 0) <= 16:
    bad.append(f"reserve_mem_gib={p.get('reserve_mem_gib')!r}")
cmds = [p["verify"], p["train"]["gate"], p["hooks"]["provision"], p["hooks"]["budget"], *p["hooks"]["teardown"]]
for cmd in cmds:
    exe = os.path.join(repo, shlex.split(cmd)[0])
    if not (os.path.isfile(exe) and os.access(exe, os.X_OK)):
        bad.append(f"{shlex.split(cmd)[0]}: not an executable file in the repo")
print("; ".join(bad) or "ok")
sys.exit(1 if bad else 0)
PY
)"; rc=$?
check '[[ $rc -eq 0 ]]' "profile.toml fields and hook scripts: $out"

echo
if [[ $fails -eq 0 ]]; then echo "ALL PASS"; else echo "$fails FAILED"; fi
exit $(( fails > 0 ))
