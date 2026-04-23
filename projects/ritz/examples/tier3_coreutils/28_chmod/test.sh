#!/bin/bash
# Integration tests for `chmod` — change file mode.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
CHMOD="$(pwd)/chmod"

# --- octal mode 755 on a file ---
touch "$T/f"
"$CHMOD" 755 "$T/f"
mode=$(stat -c '%a' "$T/f")
[[ "$mode" == "755" ]] || fail "expected 755, got $mode"

# --- 600: owner only ---
"$CHMOD" 600 "$T/f"
mode=$(stat -c '%a' "$T/f")
[[ "$mode" == "600" ]] || fail "expected 600, got $mode"

# --- 644: typical file perms ---
"$CHMOD" 644 "$T/f"
mode=$(stat -c '%a' "$T/f")
[[ "$mode" == "644" ]] || fail "expected 644, got $mode"

echo "ok - 3 chmod scenarios"
