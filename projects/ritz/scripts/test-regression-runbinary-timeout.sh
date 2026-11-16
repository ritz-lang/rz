#!/bin/bash
# Self-test: run_binary bounds every example binary on any timeout(1) -- AGAST #3157.
#
# run_binary used to bound each example with `timeout --signal=KILL`.  That
# depends on which timeout is installed: GNU exits 137 and KILLs its process
# group; uutils 0.10 KILLs but exits 124; uutils 0.2.2 (huburght) never
# delivers the KILL at all and waits for the program to finish on its own, so
# a hung example was not bounded there.  run_test_script had the same problem
# and #3139 fixed it with a watchdog `sleep` raced under `wait -n -p`;
# run_binary now shares that helper (watchdog_wait).
#
# So every case runs once per timeout(1): the host's own, uutils if installed
# (/usr/bin/coreutils, copied under the name `timeout` -- it refuses to run via
# a symlink), any listed in $RUNBINARY_EXTRA_TIMEOUTS (colon-separated paths;
# how uutils 0.2.2 was checked), and a stub that execs its command and never
# times anything out.  The stub is the hard proof: the assertions hold with no
# working timeout(1) at all.
#
# Prepending to PATH, as test-regression-orphans.sh does, cannot swap the
# timeout run_binary sees: it runs the program under `env -i
# PATH=/usr/local/bin:/usr/bin:/bin`, which resets PATH before the lookup.  So
# each non-host case re-runs this script in a user + mount namespace with the
# substitute bind-mounted over the timeout that fixed PATH resolves to.  Where
# unprivileged namespaces are unavailable, those cases are replaced by a check
# that run_binary does not invoke timeout(1) at all.
#
# Hermetic: shell-script "binaries" in a scratch dir under build/ (not /tmp),
# a 1s budget, and `sleep 15.<tag><n>` as the hang, so a broken bound costs
# 15s rather than hanging the suite, and pgrep finds exactly our sleeper and
# nothing else on a shared host.
#
# Exit codes: 0 all assertions held, 1 otherwise.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Our own arguments (--as, below); regression.sh parses whatever it is sourced with.
ARGS=("$@")
set --
export RITZ_REGRESSION_LIB_ONLY=1
# shellcheck source=/dev/null
source "$SCRIPT_DIR/regression.sh"
# shellcheck source=selftest-ignoring-parent.sh
source "$SCRIPT_DIR/selftest-ignoring-parent.sh"

trap - EXIT
mkdir -p "$SCRIPT_DIR/../build"
SCRATCH=$(mktemp -d "$SCRIPT_DIR/../build/selftest-runbinary.XXXXXX")
SCRATCH=$(cd "$SCRATCH" && pwd)
# Unique per run: a concurrent run of this test can never match ours.
TAG="3157$$"

