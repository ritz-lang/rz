#!/bin/bash
# Integration tests for `sort` — lexicographic line ordering.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

# --- basic alphabetic ---
got=$(printf 'c\na\nb\n' | ./sort)
expected=$(printf 'a\nb\nc')
[[ "$got" == "$expected" ]] || fail "basic alpha: expected '$expected', got '$got'"

# --- already sorted is idempotent ---
got=$(printf 'a\nb\nc\n' | ./sort)
[[ "$got" == "$expected" ]] || fail "idempotent: got '$got'"

# --- reverse input ---
got=$(printf 'z\ny\nx\n' | ./sort)
expected=$(printf 'x\ny\nz')
[[ "$got" == "$expected" ]] || fail "reverse: got '$got'"

# --- empty ---
got=$(printf '' | ./sort)
[[ -z "$got" ]] || fail "empty: got '$got'"

# --- duplicates preserved (sort doesn't dedupe without -u) ---
got=$(printf 'b\na\na\nb\n' | ./sort)
expected=$(printf 'a\na\nb\nb')
[[ "$got" == "$expected" ]] || fail "duplicates: expected '$expected', got '$got'"

echo "ok - 5 sort scenarios"
