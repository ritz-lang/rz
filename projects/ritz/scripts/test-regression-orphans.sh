#!/bin/bash
# Self-test: run_test_script leaves nothing running behind it -- AGAST #3139.
#
# 59_async_net and 60_echo_server's test binaries fork a server and a client.
# When the parent bails out early (a port it could not bind, a failed connect)
# its test.sh exits while the children are still blocked in accept/connect;
# they are reparented to init and hold their ports and memory on the shared
# gate host until someone notices.  run_binary already reaps its program's
# leftovers; run_test_script had nothing.
#
# run_test_script runs test.sh in its own session (setsid), enforces the budget
# itself, and kills that whole session afterwards -- whether test.sh exited
# normally, failed, timed out, or forked a child into a process group of its
# own.  A timed-out test.sh is always reported as 137 (SIGKILL).
#
# It must not lean on `timeout(1)`, whose behaviour differs by implementation:
# GNU `timeout --signal=KILL` exits 137 and KILLs its process group; uutils
# 0.10 exits 124; uutils 0.2.2 never delivers the KILL at all and waits for
# the child to finish on its own.  So every case below runs once per
# `timeout` on PATH: the host's own, uutils if installed (/usr/bin/coreutils,
# copied under the name `timeout` -- it refuses to run via a symlink), and a
# stub that just execs its command and never times anything out.  The stub
# is the hard proof: the assertions hold with no working timeout(1) at all.
#
# Hermetic: a synthetic example in a temp dir, `sleep` as the forked child,
# a 1s test.sh budget.  Each sleeper has a unique duration so pgrep can find
# exactly it and nothing else on a shared host.
#
# Exit codes: 0 all assertions held, 1 otherwise.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

export RITZ_REGRESSION_LIB_ONLY=1
# shellcheck source=/dev/null
source "$SCRIPT_DIR/regression.sh"
# shellcheck source=selftest-ignoring-parent.sh
source "$SCRIPT_DIR/selftest-ignoring-parent.sh"

trap - EXIT
SCRATCH=$(mktemp -d)
# Unique per run: the sleepers' argv is "sleep <TAG><n>", so a concurrent run
# of this test (or anything else) can never be matched or killed by ours.
TAG="3139$$"
cleanup() {
    pkill -KILL -fx "sleep ${TAG}[0-9]+" 2>/dev/null
    rm -rf "$SCRATCH"
}
trap cleanup EXIT
BUILD_DIR="$SCRATCH/build"
EXAMPLES_DIR="$SCRATCH/examples"
mkdir -p "$BUILD_DIR" "$EXAMPLES_DIR"

# Keep the timed-out cases fast.  Production uses the 30s default.
TEST_SCRIPT_TIMEOUT=1

TESTS_RUN=0
TESTS_FAILED=0

check() {
    local desc="$1" want="$2" got="$3"
    TESTS_RUN=$((TESTS_RUN + 1))
    if [[ "$want" == "$got" ]]; then
        echo "ok: $desc"
        return 0
    fi
    echo "FAIL: $desc"
    echo "      want: $want"
    echo "      got:  $got"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    return 1
}

BIN="$SCRATCH/prog.bin"
printf '#!/bin/sh\nexit 0\n' > "$BIN"
chmod 755 "$BIN"

# Args: $1=name, $2=test.sh body.  Prints the example dir.
make_example() {
    local dir="$EXAMPLES_DIR/tier1/$1"
    mkdir -p "$dir/src"
    echo 'fn main() -> i32' > "$dir/src/main.ritz"
    printf '[package]\nname = "%s"\n' "$1" > "$dir/ritz.toml"
    printf '#!/bin/bash\n%s\n' "$2" > "$dir/test.sh"
    chmod 755 "$dir/test.sh"
    echo "$dir"
}

# Is sleeper n still alive?  Give a SIGKILL'd process a moment to be reaped.
alive() {
    local i
    for i in 1 2 3 4 5; do
        pgrep -fx "sleep ${TAG}$1" >/dev/null || { echo gone; return; }
        sleep 0.1
    done
    echo alive
}

# `timeout` implementations to run every case under: "name:dir-to-prepend".
# An empty dir means the host's own.
IMPLS=("host $(timeout --version 2>/dev/null | head -1 | tr -d '()'):")
STUB="$SCRATCH/stub"
mkdir -p "$STUB"
# Parses nothing it does not need: drops options and the duration, execs the rest.
printf '#!/bin/bash\nwhile [[ $1 == -* ]]; do shift; done\nshift\nexec "$@"\n' > "$STUB/timeout"
chmod 755 "$STUB/timeout"
IMPLS+=("no-op stub:$STUB")
if [[ -x /usr/bin/coreutils ]] && /usr/bin/coreutils timeout --version 2>/dev/null | grep -q uutils; then
    mkdir -p "$SCRATCH/uu"
    cp /usr/bin/coreutils "$SCRATCH/uu/timeout"
    IMPLS+=("$("$SCRATCH/uu/timeout" --version | head -1 | tr -d '()'):$SCRATCH/uu")
