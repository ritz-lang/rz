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
# Never the real ritz-gate-train unit (AGAST #4151): the fake ssh below runs
# REMOTE_SH's `stop <name>` with the real systemctl, on this very machine.
export RZ_TRAIN_NAME="test-train-$$"
TR="$HERE/train.sh"
fetch() { git -C "$M" fetch -q origin; }
# gland: gate the train to gate (a passing fake gate) and land it.  Every
# train with a car needs a full gate (AGAST #4580 item 9), KEPT cars too.
gland() { bash "$TR" land "$(bash "$TR" gate 2>/dev/null)"; }

# 1. One commit already on main: kept with its SHA, no gate, lands.
fetch; s1="$(room r1 a A1)"; git -C "$M" checkout -q main
out="$(bash "$TR" build "r1:$s1" 2>&1)"
has "$out" "^KEPT +r1 ${s1:0:12}" "fast-forward item is KEPT"
has "$out" "gate=needed" "a lone KEPT item still needs a full gate (#4580: its room may have smoke-checked only)"
out="$(bash "$TR" land 2>&1)"; has "$out" "gate needed" "land refuses a KEPT train with no gate log"
out="$(gland 2>&1)"
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
# Re-gating a red train 1 is explicit (AGAST #4156: plain `gate` says fail it).
log="$(bash "$TR" gate 1)"
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
printf "%s\n" "$*" >> "$RZ_TEST_DIR/systemd-run-log"
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
# `stop <unit>` is logged and ends the fake unit (AGAST #4151).
if [[ " $* " == *" stop "* ]]; then
    echo "stop ${!#}" >> "$RZ_TEST_DIR/systemctl-log"; rm -f "$RZ_TEST_ACTIVE/${!#}"; exit 0
fi
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
before="$(date +%s)"; out="$(gland 2>&1)"
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
# #4420: a caller's `.gate-log-name` in the worktree the gate tests must not
# outlive the gate, or `adele room rm` of that worktree refuses it at teardown.
pre22="$(git -C "$T/train" status --porcelain)"
printf 'gate-logs/stale-1.log\n' > "$T/train/.gate-log-name"
log="$(RZ_GATE_SCRIPT="$RG" RZ_TEST_NAME=T RZ_GATE_CMD="$rec; ls -A \"\$RZ_DIR\" > \"\$RZ_TEST_ORDER.during-t\"" \
    timeout 30 bash "$TR" gate)"
[[ ! -e "$T/train/.gate-log-name" && "$(git -C "$T/train" status --porcelain)" == "$pre22" ]] \
    && ok "the train's gate leaves no .gate-log-name in its worktree (#4420)" \
    || bad "the train's gate leaves no .gate-log-name in its worktree (#4420)"
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

# 6d. A train that needs no gate drops the reservation: no train gate is
# coming.  Only a train with no car needs none (AGAST #4580): here its one
# item is already on main.
date +%s > "$RES"
fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build "r9:$s9" 2>&1)"
has "$out" "n=0 gate=not-needed" "a train with no car needs no gate"
[[ ! -e "$RES" ]] && ok "building a gate=not-needed train drops the reservation" \
    || bad "building a gate=not-needed train drops the reservation"

# 7. Touched packages (AGAST #3363): `pkgs list` names the workspace packages
# a train touches, for the gate's PKGS preview line.  The gate itself adds no
# package-test step: its test-all job tests every package (AGAST #3969), and
# `pkgs test` with its PRE-EXISTING base re-run is retired (AGAST #3970).
fetch; git -C "$M" checkout -q --detach origin/main
for d in projects/ritz projects/harland projects/harland/boot projects/ritzunit/inventory \
         projects/oldbad projects/lexis projects/ritz-lsp projects/prism; do
    mkdir -p "$M/$d"; echo "[package]" > "$M/$d/ritz.toml"
done
mkdir -p "$M/projects/prism/src"; echo x > "$M/projects/prism/src/main.ritz"
printf '%s\n' '[workspace.exclude]' '"projects/harland/boot" = "built by harland"' > "$M/rz.toml"
git -C "$M" add -A; git -C "$M" commit -qm packages; git -C "$M" push -q origin HEAD:main
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

train projects/prism/src/main.ritz projects/ritz/x projects/harland/boot/y \
      projects/ritzunit/inventory/z projects/README projects/ritz-lsp/w
out="$(cd "$T/train" && bash "$PK" pkgs list "$tb" 2>&1)"
want="projects/harland projects/prism projects/ritz-lsp projects/ritzunit/inventory "
[[ "$(tr '\n' ' ' <<<"$out")" == "$want" ]] \
    && ok "list: each touched file's owning package, minus projects/ritz and excluded dirs" \
    || { bad "list: touched packages"; echo "$out" | sed 's/^/     | /'; }
log="$(bash "$TR" gate 2>"$T/err")"
has "$(cat "$log")" "^AFTER=$" "a train touching packages adds no package-test step to its gate (AGAST #3970)"
has "$(cat "$T/err")" "^PKGS projects/harland projects/prism " "the gate still previews the touched packages"
out="$(cd "$T/train" && bash "$PK" pkgs test "$tb" 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && ok "pkgs test is retired: it fails (rc=$rc)" || bad "pkgs test is retired: it fails (rc=$rc)"
has "$out" "usage: .* pkgs list <base>" "pkgs test is retired: a usage error naming pkgs list"

train projects/ritz/only
log="$(bash "$TR" gate 2>/dev/null)"
has "$(cat "$log")" "^AFTER=$" "a train touching only projects/ritz adds nothing to its gate"
# No ritzlib/tests package (yet): a ritzlib change has nothing to select.
train projects/ritz/ritzlib/net.ritz
out="$(cd "$T/train" && bash "$PK" pkgs list "$tb" 2>&1)"
[[ -z "$out" ]] && ok "list: a ritzlib change selects no ritzlib/tests that doesn't exist" \
    || { bad "list: a ritzlib change selects no ritzlib/tests that doesn't exist"; echo "$out" | sed 's/^/     | /'; }


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
has "$(cat "$log")" "^AFTER=$" "a ritzlib-only train adds no package-test step to its gate"

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
t1="$(git -C "$T/train" rev-parse HEAD)"
log1="$(bash "$TR" gate)"; s1="$(st1)"
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
# Deepest first (AGAST #4156): one gate, on train 2's tip, lands all 10.
out="$(bash "$TR" land "$(bash "$TR" gate)" 2>&1)"
[[ "$(grep -c '^MERGED' <<<"$out")" == 10 ]] && ok "one gate on train 2's tip lands all 10 cars" \
    || bad "one gate on train 2's tip lands all 10 cars"
has "$out" "^MERGED +sc9 " "train 2 lands its cars"

# 10c. A car rebased onto an unlanded train commit boards, not BAD.
fetch; git -C "$M" checkout -q main
d1="$(room sd1 s/d1 D1)"; d2="$(room sd2 s/d2 D2)"; fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build "sd1:$d1" "sd2:$d2" 2>&1)"; td="$(git -C "$T/train" rev-parse HEAD)"
e="$(room se s/e E "$td")"; fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build --next "se:$e" 2>&1)"
has "$out" "^KEPT +se ${e:0:12}" "a car rebased onto the gating train's tail is KEPT"
has "$out" "^TRAIN 2 .*n=1 gate=needed" "a KEPT car's train still needs a full gate (#4580)"
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

# 10e. A multi-slice room (AGAST #4382): one branch, one REAP per slice, so
# the branch tip has moved on when a later slice boards, and every earlier
# slice is on main (or in a train) under the train's cherry-picked SHA.  Each
# slice must board as it arrives; a multi-commit car with two genuinely
# unlanded commits must still be refused.
# sl <branch> <n>: commit slice <n> on the current branch; say its SHA.
sl() {
    mkdir -p "$M/sl"; echo "$1 slice $2" > "$M/sl/$1-$2"
    git -C "$M" add -A; git -C "$M" commit -qm "$1: slice $2"
    git -C "$M" rev-parse HEAD
}
# 10e. 4 slices, each REAPed at the tip: a fresh branch based one commit
# behind main, so landing always cherry-picks to a new SHA.
fetch; git -C "$M" checkout -q main
mbase="$(git -C "$M" rev-parse origin/main~1)"
git -C "$M" checkout -q --detach "$mbase"; git -C "$M" checkout -q -b mslice
m1="$(sl mslice 1)"; git -C "$M" push -q origin HEAD:refs/heads/mslice
fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build "mslice:$m1" 2>&1)"
has "$out" "^APPLIED +mslice ${m1:0:12} as " "slice 1 of 4 boards"
out="$(bash "$TR" land "$(bash "$TR" gate)" 2>&1)"
has "$out" "^MERGED +mslice ${m1:0:12} as " "slice 1 of 4 lands under a new SHA"
git -C "$M" checkout -q mslice
m2="$(sl mslice 2)"; git -C "$M" push -q origin HEAD:refs/heads/mslice
fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build "mslice:$m2" 2>&1)"
has "$out" "^APPLIED +mslice ${m2:0:12} as " \
    "slice 2 of 4 boards after slice 1 landed under a new SHA"
out="$(bash "$TR" land "$(bash "$TR" gate)" 2>&1)"
git -C "$M" checkout -q mslice
m3="$(sl mslice 3)"; m4="$(sl mslice 4)"
git -C "$M" push -q origin HEAD:refs/heads/mslice        # the tip is m4
fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build "mslice:$m3" 2>&1)"
has "$out" "^APPLIED +mslice ${m3:0:12} as " \
    "a REAP the branch tip has moved past boards its own slice"
out="$(bash "$TR" land "$(bash "$TR" gate)" 2>&1)"
git -C "$M" checkout -q main
out="$(bash "$TR" build "mslice:$m4" 2>&1)"
has "$out" "^APPLIED +mslice ${m4:0:12} as " "slice 4 of 4 boards"
out="$(bash "$TR" land "$(bash "$TR" gate)" 2>&1)"
has "$out" "^MERGED +mslice ${m4:0:12} as " "slice 4 of 4 lands"
[[ "$(git -C "$M" show origin/main:sl/mslice-4)" == "mslice slice 4" ]] \
    && ok "all 4 slices are on main" || bad "all 4 slices are on main"
# 10f. 3 slices, slice 1 landed, slice 2 gating in train 1, slice 3 arrives:
# the count is over unlanded, untrained commits, so it boards (the shape of
# the ritz-task-202 repro).
fetch; git -C "$M" checkout -q main
tbase="$(git -C "$M" rev-parse origin/main~1)"
git -C "$M" checkout -q --detach "$tbase"; git -C "$M" checkout -q -b tslice
t1="$(sl tslice 1)"; git -C "$M" push -q origin HEAD:refs/heads/tslice
fetch; git -C "$M" checkout -q main
bash "$TR" build "tslice:$t1" >/dev/null 2>&1
bash "$TR" land "$(bash "$TR" gate)" >/dev/null 2>&1
git -C "$M" checkout -q tslice
t2="$(sl tslice 2)"; git -C "$M" push -q origin HEAD:refs/heads/tslice
fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build "tslice:$t2" 2>&1)"
has "$out" "^APPLIED +tslice ${t2:0:12} as " "the second slice boards as train 1"
bash "$TR" gate >/dev/null 2>&1                      # train 1 gating
git -C "$M" checkout -q tslice
t3="$(sl tslice 3)"; git -C "$M" push -q origin HEAD:refs/heads/tslice
fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build --next "tslice:$t3" 2>&1)"
has "$out" "^APPLIED +tslice ${t3:0:12} as " \
    "slice 3 boards with slice 1 on main and slice 2 in train 1"
has "$out" "^TRAIN 2 .*n=1 gate=needed" "it is the only car of train 2"
git -C "$M" checkout -q main
# 10g. Two genuinely unlanded commits are still refused, also when an earlier
# slice has landed under a new SHA; the named slice alone still boards.
fetch; git -C "$M" checkout -q main
ubase="$(git -C "$M" rev-parse origin/main~1)"
git -C "$M" checkout -q --detach "$ubase"; git -C "$M" checkout -q -b uslice
u1="$(sl uslice 1)"; git -C "$M" push -q origin HEAD:refs/heads/uslice
fetch; git -C "$M" checkout -q main
bash "$TR" build "uslice:$u1" >/dev/null 2>&1
bash "$TR" land "$(bash "$TR" gate)" >/dev/null 2>&1
git -C "$M" checkout -q uslice
u2="$(sl uslice 2)"; u3="$(sl uslice 3)"
git -C "$M" push -q origin HEAD:refs/heads/uslice
fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build "uslice:$u3" 2>&1)"
has "$out" "^BAD +uslice ${u3:0:12}: 3 commits over main, 2 not in the train" \
    "two genuinely unlanded commits are still BAD"
out="$(bash "$TR" build "uslice:$u2" 2>&1)"
has "$out" "^APPLIED +uslice ${u2:0:12} as " \
    "the named slice alone still boards when the tip has moved past it"
out="$(bash "$TR" land "$(bash "$TR" gate)" 2>&1)"
has "$out" "^MERGED +uslice ${u2:0:12} as " "the named slice lands"

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
# ssh-flaky: every other connection fails (a slow host, AGAST #4318).
if [[ -e "$RZ_TEST_DIR/ssh-flaky" ]]; then
    if [[ "$(cat "$RZ_TEST_DIR/ssh-flaky")" == 1 ]]; then
        echo 0 > "$RZ_TEST_DIR/ssh-flaky"; echo "ssh: connect to host $host: timed out" >&2; exit 255
    fi
    echo 1 > "$RZ_TEST_DIR/ssh-flaky"
fi
# ssh-wait-err holds N > 0: the next N remote waits fail with exit 1, an
# error in the wait itself, not a verdict (AGAST #5001).
if [[ -e "$RZ_TEST_DIR/ssh-wait-err" && " $* " == *" -- wait "* ]]; then
    n="$(cat "$RZ_TEST_DIR/ssh-wait-err")"
    if [[ $n -gt 0 ]]; then
        echo $((n - 1)) > "$RZ_TEST_DIR/ssh-wait-err"; echo "remote: the wait failed" >&2; exit 1
    fi
fi
# The remote user's own HOME (its venv lives there), and a login shell's
# PATH: /etc/profile resets it, so no venv on it (AGAST #4025).
# Each host has its own gate dir, and its own host.env if the test wrote one
# (AGAST #4031: `free` reads them).
export RZ_GATE_DIR="$RZ_TEST_DIR/gates-$host" RZ_TEST_HOST="$host"
if [[ -e "$RZ_TEST_DIR/host-$host.env" ]]; then
    unset RZ_GATE_SLOTS RZ_TRAIN_SLOTS; export RZ_HOST_ENV="$RZ_TEST_DIR/host-$host.env"
fi
HOME="$RZ_TEST_DIR/rhome" PATH="$RZ_TEST_DIR/rbin:/usr/local/bin:/usr/bin:/bin" exec bash -c "$*"
EOF
chmod +x "$T/bin/fakessh"
# The remote host's gate venv: a python3 whose `import pytest` works unless
# no-pytest exists.  Any other -c runs the real python3, with the host's
# rsite-<host> on its path if there is one: hand-made dist-infos for the
# requirements.lock check (AGAST #4583).
mkdir -p "$T/rhome/dev/.venv/bin"
cat > "$T/rhome/dev/.venv/bin/python3" <<EOF
#!/bin/sh
[ -e "\$RZ_TEST_DIR/no-pytest" ] && { echo "No module named pytest" >&2; exit 1; }
[ "\$1 \$2" = "-c import pytest" ] && exit 0
if [ "\$1" = -c ]; then
    [ -d "\$RZ_TEST_DIR/rsite-\$RZ_TEST_HOST" ] && export PYTHONPATH="\$RZ_TEST_DIR/rsite-\$RZ_TEST_HOST"
    exec "$(command -v python3)" "\$@"
fi
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
        if [[ $n -gt 0 ]]; then
        echo $((n - 1)) > "$RZ_TEST_DIR/queued-polls"
        # RZ_FAKE_GROW: the gate is mid-run, its log advancing (AGAST #4318).
        [[ -n "${RZ_FAKE_GROW:-}" ]] && echo "tests/x.py ... [$n%]" >> "$2"
        exit "${RZ_FAKE_QUEUED_RC:-1}"
    fi
        [[ -e "$RZ_TEST_DIR/queued-polls" ]] && echo EXIT=0 >> "$2"
    fi
    exit "$(sed -n 's/^EXIT=//p' "$2" | tail -1)"
