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
change docs/a.md >/dev/null;                    eq "$(targets)" "smoke" "a doc-only diff is smoke alone"
change projects/ritz/README.md >/dev/null;      eq "$(targets)" "smoke doc-examples" "a ritz doc checks its examples"
change projects/ritz/ritz0/x.py >/dev/null;     eq "$(targets)" "smoke unit ritz1-bootstrap matrix" "ritz0 runs the full unit suite, ritz1-bootstrap and the matrix"
change projects/ritz/runtime/r.c >/dev/null;    eq "$(targets)" "smoke unit ritz1-bootstrap matrix" "the runtime runs the compiler set"
change projects/ritz/ritz1/src/m.ritz >/dev/null
eq "$(targets)" "smoke unit ritz1-bootstrap matrix" "ritz1 runs the compiler set rz briefs"
change projects/ritz/grammars/g.grammar >/dev/null
eq "$(targets)" "smoke unit ritz1-bootstrap matrix" "the grammar runs what ritz1 does (regen-check is in the matrix)"
change projects/ritz/ritzlib/v.ritz >/dev/null; eq "$(targets)" "smoke ritzlib matrix" "ritzlib runs its tests and the matrix"
change projects/ritz/test/t.ritz >/dev/null;    eq "$(targets)" "smoke ritz-tests matrix" "ritz/test runs the language tests and the matrix"
change projects/ritz/examples/e.ritz >/dev/null; eq "$(targets)" "smoke examples" "examples run the examples"
change projects/ritz/tools/t.py >/dev/null;     eq "$(targets)" "smoke tools-unit" "tools run tools-unit"
change projects/ritz/scripts/s.sh >/dev/null;   eq "$(targets)" "smoke harness-selftest" "scripts run the harness self-tests"
change projects/ritz/build.py >/dev/null;       eq "$(targets)" "smoke tools-unit unit" "other ritz files run unit and tools-unit"
change projects/nexus/src/n.ritz >/dev/null;    eq "$(targets)" "smoke pkg:nexus" "a package runs its own build and tests"
change .claude/skills/rz-iterate/train.sh >/dev/null
eq "$(targets)" "smoke tools-unit skill:rz-iterate" "a skill runs its own tests and tools-unit"
# AGAST #4580 bounce: tools/test_provision_room.py and test_smoke.py assert
# SKILL.md's text, so a .claude/ change (markdown included) runs tools-unit.
change .claude/skills/rz-iterate/SKILL.md >/dev/null
eq "$(targets)" "smoke tools-unit skill:rz-iterate" "a skill's SKILL.md runs tools-unit and the skill's tests"
change .claude/settings.json >/dev/null;        eq "$(targets)" "smoke tools-unit" "any other .claude/ file runs tools-unit"
change .claude/host-env.sh >/dev/null;          eq "$(targets)" "smoke tools-unit skill:rz-iterate" "host-env.sh runs tools-unit and rz-iterate's tests"
change rz.toml >/dev/null;                      eq "$(targets)" "smoke build-all" "the workspace manifest builds everything"
change .github/workflows/main.yml >/dev/null;   eq "$(targets)" "smoke" "CI config is smoke alone (the train gate covers it)"

# 2. A mixed diff: each target once, in the fixed order, packages last.
s="$(change projects/ritz/ritz0/y.py projects/ritz/tools/u.py projects/ritz/ritz0/z.py \
    projects/spire/lib/a.ritz projects/angelo/src/b.ritz docs/c.md)"
eq "$(targets)" "smoke tools-unit unit ritz1-bootstrap matrix pkg:angelo pkg:spire" "a mixed diff: each target once, in order"
eq "$(targets "$s^!")" "smoke tools-unit unit ritz1-bootstrap matrix pkg:angelo pkg:spire" "<sha>^! plans one commit"
eq "$(targets HEAD~3..HEAD)" "smoke tools-unit unit ritz1-bootstrap matrix build-all pkg:angelo pkg:spire" \
    "a range plans every commit in it"
