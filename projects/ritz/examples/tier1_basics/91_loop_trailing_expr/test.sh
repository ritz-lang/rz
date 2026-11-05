#!/bin/bash
# AGAST #1329: functions ending in a loop with a trailing body expression
# must compile to verifier-clean IR. The zeros are each fn's explicit tail:
# #1429 made reaching the end of a `-> T` fn without a value an error.
out=$(./loop_trailing_expr) || exit 1
[ "$out" = "00000000" ] || { echo "unexpected output: $out"; exit 1; }
