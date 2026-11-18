#!/bin/bash
# Test watch: run a command once and verify it clears screen and shows output
# We use timeout to kill watch after it runs once (since it loops forever)

# Test 1: verify watch runs a command and produces output
OUTPUT=$(timeout 1 ./watch -n 1 echo hello 2>&1 || true)
echo "$OUTPUT" | grep -q "Every 1s: echo hello" || { echo "FAIL: header not found"; exit 1; }
echo "$OUTPUT" | grep -q "hello" || { echo "FAIL: command output not found"; exit 1; }

# Test 2: the command inherits watch's environment (env_raw_envp, AGAST #1750)
OUTPUT=$(RITZ_WATCH_ENV_TEST=inherited timeout 1 ./watch -n 1 'echo "v=$RITZ_WATCH_ENV_TEST"' 2>&1 || true)
echo "$OUTPUT" | grep -q "v=inherited" || { echo "FAIL: environment not inherited"; exit 1; }

# Test 3: verify invalid interval is rejected
./watch -n 0 echo test 2>&1 | grep -q "at least 1 second" || { echo "FAIL: interval validation"; exit 1; }


# --- argument parsing (ritzlib.argspec, AGAST #1492) ---
fail() { echo "FAIL: $*"; exit 1; }
# usage_error WANT CMD...: CMD must exit 1 with exactly WANT on stderr.
usage_error() {
  local want=$1 rc=0 err; shift
  err=$("$@" 2>&1 >/dev/null </dev/null) || rc=$?
  [[ $rc -eq 1 ]] || fail "$*: expected exit 1, got $rc"
  [[ "$err" == "$want" ]] || fail "$*: expected stderr '$want', got '$err'"
}

OUTPUT=$(timeout 1 ./watch --interval=1 echo a b 2>&1 || true)
echo "$OUTPUT" | grep -q "Every 1s: echo a b" || fail "--interval=1 with command args"
usage_error "watch: invalid number 'abc'" ./watch -n abc echo hi
usage_error "watch: missing required argument 'COMMAND'" ./watch
usage_error "watch: missing required argument 'COMMAND'" ./watch -n 1
usage_error "watch: unknown option '-z'" ./watch -z echo

echo "PASS"
