#!/bin/bash
# Test watch: run a command once and verify it clears screen and shows output
# We use timeout to kill watch after it runs once (since it loops forever)

# Test 1: verify watch runs a command and produces output
OUTPUT=$(timeout 1 ./watch -n 1 echo hello 2>&1 || true)
echo "$OUTPUT" | grep -q "Every 1s: echo hello" || { echo "FAIL: header not found"; exit 1; }
echo "$OUTPUT" | grep -q "hello" || { echo "FAIL: command output not found"; exit 1; }

# Test 2: verify invalid interval is rejected
./watch -n 0 echo test 2>&1 | grep -q "at least 1 second" || { echo "FAIL: interval validation"; exit 1; }

echo "PASS"