# Case 6's stress loops (AGAST #3211; see there).  Each sets its own EXIT
# trap, so call them inside $( ).  Defined above cleanup's trap so that one
# stays the script's last (tools/test_gate_tmpdirs.py reads it as the one
# in force).
#
# stress_watchdog DIR -- 300 watchdog_wait calls on a job that lives a few
# microseconds, under an EXIT trap that leaves DIR/PID behind when it runs
# in any other process.  Prints "status" per call not returning the job's 3
# and "slow" per call that took half the 1s budget.  That short a job often
# exits just as `wait -n` starts blocking: bash's lost wakeup (AGAST #3228,
# see watchdog_wait), which lost_wakeup below provokes on purpose.
stress_watchdog() {
    local dir="$1" main=$BASHPID t0 s r
    # Expanded now: the locals are gone when the $( ) shell itself exits.
    trap "[[ \$BASHPID != $main ]] && : > $(printf %q "$dir")/\$BASHPID" EXIT
    for _ in $(seq 300); do
        t0=${EPOCHREALTIME//[!0-9]/}
        { ( for ((j = 0; j < 10; j++)); do :; done; exit 3 ) & s=$!
          watchdog_wait "$s" 1s; r=$?; } 2>/dev/null
        [[ $r == 3 ]] || echo status
        (( ${EPOCHREALTIME//[!0-9]/} - t0 < 500000 )) || echo slow
    done
}
# lost_wakeup MODE -- one watchdog_wait call on an instant job, with bash's
# lost wakeup forced: a child reaped by the SIGCHLD handler between the
# dead-job check and the blocking waitpid(-1) goes unseen until some other
# child exits.  MODE "-n": the first `wait -n` loses the job's exit, so
# waits for the job's siblings alone.  MODE "pid": the first `wait PID...`
# loses its children's exits, so first waits for any other child still
# running.  Prints "<status> <ms>"; call inside $( ), as it overrides `wait`.
lost_wakeup() {
    local mode="$1" s t0 r lost=
    wait() {
        local var p others=()
        if [[ -z "$lost" && "$mode" == -n && "$1 $2" == "-n -p" ]]; then
            lost=1
            var="$3"
            shift 3
            for p; do [[ "$p" == "$s" ]] || others+=("$p"); done
            builtin wait -n -p "$var" "${others[@]}"
            return
        fi
        if [[ -z "$lost" && "$mode" == pid && "$1" != -* ]]; then
            lost=1
            for p in $(jobs -pr); do
                [[ " $* " == *" $p "* ]] || others+=("$p")
            done
            (( ${#others[@]} )) && builtin wait -n "${others[@]}"
        fi
        builtin wait "$@"
    }
    t0=${EPOCHREALTIME//[!0-9]/}
    { ( exit 3 ) & s=$!; watchdog_wait "$s" 2s; r=$?; } 2>/dev/null
    echo "$r $(( (${EPOCHREALTIME//[!0-9]/} - t0) / 1000 ))"
}
# stress_run_binary BIN DIR -- 20 run_binary calls of BIN (prints out/err,
# exits 3) writing into DIR, under an EXIT trap that removes DIR, as cleanup
# removes $SCRATCH.  Prints one "run N: <exit> <output>;" per wrong capture.
stress_run_binary() {
    local bin="$1" dir="$2" got i
    trap "rm -rf $(printf %q "$dir")" EXIT
    for i in $(seq 20); do
        mkdir -p "$dir"
        run_binary "$bin" "$dir/out.stdout" "$dir/out.exit"
        got="$(cat "$dir/out.exit" 2>&1) $(tr '\n' ' ' < "$dir/out.stdout" 2>&1)"
        [[ "$got" == "3 out err " ]] || echo "run $i: $got;"
    done
}

cleanup() {
    pkill -KILL -fx "sleep 15\.${TAG}[0-9]+" 2>/dev/null
    rm -rf "$SCRATCH"
}
trap cleanup EXIT
BUILD_DIR="$SCRATCH/build"
mkdir -p "$BUILD_DIR"

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

# Args: $1=name, $2=body.  Prints the binary's absolute path.
make_binary() {
    local bin="$SCRATCH/bin/$1"
    mkdir -p "$SCRATCH/bin"
    printf '#!/bin/sh\n%s\n' "$2" > "$bin"
    chmod 755 "$bin"
    echo "$bin"
}

# Is sleeper n still alive?  Give a SIGKILL'd process a moment to be reaped.
alive() {
    local i
    for i in 1 2 3 4 5; do
        pgrep -fx "sleep 15\.${TAG}$1" >/dev/null || { echo gone; return; }
        sleep 0.1
    done
    echo alive
}

# The timeout run_binary's fixed PATH resolves to, symlinks followed.
HOST_TIMEOUT=$(readlink -f "$(PATH=/usr/local/bin:/usr/bin:/bin command -v timeout)")

# Inner run: `$0 --as NAME FILE` runs the cases once with FILE mounted over
# HOST_TIMEOUT.  Only ever invoked under `unshare -rm` (below).
if [[ "${ARGS[0]:-}" == "--as" ]]; then
    mount --bind "${ARGS[2]}" "$HOST_TIMEOUT" || { echo "FAIL: [${ARGS[1]}] cannot mount over $HOST_TIMEOUT"; exit 1; }
    NAME=${ARGS[1]}
else
    NAME="host $(timeout --version 2>/dev/null | head -1 | tr -d '()')"
fi

# Substitutes: "name:file".  Each runs in its own namespace.
SUBS=()
STUB="$SCRATCH/stub/timeout"
mkdir -p "$SCRATCH/stub"
# Parses nothing it does not need: drops options and the duration, execs the rest.
printf '#!/bin/bash\nwhile [[ $1 == -* ]]; do shift; done\nshift\nexec "$@"\n' > "$STUB"
chmod 755 "$STUB"
SUBS+=("no-op stub:$STUB")
add_sub() {
    local src="$1" n=${#SUBS[@]}
    mkdir -p "$SCRATCH/sub$n"
    cp "$src" "$SCRATCH/sub$n/timeout"
    "$SCRATCH/sub$n/timeout" --version 2>/dev/null | grep -q . || return 0
    SUBS+=("$("$SCRATCH/sub$n/timeout" --version | head -1 | tr -d '()'):$SCRATCH/sub$n/timeout")
}
if [[ "${ARGS[0]:-}" != "--as" ]]; then
    if [[ -x /usr/bin/coreutils ]] && /usr/bin/coreutils timeout --version 2>/dev/null | grep -q uutils; then
        add_sub /usr/bin/coreutils
    fi
    IFS=: read -ra extra <<< "${RUNBINARY_EXTRA_TIMEOUTS:-}"
    for x in "${extra[@]}"; do [[ -n "$x" ]] && add_sub "$x"; done
fi

echo "--- timeout(1) = $NAME"
out="$SCRATCH/out"
RUN_SANDBOX="$SCRATCH/sandbox"

# 1. A program that never exits is KILLed at the budget, on every timeout.
#    It forks a child first: the whole session goes, not just the program.
bin=$(make_binary hang "sleep 15.${TAG}1 &
exec sleep 15.${TAG}2")
RUN_TIMEOUT=1s
t0=$SECONDS
run_binary "$bin" "$out.stdout" "$out.exit"
check "[$NAME] hang: run_binary returns 0 (it ran)" 0 $?
check "[$NAME] hang: returns within the 1s budget, not the program's 15s" yes \
    "$( (( SECONDS - t0 <= 4 )) && echo yes || echo "no ($((SECONDS - t0))s)")"
check "[$NAME] hang: recorded as SIGKILL (137)" 137 "$(cat "$out.exit" 2>/dev/null)"
check "[$NAME] hang: marked non-terminating" 1 "$(cat "$out.exit.nonterminating" 2>/dev/null)"
check "[$NAME] hang: the program is killed" gone "$(alive 2)"
check "[$NAME] hang: its forked child is killed" gone "$(alive 1)"

# 2. A program that exits on its own keeps its status and output, and is
#    not mistaken for a hang.  RUN_TIMEOUT unset: the RUN_BUDGET default.
bin=$(make_binary exits 'echo out; echo err >&2; exit 3')
RUN_TIMEOUT=""
t0=$SECONDS
run_binary "$bin" "$out.stdout" "$out.exit"
check "[$NAME] normal exit: run_binary returns 0" 0 $?
check "[$NAME] normal exit: does not wait out the budget" yes \
    "$( (( SECONDS - t0 <= 2 )) && echo yes || echo "no ($((SECONDS - t0))s)")"
check "[$NAME] normal exit: status 3 recorded" 3 "$(cat "$out.exit" 2>/dev/null)"
check "[$NAME] normal exit: stdout and stderr captured" "out err" \
    "$(tr '\n' ' ' < "$out.stdout" | sed 's/ $//')"
check "[$NAME] normal exit: not marked non-terminating" no \
    "$([[ -e "$out.exit.nonterminating" ]] && echo yes || echo no)"

# 3. A program killed by a signal keeps 128+signal, as timeout(1) passed on.
bin=$(make_binary killed 'kill -SEGV $$')
run_binary "$bin" "$out.stdout" "$out.exit"
check "[$NAME] signalled: 139 (SIGSEGV) recorded" 139 "$(cat "$out.exit" 2>/dev/null)"

# 4. The program sees default signal dispositions, as a foreground command
#    would: an `&` job of a non-interactive bash starts with SIGINT and
#    SIGQUIT ignored, and a program can notice (or fail to die of them).
bin=$(make_binary dispositions 'grep SigIgn /proc/self/status')
run_binary "$bin" "$out.stdout" "$out.exit"
check "[$NAME] dispositions: nothing ignored" "SigIgn:	0000000000000000" "$(cat "$out.stdout")"

# 5. ...even when the harness itself started with signals ignored, as a
#    GitHub Actions job does with SIGPIPE -- AGAST #3180.  bash cannot undo
#    an ignore it inherited (`trap -` is a no-op on it), so only the exec'd
#    reset (SIGDFL) passes this.  Once per reset mechanism this host has.
#    First prove the parent really does ignore them: with no reset, they leak.
call_ignoring none run_binary "$bin" "$out.stdout" "$out.exit"
check "[$NAME] dispositions under an ignoring parent, no reset: inherited" yes \
    "$(grep -q 'SigIgn:.0000000000000000' "$out.stdout" 2>/dev/null && echo "no ($(cat "$out.stdout"))" || echo yes)"
mechs=(default)
if [[ "${ARGS[0]:-}" != "--as" ]]; then
    env --default-signal true 2>/dev/null && mechs+=(env)
    command -v perl >/dev/null && mechs+=(perl)
fi
for m in "${mechs[@]}"; do
    rm -f "$out.stdout"
    call_ignoring "$m" run_binary "$bin" "$out.stdout" "$out.exit"
    check "[$NAME] dispositions under an ignoring parent ($m): nothing ignored" \
        "SigIgn:	0000000000000000" "$(cat "$out.stdout" 2>/dev/null)"
done

# 6. Stress: the watchdog must die without running the caller's EXIT trap
#    -- AGAST #3211.  watchdog_wait used to end its watchdog `sleep` with a
#    plain `kill` (SIGTERM).  When the job is fast, that often lands before
#    the forked child has exec'd sleep, while it is still a copy of this
#    shell: bash catches the TERM and runs the inherited EXIT trap, then
#    exits.  Here that trap is cleanup, i.e. `rm -rf $SCRATCH`, racing
#    run_binary as it writes out.stdout ("[no-op stub] normal exit: stdout
#    and stderr captured" failed with out.stdout missing on a loaded gate
#    host); in regression.sh it is cleanup_build_dir.  Or bash catches it
#    and then execs sleep anyway, and the caller waits out the whole budget.
#    SIGKILL can be neither caught nor lost.  Each loop below did hit it on
#    an idle host: 40 instant jobs ran the trap 13-24 times and waited out
#    the budget 8-23 times.
#    Each loop runs in $( ) under its own EXIT trap (stress_watchdog
#    and stress_run_binary, defined above cleanup's trap), so a stray run
#    cannot be cleanup.
#    The first check also catches bash's lost wakeup -- AGAST #3228: a job
#    that exits just as `wait -n` starts blocking is reaped by the SIGCHLD
#    handler and not seen until another child exits.  With the budget
#    watchdog the only other child, that call returned the job's status a
#    whole budget late ("got: slow" on a loaded ubuntu-26.04 runner); on an
#    idle host ~0.4% of these calls hit it.  watchdog_wait's ticker
#    bounds it to one tick, and KILLs every sleep before it waits for any,
#    so a lost wakeup there finds the next exit already due.  lost_wakeup
#    provokes each case every time.
for m in -n pid; do
    read -r lw_status lw_ms <<< "$(lost_wakeup "$m")"
    check "[$NAME] lost wakeup ($m): watchdog_wait still returns the job's status" 3 "$lw_status"
    check "[$NAME] lost wakeup ($m): within a tick or so, not the 2s budget" yes \
        "$( (( lw_ms < 1000 )) && echo yes || echo "no (${lw_ms}ms)")"
done
wd_trap="$SCRATCH/wd-trap"
mkdir -p "$wd_trap"
check "[$NAME] stress: watchdog_wait x300 returns each job's status at once" "" \
    "$(echo $(stress_watchdog "$wd_trap"))"
check "[$NAME] stress: its killed watchdog never runs the caller's EXIT trap" 0 \
    "$(find "$wd_trap" -type f | wc -l)"
bin=$(make_binary exits 'echo out; echo err >&2; exit 3')
check "[$NAME] stress: run_binary x20 under a cleanup trap: status and output captured" "" \
    "$(stress_run_binary "$bin" "$SCRATCH/e2e")"

# 7. A job the budget catches before it has reached setsid() is still
#    KILLed at the budget -- AGAST #3222.  The sid names a session only once
#    the `&` job has exec'd setsid and setsid() has run; until then the job
#    is still in the harness's session, so `pkill -s SID` matched nothing and
#    `wait SID` waited for it to end on its own: unbounded for a hang.  A
#    fake setsid first on PATH stalls 15s in a builtin `read -t` (no fork:
#    the stalled process IS the would-be leader, pid SID) before it execs the
#    real one.  Where a real stall needs a budget's worth of extreme load,
#    this hits the window every time.
#    Once for run_binary and once for run_test_script, which share the bug.
REAL_SETSID=$(command -v setsid)
STALL="$SCRATCH/stall-${TAG}"
mkdir -p "$STALL"
mkfifo "$STALL/fifo"
printf '#!/bin/bash\nread -rt 15 <> %q\nexec %q "$@"\n' "$STALL/fifo" "$REAL_SETSID" > "$STALL/setsid"
chmod 755 "$STALL/setsid"
# stalled -- is a stalled fake setsid still running?
stalled() {
    local i
    for i in 1 2 3 4 5; do
        pgrep -f "stall-${TAG}/setsid" >/dev/null || { echo gone; return; }
        sleep 0.1
    done
    echo alive
}
# In ( ) so PATH and the hash table revert after.
bin=$(make_binary stalled 'exit 0')
t0=$SECONDS
( PATH="$STALL:$PATH"; hash -r; RUN_TIMEOUT=1s run_binary "$bin" "$out.stdout" "$out.exit" )
check "[$NAME] stalled before setsid: run_binary returns within the 1s budget, not the stall's 15s" yes \
    "$( (( SECONDS - t0 <= 4 )) && echo yes || echo "no ($((SECONDS - t0))s)")"
check "[$NAME] stalled before setsid: run_binary records SIGKILL (137)" 137 "$(cat "$out.exit" 2>/dev/null)"
check "[$NAME] stalled before setsid: run_binary's job is killed" gone "$(stalled)"
pkill -KILL -f "stall-${TAG}/setsid" 2>/dev/null
ex="$SCRATCH/ex-stalled"
mkdir -p "$ex"
printf '[package]\nname = "stalled"\n' > "$ex/ritz.toml"
printf 'exit 0\n' > "$ex/test.sh"
t0=$SECONDS
( PATH="$STALL:$PATH"; hash -r; TEST_SCRIPT_TIMEOUT=1 run_test_script "$ex" "$bin" ); r=$?
check "[$NAME] stalled before setsid: run_test_script returns within the 1s budget, not the stall's 15s" yes \
    "$( (( SECONDS - t0 <= 4 )) && echo yes || echo "no ($((SECONDS - t0))s)")"
check "[$NAME] stalled before setsid: run_test_script reports SIGKILL (137)" 137 "$r"
check "[$NAME] stalled before setsid: run_test_script's job is killed" gone "$(stalled)"
pkill -KILL -f "stall-${TAG}/setsid" 2>/dev/null

# 8. kill_session sweeps until a pass finds nothing -- AGAST #3222.  One
#    `pkill -s` is one /proc scan, which misses a child forked after the scan
#    read the directory by a parent it then KILLs.  That race is not
#    reproducible on demand, so a shadow pkill stands in for it: its first
#    pass "matches" (returns 0) yet kills nothing, as a pass that killed the
#    parent and missed the new child.  A single pass leaves the session
#    alive; a sweep's next pass ends it.  In $( ) so the shadow stays there.
{ setsid bash -c "sleep 15.${TAG}4 & exit 0" & s=$!; wait "$s"; } 2>/dev/null
for _ in $(seq 50); do pgrep -fx "sleep 15\.${TAG}4" >/dev/null && break; sleep 0.02; done
check "[$NAME] kill_session: a pass that misses a late fork is followed by another" gone "$(
    missed=
    pkill() { [[ -n "$missed" ]] && { command pkill "$@"; return; }; missed=1; return 0; }
    kill_session "$s"
    alive 4)"
pkill -KILL -fx "sleep 15\.${TAG}4" 2>/dev/null

if [[ "${ARGS[0]:-}" == "--as" ]]; then
    [[ $TESTS_FAILED -eq 0 ]]; exit
fi

if unshare -rm true 2>/dev/null; then
    for sub in "${SUBS[@]}"; do
        TESTS_RUN=$((TESTS_RUN + 1))
        unshare -rm bash "$0" --as "${sub%%:*}" "${sub#*:}" || TESTS_FAILED=$((TESTS_FAILED + 1))
    done
else
    echo "--- no unprivileged user namespaces: cannot swap $HOST_TIMEOUT"
    check "run_binary does not invoke timeout(1)" 0 \
        "$(declare -f run_binary | grep -cE '(^|[[:space:]])timeout[[:space:]]')"
fi

echo "===================================="
if [[ $TESTS_FAILED -eq 0 ]]; then
    echo "All $TESTS_RUN run_binary timeout assertions held."
    exit 0
fi
echo "$TESTS_FAILED of $TESTS_RUN run_binary timeout assertions FAILED."
exit 1
