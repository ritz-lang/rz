#!/bin/bash
# AGAST #1329: functions ending in a loop with a trailing body expression
# must compile to verifier-clean IR and return the zero default.
out=$(./loop_trailing_expr) || exit 1
[ "$out" = "00000000" ] || { echo "unexpected output: $out"; exit 1; }
