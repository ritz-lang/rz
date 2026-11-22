#!/bin/bash
# Self-test for ritz0/tests/test_reject_parity.py -- the expect-error
# differential (AGAST #4541).
#
# That test is the gate's only check that ritz1 rejects what ritz0 rejects,
# for the same reason, at the same place.  Its failure mode is silent: if the
# comparison absorbed a disagreement (compared verdicts only, or reported a
# position mismatch as a known gap it was not listed as), the gate would stay
# green while the property it exists to protect was false.  The Stage 5
# precedent is scripts/test-regression-stage5.sh.
#
# Running the real corpus needs a ritz1 build, which the gate does not have
# yet when this step runs (harness self-tests come before bootstrap).  So the
# test honours RITZ_REJECT_PARITY_INJECT=<compiler>:accept|position: it feeds
# synthetic compiler results through the SAME `_row_failures` the real run
# uses and runs no compiler.  This script asserts that injection turns the
# test red, naming the divergence.  Runs in a few seconds.
#
# Exit codes: 0 all assertions held, 1 otherwise.

set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3}"
TEST_FILE="ritz0/tests/test_reject_parity.py"
SCRATCH=$(mktemp -d)
trap 'rm -rf "$SCRATCH"' EXIT
OUT="$SCRATCH/pytest.log"
FAILED=0

# run_expect_red <injection> <text the failure must name>...
run_expect_red() {
    local inject="$1"
    shift
    : > "$OUT"
    if RITZ_REJECT_PARITY_INJECT="$inject" \
       "$PY" -m pytest -q -p no:cacheprovider "$TEST_FILE" >"$OUT" 2>&1; then
        echo "FAIL: injection $inject did not turn the parity test red"
        sed 's/^/      | /' "$OUT"
        FAILED=$((FAILED + 1))
        return
    fi
    local want
    for want in "$@"; do
        if ! grep -qF "$want" "$OUT"; then
            echo "FAIL: injection $inject went red, but did not name: $want"
            sed 's/^/      | /' "$OUT"
            FAILED=$((FAILED + 1))
            return
        fi
    done
    echo "ok: injection $inject goes red"
}

echo "reject-parity self-test"
echo "======================="

# One pytest invocation, three injected disagreements.  Each must be named:
#   * ritz1 accepts a row ritz0 rejects (the verdict comparison)
#   * ritz1 refuses at the wrong position (the position comparison)
#   * ritz1_selfhosted does the same (it is held separately)
run_expect_red \
    "ritz1:accept,ritz1:position,ritz1_selfhosted:position" \
    "ritz1 ACCEPTED it; ritz0 rejects it" \
    "ritz1 points at unit.ritz:" \
    "ritz1_selfhosted points at unit.ritz:"

if [[ $FAILED -ne 0 ]]; then
    echo "$FAILED self-test(s) failed"
    exit 1
fi
echo "all self-tests held"