fi
log="$RZ_TEST_DIR/gate-$(git -C "$1" rev-parse --short=12 HEAD).log"
printf 'SHA=%s\nEXIT=%s\nTRAIN=%s\nAFTER=%s\nPYTHON=%s\nGBASE=%s\n' "$(git -C "$1" rev-parse HEAD)" "${RZ_FAKE_EXIT:-0}" "${RZ_GATE_TRAIN:-}" "${RZ_GATE_AFTER:-}" "$(command -v python3)" "${RZ_GATE_BASE:-}" > "$log"
echo "$log"
EOF
git clone -q "$T/origin.git" "$T/remote-rz" 2>/dev/null
export RZ_TRAIN_SSH="$T/bin/fakessh" RZ_TRAIN_HOSTS=hostx RZ_TRAIN_LOCAL=localbox RZ_REMOTE_REPO="$T/remote-rz" \
    RZ_REMOTE_WT="$T/remote-train" RZ_REMOTE_GATE="$T/gate.sh" RZ_TRAIN_SSH_RETRY=0 RZ_GATE_SCRIPT="$T/gate.sh"
export RZ_TRAIN_QUEUED_PAUSE=0
RW="$T/remote-train"
oref() { git -C "$M" ls-remote origin "refs/heads/rz-train/$1" | cut -f1; }
# The deepest SPEC: train 1 can have one too now (AGAST #4422).
specof() { bash "$TR" show 2>/dev/null | sed -n 's/^SPEC=//p' | tail -1; }
# rw_of <k>: the remote worktree train k gates in (AGAST #4031: one per slot).
rw_of() {
    local w; w="$(bash "$TR" show 2>/dev/null | sed -n "s/^== train $1 //p")"
    if [[ "$w" == "$T/train" ]]; then echo "$RW"; else echo "$RW-${w##*-}"; fi
}
# two <prefix> <file>: two cars, one each, on the current main.  Sets c1 c2.
two() { c1="$(room "$1"1 "$2"1 X1)"; c2="$(room "$1"2 "$2"2 X2)"; fetch; git -C "$M" checkout -q main; }

# 11a. N and N+1 both pass: land N, then N+1 with the remote verdict.
fetch; git -C "$M" checkout -q main
out="$(bash "$TR" gate --next 2>&1)"; has "$out" "no train" "gate --next with no trains refuses"
two pa s/pa; bash "$TR" build "pa1:$c1" "pa2:$c2" >/dev/null 2>&1
mb="$(git -C "$M" rev-parse origin/main)"
t1="$(git -C "$T/train" rev-parse HEAD)"
# Train 1 gates remotely too (AGAST #4422); plain `gate` stays the local path.
log1="$(bash "$TR" gate --next 2>"$T/err")"; rc=$?
[[ $rc -eq 0 && "$log1" == "$RZ_GATE_DIR/"*"@hostx.log" ]] && ok "gate --next gates train 1 on hostx (a remote SPEC)" \
    || { bad "gate --next gates train 1 on hostx (rc=$rc, '$log1')"; sed 's/^/     | /' "$T/err"; }
[[ "$(specof)" == "hostx rz-train/${t1:0:12} "* ]] && ok "train 1 records SPEC=hostx <ref> ..." \
    || bad "train 1 records SPEC=hostx <ref> ... (spec: '$(specof)')"
rlog1="$(specof | cut -d' ' -f3)"
has "$(cat "$rlog1" 2>/dev/null)" "^TRAIN=1$" "the remote train 1 gate has train priority (RZ_GATE_TRAIN=1)"
has "$(cat "$rlog1" 2>/dev/null)" "^GBASE=$mb$" "train 1's remote gate base is main"
has "$(cat "$rlog1" 2>/dev/null)" "^SHA=$t1$" "the remote gate runs train 1's tip"
out="$(bash "$TR" wait "$log1" 2>&1)"; rc=$?
[[ $rc -eq 0 && "$(sed -n 's/^SHA=//p' "$log1" 2>/dev/null)" == "$t1" ]] && ok "wait fetches train 1's remote verdict" \
    || { bad "wait fetches train 1's remote verdict (rc=$rc)"; echo "$out" | sed 's/^/     | /'; }
two pb projects/prism/src/pb; out="$(bash "$TR" build --next "pb1:$c1" "pb2:$c2" 2>&1)"
t2="$(git -C "$T/train-2" rev-parse HEAD)"; t1="$(git -C "$T/train" rev-parse HEAD)"
rw2="$(rw_of 2)"
llog="$(bash "$TR" gate --next 2>"$T/err")"; rc=$?
[[ $rc -eq 0 && "$llog" == "$RZ_GATE_DIR/"*"@hostx.log" ]] && ok "gate --next prints a local log path for the remote gate" \
    || { bad "gate --next prints a local log path (rc=$rc, '$llog')"; sed 's/^/     | /' "$T/err"; }
[[ "$(oref "${t2:0:12}")" == "$t2" ]] && ok "the train 2 tail is pushed to refs/heads/rz-train/<tip12>" \
    || bad "the train 2 tail is pushed to refs/heads/rz-train/<tip12>"
[[ "$(git -C "$rw2" rev-parse HEAD 2>/dev/null)" == "$t2" ]] && ok "the remote train worktree is at train 2's tip" \
    || bad "the remote train worktree is at train 2's tip"
rlog="$(specof | cut -d' ' -f3)"
has "$(cat "$rlog" 2>/dev/null)" "^TRAIN=1$" "the remote gate has train priority (RZ_GATE_TRAIN=1)"
# Against main, train 1's base, not train 1's tail (AGAST #4151): a pass of
# train 2 lands train 1 too, so its gate must test train 1's packages.
has "$(cat "$rlog" 2>/dev/null)" "^AFTER=$" "the remote gate adds no package-test step (AGAST #3970)"
has "$(cat "$rlog" 2>/dev/null)" "^GBASE=$mb$" "the remote gate's diff base is main, train 1's base"
out="$(bash "$TR" gate --next 2>&1)"; has "$out" "already gating" "gate --next refuses when every later train is gating"
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
out="$(bash "$TR" gate 1 2>&1)"; has "$out" "train 1 passed on hostx: train.sh land $llog" "gate 1 refuses a train whose remote gate passed"
out="$(bash "$TR" land "$llog" 2>&1)"
has "$out" "^MERGED +pb2 " "train 2 lands on the remote verdict"
[[ "$(git -C "$M" rev-parse origin/main)" == "$t2" ]] && ok "main is train 2's tail" || bad "main is train 2's tail"
[[ -z "$(oref "${t2:0:12}")" ]] && ok "landing deletes the rz-train ref" || bad "landing deletes the rz-train ref"

# 11a-fallback. Train 1 gates here when no remote host has a free train slot
# (AGAST #4422: plain `gate` is the local fallback; the reason is on stderr).
fetch; git -C "$M" checkout -q main
printf 'RZ_GATE_SLOTS=1\nRZ_TRAIN_SLOTS=1\n' > "$T/host-hostx.env"
mkdir -p "$T/gates-hostx"
exec 8>>"$T/gates-hostx/.gate-slot-0"; flock -n 8
two pa2 s/pa2; bash "$TR" build "pa21:$c1" "pa22:$c2" >/dev/null 2>&1
tf="$(git -C "$T/train" rev-parse HEAD)"
out="$(bash "$TR" gate --next 2>"$T/err")"; rc=$?
exec 8>&-; rm -f "$T/host-hostx.env"
[[ $rc -eq 0 ]] && ok "train 1 gates here when no host has a free train slot" \
    || { bad "train 1 gates here when no host has a free train slot (rc=$rc)"; sed 's/^/     | /' "$T/err"; }
grep -q "hostx: no free train slot" "$T/err" && ok "the fallback says why (hostx: no free train slot)" \
    || { bad "the fallback says why (hostx: no free train slot)"; sed 's/^/     | /' "$T/err"; }
gl="$(bash "$TR" show 2>/dev/null | sed -n 's/^GATED=//p' | tail -1)"
has "$(cat "$gl" 2>/dev/null)" "^SHA=$tf$" "the local fallback gate ran train 1 (GATED, as plain gate)"
has "$(cat "$gl" 2>/dev/null)" "^TRAIN=1$" "the local fallback gate has train priority"
out="$(bash "$TR" land "$gl" 2>&1)"; has "$out" "^MERGED +pa22 " "the local fallback verdict lands train 1"

# 11a-unreachable. An unreachable host is skipped, not fatal, for train 1 too.
fetch; git -C "$M" checkout -q main
two pa3 s/pa3; bash "$TR" build "pa31:$c1" "pa32:$c2" >/dev/null 2>&1
tu="$(git -C "$T/train" rev-parse HEAD)"
touch "$T/ssh-down"
out="$(bash "$TR" gate --next 2>"$T/err")"; rc=$?
rm -f "$T/ssh-down"
[[ $rc -eq 0 ]] && ok "an unreachable host is skipped, not fatal, for train 1" \
    || { bad "an unreachable host is skipped, not fatal, for train 1 (rc=$rc)"; sed 's/^/     | /' "$T/err"; }
grep -q "hostx: unreachable" "$T/err" && ok "an unreachable host is named, not fatal" \
    || { bad "an unreachable host is named, not fatal"; sed 's/^/     | /' "$T/err"; }
gu="$(bash "$TR" show 2>/dev/null | sed -n 's/^GATED=//p' | tail -1)"
has "$(cat "$gu" 2>/dev/null)" "^SHA=$tu$" "train 1 falls back here after the unreachable host"
bash "$TR" land "$gu" >/dev/null 2>&1

# 11b. N fails: N+1's verdict is discarded, N+1 rebuilt on the new base.
fetch; git -C "$M" checkout -q main
two fa s/fa; bash "$TR" build "fa1:$c1" "fa2:$c2" >/dev/null 2>&1; fa1="$c1"
log1="$(RZ_FAKE_EXIT=1 bash "$TR" gate)"; sed -i '/^EXIT=/d' "$log1"   # still running
two fb s/fb; bash "$TR" build --next "fb1:$c1" "fb2:$c2" >/dev/null 2>&1; fb1="$c1"; fb2="$c2"
t2="$(git -C "$T/train-2" rev-parse HEAD)"
llog="$(bash "$TR" gate --next 2>/dev/null)"; bash "$TR" wait "$llog" >/dev/null 2>&1
echo EXIT=1 >> "$log1"                                                  # then red
out="$(bash "$TR" land "$log1" 2>&1)"; has "$out" "did not pass" "a failed train 1 doesn't land"
: > "$T/ssh-log"
out="$(bash "$TR" build "fa1:$fa1" 2>&1)"
has "$out" "^DISCARDED .*@hostx.log" "rebuilding drops train 2's speculative verdict"
[[ -z "$(oref "${t2:0:12}")" ]] && ok "a discard deletes the rz-train ref" || bad "a discard deletes the rz-train ref"
grep -q "^hostx bash -l -s -- stop $RZ_TRAIN_NAME" "$T/ssh-log" && ok "a discard stops the remote gate" || bad "a discard stops the remote gate"
out="$(bash "$TR" wait "$llog" 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "discarded" "wait refuses a discarded remote gate" || bad "wait refuses a discarded remote gate (rc=$rc)"
n1="$(git -C "$T/train" rev-parse HEAD)"
out="$(bash "$TR" build --next "fb1:$fb1" "fb2:$fb2" 2>&1)"
has "$out" "^TRAIN 2 base=${n1:0:12} " "N+1 is rebuilt on the new train 1's tail"
nt2="$(git -C "$T/train-2" rev-parse HEAD)"
[[ "$nt2" != "$t2" ]] && ok "the rebuilt N+1 has a new tip" || bad "the rebuilt N+1 has a new tip"
bash "$TR" land "$(bash "$TR" gate 1)" >/dev/null 2>&1
out="$(bash "$TR" land "$llog" 2>&1)"; has "$out" "another commit" "the old speculative verdict can't land the rebuilt N+1"
llog="$(bash "$TR" gate --next 2>/dev/null)"; rc=$?
[[ $rc -eq 0 && "$(specof | cut -d' ' -f1)" == hostx ]] \
    && ok "after the land, the rebuilt train is train 1 (and gate --next gates it)" \
    || bad "after the land, the rebuilt train is train 1 (rc=$rc, spec: '$(specof)')"
bash "$TR" wait "$llog" >/dev/null 2>&1
[[ "$(sed -n 's/^SHA=//p' "$llog" 2>/dev/null)" == "$nt2" ]] \
    && ok "the rebuilt train's remote verdict is for its tip" \
    || bad "the rebuilt train's remote verdict is for its tip"
bash "$TR" land "$llog" >/dev/null 2>&1

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
kill "$qpid" 2>/dev/null; wait "$qpid" 2>/dev/null

# 11g. A remote gate's slice is no verdict until its log has EXIT= (AGAST
# #4116: `wait` printed EXIT=none mid-gate).  Two slices that time out (124)
# and then EXIT=0: wait keeps waiting.
polls() { grep -c -- '-- wait ' "$T/ssh-log"; }
sed -i '/^EXIT=/d' "$rlog"; echo 2 > "$T/queued-polls"; : > "$T/ssh-log"
out="$(RZ_FAKE_QUEUED_RC=124 timeout 60 bash "$TR" wait "$llog" 2>&1)"; rc=$?
[[ $rc -eq 0 && "$(polls)" == 3 ]] && has "$out" "SHA=${t2:0:12} EXIT=0$" "wait keeps waiting through two timed-out (124) slices to EXIT=0" \
    || { bad "wait keeps waiting through two timed-out (124) slices to EXIT=0 (rc=$rc, $(polls) polls)"; echo "$out" | sed 's/^/     | /'; }
# A slice that ends 0 while the log has no EXIT= (the gate still running, its
# unit missed by alive()) is polled again, not printed as EXIT=none.
sed -i '/^EXIT=/d' "$rlog"; echo 1 > "$T/queued-polls"; : > "$T/ssh-log"
out="$(RZ_FAKE_QUEUED_RC=0 timeout 60 bash "$TR" wait "$llog" 2>&1)"; rc=$?
[[ $rc -eq 0 && "$(polls)" == 2 && "$out" != *EXIT=none* ]] && has "$out" "SHA=${t2:0:12} EXIT=0$" "a slice that ends 0 with no EXIT= in the log is polled again" \
    || { bad "a slice that ends 0 with no EXIT= in the log is polled again (rc=$rc, $(polls) polls)"; echo "$out" | sed 's/^/     | /'; }
# Its waiter gone and never an EXIT: a dead gate, no verdict (non-zero), not
# a hang, after 5 polls.
sed -i '/^EXIT=/d' "$rlog"; echo 99 > "$T/queued-polls"; : > "$T/ssh-log"
out="$(timeout 60 bash "$TR" wait "$llog" 2>&1)"; rc=$?
[[ $rc -eq 98 && "$(polls)" == 5 ]] && has "$out" "EXIT=none" "a remote gate that dies with no verdict exits 98 after 5 polls, not a hang" \
    || bad "a remote gate that dies with no verdict exits 98 after 5 polls, not a hang (rc=$rc, $(polls) polls)"
rm -f "$T/queued-polls" "$(dirname "$rlog")/.gate-queue"; echo EXIT=0 >> "$rlog"
# 11h. A remote wait runs the run-gate.sh of the slot's own tree (AGAST
# #4247): train 2 gates in remote-train-<s>, and on a host where slot 1
# never ran there is no remote-train, so the slot-1 tree's script is no
# verdict (98).  RZ_REMOTE_GATE=- (the default) picks the tree's own script;
# only train 2's tree has one here.
rw2="$(rw_of 2)"; g2="$rw2/.claude/skills/rz-iterate/run-gate.sh"
[[ "$rw2" != "$RW" ]] || bad "train 2 gates in a slot >= 2 tree ($rw2)"
[[ -e "$RW" ]] && mv "$RW" "$T/remote-train.aside"
mkdir -p "$(dirname "$g2")"; [[ -e "$g2" ]] && mv "$g2" "$g2.aside"; cp "$T/gate.sh" "$g2"
# The gate is still running (no EXIT= yet); its --wait ends it with EXIT=0.
sed -i '/^EXIT=/d' "$rlog"; echo 0 > "$T/queued-polls"; : > "$T/ssh-log"
out="$(RZ_REMOTE_GATE=- timeout 60 bash "$TR" wait "$llog" 2>&1)"; rc=$?
rm -f "$T/queued-polls"; grep -q '^EXIT=' "$rlog" || echo EXIT=0 >> "$rlog"
[[ $rc -eq 0 ]] && has "$out" "SHA=${t2:0:12} EXIT=0$" "a slot >= 2 remote wait with no slot-1 tree reads the verdict from its own tree" \
    || { bad "a slot >= 2 remote wait with no slot-1 tree reads the verdict from its own tree (rc=$rc)"; echo "$out" | sed 's/^/     | /'; }
