#!/bin/bash
# Integration tests for `tac` — reverse line order.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

# --- reverse basic ---
got=$(printf '1\n2\n3\n' | ./tac)
expected=$(printf '3\n2\n1')
[[ "$got" == "$expected" ]] || fail "basic reverse: expected '$expected', got '$got'"

# --- single line: identity ---
got=$(printf 'only\n' | ./tac)
[[ "$got" == 'only' ]] || fail "single line: got '$got'"

# --- empty: no output ---
got=$(printf '' | ./tac)
[[ -z "$got" ]] || fail "empty: got '$got'"

# --- long-ish sequence ---
got=$(printf 'a\nb\nc\nd\ne\n' | ./tac)
expected=$(printf 'e\nd\nc\nb\na')
[[ "$got" == "$expected" ]] || fail "5-line reverse: got '$got'"

echo "ok - 4 tac scenarios"
