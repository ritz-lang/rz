#!/bin/bash
# Test async file I/O: all tests should pass
./async_fs_test || exit 1

# Concurrent runs must not share a scratch file (AGAST #4207).  With a fixed
# /tmp name, one run's unlink landed between another's write and read and
# regression Stage 1 flaked when two gates ran this example at once.  8 copies
# at a time, 20 rounds: the old fixed paths failed ~3 runs in 480 this way.
fails=0
for _ in $(seq 20); do
    pids=()
    for _ in 1 2 3 4 5 6 7 8; do
        ./async_fs_test >/dev/null 2>&1 &
        pids+=($!)
    done
    for p in "${pids[@]}"; do
        wait "$p" || fails=$((fails + 1))
    done
done
if [ "$fails" -ne 0 ]; then
    echo "FAIL: $fails of 160 concurrent runs failed"
    exit 1
fi
echo "160 concurrent runs passed"
