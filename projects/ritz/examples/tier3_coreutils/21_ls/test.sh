#!/bin/bash
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
mkdir -p /tmp/ritz_ls_test
touch /tmp/ritz_ls_test/file.txt
mkdir /tmp/ritz_ls_test/subdir
./ls -F /tmp/ritz_ls_test | grep -q "subdir/" || exit 1
rm -rf /tmp/ritz_ls_test
