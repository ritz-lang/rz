#!/usr/bin/env bash
#
# Merge train: land several REAPed commits on main with ONE gate (Aaron,
# 2026-11-12).  Every REAP is one squashed commit that its room checked on
# its own base (smoke-plan.sh: its subsystems in full, AGAST #4580), so
# instead of each room rebasing and re-gating in turn, rz stacks them on
# origin/main in queue order and gates only the top, in full.
#
#   train.sh build <branch>:<sha> ...         stack the cars on origin/main,
#                                             replacing every train
#   train.sh build --next <branch>:<sha> ...  keep train 1 (the one gating) and
#                                             stack these cars on its tail as
#                                             train 2, replacing trains 2+
#                                             (keeps a train 2 gating on a
#                                             remote host too: then train 3)
#   train.sh gate [<k>]                 gate the train to gate (below) here,
#                                       or train <k> (prints the log)
#   train.sh gate --next [<host>]       gate the train to gate (train 1
#                                       included) on <host>, default the
#                                       first RZ_TRAIN_HOSTS host with a free
#                                       train slot; train 1 tries the remote
#                                       hosts first and falls back to a gate
#                                       here (plain `gate`) when none is free
#                                       (prints the local log path; AGAST
#                                       #4031, #4422)
#   train.sh wait <log>                 wait for a gate, local or remote, and
#                                       exit with its verdict (fetches a
#                                       remote log back first)
#   train.sh discard [<host>]           drop every speculative gate, or
#                                       <host>'s (a dead host); trains stay
#   train.sh fail <log>                 train k's gate failed: drop train k
#                                       and every train after it (gates
#                                       stopped), print train k's cars as
#                                       HELD, and restack the later trains'
#                                       cars on train k-1's tail
#   train.sh pending                    the train to gate: GATE now, or
#                                       WAIT (8 cars, or 60 s with no new
#                                       car on the first train; a train
#                                       behind a gating one buffers to 8);
#                                       FAIL: a red train with nothing
#                                       below it to bisect
#   train.sh precheck [<k>]             make train-precheck (tools-ratchets
#                                       and the ritz0 test-count cap) on the
#                                       tip of the train pending would gate,
#                                       or train <k>, before it gates (AGAST
#                                       #4672, #4904; see cmd_precheck)
#   train.sh land [<log>]               push the tail of the train <log>
#                                       passed (train k) to main, landing
#                                       trains 1..k and cancelling their
#                                       gates; train k+1 becomes train 1
#   train.sh show                       print every train, in landing order
#   train.sh pkgs list <base>           the packages the train touches
#                                       (#3363), for the gate's PKGS line
#   train.sh tail                       the deepest built train's tail
#                                       (<tip12> rz-train/<tip12>), nothing
#                                       when none is built (#4413)
#   train.sh rebase-plan [<ref>]        one loop turn's preemptive rebase
#        [--dropped <oldtip> [--onto <ref>]]
#                                       advice, rooms on stdin (#4413): print
#                                       each room's base vs the deepest tail,
#                                       SKIP a room mid-gate, and one REBASE
#                                       line for a room to move (see the
#                                       function comment)
#   train.sh hold-tail <sha>            push <sha> to origin
#                                       refs/heads/rz-train/<sha12> (fail may
#                                       have deleted a red tail's ref: this
#                                       re-publishes it for a fix-forward
#                                       room) and record it in RZ_HELD_TAILS
#                                       (main worktree's git dir) so `land`
#                                       deletes it once it is subsumed
#                                       (AGAST #4753)
#   train.sh hold-resolve <room> <sha>  push <sha> to origin
#                                       refs/heads/rz-resolve/<room>-<sha12>
#                                       and record it in RZ_HELD_RESOLVES the
#                                       same way, for a conflict resolution
#                                       boarded in a car's place (SKILL.md
#                                       step 7; AGAST #4753)
#   train.sh prune-refs [--dry-run]     delete every rz-train/* or
#                                       rz-resolve/* ref on origin that no
#                                       live train or held tail/resolve
#                                       names, and that is either fully on
#                                       main (git cherry: no unmerged patch)
#                                       or older than RZ_PRUNE_DAYS days
#                                       (default 2); --dry-run prints what it
#                                       would delete without deleting it
#                                       (AGAST #4753).  rz runs this after
#                                       landing; never against a live train's
#                                       ref, and never from a test against
#                                       origin's real refs.
#
# Stacked trains (AGAST #3809): a train holds at most 8 cars (RZ_TRAIN_MAX);
# car 9 onward start the next train on its tail.  Each train has its own
# worktree (train 1 first used $RZ_TRAIN_WT, the next free slot <wt>-2, ...)
# and state file, so building train 2 while train 1 gates leaves train 1's
# tree and state alone.  Trains land in order, and the landing order is the
# slot list in <common git dir>/RZ_TRAINS.  A passed train k covers trains
# 1..k-1 (AGAST #4151): it is built on their tails, so its gate tested every
# car below it.  `land <train k's log>` pushes train k's tail (one
# fast-forward), prints MERGED for every car of trains 1..k, cancels trains
# 1..k-1's gates (stops the local ritz-gate-<name> unit and clears its
# .train-waiting; stops a remote SPEC gate and deletes its ref: CANCELLED
# lines), and promotes train k+1.  The 8-car cap is per gate, not per land.
#
# `build` prints one line per item, then a summary per train:
#   APPLIED  <branch> <sha12> as <new12>   (cherry-picked; same patch.  Also
#                                          a car its room rebased cleanly
#                                          after the REAP without a new
#                                          gate: <sha12> is the REAP's, the
#                                          pick its branch's commit with
#                                          that patch; never KEPT, so a
#                                          train gate covers it; AGAST #4580)
#   KEPT     <branch> <sha12>              (its parent is the tail: same SHA)
#   CONFLICT <branch> <sha12> with <cars|main> on <files>
#                                          (left out; its room must rebase)
#   EMPTY    <branch> <sha12>              (left out; already on main)
#   BAD      <branch> <sha12>: <why>       (left out; a room mistake)
#   TRAIN <k> base=<12> tip=<12> n=<cars> gate=<needed|not-needed>
#
# A car may sit on unlanded train commits (a CONFLICT bounced to "rebase onto
# <tail>"): its commits over main must be that train's commits, by SHA or by
# patch, plus its own one.  Picks keep the car's committer date, so a rebuilt
# train over the same cars has the same SHAs and such a car stays KEPT.
#
# A multi-slice room (AGAST #4382) REAPs one slice per commit on one branch,
# so the tip has moved past the REAPed slice and earlier slices are on main
# under the train's cherry-picked SHA.  An item may name any commit on its
# branch, not just the tip; the car's commits over main are matched against
# the base (main, every train below, and this train's earlier cars) by
# `git patch-id --verbatim` as a multiset, and only one unlanded commit may
# remain.  Two genuinely unlanded commits are still BAD.
#
# rz never resolves a conflict or edits a commit: a CONFLICT is aborted and
# skipped, and the room gets the turn once the train lands.
#
# Env overrides (for tests):
#   RZ_TRAIN_WT    train 1's worktree  (default ~/dev/ritz-lang/rz-train)
#   RZ_TRAIN_MAX   cars per train      (default 8)
#   RZ_TRAIN_DEPTH trains in flight    (default: host.env RZ_TRAIN_DEPTH,
#                  else 6; AGAST #4031, #4409)
#   RZ_TRAIN_HOSTS where every train (train 1 included) may gate, in order:
#                  `gate --next` looks for a free train slot here (default:
#                  host.env RZ_TRAIN_HOSTS, else "omegalisk huburght
#                  bangerang starbux toffee chungus": the live hosts of
#                  2026-11-20, no ephemeral skronk*; AGAST #4409, #4422).
#                  For train 1 this host is tried last by preference, as its
#                  local fallback.
#   RZ_TRAIN_LOCAL this host's name in that list (default: hostname -s)
#   RZ_TRAIN_DEBOUNCE  seconds `pending` waits for another car (default 60)
#   RZ_MAIN_WT     main checkout       (default ~/dev/ritz-lang/rz)
#   RZ_TRAIN_NAME  gate name           (default train)
#   RZ_GATE_SCRIPT run-gate.sh to use  (default: beside this script)
#   RZ_GATE_DIR    gate logs/slots     (default ~/dev/ritz-lang/gate-logs)
#
# DEPTH and HOSTS are read from ~/.config/rz/host.env too (RZ_HOST_ENV
# overrides the path), the environment winning over the file (AGAST #4409:
# the operator wrapper ~/dev/ritz-lang/rz-train-ops.sh used to set them on
# every call).  host-env.sh validates both, and so does this script for an
# environment override.
#
# Slot reservation (AGAST #3365, #3427): the train's gate writes <gate
# dir>/.train-reserved as it ends, and `land` renews it, so a room gate can't
# take the gate slot before the next train's gate starts; run-gate.sh honours
# it for RZ_GATE_TRAIN_HOLD seconds (default 600).  Except a room gate that
# has waited RZ_GATE_STARVE seconds (default 2700): it goes ahead of the next
# train, at most one per bound (AGAST #3578; see run-gate.sh).
#
# Speculative trains (AGAST #3988): omegalisk has one gate slot, and a train
# gate takes ~25-35 min for <= 8 cars, so trains were the merge bottleneck.
# `gate --next` gates train 2 on train 1's tail while train 1 still gates,
# on a remote host (omegalisk can't hold two gates).  Train 1 itself gates
# on a remote host too (AGAST #4422: otherwise its gate serialises every
# local room gate): `gate --next` prefers a remote free slot for it and falls
# back to plain `gate` here; plain `gate` stays local-only.  A remote start,
# for any train:
#   1. ensure the target train's tail is on origin refs/heads/rz-train/<tip12> (a
#      build publishes every train's tail: see "Tail refs" below);
#   2. ssh <host> (RZ_TRAIN_SSH) runs REMOTE_SH below, `start`: fetch that
#      ref into the host's clone, check out <tip> in its own worktree
#      (RZ_REMOTE_WT), and start that tree's run-gate.sh with
#      RZ_GATE_TRAIN=1 (train priority and reservation on that host, #3317,
#      #3427); it prints the log path;
#   3. train 2's state gets `SPEC=<host> <ref> <remote log> <local log>`.
# `wait <local log>` runs the remote run-gate.sh --wait in slices, then
# copies the remote log to <local log> and checks its SHA is the train's tip,
# so `land` checks `SHA=<tip>` and `EXIT=0` exactly as for a local log.  The
# remote gate's base (ci-local --diff-base) is main, train 1's
# base, not train 1's tail: its pass lands train 1 too (AGAST #4151).  (Was
# at most 2 trains in flight; since #4031, RZ_TRAIN_DEPTH: see below.)
# `build --next` keeps every train that has a SPEC and stacks new cars on
# the last one's tail.  Any build that replaces a train with a SPEC discards it (DISCARDED
# line): stops the remote gate, deletes the ref.  `land` deletes the landed
# train's ref.  A verdict can never outlive its tree: it names the tip, and
# a rebuilt train on another base has another tip.
#
# N trains in flight (AGAST #4031): the 2-train cap is RZ_TRAIN_DEPTH (default
# 6: host.env RZ_TRAIN_DEPTH, else 6; AGAST #4409), counting every train with
# a GATED= or SPEC=.  `gate --next` gates the
# train to gate (pick_target, AGAST #4156: the deepest, or a bisect prefix;
# train 1 included, #4422), on the first host in RZ_TRAIN_HOSTS with a free
# train slot (pick_train_host: rz_train_free in host-env.sh, over ssh for a
# remote host; an unreachable host is skipped).  Train 1 gates the same way:
# `gate --next` tries the remote hosts first and falls back to a gate here
# (plain `gate`) when none has a free train slot, so the coordinator's one
# gate slot is free for rooms while a remote host gates train 1.  This host (RZ_TRAIN_LOCAL) is local: its
# gate runs here and its SPEC is `SPEC=<host> - <log> <log>` (train 1's local
# gate, as plain `gate`, is `GATED=<log>`).  Each train's
# gate is named for its worktree slot (gname: `train` for slot 1, `train-<s>`
# for slot s), and a remote one checks out in RZ_REMOTE_WT, -<s> for slot s,
# so two trains can gate on one host at once (skronk has 2 train slots).
# `build --next` keeps train 1 and every train up to the last one with a
# SPEC.  A failed train k (`fail <log>`) invalidates every train after it
# (their bases hold its cars): their gates are stopped, and their cars are
# rebuilt on train k-1's tail.  A pass still lands every train below it.
#
# Tail refs (AGAST #4409; Aaron 2026-11-20): every train's tail is pushed to
# origin refs/heads/rz-train/<tip12> when the train is built, not only when
# `gate --next` starts a remote gate, so a new room can base on the deepest
# tail (SKILL.md "Spawning a room"): the host creates the worktree off main,
# then the room runs `git fetch origin rz-train/<tip12> && git reset --hard
# FETCH_HEAD`, and `build --next` boards its commit as KEPT instead of
# cherry-picking it.  A tail ref is deleted when its train lands (a pass
# covers it), is replaced by a build, or fails/discards it; publish_tail is
# idempotent, so `gate --next` re-ensuring the target's ref costs one push.
#
# Held tails and resolves (AGAST #4753): `fail` deletes a red train's tail
# (unpublish_tail), but rz re-publishes it by hand for a fix-forward room
# (SKILL.md step 6.3: `hold-tail`), and a conflict resolution is pushed to
# its own rz-resolve/<room>-<sha12> ref (step 7: `hold-resolve`).  Neither is
# named by any train's state once that happens, so nothing landing or
# failing would otherwise delete them.  `hold-tail`/`hold-resolve` record
# them in RZ_HELD_TAILS/RZ_HELD_RESOLVES (main worktree's git dir); `land`
# deletes every held ref whose SHA is now an ancestor of the landed tip (a
# fix-forward or resolution always reboards into a later train, so a land
# covering it also covers the tail or resolve it was pushed for).
# `prune-refs` is the sweep for everything else that leaked: any rz-train/*
# or rz-resolve/* ref no live train or held file names, deleted once it is
# fully on main or RZ_PRUNE_DAYS days old (default 2).
#
# Dispatch (AGAST #4031, #4156; Aaron 2026-11-20; SKILL.md "Merge trains"):
# `build` stamps each train it starts with BUILT=<epoch>, and each REAP is a
# rebuild, so BUILT is the last car's arrival.  The first train (nothing
# gating below it) gates at 8 cars or after RZ_TRAIN_DEBOUNCE seconds with no
# new car, else WAIT.  A train stacked behind a gating one does not spend a
# second slot early: it buffers to 8 cars before GATE, and WAITs until then.
# The whole stack is gated at its tip, so a full buffered train gates every
# car below it at once.  `gate` marks the gated train GATED=<log> (or a
# remote SPEC=<host> ...), so a train already gating is never pending.
#
# Deepest train first (AGAST #4156): a pass of train k lands trains 1..k
# (#4151), so gating a shorter prefix while a deeper train is built only
# repeats part of that verdict.  The train to gate (pick_target) is the
# deepest built train, once it isn't gating already, if it or a train below
# it needs a gate; each train still holds at most 8 cars.  A shorter prefix
# gates only to bisect a red deeper gate: with train r the lowest red and
# train g the highest green below it (0: none), gate train g + (r-g)/2, once
# no train between them is still gating; when r = g+1 there is nothing to
# bisect, and `pending` says FAIL (car-level bisect: `fail`, SKILL.md step
# 6).  A verdict is the train's gate log (GATED=, or SPEC's local log, which
# a remote gate has once `wait` fetched it) whose SHA= is the train's tip.
# `gate` gates the train to gate here: train 1 as GATED=, a later train as a
# local SPEC (`SPEC=<this host> - <log> <log>`, the form `gate --next` writes
# for this host, so wait/land/fail/discard treat it as before).  `gate <k>`
# gates train <k> here whatever the rule says (a retry, a hand bisect).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
MAIN_WT="${RZ_MAIN_WT:-$HOME/dev/ritz-lang/rz}"
TRAIN_WT="${RZ_TRAIN_WT:-$HOME/dev/ritz-lang/rz-train}"
MAX="${RZ_TRAIN_MAX:-8}"
NAME="${RZ_TRAIN_NAME:-train}"
GATE="${RZ_GATE_SCRIPT:-$HERE/run-gate.sh}"
GATES="${RZ_GATE_DIR:-$HOME/dev/ritz-lang/gate-logs}"
RESERVED="$GATES/.train-reserved"
# Speculative remote gates (AGAST #3988; see above).  Remote paths are
# relative to the remote $HOME unless absolute.
# ConnectTimeout: pick_train_host asks each host in turn, and a spot-killed
# skronk must cost seconds, not the default TCP timeout (AGAST #4031).
SSH="${RZ_TRAIN_SSH:-ssh -F $HOME/.ssh/rz_hosts -o ConnectTimeout=10}"
LOCAL="${RZ_TRAIN_LOCAL:-$(hostname -s)}"
DEBOUNCE="${RZ_TRAIN_DEBOUNCE:-60}"
REMOTE_REPO="${RZ_REMOTE_REPO:-dev/ritz-lang/rz}"
REMOTE_WT="${RZ_REMOTE_WT:-dev/ritz-lang/rz-train-remote}"
REMOTE_GATE="${RZ_REMOTE_GATE:--}"      # - = the train tree's own run-gate.sh
SSH_RETRY="${RZ_TRAIN_SSH_RETRY:-30}"   # seconds between ssh retries
WAIT_SLICE="${RZ_TRAIN_WAIT_SLICE:-540}"
# Pause before re-polling a gate still queued whose --wait slice ended early.
QUEUED_PAUSE="${RZ_TRAIN_QUEUED_PAUSE:-15}"
# rz_venv_path, sent to the gate host with REMOTE_SH (AGAST #4025).
# shellcheck source=../../host-env.sh
source "$HERE/../../host-env.sh"

