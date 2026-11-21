#!/usr/bin/env bash
#
# Run a room's verification gate so it cannot be killed, cannot overload the
# machine, and always ends in a verdict.
#
#   run-gate.sh <worktree> <name>      start the gate, print its log path
#                                      (<gate dir>/<name>-<sha12>-<n>.log)
#   run-gate.sh --wait <log>           block until it ends; exit with its code
#
# Env overrides:
#   RZ_GATE_CMD    command run from a checkout of <worktree>'s HEAD
#                                                (default: clean ci-local)
#   RZ_GATE_SLOTS  gates allowed at once         (default: host.env, else 1)
#   RZ_TRAIN_SLOTS of those, train gates only    (default: host.env, else 0)
#   RZ_HOST_ENV    per-host config file          (default: ~/.config/rz/host.env)
#   RZ_GATE_DIR    where logs and slot locks go  (default: ~/dev/ritz-lang/gate-logs)
#   RZ_GATE_POLL   seconds between slot polls    (default: 20; tests use less)
#   RZ_GATE_TRAIN  1 = a merge-train gate        (train.sh gate sets it)
#   RZ_GATE_AFTER  run after the command passes  (train.sh gate: its package
#                  tests, AGAST #3363)
#   RZ_GATE_TRAIN_HOLD  seconds a .train-reserved holds room gates (default 600)
#   RZ_GATE_STARVE seconds a room gate waits before it goes ahead of the
#                  merge trains (default 2700; AGAST #3578)
#
# Why each piece exists (rz-iterate):
#   * systemd-run: a Bash background job dies when the agent's next turn
#     starts (AGAST #1441).  Two #1436 gates died that way, silently.
#   * slots: 12 cores.  ci-local has 180 s timed tests; six concurrent gates
#     turn them into timeouts that look like regressions and are not.
#     Default is 1: concurrent gates OOM'd the WSL VM and took it down.
#     A bigger host raises it in ~/.config/rz/host.env (RZ_GATE_SLOTS=2 on
#     huburght, AGAST #2998; format in .claude/host-env.sh).  Not above 2 on
#     12 cores, for the timed tests' sake.  An RZ_GATE_SLOTS in the
#     environment still wins over the file.
#   * ritz-gate.slice at CPUWeight=100: the slot protects gates from gates,
#     not from room builds.  Task rooms run in ritz-rooms.slice at
#     CPUWeight=20 under a memory cap (.claude/host-budget.sh, AGAST #1811),
#     so under contention the gate gets 5x a room's share of the CPU.  Both
#     slices nest under ritz.slice, so they are siblings; in app.slice the
#     gate would be weighed against all of app-adele\x2dagent.slice instead.
#     No memory cap on the gate: an OOM kill there is a false red.
#   * SHA in the log name, and the HEAD-moved check: the callback claims a
#     specific commit passed.  A gate that ran while HEAD moved proves nothing.
#   * <name>-<sha12>-<n>.log, a new <n> per run: a re-gate never overwrites
#     an earlier run's log, so a false red's evidence outlives the re-gate
#     that clears it (AGAST #3182).  Tests: test-run-gate.sh.
#   * train priority (AGAST #3317): waiting units poll `flock -n` every 20 s,
#     so a freed slot went to whichever poll landed first, and room gates
#     queued later twice beat the train (which carries every REAP behind it).
#     A waiting train gate writes <gate dir>/.train-waiting (its unit name);
#     room gates take no slot while that unit is active.  The train removes
#     the marker on taking its slot or on exit (trap); a marker whose unit is
#     no longer active (a crash, a reboot) is stale and ignored.
#   * train reservation (AGAST #3365): between `train.sh land` and the next
#     `train.sh gate` (a minute or two: closing tickets, building the next
#     train) no train unit exists, so .train-waiting can't hold the slot,
#     and a room gate took it once and delayed a train ~15 min.  `land`
#     writes <gate dir>/.train-reserved (epoch seconds); room gates take no
#     slot while it is under RZ_GATE_TRAIN_HOLD seconds old (default 600, so
#     a coordinator that never gates again can't starve rooms).  A train gate
#     removes it once its .train-waiting is written, and `train.sh build`
#     removes it for a train that needs no gate.  Fails open: an old,
#     future-dated or unreadable marker is ignored.
#   * reservation from the train gate's end (AGAST #3427): the slot frees
#     when the train's gate ends, 30-60 s before `land` (the coordinator
#     reads the verdict first), and a room gate first in the FIFO took it
#     in that window five times in one day, ~20 min of train time each.  So
#     a train gate writes .train-reserved itself once its command is done,
#     while it still holds the slot and before its EXIT line; `land`
#     re-stamps it.  On a failed gate too: the coordinator re-gates a halved
#     train next, and that gate is worth more than any one room's.  A train
#     gate stopped or killed before its command ends reserves nothing.  A
#     room gate that wins the flock re-checks the reservation, in case the
#     train wrote it and released the slot between the check and the flock.
#   * FIFO queue (AGAST #3364): the same poll race reordered room gates too
#     (huburght, 2 slots: ~13 min waits, not in the order asked).  A waiter
#     appends "<unit> <pid> <train>" to <gate dir>/.gate-queue (under flock
#     on .gate-queue.lock) and tries the slots only while no live waiter is
#     ahead of it; a train gate counts only trains ahead (priority above).
#     It leaves the queue on taking a slot or on exit (trap).  An entry whose
#     pid is gone or whose unit is inactive (SIGKILL, reboot) is pruned, so a
#     dead waiter never blocks the queue.  The log's WAITING lines give the
#     position (1 = next).
#   * starvation bound (AGAST #3578): with one slot, train priority plus the
#     reservation meant a room gate never ran while REAPs kept coming: rz
#     gates the next train right after each land, and #3448/#3517 sat at
#     queue position 1 for 2h+ through seven trains.  Each queue line also
#     carries the time the waiter queued.  The oldest live room waiter is
#     "starved" once it has waited RZ_GATE_STARVE seconds (default 45 min),
#     counted from when it queued or from <gate dir>/.room-override,
#     whichever is later.  A starved room gate ignores .train-reserved and
#     .train-waiting, and train gates count it as ahead of them, so it takes
#     the next free slot.  On taking it, it stamps .room-override, which
#     restarts every room's clock: at most one room gate per RZ_GATE_STARVE
#     seconds goes ahead of trains, so trains can't be starved in turn.
#     With no starved waiter nothing changes (#3317, #3427).  A queue line
#     without a time (a gate started by an older run-gate.sh) never starves.
#   * reserved train slots (AGAST #4031): with one shared pool, a train only
#     got priority for the NEXT free slot, so train 2 sat queued on
#     huburght behind two room gates for a whole room gate.  RZ_TRAIN_SLOTS
#     (host.env) of the RZ_GATE_SLOTS slots, the top-numbered ones, are for
#     train gates (RZ_GATE_TRAIN=1) only; room gates, starved or not, take
#     slots 0..SLOTS-TRAIN_SLOTS-1.  A train gate tries its reserved slots
#     first (top down), so the general ones stay free for rooms, then any
#     free general slot.  Must be below RZ_GATE_SLOTS (else no room gate
#     ever runs).  On such a host room gates ignore .train-reserved: the
#     next train has its own slot, and the time reservation would only idle
#     a general one.  The log header says SLOTS=<n> TRAIN_SLOTS=<m>.
#     train.sh asks rz_train_free (host-env.sh) whether a host has a slot
#     free for a train before it sends one there.
#   * script by path (AGAST #3567): systemd unescapes and expands `$` in a
#     unit's command line (`$$` -> `$`, `${x}` -> x from the unit's env, or
#     empty), so `bash -c "$INNER"` ran a mangled script: every queue pid was
#     a literal `$`, each waiter pruned the others as dead, and the FIFO was
#     random.  The script goes to <log minus .log>.unit.sh, which the unit
#     deletes as it starts; --setenv values are not expanded, so the env
#     carries the rest.  Tests: test-run-gate-systemd.sh (real systemd-run).
#   * a checkout of the SHA, not the room's worktree (AGAST #3559): #3455's
#     tools/smoke_stack/core.py matched .gitignore's `core.*`, so it sat
#     untracked in the room's worktree, the gate there passed, and the SHA
#     it vouched for failed the train with ModuleNotFoundError.  So once it
#     has a slot the unit runs `git worktree add --detach
#     <gate dir>/.trees/<unit> <sha>`, runs the command there, and removes
#     the checkout on exit (trap; a run killed outright leaves one that the
#     unit's next run clears).  The
#     build caches that matter are outside the tree (the CAS in
#     ~/.cache/ritz), and the gate wipes ritz1/build anyway, so the checkout
#     costs about a second.  The log lists the worktree's ignored or
#     untracked sources (*.py, *.ritz, *.toml, Makefile; build dirs left
#     out) as "NOT IN COMMIT <file> (ignored: <rule>)", so a failure on a
#     missing file names it; --wait prints them.  Those lines fail nothing.
#     A HEAD move in the worktree or the checkout still voids the result.
#   * a TMPDIR of its own that can run binaries (AGAST #3704): bangerang's
#     JumpCloud CIS policy re-mounts /tmp noexec every 50 min, and every gate
#     there failed at smoke's canary matrix (EACCES running what it built in
#     /tmp).  The command runs with TMPDIR=<gate dir>/.trees/<unit>.tmp, so
#     pytest's tmp_path, tempfile and mktemp all land there.  Before the first
#     step, projects/ritz/tools/exec_tmpdir.py (the probe smoke uses too)
#     writes, chmod +x-es and runs a file in it; if that fails the gate is a
#     SETUP ERROR (exit 2) naming the dir, and the command never runs.  The
#     log's header names the dir (TMPDIR=); the trap removes it with the
#     checkout.  RZ_GATE_PROBE overrides the probe (tests).
#   * no run-gate scratch in the worktree it tests (AGAST #4420): a caller
#     kept the log's path in `.gate-log-name` at the worktree root so a later
#     turn could --wait.  Untracked, it made `adele room rm` refuse the worktree
#     at teardown, and on a busy train that papercut is resolved with --force,
#     the one thing the dirty-worktree guard exists to prevent.  A scratch
#     file is never needed inside the tree: the start removes it before the
#     first check (a stale one from an earlier run), the unit removes it as it
#     exits (pass or fail), and --wait removes it on every exit path, including
#     the SIGTERM a `timeout` slice sends (exit 124).  Only an *untracked* file
#     of that exact name is touched; a tracked one is the caller's content.
#     Tests: test-run-gate.sh (section 22), test-train.sh (6b).
#   * EXIT line always written, and --wait reports a unit that died without
#     one (exit 98): "no verdict" must never read as "passed".
#   * the identity (UNIT=, SHA=) is written again as a trailer immediately
#     before EXIT=, and readers take its last occurrence (AGAST #4430): an
#     operator session once truncated a live log mid-run and lost the header,
#     making a valid EXIT=0 unusable.  --wait on a log with no UNIT= and no
#     verdict says so (98) instead of reading "" as an inactive unit.
#   * build-all as well as bootstrap (AGAST #2141): #2124 broke angelo,
#     passed a bootstrap-only gate, and main's build-all was red for 9 runs.
#     `rz build --all` honours the `build` known-failures.  A missing
#     toolchain binary (harland's bootx64 without lld-link) is reported as
#     SETUP ERROR (ci_local exit 3; make turns it into 2): not a pass, not a
#     regression.  --wait prints the line; install the tool and re-gate.
set -euo pipefail

