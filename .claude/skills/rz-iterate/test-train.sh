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
# Never the real gate-logs: `land` reserves the slot there (AGAST #3365).
export RZ_GATE_DIR="$T/gates" RZ_HOST_ENV="$T/no-host.env" RZ_GATE_SLOTS=1
RES="$RZ_GATE_DIR/.train-reserved"
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

# 6. The slot is reserved between `land` and the next `gate` (AGAST #3365).
# Real run-gate.sh from here on, with systemd-run/systemctl stubbed as in
# test-run-gate.sh: the stub runs the unit in the foreground and marks it
# active in $RZ_TEST_ACTIVE while it runs.
mkdir -p "$T/bin" "$T/active" "$RZ_GATE_DIR"
export RZ_TEST_ACTIVE="$T/active" PATH="$T/bin:$PATH"
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
RG="$HERE/run-gate.sh"
until_() { local i; for i in $(seq 1 100); do eval "$1" && return 0; sleep 0.1; done; return 1; }
logof() { ls "$RZ_GATE_DIR"/"$1"-*.log 2>/dev/null | head -1; }
ORDER="$T/order"
rec='echo $RZ_TEST_NAME >> "$RZ_TEST_ORDER"'
export RZ_TEST_ORDER="$ORDER" RZ_GATE_POLL=0.1
R="$T/room"; git clone -q "$T/origin.git" "$R" 2>/dev/null

# 6a. A successful land reserves the slot, stamped with the time.
fetch; s9="$(room r9 d D9)"; git -C "$M" checkout -q main
rm -f "$RES"; bash "$TR" build "r9:$s9" >/dev/null 2>&1
before="$(date +%s)"; out="$(bash "$TR" land 2>&1)"
has "$out" "^MAIN " "r9 lands"
t="$(cat "$RES" 2>/dev/null)"
[[ "$t" =~ ^[0-9]+$ ]] && (( t >= before && t <= $(date +%s) )) \
    && ok "land writes .train-reserved with the time" || bad "land writes .train-reserved with the time (got '$t')"
# A refused land reserves nothing.
rm -f "$RES"; out="$(bash "$TR" land 2>&1)"
[[ ! -e "$RES" ]] && ok "a refused land reserves nothing" || bad "a refused land reserves nothing"

# 6b. A room gate started after land waits; the train's gate takes the slot
# first, and the reservation is gone once the train's gate has started.
fetch; s10="$(room r10 a A10)"; s11="$(room r11 b B11 origin/main)"
fetch; git -C "$M" checkout -q main
date +%s > "$RES"; : > "$ORDER"
RZ_TEST_NAME=R RZ_GATE_CMD="$rec" timeout 30 bash "$RG" "$R" rroom >/dev/null &
until_ '[[ -n "$(logof rroom)" ]] && grep -q "^WAITING" "$(logof rroom)"'
sleep 1
! grep -q "^SLOT=" "$(logof rroom)" && ok "a room gate waits on a fresh reservation" \
    || bad "a room gate waits on a fresh reservation"
grep -q "reserved for the merge train" "$(logof rroom)" && ok "the room gate's log says why it waits" \
    || bad "the room gate's log says why it waits"
bash "$TR" build "r10:$s10" "r11:$s11" >/dev/null 2>&1
gstart="$(date +%s)"
log="$(RZ_GATE_SCRIPT="$RG" RZ_TEST_NAME=T RZ_GATE_CMD="$rec; ls -A \"\$RZ_DIR\" > \"\$RZ_TEST_ORDER.during-t\"" \
    timeout 30 bash "$TR" gate)"
# The train's gate reserves the slot again as it ends (AGAST #3427): the room
# gate keeps waiting through the gap before `land`.
sleep 0.5
t="$(cat "$RES" 2>/dev/null)"
[[ "$t" =~ ^[0-9]+$ ]] && (( t >= gstart )) && ! grep -q "^SLOT=" "$(logof rroom)" \
    && ok "the train's gate re-reserves the slot as it ends; the room gate still waits" \
    || bad "the train's gate re-reserves the slot as it ends; the room gate still waits (got '$t')"
rm -f "$RES"   # as the next train's gate would
wait
[[ "$(tr '\n' ' ' < "$ORDER")" == "T R " ]] && ok "the train's gate goes before the waiting room gate" \
    || bad "the train's gate goes before the waiting room gate (order: $(tr '\n' ' ' < "$ORDER"))"
grep -qx EXIT=0 "$log" && grep -qx EXIT=0 "$(logof rroom)" && ok "both gates reach a verdict" \
    || bad "both gates reach a verdict"
! grep -qx .train-reserved "$ORDER.during-t" && ok "the train's gate clears the reservation" \
    || bad "the train's gate clears the reservation"

