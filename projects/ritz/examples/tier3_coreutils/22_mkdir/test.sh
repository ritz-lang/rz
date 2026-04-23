#!/bin/bash
# Integration tests for `mkdir` — create directories.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

# Sandbox — never modify anything outside $T.
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
MKDIR="$(pwd)/mkdir"

# --- creates a single directory ---
"$MKDIR" "$T/one"
[[ -d "$T/one" ]] || fail "did not create $T/one"

# --- error on existing directory (non-zero exit) ---
if "$MKDIR" "$T/one" 2>/dev/null; then
  fail "creating existing dir should fail without -p"
fi

# --- create a sibling ---
"$MKDIR" "$T/two"
[[ -d "$T/two" ]] || fail "did not create $T/two"

echo "ok - 3 mkdir scenarios"
