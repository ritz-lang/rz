#!/bin/bash
# Integration tests for `base64` — RFC 4648 encoding.
#
# build.py invokes with CWD=pkg_dir and `./base64` symlinked to build/debug/base64.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

# --- encode "hello\n" (classic test vector) ---
got=$(printf 'hello\n' | ./base64)
expected='aGVsbG8K'
[[ "$got" == "$expected" ]] || fail "encode hello: expected '$expected', got '$got'"

# --- encode empty input → empty output ---
got=$(printf '' | ./base64)
[[ -z "$got" ]] || fail "encode empty: got '$got'"

# --- encode single byte ---
got=$(printf 'A' | ./base64)
[[ "$got" == 'QQ==' ]] || fail "encode 'A': got '$got'"

# --- encode two bytes (exercises single-pad boundary) ---
got=$(printf 'AB' | ./base64)
[[ "$got" == 'QUI=' ]] || fail "encode 'AB': got '$got'"

# --- encode three bytes (no pad needed) ---
got=$(printf 'ABC' | ./base64)
[[ "$got" == 'QUJD' ]] || fail "encode 'ABC': got '$got'"

# --- argument parsing (ritzlib.argspec, AGAST #1490) ---
# usage_error WANT CMD...: CMD must exit 1 with exactly WANT on stderr.
usage_error() {
  local want=$1 rc=0 err; shift
  err=$("$@" 2>&1 >/dev/null </dev/null) || rc=$?
  [[ $rc -eq 1 ]] || fail "$*: expected exit 1, got $rc"
  [[ "$err" == "$want" ]] || fail "$*: expected stderr '$want', got '$err'"
}
got=$(printf 'hello world\n' | ./base64 -w 4)
[[ "$got" == $'aGVs\nbG8g\nd29y\nbGQK' ]] || fail "-w 4: got '$got'"
usage_error "base64: invalid number 'abc'" ./base64 -w abc
usage_error "base64: too many arguments (at most 1): unexpected 'b'" ./base64 a b

echo "ok - 8 base64 scenarios"
