#!/bin/bash
# sage's CLI must not report success for work it did not do (AGAST #2460).
#
# sage has a lexer and parser but no interpreter (#2787), so running a file
# must fail with "not implemented" rather than print a banner and exit 0.
# When #2787 lands, replace the "not implemented" case with a real run.
set -u
cd "$(dirname "$0")"
BIN=build/debug/sage
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
printf 'console.log(6 * 7);\n' > "$TMP/t.js"
expect help       0       'usage'           -- "$BIN" --help
expect version    0       'sage'            -- "$BIN" --version
expect no_args    nonzero 'usage'           -- "$BIN"
expect run_file   nonzero 'not implemented' -- "$BIN" "$TMP/t.js"
expect missing    nonzero ''                -- "$BIN" "$TMP/no-such.js"
expect bad_flag   nonzero 'unknown option'  -- "$BIN" --no-such-flag
[ $fails -eq 0 ] || { echo "$fails sage CLI check(s) failed"; exit 1; }
