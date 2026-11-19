#!/usr/bin/env bash
# Tests for restore-wip.sh against scratch repos: a bare "origin", a room that
# commits, pushes its branch, leaves uncommitted work and is "evacuated" (a
# snapshot commit authored `adele evacuate`, parent HEAD, pushed to
# refs/wip/<host>/<room> as adele's `room evacuate` does), then a fresh clone
# "re-spawned" on the pushed branch.  Run: bash test-restore-wip.sh
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
T="$(mktemp -d)"; trap 'chmod -R u+rwx "$T"; rm -rf "$T"' EXIT
fails=0
ok()  { echo "ok   - $1"; }
bad() { echo "FAIL - $1"; fails=$((fails + 1)); }
check() { if eval "$1"; then ok "$2"; else bad "$2"; fi; }
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
export GIT_CONFIG_NOSYSTEM=1 HOME="$T/home"; mkdir -p "$HOME"
H="$HERE/restore-wip.sh"
restore() { timeout 60 bash "$H" "$@"; }
ROOM=ritz-task-9 BR=ritz-task-9

# A room on the old host: origin, a clone with a pushed branch.
new_origin() {  # $1 = name; makes $T/$1.git and the old room $T/$1-old
    local o="$T/$1.git" w="$T/$1-old"
    git init -q --bare "$o"
    git clone -q "$o" "$w" 2>/dev/null
    git -C "$w" checkout -q -b "$BR"
    printf 'one\n' > "$w/keep.txt"; printf 'two\n' > "$w/edit.txt"; printf 'three\n' > "$w/gone.txt"
    git -C "$w" add -A; git -C "$w" commit -qm base
    git -C "$w" push -q origin "$BR" 2>/dev/null
}
# What adele's evacuate does: copy the index, add -A, commit-tree -p HEAD as
# `adele evacuate`, push to the ref.  The room's own index and HEAD are untouched.
evacuate() {  # $1 = worktree, $2 = ref, [$3 = committer date]
    local w="$1" ref="$2" idx tree head sha
    idx="$(mktemp)"; cp "$(git -C "$w" rev-parse --path-format=absolute --git-path index)" "$idx"
    GIT_INDEX_FILE="$idx" git -C "$w" add -A
    tree="$(GIT_INDEX_FILE="$idx" git -C "$w" write-tree)"; rm -f "$idx"
    head="$(git -C "$w" rev-parse HEAD)"
    if [[ "$tree" == "$(git -C "$w" rev-parse "HEAD^{tree}")" ]]; then
        sha="$head"
    else
        sha="$(GIT_AUTHOR_NAME='adele evacuate' GIT_AUTHOR_EMAIL=evacuate@adele \
               GIT_COMMITTER_DATE="${3:-$(date -R)}" \
               git -C "$w" commit-tree "$tree" -p "$head" -m "adele evacuate: WIP snapshot")"
    fi
    git -C "$w" push -q origin "$sha:$ref" 2>/dev/null
    echo "$sha"
}
# The re-spawned room: a fresh clone reset to the pushed branch.
respawn() {  # $1 = origin name, $2 = new worktree dir
    git clone -q "$T/$1.git" "$2" 2>/dev/null
    git -C "$2" checkout -q -B "$BR" "origin/$BR"
}
# The old room's uncommitted work.
dirty() {  # $1 = worktree
    printf 'two, edited\n' > "$1/edit.txt"
    git -C "$1" rm -q gone.txt
    printf 'brand new\n' > "$1/new.txt"
    mkdir -p "$1/sub"; printf 'staged\n' > "$1/sub/staged.txt"; git -C "$1" add sub/staged.txt
}
same_files() {  # $1 $2: worktrees with identical files (ignoring .git)
    diff -r -x .git "$1" "$2" >/dev/null
}

