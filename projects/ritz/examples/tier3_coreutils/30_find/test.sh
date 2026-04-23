#!/bin/bash
# Integration tests for `find` — directory traversal.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
FIND="$(pwd)/find"

# Layout:
#   $T/a
#   $T/b/c
#   $T/b/d
mkdir -p "$T/b"
touch "$T/a" "$T/b/c" "$T/b/d"

got=$("$FIND" "$T")

# find should list both $T itself and all children
[[ "$got" == *"$T"* ]]      || fail "missing root $T in output, got:\n$got"
[[ "$got" == *"$T/a"* ]]    || fail "missing $T/a in output, got:\n$got"
[[ "$got" == *"$T/b"* ]]    || fail "missing $T/b in output, got:\n$got"
[[ "$got" == *"$T/b/c"* ]]  || fail "missing $T/b/c in output, got:\n$got"
[[ "$got" == *"$T/b/d"* ]]  || fail "missing $T/b/d in output, got:\n$got"

# Empty-dir traversal: find must at least emit the dir itself
mkdir "$T/empty"
got=$("$FIND" "$T/empty")
[[ "$got" == *"$T/empty"* ]] || fail "empty-dir find should emit the dir"

echo "ok - 6 find scenarios"
