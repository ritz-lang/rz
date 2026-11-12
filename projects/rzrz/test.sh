#!/bin/bash
# rzrz CLI behaviour: exit codes, and what each command delegates to.
#
# rzrz must not report success for work it did not do (AGAST #2460).
# build/test/run/clean/compare delegate to `python3 ./rz <cmd> ...` in the
# current directory and exit with the child's status (AGAST #2790). Most
# checks run rzrz inside a scratch workspace whose `./rz` is a fake that
# prints the argv it got, so they pin the exact delegation without
# recursing into a real `./rz test rzrz` (which runs this script).
set -u
cd "$(dirname "$0")"
BIN=$PWD/build/debug/rzrz
[ -x "$BIN" ] || { echo "FAIL: $BIN not built"; exit 1; }
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

# The fake ./rz: prints its argv, echoes stdin when FAKE_RZ_STDIN=1, writes
# a line to stderr, and exits with $FAKE_RZ_EXIT (default 0).
WS=$TMP/ws
mkdir -p "$WS"
cat >"$WS/rz" <<'EOF'
import os, sys
print("ARGV:", " ".join(sys.argv[1:]), flush=True)
if os.environ.get("FAKE_RZ_STDIN") == "1":
    print("STDIN:", sys.stdin.read().strip(), flush=True)
print("FAKE-STDERR", file=sys.stderr, flush=True)
if os.environ.get("FAKE_RZ_BIG") == "1":
    sys.stderr.write("e" * (1 << 20)); sys.stderr.flush()
sys.exit(int(os.environ.get("FAKE_RZ_EXIT", "0")))
EOF

# expect NAME WANT_EXIT(0|nonzero|<n>) PATTERN(or '') -- CMD...
expect() {
    local name=$1 want=$2 pat=$3; shift 4
    local out rc
    out=$("$@" 2>&1 </dev/null); rc=$?
    if [ "$want" = nonzero ]; then
        if [ $rc -eq 0 ]; then
            echo "FAIL: $name: exit 0 for work not done: $out"; fails=$((fails+1)); return
        fi
    elif [ $rc -ne "$want" ]; then
        echo "FAIL: $name: exit $rc, want $want: $out"; fails=$((fails+1)); return
    fi
    if [ -n "$pat" ] && ! grep -qE -- "$pat" <<<"$out"; then
        echo "FAIL: $name: output lacks /$pat/: $out"; fails=$((fails+1)); return
    fi
    echo "ok: $name"
}
# rzrz run inside the fake workspace.
inws() { (cd "$WS" && exec "$BIN" "$@"); }

expect help      0       'Usage'           -- "$BIN" --help
expect version   0       'rz '             -- "$BIN" --version
expect unknown   nonzero 'Unknown command' -- "$BIN" no-such-command-2460
# list reads ./projects: run it from the workspace root.
expect list      0       'rzrz'            -- bash -c 'cd ../.. && exec "$0" list' "$BIN"
# --help no longer advertises anything as unimplemented.
if "$BIN" --help | grep -qi 'not implemented'; then
    echo "FAIL: help-no-stubs: --help still lists unimplemented commands"; fails=$((fails+1))
else
    echo "ok: help-no-stubs"
fi

# Exact delegation (anchored: nothing may follow the expected argv).
expect build         0 '^ARGV: build p --compiler ritz1$'                  -- inws build p
expect build-release 0 '^ARGV: build p --compiler ritz1 --release$'        -- inws build p --release
expect test          0 '^ARGV: test p --compiler ritz1$'                   -- inws test p
expect test-all      0 '^ARGV: test --all --compiler ritz1$'               -- inws test --all
expect run           0 '^ARGV: run p --compiler ritz1$'                    -- inws run p
expect run-release   0 '^ARGV: run p --compiler ritz1 --release$'          -- inws run p --release
expect run-passthru  0 '^ARGV: run p --compiler ritz1 -- x -y --all$'      -- inws run p -- x -y --all
expect clean         0 '^ARGV: clean p$'                                   -- inws clean p
expect clean-all     0 '^ARGV: clean --all$'                               -- inws clean --all
expect compare       0 '^ARGV: compare$'                                   -- inws compare
expect compare-tier  0 '^ARGV: compare tier2$'                             -- inws compare tier2
# The child's stderr reaches ours.
expect stderr        0 '^FAKE-STDERR$'                                     -- inws test p

# The child's exit status is ours, unchanged (not flattened to 1).
for sub in build test run clean; do
    expect "$sub-exit" 3 '^ARGV: '"$sub"' p' -- env FAKE_RZ_EXIT=3 bash -c 'cd "$1" && exec "$2" "$3" p' _ "$WS" "$BIN" "$sub"
done
expect compare-exit 4 '^ARGV: compare' -- env FAKE_RZ_EXIT=4 bash -c 'cd "$1" && exec "$2" compare' _ "$WS" "$BIN"

# A command missing its project is an error, and spawns nothing.
for sub in build test run clean; do
    expect "$sub-noproject" nonzero 'Error: Specify a project' -- inws "$sub"
    if inws "$sub" 2>&1 </dev/null | grep -q '^ARGV:'; then
        echo "FAIL: $sub-noproject: delegated anyway"; fails=$((fails+1))
    fi
done
expect run-all nonzero 'Error: Specify a project' -- inws run --all

# `run` hands the child our stdin (an interactive program must not block on
# a pipe nobody writes).
out=$(cd "$WS" && echo hello-stdin | FAKE_RZ_STDIN=1 "$BIN" run p 2>&1); rc=$?
if [ $rc -eq 0 ] && grep -q '^STDIN: hello-stdin$' <<<"$out"; then
    echo "ok: run-stdin"
else
    echo "FAIL: run-stdin: exit $rc: $out"; fails=$((fails+1))
fi

# A child that writes 1 MiB to stderr does not hang rzrz (LARB #1874 (b)):
# a pipe drained stdout-first would fill at 64 KiB and deadlock.
for sub in build test; do
    expect "$sub-big-stderr" 0 '^ARGV: ' -- env FAKE_RZ_BIG=1 timeout 30 bash -c 'cd "$1" && exec "$2" "$3" p' _ "$WS" "$BIN" "$sub"
done

# No ./rz to delegate to: an error, not a silent success.
mkdir -p "$TMP/empty"
expect no-rz nonzero '' -- bash -c 'cd "$1" && exec "$2" test p' _ "$TMP/empty" "$BIN"

[ $fails -eq 0 ] || { echo "$fails rzrz CLI check(s) failed"; exit 1; }
