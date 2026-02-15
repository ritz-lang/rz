#!/bin/bash
# Test script for printenv

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
PRINTENV="$DIR/printenv"

echo "Testing printenv..."

# Test 1: printenv PATH should print PATH value
echo -n "Test 1 (single variable): "
result=$("$PRINTENV" PATH)
if [ "$result" = "$PATH" ]; then
    echo "PASS"
else
    echo "FAIL: expected '$PATH', got '$result'"
    exit 1
fi

# Test 2: printenv HOME USER should print both values
echo -n "Test 2 (multiple variables): "
result=$("$PRINTENV" HOME USER)
expected="$HOME
$USER"
if [ "$result" = "$expected" ]; then
    echo "PASS"
else
    echo "FAIL: expected '$expected', got '$result'"
    exit 1
fi

# Test 3: printenv NONEXISTENT should return exit code 1
echo -n "Test 3 (missing variable): "
if "$PRINTENV" NONEXISTENT_VAR_12345 >/dev/null 2>&1; then
    echo "FAIL: expected exit code 1"
    exit 1
else
    echo "PASS"
fi

# Test 4: printenv HOME NONEXISTENT should print HOME and return exit code 1
echo -n "Test 4 (mixed found/missing): "
result=$("$PRINTENV" HOME NONEXISTENT_VAR_12345 || true)
if [ "$result" = "$HOME" ]; then
    # Verify exit code is 1
    if "$PRINTENV" HOME NONEXISTENT_VAR_12345 >/dev/null 2>&1; then
        echo "FAIL: expected exit code 1"
        exit 1
    fi
    echo "PASS"
else
    echo "FAIL: expected '$HOME', got '$result'"
    exit 1
fi

# Test 5: printenv (no args) should print all environment variables
echo -n "Test 5 (all variables): "
result=$("$PRINTENV" | head -1)
if echo "$result" | grep -q '='; then
    echo "PASS"
else
    echo "FAIL: expected output with '=', got '$result'"
    exit 1
fi

echo "All tests passed!"
