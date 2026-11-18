#!/bin/bash
# Self-test for regression.sh's known-failure judgement and its strict-xpass
# rule — AGAST #1365, rewired onto known-failures/ by AGAST #1834.
#
# regression.sh asks tools/known_failures.py (the one parser and outcome rule
# every gate shares) about `gate = "regression"` entries in
# known-failures/<agast>.toml.  ritz1_selfhosted shares ritz1's entries.
#
# An entry is a claim about the compiler, and claims go stale: the compiler
# learns to build the example and the entry stays, so the suite keeps
# skipping a test that would now pass.  That was detected and then thrown
# away once: the check called warn(), so 74_async_tiers and 75_tier2_uring sat
# listed as "unmigrated against the current async framework" when they were
# really two `&x` -> `@x` migrations.  report_xpass() makes it a hard failure.
# (Entries naming examples that do not exist, and the AGAST-id rule, are the
# parser's job: tools/test_known_failures.py.)
#
# This file proves the floors can actually go red.  A floor that has never
# been observed failing is indistinguishable from no floor at all.
#
# Hermetic: sources regression.sh as a library, points RITZ_KNOWN_FAILURES at
# a synthetic directory, compiles nothing.
#
# Exit codes: 0 all assertions held, 1 otherwise.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RITZ_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export RITZ_REGRESSION_LIB_ONLY=1
# shellcheck source=/dev/null
source "$SCRIPT_DIR/regression.sh"

# regression.sh installs an EXIT trap that deletes the real .regression build
# dir. Drop it: a self test must not be able to disturb a real run.
trap - EXIT
SCRATCH=$(mktemp -d)
trap 'rm -rf "$SCRATCH"' EXIT

TESTS_RUN=0
TESTS_FAILED=0

check() {
    local desc="$1" want="$2" got="$3"
    TESTS_RUN=$((TESTS_RUN + 1))
    if [[ "$want" == "$got" ]]; then
        echo "ok: $desc"
        return 0
    fi
    echo "FAIL: $desc"
    echo "      want: $want"
    echo "      got:  $got"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    return 1
}

echo "regression.sh known-failure / strict-xpass self-test"
echo "======================================================="

KF="$SCRATCH/known-failures"
mkdir -p "$KF"
cat > "$KF/1365.toml" <<'EOF'
[[entry]]
gate = "regression"
compiler = "ritz0"
unit = "tier1_basics_01_hello"
reason = "synthetic ritz0 entry"
agast = 1365

[[entry]]
gate = "regression"
compiler = "ritz1"
unit = "tier5_async_47_lisp"
reason = "synthetic ritz1 entry"
agast = 1365
EOF
export RITZ_KNOWN_FAILURES="$KF"

# Capture what the helpers report: fail/warn print, _verdict writes a file.
# Run each in a subshell so a helper's state can't leak between cases.
judge_fail() {   # $1=compiler $2=key -> "<verdict>|<output>"
    local out="$SCRATCH/r.$RANDOM" msg
    msg=$(judge_compile_failure "$1" "$2" "$1" "$out" 2>&1)
    printf '%s|%s' "$(cat "$out.verdict" 2>/dev/null || echo none)" "$msg"
}
judge_pass() {   # $1=compiler $2=key -> "<rc>|<verdict>|<output>"
    local out="$SCRATCH/r.$RANDOM" msg rc
    msg=$(report_xpass "$1" "$2" "$out" 2>&1); rc=$?
    printf '%s|%s|%s' "$rc" "$(cat "$out.verdict" 2>/dev/null || echo none)" "$msg"
}
has() { case "$1" in *"$2"*) echo yes ;; *) echo no ;; esac; }

# _verdict's on-disk name: check it rather than assume it.
_vprobe="$SCRATCH/probe"; _verdict "$_vprobe" skip
check "_verdict writes <prefix>.verdict (the harness this test reads)" \
    skip "$(cat "$_vprobe.verdict" 2>/dev/null)"

# --- compile failed ---------------------------------------------------------
r=$(judge_fail ritz0 tier1_basics_01_hello)
check "listed + compile failed -> skip" skip "${r%%|*}"
check "the skip cites the AGAST ticket" yes "$(has "$r" "AGAST #1365")"

r=$(judge_fail ritz0 tier9_never_listed)
check "unlisted + compile failed -> fail" fail "${r%%|*}"