# 1. The basic re-spawn: WIP comes back as uncommitted changes on the same HEAD.
new_origin a; O="$T/a-old"; dirty "$O"
SNAP="$(evacuate "$O" "refs/wip/skronk/$ROOM")"
N="$T/a-new"; respawn a "$N"; BASE="$(git -C "$N" rev-parse HEAD)"
out="$(restore "$ROOM" "$N" 2>&1)"; rc=$?
check '[[ $rc -eq 0 ]]' "restore exits 0 (got $rc: $out)"
check 'same_files "$O" "$N"' "the re-spawned worktree's files match the old room's"
check '[[ "$(git -C "$N" rev-parse HEAD)" == "$BASE" ]]' "HEAD stays on the pushed branch tip (the snapshot is undone)"
check '[[ "$(git -C "$N" symbolic-ref --short HEAD)" == "$BR" ]]' "still on branch $BR"
check '[[ -z "$(git -C "$N" diff --cached --name-only)" ]]' "nothing is left staged (WIP comes back unstaged)"
check 'git -C "$N" status --short | grep -q "^ M edit.txt" && git -C "$N" status --short | grep -q "^ D gone.txt" && git -C "$N" status --short | grep -q "^?? new.txt"' "edit, deletion and new file show in git status"
check 'grep -q "refs/wip/skronk/$ROOM" <<<"$out" && grep -q "${SNAP:0:12}" <<<"$out"' "the report names the ref and the snapshot sha"
check 'grep -q "edit.txt" <<<"$out" && grep -q "new.txt" <<<"$out" && grep -q "gone.txt" <<<"$out"' "the report names the restored files"
check '[[ -z "$(git -C "$N" for-each-ref refs/wip refs/remotes/origin/wip)" ]]' "no local refs/wip ref is written"

# 2. Idempotent: a second run (the room restarted) changes nothing.
printf 'agent kept working\n' >> "$N/edit.txt"
out="$(restore "$ROOM" "$N" 2>&1)"; rc=$?
check '[[ $rc -eq 0 ]] && grep -qi "already restored" <<<"$out"' "a second run says already restored and exits 0 (got $rc)"
check 'grep -q "agent kept working" "$N/edit.txt"' "a second run leaves later edits alone"

# 3. A dirty worktree that wasn't restored is refused, untouched.
N3="$T/a-dirty"; respawn a "$N3"; printf 'local\n' > "$N3/local.txt"
out="$(restore "$ROOM" "$N3" 2>&1)"; rc=$?
check '[[ $rc -eq 3 ]]' "a dirty worktree is refused with exit 3 (got $rc)"
check '[[ -f "$N3/local.txt" && "$(cat "$N3/edit.txt")" == two ]]' "the refused worktree is untouched"

# 4. No hand-off ref: exit 0, says so, touches nothing.
new_origin b; N4="$T/b-new"; respawn b "$N4"
out="$(restore "$ROOM" "$N4" 2>&1)"; rc=$?
check '[[ $rc -eq 0 ]] && grep -q "^NONE" <<<"$out"' "no ref: exit 0 and a NONE line (got $rc: $out)"
check '[[ -z "$(git -C "$N4" status --porcelain)" ]]' "no ref: worktree untouched"

# 5. The newest hand-off wins across hosts and -<stamp> fallbacks; a room whose
#    name only starts with ours, and +kept-/+branch/ refs, are never chosen.
new_origin c; O5="$T/c-old"; dirty "$O5"
evacuate "$O5" "refs/wip/skronk/$ROOM" "Wed, 18 Nov 2026 06:00:00 +0000" >/dev/null
printf 'newest\n' > "$O5/edit.txt"
NEWEST="$(evacuate "$O5" "refs/wip/skronk-2/$ROOM-20261118T200000Z" "Wed, 18 Nov 2026 20:00:00 +0000")"
printf 'kept\n' > "$O5/edit.txt"
evacuate "$O5" "refs/wip/skronk-2/$ROOM+kept-20261118T210000Z-0123456789ab" "Wed, 18 Nov 2026 21:00:00 +0000" >/dev/null
printf 'other room\n' > "$O5/edit.txt"
evacuate "$O5" "refs/wip/skronk-3/${ROOM}0" "Wed, 18 Nov 2026 22:00:00 +0000" >/dev/null
evacuate "$O5" "refs/wip/skronk-3/${ROOM}-foo" "Wed, 18 Nov 2026 22:00:00 +0000" >/dev/null
printf 'newest\n' > "$O5/edit.txt"
N5="$T/c-new"; respawn c "$N5"
out="$(restore "$ROOM" "$N5" 2>&1)"; rc=$?
check '[[ $rc -eq 0 && "$(cat "$N5/edit.txt")" == newest ]]' "the newest hand-off ref is restored (got $rc: $(cat "$N5/edit.txt"))"
check 'grep -q "refs/wip/skronk-2/$ROOM-20261118T200000Z" <<<"$out" && grep -q "${NEWEST:0:12}" <<<"$out"' "the report names the newest ref"
check 'grep -q "+kept-" <<<"$out"' "kept refs are listed, not applied"

