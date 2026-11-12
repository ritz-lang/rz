#!/bin/bash
# rzrz must not report success for work it did not do (AGAST #2460).
#
# build and list work. test/run/clean/compare are not implemented yet
# (#2790): each must exit non-zero saying so, not print "Testing project: X"
# and return 0. An unknown command is an error, not help with exit 0.
set -u
cd "$(dirname "$0")"
BIN=$PWD/build/debug/rzrz
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
expect version   0       'rz '             -- "$BIN" --version
for sub in test run clean compare; do
    expect "$sub"     nonzero 'not implemented' -- "$BIN" "$sub" rzrz
    expect "$sub-all" nonzero 'not implemented' -- "$BIN" "$sub" --all
done
expect unknown   nonzero 'unknown command' -- "$BIN" no-such-command-2460
# list reads ./projects: run it from the workspace root.
expect list      0       'rzrz'            -- bash -c 'cd ../.. && exec "$0" list' "$BIN"
[ $fails -eq 0 ] || { echo "$fails rzrz CLI check(s) failed"; exit 1; }
