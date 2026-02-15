#!/bin/bash
# run_all_tests.sh - Run all iris unit tests

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Running All Iris Tests ==="
echo

FAILED=0
TOTAL=0

for test_file in tests/test_*.ritz; do
    echo ">>> Running $test_file"
    if ./build_tests.sh "$test_file" 2>&1 | tail -20; then
        echo
    else
        FAILED=$((FAILED + 1))
    fi
    TOTAL=$((TOTAL + 1))
done

echo
echo "=================================="
if [ $FAILED -eq 0 ]; then
    echo "ALL TESTS PASSED ($TOTAL test files)"
else
    echo "FAILED: $FAILED out of $TOTAL test files had failures"
    exit 1
fi
