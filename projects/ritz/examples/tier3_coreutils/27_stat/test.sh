#!/bin/bash
# Integration tests for `stat` — file info.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
STAT="$(pwd)/stat"

# --- stat a regular file ---
printf 'xyz\n' > "$T/f"
got=$("$STAT" "$T/f")
[[ "$got" == *"File:"* ]] || fail "expected 'File:' label, got:\n$got"
[[ "$got" == *"$T/f"* ]] || fail "expected path in output, got:\n$got"
# Size is 4 bytes (xyz\n)
[[ "$got" == *"Size: 4"* ]] || fail "expected size 4, got:\n$got"

# --- stat a directory ---
mkdir "$T/d"
got=$("$STAT" "$T/d")
[[ "$got" == *"directory"* ]] || fail "expected 'directory' for dir stat, got:\n$got"

# --- missing file errors ---
if "$STAT" "$T/nope" 2>/dev/null; then
  fail "stat of missing file should fail"
fi

echo "ok - 3 stat scenarios"