# 6c. Fail open: a reservation expires (RZ_GATE_TRAIN_HOLD), and a stale,
# future-dated or garbled one is ignored.
date +%s > "$RES"; : > "$ORDER"
start=$SECONDS
RZ_GATE_TRAIN_HOLD=2 RZ_TEST_NAME=E RZ_GATE_CMD="$rec" timeout 15 bash "$RG" "$R" rexp >/dev/null; rc=$?
[[ $rc -eq 0 ]] && grep -qx EXIT=0 "$(logof rexp)" && (( SECONDS - start >= 1 )) \
    && ok "a room gate takes the slot once the reservation expires" \
    || bad "a room gate takes the slot once the reservation expires (rc=$rc, $((SECONDS - start))s)"
i=0
for v in "$(( $(date +%s) - 601 ))" "$(( $(date +%s) + 3600 ))" garbage ""; do
    echo "$v" > "$RES"; i=$((i + 1)); n="rs$i"
    RZ_GATE_CMD=true timeout 5 bash "$RG" "$R" "$n" >/dev/null; rc=$?
    [[ $rc -eq 0 ]] && grep -qx EXIT=0 "$(logof "$n")" && ok "a reservation of '$v' doesn't block a room gate" \
        || bad "a reservation of '$v' doesn't block a room gate (rc=$rc)"
done

# 6d. A train that needs no gate drops the reservation: no train gate is coming.
date +%s > "$RES"
fetch; s12="$(room r12 c C12)"; git -C "$M" checkout -q main
out="$(bash "$TR" build "r12:$s12" 2>&1)"
has "$out" "gate=not-needed" "a lone KEPT train needs no gate"
[[ ! -e "$RES" ]] && ok "building a gate=not-needed train drops the reservation" \
    || bad "building a gate=not-needed train drops the reservation"

# 7. Package tests (AGAST #3363): the train gate also tests the workspace
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
printf '%s\n' '[workspace.exclude]' '"projects/harland/boot" = "built by harland"' > "$M/rz.toml"
# lexis is excused the real way: the real parser, a fake ticket (AGAST #1834).
mkdir -p "$M/projects/ritz/tools" "$M/known-failures"
cp "$HERE/../../../projects/ritz/tools/known_failures.py" "$M/projects/ritz/tools/"
printf '%s\n' '[[entry]]' 'gate = "build"' 'compiler = "any"' 'unit = "lexis"' \
    'reason = "fake"' 'agast = 1' > "$M/known-failures/1.toml"
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
# No ritzlib/tests package (yet): a ritzlib change has nothing to select.
train projects/ritz/ritzlib/net.ritz
out="$(cd "$T/train" && bash "$PK" pkgs list "$tb" 2>&1)"
[[ -z "$out" ]] && ok "list: a ritzlib change selects no ritzlib/tests that doesn't exist" \
    || { bad "list: a ritzlib change selects no ritzlib/tests that doesn't exist"; echo "$out" | sed 's/^/     | /'; }

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


# 8. A ritzunit or test-runner change selects every package (AGAST #3735).
# ritzunit is linked into every test binary (ritz0/test_runner.py), so #2072,
# a ritzunit-only change, broke ritzlib/tests and zeus while its gate tested
# only ritzunit.  Such a train tests what `rz test --all` sweeps: [workspace]
# members minus [workspace.exclude], projects/ritz included.
fetch; git -C "$M" checkout -q --detach origin/main
for d in projects/ritzunit projects/ritz/ritzlib/tests projects/ritz/examples/ex1 bench/b1; do
    mkdir -p "$M/$d"; echo "[package]" > "$M/$d/ritz.toml"
done
printf '%s\n' '[workspace]' 'members = ["projects/**", "bench/*"]' '[workspace.exclude]' \
    '"projects/harland/boot" = "built by harland"' '"projects/ritz/examples" = "regression.sh"' \
    > "$M/rz.toml"
git -C "$M" add -A; git -C "$M" commit -qm "workspace members"; git -C "$M" push -q origin HEAD:main
all="bench/b1 projects/harland projects/lexis projects/oldbad projects/prism projects/ritz projects/ritz-lsp projects/ritz/ritzlib/tests projects/ritzunit projects/ritzunit/inventory "
for f in projects/ritzunit/src/runner.ritz projects/ritz/ritz0/test_runner.py; do
    train "$f"
    out="$(cd "$T/train" && bash "$PK" pkgs list "$tb" 2>&1)"
    [[ "$(tr '\n' ' ' <<<"$out")" == "$all" ]] \
        && ok "list: a $f change selects every package rz test --all sweeps" \
        || { bad "list: a $f change selects every package"; echo "$out" | sed 's/^/     | /'; }
