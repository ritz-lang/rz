#!/bin/bash
# Integration tests for `cp` — copy files.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
CP="$(pwd)/cp"

# --- copy empty file ---
: > "$T/empty"
"$CP" "$T/empty" "$T/empty2"
[[ -f "$T/empty2" ]] || fail "empty file not copied"

# --- copy with content ---
printf 'hello world\n' > "$T/src"
"$CP" "$T/src" "$T/dst"
diff -q "$T/src" "$T/dst" > /dev/null || fail "content mismatch after cp"

# --- overwrites existing destination ---
printf 'new content\n' > "$T/src"
"$CP" "$T/src" "$T/dst"
[[ "$(cat "$T/dst")" == "new content" ]] || fail "overwrite didn't replace content"

echo "ok - 3 cp scenarios"
