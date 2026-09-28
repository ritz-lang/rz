#!/bin/bash
# AGAST #1573: non-void impl methods ending in an if/loop get an implicit ret.
out=$(./method_tail_return) || exit 1
[ "$out" = "00007733" ] || { echo "unexpected output: $out"; exit 1; }
