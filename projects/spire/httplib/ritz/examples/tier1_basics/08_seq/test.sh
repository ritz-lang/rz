#!/bin/bash
# Test seq

# Test seq LAST
result=$(./seq 5)
expected="1
2
3
4
5"
test "$result" = "$expected" || { echo "Failed: seq 5"; exit 1; }

# Test seq FIRST LAST
result=$(./seq 3 6)
expected="3
4
5
6"
test "$result" = "$expected" || { echo "Failed: seq 3 6"; exit 1; }

# Test seq FIRST INCREMENT LAST
result=$(./seq 0 2 6)
expected="0
2
4
6"
test "$result" = "$expected" || { echo "Failed: seq 0 2 6"; exit 1; }
