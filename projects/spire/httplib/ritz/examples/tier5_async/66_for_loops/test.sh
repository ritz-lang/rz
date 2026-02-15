#!/bin/bash
# Test for loops

expected="Counting 0 to 4:
0
1
2
3
4

Counting 1 to 5 (inclusive):
1
2
3
4
5

Sum of 1 to 10: 55"

result=$(./for_loops)
test "$result" = "$expected" || { echo "Failed: output mismatch"; echo "Expected:"; echo "$expected"; echo "Got:"; echo "$result"; exit 1; }

echo "✓ For loops test passed"