grep -q -- "-- wait $rw2 - " "$T/ssh-log" && ok "the remote wait names the slot's own tree" \
    || bad "the remote wait names the slot's own tree ($(grep -- '-- wait ' "$T/ssh-log" | head -1))"
mv "$g2" "$T/run-gate.sh.4247"; [[ -e "$g2.aside" ]] && mv "$g2.aside" "$g2"
[[ -e "$T/remote-train.aside" ]] && mv "$T/remote-train.aside" "$RW"

# 11i. A remote gate that outlives the old 5-poll cap (AGAST #4318: EXIT=none
# twice with pytest still running).  Each --wait slice ends early with no
# EXIT= (its `systemctl is-active` missed the unit: 98), more than 5 times in
# a row; while the unit is still active, its state is unknown, or the log
# still grows, wait keeps polling to the verdict.  Only a stopped unit whose
# log no longer grows is a dead gate (98, and says so).  The remote side's
# systemctl is a fake: rsystemctl-state holds the unit's ActiveState
# (BUSDOWN: systemctl can't reach the user bus); is-active always misses.
mkdir -p "$T/rbin"
cat > "$T/rbin/systemctl" <<'EOF'
#!/usr/bin/env bash
st="$RZ_TEST_DIR/rsystemctl-state"
[[ -e "$st" ]] || exec env PATH=/usr/local/bin:/usr/bin:/bin systemctl "$@"
[[ "$(cat "$st")" == BUSDOWN ]] && { echo "Failed to connect to bus" >&2; exit 1; }
[[ " $* " == *" show "* ]] && { cat "$st"; exit 0; }
[[ " $* " == *" stop "* ]] && exit 0
exit 3
EOF
chmod +x "$T/rbin/systemctl"
grep -q '^UNIT=' "$rlog" || echo "UNIT=rz-test-4318-unit" >> "$rlog"
# wait4318 <state> <polls> [env...]: a gate with no EXIT= whose --wait ends
# early (98) <polls> times, then writes EXIT=0.
wait4318() {
    local st="$1" n="$2"; shift 2
    sed -i '/^EXIT=/d' "$rlog"; echo "$n" > "$T/queued-polls"; : > "$T/ssh-log"
    echo "$st" > "$T/rsystemctl-state"
    out="$(env RZ_FAKE_QUEUED_RC=98 "$@" timeout 60 bash "$TR" wait "$llog" 2>&1)"; rc=$?
}
wait4318 inactive 8 RZ_FAKE_GROW=1
[[ $rc -eq 0 && "$(polls)" == 9 && "$out" != *EXIT=none* ]] && has "$out" "SHA=${t2:0:12} EXIT=0$" \
    "wait keeps polling a gate whose log still grows, past 5 early ends, to EXIT=0" \
    || { bad "wait keeps polling a gate whose log still grows, past 5 early ends (rc=$rc, $(polls) polls)"; echo "$out" | sed 's/^/     | /'; }
wait4318 active 8
[[ $rc -eq 0 && "$(polls)" == 9 ]] && has "$out" "SHA=${t2:0:12} EXIT=0$" \
    "wait keeps polling a gate whose unit is still active, past 5 early ends, to EXIT=0" \
    || { bad "wait keeps polling a gate whose unit is still active, past 5 early ends (rc=$rc, $(polls) polls)"; echo "$out" | sed 's/^/     | /'; }
wait4318 BUSDOWN 8
[[ $rc -eq 0 && "$(polls)" == 9 ]] && has "$out" "SHA=${t2:0:12} EXIT=0$" \
    "wait keeps polling a gate whose unit state is unknown (no user bus) to EXIT=0" \
    || { bad "wait keeps polling a gate whose unit state is unknown (rc=$rc, $(polls) polls)"; echo "$out" | sed 's/^/     | /'; }
# Queued for a slot (its waiter alive, the unit not started: inactive).
sleep 300 & qpid=$!
echo "$(sed -n 's/^UNIT=//p' "$rlog" | head -1) $qpid 1 $(date +%s)" > "$(dirname "$rlog")/.gate-queue"
wait4318 inactive 8
kill "$qpid" 2>/dev/null; wait "$qpid" 2>/dev/null; rm -f "$(dirname "$rlog")/.gate-queue"
[[ $rc -eq 0 && "$(polls)" == 9 ]] && has "$out" "SHA=${t2:0:12} EXIT=0$" \
    "wait keeps polling a gate queued for a slot, past 5 early ends, to EXIT=0" \
    || { bad "wait keeps polling a gate queued for a slot, past 5 early ends (rc=$rc, $(polls) polls)"; echo "$out" | sed 's/^/     | /'; }
# A slow host whose ssh fails every other time, 8 times over one long gate:
# the retry budget is for failures in a row, not for the whole wait.
echo 1 > "$T/ssh-flaky"; wait4318 active 8; rm -f "$T/ssh-flaky"
[[ $rc -eq 0 ]] && has "$out" "SHA=${t2:0:12} EXIT=0$" "ssh failures that are not 5 in a row don't end a long remote wait" \
    || { bad "ssh failures that are not 5 in a row don't end a long remote wait (rc=$rc)"; echo "$out" | sed 's/^/     | /'; }
# The unit stopped, the log no longer grows, never an EXIT=: dead, 98, and
# the message says the unit stopped.
wait4318 failed 99
[[ $rc -eq 98 && "$(polls)" == 5 ]] && has "$out" "EXIT=none .*stopped" "a stopped remote unit with no EXIT= is 98, saying the unit stopped" \
    || { bad "a stopped remote unit with no EXIT= is 98, saying the unit stopped (rc=$rc, $(polls) polls)"; echo "$out" | sed 's/^/     | /'; }
# Unreachable past the retry budget: 98, saying so.
touch "$T/ssh-down"; wait4318 active 99; rm -f "$T/ssh-down"
[[ $rc -eq 98 ]] && has "$out" "EXIT=none .*unreachable" "a host unreachable past the ssh retry budget is 98, saying unreachable" \
    || { bad "a host unreachable past the ssh retry budget is 98, saying unreachable (rc=$rc)"; echo "$out" | sed 's/^/     | /'; }
# 11k. AGAST #5001: two bangerang train gates were called dead (EXIT=none,
# unit stopped) while their units ran.  Each remote `wait` exited 1, never
# 124: REMOTE_SH ran `exit 124` under set -e in a login shell, so bash ran
# ~/.bash_logout with errexit on, and Ubuntu's `clear_console -q` fails
# with no console over ssh: errexit turned every exit code into 1.  The
# fake remote HOME gets that .bash_logout.  Six timed-out (124) slices,
# then EXIT=0: a verdict, never EXIT=none.
printf '%s\n' '# Ubuntu skel: clear the console on logout (fails over ssh)' 'if [ -e "$RZ_TEST_DIR/rlogout-fails" ]; then' '    [ -x /bin/false ] && /bin/false' 'fi' > "$T/rhome/.bash_logout"
touch "$T/rlogout-fails"
wait4318 active 6 RZ_FAKE_QUEUED_RC=124
[[ $rc -eq 0 && "$(polls)" == 7 && "$out" != *EXIT=none* ]] && has "$out" "SHA=${t2:0:12} EXIT=0$" \
    "a host whose .bash_logout fails under errexit still reports 124 slices: wait goes on to EXIT=0" \
    || { bad "a host whose .bash_logout fails under errexit still reports 124 slices (rc=$rc, $(polls) polls)"; echo "$out" | sed 's/^/     | /'; }
wait4318 failed 2 RZ_FAKE_QUEUED_RC=98
[[ "$out" == *"(wait exit 98): polling again"* ]] && ok "and its 98 (a stopped unit) still reaches the local side as 98" \
    || { bad "and its 98 (a stopped unit) still reaches the local side as 98"; echo "$out" | sed 's/^/     | /'; }
rm -f "$T/rlogout-fails"
# Only the remote's 98 means stopped.  Any other exit is an error in the
# wait itself: retried, never counted as a stopped unit.  The ticket's row:
# exit 1, then 124, then EXIT=0.
echo 1 > "$T/ssh-wait-err"; wait4318 active 1 RZ_FAKE_QUEUED_RC=124
[[ $rc -eq 0 && "$(polls)" == 3 && "$out" != *EXIT=none* ]] && has "$out" "SHA=${t2:0:12} EXIT=0$" \
    "a remote wait that exits 1, then 124, then EXIT=0 is a verdict" \
    || { bad "a remote wait that exits 1, then 124, then EXIT=0 is a verdict (rc=$rc, $(polls) polls)"; echo "$out" | sed 's/^/     | /'; }
# Four errors and two stopped reports are six non-124 slices but not five
# stopped in a row: the old count called that gate dead.
echo 4 > "$T/ssh-wait-err"; wait4318 failed 2 RZ_FAKE_QUEUED_RC=98
[[ $rc -eq 0 && "$(polls)" == 7 && "$out" != *EXIT=none* ]] && has "$out" "SHA=${t2:0:12} EXIT=0$" \
    "wait errors don't count toward the 5 stopped reports that end a wait" \
    || { bad "wait errors don't count toward the 5 stopped reports that end a wait (rc=$rc, $(polls) polls)"; echo "$out" | sed 's/^/     | /'; }
# Errors only, 5 in a row: no verdict (98), and it says the wait failed and
# the gate may be live, not that its unit stopped.
echo 99 > "$T/ssh-wait-err"; wait4318 active 99
[[ $rc -eq 98 && "$(polls)" == 5 && "$out" != *"unit stopped"* ]] && has "$out" "EXIT=none .*remote wait failed 5 times in a row \(last exit 1\).*may still be running" \
    "5 wait errors in a row are 98 saying the wait failed, not that the unit stopped" \
    || { bad "5 wait errors in a row are 98 saying the wait failed, not that the unit stopped (rc=$rc, $(polls) polls)"; echo "$out" | sed 's/^/     | /'; }
rm -f "$T/ssh-wait-err"
rm -f "$T/queued-polls" "$T/rsystemctl-state"; grep -q '^EXIT=' "$rlog" || echo EXIT=0 >> "$rlog"
bash "$TR" wait "$llog" >/dev/null 2>&1
bash "$TR" land "$log1" >/dev/null 2>&1
out="$(bash "$TR" land "$llog" 2>&1)"; has "$out" "^MERGED +eb2 " "the queued-then-passed remote verdict lands"

# 11j. A remote gate log truncated mid-run keeps its identity in a trailer
# next to the verdict (AGAST #4430): wait's SHA check and land read the LAST
# SHA=, so a valid EXIT=0 isn't REFUSED for a lost header.  The stale first
# SHA= stands for a header that survived the truncation.
fetch; git -C "$M" checkout -q main
two ja s/ja; bash "$TR" build "ja1:$c1" "ja2:$c2" >/dev/null 2>&1
t="$(git -C "$T/train" rev-parse HEAD)"
llog="$(bash "$TR" gate --next 2>/dev/null)"; rlog="$(specof | cut -d' ' -f3)"
printf 'SHA=%s\nok Stage 1 output is identical with 1 and 8 jobs\nUNIT=%s\nSHA=%s\nEXIT=0\n' \
    "$(git -C "$M" rev-parse origin/main)" "rz-test-4430-unit" "$t" > "$rlog"
out="$(bash "$TR" wait "$llog" 2>&1)"; rc=$?
[[ $rc -eq 0 ]] && has "$out" "SHA=${t:0:12} EXIT=0$" \
    "wait reads a truncated remote log's trailer SHA= (AGAST #4430)" \
    || { bad "wait reads a truncated remote log's trailer SHA= (rc=$rc)"; echo "$out" | sed 's/^/     | /'; }
out="$(bash "$TR" land "$llog" 2>&1)"
has "$out" "^MERGED +ja2 " "land reads a truncated log's trailer SHA="
# 12. A passed train k lands trains 1..k at once (AGAST #4151, #4130): train
# k is built on train k-1's tail, so its green gate tested every car of
# trains 1..k.  The covered trains' gates are cancelled: the local unit
# stopped, its .train-waiting cleared, a remote one stopped and its ref gone.
U="ritz-gate-$RZ_TRAIN_NAME"; TW="$RZ_GATE_DIR/.train-waiting"
# running <log>: a local train gate still going: no EXIT yet, unit active,
# holding .train-waiting.
running() { sed -i '/^EXIT=/d' "$1"; touch "$T/active/$U"; echo "$U" > "$TW"; }
stops() { cat "$T/systemctl-log" 2>/dev/null; }
ntrains() { bash "$TR" show 2>/dev/null | grep -c '^== train'; }

# 12a. Train 2 passes (remote) while train 1 still gates here: both land in
# one push, train 1's gate is stopped, train 3 is promoted.  Train 2's
# `pkgs list` base is main, so it covers train 1's packages too.
fetch; git -C "$M" checkout -q main; m0="$(git -C "$M" rev-parse origin/main)"
two ga projects/prism/src/ga; bash "$TR" build "ga1:$c1" "ga2:$c2" >/dev/null 2>&1
log1="$(bash "$TR" gate 2>/dev/null)"; running "$log1"
two gb s/gb; bash "$TR" build --next "gb1:$c1" "gb2:$c2" >/dev/null 2>&1
t2="$(git -C "$T/train-2" rev-parse HEAD)"
llog="$(bash "$TR" gate --next 2>/dev/null)"; rlog="$(specof | cut -d' ' -f3)"
has "$(cat "$rlog" 2>/dev/null)" "^AFTER=$" "train 2's remote gate adds no package-test step"
out="$(cd "$(rw_of 2)" && bash "$TR" pkgs list "$m0" 2>&1)"
has "$out" "^projects/prism$" "pkgs list <main> on train 2's tip covers train 1's packages"
c3="$(room gc1 s/gc1 X)"; fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build --next "gc1:$c3" 2>&1)"; t3="$(tipof 3 "$out")"
bash "$TR" wait "$llog" >/dev/null 2>&1
: > "$T/systemctl-log"; : > "$T/ssh-log"
out="$(bash "$TR" land "$llog" 2>&1)"; rc=$?
[[ $rc -eq 0 && "$(grep -c '^MERGED' <<<"$out")" == 4 ]] && ok "land <train 2's log> merges the cars of trains 1 and 2" \
    || { bad "land <train 2's log> merges the cars of trains 1 and 2 (rc=$rc)"; echo "$out" | sed 's/^/     | /'; }
has "$out" "^MERGED +ga1 " "train 1's cars are MERGED"
[[ "$(git -C "$M" rev-parse origin/main)" == "$t2" ]] && ok "main is train 2's tail, in one push" || bad "main is train 2's tail, in one push"
[[ "$(stops)" == "stop $U" && ! -e "$T/active/$U" ]] && ok "train 1's local gate is stopped" \
    || bad "train 1's local gate is stopped (systemctl: '$(stops)')"
[[ ! -e "$TW" ]] && ok "train 1's .train-waiting is cleared, so the slot frees at once" \
    || bad "train 1's .train-waiting is cleared"
has "$out" "^CANCELLED local gate $U " "land says it cancelled train 1's gate"
has "$out" "^NEXT +base=${t2:0:12} tip=$t3 n=1 gate=" "train 3 is promoted to train 1"
[[ "$(ntrains)" == 1 && -z "$(oref "${t2:0:12}")" ]] && ok "trains 1 and 2 are gone, with train 2's ref" \
    || bad "trains 1 and 2 are gone, with train 2's ref ($(ntrains) trains)"
out="$(bash "$TR" land "$(bash "$TR" gate)" 2>&1)"; has "$out" "^MERGED +gc1 " "the promoted train 3 lands next"