GATES="${RZ_GATE_DIR:-$HOME/dev/ritz-lang/gate-logs}"

if [[ "${1:-}" == "--wait" ]]; then
    LOG="${2:?usage: $0 --wait <log>}"
    UNIT="$(sed -n 's/^UNIT=//p' "$LOG" | tail -1)"
    # The worktree this log gated, if the log is new enough to name it
    # (AGAST #4420; see the header).
    WT="$(sed -n 's/^WT=//p' "$LOG" | head -1)"
    # Remove run-gate's scratch from the worktree on every exit path, the
    # SIGTERM a `timeout` slice sends included: on 124 the unit may still be
    # running, and this caller is the only one left to clean it.  Never a
    # tracked file: that would be the caller's content, not our scratch.
    scratch_clean() {
        [[ -n "$WT" && -e "$WT/.gate-log-name" ]] || return 0
        git -C "$WT" ls-files --error-unmatch -- .gate-log-name >/dev/null 2>&1 && return 0
        rm -f "$WT/.gate-log-name" 2>/dev/null || true
    }
    trap 'scratch_clean' EXIT
    trap 'scratch_clean; exit 124' TERM INT
    # An empty unit is not a live unit (AGAST #4430): with no UNIT= anywhere
    # and no verdict, systemctl would read "" as inactive and this would call
    # a possibly-live gate dead.  Say the log is headerless instead.  The
    # gate writes the identity again as a trailer before EXIT=, so a header
    # truncated mid-run still names the unit and SHA once it ends.
    if [[ -z "$UNIT" ]] && ! grep -q '^EXIT=' "$LOG"; then
        echo "GATE LOG HAS NO UNIT= (truncated?): $LOG" >&2
        exit 98
    fi
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
    # First, apart from the tail below: they come before any of the output.
    grep '^NOT IN COMMIT ' "$LOG" || true
    grep -E '^(SHA|SLOT|EXIT)=|Stage [0-9]:|passed|FATAL|Failed build|SETUP ERROR|step\(s\) failed|^PKG ' "$LOG" | tail -20
    exit "$rc"
