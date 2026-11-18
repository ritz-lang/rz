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


# --- argument parsing (ritzlib.argspec, AGAST #1492) ---
fail() { echo "FAIL: $*"; exit 1; }
# usage_error WANT CMD...: CMD must exit 1 with exactly WANT on stderr.
usage_error() {
  local want=$1 rc=0 err; shift
  err=$("$@" 2>&1 >/dev/null </dev/null) || rc=$?
  [[ $rc -eq 1 ]] || fail "$*: expected exit 1, got $rc"
  [[ "$err" == "$want" ]] || fail "$*: expected stderr '$want', got '$err'"
}

echo -n "Test 9 (argument parsing): "
"$TEE" -h | grep -q "^Usage: tee" || fail "-h"
"$TEE" --help | grep -q -- "--append" || fail "--help lists --append"
echo one > "$TMPDIR/t9.txt"
echo two | "$TEE" --append "$TMPDIR/t9.txt" >/dev/null
[[ "$(cat "$TMPDIR/t9.txt")" == $'one\ntwo' ]] || fail "--append"
usage_error "tee: unknown option '-z'" "$TEE" -z
echo "PASS"

echo "All tests passed!"
