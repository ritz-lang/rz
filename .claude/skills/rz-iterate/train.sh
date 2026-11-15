#!/usr/bin/env bash
#
# Merge train: land several REAPed commits on main with ONE gate (Aaron,
# 2026-11-12).  Every REAP is one squashed commit that its room already gated
# on its own base, so instead of each room rebasing and re-gating in turn,
# rz stacks them on origin/main in queue order and gates only the top.
#
#   train.sh build <branch>:<sha> ...   stack the commits on origin/main
#   train.sh gate                       gate the stack's tip (prints the log)
#   train.sh land [<log>]               push the gated tip to main
#   train.sh show                       print the current train
#   train.sh pkgs list|test <base>      the touched packages' tests (#3363;
#                                       the gate runs `test` after its jobs)
#
# `build` prints one line per item, then a summary:
#   APPLIED  <branch> <sha12> as <new12>   (cherry-picked; same patch)
#   KEPT     <branch> <sha12>              (already on the base: same SHA)
#   CONFLICT <branch> <sha12>              (left out; its room must rebase)
#   EMPTY    <branch> <sha12>              (left out; already on main)
#   BAD      <branch> <sha12>: <why>       (left out; a room mistake)
#   TRAIN base=<12> tip=<12> n=<applied> gate=<needed|not-needed>
#
# rz never resolves a conflict or edits a commit: a CONFLICT is aborted and
# skipped, and the room gets the turn once the train lands.
#
# Env overrides (for tests):
#   RZ_TRAIN_WT    train worktree      (default ~/dev/ritz-lang/rz-train)
#   RZ_MAIN_WT     main checkout       (default ~/dev/ritz-lang/rz)
#   RZ_TRAIN_NAME  gate name           (default train)
#   RZ_GATE_SCRIPT run-gate.sh to use  (default: beside this script)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
MAIN_WT="${RZ_MAIN_WT:-$HOME/dev/ritz-lang/rz}"
TRAIN_WT="${RZ_TRAIN_WT:-$HOME/dev/ritz-lang/rz-train}"
NAME="${RZ_TRAIN_NAME:-train}"
GATE="${RZ_GATE_SCRIPT:-$HERE/run-gate.sh}"

die() { echo "error: $*" >&2; exit 1; }
g() { git -C "$TRAIN_WT" "$@"; }
state() { echo "$(g rev-parse --absolute-git-dir)/RZ_TRAIN"; }

ensure_worktree() {
    if [[ ! -e "$TRAIN_WT/.git" ]]; then
        git -C "$MAIN_WT" fetch -q origin
        git -C "$MAIN_WT" worktree add -q --detach "$TRAIN_WT" origin/main
    fi
}

