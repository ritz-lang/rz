#!/bin/bash
# Scratch from mktemp -d, removed only by this trap: gates share /tmp
# (AGAST #3178), so a fixed /tmp name is shared with every other gate.
T=$(mktemp -d) || exit 1
trap 'rm -rf "$T"' EXIT

# Test ls: basic listing
./ls . | grep -q "src" || exit 1

# Test ls: long listing
./ls -l . | grep -q "drwx" || exit 1

# Test ls: hidden files
./ls -a . | grep -q '^\.' || exit 1

# Test ls: human readable
./ls -lh . | grep -qE '[0-9]+K|[0-9]+M|[0-9]+ ' || exit 1

# Test ls: one per line
COUNT=$(./ls -1 . | wc -l)
[ "$COUNT" -ge 2 ] || exit 1

# Test ls: multiple paths
./ls . .. | grep -q "src" || exit 1

# Test ls: classify
mkdir -p "$T"/ritz_ls_test
touch "$T"/ritz_ls_test/file.txt
mkdir "$T"/ritz_ls_test/subdir
./ls -F "$T"/ritz_ls_test | grep -q "subdir/" || exit 1
