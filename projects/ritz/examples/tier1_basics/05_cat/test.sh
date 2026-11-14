#!/bin/bash
# Scratch from mktemp -d, removed only by this trap: gates share /tmp
# (AGAST #3178), so a fixed /tmp name is shared with every other gate.
T=$(mktemp -d) || exit 1
trap 'rm -rf "$T"' EXIT

# Test cat: read from file
echo "test content" > "$T"/ritz_test_cat.txt
./cat "$T"/ritz_test_cat.txt | grep -q "test content" || exit 1

# Test cat: read from stdin
echo "stdin test" | ./cat | grep -q "stdin test" || exit 1