# 12b. Train 2 red while train 1 gates: nothing changes.
fetch; git -C "$M" checkout -q main; m="$(git -C "$M" rev-parse origin/main)"
two ha s/ha; bash "$TR" build "ha1:$c1" "ha2:$c2" >/dev/null 2>&1
log1="$(bash "$TR" gate 2>/dev/null)"; running "$log1"
two hb s/hb; bash "$TR" build --next "hb1:$c1" "hb2:$c2" >/dev/null 2>&1; hb1="$c1"; hb2="$c2"
llog="$(RZ_FAKE_EXIT=1 bash "$TR" gate --next 2>/dev/null)"; bash "$TR" wait "$llog" >/dev/null 2>&1
: > "$T/systemctl-log"; : > "$T/ssh-log"
out="$(bash "$TR" land "$llog" 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "did not pass" "a red train 2 doesn't land" || bad "a red train 2 doesn't land (rc=$rc)"
[[ "$(git -C "$M" rev-parse origin/main)" == "$m" && "$(ntrains)" == 2 && -n "$(specof)" ]] \
    && ok "a red train 2 leaves main and both trains alone" || bad "a red train 2 leaves main and both trains alone"
[[ -z "$(stops)" && -e "$T/active/$U" && -e "$TW" && ! -s "$T/ssh-log" ]] && ok "a red train 2 cancels no gate" \
    || bad "a red train 2 cancels no gate (systemctl: '$(stops)')"
rm -f "$T/active/$U" "$TW"; echo EXIT=0 >> "$log1"
bash "$TR" land "$log1" >/dev/null 2>&1; bash "$TR" build "hb1:$hb1" "hb2:$hb2" >/dev/null 2>&1
bash "$TR" land "$(bash "$TR" gate)" >/dev/null 2>&1

# 12c. Train 1 red, train 2 green (#4130's question): train 2 contains every
# car of train 1 and passed on exactly the tree that lands, so both land.
fetch; git -C "$M" checkout -q main
two ia s/ia; bash "$TR" build "ia1:$c1" "ia2:$c2" >/dev/null 2>&1
log1="$(RZ_FAKE_EXIT=1 bash "$TR" gate 2>/dev/null)"; sed -i '/^EXIT=/d' "$log1"
two ib s/ib; bash "$TR" build --next "ib1:$c1" "ib2:$c2" >/dev/null 2>&1
t2="$(git -C "$T/train-2" rev-parse HEAD)"
llog="$(bash "$TR" gate --next 2>/dev/null)"; bash "$TR" wait "$llog" >/dev/null 2>&1
echo EXIT=1 >> "$log1"                       # train 1 goes red after train 2 started
: > "$T/systemctl-log"
out="$(bash "$TR" land "$llog" 2>&1)"
[[ "$(git -C "$M" rev-parse origin/main)" == "$t2" ]] && has "$out" "^MERGED +ia1 " "a green train 2 lands a red train 1 with it" \
    || { bad "a green train 2 lands a red train 1 with it"; echo "$out" | sed 's/^/     | /'; }
[[ -z "$(stops)" ]] && ok "no local gate to stop when train 1's has ended" || bad "no local gate to stop when train 1's has ended"

# 12d. Train 1 gating remotely (a promoted speculative train) and train 2 on
# another host: train 2's pass stops train 1's remote gate and deletes its ref.
fetch; git -C "$M" checkout -q main
two ja s/ja; bash "$TR" build "ja1:$c1" "ja2:$c2" >/dev/null 2>&1; log1="$(bash "$TR" gate)"
two jb s/jb; bash "$TR" build --next "jb1:$c1" "jb2:$c2" >/dev/null 2>&1
tb="$(git -C "$T/train-2" rev-parse HEAD)"
blog="$(bash "$TR" gate --next 2>/dev/null)"; brlog="$(specof | cut -d' ' -f3)"
bash "$TR" land "$log1" >/dev/null 2>&1          # train jb is train 1 now, gating on hostx
sed -i '/^EXIT=/d' "$brlog"
two jc s/jc; bash "$TR" build --next "jc1:$c1" "jc2:$c2" >/dev/null 2>&1
tc="$(bash "$TR" show | sed -n 's/^TIP=//p' | tail -1)"
clog="$(bash "$TR" gate --next hosty 2>/dev/null)"; bash "$TR" wait "$clog" >/dev/null 2>&1
: > "$T/ssh-log"
out="$(bash "$TR" land "$clog" 2>&1)"
[[ "$(git -C "$M" rev-parse origin/main)" == "$tc" ]] && has "$out" "^MERGED +jb1 " "train 2 on hosty lands train 1 gating on hostx" \
    || { bad "train 2 on hosty lands train 1 gating on hostx"; echo "$out" | sed 's/^/     | /'; }
grep -q "^hostx bash -l -s -- stop $RZ_TRAIN_NAME" "$T/ssh-log" && ok "the covered train's remote gate is stopped" \
    || bad "the covered train's remote gate is stopped"
has "$out" "^CANCELLED speculative gate on hostx for ${tb:0:12} " "land says it cancelled the remote gate"
[[ -z "$(oref "${tb:0:12}")" && -z "$(oref "${tc:0:12}")" ]] && ok "both trains' rz-train refs are deleted" \
    || bad "both trains' rz-train refs are deleted"
out="$(bash "$TR" show 2>&1)"; has "$out" "no train built" "nothing left after landing both"

# 12e. Refusals stay: a log for no train's tip, main moved, a covered train's
# worktree moved; none of them cancels a gate.
fetch; git -C "$M" checkout -q main
two ka s/ka; bash "$TR" build "ka1:$c1" "ka2:$c2" >/dev/null 2>&1
log1="$(bash "$TR" gate 2>/dev/null)"; running "$log1"
two kb s/kb; bash "$TR" build --next "kb1:$c1" "kb2:$c2" >/dev/null 2>&1
llog="$(bash "$TR" gate --next 2>/dev/null)"; bash "$TR" wait "$llog" >/dev/null 2>&1
: > "$T/systemctl-log"
m="$(git -C "$M" rev-parse origin/main)"; sed "s/^SHA=.*/SHA=$m/" "$llog" > "$T/main.log"
out="$(bash "$TR" land "$T/main.log" 2>&1)"; has "$out" "another commit" "land refuses a log for no train's tip"
echo x > "$T/train/d"; git -C "$T/train" commit -qam stray
out="$(bash "$TR" land "$llog" 2>&1)"; has "$out" "train 1's worktree moved since build" "land refuses when a covered train's worktree moved"
git -C "$T/train" reset -q --hard HEAD~1
s="$(room km s/km X)"; git -C "$M" push -q origin "$s:refs/heads/main"; git -C "$M" checkout -q main
out="$(bash "$TR" land "$llog" 2>&1)"; has "$out" "main moved" "land <train 2's log> refuses when main moved"
[[ -z "$(stops)" && -e "$T/active/$U" && "$(ntrains)" == 2 ]] && ok "a refused land cancels no gate and keeps the trains" \
    || bad "a refused land cancels no gate and keeps the trains (systemctl: '$(stops)')"

# 13. N trains in flight (AGAST #4031).  RZ_TRAIN_DEPTH trains gate at once,
# train k on train k-1's tail, each on the first RZ_TRAIN_HOSTS host with a
# free train slot; two can share a host (own gate name, own remote tree).
gating() { bash "$TR" show 2>/dev/null | grep -c '^SPEC='; }
tipn() { bash "$TR" show 2>/dev/null | sed -n 's/^TIP=//p' | sed -n "${1}p"; }

# 13a. Three trains in flight land in order.
fetch; git -C "$M" checkout -q main
two na s/na; bash "$TR" build "na1:$c1" "na2:$c2" >/dev/null 2>&1
log1="$(bash "$TR" gate)"
two nb s/nb; bash "$TR" build --next "nb1:$c1" "nb2:$c2" >/dev/null 2>&1
l2="$(bash "$TR" gate --next 2>/dev/null)"
two nc s/nc; out="$(bash "$TR" build --next "nc1:$c1" "nc2:$c2" 2>&1)"
t2="$(tipn 2)"
has "$out" "^TRAIN 3 base=${t2:0:12} " "build --next keeps gating train 2 and stacks train 3 on its tail"
rw3="$(rw_of 3)"; rw2="$(rw_of 2)"
l3="$(bash "$TR" gate --next 2>"$T/err")"; rc=$?
t3="$(tipn 3)"
[[ $rc -eq 0 && "$(gating)" == 2 ]] && ok "a third train gates while two are in flight" \
    || { bad "a third train gates while two are in flight (rc=$rc)"; sed 's/^/     | /' "$T/err"; }
[[ "$rw2" != "$rw3" && "$(git -C "$rw3" rev-parse HEAD 2>/dev/null)" == "$t3" && "$(git -C "$rw2" rev-parse HEAD 2>/dev/null)" == "$t2" ]] \
    && ok "trains 2 and 3 gate in their own remote trees on one host" || bad "trains 2 and 3 gate in their own remote trees"
grep -q -- "start .* $RZ_TRAIN_NAME-[0-9]" "$T/ssh-log" && ok "a train past slot 1 gates under its own name" \
    || bad "a train past slot 1 gates under its own name"
