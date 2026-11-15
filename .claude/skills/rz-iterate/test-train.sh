#!/usr/bin/env bash
# Tests for train.sh against a throwaway origin.  Run: bash test-train.sh
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
fails=0
ok()   { echo "ok   - $1"; }
bad()  { echo "FAIL - $1"; fails=$((fails + 1)); }
has()  { grep -qE "$2" <<<"$1" && ok "$3" || { bad "$3"; echo "$1" | sed 's/^/     | /'; }; }

export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
git init -q --bare -b main "$T/origin.git"
git clone -q "$T/origin.git" "$T/main" 2>/dev/null
M="$T/main"
for f in a b c d; do echo "$f" > "$M/$f"; done
git -C "$M" add . && git -C "$M" commit -qm init && git -C "$M" push -q origin HEAD:main

# room <name> <file> <content> [base]: one commit on its own branch, pushed.
room() {
    git -C "$M" checkout -q --detach "${4:-origin/main}"
    mkdir -p "$M/$(dirname "$2")"; echo "$3" > "$M/$2"
    git -C "$M" add -A; git -C "$M" commit -qm "$1: change $2"
    git -C "$M" push -q -f origin "HEAD:refs/heads/$1"
    git -C "$M" rev-parse HEAD
}

# Fake gate: writes a log the way run-gate.sh does, with RZ_FAKE_EXIT.
cat > "$T/gate.sh" <<'EOF'
#!/usr/bin/env bash
log="$RZ_TEST_DIR/gate-$(git -C "$1" rev-parse --short=12 HEAD).log"
printf 'SHA=%s\nEXIT=%s\nTRAIN=%s\nAFTER=%s\n' "$(git -C "$1" rev-parse HEAD)" "${RZ_FAKE_EXIT:-0}" "${RZ_GATE_TRAIN:-}" "${RZ_GATE_AFTER:-}" > "$log"
echo "$log"
EOF
chmod +x "$T/gate.sh"
export RZ_TEST_DIR="$T" RZ_MAIN_WT="$M" RZ_TRAIN_WT="$T/train" RZ_GATE_SCRIPT="$T/gate.sh"
TR="$HERE/train.sh"
fetch() { git -C "$M" fetch -q origin; }

# 1. One commit already on main: kept with its SHA, no gate, lands.
fetch; s1="$(room r1 a A1)"; git -C "$M" checkout -q main
out="$(bash "$TR" build "r1:$s1" 2>&1)"
has "$out" "^KEPT +r1 ${s1:0:12}" "fast-forward item is KEPT"
has "$out" "gate=not-needed" "a lone KEPT item needs no gate"
out="$(bash "$TR" land 2>&1)"
has "$out" "^MERGED +r1 ${s1:0:12} as ${s1:0:12}" "KEPT item lands with its own SHA"
[[ "$(git -C "$M" rev-parse origin/main)" == "$s1" ]] && ok "origin/main is r1" || bad "origin/main is r1"

# 2. Stale bases: two apply, one conflicts and is skipped; gate required.
base0="$(git -C "$M" rev-parse HEAD~1)"
s2="$(room r2 b B2 "$base0")"
s3="$(room r3 a CONFLICTS "$base0")"   # r1 changed a too
s4="$(room r4 c C4 "$base0")"
fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build "r2:$s2" "r3:$s3" "r4:$s4" 2>&1)"
has "$out" "^APPLIED +r2 ${s2:0:12} as " "stale item is cherry-picked"
has "$out" "^CONFLICT +r3 ${s3:0:12}" "conflicting item is skipped"
has "$out" "^APPLIED +r4 " "items after a conflict still apply"
has "$out" "n=2 gate=needed" "two picks need a gate"
[[ -z "$(git -C "$T/train" status --porcelain)" ]] && ok "no conflict left in worktree" || bad "no conflict left in worktree"
out="$(bash "$TR" land 2>&1)"; has "$out" "gate needed" "land refuses without a gate log"
log="$(RZ_FAKE_EXIT=1 bash "$TR" gate)"
out="$(bash "$TR" land "$log" 2>&1)"; has "$out" "did not pass" "land refuses a failed gate"
echo x > "$T/train/d"; git -C "$T/train" commit -qam stray
out="$(bash "$TR" land 2>&1)"; has "$out" "moved since build" "land refuses a moved worktree"
git -C "$T/train" reset -q --hard HEAD~1
log="$(bash "$TR" gate)"
out="$(bash "$TR" land "$log" 2>&1)"
has "$out" "^MERGED +r2 " "r2 merged"; has "$out" "^MERGED +r4 " "r4 merged"
[[ "$(git -C "$M" show origin/main:b)" == B2 && "$(git -C "$M" show origin/main:c)" == C4 ]] \
    && ok "main has both changes" || bad "main has both changes"
