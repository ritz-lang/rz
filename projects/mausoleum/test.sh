#!/bin/bash
# mausoleum's integer output through the real binary (AGAST #1957).
#
# `mausoleum shell --port N` echoes N through src/main.ritz's print_i32
# before it tries to connect. Its old digit loop negated with `v = -v`,
# which wraps for i32's minimum, so -2147483648 printed as a bare "-".
# parse_int skips the '-' and 2147483648 wraps to i32's minimum, which is
# how that value reaches print_i32. Nothing listens on 127.0.0.1 here, so
# the connect fails at once; timeout guards the case where it doesn't.
set -u
cd "$(dirname "$0")"
BIN=$PWD/build/debug/mausoleum
[ -x "$BIN" ] || { echo "FAIL: $BIN not built"; exit 1; }
fails=0
for case in "0 0" "2147483647 2147483647" "2147483648 -2147483648"; do
    set -- $case
    out=$(timeout 10 "$BIN" shell --host 127.0.0.1 --port "$1" 2>&1 </dev/null)
    if grep -qF -- "Connecting to 127.0.0.1:$2," <<<"$out"; then
        echo "ok: port $1 prints $2"
    else
        echo "FAIL: port $1 should print $2: $out"
        fails=$((fails+1))
    fi
done
[ $fails -eq 0 ]
