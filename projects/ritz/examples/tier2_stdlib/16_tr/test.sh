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

echo "ok - 5 tr scenarios"