[[ "$(git -C "$M" rev-parse main)" == "$(git -C "$M" rev-parse origin/main)" ]] \
    && ok "main checkout fast-forwarded" || bad "main checkout fast-forwarded"
[[ "$(git -C "$M" log -1 --format=%s origin/main)" == "r4: change c" ]] \
    && ok "commit messages kept" || bad "commit messages kept"

# 3. Room mistakes: branch tip isn't the REAP SHA; two commits.
fetch; s5="$(room r5 d D5)"; room r5 d D5b >/dev/null
s6a="$(room r6 b B6)"; echo more >> "$M/b"; git -C "$M" commit -qam "r6: two"
git -C "$M" push -q -f origin HEAD:refs/heads/r6; s6="$(git -C "$M" rev-parse HEAD)"
fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build "r5:$s5" "r6:$s6" 2>&1)"
has "$out" "^BAD +r5 .*not this commit" "stale REAP SHA is BAD"
has "$out" "^BAD +r6 .*2 commits" "two commits is BAD"
has "$out" "n=0 gate=not-needed" "nothing applied"
out="$(bash "$TR" land 2>&1)"; has "$out" "empty" "empty train won't land"

# 4. Already on main: EMPTY.
out="$(bash "$TR" build "r2:$s2" 2>&1)"
has "$out" "^EMPTY +r2 " "already-merged patch is EMPTY"

# 5. main moves between build and land.
fetch; s7="$(room r7 d D7 origin/main~1)"; fetch; git -C "$M" checkout -q main
bash "$TR" build "r7:$s7" >/dev/null 2>&1; log="$(bash "$TR" gate)"
s8="$(room r8 c C8)"; git -C "$M" push -q origin "$s8:refs/heads/main"; git -C "$M" checkout -q main
out="$(bash "$TR" land "$log" 2>&1)"; has "$out" "main moved" "land refuses when main moved"
# The train's gate asks run-gate.sh for train priority (AGAST #3317).
has "$(cat "$log")" "^TRAIN=1$" "train.sh gate sets RZ_GATE_TRAIN=1"

# 6. Package tests (AGAST #3363): the train gate also tests the workspace
# packages the train touches, and a failure blocks only if the base passes.
# Fake packages; RZ_PKG_TEST stands in for `./rz test <dir>` and fails when
# the package has a FAIL file.
fetch; git -C "$M" checkout -q --detach origin/main
for d in projects/ritz projects/harland projects/harland/boot projects/ritzunit/inventory \
         projects/oldbad projects/lexis projects/ritz-lsp projects/prism; do
    mkdir -p "$M/$d"; echo "[package]" > "$M/$d/ritz.toml"
done
mkdir -p "$M/projects/prism/src"; echo x > "$M/projects/prism/src/main.ritz"
touch "$M/projects/oldbad/FAIL" "$M/projects/lexis/FAIL"
printf '%s\n' '[workspace.exclude]' '"projects/harland/boot" = "built by harland"' \
    '[ci.known_failing.build]' 'lexis = "AGAST #1 - fake"' > "$M/rz.toml"
