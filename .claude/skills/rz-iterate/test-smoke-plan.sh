#!/usr/bin/env bash
# Tests for smoke-plan.sh (AGAST #4580 item 9) in a scratch repo.
# Run: bash test-smoke-plan.sh
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SP="$HERE/smoke-plan.sh"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
fails=0
ok()  { echo "ok   - $1"; }
bad() { echo "FAIL - $1"; fails=$((fails + 1)); }
eq()  { [[ "$1" == "$2" ]] && ok "$3" || { bad "$3"; echo "     | got '$1', want '$2'"; }; }
has() { grep -qE "$2" <<<"$1" && ok "$3" || { bad "$3"; echo "$1" | sed 's/^/     | /'; }; }

export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
R="$T/repo"; git init -q -b main "$R"; cd "$R" || exit 1
echo x > README.md; git add .; git commit -qm init
# change <path>...: one commit touching each path; prints its SHA.
change() {
    local p
    for p in "$@"; do mkdir -p "$(dirname "$p")"; echo "$RANDOM" >> "$p"; done
    git add -A; git commit -qm "change $*"; git rev-parse HEAD
}
# targets [<range>]: the plan's target names on one line.
targets() { bash "$SP" plan "$@" | cut -f1 | paste -sd' '; }

# 1. The path -> targets mapping, one rule at a time.
change docs/a.md >/dev/null;                    eq "$(targets)" "smoke tools-ratchets" "a doc-only diff is smoke and the ratchets"
change projects/ritz/README.md >/dev/null;      eq "$(targets)" "smoke doc-examples tools-ratchets" "a ritz doc checks its examples"
change projects/ritz/ritz0/x.py >/dev/null;     eq "$(targets)" "smoke tools-ratchets unit ritz1-bootstrap matrix build-all-ritz1" "ritz0 runs the full unit suite, ritz1-bootstrap, the matrix and every package under ritz1"
change projects/ritz/runtime/r.c >/dev/null;    eq "$(targets)" "smoke tools-ratchets unit ritz1-bootstrap matrix build-all-ritz1" "the runtime runs the compiler set (every package links it)"
change projects/ritz/ritz1/src/m.ritz >/dev/null
eq "$(targets)" "smoke tools-ratchets unit ritz1-bootstrap ritz1-unit matrix build-all-ritz1" "ritz1/src runs the compiler set, its unit suites and every package under ritz1"
change projects/ritz/grammars/g.grammar >/dev/null
eq "$(targets)" "smoke tools-ratchets unit ritz1-bootstrap matrix build-all-ritz1" "the grammar runs the compiler set (regen-check is in the matrix)"
change projects/ritz/ritzlib/v.ritz >/dev/null; eq "$(targets)" "smoke tools-ratchets ritzlib matrix build-all-ritz1" "ritzlib runs its tests, the matrix and every package under ritz1"
change projects/ritz/test/t.ritz >/dev/null;    eq "$(targets)" "smoke tools-ratchets ritz-tests matrix" "ritz/test runs the language tests and the matrix"
change projects/ritz/examples/e.ritz >/dev/null; eq "$(targets)" "smoke tools-ratchets examples" "examples run the examples"
change projects/ritz/tools/t.py >/dev/null;     eq "$(targets)" "smoke tools-unit tools-ratchets" "tools run tools-unit (and the ratchets: no unit for ritz0's half)"
change projects/ritz/scripts/s.sh >/dev/null;   eq "$(targets)" "smoke tools-ratchets harness-selftest" "scripts run the harness self-tests"
change projects/ritz/build.py >/dev/null;       eq "$(targets)" "smoke tools-unit unit" "other ritz files run unit and tools-unit"
change projects/nexus/src/n.ritz >/dev/null;    eq "$(targets)" "smoke tools-ratchets ritz1-bootstrap pkg:nexus" "a package builds the compilers, then its own build and tests"
# AGAST #4822: projects/builder has no ritz.toml (a Dockerfile, not a
# package), so pkg:builder would be `./rz build builder`, which fails.  Its
# own test builds the image, which bootstraps the compilers inside it.
change projects/builder/Dockerfile >/dev/null;  eq "$(targets)" "smoke tools-ratchets builder" "the builder image runs its own image test, not a package build"
has "$(bash "$SP" plan)" "^builder	bash projects/builder/test.sh$" "the builder target runs projects/builder/test.sh"
change .claude/skills/rz-iterate/train.sh >/dev/null
eq "$(targets)" "smoke tools-unit tools-ratchets skill:rz-iterate" "a skill runs its own tests and tools-unit"
# AGAST #4580 bounce: tools/test_provision_room.py and test_smoke.py assert
# SKILL.md's text, so a .claude/ change (markdown included) runs tools-unit.
change .claude/skills/rz-iterate/SKILL.md >/dev/null
eq "$(targets)" "smoke tools-unit tools-ratchets skill:rz-iterate" "a skill's SKILL.md runs tools-unit and the skill's tests"
change .claude/settings.json >/dev/null;        eq "$(targets)" "smoke tools-unit tools-ratchets" "any other .claude/ file runs tools-unit"
change .claude/host-env.sh >/dev/null;          eq "$(targets)" "smoke tools-unit tools-ratchets skill:rz-iterate" "host-env.sh runs tools-unit and rz-iterate's tests"
toml="$(change rz.toml)";                       eq "$(targets)" "smoke tools-ratchets build-all" "the workspace manifest builds everything"
change .github/workflows/main.yml >/dev/null;   eq "$(targets)" "smoke tools-ratchets" "CI config is smoke and the ratchets (the train gate covers the rest)"
# AGAST #4587: train 814a64f4 went red on tools/test_ritz1_kind_match.py, a
# ratchet that reads ritz1 sources, which the compiler set never ran.
change projects/ritz/grammars/h.grammar >/dev/null
has "$(bash "$SP" plan)" "^tools-ratchets	make -C projects/ritz tools-ratchets$" "tools-ratchets runs the Makefile's source-reading subset"
# tools-unit runs all of tools/ and unit all of ritz0, so a diff that needs
# both runs them instead (#4587, #4622).
change projects/ritz/ritz1/src/k.ritz projects/ritz/tools/k.py >/dev/null
eq "$(targets)" "smoke tools-unit unit ritz1-bootstrap ritz1-unit matrix build-all-ritz1" "tools-unit subsumes tools-ratchets"
change projects/ritz/ritz1/src/k.ritz .claude/settings.json >/dev/null
eq "$(targets)" "smoke tools-unit unit ritz1-bootstrap ritz1-unit matrix build-all-ritz1" "and so does a .claude/ change's tools-unit"