has "$(bash "$SP" plan)" "^unit	make -C projects/ritz unit$" "plan prints each target's command, tab-separated"
has "$(bash "$SP" plan)" "^pkg:spire	\./rz build spire && \./rz test spire$" "a package's command builds and tests it"

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
eq "$(tail -1 <<<"$out")" "smoke $h12 [smoke tools-unit unit ritz1-bootstrap matrix pkg:angelo pkg:spire] EXIT=0" \
    "run's last line is the REAP quote"
: > "$T/ran"; out="$(RZ_TEST_FAIL="tools-unit" bash "$SP" run 2>"$T/err")"; rc=$?
eq "$rc" 1 "run exits non-zero when a target fails"
eq "$(paste -sd' ' "$T/ran")" "smoke tools-unit unit ritz1-bootstrap matrix pkg:angelo pkg:spire" \
    "a failing target does not stop the rest (every subsystem runs in full)"
eq "$(tail -1 <<<"$out")" "smoke $h12 [smoke tools-unit unit ritz1-bootstrap matrix pkg:angelo pkg:spire] EXIT=1" \
    "the quote carries the failure"
has "$(cat "$T/err")" "^FAILED: tools-unit$" "run names the failed targets"
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
q="smoke $h12 [smoke tools-unit unit ritz1-bootstrap matrix pkg:angelo pkg:spire] EXIT=0"
out="$(bash "$SP" check "$full" "$q")"; rc=$?
eq "$rc" 0 "check accepts the quote run printed"; has "$out" "^OK smoke $h12" "and says OK"
out="$(bash "$SP" check "$full" "smoke $h12 [smoke unit matrix pkg:angelo pkg:spire build-all] EXIT=0")"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "misses tools-unit" "check refuses a quote missing a planned target" \
    || bad "check refuses a quote missing a planned target"
out="$(bash "$SP" check "$full" "smoke $h12 [smoke tools-unit unit ritz1-bootstrap matrix pkg:angelo pkg:spire build-all] EXIT=0")"
has "$out" "^OK" "check allows extra targets"
out="$(bash "$SP" check "$full" "smoke $h12 [smoke tools-unit unit ritz1-bootstrap matrix pkg:angelo pkg:spire] EXIT=1")"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "EXIT=1" "check refuses a failed run" || bad "check refuses a failed run"
other="$(git rev-parse --short=12 HEAD~1)"
out="$(bash "$SP" check "$full" "smoke $other [smoke tools-unit unit ritz1-bootstrap matrix pkg:angelo pkg:spire] EXIT=0")"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "not $h12" "check refuses a quote for another SHA" || bad "check refuses a quote for another SHA"
out="$(bash "$SP" check "$full" "gate skipped (train-gated)")"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "not a smoke quote" "check refuses a bare no-check marker" || bad "check refuses a bare no-check marker"
# rz's interim hand-written form (2026-11-23), for rooms briefed before this.
base12="$(git rev-parse --short=12 HEAD~1)"
out="$(bash "$SP" check "$full" "verified smoke+tools-unit+unit+ritz1-bootstrap+matrix+pkg:angelo+pkg:spire on $base12 (unit: 24000 passed, 0 failed)")"; rc=$?
eq "$rc" 0 "check accepts rz's interim verified line"
out="$(bash "$SP" check "$full" "verified smoke+unit+ritz1-bootstrap+matrix on $base12 (unit: 24000 passed, 0 failed)")"; rc=$?
[[ $rc -ne 0 ]] && has "$out" "misses tools-unit pkg:angelo pkg:spire" "the verified line must cover the plan" \
    || bad "the verified line must cover the plan (rc=$rc)"
out="$(bash "$SP" check "$full" "verified smoke+tools-unit+unit+ritz1-bootstrap+matrix+pkg:angelo+pkg:spire on $base12 (unit: 23988 passed, 12 failed)")"; rc=$?
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