done
out="$(pt)"
has "$out" "^PKG PASS +ritz/ritzlib/tests" "an all-packages train tests a package inside projects/ritz"
has "$out" "^PKG PRE-EXISTING +oldbad" "an all-packages train still compares failures against the base"
train projects/ritzunit/inventory/src.ritz
out="$(cd "$T/train" && bash "$PK" pkgs list "$tb" 2>&1)"
[[ "$(tr '\n' ' ' <<<"$out")" == "projects/ritzunit/inventory " ]] \
    && ok "list: a nested package under ritzunit is only itself" \
    || { bad "list: a nested package under ritzunit is only itself"; echo "$out" | sed 's/^/     | /'; }

# 9. Nested packages under projects/ritz (AGAST #3909).  The compiler package
# projects/ritz is left to build-all + bootstrap, but ci-local runs no package
# nested in it: #3880 broke ritzlib/tests and its train (ritzlib only) listed
# nothing under projects/ritz.  A ritzlib change selects ritzlib/tests; any
# other non-excluded package under projects/ritz is tested as its own.
# lsr <files...>: pkgs list for a one-room train touching <files>, one line.
lsr() { train "$@"; (cd "$T/train" && bash "$PK" pkgs list "$tb" 2>&1) | tr '\n' ' '; }
eq() { [[ "$1" == "$2" ]] && ok "$3" || { bad "$3"; echo "     | got '$1', want '$2'"; }; }
fetch; git -C "$M" checkout -q --detach origin/main
mkdir -p "$M/projects/ritz/tools/nested"; echo "[package]" > "$M/projects/ritz/tools/nested/ritz.toml"
git -C "$M" add -A; git -C "$M" commit -qm "nested ritz package"; git -C "$M" push -q origin HEAD:main
eq "$(lsr projects/ritz/ritzlib/net.ritz)" "projects/ritz/ritzlib/tests " \
    "list: a ritzlib source change selects ritzlib/tests"
eq "$(lsr projects/ritz/ritzlib/sub/deep.ritz)" "projects/ritz/ritzlib/tests " \
    "list: a change deeper in ritzlib selects ritzlib/tests"
eq "$(lsr projects/ritz/ritzlib/tests/test_net_api.ritz)" "projects/ritz/ritzlib/tests " \
    "list: a ritzlib/tests change selects ritzlib/tests"
eq "$(lsr projects/ritz/ritz0/codegen.py)" "" "list: a ritz0-only change still lists nothing"
eq "$(lsr projects/ritz/ritzlibx/y.ritz)" "" "list: a sibling dir named like ritzlib isn't ritzlib"
eq "$(lsr projects/ritz/examples/ex1/src.ritz)" "" \
    "list: an excluded dir under projects/ritz still lists nothing"
eq "$(lsr projects/ritz/tools/nested/src.ritz)" "projects/ritz/tools/nested " \
    "list: any other nested package under projects/ritz is tested as its own"
train projects/ritz/ritzlib/net.ritz
log="$(bash "$TR" gate 2>/dev/null)"
has "$(cat "$log")" "^AFTER=.*train.sh.* pkgs test $tb" "a ritzlib-only train adds the package tests to its gate"
has "$(pt)" "^PKG PASS +ritz/ritzlib/tests" "a ritzlib-only train tests ritzlib/tests"

# 10. Stacked trains (AGAST #3809).  A train holds at most 8 cars; the next
# train builds on its tail (`build --next`, or overflow) and lands after it.
st1() { cat "$(git -C "$T/train" rev-parse --absolute-git-dir)/RZ_TRAIN"; }
tipof() { sed -nE "s/^TRAIN $1 .*tip=([0-9a-f]{12}).*/\1/p" <<<"$2"; }
fetch; git -C "$M" checkout -q main; git -C "$M" merge -q --ff-only origin/main

# 10a. Train 2 builds on train 1's tail while train 1 gates, and leaves train
# 1's worktree and state alone; land takes 1, promotes 2, then lands 2.
b9="$(git -C "$M" rev-parse origin/main)"
a1="$(room sa1 s/a1 A1)"; a2="$(room sa2 s/a2 A2)"; fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build "sa1:$a1" "sa2:$a2" 2>&1)"
has "$out" "^TRAIN 1 base=${b9:0:12} .*n=2 gate=needed" "train 1 builds on main"
t1="$(git -C "$T/train" rev-parse HEAD)"; s1="$(st1)"
log1="$(bash "$TR" gate)"
c1="$(room sb1 s/b1 B1)"; c2="$(room sb2 s/b2 B2)"; fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build --next "sb1:$c1" "sb2:$c2" 2>&1)"
has "$out" "^TRAIN 2 base=${t1:0:12} .*n=2 gate=needed" "build --next stacks train 2 on train 1's tail"
t2="$(tipof 2 "$out")"
[[ "$(git -C "$T/train" rev-parse HEAD)" == "$t1" && "$(st1)" == "$s1" ]] \
    && ok "build --next leaves train 1's worktree and state untouched" \
    || bad "build --next leaves train 1's worktree and state untouched"