# AGAST #4672: every car runs the ratchets (~15 s), not only a compiler
# change: #4653 and #4654 both broke a pin their smoke never ran.  Only
# tools-unit and unit together subsume them (tools/ and all of ritz0).
change projects/ritz/tools/v.py >/dev/null
has "$(bash "$SP" plan)" "^tools-ratchets	" "tools-unit alone does not subsume the ratchets (ritz0's -m inproc half)"
change projects/ritz/build.py >/dev/null
eq "$(targets)" "smoke tools-unit unit" "tools-unit and unit together do"

# AGAST #4777: two red trains from cars whose smoke passed.  #4772 changed
# ritz1/src and broke ritz1/test (ritz1-unit, which nothing planned); #4739
# changed a package that only ritz1 could not build (pkg: built with ritz0).
change projects/ritz/ritz1/test/test_v.ritz >/dev/null
eq "$(targets)" "smoke tools-ratchets unit ritz1-bootstrap ritz1-unit matrix" "ritz1/test runs ritz1's unit suites (no package sweep: no compiler change)"
has "$(bash "$SP" plan)" "^ritz1-unit	make -C projects/ritz ritz1-unit$" "ritz1-unit runs the Makefile's ritz1 unit suites"
change projects/ritz/ritz1/src/n.ritz >/dev/null
has "$(bash "$SP" plan)" "^build-all-ritz1	make -C projects/ritz build-all-ritz1$" "build-all-ritz1 builds every package under ritz1 and ritz1_selfhosted"
change projects/ritz/docs/LANGUAGE_SPEC.md >/dev/null
eq "$(targets)" "smoke doc-examples tools-ratchets build-all-ritz1" "a language spec change builds every package under ritz1"
change projects/ritz/docs/TESTING.md >/dev/null
eq "$(targets)" "smoke doc-examples tools-ratchets" "other ritz docs do not"
change projects/harland/netstack/src/arp.ritz >/dev/null
pk="$(bash "$SP" plan | grep '^pkg:harland')"
has "$pk" "\./rz build harland --compiler \\\$c" "a package builds under each compiler"
has "$pk" "for c in ritz0 ritz1 ritz1_selfhosted;" "ritz0, ritz1 and ritz1_selfhosted"
has "$pk" "\./rz test harland" "and still runs its tests"
has "$pk" "known_failures\.py list --gate build --compiler" "a compiler a known-failures build entry excuses is skipped"
# Run the command against stubs: rz logs its args (and fails a ritz1 build),
# known_failures.py excuses harland under ritz1_selfhosted only.
mkdir -p "$T/stub/projects/ritz/tools"
printf '#!/usr/bin/env bash\necho "$*" >> rz.log\n[[ "$*" != "build harland --compiler ritz1" ]]\n' > "$T/stub/rz"
chmod +x "$T/stub/rz"
printf 'import sys\nif sys.argv[-1] == "ritz1_selfhosted":\n    print("harland\\tAGAST #1: stub")\n' > "$T/stub/projects/ritz/tools/known_failures.py"
(cd "$T/stub" && bash -c "$(cut -f2 <<<"$pk")" >out.log 2>&1); rc=$?
eq "$(paste -sd'|' "$T/stub/rz.log")" "build harland --compiler ritz0|build harland --compiler ritz1|test harland" \
    "pkg: builds under each compiler in full, skips an excused one, then tests"
