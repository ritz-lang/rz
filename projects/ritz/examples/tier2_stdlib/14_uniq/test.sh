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

echo "ok - 7 uniq scenarios"
