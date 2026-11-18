#!/bin/bash
# Integration tests for `cut` — extract fields from each line.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

# --- -d, -f: field extraction from comma-delimited ---
got=$(printf 'a,b,c\nd,e,f\n' | ./cut -d, -f2)
expected=$(printf 'b\ne')
[[ "$got" == "$expected" ]] || fail "field 2: expected '$expected', got '$got'"

# --- first field ---
got=$(printf 'a,b,c\nd,e,f\n' | ./cut -d, -f1)
expected=$(printf 'a\nd')
[[ "$got" == "$expected" ]] || fail "field 1: expected '$expected', got '$got'"

# --- last field ---
got=$(printf 'a,b,c\nd,e,f\n' | ./cut -d, -f3)
expected=$(printf 'c\nf')
[[ "$got" == "$expected" ]] || fail "field 3: expected '$expected', got '$got'"

# --- empty input ---
got=$(printf '' | ./cut -d, -f1)
[[ -z "$got" ]] || fail "empty: got '$got'"

# --- argument parsing (ritzlib.argspec, AGAST #1490) ---
# usage_error WANT CMD...: CMD must exit 1 with exactly WANT on stderr.
usage_error() {
  local want=$1 rc=0 err; shift
  err=$("$@" 2>&1 >/dev/null </dev/null) || rc=$?
  [[ $rc -eq 1 ]] || fail "$*: expected exit 1, got $rc"
  [[ "$err" == "$want" ]] || fail "$*: expected stderr '$want', got '$err'"
}
got=$(printf 'a:b:c\n' | ./cut -d: -f2-)
[[ "$got" == 'b:c' ]] || fail "-d: -f2-: got '$got'"
usage_error "cut: option '-f' requires a value" ./cut -f
usage_error "cut: only one of -f or -c may be specified" ./cut -f 1 -c 2
usage_error "cut: you must specify a list of bytes, characters, or fields" ./cut

echo "ok - 8 cut scenarios"
