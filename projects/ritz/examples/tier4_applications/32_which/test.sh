#!/bin/bash
# Test which: should find executables in PATH
{ ./which ls | grep -q /bin/ls || ./which ls | grep -q /usr/bin/ls; } || { echo "FAIL: which ls"; exit 1; }

# --- argument parsing (ritzlib.argspec, AGAST #1492) ---
fail() { echo "FAIL: $*"; exit 1; }
# usage_error WANT CMD...: CMD must exit 1 with exactly WANT on stderr.
usage_error() {
  local want=$1 rc=0 err; shift
  err=$("$@" 2>&1 >/dev/null </dev/null) || rc=$?
  [[ $rc -eq 1 ]] || fail "$*: expected exit 1, got $rc"
  [[ "$err" == "$want" ]] || fail "$*: expected stderr '$want', got '$err'"
}
[[ $(PATH=/usr/bin:/bin ./which -a sh | wc -l) -ge 1 ]] || fail "-a sh"
[[ $(PATH=/usr/bin:/bin:/usr/bin ./which --all sh | wc -l) -ge 2 ]] || fail "--all lists every match"
rc=0; ./which ritz_surely_not_a_command >/dev/null 2>&1 || rc=$?
[[ $rc -eq 1 ]] || fail "not found: expected exit 1, got $rc"
usage_error "which: missing required argument 'NAME'" ./which
usage_error "which: unknown option '-z'" ./which -z ls