out="$(bash "$TR" show 2>&1)"
has "$out" "^== train 2 " "show lists the stacked train"
out="$(bash "$TR" land "$log1" 2>&1)"
has "$out" "^MERGED +sa2 " "land takes train 1"
! grep -q "^MERGED +sb1" <<<"$out" && ok "land leaves train 2 for its own gate" || bad "land leaves train 2 for its own gate"
has "$out" "^NEXT +base=${t1:0:12} tip=$t2 n=2 gate=needed" "land promotes train 2, its base now main"
[[ "$(git -C "$M" rev-parse origin/main)" == "$t1" ]] && ok "main is train 1's tail" || bad "main is train 1's tail"
out="$(bash "$TR" land 2>&1)"; has "$out" "gate needed" "the promoted train still needs its gate"
log2="$(bash "$TR" gate)"
[[ "$(sed -n 's/^SHA=//p' "$log2")" == "$t2"* ]] && ok "gate gates the promoted train's tip" \
    || bad "gate gates the promoted train's tip"
out="$(bash "$TR" land "$log2" 2>&1)"
has "$out" "^MERGED +sb2 " "train 2 lands after train 1"
[[ "$(git -C "$M" rev-parse --short=12 origin/main)" == "$t2" ]] && ok "main is train 2's tail" || bad "main is train 2's tail"
out="$(bash "$TR" land 2>&1)"; has "$out" "no train built" "nothing left to land"

# 10b. 10 cars: trains of 8 and 2, the second on the first's tail.
fetch; git -C "$M" checkout -q main; b10="$(git -C "$M" rev-parse origin/main)"
items=(); for i in 0 1 2 3 4 5 6 7 8 9; do items+=("sc$i:$(room "sc$i" "s/c$i" "C$i")"); done
fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build "${items[@]}" 2>&1)"
has "$out" "^TRAIN 1 base=${b10:0:12} .*n=8 gate=needed" "the first 8 cars form train 1"
tt1="$(tipof 1 "$out")"
has "$out" "^TRAIN 2 base=$tt1 .*n=2 gate=needed" "cars 9-10 form train 2 on train 1's tail"
[[ "$(git -C "$M" rev-list --count "$b10..$tt1")" == 8 ]] && ok "train 1 holds 8 commits" || bad "train 1 holds 8 commits"
out="$(bash "$TR" land "$(bash "$TR" gate)" 2>&1)"
[[ "$(grep -c '^MERGED' <<<"$out")" == 8 ]] && ok "landing train 1 merges 8 cars" || bad "landing train 1 merges 8 cars"
out="$(bash "$TR" land "$(bash "$TR" gate)" 2>&1)"
has "$out" "^MERGED +sc9 " "train 2 lands its cars"

# 10c. A car rebased onto an unlanded train commit boards, not BAD.
fetch; git -C "$M" checkout -q main
d1="$(room sd1 s/d1 D1)"; d2="$(room sd2 s/d2 D2)"; fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build "sd1:$d1" "sd2:$d2" 2>&1)"; td="$(git -C "$T/train" rev-parse HEAD)"
e="$(room se s/e E "$td")"; fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build --next "se:$e" 2>&1)"
has "$out" "^KEPT +se ${e:0:12}" "a car rebased onto the gating train's tail is KEPT"
has "$out" "^TRAIN 2 .*n=1 gate=not-needed" "its own gate ran on that tree: no gate"
out="$(bash "$TR" build "sd1:$d1" "sd2:$d2" "se:$e" 2>&1)"
has "$out" "^KEPT +se ${e:0:12}" "a rebuilt train has the same tail, so it is still KEPT"
f="$(room sf s/f F)"; fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build "sf:$f" "sd1:$d1" "sd2:$d2" "se:$e" 2>&1)"
has "$out" "^APPLIED +se ${e:0:12}" "a car on re-picked train commits (same patches) is APPLIED"
out="$(bash "$TR" build "sd1:$d1" "se:$e" 2>&1)"
has "$out" "^BAD +se .*not in the train" "a car on a commit that isn't in the train is BAD"

