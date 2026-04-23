#!/bin/bash
# Integration tests for `du` — disk usage summaries.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
DU="$(pwd)/du"

# --- du on an empty dir: non-empty output mentioning the path ---
mkdir "$T/empty"
got=$("$DU" "$T/empty")
[[ "$got" == *"$T/empty"* ]] || fail "expected path in output, got:\n$got"

# --- du on a non-empty dir tree ---
mkdir -p "$T/nest/a" "$T/nest/b"
printf 'data\n' > "$T/nest/a/file"
got=$("$DU" "$T/nest")
[[ "$got" == *"$T/nest"* ]] || fail "expected $T/nest in output, got:\n$got"

echo "ok - 2 du scenarios"
