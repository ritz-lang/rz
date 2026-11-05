#!/bin/bash
# AGAST #1573: impl methods ending in an if/loop get an implicit ret. Since
# #1429 that means procedures; non-void methods must end in a value.
out=$(./method_tail_return) || exit 1
[ "$out" = "00007733" ] || { echo "unexpected output: $out"; exit 1; }