# 10d. CONFLICT names the train car and the files.
fetch; git -C "$M" checkout -q main
root="$(git -C "$M" rev-list --max-parents=0 origin/main)"
x="$(room sx s/x X)"; y="$(room sy s/x Y)"; z="$(room sz a ZZ "$root")"
fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build "sx:$x" "sy:$y" "sz:$z" 2>&1)"
has "$out" "^CONFLICT +sy ${y:0:12} with sx on s/x$" "CONFLICT names the train car and file"
has "$out" "^CONFLICT +sz ${z:0:12} with main on a$" "a conflict with no train car names main"

# 11. Speculative gates (AGAST #3988): train 2 gates on a remote host, on
# train 1's tail, while train 1 gates here.  The remote side is a clone of
# origin; the fake ssh runs the command line locally the way sshd would
# (one string, re-parsed by a shell), and the fake gate stands in for the
# remote run-gate.sh (RZ_FAKE_EXIT picks its verdict).
cat > "$T/bin/fakessh" <<'EOF'
#!/usr/bin/env bash
host="$1"; shift
echo "$host $*" >> "$RZ_TEST_DIR/ssh-log"
[[ -e "$RZ_TEST_DIR/ssh-down" ]] && { echo "ssh: connect to host $host: refused" >&2; exit 255; }
# The remote user's own HOME (its venv lives there), and a login shell's
# PATH: /etc/profile resets it, so no venv on it (AGAST #4025).
HOME="$RZ_TEST_DIR/rhome" PATH=/usr/local/bin:/usr/bin:/bin exec bash -c "$*"
EOF
chmod +x "$T/bin/fakessh"
# The remote host's gate venv: a python3 whose `import pytest` works unless
# no-pytest exists.
mkdir -p "$T/rhome/dev/.venv/bin"
cat > "$T/rhome/dev/.venv/bin/python3" <<'EOF'
#!/bin/sh
[ -e "$RZ_TEST_DIR/no-pytest" ] && { echo "No module named pytest" >&2; exit 1; }
exit 0
EOF
chmod +x "$T/rhome/dev/.venv/bin/python3"
# The fake gate can --wait too: exit with the log's verdict.  A log with no
# EXIT is a gate still queued for a slot: while queued-polls holds N > 0,
# --wait exits RZ_FAKE_QUEUED_RC (not 124: #4025) and counts down; at 0 the
# gate "ends" with EXIT=0.  The log records the python3 the gate would run.
cat > "$T/gate.sh" <<'EOF'
#!/usr/bin/env bash
if [[ "$1" == --wait ]]; then
    echo "waited $2" >&2
    if ! grep -q '^EXIT=' "$2"; then
        n="$(cat "$RZ_TEST_DIR/queued-polls" 2>/dev/null || echo 0)"
        if [[ $n -gt 0 ]]; then echo $((n - 1)) > "$RZ_TEST_DIR/queued-polls"; exit "${RZ_FAKE_QUEUED_RC:-1}"; fi
        [[ -e "$RZ_TEST_DIR/queued-polls" ]] && echo EXIT=0 >> "$2"
    fi
    exit "$(sed -n 's/^EXIT=//p' "$2" | tail -1)"
fi
log="$RZ_TEST_DIR/gate-$(git -C "$1" rev-parse --short=12 HEAD).log"
printf 'SHA=%s\nEXIT=%s\nTRAIN=%s\nAFTER=%s\nPYTHON=%s\n' "$(git -C "$1" rev-parse HEAD)" "${RZ_FAKE_EXIT:-0}" "${RZ_GATE_TRAIN:-}" "${RZ_GATE_AFTER:-}" "$(command -v python3)" > "$log"
echo "$log"
EOF
git clone -q "$T/origin.git" "$T/remote-rz" 2>/dev/null
export RZ_TRAIN_SSH="$T/bin/fakessh" RZ_TRAIN_REMOTE=hostx RZ_REMOTE_REPO="$T/remote-rz" \
    RZ_REMOTE_WT="$T/remote-train" RZ_REMOTE_GATE="$T/gate.sh" RZ_TRAIN_SSH_RETRY=0 RZ_GATE_SCRIPT="$T/gate.sh"
export RZ_TRAIN_QUEUED_PAUSE=0
RW="$T/remote-train"
oref() { git -C "$M" ls-remote origin "refs/heads/rz-train/$1" | cut -f1; }
specof() { bash "$TR" show 2>/dev/null | sed -n 's/^SPEC=//p' | head -1; }
# two <prefix> <file>: two cars, one each, on the current main.  Sets c1 c2.
two() { c1="$(room "$1"1 "$2"1 X1)"; c2="$(room "$1"2 "$2"2 X2)"; fetch; git -C "$M" checkout -q main; }

