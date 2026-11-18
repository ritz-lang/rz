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

# --- argument parsing (ritzlib.argspec, AGAST #1490) ---
# usage_error WANT CMD...: CMD must exit 1 with exactly WANT on stderr.
usage_error() {
  local want=$1 rc=0 err; shift
  err=$("$@" 2>&1 >/dev/null </dev/null) || rc=$?
  [[ $rc -eq 1 ]] || fail "$*: expected exit 1, got $rc"
  [[ "$err" == "$want" ]] || fail "$*: expected stderr '$want', got '$err'"
}
got=$(printf 'a\tb\n' | ./expand -t4)
[[ "$got" == 'a   b' ]] || fail "-t4: got |$got|"
usage_error "expand: invalid number 'abc'" ./expand -t abc
usage_error "expand: option '-t' requires a value" ./expand -t

echo "ok - 7 expand scenarios"
