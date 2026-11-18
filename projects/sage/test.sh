#!/bin/bash
# sage's CLI must not report success for work it did not do (AGAST #2460),
# and `sage FILE.js` runs the script (AGAST #2787): exit 0 only if it ran to
# the end, exit 1 with the error on stderr if it threw or did not parse.
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
printf 'console.log("before");\nnope();\n' > "$TMP/throws.js"
printf 'let = ;\n' > "$TMP/syntax.js"
# expect_exact NAME WANT_STDOUT -- CMD...: exit 0, stdout exactly WANT_STDOUT
expect_exact() {
    local name=$1 want=$2; shift 3
    local out rc
    out=$("$@" 2>/dev/null </dev/null); rc=$?
    if [ $rc -ne 0 ] || [ "$out" != "$want" ]; then
        echo "FAIL: $name: exit $rc, stdout [$out], want exit 0 and [$want]"; fails=$((fails+1)); return
    fi
    echo "ok: $name"
}
expect help       0       'usage'           -- "$BIN" --help
expect version    0       'sage'            -- "$BIN" --version
expect no_args    nonzero 'usage'           -- "$BIN"
expect_exact run_file 42                   -- "$BIN" "$TMP/t.js"
expect throws     nonzero 'ReferenceError: nope is not defined' -- "$BIN" "$TMP/throws.js"
# Output before the throw is kept on stdout; the error goes to stderr only.
if [ "$("$BIN" "$TMP/throws.js" 2>/dev/null </dev/null)" = before ]; then
    echo "ok: throws_stdout"
else
    echo "FAIL: throws_stdout: stdout is not exactly 'before'"; fails=$((fails+1))
fi
expect syntax     nonzero 'SyntaxError'     -- "$BIN" "$TMP/syntax.js"
expect missing    nonzero ''                -- "$BIN" "$TMP/no-such.js"
expect bad_flag   nonzero 'unknown option'  -- "$BIN" --no-such-flag
[ $fails -eq 0 ] || { echo "$fails sage CLI check(s) failed"; exit 1; }
