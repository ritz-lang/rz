#!/bin/bash
# Self-test for regression.sh Stage 5 — the self-hosting fixed-point check.
#
# Stage 5 asserts accepted_by_ritz1 == accepted_by_ritz1_selfhosted, and it is
# the one assertion in the suite that no allowlist entry can silence.  That
# makes it the assertion most worth protecting: a future edit that quietly
# reintroduces an escape hatch (consulting the allowlist, treating an empty set
# as agreement, downgrading a divergence to a warning) would restore exactly
# the hole this stage was written to close, and the end-to-end suite would
# still print a cheerful green because on most machines the two compilers do
# agree.
#
# Exercising Stage 5 for real costs a full ritz1 bootstrap (~6 minutes), so it
# would never be re-run during ordinary development.  Instead we source
# regression.sh for its functions (RITZ_REGRESSION_LIB_ONLY) and hand Stage 5
# synthetic accept sets.  Runs in well under a second.
#
# Exit codes: 0 all assertions held, 1 otherwise.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Source regression.sh for its helpers without running the suite.
export RITZ_REGRESSION_LIB_ONLY=1
# shellcheck source=/dev/null
source "$SCRIPT_DIR/regression.sh"

# regression.sh installs an EXIT trap that deletes its build dir, and points
# BUILD_DIR at the real .regression.  Neither is wanted here: drop the trap and
# work in a scratch dir so a test run cannot disturb a real one.
trap - EXIT
BUILD_DIR=$(mktemp -d)
trap 'rm -rf "$BUILD_DIR"' EXIT

TESTS_RUN=0
TESTS_FAILED=0

# Put Stage 5 in a known starting state with the given accept sets.
# Args: $1=newline-separated ritz1 accepts, $2=same for ritz1_selfhosted,
#       $3(optional)="no-ran" to omit the stage-ran markers.
setup_sets() {
    rm -f "$BUILD_DIR"/acceptset_*
    printf '%s\n' "$1" | grep -v '^$' > "$BUILD_DIR/acceptset_ritz1.accepted" || true
    printf '%s\n' "$2" | grep -v '^$' > "$BUILD_DIR/acceptset_ritz1_selfhosted.accepted" || true
    if [[ "${3:-}" != "no-ran" ]]; then
        echo 1 > "$BUILD_DIR/acceptset_ritz1.ran"
        echo 1 > "$BUILD_DIR/acceptset_ritz1_selfhosted.ran"
    fi
    TOTAL_PASSED=0
    TOTAL_FAILED=0
    STAGE_RESULTS=()
}

# Args: $1=description, $2=expected return code, $3=expected TOTAL_FAILED
expect() {
    local desc="$1" want_rc="$2" want_failed="$3"
    TESTS_RUN=$((TESTS_RUN + 1))
    local rc
    # Capture output via a file, NOT `$(run_stage5)`: command substitution runs
    # the function in a subshell, so its updates to TOTAL_FAILED and
    # STAGE_RESULTS would be discarded and every count assertion below would
    # read a stale 0 -- the test would then "pass" regardless of what Stage 5
    # counted, which is precisely the kind of vacuous green this suite exists
    # to prevent.
    local log="$BUILD_DIR/stage5.log"
    run_stage5 > "$log" 2>&1
    rc=$?
    if [[ $rc -ne $want_rc || $TOTAL_FAILED -ne $want_failed ]]; then
        echo "FAIL: $desc"
        echo "      want rc=$want_rc TOTAL_FAILED=$want_failed"
        echo "      got  rc=$rc TOTAL_FAILED=$TOTAL_FAILED"
        sed 's/^/      | /' "$log"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
    echo "ok: $desc"
    return 0
}

echo "Stage 5 self-test"
echo "================="

# Identical accept sets: the fixed point holds.
setup_sets $'a\nb\nc' $'a\nb\nc'
expect "identical accept sets pass" 0 0

# Order must not matter -- these are sets, not lists.
setup_sets $'c\na\nb' $'b\nc\na'
expect "accept sets compare unordered" 0 0

# The real defect, reproduced: ritz1 accepts an example its self-compiled twin
# rejects.  This is CI 33679700130 / tier5_async_49_ritzgen in miniature, and
# before Stage 5 existed it exited 0.
setup_sets $'a\nb\ntier5_async_49_ritzgen' $'a\nb'
expect "example accepted by ritz1 but not selfhosted fails" 1 1

# The other direction is equally a fixed-point violation.
setup_sets $'a\nb' $'a\nb\nz'
expect "example accepted by selfhosted but not ritz1 fails" 1 1

# Every divergent example is counted, not just the first.
setup_sets $'a\nb\nc\nd' $'a\nz'
expect "all divergent examples are counted" 1 4

# An allowlisted example still fails Stage 5.  This is the whole point: the
# allowlist is the mechanism that hid the original bug, so listing an entry
# must not change this verdict.  tier5_async_49_ritzgen is genuinely on
# regression-known-failures-ritz1.txt, so if Stage 5 consulted the allowlist at
# all this case would pass and the assertion below would catch it.
setup_sets $'tier5_async_49_ritzgen' ''
if is_known_failure ritz1 tier5_async_49_ritzgen; then
    expect "allowlisted example still fails Stage 5 (no escape hatch)" 1 1
else
    echo "SKIP: tier5_async_49_ritzgen no longer allowlisted;" \
         "pick another listed entry to keep this assertion meaningful"
fi

# Two stages that never ran produce two empty sets, which compare equal.  That
# must be reported as "not checked", never as a pass -- a green assembled from
# two things that did not happen is the failure mode this suite keeps hitting.
setup_sets '' '' no-ran
expect "missing stage-ran markers do not yield a pass" 0 0
TESTS_RUN=$((TESTS_RUN + 1))
if [[ "${STAGE_RESULTS[*]}" == *SKIPPED* ]]; then
    echo "ok: unrun stages are reported as SKIPPED, not passed"
else
    echo "FAIL: unrun stages should report SKIPPED, got: ${STAGE_RESULTS[*]}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# A legitimate zero-accept run (stages ran, nothing compiled) is agreement.
setup_sets '' ''
expect "both stages ran and accepted nothing is agreement" 0 0

echo "================="
if [[ $TESTS_FAILED -eq 0 ]]; then
    echo "All $TESTS_RUN Stage 5 assertions held."
    exit 0
fi
echo "$TESTS_FAILED of $TESTS_RUN Stage 5 assertions FAILED."
exit 1
