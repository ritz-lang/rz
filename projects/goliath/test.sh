#!/bin/bash
# goliath's CLI must not report success for work it did not do (AGAST #2460).
#
# goliath is a library (blob store, namespace, path) with no CLI yet (#2788).
# The binary answers --help; every command fails with "not implemented"
# rather than print a banner and exit 0. When #2788 adds put/get/ls, test
# them here.
set -u
cd "$(dirname "$0")"
BIN=build/debug/goliath
[ -x "$BIN" ] || { echo "FAIL: $BIN not built"; exit 1; }
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
# expect NAME WANT_EXIT(0|nonzero) PATTERN(or '') -- CMD...
expect() {
    local name=$1 want=$2 pat=$3; shift 4
    local out rc
    out=$("$@" 2>&1 </dev/null); rc=$?
    if [ "$want" = 0 ] && [ $rc -ne 0 ]; then
        echo "FAIL: $name: exit $rc, want 0: $out"; fails=$((fails+1)); return
    fi
    if [ "$want" = nonzero ] && [ $rc -eq 0 ]; then
        echo "FAIL: $name: exit 0 for work not done: $out"; fails=$((fails+1)); return
    fi
    if [ -n "$pat" ] && ! grep -qiE -- "$pat" <<<"$out"; then
        echo "FAIL: $name: output lacks /$pat/: $out"; fails=$((fails+1)); return
    fi
    echo "ok: $name"
}
expect help      0       'usage'           -- "$BIN" --help
expect no_args   nonzero 'usage'           -- "$BIN"
expect put       nonzero 'not implemented' -- "$BIN" put "$0"
expect get       nonzero 'not implemented' -- "$BIN" get 00
expect unknown   nonzero 'unknown command' -- "$BIN" no-such-command-2460
[ $fails -eq 0 ] || { echo "$fails goliath CLI check(s) failed"; exit 1; }
