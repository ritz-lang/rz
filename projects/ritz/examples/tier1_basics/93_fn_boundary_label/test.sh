#!/bin/bash
# AGAST #1335: an entry-block value must never satisfy the implicit-return
# guard via a label inherited from the previous function.  z2/z3 return their
# explicit 0, not the 555.
out=$(./fn_boundary_label) || exit 1
[ "$out" = "200200" ] || { echo "unexpected output: $out"; exit 1; }
