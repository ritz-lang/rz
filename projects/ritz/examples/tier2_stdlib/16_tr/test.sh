#!/bin/bash
# Integration tests for `tr` — character translation.
#
# build.py invokes with CWD=pkg_dir and `./tr` symlinked to build/debug/tr.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

# --- case conversion via a-z → A-Z range ---
got=$(printf 'Hello World\n' | ./tr 'a-z' 'A-Z')
[[ "$got" == 'HELLO WORLD' ]] || fail "lowercase→uppercase: got '$got'"

# --- case conversion reverse ---
got=$(printf 'Hello World\n' | ./tr 'A-Z' 'a-z')
[[ "$got" == 'hello world' ]] || fail "uppercase→lowercase: got '$got'"

# --- single-char translation ---
got=$(printf 'abc\n' | ./tr 'b' 'Z')
[[ "$got" == 'aZc' ]] || fail "single-char: got '$got'"

# --- empty input ---
got=$(printf '' | ./tr 'a' 'b')
[[ -z "$got" ]] || fail "empty input: got '$got'"

# --- identity: set1 == set2 ---
got=$(printf 'hello\n' | ./tr 'a-z' 'a-z')
[[ "$got" == 'hello' ]] || fail "identity translation: got '$got'"

# --- argument parsing (ritzlib.argspec, AGAST #1490) ---
# usage_error WANT CMD...: CMD must exit 1 with exactly WANT on stderr.
usage_error() {
  local want=$1 rc=0 err; shift
  err=$("$@" 2>&1 >/dev/null </dev/null) || rc=$?
  [[ $rc -eq 1 ]] || fail "$*: expected exit 1, got $rc"
  [[ "$err" == "$want" ]] || fail "$*: expected stderr '$want', got '$err'"
}
got=$(printf 'abc\n' | ./tr -d b)
[[ "$got" == 'ac' ]] || fail "-d b: got '$got'"
usage_error "tr: missing required argument 'SET1 [SET2]'" ./tr
usage_error "tr: too many arguments (at most 2): unexpected 'c'" ./tr a b c

echo "ok - 8 tr scenarios"
