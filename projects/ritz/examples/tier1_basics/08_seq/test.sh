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

# Negative numbers parse (the sign is part of the number)
result=$(./seq -2 0)
expected="-2
-1
0"
test "$result" = "$expected" || { echo "Failed: seq -2 0"; exit 1; }

# i64's minimum round-trips through strview_parse_i64 and string_push_i64
result=$(./seq -9223372036854775808 -9223372036854775808)
test "$result" = "-9223372036854775808" || { echo "Failed: seq i64 min"; exit 1; }

# A non-number is an error, not 0 (atoi's answer) or its numeric prefix
for bad in abc 12x "" 9223372036854775808; do
    result=$(./seq "$bad" 2>&1)
    status=$?
    test $status -eq 1 || { echo "Failed: seq '$bad' exited $status, want 1"; exit 1; }
    test "$result" = "seq: invalid number: '$bad'" || { echo "Failed: seq '$bad' printed '$result'"; exit 1; }
done
result=$(./seq 1 x 3 2>&1)
test "$result" = "seq: invalid number: 'x'" || { echo "Failed: seq 1 x 3"; exit 1; }
