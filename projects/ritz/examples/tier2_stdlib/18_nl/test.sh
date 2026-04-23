#!/bin/bash
# Integration tests for `nl` — number lines.
#
# build.py invokes with CWD=pkg_dir and `./nl` symlinked to build/debug/nl.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

# --- basic numbering: coreutils-style right-aligned with tab separator ---
got=$(printf 'first\nsecond\nthird\n' | ./nl)
expected=$'     1\tfirst\n     2\tsecond\n     3\tthird'
[[ "$got" == "$expected" ]] || fail "basic numbering:\nexpected: '$expected'\ngot:      '$got'"

# --- single line ---
got=$(printf 'only\n' | ./nl)
[[ "$got" == $'     1\tonly' ]] || fail "single line: got '$got'"

# --- empty input: no output ---
got=$(printf '' | ./nl)
[[ -z "$got" ]] || fail "empty: got '$got'"

echo "ok - 3 nl scenarios"
