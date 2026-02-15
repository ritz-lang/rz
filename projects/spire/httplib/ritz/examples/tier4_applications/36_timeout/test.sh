#!/bin/bash
# Test script for timeout

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
TIMEOUT="$DIR/timeout"

echo "Testing timeout..."

# Test 1: Command that completes before timeout
echo -n "Test 1 (command completes): "
result=$("$TIMEOUT" 5 echo hello)
if [ "$result" = "hello" ]; then
    echo "PASS"
else
    echo "FAIL: expected 'hello', got '$result'"
    exit 1
fi

# Test 2: Command times out (exit code 124)
echo -n "Test 2 (command times out): "
set +e
"$TIMEOUT" 0.1 sleep 10 >/dev/null 2>&1
exit_code=$?
set -e
if [ "$exit_code" = "124" ]; then
    echo "PASS"
else
    echo "FAIL: expected exit code 124, got $exit_code"
    exit 1
fi

# Test 3: Fractional duration works
echo -n "Test 3 (fractional duration): "
start=$(date +%s.%N)
set +e
"$TIMEOUT" 0.2 sleep 10 >/dev/null 2>&1
set -e
end=$(date +%s.%N)
elapsed=$(echo "$end - $start" | bc)
# Should be about 0.2 seconds, definitely less than 1
if (( $(echo "$elapsed < 1.0" | bc -l) )); then
    echo "PASS"
else
    echo "FAIL: took too long ($elapsed seconds)"
    exit 1
fi

# Test 4: Command not found (exit code 127)
echo -n "Test 4 (command not found): "
set +e
"$TIMEOUT" 1 nonexistent_command_12345 >/dev/null 2>&1
exit_code=$?
set -e
if [ "$exit_code" = "127" ]; then
    echo "PASS"
else
    echo "FAIL: expected exit code 127, got $exit_code"
    exit 1
fi

# Test 5: Command exits with specific code
echo -n "Test 5 (exit code preserved): "
set +e
"$TIMEOUT" 5 sh -c "exit 42"
exit_code=$?
set -e
if [ "$exit_code" = "42" ]; then
    echo "PASS"
else
    echo "FAIL: expected exit code 42, got $exit_code"
    exit 1
fi

# Test 6: Kill after option (-k)
echo -n "Test 6 (kill after option): "
set +e
# Use a script that traps SIGTERM and ignores it
"$TIMEOUT" -k 0.2 0.1 sh -c 'trap "" TERM; sleep 10' >/dev/null 2>&1
exit_code=$?
set -e
# Should still exit with 124 (timed out) after SIGKILL
if [ "$exit_code" = "124" ] || [ "$exit_code" = "137" ]; then
    echo "PASS"
else
    echo "FAIL: expected exit code 124 or 137, got $exit_code"
    exit 1
fi

# Test 7: Command with arguments
echo -n "Test 7 (command with args): "
result=$("$TIMEOUT" 5 echo one two three)
if [ "$result" = "one two three" ]; then
    echo "PASS"
else
    echo "FAIL: expected 'one two three', got '$result'"
    exit 1
fi

# Test 8: Zero timeout
echo -n "Test 8 (zero timeout): "
set +e
"$TIMEOUT" 0 sleep 1 >/dev/null 2>&1
exit_code=$?
set -e
if [ "$exit_code" = "124" ]; then
    echo "PASS"
else
    echo "FAIL: expected exit code 124, got $exit_code"
    exit 1
fi

echo "All tests passed!"
