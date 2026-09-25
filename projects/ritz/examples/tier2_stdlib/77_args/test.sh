#!/bin/bash
# Golden tests for argdemo (examples/tier2_stdlib/77_args) — the idiomatic
# ritzlib.argspec API (AGAST #1448).
#
# Run by scripts/regression.sh once per compiler, with CWD=pkg_dir and
# ./argdemo linked to that compiler's build, so passing here under every
# stage means ritz0 and ritz1 builds agree on every case below.
set -uo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

# expect <want-exit> <want-stdout> <want-stderr> -- args...
expect() {
    local want_rc="$1" want_out="$2" want_err="$3"; shift 4
    local out err rc
    out=$(./argdemo "$@" 2>/tmp/argdemo_err.$$); rc=$?
    err=$(cat /tmp/argdemo_err.$$); rm -f /tmp/argdemo_err.$$
    [[ "$rc" == "$want_rc" ]]   || fail "argdemo $*: exit $rc, want $want_rc"
    [[ "$out" == "$want_out" ]] || fail "argdemo $*: stdout
--- got ---
$out
--- want ---
$want_out"
    [[ "$err" == "$want_err" ]] || fail "argdemo $*: stderr '$err', want '$want_err'"
}

defaults='verbose: no
quiet: no
count given: no
count: 10
name: (none)'

# --- nothing given: defaults, no positionals ---
expect 0 "args: 0
first: (none)
$defaults
items: 0" "" --

# --- short switch, short value in next arg, long --opt=value, positionals ---
expect 0 'args: 6
first: -v
verbose: yes
quiet: no
count given: yes
count: 42
name: bob
items: 2
  0: a
  1: b' "" -- -v -n 42 --name=bob a b

# --- bundled shorts, long value in next arg, -- ends options ---
expect 0 'args: 5
first: -vq
verbose: yes
quiet: yes
count given: yes
count: 7
name: (none)
items: 1
  0: -x' "" -- -vq --count 7 -- -x

# --- attached short value; last occurrence wins ---
expect 0 'args: 3
first: -n1
verbose: no
quiet: no
count given: yes
count: 3
name: (none)
items: 0' "" -- -n1 --count=2 -n3

# --- argspec_find: by long name, by short-only name, unknown ---
expect 0 "args: 1
first: --lookup=count
$defaults
lookup: 4
items: 0" "" -- --lookup=count
expect 0 "args: 1
first: --lookup=q
$defaults
lookup: 2
items: 0" "" -- --lookup=q
expect 0 "args: 1
first: --lookup=zzz
$defaults
lookup: not an option
items: 0" "" -- --lookup=zzz

# --- arg_parse_i64 over the positionals ---
expect 0 "args: 5
first: -s
$defaults
items: 3
  0: 1
  1: 2
  2: -3
sum: 0" "" -- -s -- 1 2 -3
expect 2 "args: 3
first: --sum
$defaults
items: 2
  0: 1
  1: x" "argdemo: invalid number 'x'" -- --sum 1 x

# --- every parse error, reported by arg_error_print ---
expect 2 'args: 1
first: --bogus' "argdemo: unknown option '--bogus'" -- --bogus
expect 2 'args: 1
first: -vz' "argdemo: unknown option '-z'" -- -vz
expect 2 'args: 1
first: -n' "argdemo: option '-n' requires a value" -- -n
expect 2 'args: 1
first: --count' "argdemo: option '--count' requires a value" -- --count
expect 2 'args: 1
first: --verbose=1' "argdemo: option '--verbose' doesn't accept a value" -- --verbose=1
expect 2 'args: 2
first: -n
verbose: no
quiet: no
count given: yes' "argdemo: invalid number 'abc'" -- -n abc

# --- help ---
expect 0 'args: 1
first: --help
Usage: argdemo [OPTIONS] [ITEM]...

Report how a command line parses.

Options:
  -h, --help
        Show this help
  -v, --verbose
        Say more
  -q
        Say less
  -s, --sum
        Add up the ITEMs as integers
  -n, --count=NUM
        A number (default: 10)
      --name=S
        A name
      --lookup=OPT
        Report where OPT sits in the spec

Arguments:
  ITEM
        Things to report on' "" -- --help

echo "argdemo: all cases passed"
