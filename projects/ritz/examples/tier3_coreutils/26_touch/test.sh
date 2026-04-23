#!/bin/bash
# Integration tests for `touch` — create/update file timestamps.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
TOUCH="$(pwd)/touch"

# --- creates a nonexistent file ---
"$TOUCH" "$T/new"
[[ -f "$T/new" ]] || fail "did not create $T/new"
[[ ! -s "$T/new" ]] || fail "new file should be empty"

# --- leaves an existing file's content intact ---
printf 'keep me\n' > "$T/existing"
"$TOUCH" "$T/existing"
[[ "$(cat "$T/existing")" == "keep me" ]] || fail "touch clobbered content"

# --- multiple files in one call ---
"$TOUCH" "$T/a" "$T/b" "$T/c"
[[ -f "$T/a" && -f "$T/b" && -f "$T/c" ]] || fail "multi-arg touch missed a file"

echo "ok - 3 touch scenarios"
