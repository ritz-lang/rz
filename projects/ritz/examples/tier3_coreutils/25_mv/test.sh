#!/bin/bash
# Integration tests for `mv` — rename/move files.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
MV="$(pwd)/mv"

# --- rename a file within a dir ---
printf 'payload\n' > "$T/a"
"$MV" "$T/a" "$T/b"
[[ ! -e "$T/a" ]] || fail "$T/a still exists after mv"
[[ -f "$T/b" && "$(cat "$T/b")" == "payload" ]] || fail "content lost after mv"

# --- mv between subdirs ---
mkdir -p "$T/d1" "$T/d2"
touch "$T/d1/file"
"$MV" "$T/d1/file" "$T/d2/file"
[[ ! -e "$T/d1/file" && -e "$T/d2/file" ]] || fail "cross-dir mv failed"

# --- error on non-existent source ---
if "$MV" "$T/never" "$T/dst" 2>/dev/null; then
  fail "mv of missing source should fail"
fi

echo "ok - 3 mv scenarios"
