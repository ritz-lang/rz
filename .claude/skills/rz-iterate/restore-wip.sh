#!/usr/bin/env bash
# restore-wip.sh — bring a re-spawned room's evacuated WIP back (AGAST #4287).
#
#   restore-wip.sh [--remote <remote>] [--ref <ref>] <room> <worktree>
#
# When a host is lost, adele's `room evacuate` (adele docs/host-evacuation.md)
# pushes each room's HEAD plus a snapshot of its uncommitted work to
# refs/wip/<host>/<room> (or refs/wip/<host>/<room>-<stamp> when that ref was
# taken). The snapshot is a commit authored `adele evacuate` whose parent is
# the room's HEAD. This script does the doc's restore inside the re-spawned
# room's existing worktree (already reset to its pushed ritz-task-<id> branch):
#
#   1. find the hand-off ref: --ref if given (the one the hand-off message
#      names), else the newest (committer date) refs/wip/<any host>/<room> or
#      <room>-<digit…> on the remote. +kept-/+branch/ refs are listed, never
#      applied (they may hold work deleted on purpose);
#   2. fetch it objects-only (no local ref, no FETCH_HEAD);
#   3. fast-forward the branch to the snapshot's HEAD (commits the old room
#      never pushed), then check the snapshot's files out and unstage them, so
#      the WIP is back as uncommitted changes, exactly as `reset HEAD~1` leaves it.
#
# It never clobbers: it refuses (exit 3, worktree untouched) when the worktree
# is dirty, when the branch has commits the snapshot's HEAD lacks, or when the
# hand-off has a side ref or a pre-rebase tip (follow the hand-off's own
# commands then). A run after a successful restore says "already restored".
# It never pushes or deletes a ref.
#
# Exit: 0 restored / already restored / NONE (no hand-off ref);
#       2 usage, not a worktree, remote unreachable, fetch failed;
#       3 refused, nothing changed.
set -uo pipefail

