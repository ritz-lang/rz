#!/bin/bash
# Test env: should print environment variables
# Compare first 5 lines of env output with system env
# Scratch from mktemp -d, removed only by this trap: gates share /tmp
# (AGAST #3178), so a fixed /tmp name is shared with every other gate.
T=$(mktemp -d) || exit 1
trap 'rm -rf "$T"' EXIT

./env | head -5 > "$T"/ritz_env.out
env | head -5 > "$T"/sys_env.out
diff -q "$T"/ritz_env.out "$T"/sys_env.out || { echo "FAIL: env differs from system env"; exit 1; }

# --- argument parsing (ritzlib.argspec, AGAST #1492) ---
fail() { echo "FAIL: $*"; exit 1; }
# usage_error WANT CMD...: CMD must exit 1 with exactly WANT on stderr.
usage_error() {
  local want=$1 rc=0 err; shift
  err=$("$@" 2>&1 >/dev/null </dev/null) || rc=$?
  [[ $rc -eq 1 ]] || fail "$*: expected exit 1, got $rc"
  [[ "$err" == "$want" ]] || fail "$*: expected stderr '$want', got '$err'"
}
got=$(env -i FOO=bar ./env -0 FOO | tr '\0' '@')
[[ "$got" == 'bar@' ]] || fail "-0 FOO: got |$got|"
got=$(env -i FOO=bar ./env --null | tr '\0' '@')
[[ "$got" == 'FOO=bar@' ]] || fail "--null: got |$got|"
rc=0; ./env RITZ_ENV_SURELY_UNSET >/dev/null 2>&1 || rc=$?
[[ $rc -eq 1 ]] || fail "unset NAME: expected exit 1, got $rc"
usage_error "env: unknown option '-x'" ./env -x
usage_error "env: too many arguments (at most 1): unexpected 'B'" ./env A B