cmd_build() {
    [[ $# -ge 1 ]] || die "usage: $0 build <branch>:<sha> ..."
    ensure_worktree
    g fetch -q origin
    # A half-finished pick from an interrupted run must not leak in.
    g cherry-pick --abort >/dev/null 2>&1 || true
    g reset -q --hard
    local base; base="$(g rev-parse origin/main)"
    g checkout -q --detach "$base"
    local st; st="$(state)"
    printf 'BASE=%s\n' "$base" > "$st"

    local n=0 picked=0 item branch sha full parent count
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
        count="$(g rev-list --count "$(g merge-base origin/main "$full")..$full")"
        if [[ "$count" != 1 ]]; then
            echo "BAD      $branch ${full:0:12}: $count commits over main, want 1"; continue
        fi
        parent="$(g rev-parse "$full^")"
        if [[ $n -eq 0 && "$parent" == "$(g rev-parse HEAD)" ]]; then
            # Already on the base: keep its SHA, so its own gate still counts.
            g merge -q --ff-only "$full"
            echo "KEPT     $branch ${full:0:12}"
            printf 'ITEM=%s %s %s\n' "$branch" "$full" "$full" >> "$st"
            n=$((n + 1)); continue
        fi
        if ! g cherry-pick --empty=drop "$full" >/dev/null 2>&1; then
            g cherry-pick --abort >/dev/null 2>&1 || g reset -q --hard
            echo "CONFLICT $branch ${full:0:12}"; continue
        fi
        # --empty=drop succeeds without a commit when main already has it.
        if [[ "$(g rev-list --count "$base..HEAD")" -le $n ]]; then
            echo "EMPTY    $branch ${full:0:12}"; continue
        fi
        echo "APPLIED  $branch ${full:0:12} as $(g rev-parse --short=12 HEAD)"
        printf 'ITEM=%s %s %s\n' "$branch" "$full" "$(g rev-parse HEAD)" >> "$st"
        n=$((n + 1)); picked=$((picked + 1))
    done

    local need=needed
    # Nothing new to test: either nothing applied, or one commit kept as-is
    # (its room's gate ran on exactly this tree).
    [[ $picked -eq 0 ]] && need=not-needed
    printf 'TIP=%s\nGATE=%s\n' "$(g rev-parse HEAD)" "$need" >> "$st"
    echo "TRAIN base=${base:0:12} tip=$(g rev-parse --short=12 HEAD) n=$n gate=$need"
}

cmd_show() {
    local st; st="$(state)"
    [[ -f "$st" ]] || die "no train built"
    cat "$st"
}

cmd_gate() {
    local st; st="$(state)"
    [[ -f "$st" ]] || die "no train built"
    [[ "$(sed -n 's/^TIP=//p' "$st")" == "$(g rev-parse HEAD)" ]] \
        || die "train worktree moved since build; rebuild"
    # Package tests for what the train touches (AGAST #3363); none, and so no
    # extra step, for a compiler-only train.  stdout is only the log path.
    local base pkgs after=""
    base="$(sed -n 's/^BASE=//p' "$st")"
    pkgs="$(cd "$TRAIN_WT" && bash "$HERE/train.sh" pkgs list "$base")"
    if [[ -n "$pkgs" ]]; then
        echo "PKGS $(tr '\n' ' ' <<<"$pkgs")" >&2
        after="bash $(printf %q "$HERE/train.sh") pkgs test $base"
    fi
    # Train priority: the next free slot goes to this gate ahead of room
    # gates (run-gate.sh, AGAST #3317).
    RZ_GATE_TRAIN=1 RZ_GATE_AFTER="$after" "$GATE" "$TRAIN_WT" "$NAME"
}

# --- Package tests (AGAST #3363) ------------------------------------------
# The gate's build-all + bootstrap jobs cover the compiler, not the workspace
# projects' own tests: #3290's bug landed through a green train and only CI's
# test-all caught it.  So once those jobs pass, the train gate also runs
# `train.sh pkgs test <base>` from the train worktree (the tip is HEAD):
#
#   pkgs list <base>   the package dirs the train touches, one per line
#   pkgs test <base>   test each; exit 1 on a failure the base doesn't have
#
# A touched file belongs to the deepest directory above it with a ritz.toml,
# so a nested package (projects/ritzunit/inventory) is tested on its own.
# Skipped: projects/ritz and everything in it (build-all + bootstrap is its
# gate, so a compiler-only train costs exactly what it did), and rz.toml
# [workspace.exclude] dirs, which resolve to the package above them.
#
# One verdict line per package:
#   PKG PASS <id>
#   PKG KNOWN <id>: ...         fails, excused in [ci.known_failing.build] as
#                               `rz test --all` excuses it: advisory
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

pkgs_list() {
    local base="$1" f d excl
    mapfile -t excl < <(toml_keys 'c.get("workspace", {}).get("exclude", {})')
    git diff --name-only "$base" HEAD -- projects/ | while IFS= read -r f; do
        d="$(dirname "$f")"
        while [[ "$d" == projects/* ]]; do
            if [[ -f "$d/ritz.toml" ]] && ! in_list "$d" ${excl[@]+"${excl[@]}"}; then
                in_list "$d" projects/ritz || echo "$d"
                break
            fi
            d="$(dirname "$d")"
        done
    done | sort -u
}

pkgs_test() {
    local base="$1" test="${RZ_PKG_TEST:-./rz test}" p id rc brc rc_all=0 pkgs known
    mapfile -t pkgs < <(pkgs_list "$base")
    mapfile -t known < <(toml_keys 'c.get("ci", {}).get("known_failing", {}).get("build", {})')
    BASE_WT=""
    trap '[[ -z "$BASE_WT" ]] || { git worktree remove --force "$BASE_WT/tree" >/dev/null 2>&1; rm -rf "$BASE_WT"; git worktree prune; }' EXIT
    echo "=== Train package tests (AGAST #3363): ${#pkgs[@]} package(s) vs base ${base:0:12}"
    for p in ${pkgs[@]+"${pkgs[@]}"}; do
        id="${p#projects/}"
        echo "--- $id (train tip)"
        # The exit code comes straight from the command, never through a pipe.
        rc=0; $test "$p" || rc=$?
        if [[ $rc -eq 0 ]]; then echo "PKG PASS $id"; continue; fi
        # Exact id match: a nested package isn't excused by its parent's entry.
        if printf '%s\n' ${known[@]+"${known[@]}"} | grep -qxF -- "$id"; then
            echo "PKG KNOWN $id: exit $rc, excused in rz.toml [ci.known_failing.build] (advisory)"
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
    local st; st="$(state)"
    [[ -f "$st" ]] || die "no train built"
    local base tip need
    base="$(sed -n 's/^BASE=//p' "$st")"
    tip="$(sed -n 's/^TIP=//p' "$st")"
    need="$(sed -n 's/^GATE=//p' "$st")"
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
    [[ "$(g rev-parse origin/main)" == "$base" ]] \
        || die "main moved since the train was built (${base:0:12} -> $(g rev-parse --short=12 origin/main)); rebuild and re-gate"
    # Not forced: GitHub refuses it if main moved in the meantime.
    g push -q origin "$tip:refs/heads/main"
    git -C "$MAIN_WT" fetch -q origin
    git -C "$MAIN_WT" merge -q --ff-only origin/main
    local b room merged
    while read -r b room merged; do
        echo "MERGED   $b ${room:0:12} as ${merged:0:12}"
    done < <(sed -n 's/^ITEM=//p' "$st")
    echo "MAIN     ${tip:0:12}"
    rm -f "$st"
}

case "${1:-}" in
    build) shift; cmd_build "$@" ;;
    gate)  shift; cmd_gate ;;
    land)  shift; cmd_land "$@" ;;
    pkgs)  shift; cmd_pkgs "$@" ;;
    show)  cmd_show ;;
    *) echo "usage: $0 build <branch>:<sha> ... | gate | land [<log>] | show | pkgs list|test <base>" >&2; exit 2 ;;
esac
