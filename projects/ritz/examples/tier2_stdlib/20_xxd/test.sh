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

echo "ok - 3 xxd scenarios"