r=$(judge_fail ritz0 tier5_async_47_lisp)
check "a ritz1 entry does not excuse ritz0" fail "${r%%|*}"

r=$(judge_fail ritz1 tier5_async_47_lisp)
check "listed ritz1 + compile failed -> skip" skip "${r%%|*}"
r=$(judge_fail ritz1_selfhosted tier5_async_47_lisp)
check "ritz1_selfhosted SHARES ritz1's entry" skip "${r%%|*}"

r=$(judge_fail ritz0 tier1_basics)
check "a strict PREFIX of an entry does not match" fail "${r%%|*}"

# --- compiled -------------------------------------------------------------
r=$(judge_pass ritz0 tier9_never_listed)
check "unlisted + compiles -> not an xpass, no verdict" "1|none" \
    "$(cut -d'|' -f1-2 <<<"$r")"

r=$(judge_pass ritz0 tier1_basics_01_hello)
check "listed + compiles -> xpass, verdict fail" "0|fail" \
    "$(cut -d'|' -f1-2 <<<"$r")"
check "xpass message names the example" yes "$(has "$r" tier1_basics_01_hello)"
check "xpass message says the example COMPILES" yes "$(has "$r" COMPILES)"
check "xpass message names the file to edit" yes "$(has "$r" "1365.toml")"

r=$(judge_pass ritz1_selfhosted tier5_async_47_lisp)
check "ritz1_selfhosted xpasses on ritz1's entry" "0|fail" \
    "$(cut -d'|' -f1-2 <<<"$r")"

# --- fail closed ------------------------------------------------------------
# A malformed list (here: an entry with no agast) makes the CLI exit 2 with
# nothing on stdout.  A listed failure must then FAIL, not skip.
cp "$KF/1365.toml" "$SCRATCH/1365.good"
printf '\n[[entry]]\ngate = "regression"\ncompiler = "ritz0"\nunit = "x"\nreason = "no ticket"\n' \
    >> "$KF/1365.toml"
r=$(judge_fail ritz0 tier1_basics_01_hello)
check "a malformed list fails closed (listed failure -> fail)" fail "${r%%|*}"
cp "$SCRATCH/1365.good" "$KF/1365.toml"

_real_cli="$KNOWN_FAILURES_CLI"; KNOWN_FAILURES_CLI="$SCRATCH/no-such-cli.py"
r=$(judge_fail ritz0 tier1_basics_01_hello)
KNOWN_FAILURES_CLI="$_real_cli"
check "a missing CLI fails closed (listed failure -> fail)" fail "${r%%|*}"

# ---------------------------------------------------------------------------
# Floor (b): the xpass check is WIRED AS A FAILURE at both call sites.
#
# Source-level rather than behavioural, deliberately: exercising the real
# call sites means compiling the corpus with three compilers, the ~20-minute
# suite this self-test exists to stay out of.  What it pins is precisely the
# regression that happened — the check present but advisory.
# ---------------------------------------------------------------------------
rs="$SCRIPT_DIR/regression.sh"

# Two call sites since #1806: Stage 1's judge, and the differential worker
# that Stages 3 and 4 share (run_compare_stage since #1838).
check "every stage's code path checks for an xpass and stops on one" 2 \
    "$(grep -cE '^\s*report_xpass .* "\$out" && return 0$' "$rs")"
check "every stage's code path judges compile failures the same way" 2 \
    "$(grep -cE '^\s*judge_compile_failure ' "$rs")"
check "Stages 3 and 4 both go through the shared differential worker" 2 \
    "$(grep -cE '^\s*run_compare_stage [34] ritz1(_selfhosted)? ' "$rs")"
check "no stage still only warns about a listed example that compiles" 0 \
    "$(grep -cE 'warn .*(but COMPILES|allowlist but)' "$rs")"
check "the old private-list helpers are gone" 0 \
    "$(grep -cE 'is_known_failure|known_failures_file|regression-known-failures[-a-z0-9]*\.txt"' "$rs")"

echo
echo "-----------------------------------------------"
if [[ $TESTS_FAILED -eq 0 ]]; then
    echo "✓ $TESTS_RUN assertions passed"
    exit 0
fi
echo "✗ $TESTS_FAILED of $TESTS_RUN assertions failed"
exit 1