eq "$rc" 1 "a failed build under ritz1 fails the target"
has "$(cat "$T/stub/out.log")" "build under ritz1_selfhosted excused" "and says which build it skipped"
# A nested package (its own ritz.toml) is built by itself too: #4739's
# arp.ritz is in harland/netstack, which harland's own build never compiles.
# The enclosing package stays (harland builds its nested *_abi deps).  An
# excluded dir (rz.toml [workspace.exclude]) is not a package of its own.
printf '[workspace.exclude]\n"projects/harland/boot" = "harland builds it"\n' > rz.toml
change projects/harland/ritz.toml projects/harland/netstack/ritz.toml projects/harland/boot/ritz.toml >/dev/null
change projects/harland/netstack/src/arp.ritz >/dev/null
eq "$(targets)" "smoke tools-ratchets ritz1-bootstrap pkg:harland pkg:harland/netstack" "a nested package's change builds it and its enclosing package"
change projects/harland/boot/src/b.ritz >/dev/null
eq "$(targets)" "smoke tools-ratchets ritz1-bootstrap pkg:harland" "an excluded nested dir is its enclosing package's"
change projects/harland/kernel/src/k.ritz >/dev/null
eq "$(targets)" "smoke tools-ratchets ritz1-bootstrap pkg:harland" "the enclosing package's own files build it alone"
nest="$(git rev-parse HEAD~2)"; git mv -k projects/harland/netstack/ritz.toml projects/harland/netstack/x.toml; git commit -qm unnest
eq "$(targets "$nest^!")" "smoke tools-ratchets ritz1-bootstrap pkg:harland pkg:harland/netstack" "the planned commit's tree decides, not the work tree"
git reset -q --hard HEAD~1
# AGAST #4813: a top-level package rz.toml excludes (buddhafinger: built with
# ritz1_selfhosted only) runs its dedicated entry, never pkg:'s
# three-compiler build, which is the sweep the exclusion keeps it out of.
printf '"projects/editor" = "make -C projects/editor test"\n' >> rz.toml
change projects/editor/ritz.toml >/dev/null
change projects/editor/src/e.ritz >/dev/null
eq "$(targets)" "smoke tools-ratchets ritz1-bootstrap entry:editor" "an excluded top-level package runs its dedicated entry, not pkg:"
has "$(bash "$SP" plan)" "^entry:editor	make -C projects/editor test$" "entry: runs the package's own make test"
# #4822 x #4813: the two rules side by side.  buddhafinger keeps its entry:
# when the same diff touches the builder image, and projects/builder stays
# builder even if rz.toml excludes it (it has no make test to run).  Reset
# after, so the range assertion below is unchanged.
mark="$(git rev-parse HEAD)"
printf '"projects/buddhafinger" = "ritz1_selfhosted only, #4782"\n"projects/builder" = "not a package"\n' >> rz.toml
change projects/buddhafinger/ritz.toml >/dev/null
change projects/buddhafinger/src/main.ritz projects/builder/test.sh >/dev/null
eq "$(targets)" "smoke tools-ratchets ritz1-bootstrap builder entry:buddhafinger" "builder and an excluded package in one diff: builder, and buddhafinger's entry:"
has "$(bash "$SP" plan)" "^entry:buddhafinger	make -C projects/buddhafinger test$" "buddhafinger's entry: runs its make test"
change projects/builder/Dockerfile >/dev/null
eq "$(targets)" "smoke tools-ratchets builder" "an excluded projects/builder is still builder, never entry:builder"
git reset -q --hard "$mark"

