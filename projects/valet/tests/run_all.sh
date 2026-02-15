#!/bin/bash
# run_all.sh - Run all Valet tests
#
# Usage:
#   ./tests/run_all.sh          # Run all tests
#   VALET=/path/to/valet ./tests/run_all.sh  # Use custom binary

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALET="${VALET:-$(dirname $DIR)/valet}"

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
        ((PASSED++))
    else
        ((FAILED++))
    fi
}

# Make test scripts executable
chmod +x "$DIR"/*.sh

# Run all tests
run_test "$DIR/test_basic.sh"
run_test "$DIR/test_multishot.sh"
run_test "$DIR/test_workers.sh"

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
