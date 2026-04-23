#!/bin/bash
# Integration tests for `cut` — extract fields from each line.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

# --- -d, -f: field extraction from comma-delimited ---
got=$(printf 'a,b,c\nd,e,f\n' | ./cut -d, -f2)
expected=$(printf 'b\ne')
[[ "$got" == "$expected" ]] || fail "field 2: expected '$expected', got '$got'"

# --- first field ---
got=$(printf 'a,b,c\nd,e,f\n' | ./cut -d, -f1)
expected=$(printf 'a\nd')
[[ "$got" == "$expected" ]] || fail "field 1: expected '$expected', got '$got'"

# --- last field ---
got=$(printf 'a,b,c\nd,e,f\n' | ./cut -d, -f3)
expected=$(printf 'c\nf')
[[ "$got" == "$expected" ]] || fail "field 3: expected '$expected', got '$got'"

# --- empty input ---
got=$(printf '' | ./cut -d, -f1)
[[ -z "$got" ]] || fail "empty: got '$got'"

echo "ok - 4 cut scenarios"