# AGAST #4752: a CI boot script's pin.  Train e0f78f1e went red on
# test_ci_msix_boot.py after a car changed test_msix_boot.sh, which only
# pkg:harland covered.  A path a projects/ritz/tools/test_ci_*.py names
# runs that file (ci:), read from the planned commit's tree.
mark="$(git rev-parse HEAD)"
mkdir -p projects/ritz/tools
printf 'SCRIPT = "projects/harland/tools/test_msix_boot.sh"\nS = "projects/harland/tools/shell_session.py"\n' > projects/ritz/tools/test_ci_msix_boot.py
printf 'S = REPO / "projects/harland/tools/shell_session.py"\n' > projects/ritz/tools/test_ci_shell_boot.py
git add -A; git commit -qm pins
change projects/harland/tools/test_msix_boot.sh >/dev/null
eq "$(targets)" "smoke tools-ratchets ritz1-bootstrap ci:test_ci_msix_boot.py pkg:harland" "a CI boot script runs the test_ci_*.py that names it"
has "$(bash "$SP" plan)" "^ci:test_ci_msix_boot.py	cd projects/ritz && python3 -m pytest -q -n 8 --dist loadgroup tools/test_ci_msix_boot.py$" \
    "ci: runs that one file under xdist, as tools-unit does"
change projects/harland/tools/shell_session.py >/dev/null
eq "$(targets)" "smoke tools-ratchets ritz1-bootstrap ci:test_ci_msix_boot.py ci:test_ci_shell_boot.py pkg:harland" "a file two pins name runs both"
change projects/harland/tools/other.sh >/dev/null
eq "$(targets)" "smoke tools-ratchets ritz1-bootstrap pkg:harland" "a path no pin names runs none"
change projects/ritz/tools/test_ci_msix_boot.py >/dev/null
eq "$(targets)" "smoke tools-unit tools-ratchets" "a pin itself is tools-unit's (which runs it)"
git reset -q --hard "$mark"

# 2. A mixed diff: each target once, in the fixed order, packages last.
s="$(change projects/ritz/ritz0/y.py projects/ritz/tools/u.py projects/ritz/ritz0/z.py \
    projects/spire/lib/a.ritz projects/angelo/src/b.ritz docs/c.md)"
eq "$(targets)" "smoke tools-unit unit ritz1-bootstrap matrix build-all-ritz1 pkg:angelo pkg:spire" "a mixed diff: each target once, in order"
eq "$(targets "$s^!")" "smoke tools-unit unit ritz1-bootstrap matrix build-all-ritz1 pkg:angelo pkg:spire" "<sha>^! plans one commit"
eq "$(targets "$toml^..HEAD")" "smoke doc-examples tools-unit unit ritz1-bootstrap ritz1-unit matrix build-all build-all-ritz1 entry:editor pkg:angelo pkg:harland pkg:harland/netstack pkg:spire" \
    "a range plans every commit in it"
has "$(bash "$SP" plan)" "^unit	make -C projects/ritz unit$" "plan prints each target's command, tab-separated"
has "$(bash "$SP" plan)" "^pkg:spire	rc=0; for c in ritz0 ritz1 ritz1_selfhosted; .*\./rz test spire [|][|] rc=1; exit .rc$" "a package's command builds it under each compiler, then tests it"

