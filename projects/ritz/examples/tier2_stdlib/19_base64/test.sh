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

echo "ok - 5 base64 scenarios"
