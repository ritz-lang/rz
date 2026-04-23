#!/bin/bash
# Integration tests for `expand` — replace TABs with spaces.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

# --- default tab stops (8): each tab pads to next multiple of 8 ---
got=$(printf 'a\tb\n' | ./expand)
# 'a' is col 1, tab pads to col 9 (7 spaces), then 'b'
expected='a       b'
[[ "$got" == "$expected" ]] || fail "single tab: expected |$expected|, got |$got|"

# --- multiple tabs ---
got=$(printf 'a\tb\tc\n' | ./expand)
expected='a       b       c'
[[ "$got" == "$expected" ]] || fail "multiple tabs: got |$got|"

# --- no tabs: identity ---
got=$(printf 'hello world\n' | ./expand)
[[ "$got" == 'hello world' ]] || fail "identity: got |$got|"

# --- empty ---
got=$(printf '' | ./expand)
[[ -z "$got" ]] || fail "empty: got |$got|"

echo "ok - 4 expand scenarios"
