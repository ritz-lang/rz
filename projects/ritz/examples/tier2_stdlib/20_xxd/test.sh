#!/bin/bash
# Integration tests for `xxd` — hex dump.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

# --- 2 bytes + newline = 3 bytes ("hi\n") ---
got=$(printf 'hi\n' | ./xxd)
# Classic xxd line: offset ':' bytes-in-hex (grouped) plus ASCII side
# We assert structural properties rather than exact byte-perfect equality
# in case this xxd implementation differs slightly in whitespace.
[[ "$got" == *"6869"* ]]  || fail "expected 0x68 0x69 ('hi') in hex columns, got: $got"
[[ "$got" == *"0a"*    ]] || fail "expected 0x0a (newline) in hex columns, got: $got"
[[ "$got" == *"hi"*    ]] || fail "expected 'hi' in ASCII column, got: $got"
[[ "$got" == 00000000* ]] || fail "expected offset column starting 00000000, got: $got"

# --- empty input: empty output ---
got=$(printf '' | ./xxd)
[[ -z "$got" ]] || fail "empty: got '$got'"

# --- single-char input ---
got=$(printf 'A' | ./xxd)
[[ "$got" == *"41"* ]] || fail "expected 0x41 for 'A', got: $got"
[[ "$got" == *"A"*  ]] || fail "expected 'A' in ASCII column, got: $got"

# --- argument parsing (ritzlib.argspec, AGAST #1490) ---
# usage_error WANT CMD...: CMD must exit 1 with exactly WANT on stderr.
usage_error() {
  local want=$1 rc=0 err; shift
  err=$("$@" 2>&1 >/dev/null </dev/null) || rc=$?
  [[ $rc -eq 1 ]] || fail "$*: expected exit 1, got $rc"
  [[ "$err" == "$want" ]] || fail "$*: expected stderr '$want', got '$err'"
}
got=$(printf 'abcd' | ./xxd -c 2 -g 1)
[[ "$got" == $'00000000: 61 62  ab\n00000002: 63 64  cd' ]] || fail "-c 2 -g 1: got '$got'"
usage_error "xxd: invalid number 'abc'" ./xxd -c abc
usage_error "xxd: invalid number 'x'" ./xxd -g x

echo "ok - 6 xxd scenarios"
