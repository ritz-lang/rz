#!/bin/bash
# Test script for xargs

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
XARGS="$DIR/xargs"

echo "Testing xargs..."

# Test 1: Basic xargs with echo (default command)
echo -n "Test 1 (default echo): "
result=$(echo "a b c" | "$XARGS")
if [ "$result" = "a b c" ]; then
    echo "PASS"
else
    echo "FAIL: expected 'a b c', got '$result'"
    exit 1
fi

# Test 2: xargs with explicit echo
echo -n "Test 2 (explicit echo): "
result=$(echo "hello world" | "$XARGS" echo)
if [ "$result" = "hello world" ]; then
    echo "PASS"
else
    echo "FAIL: expected 'hello world', got '$result'"
    exit 1
fi

# Test 3: xargs with initial arguments
echo -n "Test 3 (initial args): "
result=$(echo "world" | "$XARGS" echo hello)
if [ "$result" = "hello world" ]; then
    echo "PASS"
else
    echo "FAIL: expected 'hello world', got '$result'"
    exit 1
fi

# Test 4: xargs -n1 (one argument per command)
echo -n "Test 4 (-n1): "
result=$(echo "a b c" | "$XARGS" -n1 echo)
expected="a
b
c"
if [ "$result" = "$expected" ]; then
    echo "PASS"
else
    echo "FAIL: expected '$expected', got '$result'"
    exit 1
fi

# Test 5: xargs -n2
echo -n "Test 5 (-n2): "
result=$(echo "a b c d" | "$XARGS" -n2 echo)
expected="a b
c d"
if [ "$result" = "$expected" ]; then
    echo "PASS"
else
    echo "FAIL: expected '$expected', got '$result'"
    exit 1
fi

# Test 6: xargs -0 (NUL-separated)
echo -n "Test 6 (-0 NUL-separated): "
result=$(printf "a\0b\0c" | "$XARGS" -0 echo)
if [ "$result" = "a b c" ]; then
    echo "PASS"
else
    echo "FAIL: expected 'a b c', got '$result'"
    exit 1
fi

# Test 7: xargs with newline-separated input
echo -n "Test 7 (newline-separated): "
result=$(printf "one\ntwo\nthree" | "$XARGS" echo)
if [ "$result" = "one two three" ]; then
    echo "PASS"
else
    echo "FAIL: expected 'one two three', got '$result'"
    exit 1
fi

# Test 8: xargs -0 -n1
echo -n "Test 8 (-0 -n1): "
result=$(printf "x\0y\0z" | "$XARGS" -0 -n1 echo)
expected="x
y
z"
if [ "$result" = "$expected" ]; then
    echo "PASS"
else
    echo "FAIL: expected '$expected', got '$result'"
    exit 1
fi

# Test 9: Empty input
echo -n "Test 9 (empty input): "
result=$(echo -n "" | "$XARGS" echo 2>&1 || true)
if [ -z "$result" ] || [ "$result" = "" ]; then
    echo "PASS"
else
    echo "FAIL: expected empty output, got '$result'"
    exit 1
fi

# Test 10: Multiple whitespace
echo -n "Test 10 (multiple whitespace): "
result=$(echo "  a    b   c  " | "$XARGS" echo)
if [ "$result" = "a b c" ]; then
    echo "PASS"
else
    echo "FAIL: expected 'a b c', got '$result'"
    exit 1
fi

echo "All tests passed!"