two nd s/nd; bash "$TR" build --next "nd1:$c1" "nd2:$c2" >/dev/null 2>&1
out="$(RZ_TRAIN_DEPTH=3 bash "$TR" gate --next 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "3 trains in flight already \(at most 3" "RZ_TRAIN_DEPTH caps the trains in flight" \
    || bad "RZ_TRAIN_DEPTH caps the trains in flight (rc=$rc)"
l4="$(bash "$TR" gate --next 2>/dev/null)"
[[ "$(gating)" == 3 ]] && ok "the default depth (6) lets a fourth train gate" || bad "the default depth (6) lets a fourth train gate ($(gating))"
t4="$(tipn 4)"
for l in "$l2" "$l3" "$l4"; do bash "$TR" wait "$l" >/dev/null 2>&1; done
out="$(bash "$TR" land "$log1" 2>&1)"; has "$out" "^NEXT .*spec=$l2" "train 1 lands first; train 2 is next"
out="$(bash "$TR" land "$l2" 2>&1)"; has "$out" "^MERGED +nb2 " "train 2 lands second"
has "$out" "^NEXT .*tip=${t3:0:12} .*spec=$l3" "train 3 is next"
out="$(bash "$TR" land "$l3" 2>&1)"; has "$out" "^MERGED +nc2 " "train 3 lands third"
out="$(bash "$TR" land "$l4" 2>&1)"; has "$out" "^MERGED +nd2 " "train 4 lands fourth"
[[ "$(git -C "$M" rev-parse origin/main)" == "$t4" && -z "$(oref "${t3:0:12}")" ]] \
    && ok "main is train 4's tail, each ref gone" || bad "main is train 4's tail, each ref gone"

# 13b. A middle train fails: train 1 and its gate stay; train 2's cars are
# HELD; train 3's gate is stopped and its cars rebuilt on train 1's tail.
fetch; git -C "$M" checkout -q main
two ma s/ma; bash "$TR" build "ma1:$c1" "ma2:$c2" >/dev/null 2>&1
log1="$(bash "$TR" gate)"; t1="$(tipn 1)"
two mb s/mb; bash "$TR" build --next "mb1:$c1" "mb2:$c2" >/dev/null 2>&1; mb1="$c1"
l2="$(RZ_FAKE_EXIT=1 bash "$TR" gate --next 2>/dev/null)"
two mc s/mc; bash "$TR" build --next "mc1:$c1" "mc2:$c2" >/dev/null 2>&1
l3="$(bash "$TR" gate --next 2>/dev/null)"; t3="$(tipn 3)"
bash "$TR" wait "$l2" >/dev/null 2>&1
out="$(bash "$TR" fail "$log1" 2>&1)"; has "$out" "passed" "fail refuses a passed gate"
: > "$T/ssh-log"
out="$(bash "$TR" fail "$l2" 2>&1)"; rc=$?
[[ $rc -eq 0 ]] && has "$out" "^HELD +mb1 ${mb1:0:12}" "fail prints the failed train's cars as HELD" \
    || { bad "fail <train 2's log> (rc=$rc)"; echo "$out" | sed 's/^/     | /'; }
has "$out" "^DISCARDED speculative gate on hostx for ${t3:0:12} " "the later train's gate is discarded"
grep -q -- "-- stop $RZ_TRAIN_NAME-" "$T/ssh-log" && ok "its remote gate is stopped" || bad "its remote gate is stopped"
[[ -z "$(oref "${t3:0:12}")" ]] && ok "its rz-train ref is deleted" || bad "its rz-train ref is deleted"
has "$out" "^TRAIN 2 base=${t1:0:12} .*n=2 gate=needed" "the later train's cars are rebuilt on train 1's tail"
! grep -q "mb[12]" <<<"$(bash "$TR" show | grep ^ITEM=)" && ok "the failed cars are out of every train" \
    || bad "the failed cars are out of every train"
[[ "$(tipn 1)" == "$t1" ]] && ok "train 1 is untouched" || bad "train 1 is untouched"
l2="$(bash "$TR" gate --next 2>/dev/null)"
[[ "$(gating)" == 1 ]] && ok "the rebuilt train re-gates" || bad "the rebuilt train re-gates"
bash "$TR" wait "$l2" >/dev/null 2>&1
out="$(bash "$TR" land "$l2" 2>&1)"
has "$out" "^MERGED +mc2 " "the rebuilt train lands trains 1 and 2"
! grep -q "MERGED +mb" <<<"$out" && ok "without the held cars" || bad "without the held cars"
# A failed train 1 with nothing behind it is just dropped.
fetch; git -C "$M" checkout -q main
two mf s/mf; bash "$TR" build "mf1:$c1" "mf2:$c2" >/dev/null 2>&1
out="$(bash "$TR" fail "$(RZ_FAKE_EXIT=1 bash "$TR" gate)" 2>&1)"
has "$out" "^HELD +mf2 " "a failed lone train holds its cars"
out="$(bash "$TR" show 2>&1)"; has "$out" "no train built" "and leaves no train"

# 13c. pick_train_host: the first host with a free train slot.  This host
# (RZ_TRAIN_LOCAL, 1 slot) and hostx (2 slots, 1 reserved) are full: hosty.
fetch; git -C "$M" checkout -q main
printf 'RZ_GATE_SLOTS=2\nRZ_TRAIN_SLOTS=1\n' > "$T/host-hostx.env"
mkdir -p "$T/gates-hostx" "$RZ_GATE_DIR"
exec 5>>"$RZ_GATE_DIR/.gate-slot-0" 6>>"$T/gates-hostx/.gate-slot-0" 7>>"$T/gates-hostx/.gate-slot-1"
flock -n 5; flock -n 6; flock -n 7
export RZ_TRAIN_HOSTS="localbox hostx hosty"
two pha s/pha; bash "$TR" build "pha1:$c1" "pha2:$c2" >/dev/null 2>&1; log1="$(bash "$TR" gate)"
two phb s/phb; bash "$TR" build --next "phb1:$c1" "phb2:$c2" >/dev/null 2>&1
l2="$(bash "$TR" gate --next 2>"$T/err")"
[[ "$(specof | cut -d' ' -f1)" == hosty ]] && ok "gate --next skips a host whose train slots are full" \
    || { bad "gate --next skips a host whose train slots are full (spec: $(specof))"; sed 's/^/     | /' "$T/err"; }
grep -q "localbox: no free train slot" "$T/err" && grep -q "hostx: no free train slot" "$T/err" \
    && ok "it says why it passed over each" || bad "it says why it passed over each"
# A room gate on hostx's general slot leaves its reserved one free: hostx.
exec 7>&-
bash "$TR" discard hosty >/dev/null 2>&1
[[ -z "$(specof)" ]] && ok "discard <host> drops that host's gate" || bad "discard <host> drops that host's gate"
l2="$(bash "$TR" gate --next 2>/dev/null)"
[[ "$(specof | cut -d' ' -f1)" == hostx ]] && ok "a host with a free reserved slot is picked" \
    || bad "a host with a free reserved slot is picked (spec: $(specof))"
bash "$TR" discard >/dev/null 2>&1
# Every host full: refused, nothing pushed or recorded.
exec 7>>"$T/gates-hostx/.gate-slot-1"; flock -n 7
touch "$T/ssh-down"
out="$(bash "$TR" gate --next 2>&1)"; rc=$?
rm -f "$T/ssh-down"
[[ $rc -ne 0 && -z "$(specof)" ]] && has "$out" "no host in RZ_TRAIN_HOSTS" "no free host: gate --next refuses" \
    || bad "no free host: gate --next refuses (rc=$rc)"
has "$out" "hosty: unreachable" "an unreachable host is skipped"
# This host free: the speculative gate runs here, and waits and lands locally.
exec 5>&- 6>&- 7>&-
l2="$(bash "$TR" gate --next 2>/dev/null)"
[[ "$(specof)" == "localbox - $l2 $l2" && "$l2" != *@* ]] && ok "this host, when free, gates the train here (a local SPEC)" \
    || bad "this host, when free, gates the train here (spec: $(specof))"
out="$(bash "$TR" wait "$l2" 2>&1)"; rc=$?
[[ $rc -eq 0 ]] && ok "wait on a local speculative gate" || bad "wait on a local speculative gate (rc=$rc)"
out="$(bash "$TR" land "$l2" 2>&1)"; has "$out" "^MERGED +phb2 " "a local speculative pass lands"
! grep -q "warning" <<<"$out" && ok "with no ref to delete" || { bad "with no ref to delete"; echo "$out" | sed 's/^/     | /'; }
export RZ_TRAIN_HOSTS=hostx; rm -f "$T/host-hostx.env"

# 13d. pending (the dispatch rule): gate at 8 cars, or after 60 s with no new
# car; each car (a rebuild) restarts the 60 s.
# The slack (50-60 s) is for a loaded host: #4902 saw `58s` at load ~30,
# where three cars took ~2 s to build.  A window that did not restart
# prints GATE, not WAIT.
fetch; git -C "$M" checkout -q main
two qa s/qa; bash "$TR" build "qa1:$c1" "qa2:$c2" >/dev/null 2>&1
out="$(bash "$TR" pending)"
has "$out" "^WAIT train 1 n=2 (5[0-9]|60)s$" "a new train waits 60 s for more cars"
st="$(git -C "$T/train" rev-parse --absolute-git-dir)/RZ_TRAIN"
sed -i "s/^BUILT=.*/BUILT=$(( $(date +%s) - 61 ))/" "$st"
has "$(bash "$TR" pending)" "^GATE train 1 n=2 \(no new car for 60s\): train.sh gate --next$" "no new car for 60 s: gate it"
c3="$(room qa3 s/qa3 X)"; fetch; git -C "$M" checkout -q main
bash "$TR" build "qa1:$c1" "qa2:$c2" "qa3:$c3" >/dev/null 2>&1
has "$(bash "$TR" pending)" "^WAIT train 1 n=3 (5[0-9]|60)s$" "another car restarts the window"
log1="$(bash "$TR" gate)"
[[ -z "$(bash "$TR" pending)" ]] && ok "a gating train is not pending" || bad "a gating train is not pending"
# A train stacked behind a gating one buffers to 8: it takes no second slot
# for a partly-filled train, so the whole next train is gated at once
# (Aaron, 2026-11-20).
c9="$(room qb9 s/qb9 X)"; fetch; git -C "$M" checkout -q main
bash "$TR" build --next "qb9:$c9" >/dev/null 2>&1
eq "$(bash "$TR" pending)" "WAIT train 2 n=1 (buffer to 8: a train below is gating)" \
    "a train behind a gating one buffers to 8 instead of gating"
items=(); for i in 0 1 2 3 4 5 6 7; do items+=("qb$i:$(room "qb$i" "s/qb$i" "Q$i")"); done
fetch; git -C "$M" checkout -q main
bash "$TR" build --next "${items[@]}" >/dev/null 2>&1
has "$(bash "$TR" pending)" "^GATE train 2 n=8 \(full\): train.sh gate --next$" "a train of 8 gates at once"
l2="$(bash "$TR" gate --next 2>/dev/null)"
[[ -z "$(bash "$TR" pending)" ]] && ok "a speculatively gating train is not pending" || bad "a speculatively gating train is not pending"
bash "$TR" wait "$l2" >/dev/null 2>&1; bash "$TR" land "$l2" >/dev/null 2>&1

# 14. Deepest train first (AGAST #4156).  Since #4151 a pass of train k lands
# trains 1..k, so the train to gate is the deepest built one (its tip covers
# every car below it); a shorter prefix gates only to bisect a red deeper
# gate.  Trains of 2 cars here (RZ_TRAIN_MAX), so 6 cars are 3 trains.
export RZ_TRAIN_MAX=2 RZ_TRAIN_DEBOUNCE=0
# cars <prefix> <n>: <n> one-file cars on the current main, as build items.
cars() { local i; items=(); for ((i = 1; i <= $2; i++)); do items+=("$1$i:$(room "$1$i" "s/$1$i" X)"); done; fetch; git -C "$M" checkout -q main; }
specn() { bash "$TR" show 2>/dev/null | awk -v k="$1" '/^== train /{t=$3} t==k && /^SPEC=/{sub(/^SPEC=/,""); print}'; }
gatedn() { bash "$TR" show 2>/dev/null | awk -v k="$1" '/^== train /{t=$3} t==k && /^GATED=/{sub(/^GATED=/,""); print}'; }
shaof() { sed -n 's/^SHA=//p' "$1" 2>/dev/null | head -1; }

# 14a. Three trains built, none gating: pending names train 3 only, and plain
# `gate` gates train 3's tip here (a local SPEC, so wait/land/fail know it),
# against main, train 1's base.
fetch; git -C "$M" checkout -q main; m0="$(git -C "$M" rev-parse origin/main)"
cars ua 6; out="$(bash "$TR" build "${items[@]}" 2>&1)"
has "$out" "^TRAIN 3 .*n=2 gate=needed" "six cars build three trains of two"
t3="$(tipn 3)"
out="$(bash "$TR" pending)"
eq "$out" "GATE train 3 n=2 (full): train.sh gate --next" "pending names only the deepest train"
log3="$(bash "$TR" gate 2>/dev/null)"; rc=$?
[[ $rc -eq 0 && "$(shaof "$log3")" == "$t3" ]] && ok "plain gate gates the deepest train's tip" \
    || bad "plain gate gates the deepest train's tip (rc=$rc, sha $(shaof "$log3"))"
eq "$(specn 3)" "localbox - $log3 $log3" "a local gate of train 3 is recorded as a local SPEC"
[[ -z "$(gatedn 1)$(specn 1)$(specn 2)" ]] && ok "trains 1 and 2 are not gated" || bad "trains 1 and 2 are not gated"
has "$(cat "$log3")" "^GBASE=$m0$" "train 3's gate diffs against main, train 1's base"
sed -i '/^EXIT=/d' "$log3"                       # still running
eq "$(bash "$TR" pending)" "" "nothing is pending while the deepest train gates"
out="$(bash "$TR" gate 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "train 3 is already gating.*train.sh wait" "gate refuses while the deepest train gates" \
    || bad "gate refuses while the deepest train gates (rc=$rc)"
out="$(bash "$TR" gate 3 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "train 3 is already gating on localbox: train.sh wait $log3" "gate 3 refuses a train gating here" \
    || bad "gate 3 refuses a train gating here (rc=$rc)"
out="$(bash "$TR" gate --next 2>&1)"; rc=$?
[[ $rc -ne 0 && -z "$(specn 2)" ]] && has "$out" "already gating" "gate --next gates no shorter prefix while the deepest gates" \
    || bad "gate --next gates no shorter prefix while the deepest gates (rc=$rc)"
echo EXIT=0 >> "$log3"
out="$(bash "$TR" wait "$log3" 2>&1)"; rc=$?
[[ $rc -eq 0 ]] && ok "wait on the local gate of train 3" || bad "wait on the local gate of train 3 (rc=$rc)"
out="$(bash "$TR" land "$log3" 2>&1)"
[[ "$(grep -c '^MERGED' <<<"$out")" == 6 && "$(git -C "$M" rev-parse origin/main)" == "$t3" ]] \
    && ok "train 3's pass lands all six cars" || { bad "train 3's pass lands all six cars"; echo "$out" | sed 's/^/     | /'; }

# 14b. gate --next (a remote slot frees) also takes the deepest train.
fetch; git -C "$M" checkout -q main
cars ub 6; bash "$TR" build "${items[@]}" >/dev/null 2>&1; t3="$(tipn 3)"
l3="$(bash "$TR" gate --next 2>/dev/null)"
[[ "$(specn 3 | cut -d' ' -f1)" == hostx && -z "$(specn 2)" && "$(oref "${t3:0:12}")" == "$t3" ]] \
    && ok "gate --next gates the deepest train on the free host" \
    || bad "gate --next gates the deepest train on the free host (2: '$(specn 2)', 3: '$(specn 3)')"
bash "$TR" wait "$l3" >/dev/null 2>&1
out="$(bash "$TR" land "$l3" 2>&1)"; has "$out" "^MERGED +ub1 " "its pass lands train 1 too"

# 14c. A KEPT-only deepest train covers the train below it: it is the one
# to gate (and, since #4580, needs a gate itself).
fetch; git -C "$M" checkout -q main
two uc s/uc; bash "$TR" build "uc1:$c1" "uc2:$c2" >/dev/null 2>&1
k1="$(room uc3 s/uc3 X "$(tipn 1)")"; fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build --next "uc3:$k1" 2>&1)"
has "$out" "^TRAIN 2 .*n=1 gate=needed" "a car on train 1's tail is a KEPT train 2 that needs a gate"
eq "$(bash "$TR" pending)" "GATE train 2 n=1 (no new car for 0s): train.sh gate --next" \
    "the KEPT deepest train over a needed one is the one to gate"
log="$(bash "$TR" gate 2>/dev/null)"
[[ "$(shaof "$log")" == "$(tipn 2)" ]] && ok "gate gates it" || bad "gate gates it"
out="$(bash "$TR" land "$log" 2>&1)"; has "$out" "^MERGED +uc3 " "and its pass lands both"

# 14d. Bisect a red deeper gate with shorter prefixes: 4 trains, train 4 red
# -> gate train 2 (half); it passes and lands -> the red train is train 2 ->
# gate train 1; it is red with nothing below -> fail it.
fetch; git -C "$M" checkout -q main
cars ud 8; bash "$TR" build "${items[@]}" >/dev/null 2>&1
t2="$(tipn 2)"
log4="$(RZ_FAKE_EXIT=1 bash "$TR" gate 2>/dev/null)"
eq "$(bash "$TR" pending)" "GATE train 2 n=2 (bisect red train 4): train.sh gate --next" \
    "a red train 4 bisects: gate train 2"
log2="$(bash "$TR" gate --next 2>/dev/null)"
[[ "$(specn 2 | cut -d' ' -f1)" == hostx ]] && ok "gate --next gates the bisect prefix" \
    || bad "gate --next gates the bisect prefix (2: '$(specn 2)')"
eq "$(bash "$TR" pending)" "" "nothing more is pending while the bisect prefix gates"
bash "$TR" wait "$log2" >/dev/null 2>&1
out="$(bash "$TR" land "$log2" 2>&1)"
[[ "$(git -C "$M" rev-parse origin/main)" == "$t2" ]] && ok "the green prefix lands" || bad "the green prefix lands"
eq "$(bash "$TR" pending)" "GATE train 1 n=2 (bisect red train 2): train.sh gate --next" \
    "the red train is now train 2: gate train 1"
log1="$(RZ_FAKE_EXIT=1 bash "$TR" gate 2>/dev/null)"
[[ -n "$(gatedn 1)" && -z "$(specn 1)" ]] && ok "plain gate gates train 1 as before (GATED=)" \
    || bad "plain gate gates train 1 as before (GATED=)"
eq "$(bash "$TR" pending)" "FAIL train 1 n=2 (red, nothing below to bisect): train.sh fail $log1" \
    "a red train 1 is failed, not bisected further"
out="$(bash "$TR" gate 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "train.sh fail" "plain gate refuses a red train with nothing to bisect" \
    || bad "plain gate refuses a red train with nothing to bisect (rc=$rc)"
out="$(bash "$TR" fail "$log1" 2>&1)"
has "$out" "^HELD +ud5 " "fail holds the culprit train's cars"
has "$out" "^TRAIN 1 .*n=2 gate=needed" "the train above it is restacked on main"
eq "$(bash "$TR" pending)" "GATE train 1 n=2 (full): train.sh gate --next" "the restacked train gates"
bash "$TR" land "$(bash "$TR" gate)" >/dev/null 2>&1

# 14e. A green train below the red one: bisect only above it; train 3 red
# over a green train 2 (not landed yet) is failed, not bisected.
fetch; git -C "$M" checkout -q main
cars ue 6; bash "$TR" build "${items[@]}" >/dev/null 2>&1
l3="$(RZ_FAKE_EXIT=1 bash "$TR" gate 2>/dev/null)"
eq "$(bash "$TR" pending)" "GATE train 1 n=2 (bisect red train 3): train.sh gate --next" "a red train 3 bisects: gate train 1"
bash "$TR" gate 2 >/dev/null 2>&1
eq "$(bash "$TR" pending)" "FAIL train 3 n=2 (red, nothing below to bisect): train.sh fail $l3" \
    "a red train over a green one is failed"

# 14f. gate <k> gates train k here, whatever the rule says.
l1="$(bash "$TR" gate 1 2>/dev/null)"
[[ "$(shaof "$l1")" == "$(tipn 1)" && "$(gatedn 1)" == "$l1" ]] && ok "gate 1 gates train 1 here" || bad "gate 1 gates train 1 here"
out="$(bash "$TR" gate 9 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "no train 9" "gate <k> refuses a train that isn't built" || bad "gate <k> refuses a train that isn't built (rc=$rc)"
bash "$TR" land "$(specn 2 | cut -d' ' -f3)" >/dev/null 2>&1
bash "$TR" fail "$l3" >/dev/null 2>&1

# 14g. Trains that need no gate are never pending; a gate log for another
# SHA than the tip is no verdict of this train (it gates again, not FAIL).
# A lone KEPT car needs its gate (AGAST #4580); only a train with no car
# needs none.
fetch; git -C "$M" checkout -q main
k1="$(room uf1 s/uf1 X)"; fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build "uf1:$k1" 2>&1)"; has "$out" "gate=needed" "a lone KEPT car still needs a full gate"
has "$(bash "$TR" pending)" "^GATE train 1 n=1 " "a KEPT-only train is pending"
gland >/dev/null 2>&1
out="$(bash "$TR" build "uf1:$k1" 2>&1)"; has "$out" "n=0 gate=not-needed" "a train with no car needs no gate"
eq "$(bash "$TR" pending)" "" "a not-needed train is not pending"
out="$(bash "$TR" gate 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "no train needs a gate" "gate refuses when no train needs one" || bad "gate refuses when no train needs one (rc=$rc)"
two ug s/ug; bash "$TR" build "ug1:$c1" "ug2:$c2" >/dev/null 2>&1
l1="$(RZ_FAKE_EXIT=1 bash "$TR" gate 2>/dev/null)"
sed -i "s/^SHA=.*/SHA=$(git -C "$M" rev-parse origin/main)/" "$l1"
eq "$(bash "$TR" pending)" "GATE train 1 n=2 (full): train.sh gate --next" "a red log for another SHA is no verdict: the train gates again"
bash "$TR" land "$(bash "$TR" gate)" >/dev/null 2>&1

