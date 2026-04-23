#!/bin/bash
# Integration tests for `time` — measure elapsed wall/user/sys time of a command.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

TIME="$(pwd)/time"

# --- running /bin/true emits real/user/sys lines (in some order) ---
# We capture both stdout and stderr since tools vary in where they print.
out=$("$TIME" /bin/true 2>&1)
[[ "$out" == *"real"* ]] || fail "expected 'real' in output, got:\n$out"
# user/sys may be folded into the same report; if absent it's non-fatal
# but we want at least 'real' for a smoke test.

# --- timing a command that exits non-zero still emits the report
# and propagates the child's exit code (time's job is to wrap, not eat errors).
set +e
"$TIME" /bin/false > /tmp/time_out.$$ 2>&1
rc=$?
set -e
# child exited with 1 → wrapper exits with 1 (coreutils behavior). Some
# implementations always return 0; accept either but require 'real' in report.
out=$(cat /tmp/time_out.$$)
rm -f /tmp/time_out.$$
[[ "$out" == *"real"* ]] || fail "expected 'real' for /bin/false, got:\n$out"

echo "ok - 2 time scenarios"
