#!/bin/bash
# Test script for tee

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
TEE="$DIR/tee"
TMPDIR=$(mktemp -d)

cleanup() {
    rm -rf "$TMPDIR"
}
trap cleanup EXIT

echo "Testing tee..."

# Test 1: Basic tee to single file
echo -n "Test 1 (single file): "
output=$(echo "hello" | "$TEE" "$TMPDIR/test1.txt")
if [ "$output" = "hello" ] && [ "$(cat "$TMPDIR/test1.txt")" = "hello" ]; then
    echo "PASS"
else
    echo "FAIL"
    exit 1
fi

# Test 2: Tee to multiple files
echo -n "Test 2 (multiple files): "
output=$(echo "world" | "$TEE" "$TMPDIR/test2a.txt" "$TMPDIR/test2b.txt")
if [ "$output" = "world" ] && \
   [ "$(cat "$TMPDIR/test2a.txt")" = "world" ] && \
   [ "$(cat "$TMPDIR/test2b.txt")" = "world" ]; then
    echo "PASS"
else
    echo "FAIL"
    exit 1
fi

# Test 3: Overwrite mode (default)
echo -n "Test 3 (overwrite): "
echo "first" | "$TEE" "$TMPDIR/test3.txt" > /dev/null
echo "second" | "$TEE" "$TMPDIR/test3.txt" > /dev/null
if [ "$(cat "$TMPDIR/test3.txt")" = "second" ]; then
    echo "PASS"
else
    echo "FAIL"
    exit 1
fi

# Test 4: Append mode
echo -n "Test 4 (append): "
echo "line1" | "$TEE" "$TMPDIR/test4.txt" > /dev/null
echo "line2" | "$TEE" -a "$TMPDIR/test4.txt" > /dev/null
expected="line1
line2"
if [ "$(cat "$TMPDIR/test4.txt")" = "$expected" ]; then
    echo "PASS"
else
    echo "FAIL"
    exit 1
fi

# Test 5: No files (just pass through)
echo -n "Test 5 (no files): "
output=$(echo "passthrough" | "$TEE")
if [ "$output" = "passthrough" ]; then
    echo "PASS"
else
    echo "FAIL"
    exit 1
fi

# Test 6: Multi-line input
echo -n "Test 6 (multi-line): "
input="line1
line2
line3"
output=$(echo "$input" | "$TEE" "$TMPDIR/test6.txt")
if [ "$output" = "$input" ] && [ "$(cat "$TMPDIR/test6.txt")" = "$input" ]; then
    echo "PASS"
else
    echo "FAIL"
    exit 1
fi

# Test 7: Binary-safe (check that it handles arbitrary bytes)
echo -n "Test 7 (binary data): "
printf 'hello\x00world' | "$TEE" "$TMPDIR/test7.bin" > "$TMPDIR/test7-stdout.bin"
if cmp -s "$TMPDIR/test7.bin" "$TMPDIR/test7-stdout.bin"; then
    echo "PASS"
else
    echo "FAIL"
    exit 1
fi

# Test 8: Help flag
echo -n "Test 8 (help): "
if "$TEE" --help 2>&1 | grep -q "Usage"; then
    echo "PASS"
else
    echo "FAIL"
    exit 1
fi

echo "All tests passed!"
