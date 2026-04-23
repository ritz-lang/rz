#!/bin/bash
# Integration tests for `rm` — remove files.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
RM="$(pwd)/rm"

# --- removes an existing file ---
touch "$T/a"
[[ -e "$T/a" ]]
"$RM" "$T/a"
[[ ! -e "$T/a" ]] || fail "did not remove $T/a"

# --- removes multiple files ---
touch "$T/x" "$T/y" "$T/z"
"$RM" "$T/x" "$T/y" "$T/z"
[[ ! -e "$T/x" && ! -e "$T/y" && ! -e "$T/z" ]] || fail "multi-remove left a file behind"

# --- nonexistent file (without -f) errors ---
if "$RM" "$T/never" 2>/dev/null; then
  fail "removing nonexistent file should fail (no -f)"
fi

echo "ok - 3 rm scenarios"
