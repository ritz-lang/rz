#!/bin/bash
# Integration tests for `uniq` — verify adjacent-line deduplication and flags.
#
# Invocation contract (from projects/ritz/build.py:run_tests):
#   * CWD = pkg_dir (this directory)
#   * A `./uniq` symlink is placed here by build.py, pointing at build/debug/uniq
#   * Any non-zero exit = test failure. Print to stderr for visibility.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

# --- default mode: drop adjacent dupes ---
got=$(printf 'a\na\nb\nb\nb\nc\n' | ./uniq)
expected=$(printf 'a\nb\nc')
[[ "$got" == "$expected" ]] || fail "default mode: expected '$expected', got '$got'"

# --- -c: prefix count ---
got=$(printf 'a\na\nb\nb\nb\nc\n' | ./uniq -c)
expected=$'2 a\n3 b\n1 c'
[[ "$got" == "$expected" ]] || fail "-c: expected '$expected', got '$got'"

# --- -d: only duplicates ---
got=$(printf 'a\na\nb\nb\nb\nc\n' | ./uniq -d)
expected=$(printf 'a\nb')
[[ "$got" == "$expected" ]] || fail "-d: expected '$expected', got '$got'"

# --- -u: only uniques ---
got=$(printf 'a\na\nb\nb\nb\nc\n' | ./uniq -u)
expected='c'
[[ "$got" == "$expected" ]] || fail "-u: expected '$expected', got '$got'"

# --- empty input: empty output ---
got=$(printf '' | ./uniq)
[[ -z "$got" ]] || fail "empty input: expected no output, got '$got'"

# --- single line, no newline: roundtrip ---
got=$(printf 'only' | ./uniq)
[[ "$got" == 'only' ]] || fail "single line no-newline: expected 'only', got '$got'"

# --- all identical: collapse to one ---
got=$(printf 'x\nx\nx\nx\n' | ./uniq)
[[ "$got" == 'x' ]] || fail "all identical: expected 'x', got '$got'"

# --- argument parsing (ritzlib.argspec, AGAST #1490) ---
# usage_error WANT CMD...: CMD must exit 1 with exactly WANT on stderr.
usage_error() {
  local want=$1 rc=0 err; shift
  err=$("$@" 2>&1 >/dev/null </dev/null) || rc=$?
  [[ $rc -eq 1 ]] || fail "$*: expected exit 1, got $rc"
  [[ "$err" == "$want" ]] || fail "$*: expected stderr '$want', got '$err'"
}
got=$(printf 'a\na\nb\n' | ./uniq --count)
[[ "$got" == $'2 a\n1 b' ]] || fail "--count: got '$got'"
usage_error "uniq: too many arguments (at most 2): unexpected 'c'" ./uniq a b c
usage_error "uniq: option '--count' doesn't accept a value" ./uniq --count=1

echo "ok - 10 uniq scenarios"