git -C "$M" add -A; git -C "$M" commit -qm packages; git -C "$M" push -q origin HEAD:main
printf '%s\n' '#!/usr/bin/env bash' 'echo "testing $1 in $PWD"; [[ ! -e "$1/FAIL" ]]' > "$T/pkgtest.sh"
chmod +x "$T/pkgtest.sh"; export RZ_PKG_TEST="$T/pkgtest.sh"
PK="$TR"
# train <files...>: a fresh one-room train whose commit touches <files>, on a
# base one commit behind main (so it is APPLIED and needs a gate).  Sets $tb.
train() {
    fetch; git -C "$M" checkout -q --detach origin/main
    local f s
    for f in "$@"; do mkdir -p "$M/$(dirname "$f")"; echo "$RANDOM $f" >> "$M/$f"; done
    git -C "$M" add -A; git -C "$M" commit -qm "pk: change"
    git -C "$M" push -q -f origin HEAD:refs/heads/pk; s="$(git -C "$M" rev-parse HEAD)"
    git -C "$M" checkout -q --detach origin/main; echo "$RANDOM" > "$M/d"
    git -C "$M" commit -qam bump; git -C "$M" push -q origin HEAD:main; fetch
    tb="$(git -C "$M" rev-parse origin/main)"
    bash "$TR" build "pk:$s" >/dev/null 2>&1
}
pt() { (cd "$T/train" && bash "$PK" pkgs test "$tb" 2>&1); }

train projects/prism/src/main.ritz projects/ritz/x projects/harland/boot/y \
      projects/ritzunit/inventory/z projects/README projects/ritz-lsp/w
out="$(cd "$T/train" && bash "$PK" pkgs list "$tb" 2>&1)"
want="projects/harland projects/prism projects/ritz-lsp projects/ritzunit/inventory "
[[ "$(tr '\n' ' ' <<<"$out")" == "$want" ]] \
    && ok "list: each touched file's owning package, minus projects/ritz and excluded dirs" \
    || { bad "list: touched packages"; echo "$out" | sed 's/^/     | /'; }
log="$(bash "$TR" gate 2>/dev/null)"
has "$(cat "$log")" "^AFTER=.*train.sh.* pkgs test $tb" "a train touching packages adds their tests to its gate"
out="$(pt)"; rc=$?
[[ $rc -eq 0 ]] && ok "passing package tests pass (rc=$rc)" || bad "passing package tests pass (rc=$rc)"
has "$out" "^PKG PASS +prism" "each touched package is tested"
has "$out" "^PKG PASS +ritzunit/inventory" "a nested package is tested by its own dir"

train projects/ritz/only
log="$(bash "$TR" gate 2>/dev/null)"
has "$(cat "$log")" "^AFTER=$" "a train touching only projects/ritz adds nothing to its gate"

train projects/prism/FAIL
out="$(pt)"; rc=$?
[[ $rc -ne 0 ]] && ok "a new package failure fails (rc=$rc)" || bad "a new package failure fails (rc=$rc)"
has "$out" "^PKG FAIL +prism.*passes on base" "the new failure is named, against the base"
has "$out" "^--- prism \(base " "the base was tested too"
[[ "$(git -C "$T/train" worktree list | wc -l)" -eq 2 ]] && ok "the base worktree is removed" \
    || { bad "the base worktree is removed"; git -C "$T/train" worktree list; }

train projects/oldbad/src.ritz
out="$(pt)"; rc=$?
[[ $rc -eq 0 ]] && ok "a failure the base has too doesn't block (rc=$rc)" || bad "a failure the base has too doesn't block (rc=$rc)"
has "$out" "^PKG PRE-EXISTING +oldbad" "a pre-existing failure is reported"

train projects/lexis/src.ritz
out="$(pt)"; rc=$?
[[ $rc -eq 0 ]] && ok "a known-failing package is advisory (rc=$rc)" || bad "a known-failing package is advisory (rc=$rc)"
has "$out" "^PKG KNOWN +lexis" "a known-failing package is reported"

train projects/newpkg/ritz.toml projects/newpkg/FAIL
out="$(pt)"; rc=$?
[[ $rc -ne 0 ]] && ok "a new package that fails blocks (rc=$rc)" || bad "a new package that fails blocks (rc=$rc)"
has "$out" "^PKG FAIL +newpkg.*not on the base" "a new package's failure needs no base run"

echo; [[ $fails -eq 0 ]] && echo "all passed" || { echo "$fails failed"; exit 1; }