fi

if [[ $# -ne 2 ]]; then
    echo "usage: $0 <worktree> <name>   |   $0 --wait <log>" >&2
    exit 2
fi

WT="$(cd "$1" && pwd -P)"
NAME="$2"
# run-gate's scratch (AGAST #4420; see the header).  Clear a stale one before
# anything else can fail: it is untracked, so it would otherwise outlive a
# refused gate too.  Never a *tracked* file of that name: that is content.
scratch_clean() {
    [[ -e "$WT/.gate-log-name" ]] || return 0
    git -C "$WT" ls-files --error-unmatch -- .gate-log-name >/dev/null 2>&1 && return 0
    rm -f "$WT/.gate-log-name" 2>/dev/null || true
}
scratch_clean
# shellcheck source=../../host-env.sh
source "$(dirname "${BASH_SOURCE[0]}")/../../host-env.sh"
rz_host_env_load || exit 2
# Slots, and how many of them only train gates take (AGAST #4031).
SLOT_CFG="$(rz_gate_slots)" || exit 2
read -r SLOTS TSLOTS <<<"$SLOT_CFG"
# The ritz0 suite budget's scale on this host (AGAST #4138): host.env's
# RZ_TEST_BUDGET_SCALE, or the same name in this script's environment.  The
# unit gets it under that name; main.yml's ritz0 step turns it into
# RITZ_TEST_BUDGET_SCALE for check_test_budget.py alone.  Never set
# RITZ_TEST_BUDGET_SCALE host-wide (#4004 did, with systemctl set-environment):
# every pytest inherits it, and tools/test_check_test_budget.py went red.
BUDGET_SCALE="${RZ_TEST_BUDGET_SCALE:-${HOST_ENV[RZ_TEST_BUDGET_SCALE]:-}}"
if [[ -n "$BUDGET_SCALE" ]] && ! rz_budget_scale_ok "$BUDGET_SCALE"; then
    echo "error: RZ_TEST_BUDGET_SCALE must be a number > 0 like 1.5: '$BUDGET_SCALE'" >&2
    exit 2
fi
# This host's fixed CPU factor for that budget (AGAST #4172): RZ_CPU_FACTOR in
# this script's environment (one gate), else host.env's.  The unit gets it
# under that name; main.yml's ritz0 step hands it to cpu_calibrate.py as
# --factor, never to pytest.  Unset, the step measures the factor live.
if [[ -n "${RZ_CPU_FACTOR:-}" ]]; then
    CPU_FACTOR="$RZ_CPU_FACTOR" CPU_FACTOR_FROM="environment"
else
    CPU_FACTOR="${HOST_ENV[RZ_CPU_FACTOR]:-}" CPU_FACTOR_FROM="host.env"
fi
if [[ -n "$CPU_FACTOR" ]] && ! rz_budget_scale_ok "$CPU_FACTOR"; then
    echo "error: RZ_CPU_FACTOR must be a number > 0 like 1.67: '$CPU_FACTOR'" >&2
    exit 2
fi
if [[ -n "$CPU_FACTOR" ]]; then
    CPU_FACTOR_HDR="$CPU_FACTOR ($CPU_FACTOR_FROM)"
else
    CPU_FACTOR_HDR="(measured)"
fi
# Wipe ritz1/build too: a gate is a verdict on the commit, not on whatever
# objects an earlier base left behind.  Reusing it is how #1497 got 30 bogus
# failures from stale struct layouts (AGAST #1659).
#
# `make smoke` first (AGAST #1803): a fully broken commit fails in ~2 min, not
# ~26.  main.yml's bootstrap job also starts with "Smoke"; ci-local skips it
# (`--skip Smoke`, AGAST #1897) rather than pay ~30 s to run it again.
# build-all runs first (main.yml order): ~30 s on a warm CAS, so a broken
# ecosystem package fails before the long bootstrap job (AGAST #2141).
# test-all (`./rz test --all`) runs next (AGAST #3969, Aaron 2026-11-18): a
# package test break fails the gate, not CI after the push to main.  It is
# main.yml's own job, so CI and the gate run the same command, on the CAS
# build-all just warmed; one `PKG <VERDICT> <id>` line per package.
#
# The base (AGAST #4027): ci-local --diff-base skips "ritz0 unit tests" when
# no change since it can reach that step (tools/ritz0_scope.py; it prints
# SKIPPED ... (base <sha7>), never silently).  A train passes its BASE as
# RZ_GATE_BASE; a room gate uses its merge-base with origin/main.  A base
# that doesn't resolve is dropped, and no base means the step runs.
BASE="${RZ_GATE_BASE:-}"
[[ -n "$BASE" ]] || BASE="$(git -C "$WT" merge-base origin/main HEAD 2>/dev/null)" || BASE=""
BASE="$(git -C "$WT" rev-parse --verify --quiet "${BASE:-none}^{commit}" 2>/dev/null)" || BASE=""
CMD="${RZ_GATE_CMD:-rm -rf projects/ritz/.regression projects/ritz/ritz1/build && make -C projects/ritz smoke && make -C projects/ritz ci-local ARGS=\"--fail-fast --skip Smoke ${BASE:+--diff-base $BASE }--job build-all --job test-all --job bootstrap\"}"
# A merge train's package tests (AGAST #3363), only once CMD has passed.
if [[ -n "${RZ_GATE_AFTER:-}" ]]; then CMD="($CMD) && $RZ_GATE_AFTER"; fi
UNIT="ritz-gate-$NAME"
TREE="$GATES/.trees/$UNIT"
# The gate's own exec-able TMPDIR, beside its checkout (AGAST #3704).
GATE_TMP="$TREE.tmp"
PROBE="${RZ_GATE_PROBE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)/projects/ritz/tools/exec_tmpdir.py}"

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
# One log per run, never reused (AGAST #3182): a re-gate of the same SHA once
# truncated the earlier run's log, and #3178 lost the EXIT=2 evidence it
# needed.  noclobber makes the create atomic (O_EXCL), so two runs racing for
# the same <n> can't share a log; the loser takes the next number.
n=1
while :; do
    LOG="$GATES/$NAME-${SHA:0:12}-$n.log"
    if (set -C; : > "$LOG") 2>/dev/null; then break; fi
    if [[ ! -e "$LOG" ]]; then
        echo "error: cannot create $LOG" >&2
        exit 1
    fi
    n=$((n + 1))
done
printf 'UNIT=%s\nSHA=%s\nBASE=%s\nCMD=%s\nTMPDIR=%s\nWT=%s\nBUDGET_SCALE=%s\nCPU_FACTOR=%s\nSLOTS=%s TRAIN_SLOTS=%s\n' \
    "$UNIT" "$SHA" "$BASE" "$CMD" "$GATE_TMP" "$WT" "$BUDGET_SCALE" "$CPU_FACTOR_HDR" "$SLOTS" "$TSLOTS" >> "$LOG"

# Source files the room's worktree has and the commit doesn't (AGAST #3559).
# The gate can't see them (it runs on a checkout of the SHA), so a gate that
# fails on a missing import says why: "NOT IN COMMIT <file> (ignored: <rule>)".
# Informational: a scratch file the commit doesn't need fails nothing.
not_in_commit() {
    local src=('*.py' '*.ritz' '*.toml' '*Makefile') skip f how n=0
    # Build output and caches: never source, and never meant to be committed.
    skip='(build|\.ritz-cache[^/]*|__pycache__|\.regression|\.pytest_cache|\.venv|venv|node_modules)'
    {
        git -C "$WT" ls-files --others --exclude-standard -- "${src[@]}" | sed 's/^/U /'
        git -C "$WT" ls-files --others --ignored --exclude-standard -- "${src[@]}" | sed 's/^/I /'
    } | grep -Ev "^. (.*/)?$skip/" | while read -r how f; do
        n=$((n + 1))
        if [[ $n -gt 20 ]]; then echo "NOT IN COMMIT ... (more; see git status --ignored)"; break; fi
        if [[ $how == U ]]; then
            echo "NOT IN COMMIT $f (untracked)"
        else
            echo "NOT IN COMMIT $f (ignored: $(git -C "$WT" check-ignore -v -- "$f" | cut -f1))"
        fi
    done
}
not_in_commit >> "$LOG" 2>/dev/null || true

# The inner script reads everything from the environment, so nothing here
# needs a second layer of quoting.
read -r -d '' INNER <<'EOF' || true
set -u
# Bash holds the script open, so it can go now (see "script by path" above).
rm -f "$0"
# Train priority (AGAST #3317; see the header).
MARK="$RZ_DIR/.train-waiting"
unmark() {
    if [ "$(cat "$MARK" 2>/dev/null)" = "$RZ_UNIT" ]; then rm -f "$MARK"; fi
}
RES="$RZ_DIR/.train-reserved"
if [ "$RZ_TRAIN" = 1 ]; then
    echo "$RZ_UNIT" > "$MARK" 2>/dev/null
    # .train-waiting now holds the slot for us; the reservation is done.
    rm -f "$RES"
fi
# Train reservation (AGAST #3365; see the header).  Fails open: anything but
# a time from the last RZ_HOLD seconds is ignored.
train_reserved() {
    [ "$RZ_TRAIN" = 1 ] && return 1
    # Reserved train slots supersede it (AGAST #4031; see the header).
    [ "$RZ_TSLOTS" -gt 0 ] 2>/dev/null && return 1
    local t now
    t="$(cat "$RES" 2>/dev/null)" || return 1
    now="$(date +%s)"
    [ "$t" -le "$now" ] 2>/dev/null && [ $((now - t)) -lt "$RZ_HOLD" ] 2>/dev/null
}
# A room gate yields while a train gate is waiting and its unit is alive.
train_waiting() {
    [ "$RZ_TRAIN" = 1 ] && return 1
    local u
    u="$(cat "$MARK" 2>/dev/null)" || return 1
    [ -n "$u" ] && systemctl --user is-active -q "$u"
}
# FIFO queue (AGAST #3364; see the header).  One line per waiter,
# "<unit> <pid> <train> <queued epoch>", edited only under flock on
# .gate-queue.lock.
Q="$RZ_DIR/.gate-queue"
OVR="$RZ_DIR/.room-override"
ME="$RZ_UNIT $$ $RZ_TRAIN $(date +%s)"
# Starvation bound (AGAST #3578; see the header).  starved <queued epoch>:
# has a room gate queued then waited RZ_STARVE seconds, counting from the last
# override if that is later?  Fails closed (not starved) on anything odd.
starved() {
    local e="$1" o now
    [ -n "$e" ] && [ "$e" -ge 0 ] 2>/dev/null || return 1
    o="$(cat "$OVR" 2>/dev/null)"
    [ "$o" -ge 0 ] 2>/dev/null || o=0
    now="$(date +%s)"
    [ "$o" -le "$now" ] || o=0
    [ "$o" -gt "$e" ] && e=$o
    [ $((now - e)) -ge "$RZ_STARVE" ] 2>/dev/null
}
# The slots this gate may take, in the order it tries them (AGAST #4031): a
# room gate the general ones, a train gate its reserved ones first, then any.
slots() {
    if [ "$RZ_TRAIN" = 1 ]; then seq $((RZ_SLOTS - 1)) -1 0
    else seq 0 $((RZ_SLOTS - RZ_TSLOTS - 1)); fi
}
qlock() { exec 8>>"$Q.lock" && flock 8; }
qunlock() { exec 8>&-; }
dequeue() {
    qlock || return
    grep -vxF "$ME" "$Q" > "$Q.tmp" 2>/dev/null; mv -f "$Q.tmp" "$Q"
    qunlock
}
# ahead: print "<n> <starved>": how many live waiters are ahead of this one,
# and 1 if this is a starved room gate (else 0).  Prunes dead entries (pid
# gone or unit inactive: a SIGKILL or reboot skips the trap).  A train gate
# counts only trains ahead of it (room gates already yield to it), plus the
# oldest room waiter if that one is starved.  A starved room gate is the
# oldest room waiter, so nothing counts ahead of it (it outranks trains).
ahead() {
    local u p t e n=0 seen= keep= head= me_starved=0
    qlock || { echo "0 0"; return; }
    while read -r u p t e; do
        [ -n "$u" ] || continue
        if [ "$u $p $t${e:+ $e}" = "$ME" ]; then
            seen=1
        elif ! { kill -0 "$p" 2>/dev/null && systemctl --user is-active -q "$u"; }; then
            continue
        elif [ -z "$seen" ] && { [ "$RZ_TRAIN" != 1 ] || [ "$t" = 1 ]; }; then
            n=$((n + 1))
        fi
        # The oldest live room waiter, this one or another.
        if [ "$t" != 1 ] && [ -z "$head" ]; then
            head=1
            if starved "$e"; then
                if [ "$u $p $t${e:+ $e}" = "$ME" ]; then me_starved=1; n=0
                elif [ "$RZ_TRAIN" = 1 ]; then n=$((n + 1)); fi
            fi
        fi
        keep+="$u $p $t${e:+ $e}"$'\n'
    done < "$Q"
    # Lost our line (the file was removed by hand)?  Rejoin at the back.
    [ -n "$seen" ] || keep+="$ME"$'\n'
    printf '%s' "$keep" > "$Q.tmp" && mv -f "$Q.tmp" "$Q"
    qunlock
    echo "$n $me_starved"
}
# The gate's own checkout of RZ_SHA (AGAST #3559; see the header).  untree
# also clears one a killed run left behind: same unit, same path.
untree() {
    git worktree remove --force "$RZ_TREE" >/dev/null 2>&1
    rm -rf "$RZ_TREE"
    git worktree prune
    # The gate's TMPDIR (AGAST #3704).  A test may leave a read-only dir, or
    # one with no read/search bit (mode 000) that `chmod -R u+w` can't
    # descend into (AGAST #4274).
    chmod -R u+rwx "$RZ_TMPDIR" 2>/dev/null
    rm -rf "$RZ_TMPDIR"
}
# run-gate's scratch in the worktree it tests (AGAST #4420; see the header).
# Untracked only: a tracked file of that name is the caller's content.
scratch_clean() {
    [ -n "${RZ_WT:-}" ] && [ -e "$RZ_WT/.gate-log-name" ] || return 0
    git -C "$RZ_WT" ls-files --error-unmatch -- .gate-log-name >/dev/null 2>&1 && return 0
    rm -f "$RZ_WT/.gate-log-name"
}
trap 'dequeue; unmark; untree; scratch_clean' EXIT
# Fail fast if the unit can't write: otherwise the slot loop below spins
# forever and never writes a verdict.  (Seen: an agent sandbox's /tmp is not
# the /tmp systemd units see.)  The unit ends with no EXIT line; --wait -> 98.
{ qlock && echo "$ME" >> "$Q" && qunlock; } 2>/dev/null || exit 97
read -r n st < <(ahead)
pos=$((n + 1))
echo "WAITING for a gate slot, queue position $pos $(date -Is)" >> "$RZ_LOG" || exit 97
while :; do
    read -r n st < <(ahead)
    now_pos=$((n + 1))
    if [ "$now_pos" != "$pos" ]; then
        pos=$now_pos
        echo "WAITING queue position $pos $(date -Is)" >> "$RZ_LOG"
    fi
    if [ "$st" = 1 ]; then
        # Starved (AGAST #3578; see the header): the merge train waits for us.
        if [ -z "${said_starved:-}" ]; then
            said_starved=1
            echo "STARVED: waited ${RZ_STARVE}s or more; next free slot, ahead of merge trains $(date -Is)" >> "$RZ_LOG"
        fi
        for s in $(slots); do
            exec 9>"$RZ_DIR/.gate-slot-$s"
            if flock -n 9; then
                { date +%s > "$OVR.$$" && mv -f "$OVR.$$" "$OVR"; } 2>/dev/null \
                    || echo "warning: could not stamp $OVR" >> "$RZ_LOG"
                break 2
            fi
        done
    # Reservation before marker: the train writes .train-waiting before it
    # removes .train-reserved, so checking in this order never sees neither.
    elif [ "$pos" = 1 ] && train_reserved; then
        if [ -z "${said_res:-}" ]; then
            said_res=1
            echo "WAITING: slot reserved for the merge train since $(date -Is -d "@$(cat "$RES")" 2>/dev/null) $(date -Is)" >> "$RZ_LOG"
        fi
    elif [ "$pos" = 1 ] && ! train_waiting; then
        for s in $(slots); do
            exec 9>"$RZ_DIR/.gate-slot-$s"
            if flock -n 9; then
                # A train gate may have reserved the slot and released it
                # between our check above and this flock: look again.
                train_reserved || break 2
                exec 9>&-
                break
            fi
        done
    fi
    sleep "$RZ_POLL"
done
dequeue
unmark
echo "SLOT=$s START $(date -Is)" >> "$RZ_LOG"
untree
t0=$(date +%s)
if ! { mkdir -p "$(dirname "$RZ_TREE")" \
        && git worktree add -q --detach "$RZ_TREE" "$RZ_SHA" >> "$RZ_LOG" 2>&1; }; then
    echo "SETUP ERROR: could not check out $RZ_SHA into $RZ_TREE" >> "$RZ_LOG"
    rc=2
    tree_now="$RZ_SHA"
else
    echo "TREE=$RZ_TREE checked out in $(( $(date +%s) - t0 )) s" >> "$RZ_LOG"
    tree_now="$(git -C "$RZ_TREE" rev-parse HEAD)"
    # Prove the gate's TMPDIR can run a binary before any step (AGAST #3704).
    if ! why="$(mkdir -p -m 700 "$RZ_TMPDIR" 2>&1 && "$RZ_PROBE" probe "$RZ_TMPDIR" 2>&1)"; then
        echo "SETUP ERROR: the gate's TMPDIR $RZ_TMPDIR can't run binaries (noexec?); not a test failure: $why" >> "$RZ_LOG"
        rc=2
    else
        (cd "$RZ_TREE" && TMPDIR="$RZ_TMPDIR" bash -c "$RZ_CMD") >> "$RZ_LOG" 2>&1
        rc=$?
        tree_now="$(git -C "$RZ_TREE" rev-parse HEAD)"
    fi
fi
now="$(git rev-parse HEAD)"
if [ "$now" != "$RZ_SHA" ]; then
    echo "HEAD MOVED during the gate: $RZ_SHA -> $now; result void" >> "$RZ_LOG"
    rc=99
elif [ "$tree_now" != "$RZ_SHA" ]; then
    echo "HEAD MOVED in the gate's checkout: $RZ_SHA -> $tree_now; result void" >> "$RZ_LOG"
    rc=99
fi
# A train gate reserves the slot for the next train before it releases it
# (AGAST #3427; see the header).  Pass or fail, before the EXIT line, so the
# reservation exists by the time anyone reads the verdict.
if [ "$RZ_TRAIN" = 1 ]; then
    { date +%s > "$RES.$$" && mv -f "$RES.$$" "$RES"; } 2>/dev/null \
        || echo "warning: could not reserve the gate slot ($RES)" >> "$RZ_LOG"
fi
# The identity again, next to the verdict (AGAST #4430): a live log truncated
# mid-run by an operator session lost its header, and a valid EXIT=0 was
# refused for want of SHA=.  The trailer is authoritative; readers take the
# last occurrence.  Written on every path that writes EXIT=.
printf 'UNIT=%s\nSHA=%s\n' "$RZ_UNIT" "$RZ_SHA" >> "$RZ_LOG"
echo "EXIT=$rc" >> "$RZ_LOG"
EOF
# By path, never as `bash -c "$INNER"` (AGAST #3567; see the header).
SCRIPT="${LOG%.log}.unit.sh"
printf '%s\n' "$INNER" > "$SCRIPT"

systemd-run --user --quiet --unit="$UNIT" --collect --working-directory="$WT" \
    --slice=ritz-gate.slice --property=CPUWeight=100 \
    --setenv=PATH="$PATH" --setenv=HOME="$HOME" \
    --setenv=RZ_LOG="$LOG" --setenv=RZ_SHA="$SHA" --setenv=RZ_CMD="$CMD" \
    --setenv=RZ_SLOTS="$SLOTS" --setenv=RZ_TSLOTS="$TSLOTS" --setenv=RZ_DIR="$GATES" \
    --setenv=RZ_WT="$WT" \
    --setenv=RZ_POLL="${RZ_GATE_POLL:-20}" --setenv=RZ_UNIT="$UNIT" \
    --setenv=RZ_TRAIN="${RZ_GATE_TRAIN:-0}" \
    --setenv=RZ_HOLD="${RZ_GATE_TRAIN_HOLD:-600}" \
    --setenv=RZ_TREE="$TREE" \
    --setenv=RZ_TMPDIR="$GATE_TMP" --setenv=RZ_PROBE="$PROBE" \
    --setenv=RZ_STARVE="${RZ_GATE_STARVE:-2700}" \
    --setenv=RZ_TEST_BUDGET_SCALE="$BUDGET_SCALE" \
    --setenv=RZ_CPU_FACTOR="$CPU_FACTOR" \
    /bin/bash "$SCRIPT"

echo "$LOG"