die() { echo "error: $*" >&2; exit 1; }

# DEPTH and HOSTS may also come from host.env (AGAST #4409): the environment
# wins, then the file, then the 2026-11-20 policy.  rz_host_env_load prints
# the file's own error for a bad key, with its line number.
rz_host_env_load || exit 1
DEPTH="${RZ_TRAIN_DEPTH:-${HOST_ENV[RZ_TRAIN_DEPTH]:-6}}"
HOSTS="${RZ_TRAIN_HOSTS:-${HOST_ENV[RZ_TRAIN_HOSTS]:-omegalisk huburght bangerang starbux toffee chungus}}"
[[ "$DEPTH" =~ ^[1-9][0-9]*$ ]] \
    || die "RZ_TRAIN_DEPTH must be a whole number >= 1: '$DEPTH'"
[[ "$HOSTS" =~ ^[A-Za-z0-9._-]+([[:space:]]+[A-Za-z0-9._-]+)*$ ]] \
    || die "RZ_TRAIN_HOSTS must be a space-separated host list: '$HOSTS'"

WT="$TRAIN_WT"                      # the train being worked on (use_slot)
g() { git -C "$WT" "$@"; }
state() { echo "$(g rev-parse --absolute-git-dir)/RZ_TRAIN"; }
field() { sed -n "s/^$1=//p" "$2"; }

