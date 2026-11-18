#!/usr/bin/env bash
#
# Merge train: land several REAPed commits on main with ONE gate (Aaron,
# 2026-11-12).  Every REAP is one squashed commit that its room already gated
# on its own base, so instead of each room rebasing and re-gating in turn,
# rz stacks them on origin/main in queue order and gates only the top.
#
#   train.sh build <branch>:<sha> ...         stack the cars on origin/main,
#                                             replacing every train
#   train.sh build --next <branch>:<sha> ...  keep train 1 (the one gating) and
#                                             stack these cars on its tail as
#                                             train 2, replacing trains 2+
#                                             (keeps a train 2 gating on a
#                                             remote host too: then train 3)
#   train.sh gate                       gate train 1's tail (prints the log)
#   train.sh gate --next [<host>]       gate train 2's tail on <host> while
#                                       train 1 gates here (speculative; prints
#                                       the local log path it will fetch to)
#   train.sh wait <log>                 wait for a gate, local or remote, and
#                                       exit with its verdict (fetches a
#                                       remote log back first)
#   train.sh discard                    drop every speculative gate (a dead
#                                       host); the trains stay
#   train.sh land [<log>]               push train 1's tail to main; train 2
#                                       becomes train 1
#   train.sh show                       print every train, in landing order
#   train.sh pkgs list|test <base>      the touched packages' tests (#3363;
#                                       the gate runs `test` after its jobs)
#
# Stacked trains (AGAST #3809): a train holds at most 8 cars (RZ_TRAIN_MAX);
# car 9 onward start the next train on its tail.  Each train has its own
# worktree (train 1 first used $RZ_TRAIN_WT, the next free slot <wt>-2, ...)
# and state file, so building train 2 while train 1 gates leaves train 1's
# tree and state alone.  Trains gate and land in order: land takes train 1
# only, and train 2's base, train 1's tail, is then main.  The landing order
# is the slot list in <common git dir>/RZ_TRAINS.
#
# `build` prints one line per item, then a summary per train:
#   APPLIED  <branch> <sha12> as <new12>   (cherry-picked; same patch)
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
# rz never resolves a conflict or edits a commit: a CONFLICT is aborted and
# skipped, and the room gets the turn once the train lands.
#
# Env overrides (for tests):
#   RZ_TRAIN_WT    train 1's worktree  (default ~/dev/ritz-lang/rz-train)
#   RZ_TRAIN_MAX   cars per train      (default 8)
#   RZ_MAIN_WT     main checkout       (default ~/dev/ritz-lang/rz)
#   RZ_TRAIN_NAME  gate name           (default train)
#   RZ_GATE_SCRIPT run-gate.sh to use  (default: beside this script)
#   RZ_GATE_DIR    gate logs/slots     (default ~/dev/ritz-lang/gate-logs)
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
# on a remote host (omegalisk can't hold two gates):
#   1. push train 2's tail to origin refs/heads/rz-train/<tip12>;
#   2. ssh <host> (RZ_TRAIN_SSH) runs REMOTE_SH below, `start`: fetch that
#      ref into the host's clone, check out <tip> in its own worktree
#      (RZ_REMOTE_WT), and start that tree's run-gate.sh with
#      RZ_GATE_TRAIN=1 (train priority and reservation on that host, #3317,
#      #3427) and the package tests as RZ_GATE_AFTER; it prints the log path;
#   3. train 2's state gets `SPEC=<host> <ref> <remote log> <local log>`.
# `wait <local log>` runs the remote run-gate.sh --wait in slices, then
# copies the remote log to <local log> and checks its SHA is the train's tip,
# so `land` checks `SHA=<tip>` and `EXIT=0` exactly as for a local log.  At
# most 2 trains in flight: train 1 here, train 2 remote.  `build --next`
# keeps a train 2 that has a SPEC and stacks new cars on its tail as train
# 3.  Any build that replaces a train with a SPEC discards it (DISCARDED
# line): stops the remote gate, deletes the ref.  `land` deletes the landed
# train's ref.  A verdict can never outlive its tree: it names the tip, and
# a rebuilt train on another base has another tip.
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
SSH="${RZ_TRAIN_SSH:-ssh -F $HOME/.ssh/rz_hosts}"
REMOTE_HOST="${RZ_TRAIN_REMOTE:-huburght}"
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
WT="$TRAIN_WT"                      # the train being worked on (use_slot)
g() { git -C "$WT" "$@"; }
state() { echo "$(g rev-parse --absolute-git-dir)/RZ_TRAIN"; }
field() { sed -n "s/^$1=//p" "$2"; }

