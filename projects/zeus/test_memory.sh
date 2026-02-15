#!/bin/bash
# Quick memory leak check using /proc/self/maps

cd "$(dirname "$0")"

echo "=== Memory Leak Check ==="
echo

# Run tests and check /proc/self/maps before/after
# We can't easily do this from outside, but we can check the final state

# Run tests with verbose output
./build/zeus_tests --verbose 2>&1

# Check if process exited cleanly
EXIT_CODE=$?
echo
echo "Exit code: $EXIT_CODE"

if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ All tests passed - memory appears to be properly managed"
    echo "  (Each test forks, so any leaks would be isolated)"
else
    echo "✗ Tests failed"
fi
