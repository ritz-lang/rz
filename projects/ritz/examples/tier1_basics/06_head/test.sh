#!/bin/bash
# Test head

# Scratch from mktemp -d, removed only by this trap: gates share /tmp
# (AGAST #3178), so a fixed /tmp name is shared with every other gate.
T=$(mktemp -d) || exit 1
trap 'rm -rf "$T"' EXIT

# Create test file with 20 lines
seq 1 20 > "$T"/ritz_test_head.txt

# Test default (10 lines)
result=$(./head "$T"/ritz_test_head.txt)
expected=$(seq 1 10)
test "$result" = "$expected" || { echo "Failed: default 10 lines"; exit 1; }

# Test -n 5
result=$(./head -n 5 "$T"/ritz_test_head.txt)
expected=$(seq 1 5)
test "$result" = "$expected" || { echo "Failed: -n 5"; exit 1; }

# Test stdin
result=$(seq 1 20 | ./head -n 3)
expected=$(seq 1 3)
test "$result" = "$expected" || { echo "Failed: stdin"; exit 1; }