# 6. --ref pins the ref the hand-off message names.
N6="$T/c-pinned"; respawn c "$N6"
out="$(restore --ref "refs/wip/skronk/$ROOM" "$ROOM" "$N6" 2>&1)"; rc=$?
check '[[ $rc -eq 0 && "$(cat "$N6/edit.txt")" == "two, edited" ]]' "--ref restores that ref, not the newest (got $rc)"

# 7. Commits the old room never pushed come back too (fast-forward), then the WIP.
new_origin d; O7="$T/d-old"
printf 'unpushed\n' > "$O7/committed.txt"; git -C "$O7" add -A; git -C "$O7" commit -qm unpushed
UNPUSHED="$(git -C "$O7" rev-parse HEAD)"; dirty "$O7"
evacuate "$O7" "refs/wip/skronk/$ROOM" >/dev/null
N7="$T/d-new"; respawn d "$N7"
out="$(restore "$ROOM" "$N7" 2>&1)"; rc=$?
check '[[ $rc -eq 0 && "$(git -C "$N7" rev-parse HEAD)" == "$UNPUSHED" ]]' "an unpushed commit is fast-forwarded onto the branch (got $rc)"
check 'same_files "$O7" "$N7"' "and the WIP on top of it is restored"

# 8. The branch moved past the snapshot's HEAD: refused, untouched.
new_origin e; O8="$T/e-old"; dirty "$O8"
evacuate "$O8" "refs/wip/skronk/$ROOM" >/dev/null
W8="$T/e-other"; respawn e "$W8"; printf 'later\n' > "$W8/later.txt"
git -C "$W8" add -A; git -C "$W8" commit -qm later; git -C "$W8" push -q origin "$BR" 2>/dev/null
N8="$T/e-new"; respawn e "$N8"; H8="$(git -C "$N8" rev-parse HEAD)"
out="$(restore "$ROOM" "$N8" 2>&1)"; rc=$?
check '[[ $rc -eq 3 ]]' "a branch ahead of the snapshot's HEAD is refused with exit 3 (got $rc)"
check '[[ "$(git -C "$N8" rev-parse HEAD)" == "$H8" && -z "$(git -C "$N8" status --porcelain)" ]]' "the refused worktree is untouched"

# 9. A clean room's ref holds HEAD itself: fast-forward, nothing uncommitted.
new_origin f; O9="$T/f-old"
printf 'c\n' > "$O9/c.txt"; git -C "$O9" add -A; git -C "$O9" commit -qm clean
evacuate "$O9" "refs/wip/skronk/$ROOM" >/dev/null
N9="$T/f-new"; respawn f "$N9"
out="$(restore "$ROOM" "$N9" 2>&1)"; rc=$?
check '[[ $rc -eq 0 && "$(git -C "$N9" rev-parse HEAD)" == "$(git -C "$O9" rev-parse HEAD)" && -z "$(git -C "$N9" status --porcelain)" ]]' "a non-snapshot tip is fast-forwarded with nothing uncommitted (got $rc)"
check 'grep -qi "no uncommitted" <<<"$out"' "the report says there was no uncommitted work"

# 10. A side ref (HEAD pushed beside an earlier snapshot) needs the hand-off's
#     own commands: refused, untouched.
new_origin g; O10="$T/g-old"; dirty "$O10"
evacuate "$O10" "refs/wip/skronk/$ROOM" >/dev/null
git -C "$O10" push -q origin "HEAD:refs/wip/skronk/$ROOM+20261118T200000Z-0123456789ab" 2>/dev/null
N10="$T/g-new"; respawn g "$N10"
out="$(restore "$ROOM" "$N10" 2>&1)"; rc=$?
check '[[ $rc -eq 3 ]] && grep -q "+20261118T200000Z" <<<"$out"' "a side ref is refused with exit 3 and named (got $rc)"
check '[[ -z "$(git -C "$N10" status --porcelain)" ]]' "the refused worktree is untouched"

# 11. Usage errors.
restore "$ROOM" >/dev/null 2>&1; rc=$?
check '[[ $rc -eq 2 ]]' "missing worktree argument exits 2 (got $rc)"
restore "$ROOM" "$T/nope" >/dev/null 2>&1; rc=$?
check '[[ $rc -eq 2 ]]' "a worktree that isn't a git worktree exits 2 (got $rc)"

echo
if [[ $fails -eq 0 ]]; then echo "all restore-wip tests passed"; exit 0; fi
echo "$fails restore-wip test(s) FAILED"; exit 1
