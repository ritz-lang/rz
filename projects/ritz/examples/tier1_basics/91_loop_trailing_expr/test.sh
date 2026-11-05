#!/bin/bash
# AGAST #1329: functions ending in a loop with a trailing body expression
# must compile to verifier-clean IR. The zeros are each fn's explicit tail:
# #1429 made reaching the end of a `-> T` fn without a value an error.
#
# AGAST #1336: the fields after the zeros are the positive control, in main()'s
# order. Each is worked out by hand from the source and confirmed against ritz0.
# A tail value dropped and returned as 0 shows up here and nowhere in the zeros.
expected="00000000 5 7 7 100 103 200 203 300 306 62 61 71 72 500 504 90 83 40 43 42 41 20 10 20 10 110 113 122 121"
out=$(./loop_trailing_expr) || exit 1
[ "$out" = "$expected" ] || { echo "unexpected output: $out"; exit 1; }
