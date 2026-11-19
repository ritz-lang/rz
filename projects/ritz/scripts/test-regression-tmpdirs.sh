#!/bin/bash
# Two copies of the harness self-tests, concurrently, in one /tmp -- AGAST #3178.
#
# ritz-task-3038's gate exited 2 when test-regression-testscripts.sh's scratch
# dir vanished mid-run:
#
#     regression.sh: line 252: /tmp/tmp.zsFHqeSbn7/build/test_scripts_ran.txt:
#         No such file or directory
#     FAIL: check_test_script: present but unrunnable -> 1
#
# while another room's gate ran the same self-tests a few seconds ahead of it
# in the same /tmp.  The re-run of the same SHA passed.  Up to two gates and
# six rooms share a host's /tmp, so a self-test must own its scratch outright:
# a `mktemp -d` (unique, under $TMPDIR), removed only by its own EXIT trap.
# Never a fixed /tmp name, never a glob cleanup.
#
# This runs two copies of each self-test that keeps its scratch in $TMPDIR,
# at once, in one fresh TMPDIR that also holds another run's dir (the shape of
# a concurrent gate's `mktemp -d`).  Both copies must pass, the other run's
# dir must survive untouched, and nothing may be left behind.
# tools/test_gate_tmpdirs.py is the static half: no gate-run shell names a
# /tmp path, and every self-test's scratch is a mktemp -d its trap removes.
#
# Only the self-tests that finish in about a second are paired: the rule is
# about temp dirs, which every self-test handles the same way (the static
# half checks all of them), and pairing the 25s ones would double the step.
#
# Exit codes: 0 all assertions held, 1 otherwise.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PAIRED=(env stage4 stage5 testscripts xpass)

SHARED=$(mktemp -d)
trap 'rm -rf "$SHARED"' EXIT

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

# A copy's failing assertions, then its last lines.  `tail -5` alone showed
# only the "1 of 21 failed" summary, never which assertion (AGAST #4234).
show_failure() {
    grep -A2 '^FAIL' "$1" | sed 's/^/      | /'
    tail -3 "$1" | sed 's/^/      | /'
}

echo "harness self-tests, two copies at once in one TMPDIR"
echo "===================================================="

# The shared /tmp: a fresh dir, so "left behind" is measurable, holding a dir
# that belongs to someone else.
TMP="$SHARED/tmp"
mkdir -p "$TMP"
FOREIGN=$(TMPDIR="$TMP" mktemp -d)
echo "another gate's file" > "$FOREIGN/keep"

for name in "${PAIRED[@]}"; do
    t="$SCRIPT_DIR/test-regression-$name.sh"
    if [[ ! -f "$t" ]]; then
        check "$name: self-test exists" present missing
        continue
    fi
    TMPDIR="$TMP" bash "$t" > "$SHARED/$name.a.log" 2>&1 &
    a=$!
    TMPDIR="$TMP" bash "$t" > "$SHARED/$name.b.log" 2>&1 &
    b=$!
    wait "$a"; rc_a=$?
    wait "$b"; rc_b=$?
    check "$name: copy A passes beside copy B" 0 "$rc_a" || show_failure "$SHARED/$name.a.log"
    check "$name: copy B passes beside copy A" 0 "$rc_b" || show_failure "$SHARED/$name.b.log"
done

# Two copies only collide when they happen to: a 1-in-thousands repeat passes
# a dozen reruns.  Pin bash's $RANDOM to one value in every process and fork
# (BASH_ENV runs before the script; `unset` drops its special meaning), so a
# scratch name built from $RANDOM repeats every time instead of rarely.
# test-regression-xpass.sh named its result files "$SCRATCH/r.$RANDOM"
# until AGAST #4234; a repeat handed one case another case's .verdict.
PIN="$SHARED/pin-random.bash"
printf 'unset RANDOM\nRANDOM=7\n' > "$PIN"
pids=()
for name in "${PAIRED[@]}"; do
    t="$SCRIPT_DIR/test-regression-$name.sh"
    [[ -f "$t" ]] || continue
    BASH_ENV="$PIN" TMPDIR="$TMP" bash "$t" > "$SHARED/$name.pin.log" 2>&1 &
    pids+=("$name:$!")
done
for p in "${pids[@]}"; do
    name=${p%%:*}
    wait "${p#*:}"; rc=$?
    check "$name: passes with bash RANDOM pinned to one value" 0 "$rc" \
        || show_failure "$SHARED/$name.pin.log"
done

check "another run's dir in the shared TMPDIR is untouched" \
    "another gate's file" "$(cat "$FOREIGN/keep" 2>/dev/null)"

# Each copy removed its own scratch on exit, and only its own.
left=$(find "$TMP" -mindepth 1 -maxdepth 1 ! -path "$FOREIGN" | sort)
check "no self-test leaves its scratch behind in TMPDIR" "" "$left"

echo "===================================================="
if [[ $TESTS_FAILED -eq 0 ]]; then
    echo "All $TESTS_RUN concurrent-tmpdir assertions held."
    exit 0
fi
echo "$TESTS_FAILED of $TESTS_RUN concurrent-tmpdir assertions FAILED."
exit 1
