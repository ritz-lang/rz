#!/bin/bash
# Golden tests for osenv (examples/tier4_applications/41_osenv) — the
# idiomatic ritzlib.os.env API (AGAST #1462).
#
# Run by scripts/regression.sh once per compiler, with CWD=pkg_dir and
# ./osenv linked to that compiler's build, so passing here under every stage
# means the ritz0 and ritz1 builds agree on every case below.  `env -i` pins
# the environment so the output is a function of the program alone.
set -uo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

# expect <want-exit> <want-stdout> <want-stderr> -- env-assignments...
expect() {
    local want_rc="$1" want_out="$2" want_err="$3"; shift 4
    local out err rc errf
    errf=$(mktemp)
    out=$(env -i "$@" ./osenv 2>"$errf"); rc=$?
    err=$(cat "$errf"); rm -f "$errf"
    [[ "$rc" == "$want_rc" ]]   || fail "env -i $* ./osenv: exit $rc, want $want_rc"
    [[ "$out" == "$want_out" ]] || fail "env -i $* ./osenv: stdout
--- got ---
$out
--- want ---
$want_out"
    [[ "$err" == "$want_err" ]] || fail "env -i $* ./osenv: stderr '$err', want '$want_err'"
}

# The spec'd case: FOO set, OSENV_UNSET not, one entry, env_must succeeds.
expect 0 'FOO: bar
OSENV_UNSET: (unset)
entries: 1
must FOO: bar' '' -- FOO=bar

# env_iter counts every entry; env_get matches the whole key, not a prefix
# (FOOD must not answer for FOO) and returns an empty value as Some("").
expect 0 'FOO: x=y
OSENV_UNSET: (unset)
entries: 3
must FOO: x=y' '' -- FOOD=no FOO=x=y EMPTY=

expect 0 'FOO: 
OSENV_UNSET: (unset)
entries: 1
must FOO: ' '' -- FOO=

# env_must on a missing variable: exit 1 with the error on stderr, and
# nothing after the env_must call is printed.
expect 1 'FOO: (unset)
OSENV_UNSET: (unset)
entries: 0' 'error: required environment variable not set: FOO' --

echo PASS
