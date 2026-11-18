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

# --- argument parsing (ritzlib.argspec, AGAST #1490) ---
# usage_error WANT CMD...: CMD must exit 1 with exactly WANT on stderr.
usage_error() {
  local want=$1 rc=0 err; shift
  err=$("$@" 2>&1 >/dev/null </dev/null) || rc=$?
  [[ $rc -eq 1 ]] || fail "$*: expected exit 1, got $rc"
  [[ "$err" == "$want" ]] || fail "$*: expected stderr '$want', got '$err'"
}
got=$(printf 'x\n\ny\n' | ./nl -w3 -s:)
[[ "$got" == $'  1:x\n   :\n  2:y' ]] || fail "-w3 -s: got '$got'"
got=$(printf 'x\n\ny\n' | ./nl -ba --number-width=2 -n ln)
[[ "$got" == $'1 \tx\n2 \t\n3 \ty' ]] || fail "-ba --number-width=2 -n ln: got '$got'"
usage_error "nl: invalid number 'abc'" ./nl -w abc
usage_error "nl: invalid body style" ./nl -b x

# --- -w wider than any fixed buffer (AGAST #4136) ---
# The padding used to be built in a 32-byte stack buffer; -w 100000
# overran it and crashed.  Each -n format pads differently, and the blank
# line takes the unnumbered-prefix path.
W=100000
for fmt in rn ln rz; do
  case $fmt in
    rn) n1=$(printf '%*d' $W 1);  n2=$(printf '%*d' $W 2) ;;
    ln) n1=$(printf '%-*d' $W 1); n2=$(printf '%-*d' $W 2) ;;
    rz) n1=$(printf '%0*d' $W 1); n2=$(printf '%0*d' $W 2) ;;
  esac
  blank=$(printf '%*s' $W '')
  got=$(printf 'a\n\nb' | ./nl -w $W -n $fmt) || fail "-w $W -n $fmt: exit $?"
  [[ "$got" == "$n1"$'\ta\n'"$blank"$'\t\n'"$n2"$'\tb' ]] \
    || fail "-w $W -n $fmt: wrong output (${#got} bytes)"
done

echo "ok - 10 nl scenarios"
