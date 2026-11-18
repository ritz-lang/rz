#!/bin/bash
# run_all.sh - Run all Valet tests
#
# Runs every test_*.sh beside it except those in EXCLUDED, each with a reason
# (AGAST #1403: it used to name 4 of 15 by hand). A new suite is run without
# touching this file. Pinned by projects/ritz/tools/test_valet_run_all.py.
#
# Usage:
#   ./test/run_all.sh          # Run all tests
#   VALET=/path/to/valet ./test/run_all.sh  # Use custom binary
#   ./test/run_all.sh --list   # Print "run <suite>" / "skip <suite> <reason>"
#
# test_basic.sh, test_multishot.sh and test_workers.sh need ab (apache2-utils)
# and test_basic.sh also wrk; without them they fail with a SETUP ERROR.

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALET="${VALET:-$(dirname "$DIR")/build/debug/valet}"

# Suites run_all.sh does not run: name -> why. Empty: every suite runs.
declare -A EXCLUDED=()

SUITES=()
for f in "$DIR"/test_*.sh; do
    name=$(basename "$f")
    if [ -n "${EXCLUDED[$name]+x}" ]; then
        [ "${1:-}" = "--list" ] && echo "skip $name ${EXCLUDED[$name]}"
    else
        SUITES+=("$f")
        [ "${1:-}" = "--list" ] && echo "run $name"
    fi
done
[ "${1:-}" = "--list" ] && exit 0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo "================================================"
echo "Valet HTTP Server Test Suite"
echo "================================================"
echo ""
echo "Using binary: $VALET"
echo ""

if [ ! -x "$VALET" ]; then
    echo -e "${RED}ERROR: Valet binary not found or not executable${NC}"
    exit 1
fi

FAILED=0
PASSED=0

run_test() {
    local test_script=$1
    local test_name=$(basename "$test_script" .sh)

    echo ""
    echo -e "${YELLOW}Running: $test_name${NC}"
    echo "----------------------------------------"

    if VALET="$VALET" bash "$test_script"; then
        PASSED=$((PASSED + 1))
    else
        FAILED=$((FAILED + 1))
    fi
}

for suite in "${SUITES[@]}"; do
    run_test "$suite"
done

# Summary
echo ""
echo "================================================"
echo "Test Summary"
echo "================================================"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All test suites passed!${NC}"
    exit 0
else
    echo -e "${RED}Some test suites failed!${NC}"
    exit 1
fi
