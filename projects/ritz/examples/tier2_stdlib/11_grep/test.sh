#!/bin/bash
# Integration tests for `grep` — verify pattern matching + common flags.
#
# build.py invokes this with CWD=pkg_dir and `./grep` symlinked to build/debug/grep.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

# --- basic substring match ---
got=$(printf 'apple\nbanana\napricot\ncherry\n' | ./grep 'ap')
expected=$(printf 'apple\napricot')
[[ "$got" == "$expected" ]] || fail "basic match: expected '$expected', got '$got'"

# --- no matches → empty output, exit 1 (standard grep behavior) ---
if printf 'one\ntwo\n' | ./grep 'xyz' > /tmp/grep_out.$$ 2>/dev/null; then
  # grep found something when it shouldn't
  rm -f /tmp/grep_out.$$
  fail "no-match case should fail but succeeded"
fi
rm -f /tmp/grep_out.$$

# --- match everything ---
got=$(printf 'a\nb\nc\n' | ./grep '')
expected=$(printf 'a\nb\nc')
[[ "$got" == "$expected" ]] || fail "empty pattern matches all: expected '$expected', got '$got'"

# --- single line match ---
got=$(printf 'only line\n' | ./grep 'only')
[[ "$got" == 'only line' ]] || fail "single-line match: got '$got'"

echo "ok - 4 grep scenarios"