# 11a. N and N+1 both pass: land N, then N+1 with the remote verdict.
fetch; git -C "$M" checkout -q main
out="$(bash "$TR" gate --next 2>&1)"; has "$out" "no train" "gate --next with no trains refuses"
two pa s/pa; bash "$TR" build "pa1:$c1" "pa2:$c2" >/dev/null 2>&1
out="$(bash "$TR" gate --next 2>&1)"; has "$out" "no train 2" "gate --next with no train 2 refuses"
log1="$(bash "$TR" gate)"
two pb projects/prism/src/pb; out="$(bash "$TR" build --next "pb1:$c1" "pb2:$c2" 2>&1)"
t2="$(git -C "$T/train-2" rev-parse HEAD)"; t1="$(git -C "$T/train" rev-parse HEAD)"
llog="$(bash "$TR" gate --next 2>"$T/err")"; rc=$?
[[ $rc -eq 0 && "$llog" == "$RZ_GATE_DIR/"*"@hostx.log" ]] && ok "gate --next prints a local log path for the remote gate" \
    || { bad "gate --next prints a local log path (rc=$rc, '$llog')"; sed 's/^/     | /' "$T/err"; }
[[ "$(oref "${t2:0:12}")" == "$t2" ]] && ok "the train 2 tail is pushed to refs/heads/rz-train/<tip12>" \
    || bad "the train 2 tail is pushed to refs/heads/rz-train/<tip12>"
[[ "$(git -C "$RW" rev-parse HEAD 2>/dev/null)" == "$t2" ]] && ok "the remote train worktree is at train 2's tip" \
    || bad "the remote train worktree is at train 2's tip"
rlog="$(specof | cut -d' ' -f3)"
has "$(cat "$rlog" 2>/dev/null)" "^TRAIN=1$" "the remote gate has train priority (RZ_GATE_TRAIN=1)"
has "$(cat "$rlog" 2>/dev/null)" "^AFTER=bash .*remote-train/.claude/skills/rz-iterate/train.sh pkgs test $t1$" \
    "the remote gate tests train 2's packages against its base, train 1's tail"
out="$(bash "$TR" gate --next 2>&1)"; has "$out" "already" "a third train can't gate: at most 2 in flight"
out="$(bash "$TR" wait "$llog" 2>&1)"; rc=$?
[[ $rc -eq 0 && "$(sed -n 's/^SHA=//p' "$llog" 2>/dev/null)" == "$t2" ]] && ok "wait fetches the remote verdict into the local log" \
    || { bad "wait fetches the remote verdict (rc=$rc)"; echo "$out" | sed 's/^/     | /'; }
# A REAP that arrives while both gate rides train 3, not into train 2.
c3="$(room pc1 s/pc1 X)"; fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build --next "pc1:$c3" 2>&1)"
has "$out" "^TRAIN 3 base=${t2:0:12} " "build --next keeps a speculatively gating train 2 and stacks train 3"
[[ "$(git -C "$T/train-2" rev-parse HEAD)" == "$t2" && -n "$(specof)" ]] && ok "train 2 and its remote gate are untouched" \
    || bad "train 2 and its remote gate are untouched"
out="$(bash "$TR" land "$log1" 2>&1)"
has "$out" "^NEXT .*tip=${t2:0:12} .*spec=$llog" "land names the promoted train's remote verdict"
out="$(bash "$TR" gate 2>&1)"; has "$out" "train.sh wait" "gate refuses a train already gating remotely"
out="$(bash "$TR" land "$llog" 2>&1)"
has "$out" "^MERGED +pb2 " "train 2 lands on the remote verdict"
[[ "$(git -C "$M" rev-parse origin/main)" == "$t2" ]] && ok "main is train 2's tail" || bad "main is train 2's tail"
[[ -z "$(oref "${t2:0:12}")" ]] && ok "landing deletes the rz-train ref" || bad "landing deletes the rz-train ref"