fi

ORIG_PATH=$PATH
IMPL=0
for impl in "${IMPLS[@]}"; do
    IMPL=$((IMPL + 1))
    NAME=${impl%%:*}
    dir=${impl#*:}
    PATH=${dir:+$dir:}$ORIG_PATH
    echo "--- timeout(1) = $NAME"

    # 1. test.sh exits normally with a forked child still running -- the
    #    59_async_net / 60_echo_server shape when the parent fails early.
    d=$(make_example normal_exit$IMPL "sleep ${TAG}${IMPL}1 &
    exit 0")
    run_test_script "$d" "$BIN"
    check "[$NAME] normal exit: test.sh's own status is still returned" 0 $?
    check "[$NAME] normal exit: the forked child is killed" gone "$(alive ${IMPL}1)"

    # 2. A failing test.sh keeps its exit status through the cleanup.
    d=$(make_example failing_exit$IMPL "sleep ${TAG}${IMPL}2 &
    exit 3")
    run_test_script "$d" "$BIN"
    check "[$NAME] failing exit: status 3 survives the session kill" 3 $?
    check "[$NAME] failing exit: the forked child is killed" gone "$(alive ${IMPL}2)"

    # 3. test.sh times out with a forked child.
    d=$(make_example timed_out$IMPL "sleep ${TAG}${IMPL}3 &
    sleep 15")
    t0=$SECONDS
    run_test_script "$d" "$BIN"
    rc=$?
    check "[$NAME] timeout: returns within the 1s budget, not test.sh's 15s" yes \
        "$( (( SECONDS - t0 <= 4 )) && echo yes || echo "no ($((SECONDS - t0))s)")"
    check "[$NAME] timeout: reported as SIGKILL (137)" 137 "$rc"
    check "[$NAME] timeout: the forked child is killed" gone "$(alive ${IMPL}3)"

    # 4. The child left test.sh's process group (job control gives every
    #    background job its own group), so a process-group KILL misses it.
    #    Only a session-wide kill reaches it.
    d=$(make_example own_pgrp$IMPL "set -m
    sleep ${TAG}${IMPL}4 &
    sleep 15")
    t0=$SECONDS
    run_test_script "$d" "$BIN"
    rc=$?
    check "[$NAME] own process group: returns within the 1s budget, not test.sh's 15s" yes \
        "$( (( SECONDS - t0 <= 4 )) && echo yes || echo "no ($((SECONDS - t0))s)")"
    check "[$NAME] own process group: timeout still reported as 137" 137 "$rc"
    check "[$NAME] own process group: the child is killed anyway" gone "$(alive ${IMPL}4)"
    PATH=$ORIG_PATH
done

# 5. test.sh sees default signal dispositions, as it would run by hand --
#    AGAST #3171, #3180.  Not the SIG_IGN on SIGINT/SIGQUIT that bash gives
#    an `&` job, nor what the harness's own parent ignored (a CI job starts
#    with SIGPIPE ignored).  Its exit status is the check: 0 only if nothing
#    is ignored.  Once per reset mechanism this host has, all under an
#    ignoring parent; first proving that parent's ignores do leak without one.
echo "--- test.sh signal dispositions"
d=$(make_example dispositions "grep -q 'SigIgn:.0000000000000000' /proc/self/status")
run_test_script "$d" "$BIN"
check "dispositions: nothing ignored" 0 $?
call_ignoring none run_test_script "$d" "$BIN"
check "dispositions under an ignoring parent, no reset: inherited" 1 $?
mechs=(default)
env --default-signal true 2>/dev/null && mechs+=(env)
command -v perl >/dev/null && mechs+=(perl)
for m in "${mechs[@]}"; do
    call_ignoring "$m" run_test_script "$d" "$BIN"
    check "dispositions under an ignoring parent ($m): nothing ignored" 0 $?
done

echo "===================================="
if [[ $TESTS_FAILED -eq 0 ]]; then
    echo "All $TESTS_RUN test.sh orphan assertions held."
    exit 0
fi
echo "$TESTS_FAILED of $TESTS_RUN test.sh orphan assertions FAILED."
exit 1
