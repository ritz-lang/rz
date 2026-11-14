#!/usr/bin/env bash
# End-to-end proof that Stage 5 turns a real, allowlist-silenced ritz1 vs
# ritz1_selfhosted divergence into a non-zero exit.
#
# WHY THIS EXISTS
# ---------------
# scripts/test-regression-stage5.sh proves the Stage 5 *logic* hermetically in
# under a second, and that is the test you should run routinely.  It does not,
# however, prove that Stage 5 is actually wired into the suite's exit code, nor
# that the allowlist really fails to silence it when the allowlist is consulted
# by the genuine stage-3/stage-4 code paths.  This script proves that end to
# end, by reconstructing the exact CI failure the gate missed.
#
# The real divergence (tier5_async_49_ritzgen under CI's older clang) is not
# reproducible on every box, so we synthesise one instead, through two env-var
# hooks in regression.sh (see "Stage 5 proof hooks" there):
#
#   1. RITZ_REGRESSION_INJECT_SELFHOSTED_REJECT makes ritz1_selfhosted reject
#      one example that plainly compiles under both.
#   2. RITZ_REGRESSION_RITZ1_ALLOWLIST points the suite at a temporary
#      allowlist = the real list + that example.  Stage 4 therefore reports
#      the rejection as a benign "known, allowlisted" SKIP and contributes
#      zero failures -- precisely the situation in which the old gate exited 0.
#   3. Assert the suite now exits 1, and that Stage 5 is what made it red.
#
# This used to text-patch a copy of regression.sh at Stage 4's compile line.
# When Stage 4 moved into differential_worker the line vanished, the patcher
# raised, and the script ran the UNPATCHED suite anyway and printed NOT
# PROVEN (AGAST #3200).  The hooks remove the dependence on regression.sh's
# text, and any setup failure now exits 2 before a suite is run.
#
# Usage:
#   scripts/prove-stage5-divergence.sh            # the proof: expect PROVEN
#   scripts/prove-stage5-divergence.sh --control  # same run, no injection:
#                                                 # expect NOT PROVEN (exit 1)
#
# Exit codes: 0 PROVEN, 1 NOT PROVEN, 2 could not set the proof up.
#
# Nothing tracked is modified: the synthetic allowlist is a temporary file,
# removed on exit.  The real regression-known-failures-*.txt files are never
# written to.  PROVE_STAGE5_REGRESSION_SH overrides the suite under test
# (scripts/test-regression-inject.sh uses it).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REGRESSION_SH="${PROVE_STAGE5_REGRESSION_SH:-$SCRIPT_DIR/regression.sh}"

INJECT=1
case "${1:-}" in
    "")        ;;
    --control) INJECT=0 ;;
    *) echo "usage: $0 [--control]" >&2; exit 2 ;;
esac

setup_error() { echo "SETUP ERROR: $*" >&2; exit 2; }

# The suite must have both hooks, or nothing below would inject anything and
# the run would be the clean suite -- the exact rot this guards against.
[[ -f "$REGRESSION_SH" ]] || setup_error "$REGRESSION_SH not found"
for hook in RITZ_REGRESSION_RITZ1_ALLOWLIST RITZ_REGRESSION_INJECT_SELFHOSTED_REJECT; do
    grep -qF "$hook" "$REGRESSION_SH" ||
        setup_error "$REGRESSION_SH has no $hook hook -- update this proof"
done

# An example that unambiguously compiles under every stage, so that the ONLY
# reason the sets can diverge is the injection.
VICTIM_DIR="tier1_basics/01_hello"
VICTIM="${VICTIM_DIR//\//_}"   # regression.sh's example_key
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
[[ -d "$ROOT_DIR/examples/$VICTIM_DIR" ]] ||
    setup_error "victim example examples/$VICTIM_DIR not found"

T=$(mktemp -d) || setup_error "mktemp -d failed"
trap 'rm -rf "$T"' EXIT
TMP_ALLOW="$T/synthetic-allowlist.txt"
LOG="$T/synthetic-run.log"

# --- 1. synthetic allowlist: the real ritz1 list, plus the victim -----------
{ cat "$SCRIPT_DIR/regression-known-failures-ritz1.txt" && echo "$VICTIM"; } \
    > "$TMP_ALLOW" || setup_error "could not write $TMP_ALLOW"

# --- 2. run it ---------------------------------------------------------------
if [[ $INJECT -eq 1 ]]; then
    echo "Running the suite with a synthetic ritz1/ritz1_selfhosted divergence on:"
    echo "  $VICTIM  (rejected by ritz1_selfhosted, and allowlisted so Stage 4 skips it)"
else
    echo "CONTROL: running the suite with $VICTIM allowlisted but NOT rejected;"
    echo "  Stage 5 should pass and this proof should report NOT PROVEN."
fi
echo ""
cd "$ROOT_DIR" || setup_error "cd $ROOT_DIR failed"
rm -rf .regression
if [[ $INJECT -eq 1 ]]; then
    RITZ_REGRESSION_RITZ1_ALLOWLIST="$TMP_ALLOW" \
    RITZ_REGRESSION_INJECT_SELFHOSTED_REJECT="$VICTIM" \
        "$REGRESSION_SH" > "$LOG" 2>&1
else
    RITZ_REGRESSION_RITZ1_ALLOWLIST="$TMP_ALLOW" \
        "$REGRESSION_SH" > "$LOG" 2>&1
fi
rc=$?

echo "--- relevant output -------------------------------------------------"
grep -E "Stage [345]:|$VICTIM|fixed point|allowlist|regression tests" "$LOG" || true
echo "--- exit code: $rc --------------------------------------------------"
echo ""

# --- 3. assert ---------------------------------------------------------------
status=0
check() {
    if eval "$2"; then echo "ok: $1"; else echo "FAIL: $1"; status=1; fi
}

check "suite exits non-zero"                      "[[ $rc -ne 0 ]]"
check "Stage 4 reports the victim as allowlisted" \
      "grep -q '$VICTIM: self-hosted ritz1 compile failed (known, allowlisted)' '$LOG'"
check "Stage 4 itself records zero failures"      "grep -q 'Stage 4: .* 0 failed' '$LOG'"
check "Stage 5 is the stage that failed"          "grep -q 'Stage 5: FAILED' '$LOG'"
check "Stage 5 names the divergent example"       \
      "grep -q '$VICTIM: accepted by ritz1, REJECTED by ritz1_selfhosted' '$LOG'"
check "Stage 5 says the allowlist cannot help"    "grep -q 'NOT allowlistable' '$LOG'"

echo ""
if [[ $status -eq 0 ]]; then
    echo "PROVEN: an allowlist-silenced self-hosting divergence now exits 1."
else
    echo "NOT PROVEN -- Stage 5 did not catch the synthetic divergence."
    echo "--- last 60 lines of the run (its scratch is removed on exit) ---"
    tail -n 60 "$LOG"
fi
exit $status