# 11b. N fails: N+1's verdict is discarded, N+1 rebuilt on the new base.
fetch; git -C "$M" checkout -q main
two fa s/fa; bash "$TR" build "fa1:$c1" "fa2:$c2" >/dev/null 2>&1; fa1="$c1"
log1="$(RZ_FAKE_EXIT=1 bash "$TR" gate)"
two fb s/fb; bash "$TR" build --next "fb1:$c1" "fb2:$c2" >/dev/null 2>&1; fb1="$c1"; fb2="$c2"
t2="$(git -C "$T/train-2" rev-parse HEAD)"
llog="$(bash "$TR" gate --next 2>/dev/null)"; bash "$TR" wait "$llog" >/dev/null 2>&1
out="$(bash "$TR" land "$log1" 2>&1)"; has "$out" "did not pass" "a failed train 1 doesn't land"
: > "$T/ssh-log"
out="$(bash "$TR" build "fa1:$fa1" 2>&1)"
has "$out" "^DISCARDED .*@hostx.log" "rebuilding drops train 2's speculative verdict"
[[ -z "$(oref "${t2:0:12}")" ]] && ok "a discard deletes the rz-train ref" || bad "a discard deletes the rz-train ref"
grep -q "^hostx bash -l -s -- stop train" "$T/ssh-log" && ok "a discard stops the remote gate" || bad "a discard stops the remote gate"
out="$(bash "$TR" wait "$llog" 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "discarded" "wait refuses a discarded remote gate" || bad "wait refuses a discarded remote gate (rc=$rc)"
n1="$(git -C "$T/train" rev-parse HEAD)"
out="$(bash "$TR" build --next "fb1:$fb1" "fb2:$fb2" 2>&1)"
has "$out" "^TRAIN 2 base=${n1:0:12} " "N+1 is rebuilt on the new train 1's tail"
nt2="$(git -C "$T/train-2" rev-parse HEAD)"
[[ "$nt2" != "$t2" ]] && ok "the rebuilt N+1 has a new tip" || bad "the rebuilt N+1 has a new tip"
bash "$TR" land "$(bash "$TR" gate)" >/dev/null 2>&1
out="$(bash "$TR" land "$llog" 2>&1)"; has "$out" "another commit" "the old speculative verdict can't land the rebuilt N+1"
llog="$(bash "$TR" gate --next 2>&1)"; has "$llog" "no train 2" "after the land, the rebuilt train is train 1"
bash "$TR" land "$(bash "$TR" gate)" >/dev/null 2>&1

# 11c. N passes, N+1 fails: land N, then bisect N+1.
fetch; git -C "$M" checkout -q main
two ca s/ca; bash "$TR" build "ca1:$c1" "ca2:$c2" >/dev/null 2>&1
log1="$(bash "$TR" gate)"
two cb s/cb; bash "$TR" build --next "cb1:$c1" "cb2:$c2" >/dev/null 2>&1; cb1="$c1"; cb2="$c2"
t2="$(git -C "$T/train-2" rev-parse HEAD)"
llog="$(RZ_FAKE_EXIT=1 bash "$TR" gate --next 2>/dev/null)"
bash "$TR" wait "$llog" >/dev/null 2>&1; rc=$?
[[ $rc -eq 1 ]] && ok "wait exits with the remote gate's failure" || bad "wait exits with the remote gate's failure (rc=$rc)"
out="$(bash "$TR" land "$log1" 2>&1)"; has "$out" "^MERGED +ca2 " "train 1 lands though train 2 failed"
out="$(bash "$TR" land "$llog" 2>&1)"; has "$out" "did not pass" "the failed train 2 doesn't land"
out="$(bash "$TR" build "cb1:$cb1" 2>&1)"
has "$out" "^DISCARDED " "the bisect rebuild drops the failed speculative gate"
[[ -z "$(oref "${t2:0:12}")" ]] && ok "the bisect deletes the rz-train ref" || bad "the bisect deletes the rz-train ref"
m="$(git -C "$M" rev-parse origin/main)"
has "$out" "^TRAIN 1 base=${m:0:12} .*n=1 gate=needed" "the first half gates as train 1, on main (train 1's tail)"
bash "$TR" land "$(bash "$TR" gate)" >/dev/null 2>&1

# 11d. A remote verdict for another SHA is refused, and ssh failures are no verdict.
fetch; git -C "$M" checkout -q main
two da s/da; bash "$TR" build "da1:$c1" "da2:$c2" >/dev/null 2>&1
log1="$(bash "$TR" gate)"
two db s/db; bash "$TR" build --next "db1:$c1" "db2:$c2" >/dev/null 2>&1
llog="$(bash "$TR" gate --next 2>/dev/null)"
touch "$T/ssh-down"
out="$(bash "$TR" wait "$llog" 2>&1)"; rc=$?
[[ $rc -ne 0 && ! -e "$llog" ]] && has "$out" "hostx" "an unreachable host is no verdict" \
    || bad "an unreachable host is no verdict (rc=$rc)"
rm -f "$T/ssh-down"
rlog="$(specof | cut -d' ' -f3)"
sed -i "s/^SHA=.*/SHA=$(git -C "$M" rev-parse origin/main)/" "$rlog"
out="$(bash "$TR" wait "$llog" 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "not the train tip" "wait refuses a remote verdict for another SHA" \
    || bad "wait refuses a remote verdict for another SHA (rc=$rc)"
