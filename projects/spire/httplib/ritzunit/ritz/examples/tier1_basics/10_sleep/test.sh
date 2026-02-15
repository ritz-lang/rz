#!/bin/bash
# Test sleep

# Test that sleep actually delays
# Sleep 0.1 seconds and verify it takes at least 100ms
start=$(date +%s%N)
./sleep 0.1
end=$(date +%s%N)
elapsed=$(( (end - start) / 1000000 ))  # Convert to ms

# Should take at least 90ms (allowing some tolerance)
if [ "$elapsed" -lt 90 ]; then
    echo "Failed: sleep 0.1 only took ${elapsed}ms"
    exit 1
fi

# Test whole second parsing
./sleep 0 || { echo "Failed: sleep 0 should exit 0"; exit 1; }
