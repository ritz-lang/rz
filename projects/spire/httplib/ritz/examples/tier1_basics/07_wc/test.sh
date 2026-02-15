#!/bin/bash
# Test wc

# Create test file
echo -e "hello world\nfoo bar baz" > /tmp/ritz_test_wc.txt

# Test file counting (2 lines, 5 words, 24 bytes including newlines)
result=$(./wc /tmp/ritz_test_wc.txt)
# Should output: "2 5 24 /tmp/ritz_test_wc.txt"
echo "$result" | grep -q "^2 5 24" || { echo "Failed: file counting got '$result'"; exit 1; }

# Test stdin
result=$(echo "one two three" | ./wc)
echo "$result" | grep -q "^1 3 14" || { echo "Failed: stdin got '$result'"; exit 1; }

rm -f /tmp/ritz_test_wc.txt