# 15. A malformed build item changes nothing (AGAST #4337).  `build --next
# ritz-task-4287 <sha>` (a space, not a colon) died with "bad item" only
# after build_on had discarded the replaced trains, removed RZ_TRAINS and
# started a new empty train in the free slot: trains 2-4, gating remotely,
# fell out of the queue.  Every item is checked before anything changes now.
# snap: RZ_TRAINS, every train worktree's HEAD and RZ_TRAIN, and `show`.
snap() {
    local d q; q="$(git -C "$M" rev-parse --path-format=absolute --git-common-dir)/RZ_TRAINS"
    echo "--- RZ_TRAINS"; cat "$q" 2>/dev/null || echo "(none)"
    for d in "$T"/train "$T"/train-*; do
        [[ -e "$d/.git" ]] || continue
        echo "--- $d $(git -C "$d" rev-parse HEAD)"
        cat "$(git -C "$d" rev-parse --absolute-git-dir)/RZ_TRAIN" 2>/dev/null || echo "(no state)"
    done
    echo "--- show"; bash "$TR" show 2>&1
}
same() {
    local after; after="$(snap)"
    [[ "$after" == "$1" ]] && ok "$2" || { bad "$2"; diff <(echo "$1") <(echo "$after") | sed 's/^/     | /'; }
}
fetch; git -C "$M" checkout -q main
cars va 6; bash "$TR" build "${items[@]}" >/dev/null 2>&1
# Train 1 gates here, trains 2 and 3 as local SPECs: build --next keeps all 3.
bash "$TR" gate 1 >/dev/null 2>&1; bash "$TR" gate 2 >/dev/null 2>&1; l3="$(bash "$TR" gate 3 2>/dev/null)"
[[ -n "$(gatedn 1)" && -n "$(specn 2)" && -n "$(specn 3)" ]] && ok "three trains gating" || bad "three trains gating"
c7="$(room va7 s/va7 X)"; fetch; git -C "$M" checkout -q main
before="$(snap)"
out="$(bash "$TR" build --next va7 "$c7" 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "bad item 'va7'" "build --next <branch> <sha> (a space) dies" || bad "build --next <branch> <sha> dies (rc=$rc)"
same "$before" "a malformed build --next item leaves every train, RZ_TRAINS and show as they were"
out="$(bash "$TR" build --next "va7:$c7" "va8" 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "bad item 'va8'" "a malformed item after a good one dies" || bad "a malformed item after a good one dies (rc=$rc)"
same "$before" "a malformed item after a good one changes nothing"
out="$(bash "$TR" build "va7:" 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "bad item 'va7:'" "plain build with an empty sha dies" || bad "plain build with an empty sha dies (rc=$rc)"
same "$before" "a malformed plain build changes nothing"
# A build that dies part-way (here: the free slot's tree can't be reset)
# leaves the kept trains in the queue, and nothing half-built in it.
if [[ -e "$T/train-4/.git" ]]; then lock="$(git -C "$T/train-4" rev-parse --absolute-git-dir)/index.lock"
else lock="$T/train-4"; fi
: > "$lock"
out="$(bash "$TR" build --next "va7:$c7" 2>&1)"; rc=$?
rm -f "$lock"
[[ $rc -ne 0 ]] && ok "a build that dies part-way fails" || bad "a build that dies part-way fails (rc=$rc)"
eq "$(bash "$TR" show 2>/dev/null | grep -c '^== train')" 3 "a build that dies part-way keeps the 3 gating trains queued"
[[ "$(specn 2)" == "$(echo "$before" | awk '/^== train 2/{t=1} t && /^SPEC=/{sub(/^SPEC=/,""); print; exit}')" && -n "$(specn 3)" ]] \
    && ok "their gates are untouched" || bad "their gates are untouched"
out="$(bash "$TR" land "$l3" 2>&1)"
[[ "$(grep -c '^MERGED' <<<"$out")" == 6 ]] && ok "the kept trains still land" || { bad "the kept trains still land"; echo "$out" | sed 's/^/     | /'; }
# Dying part-way after trains 2 and 3 (not gating) were replaced: the queue
# is train 1 alone, not a list naming slots with no state.
fetch; git -C "$M" checkout -q main
cars vb 6; bash "$TR" build "${items[@]}" >/dev/null 2>&1; l1="$(bash "$TR" gate 1 2>/dev/null)"
c7="$(room vb7 s/vb7 X)"; fetch; git -C "$M" checkout -q main
t1="$(snap | sed -n '/^--- .*\/train /,/^---/p')"
lock="$(git -C "$T/train-2" rev-parse --absolute-git-dir)/index.lock"; : > "$lock"
out="$(bash "$TR" build --next "vb7:$c7" 2>&1)"; rc=$?
rm -f "$lock"
[[ $rc -ne 0 ]] && has "$out" "stopped part-way.*1 kept" "a build dying after it replaced trains says so" || bad "a build dying after it replaced trains says so (rc=$rc)"
out="$(bash "$TR" show 2>&1)"; rc=$?
[[ $rc -eq 0 && "$(grep -c '^== train' <<<"$out")" == 1 ]] && ok "then show lists train 1 alone" || { bad "then show lists train 1 alone (rc=$rc)"; echo "$out" | sed 's/^/     | /'; }
eq "$(snap | sed -n '/^--- .*\/train /,/^---/p')" "$t1" "train 1 is untouched"
out="$(bash "$TR" land "$l1" 2>&1)"
[[ "$(grep -c '^MERGED' <<<"$out")" == 2 && -z "$(bash "$TR" show 2>/dev/null)" ]] && ok "train 1 lands, leaving no train" \
    || { bad "train 1 lands, leaving no train"; echo "$out" | sed 's/^/     | /'; }
# 16. The zero-slot queue write leaves an empty list, not no list (AGAST
# #4337).  land/fail write RZ_TRAINS before clearing trains 1..k's state, so a
# removed list lets queue()'s legacy fallback (slot 1 with an RZ_TRAIN)
# resurrect a train whose cleanup was interrupted.  The rm stub below fails at
# that first state removal, exactly where an interrupt would.
cat > "$T/bin/rm" <<'STUB'
#!/usr/bin/env bash
if [[ "${RZ_TEST_RM_FAIL_STATE:-0}" == 1 ]]; then
    for a in "$@"; do
        [[ "$a" == */RZ_TRAIN ]] && { echo "rm: cannot remove '$a' (test)" >&2; exit 1; }
    done
fi
exec /bin/rm "$@"
STUB
chmod +x "$T/bin/rm"
fetch; git -C "$M" checkout -q main
cars wc 6; bash "$TR" build "${items[@]}" >/dev/null 2>&1
eq "$(bash "$TR" show 2>/dev/null | grep -c '^== train')" 3 "three trains built"
l3="$(bash "$TR" gate 3 2>/dev/null)"
q="$(git -C "$M" rev-parse --path-format=absolute --git-common-dir)/RZ_TRAINS"
st1="$(git -C "$T/train" rev-parse --absolute-git-dir)/RZ_TRAIN"
out="$(RZ_TEST_RM_FAIL_STATE=1 bash "$TR" land "$l3" 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && ok "landing stops when clearing a train's state fails" \
    || bad "landing stops when clearing a train's state fails (rc=$rc)"
[[ -f "$st1" ]] && ok "slot 1's state survives, as after an interrupt" \
    || bad "slot 1's state survives, as after an interrupt"
[[ -f "$q" && ! -s "$q" ]] && ok "the queue is an empty list, not a removed one" \
    || bad "the queue is an empty list, not a removed one (file: $( [[ -e "$q" ]] && cat "$q" || echo absent ))"
[[ -z "$(bash "$TR" show 2>/dev/null)" ]] && ok "show lists no train" \
    || { bad "show lists no train"; bash "$TR" show 2>&1 | sed 's/^/     | /'; }
eq "$(bash "$TR" pending)" "" "nothing is pending"
out="$(bash "$TR" land 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "no train built" "a stale slot 1 is not a train" \
    || bad "a stale slot 1 is not a train (rc=$rc)"
# A list that never existed is still legacy slot 1 (a train built before
# stacking existed).
rm -f "$q"
eq "$(bash "$TR" show 2>/dev/null | grep -c '^== train')" 1 "an absent list is still legacy train 1"
rm -f "$st1"
# 17. Configurable depth and hosts, and every train's tail published (AGAST
# #4409; Aaron 2026-11-20).  DEPTH and HOSTS come from ~/.config/rz/host.env
# (RZ_HOST_ENV here), an environment variable wins, and the defaults are the
# 2026-11-20 policy: 6 trains in flight, and the live hosts only (no skronk).
gatecount() { bash "$TR" show 2>/dev/null | grep -cE '^(GATED|SPEC)='; }

# 17a. A plain build publishes train 1's tail, not only gate --next.
fetch; git -C "$M" checkout -q main
ta1="$(room ta1 s/ta1 X "$(git -C "$M" rev-parse origin/main~1)")"; fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build "ta1:$ta1" 2>&1)"
has "$out" "^TRAIN 1 .*n=1 gate=needed" "a one-car train 1 builds"
tip1="$(tipn 1)"
[[ "$(oref "${tip1:0:12}")" == "$tip1" ]] && ok "build publishes a train's tail (train 1, never gated)" \
    || bad "build publishes a train's tail (train 1, never gated)"

# 17b. A room based on that tail boards as KEPT: the new-room base rule.
tr="$(room ta_room s/ta_room X "$tip1")"; fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build --next "ta_room:$tr" 2>&1)"
has "$out" "^KEPT +ta_room ${tr:0:12}" "a room based on the deepest tail boards as KEPT"
t2="$(tipn 2)"
[[ "$(oref "${t2:0:12}")" == "$t2" ]] && ok "build publishes a stacked train's tail" \
    || bad "build publishes a stacked train's tail"

# 17c. The default host list is the 2026-11-20 policy: live hosts only.
touch "$T/ssh-down"
out="$(RZ_TRAIN_HOSTS= RZ_HOST_ENV="$T/no-host.env" bash "$TR" gate --next 2>&1)"; rc=$?
rm -f "$T/ssh-down"
[[ $rc -ne 0 ]] && has "$out" "no host in RZ_TRAIN_HOSTS \(omegalisk huburght bangerang starbux toffee chungus\)" \
    "the default host list is the 2026-11-20 policy, with no skronk" \
    || { bad "the default host list is the 2026-11-20 policy (rc=$rc)"; echo "$out" | sed 's/^/     | /'; }

# 17d. host.env supplies DEPTH and HOSTS, with no environment variable set.
printf 'RZ_TRAIN_DEPTH=2\nRZ_TRAIN_HOSTS=hosty\n' > "$T/host-train.env"
fetch; git -C "$M" checkout -q main
cars td1 1; bash "$TR" build "${items[@]}" >/dev/null 2>&1
log1="$(bash "$TR" gate 1)"
cars td2 1; bash "$TR" build --next "${items[@]}" >/dev/null 2>&1
l2="$(RZ_TRAIN_HOSTS= RZ_TRAIN_DEPTH= RZ_HOST_ENV="$T/host-train.env" bash "$TR" gate --next 2>"$T/err")"; rc=$?
[[ $rc -eq 0 && "$(specn 2 | cut -d' ' -f1)" == hosty ]] \
    && ok "host.env supplies RZ_TRAIN_HOSTS (hosty, not the exported default)" \
    || { bad "host.env supplies RZ_TRAIN_HOSTS (rc=$rc, spec: $(specn 2))"; sed 's/^/     | /' "$T/err"; }
