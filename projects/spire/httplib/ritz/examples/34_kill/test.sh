#!/bin/bash
# Test script for kill command

set -e

KILL="./kill"

echo "=== Testing kill -l (list signals) ==="
$KILL -l
echo ""

echo "=== Testing signal parsing ==="
# We can't really test sending signals without spawning test processes
# But we can test the argument parsing by sending to PID 0 (ourselves as group)

echo "Testing invalid signal..."
if $KILL -INVALID 1 2>/dev/null; then
    echo "FAIL: Should reject invalid signal"
    exit 1
else
    echo "PASS: Rejected invalid signal"
fi

echo "Testing invalid PID..."
if $KILL -TERM abc 2>/dev/null; then
    echo "FAIL: Should reject invalid PID"
    exit 1
else
    echo "PASS: Rejected invalid PID"
fi

echo "Testing missing PID..."
if $KILL -9 2>/dev/null; then
    echo "FAIL: Should require PID"
    exit 1
else
    echo "PASS: Required PID"
fi

echo ""
echo "=== All tests passed ==="