bash "$TR" land "$log1" >/dev/null 2>&1
out="$(bash "$TR" land "$llog" 2>&1)"
has "$out" "another commit" "land refuses a remote verdict whose SHA isn't the train tip"
t2="$(bash "$TR" show | sed -n 's/^TIP=//p' | head -1)"
out="$(bash "$TR" discard 2>&1)"
has "$out" "^DISCARDED speculative gate on hostx for ${t2:0:12} " "discard drops a dead host's speculative gate"
[[ -z "$(oref "${t2:0:12}")" && -z "$(specof)" ]] && ok "discard deletes the ref and the SPEC line" \
    || bad "discard deletes the ref and the SPEC line"
out="$(bash "$TR" land "$(bash "$TR" gate)" 2>&1)"; has "$out" "^MERGED +db2 " "the train then gates and lands here"

# 11e. The remote login shell has no venv on PATH (AGAST #4025): the gate
# runs the host's venv python3, and `start` refuses before taking a slot
# when that python3 can't import pytest.
fetch; git -C "$M" checkout -q main
two ea s/ea; bash "$TR" build "ea1:$c1" "ea2:$c2" >/dev/null 2>&1
log1="$(bash "$TR" gate)"
two eb s/eb; bash "$TR" build --next "eb1:$c1" "eb2:$c2" >/dev/null 2>&1
t2="$(git -C "$T/train-2" rev-parse HEAD)"
touch "$T/no-pytest"
out="$(bash "$TR" gate --next 2>&1)"; rc=$?
rm -f "$T/no-pytest"
[[ $rc -ne 0 ]] && has "$out" "can.t import pytest" "gate --next refuses a host whose gate python has no pytest" \
    || bad "gate --next refuses a host whose gate python has no pytest (rc=$rc)"
[[ ! -e "$T/gate-${t2:0:12}.log" ]] && ok "the no-pytest refusal comes before the gate starts" \
    || bad "the no-pytest refusal comes before the gate starts"
[[ -z "$(oref "${t2:0:12}")" && -z "$(specof)" ]] && ok "the no-pytest refusal leaves no rz-train ref or SPEC" \
    || bad "the no-pytest refusal leaves no rz-train ref or SPEC"
llog="$(bash "$TR" gate --next 2>/dev/null)"
rlog="$(specof | cut -d' ' -f3)"
has "$(cat "$rlog" 2>/dev/null)" "^PYTHON=$T/rhome/dev/\.venv/bin/python3$" \
    "the remote gate runs with the host's ~/dev/.venv first on PATH"

# 11f. A remote gate still queued for a slot (no EXIT yet, its waiter alive)
# is still running, whatever code its --wait slice ended with (AGAST #4025).
sed -i '/^EXIT=/d' "$rlog"
printf 'UNIT=rz-test-4025-no-such-unit\nWAITING for a gate slot, queue position 2 now\n' >> "$rlog"
sleep 300 & qpid=$!
echo "rz-test-4025-no-such-unit $qpid 1 $(date +%s)" > "$(dirname "$rlog")/.gate-queue"
echo 2 > "$T/queued-polls"; : > "$T/ssh-log"
out="$(timeout 60 bash "$TR" wait "$llog" 2>&1)"; rc=$?
[[ $rc -eq 0 ]] && has "$out" "SHA=${t2:0:12} EXIT=0$" "wait keeps waiting through a queued remote gate's non-124 slice" \
    || { bad "wait keeps waiting through a queued remote gate's non-124 slice (rc=$rc)"; echo "$out" | sed 's/^/     | /'; }
[[ "$(grep -c -- '-- wait ' "$T/ssh-log")" == 3 ]] && ok "wait polled the queued gate until its verdict" \
    || bad "wait polled the queued gate until its verdict ($(grep -c -- '-- wait ' "$T/ssh-log") polls)"
# Its waiter gone and still no EXIT: a dead gate, no verdict, not a hang.
kill "$qpid" 2>/dev/null; wait "$qpid" 2>/dev/null
sed -i '/^EXIT=/d' "$rlog"; echo 1 > "$T/queued-polls"
out="$(timeout 60 bash "$TR" wait "$llog" 2>&1)"; rc=$?
[[ $rc -eq 98 ]] && has "$out" "EXIT=none" "a queued remote gate whose waiter died is no verdict, not a hang" \
    || bad "a queued remote gate whose waiter died is no verdict, not a hang (rc=$rc)"
rm -f "$T/queued-polls" "$(dirname "$rlog")/.gate-queue"; echo EXIT=0 >> "$rlog"
bash "$TR" wait "$llog" >/dev/null 2>&1
bash "$TR" land "$log1" >/dev/null 2>&1
out="$(bash "$TR" land "$llog" 2>&1)"; has "$out" "^MERGED +eb2 " "the queued-then-passed remote verdict lands"
echo;[[ $fails -eq 0 ]] && echo "all passed" || { echo "$fails failed"; exit 1; }