# AGAST #4777: the plan is the floor.  A room adds targets by judgment
# (`+<target>`) and its quote names them, after the plan's, each once.
eq "$(targets +ritzlib-ritz1 +pkg:nexus +smoke)" "smoke tools-unit unit ritz1-bootstrap matrix build-all-ritz1 pkg:angelo pkg:spire ritzlib-ritz1 pkg:nexus" \
    "plan +<target> adds extras after the floor, each once"
eq "$(targets "$s^!" +build-all)" "smoke tools-unit unit ritz1-bootstrap matrix build-all-ritz1 pkg:angelo pkg:spire build-all" "extras combine with a range"
has "$(bash "$SP" plan +ritzlib-ritz1)" "^ritzlib-ritz1	make -C projects/ritz ritzlib-tests-ritz1$" "ritzlib-ritz1 runs ritzlib's tests under ritz1 and ritz1_selfhosted"
out="$(bash "$SP" plan +no-such 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "unknown target no-such" "an unknown extra is refused" || bad "an unknown extra is refused (rc=$rc)"

# 3. run: every target in full (no fail-fast), then the quote.
cat > "$T/runner" <<'EOF'
#!/usr/bin/env bash
echo "$1" >> "$RZ_TEST_RAN"
[[ " ${RZ_TEST_FAIL:-} " != *" $1 "* ]]
EOF
chmod +x "$T/runner"
export RZ_SMOKE_RUNNER="$T/runner" RZ_TEST_RAN="$T/ran"
h12="$(git rev-parse --short=12 HEAD)"
: > "$T/ran"; out="$(bash "$SP" run 2>/dev/null)"; rc=$?
eq "$rc" 0 "run exits 0 when every target passes"
eq "$(tail -1 <<<"$out")" "smoke $h12 [smoke tools-unit unit ritz1-bootstrap matrix build-all-ritz1 pkg:angelo pkg:spire] EXIT=0" \
    "run's last line is the REAP quote"
: > "$T/ran"; out="$(RZ_TEST_FAIL="tools-unit" bash "$SP" run 2>"$T/err")"; rc=$?
eq "$rc" 1 "run exits non-zero when a target fails"
eq "$(paste -sd' ' "$T/ran")" "smoke tools-unit unit ritz1-bootstrap matrix build-all-ritz1 pkg:angelo pkg:spire" \
    "a failing target does not stop the rest (every subsystem runs in full)"
eq "$(tail -1 <<<"$out")" "smoke $h12 [smoke tools-unit unit ritz1-bootstrap matrix build-all-ritz1 pkg:angelo pkg:spire] EXIT=1" \
    "the quote carries the failure"
has "$(cat "$T/err")" "^FAILED: tools-unit$" "run names the failed targets"
: > "$T/ran"; out="$(bash "$SP" run +ritzlib-ritz1 2>/dev/null)"; rc=$?
eq "$(tail -1 <<<"$out")" "smoke $h12 [smoke tools-unit unit ritz1-bootstrap matrix build-all-ritz1 pkg:angelo pkg:spire ritzlib-ritz1] EXIT=0" \
    "run +<target> runs the extra and quotes it"
eq "$(tail -1 "$T/ran")" "ritzlib-ritz1" "the extra ran, last"
out="$(bash "$SP" check "$(git rev-parse HEAD)" "$(tail -1 <<<"$out")")"; rc=$?
eq "$rc" 0 "check accepts a quote with extras"
echo dirty >> docs/c.md
out="$(bash "$SP" run 2>&1)"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "uncommitted changes" "run refuses a dirty tree" || bad "run refuses a dirty tree (rc=$rc)"
git checkout -q -- docs/c.md
cat > "$T/mover" <<'EOF'
#!/usr/bin/env bash
[[ "$1" != smoke ]] || git commit -q --allow-empty -m moved
EOF
chmod +x "$T/mover"
out="$(RZ_SMOKE_RUNNER="$T/mover" bash "$SP" run 2>/dev/null)"; rc=$?
eq "$rc" 99 "run exits 99 when HEAD moves under it"
has "$out" "EXIT=99$" "the quote says so"
git reset -q --hard HEAD~1
unset RZ_SMOKE_RUNNER