slot_wt() { if [[ $1 == 1 ]]; then echo "$TRAIN_WT"; else echo "$TRAIN_WT-$1"; fi; }
SLOT=1
use_slot() { SLOT="$1"; WT="$(slot_wt "$1")"; }
# The current train's gate name and remote worktree, by its slot (AGAST #4031:
# two trains may gate on one host at once).
gname() { if [[ $SLOT == 1 ]]; then echo "$NAME"; else echo "$NAME-$SLOT"; fi; }
rwt() { if [[ $SLOT == 1 ]]; then echo "$REMOTE_WT"; else echo "$REMOTE_WT-$SLOT"; fi; }
is_local() { [[ "$1" == local || "$1" == "$LOCAL" ]]; }
qfile() { echo "$(git -C "$MAIN_WT" rev-parse --path-format=absolute --git-common-dir)/RZ_TRAINS"; }
# The trains' slots in landing order.  No list yet but a train in slot 1:
# a train built before stacking existed.
queue() {
    local q; q="$(qfile)"
    if [[ -f "$q" ]]; then cat "$q"
    elif [[ -e "$TRAIN_WT/.git" ]] \
        && [[ -f "$(git -C "$TRAIN_WT" rev-parse --absolute-git-dir)/RZ_TRAIN" ]]; then echo 1
    fi
}
front() { local s; s="$(queue | head -1)"; [[ -n "$s" ]] || die "no train built"; use_slot "$s"; }
# write_queue <slots...>: RZ_TRAINS is these slots, replaced in one rename so
# no reader (or a dying writer) sees it half-written or missing; no slots: an
# empty list, in one rename too.  Not a removed file: queue()'s legacy fallback
# (no list, but an RZ_TRAIN in slot 1) would then resurrect a train land/fail
# is still clearing - they write the queue before the trains' state.  A list
# that was never written stays absent, so a pre-stacking train is still seen.
# AGAST #4337.
write_queue() {
    local q; q="$(qfile)"
    if [[ $# -eq 0 ]]; then : > "$q.tmp.$$"; else printf '%s\n' "$@" > "$q.tmp.$$"; fi \
        && mv -f "$q.tmp.$$" "$q"
}

# --- Remote speculative gates (AGAST #3988) ---------------------------------
# REMOTE_SH runs on the gate host as `bash -l -s -- <verb> <args>`, read from
# stdin, so the host needs nothing of this branch but its run-gate.sh (the
# train tree's own).  Everything runs from main, called on the last line:
# bash has read the whole script by then, so no command can eat it off stdin.
#   start <repo> <wt> <gate|-> <ref> <tip> <base> <name>
#                                  fetch, check out, start the gate; prints
#                                  the remote log path.  The gate runs on the
#                                  host's venv (rz_venv_path: a login shell's
#                                  PATH has none, AGAST #4025), and start
#                                  refuses before it takes a slot if that
#                                  python3 can't import pytest, or (after the
#                                  checkout) if its venv misses a pin of the
#                                  tip's requirements.lock (AGAST #4583)
#   wait <wt> <gate|-> <log> <secs> <pause>
#                                  run-gate.sh --wait for at most <secs>
#                                  (124: still running).  A gate with no
#                                  EXIT yet whose unit is active or whose
#                                  waiter is queued for a slot is still
#                                  running, whatever code --wait ended with
#                                  (AGAST #4025), as is one whose unit is
#                                  active or of unknown state, or whose log
#                                  grew in the slice (#4318); 98 only for a
#                                  stopped unit with a still log.  After an
#                                  early end, sleep <pause> first so a
#                                  re-poll can't spin
#   cat <log>                      the log
#   stop <name>                    stop the gate's unit, if it runs
#   free [<pins...>]               how many more train gates the host can
#                                  start now (rz_train_free; AGAST #4031), or
#                                  "stale venv: <pins it misses>" if its venv
#                                  doesn't have these name==version pins
#                                  (rz_venv_drift; AGAST #4583)
read -r -d '' REMOTE_SH <<'EOF' || true
set -euo pipefail
abs() { case "$1" in /*) echo "$1" ;; *) echo "$HOME/$1" ;; esac; }
gate_of() { if [ "$2" = - ]; then echo "$1/.claude/skills/rz-iterate/run-gate.sh"; else echo "$2"; fi; }
# alive <log>: the log's gate is still going: its unit (the log's UNIT=) is
# active, or its line in the gate dir's .gate-queue ("<unit> <pid> ...",
# run-gate.sh) names a live pid: queued for a slot.
alive() {
    local unit q u p rest
    unit="$(sed -n 's/^UNIT=//p' "$1" | tail -1)"
    [ -n "$unit" ] || return 1
    systemctl --user is-active -q "$unit" 2>/dev/null && return 0
    q="$(dirname "$1")/.gate-queue"
    [ -f "$q" ] || return 1
    while read -r u p rest; do
        [ "$u" = "$unit" ] && kill -0 "$p" 2>/dev/null && return 0
    done < "$q"
    return 1
}
# ustate <log>: its unit's ActiveState (active, inactive, failed...), "none"
# with no UNIT= line, "unknown" if systemctl can't say (no user bus).
ustate() {
    local unit s
    unit="$(sed -n 's/^UNIT=//p' "$1" | tail -1)"
    [ -n "$unit" ] || { echo none; return; }
    s="$(systemctl --user show -p ActiveState --value "$unit" 2>/dev/null)" || s=""
    echo "${s:-unknown}"
}
main() {
    # systemd-run --user needs the user bus; a non-login ssh may not set it.
    export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
    local verb="$1"; shift
    case "$verb" in
    start)
        local repo wt gate got
        repo="$(abs "$1")"; wt="$(abs "$2")"; gate="$(gate_of "$wt" "$3")"
        PATH="$(rz_venv_path "$PATH")"; export PATH
        if ! python3 -c 'import pytest' >/dev/null 2>&1; then
            echo "error: $(hostname): the gate's python3 ($(command -v python3 || echo none)) can't import pytest; no gate started (PATH=$PATH)" >&2
            exit 1
        fi
        git -C "$repo" fetch -q origin "refs/heads/$4"
        got="$(git -C "$repo" rev-parse FETCH_HEAD)"
        [ "$got" = "$5" ] || { echo "error: origin $4 is $got, not the train tip $5" >&2; exit 1; }
        if [ -e "$wt/.git" ]; then git -C "$wt" checkout -q -f --detach "$5"
        else git -C "$repo" worktree add -q --detach "$wt" "$5"; fi
        # The venv against the tip's lock (AGAST #4583): `free` checked it
        # for gate --next's pick; this catches a host named outright, or one
        # whose venv changed since.
        local pins why
        mapfile -t pins < <(rz_lock_pins "$wt/projects/ritz/requirements.lock")
        if ! why="$(rz_venv_drift "${pins[@]}")"; then
            echo "error: $(hostname): stale venv: the gate's python3 ($(command -v python3)) does not match the train tip's requirements.lock: $why; no gate started (fix: python3 -m pip install -r projects/ritz/requirements.lock)" >&2
            exit 1
        fi
        RZ_GATE_TRAIN=1 RZ_GATE_BASE="$6" bash "$gate" "$wt" "$7" ;;
    wait)
        local rc=0 t0 s0 st why=""
        t0="$(date +%s)"; s0="$(wc -c < "$3")"
        timeout "$4" bash "$(gate_of "$(abs "$1")" "$2")" --wait "$3" >&2 || rc=$?
        [ "$rc" != 124 ] || exit 124
        grep -q '^EXIT=' "$3" && exit "$rc"
        # --wait ended with no verdict.  Its one `is-active` can miss a unit
        # that is still running (a loaded host's user bus; AGAST #4318), so
        # look again after <pause>, and call the gate dead only when its unit
        # has stopped and its log has stopped growing.
        [ $(( $(date +%s) - t0 )) -ge "$5" ] || sleep "$5"
        grep -q '^EXIT=' "$3" && exit 0                 # it ended meanwhile
        st="$(ustate "$3")"
        if alive "$3"; then why="its unit is $st or queued"
        elif [ "$(wc -c < "$3")" != "$s0" ]; then why="its log is still growing"
        else case "$st" in
            inactive|failed|none) ;;
            *) why="its unit is $st" ;;                # active, activating, unknown...
        esac; fi
        if [ -n "$why" ]; then
            echo "no verdict yet, gate still running: $why (--wait exit $rc)" >&2
            exit 124
        fi
        echo "unit stopped: $(sed -n 's/^UNIT=//p' "$3" | tail -1) is $st, its log not growing, and no EXIT= (--wait exit $rc)" >&2
        exit 98 ;;
    cat) cat "$1" ;;
    stop) systemctl --user stop "ritz-gate-$1" 2>/dev/null || true ;;
    free)
        # <pins...>: the train tip's lock (AGAST #4583).  A venv that misses
        # one has no slot for that train: say why instead of a count.
        local why
        PATH="$(rz_venv_path "$PATH")"; export PATH
        if ! why="$(rz_venv_drift "$@")"; then echo "stale venv: $why"; exit 0; fi
        rz_train_free ;;
    *) echo "error: unknown verb $verb" >&2; exit 2 ;;
    esac
}
# main runs in a subshell with errexit, and this shell ends at EOF with it
# off, never by the `exit` builtin (AGAST #5001).  `exit` in a login shell
# runs ~/.bash_logout, under errexit if it is on, and Ubuntu's runs
# `clear_console -q`, which fails with no console over ssh: errexit then
# turned every exit code into 1, so bangerang's live gates reported 1, not
# 124, and the local wait counted five of those as a stopped unit.  A
# subshell's exit runs no .bash_logout.
set +e
( set -euo pipefail; main "$@" ) </dev/null
EOF

# remote <host> <verb> <args...>: REMOTE_SH on <host>.  sshd joins the
# arguments into one command line for the remote shell, hence %q.
remote() {
    local host="$1"; shift
    # shellcheck disable=SC2086  # $SSH is a command line
    $SSH "$host" "bash -l -s -- $(printf '%q ' "$@")" <<<"$(declare -f rz_venv_path \
        rz_host_env_load rz_budget_scale_ok rz_gate_slots rz_train_free \
        rz_lock_pins rz_venv_drift)
$REMOTE_SH"
}

# discard_spec [<verb>]: drop the current train's speculative gate, if it has
# one; says <verb> (default DISCARDED).
discard_spec() {
    local st host ref rlog llog verb="${1:-DISCARDED}"; st="$(state)"
    [[ -f "$st" ]] || return 0
    read -r host ref rlog llog <<<"$(field SPEC "$st")"
    [[ -n "$host" ]] || return 0
    if is_local "$host"; then
        stop_local "$(gname)"
    else
        remote "$host" stop "$(gname)" >/dev/null 2>&1 || echo "warning: could not stop the gate on $host" >&2
        git -C "$MAIN_WT" push -q origin --delete "refs/heads/$ref" 2>/dev/null \
            || echo "warning: could not delete $ref on origin" >&2
    fi
    sed -i '/^SPEC=/d' "$st"
    echo "$verb speculative gate on $host for $(field TIP "$st" | cut -c1-12) ($llog)"
}

# stop_local <gate name>: stop this host's gate unit of that name if it runs,
# saying so on stdout (a CANCELLED line, from land), and drop its
# .train-waiting so room gates see the slot free at once.  Best effort.
stop_local() {
    local unit="ritz-gate-$1" tw="$GATES/.train-waiting"
    if systemctl --user is-active -q "$unit" 2>/dev/null; then
        systemctl --user stop "$unit" 2>/dev/null || echo "warning: could not stop $unit" >&2
        [[ -z "${2:-}" ]] || echo "CANCELLED local gate $unit ($2)"
    fi
    if [[ "$(cat "$tw" 2>/dev/null)" == "$unit" ]]; then rm -f "$tw"; fi
}

# publish_tail: push the current train's tail to origin
# refs/heads/rz-train/<tip12> (AGAST #3988 for a remote gate, #4409 for every
# built train).  Idempotent: a ref already at that SHA takes a no-op push, so
# gate --next can re-ensure a target built by an older train.sh.
publish_tail() {
    local st tip
    st="$(state)"; tip="$(field TIP "$st")"
    [[ -n "$tip" ]] || return 0
    g push -q -f origin "$tip:refs/heads/rz-train/${tip:0:12}"
}

# unpublish_tail <slot>: delete <slot>'s built tail from origin, when a build
# replaces the train, land covers it, or fail drops it (AGAST #4409).  Best
# effort: an absent ref is not an error.  Call it before the state file goes.
unpublish_tail() {
    local st tip
    # RZ_TRAIN lives at the slot's own worktree administrative dir
    # (state()'s --absolute-git-dir, as conflict_with() also reads it), never
    # the shared --git-common-dir: a worktree's are different directories,
    # and --git-common-dir's RZ_TRAIN is never written, so reading it there
    # always missed the file and this was a silent no-op (AGAST #4753: the
    # root cause behind "a fail drops it" never actually deleting a train's
    # tail ref).
    st="$(git -C "$(slot_wt "$1")" rev-parse --absolute-git-dir 2>/dev/null || true)/RZ_TRAIN"
    [[ -f "$st" ]] || return 0
    tip="$(field TIP "$st")"
    [[ -n "$tip" ]] || return 0
    git -C "$MAIN_WT" push -q origin --delete "refs/heads/rz-train/${tip:0:12}" 2>/dev/null || true
}

# --- Held tails and resolves (AGAST #4753) ----------------------------------
# `fail` unpublishes a red train's tail (unpublish_tail), but rz re-pushes it
# by hand so the culprit's room can fix forward on it (SKILL.md step 6.3),
# and a conflict resolution is pushed to its own `rz-resolve/<room>-<sha12>`
# ref (SKILL.md step 7).  Neither ref is named by any train's state once the
# train that unpublished it (or never published it, for a resolve) moves on,
# so nothing ever deleted them: held_file/held_resolve_file track them in the
# main worktree's git dir until the fix-forward or resolution lands.
held_file() { echo "$(git -C "$MAIN_WT" rev-parse --path-format=absolute --git-common-dir)/RZ_HELD_TAILS"; }
held_resolve_file() { echo "$(git -C "$MAIN_WT" rev-parse --path-format=absolute --git-common-dir)/RZ_HELD_RESOLVES"; }

# held_add <file> <ref> <sha>: record <ref> <sha> in <file>, once (idempotent:
# `hold-tail`/`hold-resolve` re-ensuring an already-held ref adds no second
# line).
held_add() {
    local file="$1" ref="$2" sha="$3"
    mkdir -p "$(dirname "$file")"
    [[ -f "$file" ]] && grep -qxF "$ref $sha" "$file" && return 0
    printf '%s %s\n' "$ref" "$sha" >> "$file"
}

# held_drop_landed <file> <landed-tip>: a fix-forward or resolution always
# reboards (it is cherry-picked or kept into a later train), so once that
# later train lands, every held ref whose recorded SHA is now an ancestor of
# the landed tip has served its purpose: delete it from origin (best effort)
# and drop its line.  <file> is rewritten in one rename, even to empty, so a
# reader never sees it half-written (as write_queue does for RZ_TRAINS).
# Prints one DELETED line per ref it drops.
held_drop_landed() {
    local file="$1" tip="$2" ref sha remain=()
    [[ -f "$file" ]] || return 0
    while read -r ref sha || [[ -n "$ref" ]]; do
        [[ -n "$ref" ]] || continue
        if git -C "$MAIN_WT" merge-base --is-ancestor "$sha" "$tip" 2>/dev/null; then
            git -C "$MAIN_WT" push -q origin --delete "refs/heads/$ref" 2>/dev/null \
                && echo "DELETED  $ref (held, landed)" \
                || echo "warning: could not delete $ref on origin" >&2
        else
            remain+=("$ref $sha")
        fi
    done < "$file"
    if [[ ${#remain[@]} -eq 0 ]]; then : > "$file.tmp.$$"; else printf '%s\n' "${remain[@]}" > "$file.tmp.$$"; fi
    mv -f "$file.tmp.$$" "$file"
}

# cmd_hold_tail <sha>: re-publish <sha> as a held rz-train/<sha12> tail
# (idempotent with publish_tail's push) and record it so `land` cleans it up.
cmd_hold_tail() {
    local sha="${1:?usage: $0 hold-tail <sha>}" full ref
    full="$(git -C "$MAIN_WT" rev-parse -q --verify "$sha^{commit}")" || die "no such commit: $sha"
    ref="rz-train/${full:0:12}"
    git -C "$MAIN_WT" push -q -f origin "$full:refs/heads/$ref"
    held_add "$(held_file)" "$ref" "$full"
    echo "HELD $ref"
}

# cmd_hold_resolve <room> <sha>: push <sha> as rz-resolve/<room>-<sha12> and
# record it the same way.
cmd_hold_resolve() {
    local room="${1:?usage: $0 hold-resolve <room> <sha>}" sha="${2:?usage: $0 hold-resolve <room> <sha>}"
    local full ref
    full="$(git -C "$MAIN_WT" rev-parse -q --verify "$sha^{commit}")" || die "no such commit: $sha"
    ref="rz-resolve/${room}-${full:0:12}"
    git -C "$MAIN_WT" push -q -f origin "$full:refs/heads/$ref"
    held_add "$(held_resolve_file)" "$ref" "$full"
    echo "HELD $ref"
}

# cmd_prune_refs [--dry-run]: delete every rz-train/* or rz-resolve/* ref on
# origin that no live train (its TIP= or SPEC= ref) or held file names, and
# that is either fully on main (git cherry origin/main <sha>: no `+` line, as
# the 2026-11-25 by-hand cleanup used, AGAST #4753) or older than
# RZ_PRUNE_DAYS days (default 2).  --dry-run says WOULD DELETE and deletes
# nothing.  rz runs this after landing, never a room, and never against a
# test's scratch origin by name (test-train.sh uses its own throwaway repo).
cmd_prune_refs() {
    local dry=0
    [[ "${1:-}" == --dry-run ]] && { dry=1; shift; }
    local days="${RZ_PRUNE_DAYS:-2}"
    [[ "$days" =~ ^[0-9]+$ ]] || die "RZ_PRUNE_DAYS must be a whole number: '$days'"
    local now cutoff; now="$(date +%s)"; cutoff=$((now - days * 86400))
    git -C "$MAIN_WT" fetch -q origin

    local -A keep=()
    local s st tip spec specref f ref sha
    for s in $(queue); do
        use_slot "$s"; st="$(state)"
        [[ -f "$st" ]] || continue
        tip="$(field TIP "$st")"
        [[ -n "$tip" ]] && keep["rz-train/${tip:0:12}"]=1
        spec="$(field SPEC "$st" | tail -1)"
        if [[ -n "$spec" ]]; then
            read -r _ specref _ <<<"$spec"
            [[ "$specref" != - ]] && keep["$specref"]=1
        fi
    done
    for f in "$(held_file)" "$(held_resolve_file)"; do
        [[ -f "$f" ]] || continue
        while read -r ref sha || [[ -n "$ref" ]]; do
            [[ -n "$ref" ]] && keep["$ref"]=1
        done < "$f"
    done

    local n=0 fullref why cdate
    while read -r sha fullref; do
        ref="${fullref#refs/heads/}"
        [[ -n "${keep[$ref]:-}" ]] && continue
        why=""
        if ! git -C "$MAIN_WT" cherry origin/main "$sha" 2>/dev/null | grep -q '^+'; then
            why="on main"
        else
            cdate="$(git -C "$MAIN_WT" log -1 --format=%ct "$sha" 2>/dev/null || echo "$now")"
            [[ "$cdate" -lt "$cutoff" ]] && why="older than ${days}d"
        fi
        [[ -n "$why" ]] || continue
        n=$((n + 1))
        if [[ $dry -eq 1 ]]; then
            echo "WOULD DELETE $ref ($why)"
        else
            git -C "$MAIN_WT" push -q origin --delete "refs/heads/$ref" 2>/dev/null \
                && echo "DELETED  $ref ($why)" \
                || echo "warning: could not delete $ref on origin" >&2
        fi
    done < <(git -C "$MAIN_WT" ls-remote --heads origin 'refs/heads/rz-train/*' 'refs/heads/rz-resolve/*')
    [[ $n -gt 0 ]] || echo "nothing to prune"
}

ensure_worktree() {
    if [[ ! -e "$WT/.git" ]]; then
        git -C "$MAIN_WT" worktree add -q --detach "$WT" "$1"
    fi
}

# start_train <slot> <base>: an empty train on <base> in <slot>'s worktree.
start_train() {
    use_slot "$1"; ensure_worktree "$2"
    # A half-finished pick from an interrupted run must not leak in.
    g cherry-pick --abort >/dev/null 2>&1 || true
    g reset -q --hard
    g checkout -q --detach "$2"
    printf 'BASE=%s\nBUILT=%s\n' "$2" "$(date +%s)" > "$(state)"
    TBASE="$2"; n=0; picked=0; k=$((k + 1)); slots+=("$1")
}

# finish_train: the summary.  A later train nothing boarded is dropped.
finish_train() {
    local st need=needed; st="$(state)"
    # Every train with a car needs a full gate (AGAST #4580 item 9: rooms
    # REAP on a subsystem smoke check, so a KEPT car's room may never have
    # run the full gate; main never moves without one).  A room's own full
    # gate of a KEPT car is still a verdict for the train whose tip it is:
    # pass its log to `land`.  Only a train with no car is not-needed.
    [[ $n -eq 0 ]] && need=not-needed
    printf 'TIP=%s\nGATE=%s\n' "$(g rev-parse HEAD)" "$need" >> "$st"
    echo "TRAIN $k base=${TBASE:0:12} tip=$(g rev-parse --short=12 HEAD) n=$n gate=$need"
    if [[ $n -eq 0 && $k -gt 1 ]]; then
        rm -f "$st"; unset 'slots[-1]'; echo "         (empty: dropped)"
    else
        # Every train's tail is a possible new-room base, not just a remote
        # gate's (AGAST #4409).
        publish_tail
    fi
}

# conflict_with <files>: the cars in the trains so far that touch <files>.
conflict_with() {
    local files="$1" b room new hit=() s st
    for s in "${slots[@]}"; do
        st="$(git -C "$(slot_wt "$s")" rev-parse --absolute-git-dir)/RZ_TRAIN"
        while read -r b room new; do
            if grep -qxF -f <(g diff --name-only "$new^" "$new") <<<"$files"; then hit+=("$b"); fi
        done < <(field ITEM "$st")
    done
    if [[ ${#hit[@]} -eq 0 ]]; then echo main; else (IFS=,; echo "${hit[*]}"); fi
}

# build_abort <rc>: the EXIT trap of a build past its checks (AGAST #4337).
# Dying part-way, it drops the trains it started and queues only the kept
# ones (their trees and gates untouched); the replaced ones are gone anyway.
BUILD_KEEP=-1
build_abort() {
    [[ $1 -ne 0 && $BUILD_KEEP -ge 0 ]] || return 0
    local s d
    for s in "${slots[@]:BUILD_KEEP}"; do
        unpublish_tail "$s"   # a tail built before the failure was published
        d="$(git -C "$(slot_wt "$s")" rev-parse --absolute-git-dir 2>/dev/null)" && rm -f "$d/RZ_TRAIN"
    done
    write_queue "${slots[@]:0:BUILD_KEEP}" || true
    echo "error: build stopped part-way: RZ_TRAINS holds the $BUILD_KEEP kept train(s) only; rebuild the rest" >&2
}

cmd_build() {
    local next=0 old=() keep=0 i st
    if [[ "${1:-}" == --next ]]; then next=1; shift; fi
    [[ $# -ge 1 ]] || die "usage: $0 build [--next] <branch>:<sha> ..."
    mapfile -t old < <(queue)
    if [[ $next -eq 1 && ${#old[@]} -gt 0 ]]; then
        # Train 1 is gating, and so is every later train with a SPEC
        # (AGAST #3988, #4031): keep them all, up to the last one gating (a
        # gate=not-needed train between two gating ones stays too), and
        # stack these cars on its tail.
        keep=1
        for ((i = 1; i < ${#old[@]}; i++)); do
            use_slot "${old[$i]}"; st="$(state)"
            if [[ -f "$st" && -n "$(field SPEC "$st")" ]]; then keep=$((i + 1))
            elif [[ ! -f "$st" || "$(field GATE "$st")" != not-needed ]]; then break; fi
        done
    elif [[ $next -eq 1 ]]; then
        echo "note: no train to stack on; building on origin/main" >&2
    fi
    build_on "$keep" "$@"
}

# rebased_of <reaped> <tip>: the commit over main on <tip>'s branch with
# <reaped>'s patch (git patch-id --verbatim), when the room rebased its REAPed
# commit cleanly and pushed it without a new gate or REAP (AGAST #4580).
# Empty when none matches: the patch changed, so the room must re-gate and
# REAP.
rebased_of() {
    local want c p sha
    [[ -n "$2" ]] || return 0
    want="$(git -C "$MAIN_WT" show --no-color --format='commit %H' "$1" | git -C "$MAIN_WT" patch-id --verbatim | awk '{print $1}')"
    [[ -n "$want" ]] || return 0
    while read -r p sha; do
        if [[ "$p" == "$want" ]]; then c="$sha"; fi
    done < <(git -C "$MAIN_WT" log -p --no-color --format='commit %H' "origin/main..$2" | git -C "$MAIN_WT" patch-id --verbatim)
    echo "${c:-}"
}

# build_on <keep> <items...>: keep the first <keep> trains as they are, and
# build <items> on the last one's tail (on origin/main for 0), replacing every
# later train.
#
# Nothing changes until every item checks out (AGAST #4337: a space for the
# colon died after the replaced trains were gone and RZ_TRAINS removed, so
# trains 2-4 gating remotely fell out of the queue): a malformed item dies
# first; then, fetched, an item that is no commit or not a commit on its
# branch (its tip or an ancestor) is a BAD line and stays out.  RZ_TRAINS is
# written once, when the new trains are built; a death part-way (build_abort)
# leaves the kept trains queued.
build_on() {
    local keep="$1"; shift
    local item branch sha full tip rebased reaped items=()
    for item in "$@"; do
        branch="${item%%:*}"; sha="${item#*:}"
        [[ "$branch" != "$item" && -n "$branch" && -n "$sha" ]] \
            || die "bad item '$item' (want <branch>:<sha>); nothing changed"
    done
    git -C "$MAIN_WT" fetch -q origin
    for item in "$@"; do
        branch="${item%%:*}"; sha="${item#*:}"
        if ! full="$(git -C "$MAIN_WT" rev-parse -q --verify "$sha^{commit}")"; then
            echo "BAD      $branch ${sha:0:12}: no such commit (fetched?)"; continue
        fi
        # The REAP must name the branch tip, or a commit on it: a room that
        # REAPs one slice per commit pushes the next slice before its train
        # boards the last, so the tip has moved on (AGAST #4382).  The
        # unlanded count below still limits the pick to the named slice.
        tip="$(git -C "$MAIN_WT" rev-parse -q --verify "origin/$branch" || true)"
        if [[ "$full" != "$tip" ]] \
                && ! { [[ -n "$tip" ]] \
                    && git -C "$MAIN_WT" merge-base --is-ancestor "$full" "$tip" 2>/dev/null; }; then
            # A clean rebase after the REAP (AGAST #4580): the room moved its
            # gated commit onto a train tail or main without re-gating and
            # sent no new REAP.  Board the branch's commit with the same
            # patch, as REBASED so it is APPLIED, never KEPT: its room gate
            # ran on another base, and only the train gate covers it.
            rebased="$(rebased_of "$full" "$tip")"
            if [[ -z "$rebased" ]]; then
                echo "BAD      $branch ${full:0:12}: origin/$branch is not this commit"; continue
            fi
            items+=("$branch:$rebased:$full"); continue
        fi
        items+=("$branch:$full")
    done
    local old=() s base i
    mapfile -t old < <(queue)
    slots=(); k=0
    if [[ $keep -gt 0 ]]; then
        # Kept trains: leave their worktrees and state alone.
        for ((i = 0; i < keep; i++)); do
            use_slot "${old[$i]}"
            base="$(field TIP "$(state)")"
            [[ "$base" == "$(g rev-parse HEAD)" ]] || die "train $((i + 1)) moved since build; rebuild it"
            slots+=("${old[$i]}"); k=$((i + 1))
        done
        old=("${old[@]:keep}")
    else
        base="$(git -C "$MAIN_WT" rev-parse origin/main)"
    fi
    # The old trains change from here on.
    BUILD_KEEP=$keep; trap 'build_abort $?' EXIT
    for s in ${old[@]+"${old[@]}"}; do
        [[ -e "$(slot_wt "$s")/.git" ]] || continue
        use_slot "$s"; discard_spec; unpublish_tail "$s"
        rm -f "$(state)"
    done
    # The lowest slot not holding a kept train.
    free_slot() { local i=1; while printf '%s\n' ${slots[@]+"${slots[@]}"} | grep -qx "$i"; do i=$((i + 1)); done; echo "$i"; }
    start_train "$(free_slot)" "$base"
    local first_new=$k

    local parent count mb files pick p sha2 left=()
    local -A have=() pid=()
    for item in ${items[@]+"${items[@]}"}; do
        # <branch>:<commit>[:<reaped>]: <reaped> is set for a car rebased
        # after its REAP (rebased_of); its lines name the REAPed SHA.
        branch="${item%%:*}"; full="${item#*:}"; reaped=""
        if [[ "$full" == *:* ]]; then reaped="${full#*:}"; full="${full%%:*}"; fi
        local shown="${reaped:-$full}"
        # One unlanded commit over main, or over train commits (a car bounced
        # to rebase onto a train's tail).  A commit already on the base (main,
        # every train below, and this train's earlier cars) does not count
        # when its patch is there under the train's cherry-picked SHA: that is
        # how a multi-slice room lands its later slices (AGAST #4382).  Patch
        # ids keep whitespace (--verbatim, not `git cherry`, #2796) and are
        # matched as a multiset, so duplicated slices neither collapse nor
        # hide a missing one (#4375).
        mb="$(g merge-base origin/main "$full")"
        count="$(g rev-list --count "$mb..$full")"
        if [[ "$count" == 1 ]]; then
            pick="$full"                       # the common shape: no patch-id work
        else
            have=(); pid=()
            while read -r p sha2; do
                [[ -n "$p" ]] && have[$p]=$(( ${have[$p]:-0} + 1 ))
            done < <(g log -p --no-color --format='commit %H' "$mb..HEAD" | g patch-id --verbatim)
            while read -r p sha2; do
                [[ -n "$p" ]] && pid[$sha2]="$p"
            done < <(g log -p --no-color --format='commit %H' "$mb..$full" | g patch-id --verbatim)
            left=()
            while read -r sha2; do
                p="${pid[$sha2]:-}"
                if [[ -n "$p" && ${have[$p]:-0} -gt 0 ]]; then
                    have[$p]=$(( have[$p] - 1 ))
                else
                    left+=("$sha2")
                fi
            done < <(g rev-list --reverse "$mb..$full")
            if [[ ${#left[@]} -eq 0 ]]; then
                echo "EMPTY    $branch ${shown:0:12}"; continue
            fi
            if [[ ${#left[@]} -ne 1 ]]; then
                echo "BAD      $branch ${shown:0:12}: $count commits over main, ${#left[@]} not in the train; want 1 over it"
                continue
            fi
            pick="${left[0]}"
        fi
        if [[ $n -ge $MAX ]]; then
            finish_train
            start_train "$(free_slot)" "$(g rev-parse HEAD)"
        fi
        parent="$(g rev-parse "$pick^")"
        if [[ "$parent" == "$(g rev-parse HEAD)" && -z "$reaped" ]]; then
            # On the tail already: keep its SHA, so a room's full gate of it
            # is still a verdict for this train (`land <room log>`).
            # Not a car rebased after its REAP: its gate ran on another base.
            g merge -q --ff-only "$pick"
            echo "KEPT     $branch ${shown:0:12}"
            printf 'ITEM=%s %s %s\n' "$branch" "$full" "$pick" >> "$(state)"
            n=$((n + 1)); continue
        fi
        # The car's committer date: the same car on the same tail is the
        # same commit, however often the train is rebuilt.
        if ! GIT_COMMITTER_DATE="$(g log -1 --format=%cd --date=raw "$pick")" \
                g cherry-pick --empty=drop "$pick" >/dev/null 2>&1; then
            files="$(g diff --name-only --diff-filter=U)"
            g cherry-pick --abort >/dev/null 2>&1 || g reset -q --hard
            echo "CONFLICT $branch ${shown:0:12} with $(conflict_with "$files") on $(paste -sd, <<<"$files")"
            continue
        fi
        # --empty=drop succeeds without a commit when main already has it.
        if [[ "$(g rev-list --count "$TBASE..HEAD")" -le $n ]]; then
            echo "EMPTY    $branch ${shown:0:12}"; continue
        fi
        echo "APPLIED  $branch ${shown:0:12} as $(g rev-parse --short=12 HEAD)"
        printf 'ITEM=%s %s %s\n' "$branch" "$shown" "$(g rev-parse HEAD)" >> "$(state)"
        n=$((n + 1)); picked=$((picked + 1))
    done
    finish_train
    write_queue "${slots[@]}"
    # A kept train built before every build published tails (AGAST #4409)
    # still gets the deepest one: a new room may base on it.
    if [[ $picked -eq 0 && ${#slots[@]} -gt 0 ]]; then
        use_slot "${slots[-1]}"; publish_tail
    fi
    BUILD_KEEP=-1
    # No train gate is coming to take over the reservation: let rooms in.
    if [[ $first_new -eq 1 ]]; then
        use_slot "${slots[0]}"
        [[ "$(field GATE "$(state)")" == not-needed ]] && rm -f "$RESERVED"
    fi
    return 0
}

cmd_show() {
    local s i=0
    [[ -n "$(queue)" ]] || die "no train built"
    for s in $(queue); do
        use_slot "$s"; i=$((i + 1))
        echo "== train $i $WT"
        cat "$(state)"
    done
}

# cmd_tail: the deepest built train's tail — the base a new room should use
# (AGAST #4409, #4413).  Prints "<tip12> rz-train/<tip12>", or nothing when no
# train is built.  A train whose state file is gone, or whose published tail
# ref is absent on origin (its build was replaced, it failed, or it landed),
# is not a built train: never report such a stale TIP= (AGAST #4413).  Exits 2
# when origin can't be asked: an absent answer is not the same as an absent
# ref, and the caller must not act on it.
cmd_tail() {
    local q=() i st tip ref got
    mapfile -t q < <(queue)
    for ((i = ${#q[@]} - 1; i >= 0; i--)); do
        use_slot "${q[$i]}"; st="$(state)"
        [[ -f "$st" ]] || continue
        tip="$(field TIP "$st")"
        [[ -n "$tip" ]] || continue
        ref="rz-train/${tip:0:12}"
        if ! got="$(git -C "$MAIN_WT" ls-remote --heads origin "refs/heads/$ref" 2>/dev/null)"; then
            echo "error: cannot reach origin to check $ref (is it built?)" >&2
            exit 2
        fi
        [[ "$(cut -f1 <<<"$got")" == "$tip" ]] || continue
        echo "${tip:0:12} $ref"
        return 0
    done
    return 0
}

# gate_live <room> <field>: 0 when a gate for <room> is live.  <field> from
# the caller (gating|idle) wins: that is how a remote room is fed from its
# host's STATUS gate list.  "-" or empty asks this host: the room's
# ritz-gate-<room> unit (AGAST #4413).
gate_live() {
    local room="$1" g="${2:-}"
    case "$g" in
        gating) return 0 ;;
        idle) return 1 ;;
    esac
    systemctl --user is-active -q "ritz-gate-$room" 2>/dev/null
}
# gate_reason <room> <field>: where the liveness came from, for the SKIP line.
gate_reason() {
    local room="$1" g="${2:-}"
    case "$g" in
        gating|idle) echo "host STATUS" ;;
        *) echo "ritz-gate-$room is active" ;;
    esac
}

# cmd_rebase_plan [<ref>] [--dropped <oldtip> [--onto <ref>]]: one rz loop
# turn of the preemptive rebase advisory (AGAST #4413).  Every loop turn, a
# room based on an older base than the deepest train tail is told (once) to
# rebase onto that tail, so its car boards the train as KEPT instead of being
# cherry-picked; a room mid-gate is skipped, never rewound.  Advisory only:
# this moves no branch and touches no worktree.
#
# stdin, one room per line:
#   <room> <base> [<gate>]
#     <room>  the room name (ritz-task-<id>)
#     <base>  the room HEAD's merge-base with the reference (the caller's
#             job: local `git -C <wt> merge-base <ref> HEAD`, a remote room's
#             from its host's STATUS, or a base the caller already knows),
#             full or 12-char SHA; "-" when unknown.
#     <gate>  gating|idle, or - / absent to ask this host (gate_live).  A
#             remote room is fed from its host's STATUS gate list.
# The reference is <ref> when given, else the deepest built train's tail
# (cmd_tail), else origin/main.  Output is one status line per room, then at
# most one action line:
#   ROOM <room> base=<b12> tail=<t12|main> on-tail|behind|unknown|other
#   SKIP <room>: gate live (<why>); not rebasing mid-gate
#   REBASE <room> onto <t12>: rebase onto <t12>: `git fetch origin
#          rz-train/<t12> && git rebase FETCH_HEAD`; clean: push it, no
#          re-check and no new REAP; conflicted or changed code: resolve,
#          re-check and REAP (AGAST #4580; see rebase_line)
#   BOUNCE <room> onto <t12|main>: the train was discarded; rebase onto
#          <t12|main>: ... (--dropped mode)
# --dropped <oldtip>: bounce the rooms whose <base> is exactly <oldtip>, onto
# <ref>/--onto or the deepest tail/main: a room spawned on a tail whose train
# failed or was replaced must move even when no newer tail carries its cars.
# Rooms not based on <oldtip> are listed "other" and left alone.
cmd_rebase_plan() {
    local refarg="" dropped="" ref refname base_full t room base gate b12 why
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dropped) dropped="${2:?--dropped needs a commit}"; shift 2 ;;
            --onto)    refarg="${2:?--onto needs a commit}"; shift 2 ;;
            *)         refarg="$1"; shift ;;
        esac
    done
    if [[ -n "$refarg" ]]; then
        ref="$(git -C "$MAIN_WT" rev-parse -q --verify "$refarg^{commit}" 2>/dev/null)" \
            || die "no such commit: $refarg"
        if [[ "$ref" == "$(git -C "$MAIN_WT" rev-parse origin/main)" ]]; then
            refname="main"
        else
            refname="${refarg#refs/heads/}"; refname="${refname#rz-train/}"
            refname="${refname:0:12}"
        fi
    else
        t="$(cmd_tail | awk '{print $1}')"
        if [[ -n "$t" ]]; then
            ref="$(git -C "$MAIN_WT" rev-parse -q --verify "$t^{commit}")"
            refname="$t"
        else
            ref="$(git -C "$MAIN_WT" rev-parse origin/main)"
            refname="main"
        fi
    fi
    if [[ -n "$dropped" ]]; then
        local oldname="$dropped" dropped_sha
        dropped_sha="$(git -C "$MAIN_WT" rev-parse -q --verify "$dropped^{commit}" 2>/dev/null)" \
            || die "no such commit: $oldname"
        dropped="$dropped_sha"
    fi
    while read -r room base gate || [[ -n "$room" ]]; do
        [[ -n "$room" && "$room" != \#* ]] || continue
        base_full=""
        if [[ "$base" != - && -n "$base" ]]; then
            base_full="$(git -C "$MAIN_WT" rev-parse -q --verify "$base^{commit}" 2>/dev/null || true)"
        fi
        if [[ -z "$base_full" ]]; then
            echo "ROOM $room base=? tail=$refname unknown"
            continue
        fi
        b12="${base_full:0:12}"
        if [[ -n "$dropped" ]]; then
            if [[ "$base_full" != "$dropped" ]]; then
                echo "ROOM $room base=$b12 tail=$refname other"
                continue
            fi
            echo "ROOM $room base=$b12 tail=$refname dropped"
            if gate_live "$room" "$gate"; then
                why="$(gate_reason "$room" "$gate")"
                echo "SKIP $room: gate live ($why); not rebasing mid-gate"
                continue
            fi
            rebase_line BOUNCE "$room" "$refname"
            continue
        fi
        if [[ "$base_full" == "$ref" ]]; then
            echo "ROOM $room base=$b12 tail=$refname on-tail"
            continue
        fi
        echo "ROOM $room base=$b12 tail=$refname behind"
        if gate_live "$room" "$gate"; then
            why="$(gate_reason "$room" "$gate")"
            echo "SKIP $room: gate live ($why); not rebasing mid-gate"
            continue
        fi
        rebase_line REBASE "$room" "$refname"
    done
}

# rebase_line <verb> <room> <refname>: the one message the caller sends (or
# forwards) for <room>.  main has no rz-train ref: fetch it directly.
# A clean rebase is not re-checked (AGAST #4580, Aaron 2026-11-23): the room
# pushes it and, if it already REAPed, sends no new REAP; `build` boards the
# original REAP as APPLIED and the train gate covers it.  A room still
# working checks once, when it finishes (smoke-plan.sh run).  Only a rebase
# that conflicted, or made the room change code, is re-checked and REAPed.
REBASE_TAIL='clean: push it, no re-check and no new REAP (the train gate covers it; still working: check once when done); conflicted or changed code: resolve, re-check (smoke-plan.sh run) and REAP'
rebase_line() {
    local verb="$1" room="$2" refname="$3" fetch
    if [[ "$refname" == main ]]; then
        fetch='git fetch origin && git rebase FETCH_HEAD'
        printf '%s %s onto main: rebase onto main: `%s`; %s\n' \
            "$verb" "$room" "$fetch" "$REBASE_TAIL"
    else
        fetch="git fetch origin rz-train/$refname && git rebase FETCH_HEAD"
        printf '%s %s onto %s: rebase onto %s: `%s`; %s\n' \
            "$verb" "$room" "$refname" "$refname" "$fetch" "$REBASE_TAIL"
    fi
}

# gate_log: the current train's gate log: its SPEC's local log, else its
# last GATED=; empty if it was never gated.
gate_log() {
    local st spec; st="$(state)"; spec="$(field SPEC "$st")"
    if [[ -n "$spec" ]]; then echo "${spec##* }"; else field GATED "$st" | tail -1; fi
}

# verdict: the current train's gate: none (not gating), running (no EXIT=
# yet, or a remote log not fetched yet), pass, or red.  A log for another
# SHA than the tip is no gate of this train: none.
verdict() {
    local log sha rc; log="$(gate_log)"
    [[ -n "$log" ]] || { echo none; return; }
    [[ -f "$log" ]] || { echo running; return; }
    sha="$(sed -n 's/^SHA=//p' "$log" | tail -1)"
    if [[ -n "$sha" && "$sha" != "$(field TIP "$(state)")" ]]; then echo none; return; fi
    rc="$(sed -n 's/^EXIT=//p' "$log" | tail -1)"
    case "$rc" in "") echo running ;; 0) echo pass ;; *) echo red ;; esac
}

# pick_target: the train to gate (AGAST #4156; see the header).  Sets TGT
# (its number), REASON (deepest|bisect red train <r>) and returns 0; else
# returns 1 with WHY, and FAILK=<r> when a red train has nothing below it
# to bisect.
pick_target() {
    local q v=() i r=0 g=0 last need=0
    TGT=0; REASON=""; WHY=""; FAILK=0
    mapfile -t q < <(queue)
    [[ ${#q[@]} -gt 0 ]] || { WHY="no train built"; return 1; }
    for i in "${!q[@]}"; do use_slot "${q[$i]}"; v+=("$(verdict)"); done
    for i in "${!q[@]}"; do
        if [[ ${v[$i]} == red ]]; then r=$((i + 1)); break; fi
        [[ ${v[$i]} != pass ]] || g=$((i + 1))
    done
    if [[ $r -gt 0 ]]; then
        use_slot "${q[$((r - 1))]}"
        if [[ $((r - g)) -lt 2 ]]; then
            FAILK=$r
            WHY="train $r's gate is red with nothing below it to bisect: train.sh fail $(gate_log) (or re-gate it: train.sh gate $r)"
            return 1
        fi
        for ((i = g; i < r - 1; i++)); do
            if [[ ${v[$i]} == running ]]; then
                WHY="train $((i + 1)) is gating below red train $r: wait for its verdict"; return 1
            fi
        done
        TGT=$((g + (r - g) / 2)); REASON="bisect red train $r"; return 0
    fi
    last=${#q[@]}
    use_slot "${q[$((last - 1))]}"
    case "${v[$((last - 1))]}" in
        running) WHY="train $last is already gating (deepest first: no shorter prefix gates unless it goes red): train.sh wait $(gate_log)"; return 1 ;;
        pass) WHY="train $last passed: train.sh land $(gate_log)"; return 1 ;;
    esac
    for i in "${!q[@]}"; do
        use_slot "${q[$i]}"
        [[ "$(field GATE "$(state)")" != needed ]] || need=1
    done
    [[ $need -eq 1 ]] || { WHY="no train needs a gate (each gate=not-needed): train.sh land"; return 1; }
    TGT=$last; REASON=deepest
}

# cmd_gate [<k>|--next [<host>]]: gate the train to gate here, or train <k>.
cmd_gate() {
    if [[ "${1:-}" == --next ]]; then gate_next "${2:-}"; return; fi
    local q k="${1:-}"; REASON=""
    mapfile -t q < <(queue)
    [[ ${#q[@]} -gt 0 ]] || die "no train built"
    if [[ -z "$k" ]]; then
        pick_target || die "$WHY"
        k=$TGT
    else
        [[ "$k" =~ ^[1-9][0-9]*$ && $k -le ${#q[@]} ]] || die "no train $k (${#q[@]} built)"
    fi
    use_slot "${q[$((k - 1))]}"
    local st spec; st="$(state)"
    [[ "$(field TIP "$st")" == "$(g rev-parse HEAD)" ]] \
        || die "train $k's worktree moved since build; rebuild"
    # A train built by an older train.sh has no tail ref yet (AGAST #4409);
    # a build publishes it, and this is a no-op when it already did.
    publish_tail
    spec="$(field SPEC "$st")"
    if [[ -n "$spec" ]]; then
        case "$(verdict)" in
            running) die "train $k is already gating on ${spec%% *}: train.sh wait ${spec##* } (to gate it here instead, rebuild it: the same cars give the same tip)" ;;
            pass) die "train $k passed on ${spec%% *}: train.sh land ${spec##* }" ;;
        esac
        discard_spec >/dev/null      # red (or a stale log): re-gate it here
    fi
    # The base is main, train 1's base (AGAST #4151): a pass lands every train
    # below too, so the ritz0 diff scope covers them.  The PKGS line previews
    # the packages the trains touch (AGAST #3363); the gate's test-all job
    # tests every package (AGAST #3969, #3970).  stdout is only the log path.
    local base pkgs log
    base="$(use_slot "${q[0]}"; field BASE "$(state)")"
    pkgs="$(cd "$WT" && bash "$HERE/train.sh" pkgs list "$base")"
    [[ -z "$pkgs" ]] || echo "PKGS $(tr '\n' ' ' <<<"$pkgs")" >&2
    # Train priority: the next free slot goes to this gate ahead of room
    # gates (run-gate.sh, AGAST #3317).  GATED/SPEC: `pending` skips it (#4031).
    log="$(RZ_GATE_TRAIN=1 RZ_GATE_BASE="$base" "$GATE" "$WT" "$(gname)")"
    if [[ $k -eq 1 ]]; then printf 'GATED=%s\n' "$log" >> "$st"
    else printf 'SPEC=%s - %s %s\n' "$LOCAL" "$log" "$log" >> "$st"; fi
    echo "GATE train $k tip=$(field TIP "$st" | cut -c1-12) here${REASON:+ ($REASON)}: $log" >&2
    echo "$log"
}

# gate_next [<host>]: gate the train to gate (pick_target: the deepest, or a
# bisect prefix; AGAST #4156), train 1 included, on <host> or the first
# RZ_TRAIN_HOSTS host with a free train slot (AGAST #3988, #4031, #4422; see
# the header).  Train 1 tries the remote hosts first and falls back to a gate
# here (plain `gate`) when none has a free train slot.  stdout is only the
# local log path.
gate_next() {
    local host="$1" q i k flight=0 st tip base ref rlog llog
    mapfile -t q < <(queue)
    [[ ${#q[@]} -gt 0 ]] || die "no train built"
    pick_target || die "$WHY"
    k=$TGT
    # The base is main (train 1's base), not the tail below (AGAST #4151): a
    # pass here lands every train below too, so the ritz0 diff scope must
    # cover their cars as well.
    use_slot "${q[0]}"; base="$(field BASE "$(state)")"
    for i in "${!q[@]}"; do
        use_slot "${q[$i]}"; st="$(state)"
        [[ -z "$(field SPEC "$st")$(field GATED "$st")" ]] || flight=$((flight + 1))
    done
    [[ $flight -lt $DEPTH ]] || die "$flight trains in flight already (at most $DEPTH, RZ_TRAIN_DEPTH): train.sh wait their logs"
    use_slot "${q[$((k - 1))]}"; st="$(state)"
    tip="$(field TIP "$st")"
    [[ "$tip" == "$(g rev-parse HEAD)" ]] || die "train $k's worktree moved since build; rebuild"
    if [[ -z "$host" ]]; then
        if [[ $k -eq 1 ]]; then
            # Train 1 goes off this host (AGAST #4422: the coordinator's one
            # gate slot is for rooms then); plain `gate` here is the fallback
            # when no remote host has a free train slot.
            host="$(pick_train_host remote)" || {
                echo "note: no remote host in RZ_TRAIN_HOSTS ($HOSTS) has a free train slot: gating train 1 here" >&2
                host="$LOCAL"
            }
        else
            host="$(pick_train_host)" \
                || die "no host in RZ_TRAIN_HOSTS ($HOSTS) has a free train slot: gate train $k when one frees"
        fi
    fi
    # The tail is published for the remote gate and for a new room's base
    # (AGAST #4409): a local gate needs the ref for the room, too.
    ref="rz-train/${tip:0:12}"
    publish_tail
    if is_local "$host"; then
        llog="$(RZ_GATE_TRAIN=1 RZ_GATE_BASE="$base" "$GATE" "$WT" "$(gname)")" \
            || die "the local gate for train $k did not start"
        if [[ $k -eq 1 ]]; then
            printf 'GATED=%s\n' "$llog" >> "$st"
            echo "GATED train 1 tip=${tip:0:12} here${REASON:+ ($REASON)}: $llog" >&2
        else
            printf 'SPEC=%s - %s %s\n' "$host" "$llog" "$llog" >> "$st"
            echo "SPEC train $k tip=${tip:0:12} on $host (local): $llog" >&2
        fi
        echo "$llog"
        return
    fi
    if ! rlog="$(remote "$host" start "$REMOTE_REPO" "$(rwt)" "$REMOTE_GATE" "$ref" "$tip" "$base" "$(gname)" | tail -1)" \
            || [[ "$rlog" != /*.log ]]; then
        g push -q origin --delete "refs/heads/$ref" 2>/dev/null || true
        if [[ $k -eq 1 ]]; then
            die "the remote gate on $host did not start (got '$rlog'); gate train 1 elsewhere (gate --next <host>) or here (plain \`gate\`)"
        fi
        die "the remote gate on $host did not start (got '$rlog'); gate train $k elsewhere (gate --next <host>) or here once the trains below land"
    fi
    llog="$GATES/$(basename "${rlog%.log}")@$host.log"
    printf 'SPEC=%s %s %s %s\n' "$host" "$ref" "$rlog" "$llog" >> "$st"
    # The next gate is on another host, so no train gate will come here to
    # take over land's reservation: release the local slot for room gates at
    # once (AGAST #4526).  Only after the remote gate has started, and never
    # on the local branch above, whose fallback gate the reservation protects.
    rm -f "$RESERVED"
    echo "SPEC train $k tip=${tip:0:12} on $host: $rlog" >&2
    echo "$llog"
}

# pick_train_host [remote]: the first RZ_TRAIN_HOSTS host with a free train
# slot (rz_train_free: a slot no gate holds, less the train gates queued there).
# This host is asked directly, the rest over ssh; an unreachable one is
# skipped.  Says why on stderr for each host it passes over.  With `remote`,
# this host is passed over too: train 1 prefers another host, and gates here
# only as its fallback (AGAST #4422).  A host whose venv misses a pin of the
# train's requirements.lock (rz_venv_drift; AGAST #4583) is passed over too,
# "stale venv: <pins>": its gate would fail on the host, not the train.
pick_train_host() {
    local remote="${1:-}" h n pins
    mapfile -t pins < <(g show HEAD:projects/ritz/requirements.lock 2>/dev/null | rz_lock_pins -)
    for h in $HOSTS; do
        [[ -z "$remote" ]] || ! is_local "$h" || continue
        if ! is_local "$h"; then n="$(remote "$h" free "${pins[@]}" 2>/dev/null | tail -1)" || n=""
        elif ! n="stale venv: $(PATH="$(rz_venv_path "$PATH")" rz_venv_drift "${pins[@]}")"; then :
        else n="$(rz_train_free "$GATES" 2>/dev/null)" || n=""; fi
        if [[ "$n" =~ ^[0-9]+$ && $n -gt 0 ]]; then echo "$h"; return 0; fi
        if [[ "$n" == "stale venv: "* ]]; then echo "note: $h: $n" >&2; continue; fi
        echo "note: $h: ${n:+no free train slot}${n:-unreachable}" >&2
    done
    return 1
}

# cmd_wait <log>: block until the gate ends; exit with its code.  A remote
# gate's log is fetched to <log> once it ends; a log for another SHA than its
# train's tip exits 3.  Only an EXIT= line in that log ends a remote wait: it
# polls in WAIT_SLICE slices with no cap while the remote unit is active (or
# its state unknown) or the log still grows (AGAST #4116, #4318).  No verdict
# (98, never exit 0) is only 5 reports of a stopped unit with no EXIT= and
# a still log (the remote's 98), 5 wait errors in a row (any other code: the
# gate may be live, AGAST #5001), or 5 ssh failures in a row (host
# unreachable); the EXIT=none line says which.
# The remote wait runs in the train's own slot tree, $(rwt) (AGAST #4247).
cmd_wait() {
    local log="${1:?usage: $0 wait <log>}" s st="" spec="" host ref rlog llog rc tries=0 nov=0 errs=0 tip
    # The caller often pastes the local copy `gate --next` printed relative to
    # the repo root, while SPEC records it absolutely (AGAST #4525).  realpath
    # -m resolves a path that does not exist yet (the verdict is fetched
    # later).  The basename fallback is safe too: the copy always ends
    # `@<host>.log`, so it is unique within a state file.
    local want; want="$(realpath -m -- "$log")"
    for s in $(queue); do
        use_slot "$s"
        spec="$(field SPEC "$(state)")"
        if [[ -n "$spec" ]] \
            && { [[ "$(realpath -m -- "${spec##* }")" == "$want" ]] \
                || [[ "$(basename "${spec##* }")" == "$(basename "$log")" ]]; }; then
            st="$(state)"; break
        fi
        spec=""
    done
    if [[ -z "$spec" ]]; then
        [[ "$log" != *@*.log ]] || die "no train has a remote gate with log $log: discarded by a rebuild?"
        exec bash "$GATE" --wait "$want"
    fi
    read -r host ref rlog llog <<<"$spec"
    # A speculative gate on this host (AGAST #4031): its log is local.
    if is_local "$host"; then exec bash "$GATE" --wait "$rlog"; fi
    tip="$(field TIP "$st")"
    local why="" out crc
    while :; do
        rc=0; remote "$host" wait "$(rwt)" "$REMOTE_GATE" "$rlog" "$WAIT_SLICE" "$QUEUED_PAUSE" || rc=$?
        if [[ $rc -eq 255 ]]; then                        # ssh itself failed
            tries=$((tries + 1))
            if [[ $tries -ge 5 ]]; then
                why="host unreachable: ssh to $host failed 5 times in a row"; break
            fi
            sleep "$SSH_RETRY"; continue
        fi
        tries=0                                           # 5 in a row, not 5 per wait
        if [[ $rc -eq 124 ]]; then nov=0; continue; fi    # still running
        # The slice ended: fetch the log, retrying the fetch itself.
        for crc in 1 2 3 4 5; do
            out="$(remote "$host" cat "$rlog")" && { crc=0; break; }
            [[ $crc -eq 5 ]] || sleep "$SSH_RETRY"
        done
        if [[ $crc -ne 0 ]]; then
            why="host unreachable: could not fetch $rlog from $host 5 times in a row"; break
        fi
        printf '%s\n' "$out" > "$llog.tmp" && mv -f "$llog.tmp" "$llog"
        grep -q '^EXIT=' "$llog" && break
        # The slice ended with no verdict.  Only the remote's 98 says the
        # unit has stopped and its log no longer grows (AGAST #4318: a unit
        # still active, of unknown state, or a growing log is 124 above,
        # however long the gate runs); 5 such reports are a dead gate, and a
        # wait error between them doesn't reset the count.  Any other code
        # is an error in the wait itself, not a stopped unit (AGAST #5001:
        # bangerang's remote waits all exited 1 and two live train gates
        # were called dead): retried, and 5 in a row with no 98 between them
        # are reported as that error.
        if [[ $rc -eq 98 ]]; then
            nov=$((nov + 1)); errs=0
            if [[ $nov -ge 5 ]]; then
                why="unit stopped: the gate on $host ended without writing EXIT="; break
            fi
        else
            errs=$((errs + 1))
            if [[ $errs -ge 5 ]]; then
                why="the remote wait failed 5 times in a row (last exit $rc), so the gate on $host may still be running: check its unit before discarding it"; break
            fi
        fi
        echo "no EXIT= yet in $host:$rlog (wait exit $rc): polling again" >&2
        sleep "$QUEUED_PAUSE"
    done
    if [[ -n "$why" ]]; then
        echo "gate $(basename "$llog") SHA=${tip:0:12} EXIT=none — no verdict, $why"
        exit 98
    fi
    if [[ "$(sed -n 's/^SHA=//p' "$llog" | tail -1)" != "$tip" ]]; then
        echo "REFUSED: $host's verdict is for $(sed -n 's/^SHA=//p' "$llog" | tail -1 | cut -c1-12), not the train tip ${tip:0:12}" >&2
        exit 3
    fi
    rc="$(sed -n 's/^EXIT=//p' "$llog" | tail -1)"
    echo "gate $(basename "$llog") SHA=${tip:0:12} EXIT=${rc:-none}"
    [[ "$rc" =~ ^[0-9]+$ ]] || exit 98
    exit "$rc"
}

# --- Touched packages (AGAST #3363) ---------------------------------------
#   pkgs list <base>   the package dirs the train touches, one per line
#
# `gate` prints them as its PKGS preview line.  The gate itself tests every
# package in main.yml's test-all job (AGAST #3969).  `pkgs test`, which
# re-tested the touched packages after that and re-ran a failing one on the
# base to excuse a PRE-EXISTING failure, is retired (AGAST #3970): test-all
# stopped the gate at a failing package first, so the base re-run never ran,
# and main is gated by test-all, so a package failing on main is rare.
#
# A touched file belongs to the deepest directory above it with a ritz.toml,
# so a nested package (projects/ritzunit/inventory) is listed on its own.
# Skipped: the projects/ritz package itself (build-all + bootstrap is its
# gate), and rz.toml [workspace.exclude] dirs, which resolve to the package
# above them.  A package nested in projects/ritz (ritzlib/tests) is NOT
# skipped, and a ritzlib change selects ritzlib/tests (AGAST #3909, below).
# Except: a change to ritzunit or ritz0/test_runner.py selects every package
# `rz test --all` sweeps, projects/ritz's included (AGAST #3735, below).

# toml_keys <python expr over the parsed rz.toml `c`>: one key per line.
toml_keys() {
    [[ -f rz.toml ]] || return 0
    python3 -c 'import sys, tomllib
c = tomllib.load(open("rz.toml", "rb"))
for k in eval(sys.argv[1]): print(k)' "$1"
}

in_list() {
    local x="$1" k; shift
    for k in "$@"; do [[ "$x" == "$k" || "$x" == "$k"/* ]] && return 0; done
    return 1
}

# A change to ritzunit (its own package, not the nested inventory demo) or to
# ritz0/test_runner.py touches every package: ritzunit is linked into every
# test binary as its `main` (test_runner.py build_runner_objects).  #2072 was
# ritzunit-only, so its gate never tested ritzlib/tests or zeus, which it
# broke, and main's CI went red (AGAST #3725, #3735).  Such a train tests what
# `rz test --all` sweeps: rz.toml [workspace] members minus
# [workspace.exclude], projects/ritz and its nested packages included.
ALL_PKGS_PKG=projects/ritzunit
ALL_PKGS_FILE=projects/ritz/ritz0/test_runner.py

# ritzlib's sources live in the projects/ritz package, which the list drops,
# but its tests are their own package that ci-local never runs: #3880 broke
# ritzlib/tests and its ritzlib-only train tested nothing (AGAST #3909).  So a
# change anywhere under ritzlib selects ritzlib/tests.
RITZLIB_DIR=projects/ritz/ritzlib
RITZLIB_TESTS=projects/ritz/ritzlib/tests

# all_pkgs: every package dir `rz test --all` sweeps (rz discover_projects).
all_pkgs() {
    python3 -c 'import tomllib
from pathlib import Path
c = tomllib.load(open("rz.toml", "rb"))
w = c.get("workspace", {})
excl = [Path(e.rstrip("/")) for e in w.get("exclude", {})]
for pat in w.get("members") or ["projects/**"]:
    for m in Path(".").glob(pat + "/ritz.toml"):
        d = m.parent
        if not any(d == e or e in d.parents for e in excl):
            print(d)' | sort -u
}

pkgs_list() {
    local base="$1" f d excl touched
    mapfile -t excl < <(toml_keys 'c.get("workspace", {}).get("exclude", {})')
    touched="$(git diff --name-only "$base" HEAD -- projects/ | while IFS= read -r f; do
        [[ "$f" == "$ALL_PKGS_FILE" ]] && echo "$ALL_PKGS_PKG"
        [[ "$f" == "$RITZLIB_DIR"/* && -f "$RITZLIB_TESTS/ritz.toml" ]] && echo "$RITZLIB_TESTS"
        d="$(dirname "$f")"
        while [[ "$d" == projects/* ]]; do
            if [[ -f "$d/ritz.toml" ]] && ! in_list "$d" ${excl[@]+"${excl[@]}"}; then
                echo "$d"
                break
            fi
            d="$(dirname "$d")"
        done
    done | sort -u)"
    if grep -qxF -- "$ALL_PKGS_PKG" <<<"$touched"; then
        all_pkgs
        return
    fi
    # Only the compiler package itself: a package nested in it is not ci-local's.
    [[ -z "$touched" ]] || grep -vxF projects/ritz <<<"$touched" || true
}

cmd_pkgs() {
    [[ $# -eq 2 && "$1" == list ]] || die "usage: $0 pkgs list <base> (pkgs test is retired: AGAST #3970)"
    git rev-parse -q --verify "$2^{commit}" >/dev/null || die "no such commit: $2"
    pkgs_list "$2"
}

# cmd_land [<log>]: land the train whose tip <log> passed, and every train
# below it (AGAST #4151, #4130).  Train k is built on train k-1's tail, so a
# green gate on train k's tip tested every car of trains 1..k on main: they
# land in one fast-forward push, and trains 1..k-1's gates, now redundant,
# are cancelled.  No log: train 1 alone, which must need no gate.
cmd_land() {
    local q log="${1:-}" lsha="" k=1 i st base base1="" tip prev
    mapfile -t q < <(queue)
    [[ ${#q[@]} -gt 0 ]] || die "no train built"
    if [[ -n "$log" ]]; then
        [[ -f "$log" ]] || die "no such gate log: $log"
        lsha="$(sed -n 's/^SHA=//p' "$log" | tail -1)"
        for i in "${!q[@]}"; do
            use_slot "${q[$i]}"
            if [[ -n "$lsha" && "$(field TIP "$(state)")" == "$lsha" ]]; then k=$((i + 1)); break; fi
        done
    fi
    # Trains 1..k must be as built, each on the tail of the one before.
    prev=""
    for ((i = 0; i < k; i++)); do
        use_slot "${q[$i]}"; st="$(state)"
        tip="$(field TIP "$st")"; base="$(field BASE "$st")"
        [[ "$tip" == "$(g rev-parse HEAD)" ]] || die "train $((i + 1))'s worktree moved since build; rebuild"
        [[ -z "$prev" || "$base" == "$prev" ]] \
            || die "train $((i + 1)) is not on train $i's tail (${base:0:12} != ${prev:0:12}); rebuild"
        [[ -n "$prev" ]] || base1="$base"
        prev="$tip"
    done
    [[ "$tip" != "$base1" ]] || die "train is empty; nothing to land"
    if [[ -n "$log" ]]; then
        [[ "$lsha" == "$tip" ]] \
            || die "gate log is for another commit (${lsha:0:12}), not a train tip (train 1's is $(use_slot "${q[0]}"; field TIP "$(state)" | cut -c1-12))"
        [[ "$(sed -n 's/^EXIT=//p' "$log" | tail -1)" == 0 ]] \
            || die "gate did not pass ($(grep '^EXIT=' "$log" | tail -1 || echo 'no verdict'))"
    else
        [[ "$(field GATE "$st")" != needed ]] || die "gate needed: pass the gate log"
    fi
    g fetch -q origin
    # Train 1's base is main; a stacked train's base is the tail below it.
    [[ "$(g rev-parse origin/main)" == "$base1" ]] \
        || die "main moved since the train was built (${base1:0:12} -> $(g rev-parse --short=12 origin/main)); rebuild and re-gate"
    # Not forced: GitHub refuses it if main moved in the meantime.
    g push -q origin "$tip:refs/heads/main"
    local landed_tip="$tip"   # the loop below reuses $tip per slot
    # Hold the gate slot for the next train's gate (run-gate.sh).  Best
    # effort: main has moved already, so a failure here only warns.
    { mkdir -p "$(dirname "$RESERVED")" && date +%s > "$RESERVED.tmp" \
        && mv -f "$RESERVED.tmp" "$RESERVED"; } 2>/dev/null \
        || echo "warning: could not reserve the gate slot ($RESERVED)" >&2
    # main has moved: from here on nothing may die before the queue says so
    # (AGAST #4337), so the main checkout's catch-up only warns.
    { git -C "$MAIN_WT" fetch -q origin && git -C "$MAIN_WT" merge -q --ff-only origin/main; } \
        || echo "warning: could not fast-forward $MAIN_WT to origin/main" >&2
    local b room merged spec
    for ((i = 0; i < k; i++)); do
        use_slot "${q[$i]}"
        while read -r b room merged; do
            echo "MERGED   $b ${room:0:12} as ${merged:0:12}"
        done < <(field ITEM "$(state)")
    done
    echo "MAIN     ${tip:0:12}"
    # Trains 1..k are off the queue first, in one rename (AGAST #4337).
    local rest=()
    for ((i = k; i < ${#q[@]}; i++)); do rest+=("${q[$i]}"); done
    write_queue ${rest[@]+"${rest[@]}"}
    # Trains 1..k-1 are landed: their gates can only repeat train k's verdict.
    # Stop each: a speculative one (SPEC, local or remote), else the train's
    # own local unit, and drop its .train-waiting so room gates see the slot
    # free at once (best effort).
    for ((i = 0; i < k; i++)); do
        use_slot "${q[$i]}"; st="$(state)"
        spec="$(field SPEC "$st")"
        if [[ $((i + 1)) -lt $k ]]; then
            if [[ -n "$spec" ]]; then discard_spec CANCELLED
            else stop_local "$(gname)" "covered by train $k's pass"; fi
        elif [[ -n "$spec" ]]; then
            # The landed train's speculative ref (AGAST #3988) has served its purpose.
            read -r _ spec _ <<<"$spec"
            if [[ "$spec" != - ]]; then
                g push -q origin --delete "refs/heads/$spec" 2>/dev/null \
                    || echo "warning: could not delete $spec on origin" >&2
            fi
        fi
        # Every train's tail ref (AGAST #4409) is covered by main now; a
        # local-gate or never-gated tail has no SPEC to delete it.  Best
        # effort: a missing ref (or one already deleted above) is fine.
        tip="$(field TIP "$st")"
        [[ -z "$tip" ]] \
            || g push -q origin --delete "refs/heads/rz-train/${tip:0:12}" 2>/dev/null || true
        rm -f "$st"
    done
    # A fix-forward or resolve ref held for a train that just landed has
    # served its purpose: it always reboards, so its SHA is now an ancestor
    # of main (AGAST #4753).  Best effort, after the queue is already clear.
    held_drop_landed "$(held_file)" "$landed_tip"
    held_drop_landed "$(held_resolve_file)" "$landed_tip"
    # Promote the next train: its base, train k's tail, is main now.
    if [[ ${#rest[@]} -gt 0 ]]; then
        use_slot "${rest[0]}"; st="$(state)"
        spec="$(field SPEC "$st")"
        echo "NEXT     base=$(field BASE "$st" | cut -c1-12) tip=$(field TIP "$st" | cut -c1-12)" \
            "n=$(field ITEM "$st" | wc -l) gate=$(field GATE "$st")${spec:+ spec=${spec##* }}"
    fi
}

# cmd_fail <log>: train k's gate failed (AGAST #4031).  Every train after it
# sits on its tail, so their gates test a tree that holds the culprit: stop
# them (DISCARDED lines) and restack their cars on train k-1's tail (main
# for k = 1), as `build` would.  Train k's own cars come out, one HELD line
# each: bisect them (SKILL.md step 6) with `build --next`, culprit-suspect
# first out.  Trains 1..k-1 and their gates stay as they are.
cmd_fail() {
    local log="${1:?usage: $0 fail <log>}" lsha q i k=0 items=() b room new s tip
    [[ -f "$log" ]] || die "no such gate log: $log"
    lsha="$(sed -n 's/^SHA=//p' "$log" | tail -1)"
    [[ "$(sed -n 's/^EXIT=//p' "$log" | tail -1)" != 0 ]] || die "that gate passed: land it"
    mapfile -t q < <(queue)
    for i in "${!q[@]}"; do
        use_slot "${q[$i]}"
        if [[ -n "$lsha" && "$(field TIP "$(state)")" == "$lsha" ]]; then k=$((i + 1)); break; fi
    done
    [[ $k -gt 0 ]] || die "gate log is for no train's tip (${lsha:0:12})"
    use_slot "${q[$((k - 1))]}"
    while read -r b room new; do echo "HELD     $b ${room:0:12}"; done < <(field ITEM "$(state)")
    # The tails a room may be based on and that are about to go: train k's and
    # every later train's.  A room spawned on one must move even when no newer
    # tail carries its cars (AGAST #4413): name each, so rz can bounce them
    # (`rebase-plan --dropped <tip> --onto <new>`).
    for ((i = k - 1; i < ${#q[@]}; i++)); do
        use_slot "${q[$i]}"
        tip="$(field TIP "$(state)")"
        [[ -z "$tip" ]] || echo "DROPPED  tail ${tip:0:12} — a room based on it must rebase"
    done
    for ((i = k; i < ${#q[@]}; i++)); do
        use_slot "${q[$i]}"
        while read -r b room new; do items+=("$b:$room"); done < <(field ITEM "$(state)")
    done
    if [[ ${#items[@]} -gt 0 ]]; then build_on "$((k - 1))" "${items[@]}"; return; fi
    # Nothing behind it: just drop train k (and nothing else), off the queue
    # first (AGAST #4337).
    write_queue "${q[@]:0:k-1}"
    for ((i = k - 1; i < ${#q[@]}; i++)); do
        use_slot "${q[$i]}"; discard_spec; unpublish_tail "${q[$i]}"; rm -f "$(state)"
    done
}

# cmd_pending: the dispatch rule (AGAST #4031, #4156; SKILL.md "Merge
# trains"), for the train to gate (pick_target: the deepest built train, or
# a prefix bisecting a red deeper gate), one line, or none:
#   GATE train <k> n=<cars> (<why>): <command>   gate it now
#   WAIT train <k> n=<cars> <s>s                 more cars may come
#   FAIL train <r> n=<cars> (...): train.sh fail <log>
#                                                red, nothing below it to
#                                                bisect: bisect its cars
# The deepest train gates at 8 cars, or once RZ_TRAIN_DEBOUNCE seconds pass
# after its last car boarded (its BUILT=, stamped by each build); a state
# with no BUILT= (built before #4031) gates now.  A train with another train
# GATING below it skips the debounce and buffers to 8 cars: it takes no
# second slot until it is full (Aaron, 2026-11-20), so the next train is
# gated as a whole rather than car by car.  A bisect prefix gates at once:
# no car boards it.  <command> is `train.sh gate --next` for every train,
# train 1 included (AGAST #4422: it prefers a remote free slot and falls
# back to a local gate, plain `gate` here); plain `gate` stays the local-
# only path.
cmd_pending() {
    local q st n built left now cmd
    mapfile -t q < <(queue)
    [[ ${#q[@]} -gt 0 ]] || return 0
    if ! pick_target; then
        if [[ $FAILK -gt 0 ]]; then
            use_slot "${q[$((FAILK - 1))]}"
            echo "FAIL train $FAILK n=$(field ITEM "$(state)" | wc -l) (red, nothing below to bisect): train.sh fail $(gate_log)"
        fi
        return 0
    fi
    use_slot "${q[$((TGT - 1))]}"; st="$(state)"
    now="$(date +%s)"
    n="$(field ITEM "$st" | wc -l)"; built="$(field BUILT "$st")"
    # A train stacked behind a gating one buffers to MAX before it spends a
    # second slot (Aaron, 2026-11-20).  Only the first train -- nothing
    # gating below it -- uses the debounce.
    local below=0 q2=() i
    mapfile -t q2 < <(queue)
    for ((i = 0; i < TGT - 1; i++)); do
        use_slot "${q2[$i]}"
        if [[ -n "$(field GATED "$(state)")" || -n "$(field SPEC "$(state)")" ]]; then below=1; break; fi
    done
    use_slot "${q[$((TGT - 1))]}"
    cmd="train.sh gate --next"
    if [[ $REASON != deepest ]]; then
        echo "GATE train $TGT n=$n ($REASON): $cmd"
    elif [[ $n -ge $MAX ]]; then
        echo "GATE train $TGT n=$n (full): $cmd"
    elif [[ $below -eq 1 ]]; then
        echo "WAIT train $TGT n=$n (buffer to $MAX: a train below is gating)"
    elif [[ ! "$built" =~ ^[0-9]+$ ]] || (( (left = built + DEBOUNCE - now) <= 0 )); then
        echo "GATE train $TGT n=$n (no new car for ${DEBOUNCE}s): $cmd"
    else
        echo "WAIT train $TGT n=$n ${left}s"
    fi
}

# cmd_precheck [<k>]: the guards and ratchets on train k's tip, before it
# spends a gate slot (AGAST #4672; SKILL.md Reaping step 3b).  <k> defaults
# to the train `pending` would gate (pick_target).  Each car's smoke ran the
# ratchets on its own base; this catches pins that each car had right alone
# but that disagree on the merged tree (two cars lowering one exact count,
# two edits to one allowlist), in ~15 s instead of a red ~30 min gate.
#
# Runs `make -C projects/ritz train-precheck` (RZ_PRECHECK_CMD overrides it,
# for tests): tools-ratchets plus suite-count, the ritz0 suite's test-count
# cap from a collect-only run (AGAST #4904: #4899 and #4885 each turned a
# train red on the count after a ~25 min gate; ~10-20 s, alongside the
# ratchets, so not in every smoke).  In train k's own worktree, never the shared checkout, as a
# waited-for unit in ritz-gate.slice at the gate's CPUWeight: the
# coordinator's turn waits on it, and it must not be starved by room work.
# The ratchets read tracked files only (#4672), so a reused train worktree
# gives the verdict a fresh checkout would.
#
# Prints `PRECHECK train <k> tip=<12> EXIT=<n>`, then on red only the
# failing lines (pytest's FAILED/ERROR, the count's cap line) and the full
# log's path; appends
# `PRECHECK=<tip> <exit>` to the train's state (the last line is current; a
# rebuild starts a new state).  Exits 0 on green, 1 on red.
cmd_precheck() {
    local q k="${1:-}" st tip cmd log rc unit
    mapfile -t q < <(queue)
    [[ ${#q[@]} -gt 0 ]] || die "no train built"
    if [[ -z "$k" ]]; then
        pick_target || die "$WHY"
        k=$TGT
    else
        [[ "$k" =~ ^[1-9][0-9]*$ && $k -le ${#q[@]} ]] || die "no train $k (${#q[@]} built)"
    fi
    use_slot "${q[$((k - 1))]}"
    st="$(state)"; tip="$(field TIP "$st")"
    [[ -n "$tip" && "$tip" == "$(g rev-parse HEAD)" ]] \
        || die "train $k's worktree moved since build; rebuild"
    cmd="${RZ_PRECHECK_CMD:-make -C projects/ritz train-precheck}"
    mkdir -p "$GATES"
    log="$GATES/precheck-$(gname)-${tip:0:12}.log"
    unit="ritz-precheck-$(gname)"
    rc=0
    systemd-run --user --quiet --wait --pipe --collect --unit="$unit" \
        --slice=ritz-gate.slice --property=CPUWeight=100 \
        --working-directory="$WT" \
        --setenv=PATH="$PATH" --setenv=HOME="$HOME" \
        -- bash -c "$cmd" > "$log" 2>&1 < /dev/null || rc=$?
    printf 'PRECHECK=%s %s\n' "$tip" "$rc" >> "$st"
    echo "PRECHECK train $k tip=${tip:0:12} EXIT=$rc"
    if [[ $rc -ne 0 ]]; then
        grep -E '^(FAILED|ERROR) |^  suite: .* over its cap|^suite count: collection failed' "$log" || true
        echo "log: $log"
        return 1
    fi
}

case "${1:-}" in
    build) shift; cmd_build "$@" ;;
    gate)  shift; cmd_gate "$@" ;;
    wait)  shift; cmd_wait "$@" ;;
    discard)
        for s in $(queue); do
            use_slot "$s"
            if [[ -z "${2:-}" || "$(field SPEC "$(state)" | cut -d' ' -f1)" == "$2" ]]; then discard_spec; fi
        done ;;
    fail)  shift; cmd_fail "$@" ;;
    pending) cmd_pending ;;
    precheck) shift; cmd_precheck "$@" ;;
    land)  shift; cmd_land "$@" ;;
    pkgs)  shift; cmd_pkgs "$@" ;;
    show)  cmd_show ;;
    tail)  cmd_tail ;;
    rebase-plan) shift; cmd_rebase_plan "$@" ;;
    hold-tail) shift; cmd_hold_tail "$@" ;;
    hold-resolve) shift; cmd_hold_resolve "$@" ;;
    prune-refs) shift; cmd_prune_refs "$@" ;;
    *) echo "usage: $0 build [--next] <branch>:<sha> ... | gate [<k> | --next [<host>]] | wait <log> | discard [<host>] | fail <log> | pending | precheck [<k>] | land [<log>] | show | tail | rebase-plan [<ref>] [--dropped <oldtip> [--onto <ref>]] | pkgs list <base> | hold-tail <sha> | hold-resolve <room> <sha> | prune-refs [--dry-run]" >&2; exit 2 ;;
esac
