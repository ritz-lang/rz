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
#   RZ_HOST_ENV    per-host config file          (default: ~/.config/rz/host.env)
#   RZ_GATE_DIR    where logs and slot locks go  (default: ~/dev/ritz-lang/gate-logs)
#   RZ_GATE_POLL   seconds between slot polls    (default: 20; tests use less)
#   RZ_GATE_TRAIN  1 = a merge-train gate        (train.sh gate sets it)
#   RZ_GATE_AFTER  run after the command passes  (train.sh gate: its package
#                  tests, AGAST #3363)
#   RZ_GATE_TRAIN_HOLD  seconds a .train-reserved holds room gates (default 600)
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
#   * EXIT line always written, and --wait reports a unit that died without
#     one (exit 98): "no verdict" must never read as "passed".
#   * build-all as well as bootstrap (AGAST #2141): #2124 broke angelo,
#     passed a bootstrap-only gate, and main's build-all was red for 9 runs.
#     `rz build --all` honours rz.toml [ci.known_failing.build].  A missing
#     toolchain binary (harland's bootx64 without lld-link) is reported as
#     SETUP ERROR (ci_local exit 3; make turns it into 2): not a pass, not a
#     regression.  --wait prints the line; install the tool and re-gate.
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
# shellcheck source=../../host-env.sh
source "$(dirname "${BASH_SOURCE[0]}")/../../host-env.sh"
rz_host_env_load || exit 2
SLOTS="${RZ_GATE_SLOTS:-${HOST_ENV[RZ_GATE_SLOTS]:-1}}"
if [[ ! "$SLOTS" =~ ^[1-9][0-9]*$ ]]; then
    echo "error: RZ_GATE_SLOTS must be a whole number >= 1: '$SLOTS'" >&2
    exit 2
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
CMD="${RZ_GATE_CMD:-rm -rf projects/ritz/.regression projects/ritz/ritz1/build && make -C projects/ritz smoke && make -C projects/ritz ci-local ARGS=\"--fail-fast --skip Smoke --job build-all --job bootstrap\"}"
# A merge train's package tests (AGAST #3363), only once CMD has passed.
if [[ -n "${RZ_GATE_AFTER:-}" ]]; then CMD="($CMD) && $RZ_GATE_AFTER"; fi
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
printf 'UNIT=%s\nSHA=%s\nCMD=%s\n' "$UNIT" "$SHA" "$CMD" >> "$LOG"

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
# "<unit> <pid> <train>", edited only under flock on .gate-queue.lock.
Q="$RZ_DIR/.gate-queue"
ME="$RZ_UNIT $$ $RZ_TRAIN"
qlock() { exec 8>>"$Q.lock" && flock 8; }
qunlock() { exec 8>&-; }
dequeue() {
    qlock || return
    grep -vxF "$ME" "$Q" > "$Q.tmp" 2>/dev/null; mv -f "$Q.tmp" "$Q"
    qunlock
}
# ahead: print how many live waiters are ahead of this one, pruning dead
# entries (pid gone or unit inactive: a SIGKILL or reboot skips the trap).  A
# train gate counts only trains ahead of it: room gates already yield to it.
ahead() {
    local u p t n=0 seen= keep=
    qlock || { echo 0; return; }
    while read -r u p t; do
        [ -n "$u" ] || continue
        if [ "$u $p $t" = "$ME" ]; then
            seen=1
        elif kill -0 "$p" 2>/dev/null && systemctl --user is-active -q "$u"; then
            if [ -z "$seen" ] && { [ "$RZ_TRAIN" != 1 ] || [ "$t" = 1 ]; }; then
                n=$((n + 1))
            fi
        else
            continue
        fi
        keep+="$u $p $t"$'\n'
    done < "$Q"
    # Lost our line (the file was removed by hand)?  Rejoin at the back.
    [ -n "$seen" ] || keep+="$ME"$'\n'
    printf '%s' "$keep" > "$Q.tmp" && mv -f "$Q.tmp" "$Q"
    qunlock
    echo "$n"
}
# The gate's own checkout of RZ_SHA (AGAST #3559; see the header).  untree
# also clears one a killed run left behind: same unit, same path.
untree() {
    git worktree remove --force "$RZ_TREE" >/dev/null 2>&1
    rm -rf "$RZ_TREE"
    git worktree prune
}
trap 'dequeue; unmark; untree' EXIT
# Fail fast if the unit can't write: otherwise the slot loop below spins
# forever and never writes a verdict.  (Seen: an agent sandbox's /tmp is not
# the /tmp systemd units see.)  The unit ends with no EXIT line; --wait -> 98.
{ qlock && echo "$ME" >> "$Q" && qunlock; } 2>/dev/null || exit 97
pos=$(( $(ahead) + 1 ))
echo "WAITING for a gate slot, queue position $pos $(date -Is)" >> "$RZ_LOG" || exit 97
while :; do
    now_pos=$(( $(ahead) + 1 ))
    if [ "$now_pos" != "$pos" ]; then
        pos=$now_pos
        echo "WAITING queue position $pos $(date -Is)" >> "$RZ_LOG"
    fi
    # Reservation before marker: the train writes .train-waiting before it
    # removes .train-reserved, so checking in this order never sees neither.
    if [ "$pos" = 1 ] && train_reserved; then
        if [ -z "${said_res:-}" ]; then
            said_res=1
            echo "WAITING: slot reserved for the merge train since $(date -Is -d "@$(cat "$RES")" 2>/dev/null) $(date -Is)" >> "$RZ_LOG"
        fi
    elif [ "$pos" = 1 ] && ! train_waiting; then
        for s in $(seq 0 $((RZ_SLOTS - 1))); do
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
if mkdir -p "$(dirname "$RZ_TREE")" \
        && git worktree add -q --detach "$RZ_TREE" "$RZ_SHA" >> "$RZ_LOG" 2>&1; then
    echo "TREE=$RZ_TREE checked out in $(( $(date +%s) - t0 )) s" >> "$RZ_LOG"
    (cd "$RZ_TREE" && bash -c "$RZ_CMD") >> "$RZ_LOG" 2>&1
    rc=$?
    tree_now="$(git -C "$RZ_TREE" rev-parse HEAD)"
else
    echo "SETUP ERROR: could not check out $RZ_SHA into $RZ_TREE" >> "$RZ_LOG"
    rc=2
    tree_now="$RZ_SHA"
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
echo "EXIT=$rc" >> "$RZ_LOG"
EOF
# By path, never as `bash -c "$INNER"` (AGAST #3567; see the header).
SCRIPT="${LOG%.log}.unit.sh"
printf '%s\n' "$INNER" > "$SCRIPT"

systemd-run --user --quiet --unit="$UNIT" --collect --working-directory="$WT" \
    --slice=ritz-gate.slice --property=CPUWeight=100 \
    --setenv=PATH="$PATH" --setenv=HOME="$HOME" \
    --setenv=RZ_LOG="$LOG" --setenv=RZ_SHA="$SHA" --setenv=RZ_CMD="$CMD" \
    --setenv=RZ_SLOTS="$SLOTS" --setenv=RZ_DIR="$GATES" \
    --setenv=RZ_POLL="${RZ_GATE_POLL:-20}" --setenv=RZ_UNIT="$UNIT" \
    --setenv=RZ_TRAIN="${RZ_GATE_TRAIN:-0}" \
    --setenv=RZ_HOLD="${RZ_GATE_TRAIN_HOLD:-600}" \
    --setenv=RZ_TREE="$GATES/.trees/$UNIT" \
    /bin/bash "$SCRIPT"

echo "$LOG"