# 4. check: rz's REAP check of the quote.
full="$(git rev-parse HEAD)"
q="smoke $h12 [smoke tools-unit unit ritz1-bootstrap matrix build-all-ritz1 pkg:angelo pkg:spire] EXIT=0"
out="$(bash "$SP" check "$full" "$q")"; rc=$?
eq "$rc" 0 "check accepts the quote run printed"; has "$out" "^OK smoke $h12" "and says OK"
out="$(bash "$SP" check "$full" "smoke $h12 [smoke unit ritz1-bootstrap matrix build-all-ritz1 pkg:angelo pkg:spire build-all] EXIT=0")"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "misses tools-unit" "check refuses a quote missing a planned target" \
    || bad "check refuses a quote missing a planned target"
out="$(bash "$SP" check "$full" "smoke $h12 [smoke tools-unit unit ritz1-bootstrap matrix build-all-ritz1 pkg:angelo pkg:spire build-all] EXIT=0")"
has "$out" "^OK" "check allows extra targets"
out="$(bash "$SP" check "$full" "smoke $h12 [smoke tools-unit unit ritz1-bootstrap matrix build-all-ritz1 pkg:angelo pkg:spire] EXIT=1")"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "EXIT=1" "check refuses a failed run" || bad "check refuses a failed run"
other="$(git rev-parse --short=12 HEAD~1)"
out="$(bash "$SP" check "$full" "smoke $other [smoke tools-unit unit ritz1-bootstrap matrix build-all-ritz1 pkg:angelo pkg:spire] EXIT=0")"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "not $h12" "check refuses a quote for another SHA" || bad "check refuses a quote for another SHA"
out="$(bash "$SP" check "$full" "gate skipped (train-gated)")"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "not a smoke quote" "check refuses a bare no-check marker" || bad "check refuses a bare no-check marker"
# rz's interim hand-written form (2026-11-23), for rooms briefed before this.
base12="$(git rev-parse --short=12 HEAD~1)"
out="$(bash "$SP" check "$full" "verified smoke+tools-unit+unit+ritz1-bootstrap+matrix+build-all-ritz1+pkg:angelo+pkg:spire on $base12 (unit: 24000 passed, 0 failed)")"; rc=$?
eq "$rc" 0 "check accepts rz's interim verified line"
out="$(bash "$SP" check "$full" "verified smoke+unit+ritz1-bootstrap+matrix on $base12 (unit: 24000 passed, 0 failed)")"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "misses tools-unit build-all-ritz1 pkg:angelo pkg:spire" "the verified line must cover the plan" \
    || bad "the verified line must cover the plan (rc=$rc)"
out="$(bash "$SP" check "$full" "verified smoke+tools-unit+unit+ritz1-bootstrap+matrix+build-all-ritz1+pkg:angelo+pkg:spire on $base12 (unit: 23988 passed, 12 failed)")"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "reports failures" "a verified line with failures is refused" \
    || bad "a verified line with failures is refused (rc=$rc)"
out="$(bash "$SP" check "$full" "gate 4580-$h12-1.log SHA=$h12 EXIT=0")"; rc=$?
eq "$rc" 0 "check still accepts a full gate quote"
out="$(bash "$SP" check "$full" "gate 4580-$h12-1.log SHA=$h12 EXIT=2 budget-only: 900 / factor 1.2 = 750 vs cap")"; rc=$?
eq "$rc" 0 "check accepts the terminal budget-only gate verdict"
out="$(bash "$SP" check "$full" "gate 4580-$other-1.log SHA=$other EXIT=0")"; rc=$?
[[ $rc -ne 0 ]] && ok "check refuses a gate quote for another SHA" || bad "check refuses a gate quote for another SHA"
out="$(bash "$SP" check "$full" "gate 4580-$h12-1.log SHA=$h12 EXIT=2")"; rc=$?
[[ $rc -ne 0 ]] && ok "check refuses a red gate" || bad "check refuses a red gate"

echo; [[ $fails -eq 0 ]] && echo "all passed" || { echo "$fails failed"; exit 1; }