SNAPSHOT_AUTHOR='adele evacuate'
remote=origin pin=
usage() { echo "usage: restore-wip.sh [--remote <remote>] [--ref <ref>] <room> <worktree>" >&2; exit 2; }
while [[ $# -gt 0 ]]; do
    case "$1" in
        --remote) [[ $# -ge 2 ]] || usage; remote="$2"; shift 2 ;;
        --ref)    [[ $# -ge 2 ]] || usage; pin="$2"; shift 2 ;;
        -h|--help) usage ;;
        --*) usage ;;
        *) break ;;
    esac
done
[[ $# -eq 2 ]] || usage
room="$1" wt="$2"
die()    { echo "ERROR: $*" >&2; exit 2; }
refuse() { echo "REFUSED: $*" >&2; echo "nothing was changed in $wt" >&2; exit 3; }

[[ -d "$wt" ]] || die "$wt is not a directory"
top="$(git -C "$wt" rev-parse --show-toplevel 2>/dev/null)" || die "$wt is not a git worktree"
[[ "$(cd "$top" && pwd -P)" == "$(cd "$wt" && pwd -P)" ]] || die "$wt is not the top of a git worktree ($top is)"
g() { git -C "$wt" -c gc.auto=0 "$@"; }
marker="$(g rev-parse --git-path wip-restored)"
[[ "$marker" == /* ]] || marker="$wt/$marker"

# 1. The room's refs on the remote. A main ref's name is the room, or the room
#    plus a -<stamp> fallback (starts with a digit, so ritz-task-9 never takes
#    ritz-task-90 or ritz-task-9-foo). Anything else whose name starts with a
#    main ref's name plus '+' or '.orig-head' belongs to that ref.
listing="$(git -C "$wt" ls-remote "$remote" 'refs/wip/*' 2>/dev/null)" || die "git ls-remote $remote failed"
declare -A sha_of=()
mains=() extras=()
rx_room="$(printf '%s' "$room" | sed 's/[][\.*^$+?(){}|/]/\\&/g')"
while read -r sha ref; do
    [[ -n "$ref" ]] || continue
    sha_of["$ref"]="$sha"
    name="${ref#refs/wip/*/}"
    if [[ "$name" =~ ^${rx_room}(-[0-9][0-9A-Za-z.:-]*)?$ ]]; then
        mains+=("$ref")
    elif [[ "$name" =~ ^${rx_room}(-[0-9][0-9A-Za-z.:-]*)?(\+|\.orig-head) ]]; then
        extras+=("$ref")
    fi
done <<<"$listing"

if [[ -n "$pin" ]]; then
    [[ -n "${sha_of[$pin]:-}" ]] || die "$pin is not on $remote"
    mains=("$pin")
fi
if [[ ${#mains[@]} -eq 0 ]]; then
    echo "NONE: no refs/wip/<host>/$room hand-off on $remote; nothing to restore"
    exit 0
fi

# 2. Objects only: --refmap= and no destination write no ref and no FETCH_HEAD.
g fetch -q --no-write-fetch-head --refmap= "$remote" "${mains[@]}" 2>/dev/null \
    || die "git fetch $remote ${mains[*]} failed"
ref= tip= best=-1
for r in "${mains[@]}"; do
    ct="$(g log -1 --format=%ct "${sha_of[$r]}" 2>/dev/null)" || die "fetched ${sha_of[$r]} is not in this repo"
    if (( ct > best )) || { (( ct == best )) && [[ "$r" > "$ref" ]]; }; then
        best="$ct" ref="$r" tip="${sha_of[$r]}"
    fi
done
others=()
for r in "${mains[@]}"; do [[ "$r" == "$ref" ]] || others+=("$r ${sha_of[$r]:0:12}"); done
kept=() blockers=()
for r in "${extras[@]}"; do
    # Every +kept-/+branch/ ref of the room is listed, whichever ref it hangs off;
    # only the chosen ref's side ref or pre-rebase tip blocks the restore.
    case "$r" in
        *+kept-*|*+branch/*) kept+=("$r") ;;
        "$ref"+*|"$ref".orig-head) blockers+=("$r") ;;   # side ref (+<stamp>-<sha>), pre-rebase tip
    esac
done

if [[ -f "$marker" && "$(cat "$marker")" == "$ref $tip" ]]; then
    echo "already restored: $ref ${tip:0:12} (marker $marker); nothing to do"
    exit 0
fi
if [[ ${#blockers[@]} -gt 0 ]]; then
    refuse "$ref has a side ref or pre-rebase tip this script does not apply:
$(printf '  %s\n' "${blockers[@]}")
restore with the exact commands in the evacuate hand-off message in this room's history"
fi
[[ -z "$(g status --porcelain 2>/dev/null)" ]] \
    || refuse "$wt has uncommitted changes; a restore would mix them with the snapshot:
$(g status --short | head -20)"

# 3. A snapshot tip goes back to its parent (the old room's HEAD).
snapshot=0 base="$tip"
if [[ "$(g log -1 --format=%an "$tip")" == "$SNAPSHOT_AUTHOR" ]]; then
    snapshot=1 base="$(g rev-parse "$tip^")" || die "snapshot $tip has no parent"
fi
head="$(g rev-parse HEAD)"
branch="$(g symbolic-ref -q --short HEAD || echo '(detached)')"
if [[ "$head" != "$base" ]]; then
    g merge-base --is-ancestor "$head" "$base" \
        || refuse "$branch (${head:0:12}) has commits the evacuated HEAD ${base:0:12} lacks:
$(g log --oneline "$base..$head" | head -10)
the snapshot was taken on an older HEAD; restore it by hand (git cherry-pick --no-commit $tip) or ask rz"
    if [[ "$branch" == '(detached)' ]]; then
        g checkout -q "$base" || die "checkout $base failed"
    else
        g merge -q --ff-only "$base" || die "fast-forward of $branch to $base failed"
    fi
    echo "fast-forwarded $branch ${head:0:12} -> ${base:0:12} (commits the old room had not pushed):"
    g log --oneline "$head..$base" | head -10 | sed 's/^/  /'
fi
if [[ $snapshot -eq 1 ]]; then
    # Two-tree read-tree on a clean worktree: index and files become the
    # snapshot's; the mixed reset then unstages it all (new files untracked).
    g read-tree -u -m HEAD "$tip" || die "read-tree $tip failed"
    g reset -q || die "reset failed"
fi
printf '%s %s\n' "$ref" "$tip" > "$marker"

echo "RESTORED $ref ${tip:0:12} into $wt on $branch (HEAD ${base:0:12})"
if [[ $snapshot -eq 1 ]]; then
    echo "uncommitted work restored ($(g diff --shortstat "$base" "$tip" | sed 's/^ *//')):"
    g status --short -uall | sed 's/^/  /'
else
    echo "the ref holds a plain commit: no uncommitted work to restore"
fi
if [[ ${#others[@]} -gt 0 ]]; then
    echo "older hand-off refs, not applied:"; printf '  %s\n' "${others[@]}"
fi
if [[ ${#kept[@]} -gt 0 ]]; then
    echo "kept / branch refs, not applied (fetch one with: git fetch $remote +<ref>:<ref>):"
    printf '  %s\n' "${kept[@]}"
fi
exit 0