cars td3 1; bash "$TR" build --next "${items[@]}" >/dev/null 2>&1
out="$(RZ_TRAIN_HOSTS= RZ_TRAIN_DEPTH= RZ_HOST_ENV="$T/host-train.env" bash "$TR" gate --next 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "2 trains in flight already \(at most 2" "host.env supplies RZ_TRAIN_DEPTH (2)" \
    || { bad "host.env supplies RZ_TRAIN_DEPTH (rc=$rc)"; echo "$out" | sed 's/^/     | /'; }
bash "$TR" wait "$l2" >/dev/null 2>&1; bash "$TR" land "$l2" >/dev/null 2>&1

# 17e. Bad values are refused, by host.env and by the environment.
printf 'RZ_TRAIN_DEPTH=0\n' > "$T/host-bad-depth.env"
out="$(RZ_HOST_ENV="$T/host-bad-depth.env" bash "$TR" show 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "RZ_TRAIN_DEPTH must be a whole number >= 1: '0'" \
    "host.env rejects a bad RZ_TRAIN_DEPTH" || bad "host.env rejects a bad RZ_TRAIN_DEPTH (rc=$rc)"
printf 'RZ_TRAIN_HOSTS=\n' > "$T/host-bad-hosts.env"
out="$(RZ_HOST_ENV="$T/host-bad-hosts.env" bash "$TR" show 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "RZ_TRAIN_HOSTS must be a space-separated host list" \
    "host.env rejects an empty RZ_TRAIN_HOSTS" || bad "host.env rejects an empty RZ_TRAIN_HOSTS (rc=$rc)"
out="$(RZ_TRAIN_DEPTH=0 bash "$TR" show 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "RZ_TRAIN_DEPTH must be a whole number >= 1" \
    "the environment's RZ_TRAIN_DEPTH is validated too" || bad "the environment's RZ_TRAIN_DEPTH is validated too (rc=$rc)"

# 17f. The default depth is 6: six trains in flight, a seventh refused.
fetch; git -C "$M" checkout -q main
cars tf1 1; bash "$TR" build "${items[@]}" >/dev/null 2>&1
log1="$(bash "$TR" gate 1)"
logs=(); tips=()
for i in 2 3 4 5 6; do
    cars "tf$i" 1; bash "$TR" build --next "${items[@]}" >/dev/null 2>&1
    logs+=("$(bash "$TR" gate --next 2>/dev/null)")
    tips+=("$(tipn "$i")")
done
eq "$(gatecount)" 6 "the default depth (6) lets six trains be in flight"
log6="${logs[4]}"; t6="${tips[4]}"
cars tf7 1; bash "$TR" build --next "${items[@]}" >/dev/null 2>&1
out="$(bash "$TR" gate --next 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "6 trains in flight already \(at most 6" \
    "a seventh train is refused at the default depth (6)" \
    || { bad "a seventh train is refused at the default depth (6) (rc=$rc)"; echo "$out" | sed 's/^/     | /'; }
bash "$TR" wait "$log6" >/dev/null 2>&1
out="$(bash "$TR" land "$log6" 2>&1)"
[[ "$(grep -c '^MERGED' <<<"$out")" == 6 && "$(git -C "$M" rev-parse origin/main)" == "$t6" ]] \
    && ok "a pass of train 6 lands all six trains" || { bad "a pass of train 6 lands all six trains"; echo "$out" | sed 's/^/     | /'; }
[[ -z "$(oref "${tips[0]:0:12}")$(oref "${tips[2]:0:12}")$(oref "${t6:0:12}")" ]] \
    && ok "landing deletes the published tails" || bad "landing deletes the published tails"

# 18. Preemptive rebase advisory (AGAST #4413).  `tail` names the deepest
# built train's published tail, never a discarded one.  `rebase-plan` is one
# loop turn: it compares each running room's base (fed in, so a local and a
# remote room alike) to that tail, SKIPs a room mid-gate with the reason, and
# prints exactly one rebase message for a room that must move.  It moves
# nothing itself: no branch, no worktree.
export RZ_TRAIN_MAX=8 RZ_TRAIN_DEBOUNCE=0
# 17f left its seventh train in flight: the build succeeds and it is the gate
# that refuses past the depth.  Drop it so these tests start from no train.
lg7="$(RZ_FAKE_EXIT=1 bash "$TR" gate 2>/dev/null)" || true
[[ -n "$lg7" ]] && bash "$TR" fail "$lg7" >/dev/null 2>&1 || true
tail1() { bash "$TR" tail | awk '{print $1}'; }

# 18a. No train built: tail prints nothing (not a stale TIP=).
fetch; git -C "$M" checkout -q main
eq "$(bash "$TR" tail)" "" "tail prints nothing when no train is built"

# 18b. A built train: tail is its published tip.
za="$(room za s/za ZA)"; fetch; git -C "$M" checkout -q main
bash "$TR" build "za:$za" >/dev/null 2>&1
t1="$(tipn 1)"; p1="${t1:0:12}"
[[ "$(tail1)" == "$p1" && "$(oref "$p1")" == "$(git -C "$T/train" rev-parse HEAD)" ]] \
    && ok "tail names the built train's published tip" || bad "tail names the built train's published tip"
eq "$(bash "$TR" tail)" "$p1 rz-train/$p1" "tail prints '<tip12> rz-train/<tip12>'"

# 18c. Two trains: the deepest is the tail.
zb="$(room zb s/zb ZB)"; fetch; git -C "$M" checkout -q main
bash "$TR" build --next "zb:$zb" >/dev/null 2>&1
t2="$(tipn 2)"; p2="${t2:0:12}"
eq "$(tail1)" "$p2" "tail is the deepest of two trains"

# 18d. A discarded tail is never reported: the ref is the truth, not TIP=.
git -C "$M" push -q origin --delete "refs/heads/rz-train/$p2"
eq "$(tail1)" "$p1" "tail falls back past a train whose tail ref was discarded"
git -C "$M" push -q origin --delete "refs/heads/rz-train/$p1"
eq "$(bash "$TR" tail)" "" "tail prints nothing when every tail ref is gone"
# Restore the two trains (same cars on the same tail give the same tips).
bash "$TR" build "za:$za" >/dev/null 2>&1; bash "$TR" build --next "zb:$zb" >/dev/null 2>&1
eq "$(tail1)" "$p2" "a rebuilt train republishes its tail"

# 18e. A failed train names the tail a room based on it must leave (AGAST
# #4413 point 5): the room may carry cars that no newer tail holds.
log="$(RZ_FAKE_EXIT=1 bash "$TR" gate 2>/dev/null)"
out="$(bash "$TR" fail "$log" 2>&1)"
has "$out" "^DROPPED +tail $p2 " "fail names the tail a room based on it must rebase from"
eq "$(tail1)" "$p1" "after the fail the deepest built tail is train 1's"

# 18f. One loop turn: each room's base vs the tail, a gating room skipped with
# the reason, and exactly one rebase message for a room that must move.
main="$(git -C "$M" rev-parse origin/main)"; m12="${main:0:12}"
mkdir -p "$RZ_TEST_ACTIVE"; touch "$RZ_TEST_ACTIVE/ritz-gate-zloc"
out="$(printf 'zon %s idle\nzmain %s idle\nzloc %s\nzrem %s gating\n' \
    "$p1" "$m12" "$m12" "$m12" | bash "$TR" rebase-plan)"
rm -f "$RZ_TEST_ACTIVE/ritz-gate-zloc"
has "$out" "^ROOM zon base=$p1 tail=$p1 on-tail$" "a room on the tail is on-tail"
! grep -q '^REBASE zon' <<<"$out" && ok "a room on the tail is not messaged" || bad "a room on the tail is not messaged"
has "$out" "^ROOM zmain base=$m12 tail=$p1 behind$" "a room behind the tail says so"
has "$out" "^REBASE zmain onto $p1: rebase onto $p1: .git fetch origin rz-train/$p1 && git rebase FETCH_HEAD" \
    "a room behind the tail gets one rebase message"
[[ "$(grep -c '^REBASE zmain' <<<"$out")" == 1 ]] && ok "exactly one rebase message per room" \
    || bad "exactly one rebase message per room"
has "$out" "^SKIP zloc: gate live \(ritz-gate-zloc is active\); not rebasing mid-gate" \
    "a room mid-gate here is skipped with the local reason"
has "$out" "^SKIP zrem: gate live \(host STATUS\); not rebasing mid-gate" \
    "a remote room mid-gate (fed from its host) is skipped with that reason"
! grep -q '^REBASE zloc\|^REBASE zrem' <<<"$out" && ok "a gating room is never told to rebase" \
    || bad "a gating room is never told to rebase"
[[ "$(grep -c '^REBASE' <<<"$out")" == 1 ]] && ok "only the non-gating behind room gets a message" \
    || bad "only the non-gating behind room gets a message ($(grep -c '^REBASE' <<<"$out"))"

# 18g. An unknown base is listed, never messaged.
out="$(printf 'zunk - idle\n' | bash "$TR" rebase-plan)"
has "$out" "^ROOM zunk base=. tail=$p1 unknown$" "an unknown base is listed as unknown"
! grep -q '^REBASE zunk' <<<"$out" && ok "an unknown base gets no rebase message" || bad "an unknown base gets no rebase message"

# 18h. No train built: main is the reference (a room on main is on-tail).
gland >/dev/null 2>&1   # train 1's car is KEPT; it still gates (#4580)
eq "$(bash "$TR" tail)" "" "tail prints nothing once the trains land"
main="$(git -C "$M" rev-parse origin/main)"; m12="${main:0:12}"
older="$(git -C "$M" rev-parse origin/main~1)"; o12="${older:0:12}"
out="$(printf 'zmain %s idle\nzold %s idle\n' "$m12" "$o12" | bash "$TR" rebase-plan)"
has "$out" "^ROOM zmain base=$m12 tail=main on-tail$" "with no train, a room on main is on-tail"
has "$out" "^REBASE zold onto main: rebase onto main: .git fetch origin && git rebase FETCH_HEAD" \
    "with no train, a room off main is told to rebase onto main"

# 18i. A discarded/failed train's tail: a room based on it is bounced onto the
# new tail or main even when no newer tail carries its cars (AGAST #4413
# point 5).  The caller feeds the merge-base against the dropped tail.
zc="$(room zc s/zc ZC)"; fetch; git -C "$M" checkout -q main
bash "$TR" build "zc:$zc" >/dev/null 2>&1
drop="$(tail1)"; main="$(git -C "$M" rev-parse origin/main)"; m12="${main:0:12}"
git -C "$M" push -q origin --delete "refs/heads/rz-train/$drop"
out="$(printf 'zdrop %s idle\nzother %s idle\n' "$drop" "$m12" | bash "$TR" rebase-plan --dropped "$drop")"
has "$out" "^ROOM zdrop base=$drop tail=main dropped$" "a room on the dropped tail is named dropped"
has "$out" "^BOUNCE zdrop onto main: rebase onto main: .git fetch origin && git rebase FETCH_HEAD" \
    "a room on the dropped tail is bounced onto main"
has "$out" "^ROOM zother base=$m12 tail=main other$" "a room not on the dropped tail is left alone"
! grep -q '^BOUNCE zother' <<<"$out" && ok "a room not on the dropped tail is not bounced" \
    || bad "a room not on the dropped tail is not bounced"
out="$(printf 'zdrop2 %s gating\n' "$drop" | bash "$TR" rebase-plan --dropped "$drop")"
has "$out" "^SKIP zdrop2: gate live \(host STATUS\); not rebasing mid-gate" \
    "a room on a dropped tail but mid-gate is skipped, not rewound"
! grep -q '^BOUNCE zdrop2' <<<"$out" && ok "a gating room is never bounced" || bad "a gating room is never bounced"

# 19. Coordinator-tooling defects from the rz loop, 2026-11-22.
# 19a. #4525: `gate --next` prints the local copy of a remote gate's log, and
# the operator may paste it relative to the repo root.  The SPEC records it
# absolutely, so `wait` must normalise before deciding no train owns it.
fetch; git -C "$M" checkout -q main
gland >/dev/null 2>&1; rm -f "$RES"
two wa s/wa; bash "$TR" build "wa1:$c1" "wa2:$c2" >/dev/null 2>&1
llog="$(bash "$TR" gate --next hostx 2>/dev/null)"
bash "$TR" wait "$llog" >/dev/null 2>&1
rel="${llog#"$T"/}"
out="$(cd "$T" && bash "$TR" wait "$rel" 2>&1)"; rc=$?
[[ $rc -eq 0 ]] \
    && ok "wait finds the train given its remote log as a relative path (#4525)" \
    || { bad "wait finds the train given its remote log as a relative path (#4525) (rc=$rc)"; echo "$out" | sed 's/^/     | /'; }
bash "$TR" land "$llog" >/dev/null 2>&1; rm -f "$RES"
# The refusal half: a log no train owns is still refused, and the exit code is
# 1, not 0 (a caller's pipeline can mask this; check it cleanly).
out="$(cd "$T" && bash "$TR" wait gates/train-000000000000-1@hostx.log 2>&1)"; rc=$?
[[ $rc -eq 1 ]] && has "$out" "discarded by a rebuild" "wait refuses an unknown remote log with exit 1 (#4525)" \
    || bad "wait refuses an unknown remote log with exit 1 (#4525) (rc=$rc)"

# 19b. #4526: after `land` reserves the local slot, a next gate dispatched to a
# remote host releases it at once: no train gate is coming here, so the slot
# belongs to room gates.
fetch; git -C "$M" checkout -q main
s="$(room wr s/wr WR)"; fetch; git -C "$M" checkout -q main
rm -f "$RES"; bash "$TR" build "wr:$s" >/dev/null 2>&1
gland >/dev/null 2>&1
[[ -e "$RES" ]] && ok "land writes .train-reserved before the next gate" \
    || bad "land writes .train-reserved before the next gate"
two wb s/wb; bash "$TR" build "wb1:$c1" "wb2:$c2" >/dev/null 2>&1
llog="$(bash "$TR" gate --next hostx 2>/dev/null)"; rc=$?
[[ $rc -eq 0 && ! -e "$RES" ]] \
    && ok "a remote next gate releases land's local reservation (#4526)" \
    || { bad "a remote next gate releases land's local reservation (#4526) (rc=$rc, reserved: $( [[ -e "$RES" ]] && echo yes || echo no ))"; }
bash "$TR" wait "$llog" >/dev/null 2>&1; bash "$TR" land "$llog" >/dev/null 2>&1; rm -f "$RES"
# The local fallback is the case the reservation exists for: with no remote
# host free, the gate runs here and the reservation must survive.
fetch; git -C "$M" checkout -q main
s="$(room ws s/ws WS)"; fetch; git -C "$M" checkout -q main
rm -f "$RES"; bash "$TR" build "ws:$s" >/dev/null 2>&1
gland >/dev/null 2>&1
[[ -e "$RES" ]] && ok "land writes .train-reserved for the local fallback too" \
    || bad "land writes .train-reserved for the local fallback too"
two wl s/wl; bash "$TR" build "wl1:$c1" "wl2:$c2" >/dev/null 2>&1
wl_tip="$(bash "$TR" show 2>/dev/null | sed -n 's/^TIP=//p' | head -1)"
printf 'RZ_GATE_SLOTS=1\nRZ_TRAIN_SLOTS=1\n' > "$T/host-hostx.env"
mkdir -p "$T/gates-hostx"
exec 8>>"$T/gates-hostx/.gate-slot-0"; flock -n 8
wl="$(bash "$TR" gate --next 2>"$T/err")"; rc=$?
exec 8>&-; rm -f "$T/host-hostx.env"
[[ $rc -eq 0 && -e "$RES" ]] \
    && ok "a local fallback gate keeps land's reservation (#4526)" \
    || { bad "a local fallback gate keeps land's reservation (#4526) (rc=$rc, reserved: $( [[ -e "$RES" ]] && echo yes || echo no ))"; sed 's/^/     | /' "$T/err"; }
has "$(cat "$wl" 2>/dev/null)" "^SHA=$wl_tip$" "the local fallback ran the train"
lout="$(bash "$TR" land "$wl" 2>&1)"
has "$lout" "^MERGED " "the local fallback verdict lands"
rm -f "$RES"

# 20. A clean rebase skips the room gate; the train gate covers it (AGAST
# #4580, Aaron 2026-11-23).  A room REAPs commit X, gated on main, then
# rebases it cleanly onto a train tail and force-pushes X' without
# re-gating or re-REAPing.  rz boards the original REAP: X' is accepted
# because its patch matches X, and it is APPLIED, never KEPT, so a train
# gate is always what tests it.
fetch; git -C "$M" checkout -q main
gland >/dev/null 2>&1; rm -f "$RES"
ry="$(room ry s/ry RY)"; rx="$(room rx s/rx RX)"; fetch; git -C "$M" checkout -q main
bash "$TR" build "ry:$ry" >/dev/null 2>&1
ty="$(tipn 1)"
# rx rebases onto train 1's tail with no conflict and pushes, no new REAP.
rx2="$(room rx s/rx RX "$ty")"; fetch; git -C "$M" checkout -q main
[[ "$rx2" != "$rx" && "$(git -C "$M" rev-parse "$rx2^")" == "$ty" ]] \
    && ok "setup: rx's rebased commit sits on train 1's tail" || bad "setup: rx's rebased commit sits on train 1's tail"
out="$(bash "$TR" build --next "rx:$rx" 2>&1)"
has "$out" "^APPLIED +rx ${rx:0:12} as " "a cleanly rebased, ungated car boards on its original REAP as APPLIED"
! grep -q "^KEPT +rx\|^BAD +rx" <<<"$out" && ok "the rebased car is neither KEPT nor BAD" \
    || { bad "the rebased car is neither KEPT nor BAD"; echo "$out" | sed 's/^/     | /'; }
has "$out" "^TRAIN 2 .*n=1 gate=needed" "the train holding a rebased, ungated car needs its gate"
# Rebuilt from scratch, X' sits right on train 1's tail: still APPLIED.
out="$(bash "$TR" build "ry:$ry" "rx:$rx" 2>&1)"
has "$out" "^APPLIED +rx ${rx:0:12} as " "a rebased car on the tail is APPLIED, not KEPT"
has "$out" "^TRAIN 1 .*n=2 gate=needed" "its own gate never ran on that tree: the train gates"
# The rebased car's REAP may also name X' itself, as before: KEPT then.
out="$(bash "$TR" build "ry:$ry" "rx:$rx2" 2>&1)"
has "$out" "^KEPT +rx ${rx2:0:12}" "a REAP naming the rebased SHA on the tail is still KEPT"

# 20b. The room changed code to fit (a different patch): the old REAP is BAD.
git -C "$M" checkout -q --detach "$ty"
echo "RX changed" > "$M/s/rx"; git -C "$M" add -A; git -C "$M" commit -qm "rx: change s/rx"
git -C "$M" push -q -f origin HEAD:refs/heads/rx; fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build "ry:$ry" "rx:$rx" 2>&1)"
has "$out" "^BAD +rx ${rx:0:12}: origin/rx is not this commit" \
    "a rebase that changed the patch needs a new gate and REAP: the old REAP is BAD"

# 20c. rebase-plan no longer asks for a re-gate on a clean rebase.
main="$(git -C "$M" rev-parse origin/main)"; m12="${main:0:12}"
older="$(git -C "$M" rev-parse origin/main~1)"; o12="${older:0:12}"
out="$(printf 'zold %s idle\n' "$o12" | bash "$TR" rebase-plan "$main")"
has "$out" "^REBASE zold onto main: .*clean: push it, no re-check and no new REAP" \
    "a clean rebase is told to push without re-gating"
has "$out" "^REBASE zold onto main: .*conflicted or changed code: resolve, re-check \(smoke-plan.sh run\) and REAP" \
    "a conflicted rebase still re-gates and REAPs"

# 20d. A room gate on a train tail is that train's gate (AGAST #4580 item 7):
# a room based on train 1's tail boards train 2 KEPT, and its own log
# (SHA = train 2's tip, EXIT=0) lands trains 1 and 2 with no train gate.
bash "$TR" build "ry:$ry" >/dev/null 2>&1; ty="$(tipn 1)"
rz7="$(room rz7 s/rz7 RZ7 "$ty")"; fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build --next "rz7:$rz7" 2>&1)"
has "$out" "^KEPT +rz7 ${rz7:0:12}" "a room gated on train 1's tail boards KEPT"
rlog="$T/gate-room-rz7.log"; printf 'SHA=%s\nEXIT=0\n' "$rz7" > "$rlog"
out="$(bash "$TR" land "$rlog" 2>&1)"
has "$out" "^MERGED +ry " "the room's log lands train 1 too"
has "$out" "^MERGED +rz7 ${rz7:0:12} as ${rz7:0:12}" "the room's log lands its own train"
rm -f "$RES"

unset RZ_TRAIN_DEBOUNCE; export RZ_TRAIN_MAX=8

# 21. A host whose venv misses a pin of the train tip's requirements.lock is
# a skipped host, not a red train (AGAST #4583).  hostx's venv has rzfake-b
# at the wrong version and no rzfake-missing; hosty's matches (rzfake_a is
# rzfake-a, PEP 503).  This host's real python3 has none of them.
fakedist() {   # fakedist <site> <name> <version>
    mkdir -p "$1/$2-$3.dist-info"
    printf 'Metadata-Version: 2.1\nName: %s\nVersion: %s\n' "$2" "$3" > "$1/$2-$3.dist-info/METADATA"
}
fakedist "$T/rsite-hostx" rzfake-a 1.0; fakedist "$T/rsite-hostx" rzfake-b 1.9
fakedist "$T/rsite-hosty" rzfake_a 1.0; fakedist "$T/rsite-hosty" rzfake-b 2.0; fakedist "$T/rsite-hosty" rzfake-missing 1.0
rm -f "$T"/host-host[xy].env; export RZ_TRAIN_HOSTS="localbox hostx hosty"
fetch; git -C "$M" checkout -q main
lk="$(room vl1 projects/ritz/requirements.lock "$(printf '# pins\nrzfake-a==1.0\nrzfake-b==2.0  # x\n\nrzfake-missing==1.0')")"
v2="$(room vl2 s/vl2 X)"; fetch; git -C "$M" checkout -q main
bash "$TR" build "vl1:$lk" "vl2:$v2" >"$T/out21" 2>&1 \
    || { bad "section 21's train builds"; sed 's/^/     | /' "$T/out21"; bash "$TR" show | sed 's/^/     | /'; }
tv="$(tipn 1)"
l21="$(bash "$TR" gate --next 2>"$T/err")"
[[ "$(specof | cut -d' ' -f1)" == hosty ]] && ok "gate --next skips a host whose venv misses a lock pin" \
    || { bad "gate --next skips a host whose venv misses a lock pin (spec: $(specof))"; sed 's/^/     | /' "$T/err"; }
has "$(cat "$T/err")" "^note: hostx: stale venv: rzfake-b==2.0 \(installed 1.9\) rzfake-missing==1.0 \(not installed\)$" \
    "it names the host and every pin it misses"
