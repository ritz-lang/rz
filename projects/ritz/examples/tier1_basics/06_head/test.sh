#!/bin/bash
# Test head

# Create test file with 20 lines
seq 1 20 > /tmp/ritz_test_head.txt

# Test default (10 lines)
result=$(./head /tmp/ritz_test_head.txt)
expected=$(seq 1 10)
test "$result" = "$expected" || { echo "Failed: default 10 lines"; exit 1; }

# Test -n 5
result=$(./head -n 5 /tmp/ritz_test_head.txt)
expected=$(seq 1 5)
test "$result" = "$expected" || { echo "Failed: -n 5"; exit 1; }

# Test stdin
result=$(seq 1 20 | ./head -n 3)
expected=$(seq 1 3)
test "$result" = "$expected" || { echo "Failed: stdin"; exit 1; }

rm -f /tmp/ritz_test_head.txt