slot_wt() { if [[ $1 == 1 ]]; then echo "$TRAIN_WT"; else echo "$TRAIN_WT-$1"; fi; }
use_slot() { WT="$(slot_wt "$1")"; }
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

# --- Remote speculative gates (AGAST #3988) ---------------------------------
# REMOTE_SH runs on the gate host as `bash -l -s -- <verb> <args>`, read from
# stdin, so the host needs nothing of this branch but its run-gate.sh (the
# train tree's own).  Everything runs from main, called on the last line:
# bash has read the whole script by then, so no command can eat it off stdin.
#   start <repo> <wt> <gate|-> <ref> <tip> <base> <name> <pkgs 0|1>
#                                  fetch, check out, start the gate; prints
#                                  the remote log path.  The gate runs on the
#                                  host's venv (rz_venv_path: a login shell's
#                                  PATH has none, AGAST #4025), and start
#                                  refuses before it takes a slot if that
#                                  python3 can't import pytest
#   wait <wt> <gate|-> <log> <secs> <pause>
#                                  run-gate.sh --wait for at most <secs>
#                                  (124: still running).  A gate with no
#                                  EXIT yet whose unit is active or whose
#                                  waiter is queued for a slot is still
#                                  running, whatever code --wait ended with
#                                  (AGAST #4025); after an early end, sleep
#                                  <pause> first so a re-poll can't spin
#   cat <log>                      the log
#   stop <name>                    stop the gate's unit, if it runs
read -r -d '' REMOTE_SH <<'EOF' || true
set -euo pipefail
abs() { case "$1" in /*) echo "$1" ;; *) echo "$HOME/$1" ;; esac; }
gate_of() { if [ "$2" = - ]; then echo "$1/.claude/skills/rz-iterate/run-gate.sh"; else echo "$2"; fi; }
# alive <log>: the log's gate is still going: its unit (the log's UNIT=) is
# active, or its line in the gate dir's .gate-queue ("<unit> <pid> ...",
# run-gate.sh) names a live pid: queued for a slot.
alive() {
    local unit q u p rest
    unit="$(sed -n 's/^UNIT=//p' "$1" | head -1)"
    [ -n "$unit" ] || return 1
    systemctl --user is-active -q "$unit" 2>/dev/null && return 0
    q="$(dirname "$1")/.gate-queue"
    [ -f "$q" ] || return 1
    while read -r u p rest; do
        [ "$u" = "$unit" ] && kill -0 "$p" 2>/dev/null && return 0
    done < "$q"
    return 1
}
main() {
    # systemd-run --user needs the user bus; a non-login ssh may not set it.
    export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
    local verb="$1"; shift
    case "$verb" in
    start)
        local repo wt gate got after=""
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
        [ "$8" = 1 ] && after="bash $(printf %q "$wt/.claude/skills/rz-iterate/train.sh") pkgs test $6"
        RZ_GATE_TRAIN=1 RZ_GATE_BASE="$6" RZ_GATE_AFTER="$after" bash "$gate" "$wt" "$7" ;;
    wait)
        local rc=0 t0
        t0="$(date +%s)"
        timeout "$4" bash "$(gate_of "$(abs "$1")" "$2")" --wait "$3" >&2 || rc=$?
        if [ "$rc" != 124 ] && ! grep -q '^EXIT=' "$3" && alive "$3"; then
            echo "no verdict yet, gate still running or queued (--wait exit $rc)" >&2
            [ $(( $(date +%s) - t0 )) -ge "$5" ] || sleep "$5"
            rc=124
        fi
        exit "$rc" ;;
    cat) cat "$1" ;;
    stop) systemctl --user stop "ritz-gate-$1" 2>/dev/null || true ;;
    *) echo "error: unknown verb $verb" >&2; exit 2 ;;
    esac
}
main "$@" </dev/null
EOF

# remote <host> <verb> <args...>: REMOTE_SH on <host>.  sshd joins the
# arguments into one command line for the remote shell, hence %q.
remote() {
    local host="$1"; shift
    # shellcheck disable=SC2086  # $SSH is a command line
    $SSH "$host" "bash -l -s -- $(printf '%q ' "$@")" <<<"$(declare -f rz_venv_path)
$REMOTE_SH"
}

# discard_spec: drop the current train's speculative gate, if it has one.
discard_spec() {
    local st host ref rlog llog; st="$(state)"
    [[ -f "$st" ]] || return 0
    read -r host ref rlog llog <<<"$(field SPEC "$st")"
    [[ -n "$host" ]] || return 0
    remote "$host" stop "$NAME" >/dev/null 2>&1 || echo "warning: could not stop the gate on $host" >&2
    git -C "$MAIN_WT" push -q origin --delete "refs/heads/$ref" 2>/dev/null \
        || echo "warning: could not delete $ref on origin" >&2
    sed -i '/^SPEC=/d' "$st"
    echo "DISCARDED speculative gate on $host for ${ref#rz-train/} ($llog)"
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
    printf 'BASE=%s\n' "$2" > "$(state)"
    TBASE="$2"; n=0; picked=0; k=$((k + 1)); slots+=("$1")
}

# finish_train: the summary.  A later train nothing boarded is dropped.
finish_train() {
    local st need=needed; st="$(state)"
    # Nothing new to test: either nothing applied, or cars kept as-is (their
    # rooms' gates ran on exactly this tree).
    [[ $picked -eq 0 ]] && need=not-needed
    printf 'TIP=%s\nGATE=%s\n' "$(g rev-parse HEAD)" "$need" >> "$st"
    echo "TRAIN $k base=${TBASE:0:12} tip=$(g rev-parse --short=12 HEAD) n=$n gate=$need"
    if [[ $n -eq 0 && $k -gt 1 ]]; then
        rm -f "$st"; unset 'slots[-1]'; echo "         (empty: dropped)"
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

cmd_build() {
    local next=0
    if [[ "${1:-}" == --next ]]; then next=1; shift; fi
    [[ $# -ge 1 ]] || die "usage: $0 build [--next] <branch>:<sha> ..."
    git -C "$MAIN_WT" fetch -q origin
    local old=() s base
    mapfile -t old < <(queue)
    slots=(); k=0
    if [[ $next -eq 1 && ${#old[@]} -gt 0 ]]; then
        # Train 1 is gating: leave its worktree and state alone.
        use_slot "${old[0]}"
        base="$(field TIP "$(state)")"
        [[ "$base" == "$(g rev-parse HEAD)" ]] || die "train 1 moved since build; rebuild it"
        slots=("${old[0]}"); k=1; old=("${old[@]:1}")
        # Train 2 gating speculatively (AGAST #3988) is in flight too: keep
        # it, and stack these cars on its tail as train 3.
        if [[ ${#old[@]} -gt 0 ]]; then
            use_slot "${old[0]}"
            if [[ -f "$(state)" && -n "$(field SPEC "$(state)")" ]]; then
                base="$(field TIP "$(state)")"
                [[ "$base" == "$(g rev-parse HEAD)" ]] || die "train 2 moved since build; rebuild it"
                slots+=("${old[0]}"); k=2; old=("${old[@]:1}")
            fi
        fi
    else
        [[ $next -eq 0 ]] || echo "note: no train to stack on; building on origin/main" >&2
        base="$(git -C "$MAIN_WT" rev-parse origin/main)"
    fi
    for s in ${old[@]+"${old[@]}"}; do
        [[ -e "$(slot_wt "$s")/.git" ]] || continue
        use_slot "$s"; discard_spec
        rm -f "$(state)"
    done
    rm -f "$(qfile)"
    # The lowest slot not holding a kept train.
    free_slot() { local i=1; while printf '%s\n' ${slots[@]+"${slots[@]}"} | grep -qx "$i"; do i=$((i + 1)); done; echo "$i"; }
    start_train "$(free_slot)" "$base"
    local first_new=$k

    local item branch sha full parent count mb extra files
    for item in "$@"; do
        branch="${item%%:*}"; sha="${item#*:}"
        [[ "$branch" != "$item" && -n "$sha" ]] || die "bad item '$item' (want <branch>:<sha>)"
        if ! full="$(g rev-parse -q --verify "$sha^{commit}")"; then
            echo "BAD      $branch ${sha:0:12}: no such commit (fetched?)"; continue
        fi
        # The REAP must name the branch tip, as in the one-at-a-time checks.
        if [[ "$(g rev-parse -q --verify "origin/$branch" || true)" != "$full" ]]; then
            echo "BAD      $branch ${full:0:12}: origin/$branch is not this commit"; continue
        fi
        # One commit over main, or over train commits (a car bounced to
        # rebase onto a train's tail): every commit under it must be in the
        # trains so far, as an ancestor of the tail or as the same patch.
        mb="$(g merge-base origin/main "$full")"
        count="$(g rev-list --count "$mb..$full")"
        if [[ "$count" != 1 ]]; then
            extra="$(g cherry HEAD "$full^" "$mb" | grep -c '^+' || true)"
            if [[ "$extra" != 0 ]]; then
                echo "BAD      $branch ${full:0:12}: $count commits over main, $extra not in the train; want 1 over it"
                continue
            fi
        fi
        if [[ $n -ge $MAX ]]; then
            finish_train
            start_train "$(free_slot)" "$(g rev-parse HEAD)"
        fi
        parent="$(g rev-parse "$full^")"
        if [[ "$parent" == "$(g rev-parse HEAD)" ]]; then
            # On the tail already: keep its SHA, so its own gate still counts.
            g merge -q --ff-only "$full"
            echo "KEPT     $branch ${full:0:12}"
            printf 'ITEM=%s %s %s\n' "$branch" "$full" "$full" >> "$(state)"
            n=$((n + 1)); continue
        fi
        # The car's committer date: the same car on the same tail is the
        # same commit, however often the train is rebuilt.
        if ! GIT_COMMITTER_DATE="$(g log -1 --format=%cd --date=raw "$full")" \
                g cherry-pick --empty=drop "$full" >/dev/null 2>&1; then
            files="$(g diff --name-only --diff-filter=U)"
            g cherry-pick --abort >/dev/null 2>&1 || g reset -q --hard
            echo "CONFLICT $branch ${full:0:12} with $(conflict_with "$files") on $(paste -sd, <<<"$files")"
            continue
        fi
        # --empty=drop succeeds without a commit when main already has it.
        if [[ "$(g rev-list --count "$TBASE..HEAD")" -le $n ]]; then
            echo "EMPTY    $branch ${full:0:12}"; continue
        fi
        echo "APPLIED  $branch ${full:0:12} as $(g rev-parse --short=12 HEAD)"
        printf 'ITEM=%s %s %s\n' "$branch" "$full" "$(g rev-parse HEAD)" >> "$(state)"
        n=$((n + 1)); picked=$((picked + 1))
    done
    finish_train
    printf '%s\n' "${slots[@]}" > "$(qfile)"
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

cmd_gate() {
    if [[ "${1:-}" == --next ]]; then gate_next "${2:-$REMOTE_HOST}"; return; fi
    front
    local st spec; st="$(state)"
    [[ "$(field TIP "$st")" == "$(g rev-parse HEAD)" ]] \
        || die "train worktree moved since build; rebuild"
    spec="$(field SPEC "$st")"
    [[ -z "$spec" ]] || die "train 1 is already gating on ${spec%% *}: train.sh wait ${spec##* } (to gate it here instead, rebuild it: the same cars give the same tip)"
    # Package tests for what the train touches (AGAST #3363); none, and so no
    # extra step, for a compiler-only train.  stdout is only the log path.
    local base pkgs after=""
    base="$(field BASE "$st")"
    pkgs="$(cd "$WT" && bash "$HERE/train.sh" pkgs list "$base")"
    if [[ -n "$pkgs" ]]; then
        echo "PKGS $(tr '\n' ' ' <<<"$pkgs")" >&2
        after="bash $(printf %q "$HERE/train.sh") pkgs test $base"
    fi
    # Train priority: the next free slot goes to this gate ahead of room
    # gates (run-gate.sh, AGAST #3317).
    RZ_GATE_TRAIN=1 RZ_GATE_BASE="$base" RZ_GATE_AFTER="$after" "$GATE" "$WT" "$NAME"
}

# gate_next <host>: gate train 2 on <host> while train 1 gates here (AGAST
# #3988; see the header).  stdout is only the local log path.
gate_next() {
    local host="$1" q st tip base ref pkgs=0 rlog llog spec
    mapfile -t q < <(queue)
    [[ ${#q[@]} -gt 0 ]] || die "no train built"
    [[ ${#q[@]} -ge 2 ]] || die "no train 2 to gate: build --next first (train 1 gates with plain \`gate\`)"
    use_slot "${q[1]}"; st="$(state)"
    tip="$(field TIP "$st")"; base="$(field BASE "$st")"
    [[ "$tip" == "$(g rev-parse HEAD)" ]] || die "train 2's worktree moved since build; rebuild"
    [[ "$(field GATE "$st")" == needed ]] || die "train 2 needs no gate (gate=not-needed): land it after train 1"
    spec="$(field SPEC "$st")"
    [[ -z "$spec" ]] || die "train 2 is already gating on ${spec%% *} (at most 2 trains in flight): train.sh wait ${spec##* }"
    [[ -n "$(cd "$WT" && bash "$HERE/train.sh" pkgs list "$base")" ]] && pkgs=1
    ref="rz-train/${tip:0:12}"
    g push -q -f origin "$tip:refs/heads/$ref"
    if ! rlog="$(remote "$host" start "$REMOTE_REPO" "$REMOTE_WT" "$REMOTE_GATE" "$ref" "$tip" "$base" "$NAME" "$pkgs" | tail -1)" \
            || [[ "$rlog" != /*.log ]]; then
        g push -q origin --delete "refs/heads/$ref" 2>/dev/null || true
        die "the remote gate on $host did not start (got '$rlog'); gate train 2 here after train 1 lands"
    fi
    llog="$GATES/$(basename "${rlog%.log}")@$host.log"
    printf 'SPEC=%s %s %s %s\n' "$host" "$ref" "$rlog" "$llog" >> "$st"
    echo "SPEC train 2 tip=${tip:0:12} on $host: $rlog" >&2
    echo "$llog"
}

# cmd_wait <log>: block until the gate ends; exit with its code.  A remote
# gate's log is fetched to <log> once it ends; a log for another SHA than its
# train's tip exits 3.  Only an EXIT= line in that log ends a remote wait: a
# slice that times out (124) or ends with no EXIT= polls again, and 5 ends
# with no EXIT= in a row are no verdict (98), never exit 0 (AGAST #4116).
cmd_wait() {
    local log="${1:?usage: $0 wait <log>}" s st="" spec="" host ref rlog llog rc tries=0 nov=0 tip
    for s in $(queue); do
        use_slot "$s"
        spec="$(field SPEC "$(state)")"
        if [[ -n "$spec" && "${spec##* }" == "$log" ]]; then st="$(state)"; break; fi
        spec=""
    done
    if [[ -z "$spec" ]]; then
        [[ "$log" != *@*.log ]] || die "no train has a remote gate with log $log: discarded by a rebuild?"
        exec bash "$GATE" --wait "$log"
    fi
    read -r host ref rlog llog <<<"$spec"
    tip="$(field TIP "$st")"
    while :; do
        rc=0; remote "$host" wait "$REMOTE_WT" "$REMOTE_GATE" "$rlog" "$WAIT_SLICE" "$QUEUED_PAUSE" || rc=$?
        if [[ $rc -eq 124 ]]; then nov=0; continue; fi    # still running
        if [[ $rc -eq 255 ]]; then                        # ssh itself failed
            tries=$((tries + 1))
            [[ $tries -lt 5 ]] || die "ssh to $host failed 5 times: no verdict for $log"
            sleep "$SSH_RETRY"; continue
        fi
        remote "$host" cat "$rlog" > "$llog.tmp" || { rm -f "$llog.tmp"; die "could not fetch $rlog from $host"; }
        mv -f "$llog.tmp" "$llog"
        grep -q '^EXIT=' "$llog" && break
        # The slice ended but the log has no verdict (AGAST #4116): the gate
        # may still be running (alive() can miss its unit), so poll again;
        # only 5 such ends in a row are a dead gate, no verdict (98 below).
        nov=$((nov + 1))
        [[ $nov -lt 5 ]] || break
        echo "no EXIT= yet in $host:$rlog (wait exit $rc): polling again" >&2
        sleep "$QUEUED_PAUSE"
    done
    if [[ "$(sed -n 's/^SHA=//p' "$llog" | head -1)" != "$tip" ]]; then
        echo "REFUSED: $host's verdict is for $(sed -n 's/^SHA=//p' "$llog" | head -1 | cut -c1-12), not the train tip ${tip:0:12}" >&2
        exit 3
    fi
    rc="$(sed -n 's/^EXIT=//p' "$llog" | tail -1)"
    echo "gate $(basename "$llog") SHA=${tip:0:12} EXIT=${rc:-none}"
    [[ "$rc" =~ ^[0-9]+$ ]] || exit 98
    exit "$rc"
}

# --- Package tests (AGAST #3363) ------------------------------------------
# The gate's build-all + bootstrap jobs cover the compiler, not the workspace
# projects' own tests: #3290's bug landed through a green train and only CI's
# test-all caught it.  So once those jobs pass, the train gate also runs
# `train.sh pkgs test <base>` from the train worktree (the tip is HEAD).
# Since AGAST #3969 the gate runs main.yml's test-all job too, which tests
# every package before this step, so this step re-runs packages that already
# passed: a failure stops the gate at test-all, before the PRE-EXISTING base
# re-run below gets a chance to run.
#
#   pkgs list <base>   the package dirs the train touches, one per line
#   pkgs test <base>   test each; exit 1 on a failure the base doesn't have
#
# A touched file belongs to the deepest directory above it with a ritz.toml,
# so a nested package (projects/ritzunit/inventory) is tested on its own.
# Skipped: the projects/ritz package itself (build-all + bootstrap is its
# gate, so a compiler-only train costs exactly what it did), and rz.toml
# [workspace.exclude] dirs, which resolve to the package above them.  A
# package nested in projects/ritz (ritzlib/tests) is NOT skipped, and a
# ritzlib change selects ritzlib/tests (AGAST #3909, below).
# Except: a change to ritzunit or ritz0/test_runner.py tests every package
# `rz test --all` sweeps, projects/ritz's included (AGAST #3735, below).
#
# One verdict line per package:
#   PKG PASS <id>
#   PKG KNOWN <id>: ...         fails, excused by a `build` entry in
#                               known-failures/ as `rz test --all` excuses
#                               it: advisory
#   PKG PRE-EXISTING <id>: ...  fails on the base too: not this train's doing
#   PKG FAIL <id>: ...          fails here, passes on the base (or is new)
#
# Not the whole test-all: see SKILL.md "Merge trains" for the timing.
# Env: RZ_PKG_TEST, the command that tests one package dir (default ./rz test).

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

pkgs_test() {
    local base="$1" test="${RZ_PKG_TEST:-./rz test}" p id rc brc rc_all=0 pkgs known
    mapfile -t pkgs < <(pkgs_list "$base")
    # The excused ids, from the one known-failures parser (AGAST #1834).  A
    # malformed list exits 2 with nothing on stdout: no excuses (fail closed).
    mapfile -t known < <(python3 projects/ritz/tools/known_failures.py list \
        --gate build --compiler any | cut -f1)
    BASE_WT=""
    trap '[[ -z "$BASE_WT" ]] || { git worktree remove --force "$BASE_WT/tree" >/dev/null 2>&1; rm -rf "$BASE_WT"; git worktree prune; }' EXIT
    echo "=== Train package tests (AGAST #3363): ${#pkgs[@]} package(s) vs base ${base:0:12}"
    for p in ${pkgs[@]+"${pkgs[@]}"}; do
        id="${p#projects/}"; [[ "$p" == projects/* ]] || id="../$p"  # rz ids: ../bench/...
        echo "--- $id (train tip)"
        # The exit code comes straight from the command, never through a pipe.
        rc=0; $test "$p" || rc=$?
        if [[ $rc -eq 0 ]]; then echo "PKG PASS $id"; continue; fi
        # Exact id match: a nested package isn't excused by its parent's entry.
        if printf '%s\n' ${known[@]+"${known[@]}"} | grep -qxF -- "$id"; then
            echo "PKG KNOWN $id: exit $rc, excused in known-failures/ (gate = \"build\", advisory)"
            continue
        fi
        if ! git cat-file -e "$base:$p/ritz.toml" 2>/dev/null; then
            echo "PKG FAIL $id: exit $rc, and not on the base, so nothing to compare"
            rc_all=1; continue
        fi
        if [[ -z "$BASE_WT" ]]; then
            BASE_WT="$(mktemp -d)"
            git worktree add -q --detach "$BASE_WT/tree" "$base"
        fi
        echo "--- $id (base ${base:0:12})"
        brc=0; (cd "$BASE_WT/tree" && $test "$p") || brc=$?
        if [[ $brc -ne 0 ]]; then
            echo "PKG PRE-EXISTING $id: exit $rc, and exit $brc on base ${base:0:12} too (not this train's)"
        else
            echo "PKG FAIL $id: exit $rc, passes on base ${base:0:12}"
            rc_all=1
        fi
    done
    return $rc_all
}

cmd_pkgs() {
    [[ $# -eq 2 && ( "$1" == list || "$1" == test ) ]] || die "usage: $0 pkgs list|test <base>"
    git rev-parse -q --verify "$2^{commit}" >/dev/null || die "no such commit: $2"
    "pkgs_$1" "$2"
}

cmd_land() {
    front
    local st; st="$(state)"
    local base tip need
    base="$(field BASE "$st")"
    tip="$(field TIP "$st")"
    need="$(field GATE "$st")"
    [[ "$tip" == "$(g rev-parse HEAD)" ]] || die "train worktree moved since build; rebuild"
    [[ "$tip" != "$base" ]] || die "train is empty; nothing to land"
    if [[ "$need" == needed ]]; then
        local log="${1:-}"
        [[ -n "$log" && -f "$log" ]] || die "gate needed: pass the gate log"
        [[ "$(sed -n 's/^SHA=//p' "$log" | head -1)" == "$tip" ]] \
            || die "gate log is for another commit, not the train tip ${tip:0:12}"
        [[ "$(sed -n 's/^EXIT=//p' "$log" | tail -1)" == 0 ]] \
            || die "gate did not pass ($(grep '^EXIT=' "$log" | tail -1 || echo 'no verdict'))"
    fi
    g fetch -q origin
    # A stacked train's base is the tail of the train that landed before it.
    [[ "$(g rev-parse origin/main)" == "$base" ]] \
        || die "main moved since the train was built (${base:0:12} -> $(g rev-parse --short=12 origin/main)); rebuild and re-gate"
    # Not forced: GitHub refuses it if main moved in the meantime.
    g push -q origin "$tip:refs/heads/main"
    # Hold the gate slot for the next train's gate (run-gate.sh).  Best
    # effort: main has moved already, so a failure here only warns.
    { mkdir -p "$(dirname "$RESERVED")" && date +%s > "$RESERVED.tmp" \
        && mv -f "$RESERVED.tmp" "$RESERVED"; } 2>/dev/null \
        || echo "warning: could not reserve the gate slot ($RESERVED)" >&2
    git -C "$MAIN_WT" fetch -q origin
    git -C "$MAIN_WT" merge -q --ff-only origin/main
    local b room merged
    while read -r b room merged; do
        echo "MERGED   $b ${room:0:12} as ${merged:0:12}"
    done < <(field ITEM "$st")
    echo "MAIN     ${tip:0:12}"
    # Its speculative ref (AGAST #3988) has served its purpose.
    local spec; spec="$(field SPEC "$st")"
    if [[ -n "$spec" ]]; then
        read -r _ spec _ <<<"$spec"
        g push -q origin --delete "refs/heads/$spec" 2>/dev/null \
            || echo "warning: could not delete $spec on origin" >&2
    fi
    rm -f "$st"
    # Promote the next train: its base, this train's tail, is main now.
    local rest; rest="$(queue | tail -n +2)"
    if [[ -n "$rest" ]]; then
        printf '%s\n' "$rest" > "$(qfile)"
        use_slot "$(head -1 <<<"$rest")"; st="$(state)"
        spec="$(field SPEC "$st")"
        echo "NEXT     base=$(field BASE "$st" | cut -c1-12) tip=$(field TIP "$st" | cut -c1-12)" \
            "n=$(field ITEM "$st" | wc -l) gate=$(field GATE "$st")${spec:+ spec=${spec##* }}"
    else
        rm -f "$(qfile)"
    fi
}

case "${1:-}" in
    build) shift; cmd_build "$@" ;;
    gate)  shift; cmd_gate "$@" ;;
    wait)  shift; cmd_wait "$@" ;;
    discard) for s in $(queue); do use_slot "$s"; discard_spec; done ;;
    land)  shift; cmd_land "$@" ;;
    pkgs)  shift; cmd_pkgs "$@" ;;
    show)  cmd_show ;;
    *) echo "usage: $0 build [--next] <branch>:<sha> ... | gate [--next [<host>]] | wait <log> | discard | land [<log>] | show | pkgs list|test <base>" >&2; exit 2 ;;
esac