has "$(sed -n 's/^hostx bash -l -s -- free //p' "$T/ssh-log" | tail -1)" "^rzfake-a==1.0 rzfake-b==2.0 rzfake-missing==1.0 *$" \
    "free is sent the train tip's pins, comments dropped"
bash "$TR" discard >/dev/null 2>&1
# A host named outright: start checks out the tip, then refuses.  (hosty's
# gate above wrote the fake gate's log for this tip.)
rm -f "$T/gate-${tv:0:12}.log"
out="$(bash "$TR" gate --next hostx 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "stale venv: .*does not match the train tip.s requirements.lock: rzfake-b==2.0 \(installed 1.9\)" \
    "start refuses a named host whose venv misses a pin" \
    || bad "start refuses a named host whose venv misses a pin (rc=$rc)"
has "$out" "pip install -r projects/ritz/requirements.lock" "the refusal says how to fix the venv"
[[ ! -e "$T/gate-${tv:0:12}.log" && -z "$(specof)" && -z "$(oref "${tv:0:12}")" ]] \
    && ok "the stale-venv refusal starts no gate and leaves no SPEC or ref" \
    || bad "the stale-venv refusal starts no gate and leaves no SPEC or ref"
# Every remote host stale: train 1 falls back here, after saying why.
rm -rf "$T/rsite-hosty/rzfake-b-2.0.dist-info"
l21="$(bash "$TR" gate --next 2>"$T/err")"; rc=$?
grep -q "^note: hostx: stale venv" "$T/err" && grep -q "^note: hosty: stale venv: rzfake-b==2.0 (not installed)" "$T/err" \
    && ok "each stale host is passed over by name" || { bad "each stale host is passed over by name"; sed 's/^/     | /' "$T/err"; }
[[ $rc -eq 0 && "$l21" != *@* ]] && ok "with no host left, train 1 gates here" \
    || bad "with no host left, train 1 gates here (rc=$rc, '$l21')"
# Train 2 may gate here too: this host's own venv is checked as well, so a
# stale one here is passed over like any other (hosty synced again).
fakedist "$T/rsite-hosty" rzfake-b 2.0
v3="$(room vl3 s/vl3 X "$(tipn 1)")"; fetch; git -C "$M" checkout -q main
bash "$TR" build --next "vl3:$v3" >/dev/null 2>&1
l21="$(bash "$TR" gate --next 2>"$T/err")"
[[ "$(specof | cut -d' ' -f1)" == hosty ]] && grep -q "^note: localbox: stale venv: rzfake-a==1.0 (not installed)" "$T/err" \
    && ok "a stale venv on this host is passed over too" \
    || { bad "a stale venv on this host is passed over too (spec: $(specof))"; sed 's/^/     | /' "$T/err"; }
# 22. precheck (AGAST #4672): the guards and ratchets on a train's tip, in its
# worktree, under ritz-gate.slice, before it spends a gate slot (SKILL.md
# Reaping step 3b).  RZ_PRECHECK_CMD stands in for `make -C projects/ritz
# tools-ratchets`; the systemd-run stub above runs it in the foreground.
bash "$TR" discard >/dev/null 2>&1
unset RZ_TRAIN_HOSTS
cat > "$T/precheck.sh" <<'PRE'
#!/usr/bin/env bash
pwd -P > "$RZ_TEST_DIR/precheck-wd"
echo "=== Running tools/ source-reading ratchets"
echo "noise that is not a failure"
if [[ "${RZ_FAKE_PRECHECK:-0}" != 0 ]]; then
    echo "FAILED tools/test_standard_callers.py::test_raw_api_callers_only_go_down - AssertionError"
    echo "ERROR tests/test_x.py::test_y - ImportError"
    echo "make[1]: *** [Makefile:130: tools-ratchets-tools] Error 1"
    echo "1 failed, 457 passed in 9.1s"
    # AGAST #4904: suite-count's breach, as check_suite_count.py prints it.
    echo "test budget: 1 breach(es), collected in 9.9 s (test_budget.toml):"
    echo "  suite: 26801 tests over its cap of 26800; collapse a matrix into table rows before adding cases"
fi
exit "${RZ_FAKE_PRECHECK:-0}"
PRE
chmod +x "$T/precheck.sh"
export RZ_PRECHECK_CMD="$T/precheck.sh"
fetch; git -C "$M" checkout -q main
p1="$(room pc1 s/pc1 P1)"; p2="$(room pc2 s/pc2 P2)"; fetch; git -C "$M" checkout -q main
bash "$TR" build "pc1:$p1" "pc2:$p2" >/dev/null 2>&1
tp="$(tipn 1)"; : > "$T/systemd-run-log"

# 22a. A green tip: one line, exit 0, recorded, run in the train's worktree
# under the gate slice.
out="$(bash "$TR" precheck 2>&1)"; rc=$?
eq "$out" "PRECHECK train 1 tip=${tp:0:12} EXIT=0" "precheck prints PRECHECK train <k> tip=<12> EXIT=<n>"
eq "$rc" 0 "a green precheck exits 0"
eq "$(cat "$T/precheck-wd" 2>/dev/null)" "$(cd "$T/train" && pwd -P)" "the precheck runs in the train's worktree"
has "$(cat "$T/systemd-run-log")" "(^| )--slice=ritz-gate\.slice( |$)" "the precheck runs under ritz-gate.slice"
has "$(cat "$T/systemd-run-log")" "(^| )--wait( |$)" "systemd-run waits for the precheck's verdict"
eq "$(bash "$TR" show | sed -n 's/^PRECHECK=//p')" "$tp 0" "the train state records PRECHECK=<tip> <exit>"

# 22b. A red tip: the verdict, then only the failing lines; exit non-zero.
out="$(RZ_FAKE_PRECHECK=1 bash "$TR" precheck 1 2>&1)"; rc=$?
has "$out" "^PRECHECK train 1 tip=${tp:0:12} EXIT=1$" "a red precheck says EXIT=1"
has "$out" "^FAILED tools/test_standard_callers.py::test_raw_api_callers_only_go_down" "it prints the FAILED lines"
has "$out" "^ERROR tests/test_x.py::test_y" "and the ERROR lines"
has "$out" "^  suite: 26801 tests over its cap of 26800; " "and the test-count cap line (AGAST #4904)"
! grep -q "noise\|^===" <<<"$out" && ok "and nothing else of the run" || { bad "and nothing else of the run"; sed 's/^/     | /' <<<"$out"; }
has "$out" "log: .*precheck" "it names the full log"
[[ $rc -ne 0 ]] && ok "a red precheck exits non-zero" || bad "a red precheck exits non-zero"
eq "$(bash "$TR" show | sed -n 's/^PRECHECK=//p' | tail -1)" "$tp 1" "the red verdict is recorded too (last one wins)"

# 22c. No <k>: the train `pending` would gate (pick_target): the deepest.
q1="$(room pc3 s/pc3 P3 "$tp")"; fetch; git -C "$M" checkout -q main
bash "$TR" build --next "pc3:$q1" >/dev/null 2>&1
tp2="$(tipn 2)"
out="$(bash "$TR" precheck 2>&1)"
eq "$out" "PRECHECK train 2 tip=${tp2:0:12} EXIT=0" "precheck with no <k> takes the train pending would gate"
eq "$(cat "$T/precheck-wd")" "$(cd "$T/train-2" && pwd -P)" "in that train's own worktree"
out="$(bash "$TR" precheck 1 2>&1)"
eq "$out" "PRECHECK train 1 tip=${tp:0:12} EXIT=0" "precheck <k> takes train k"
out="$(bash "$TR" precheck 3 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "no train 3" "precheck refuses a train that isn't built" \
    || bad "precheck refuses a train that isn't built"

# 22d. A worktree that moved since build is refused: its verdict would not
# be the tip's.
echo x > "$T/train/s/pc1"; git -C "$T/train" commit -qam stray
out="$(bash "$TR" precheck 1 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "moved since build" "precheck refuses a moved worktree" \
    || bad "precheck refuses a moved worktree"
git -C "$T/train" reset -q --hard HEAD~1

# 22e. The real command is `make -C projects/ritz train-precheck`:
# tools-ratchets plus the ritz0 test-count cap (AGAST #4904).
: > "$T/systemd-run-log"
out="$(env -u RZ_PRECHECK_CMD bash "$TR" precheck 1 2>&1)"
has "$(cat "$T/systemd-run-log")" "make -C projects/ritz train-precheck$" "by default the precheck runs make train-precheck"
unset RZ_PRECHECK_CMD

# 23. Held tails and rz-resolve refs are swept up, not leaked forever
# (AGAST #4753).  `fail` deletes a red train's tail, but rz re-publishes it
# by hand (`hold-tail`) for a fix-forward room; neither it nor an
# `rz-resolve/<room>-<sha12>` ref (`hold-resolve`) is named by any train's
# state once that happens, so nothing used to delete them.  `land` now
# deletes a held ref once it reboards and lands; `prune-refs` sweeps
# anything else that leaked.
bash "$TR" discard >/dev/null 2>&1
heldfile="$(git -C "$M" rev-parse --path-format=absolute --git-common-dir)/RZ_HELD_TAILS"
rm -f "$heldfile"

# 23a. A lone red train drops with `fail`, which unpublishes its tail;
# `hold-tail` re-publishes it (idempotent) and records it.
fetch; git -C "$M" checkout -q main
sx1="$(room wa1 s/wa1 X)"; fetch; git -C "$M" checkout -q main
bash "$TR" build "wa1:$sx1" >/dev/null 2>&1
tipx="$(tipn 1)"
logx="$(RZ_FAKE_EXIT=1 bash "$TR" gate)"
out="$(bash "$TR" fail "$logx" 2>&1)"
has "$out" "^HELD +wa1 ${sx1:0:12}" "fail HELDs the lone car"
[[ -z "$(oref "${tipx:0:12}")" ]] && ok "fail unpublishes the dropped train's tail" \
    || bad "fail unpublishes the dropped train's tail"
out="$(bash "$TR" hold-tail "$tipx" 2>&1)"
has "$out" "^HELD rz-train/${tipx:0:12}$" "hold-tail re-publishes it"
[[ "$(oref "${tipx:0:12}")" == "$tipx" ]] && ok "hold-tail re-publishes the red tail" \
    || bad "hold-tail re-publishes the red tail"
eq "$(cat "$heldfile" 2>/dev/null)" "rz-train/${tipx:0:12} $tipx" "hold-tail records it in RZ_HELD_TAILS"
bash "$TR" hold-tail "$tipx" >/dev/null 2>&1
eq "$(wc -l < "$heldfile")" 1 "hold-tail is idempotent: no duplicate line"

# 23b. prune-refs never touches a live train's tail, held or not.
fetch; git -C "$M" checkout -q main
sx2="$(room wa2 s/wa2 Y)"; fetch; git -C "$M" checkout -q main
bash "$TR" build "wa2:$sx2" >/dev/null 2>&1
tipx2="$(tipn 1)"
out="$(bash "$TR" prune-refs --dry-run 2>&1)"
! grep -q "rz-train/${tipx2:0:12}" <<<"$out" && ok "prune-refs spares a live train's tail" \
    || { bad "prune-refs spares a live train's tail"; echo "$out" | sed 's/^/     | /'; }
! grep -q "rz-train/${tipx:0:12}" <<<"$out" && ok "prune-refs spares a held tail too" \
    || { bad "prune-refs spares a held tail too"; echo "$out" | sed 's/^/     | /'; }
[[ "$(oref "${tipx2:0:12}")" == "$tipx2" ]] && ok "the live tail is still on origin" \
    || bad "the live tail is still on origin"

# 23c. A leaked ref fully on main, and a leaked, old, not-on-main ref: both
# previewed by --dry-run (which deletes nothing), then actually deleted.
onmain_sha="$(git -C "$M" rev-parse origin/main)"
onmain_ref="rz-train/${onmain_sha:0:12}"
git -C "$M" push -q -f origin "$onmain_sha:refs/heads/$onmain_ref"
old_sha="$(GIT_COMMITTER_DATE="2000-01-01T00:00:00" room wa3 s/wa3 Z)"
old_ref="rz-train/${old_sha:0:12}"
git -C "$M" push -q -f origin "$old_sha:refs/heads/$old_ref"
out="$(bash "$TR" prune-refs --dry-run 2>&1)"
has "$out" "WOULD DELETE $onmain_ref \(on main\)" "dry-run previews a leaked ref already on main"
has "$out" "WOULD DELETE $old_ref \(older than 2d\)" "dry-run previews a leaked, old, unmerged ref"
[[ "$(oref "${onmain_sha:0:12}")" == "$onmain_sha" && "$(oref "${old_sha:0:12}")" == "$old_sha" ]] \
    && ok "--dry-run deletes nothing" || bad "--dry-run deletes nothing"
out="$(bash "$TR" prune-refs 2>&1)"
has "$out" "DELETED  $onmain_ref \(on main\)" "prune-refs deletes the fully-landed leaked ref"
has "$out" "DELETED  $old_ref \(older than 2d\)" "prune-refs deletes the old, unmerged leaked ref"
[[ -z "$(oref "${onmain_sha:0:12}")$(oref "${old_sha:0:12}")" ]] \
    && ok "both leaked refs are gone from origin" || bad "both leaked refs are gone from origin"
[[ "$(oref "${tipx2:0:12}")" == "$tipx2" && "$(oref "${tipx:0:12}")" == "$tipx" ]] \
    && ok "the live and held tails outlive a real prune-refs run" \
    || bad "the live and held tails outlive a real prune-refs run"

# 23d. Land the wa2 train (a plain `build` below discards it anyway), then
# board the held tail's car and its fix-forward together: once that train
# lands, the held tail always having reboarded, `land` deletes its ref and
# drops it from RZ_HELD_TAILS.
fx="$(room wa1fix s/wa1fix FIX "$tipx")"; fetch; git -C "$M" checkout -q main
out="$(bash "$TR" build "wa1:$sx1" "wa1fix:$fx" 2>&1)"
has "$out" "wa1 ${sx1:0:12}" "the held car boards again"
has "$out" "wa1fix ${fx:0:12}" "the fix-forward car boards too"
outl="$(gland 2>&1)"
has "$outl" "^MERGED +wa1 " "the held car lands"
has "$outl" "^MERGED +wa1fix " "the fix lands"
[[ -z "$(oref "${tipx:0:12}")" ]] && ok "land deletes the held tail's ref once it reboards and lands" \
    || bad "land deletes the held tail's ref once it reboards and lands"
[[ ! -s "$heldfile" ]] && ok "land clears RZ_HELD_TAILS of the landed tail" \
    || { bad "land clears RZ_HELD_TAILS of the landed tail"; sed 's/^/     | /' "$heldfile"; }

# 23e. hold-resolve is the same contract for an rz-resolve/* ref: pushed,
# recorded in RZ_HELD_RESOLVES, and dropped by `land` once it reboards.
resolvefile="$(git -C "$M" rev-parse --path-format=absolute --git-common-dir)/RZ_HELD_RESOLVES"
rm -f "$resolvefile"
fetch; git -C "$M" checkout -q main
rs="$(room wb1 s/wb1 R)"; fetch; git -C "$M" checkout -q main
out="$(bash "$TR" hold-resolve wb1room "$rs" 2>&1)"
rref="rz-resolve/wb1room-${rs:0:12}"
has "$out" "^HELD $rref$" "hold-resolve pushes rz-resolve/<room>-<sha12>"
[[ "$(git -C "$M" ls-remote origin "refs/heads/$rref" | cut -f1)" == "$rs" ]] \
    && ok "the resolve ref is on origin" || bad "the resolve ref is on origin"
eq "$(cat "$resolvefile" 2>/dev/null)" "$rref $rs" "hold-resolve records it in RZ_HELD_RESOLVES"
out="$(bash "$TR" build "$rref:$rs" 2>&1)"
has "$out" "$rref ${rs:0:12}" "the resolve ref boards like any other item"
outl="$(gland 2>&1)"
has "$outl" "^MERGED +$rref " "the resolution lands"
[[ -z "$(git -C "$M" ls-remote origin "refs/heads/$rref")" ]] \
    && ok "land deletes the held resolve ref once it reboards and lands" \
    || bad "land deletes the held resolve ref once it reboards and lands"
[[ ! -s "$resolvefile" ]] && ok "land clears RZ_HELD_RESOLVES of the landed resolve" \
    || { bad "land clears RZ_HELD_RESOLVES of the landed resolve"; sed 's/^/     | /' "$resolvefile"; }

echo;[[ $fails -eq 0 ]] && echo "all passed" || { echo "$fails failed"; exit 1; }
