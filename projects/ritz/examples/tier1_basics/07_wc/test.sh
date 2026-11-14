#!/bin/bash
# Test wc

# Scratch from mktemp -d, removed only by this trap: gates share /tmp
# (AGAST #3178), so a fixed /tmp name is shared with every other gate.
T=$(mktemp -d) || exit 1
trap 'rm -rf "$T"' EXIT

# Create test file
echo -e "hello world\nfoo bar baz" > "$T"/ritz_test_wc.txt

# Test file counting (2 lines, 5 words, 24 bytes including newlines)
result=$(./wc "$T"/ritz_test_wc.txt)
# Should output: "2 5 24 <path>"
echo "$result" | grep -q "^2 5 24" || { echo "Failed: file counting got '$result'"; exit 1; }

# Test stdin
result=$(echo "one two three" | ./wc)
echo "$result" | grep -q "^1 3 14" || { echo "Failed: stdin got '$result'"; exit 1; }

