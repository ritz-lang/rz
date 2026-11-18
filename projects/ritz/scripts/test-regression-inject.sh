#!/bin/bash
# Self-test for regression.sh's Stage 5 proof hooks (AGAST #3200).
#
# scripts/prove-stage5-divergence.sh proves end to end that a ritz1 vs
# ritz1_selfhosted divergence which a known-failure entry silences in Stage 4 still
# turns the suite red at Stage 5.  It used to get there by text-patching a
# copy of regression.sh at Stage 4's compile line.  Stage 4 was refactored
# into differential_worker, the line vanished, the patcher raised, and --
# with no `set -e` -- the proof ran the UNPATCHED suite for ~70 s and printed
# NOT PROVEN: a proof that could no longer prove anything, and said so only
# after a minute and a half of irrelevant work.
#
# The proof now drives two env-var hooks in regression.sh instead:
#   RITZ_KNOWN_FAILURES                      replaces known-failures/ (a
#                                            directory; tools/known_failures.py
#                                            honours it for every gate)
#   RITZ_REGRESSION_INJECT_SELFHOSTED_REJECT ritz1_selfhosted rejects this
#                                            example key without compiling it
#
# What must hold:
#   * unset, neither hook changes anything (the gate never sets them)
#   * a ritz1 entry in the replacement covers ritz1 and ritz1_selfhosted and
#     nothing else
#   * the reject hook rejects exactly its example, under ritz1_selfhosted
#     only, and the rejection reaches Stage 5's raw accept set
#   * the proof exits 2 at once, without running a suite, when the
#     regression.sh it is pointed at has no hooks
#
# compile_with and the run steps are stubbed; nothing is compiled.  Runs in
# well under a second.
#
# Exit codes: 0 all assertions held, 1 otherwise.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# The gate's environment must not leak in and pre-set a hook.
unset RITZ_KNOWN_FAILURES RITZ_REGRESSION_INJECT_SELFHOSTED_REJECT

export RITZ_REGRESSION_LIB_ONLY=1
# shellcheck source=/dev/null
source "$SCRIPT_DIR/regression.sh"

trap - EXIT
SCRATCH=$(mktemp -d)
trap 'rm -rf "$SCRATCH"' EXIT

ROOT_DIR="$SCRATCH/root"
BUILD_DIR="$SCRATCH/regression"
EXAMPLES_DIR="$ROOT_DIR/examples"
mkdir -p "$BUILD_DIR" "$EXAMPLES_DIR/tier1_basics/01_hello/src" \
         "$EXAMPLES_DIR/tier1_basics/02_other/src"
VICTIM_DIR="$EXAMPLES_DIR/tier1_basics/01_hello"
VICTIM="tier1_basics_01_hello"
OTHER_DIR="$EXAMPLES_DIR/tier1_basics/02_other"
OTHER="tier1_basics_02_other"
for k in "$VICTIM" "$OTHER"; do
    echo 0 > "$BUILD_DIR/stage1_${k}.exit"
    : > "$BUILD_DIR/stage1_${k}.stdout"
done

# Stubs: every compile succeeds and is logged; the worker stops right after
# the accept/reject is recorded (the run steps are not under test here).
COMPILE_LOG="$SCRATCH/compiles"
compile_with()      { echo "$1 $(basename "$2")" >> "$COMPILE_LOG"; : > "$3"; return 0; }
check_test_script() { return 1; }

TESTS_RUN=0
TESTS_FAILED=0
check() {
    local desc="$1"; shift
    TESTS_RUN=$((TESTS_RUN + 1))
    if "$@"; then
        echo "  ok   $desc"
    else
        echo "  FAIL $desc"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Run one differential worker.  Args: $1=compiler, $2=example dir
worker() {
    rm -f "$BUILD_DIR"/acceptset_* "$COMPILE_LOG"
    DIFF_COMPILER="$1" DIFF_PREFIX="t" DIFF_LABEL="$1"
    differential_worker 0 "$2" "$SCRATCH/out" > "$SCRATCH/worker.log" 2>&1
}
recorded()   { grep -qxF "$2" "$BUILD_DIR/acceptset_$1.$3" 2>/dev/null; }
compiled()   { grep -qxF "$1 $2" "$COMPILE_LOG" 2>/dev/null; }
not()        { ! "$@"; }
eq()         { [[ "$1" == "$2" ]]; }

verdict()    { known_verdict "$1" "$2" fail | cut -f1; }

echo "Hooks unset: regression.sh behaves as before"
check "the real list does not excuse the victim (ritz1)" \
      eq "$(verdict ritz1 "$VICTIM")" hard
check "the real list does not excuse the victim (ritz1_selfhosted)" \
      eq "$(verdict ritz1_selfhosted "$VICTIM")" hard
worker ritz1_selfhosted "$VICTIM_DIR"
check "ritz1_selfhosted compiles the example" compiled ritz1_selfhosted 01_hello
check "and records it accepted" recorded ritz1_selfhosted "$VICTIM" accepted

echo "RITZ_KNOWN_FAILURES"
export RITZ_KNOWN_FAILURES="$SCRATCH/known-failures"
mkdir -p "$RITZ_KNOWN_FAILURES"
printf '[[entry]]\ngate = "regression"\ncompiler = "ritz1"\nunit = "%s"\nreason = "synthetic"\nagast = 3200\n' \
    "$VICTIM" > "$RITZ_KNOWN_FAILURES/3200.toml"
check "ritz1 reads the replacement list" eq "$(verdict ritz1 "$VICTIM")" known
check "ritz1_selfhosted reads ritz1's entry in it" \
      eq "$(verdict ritz1_selfhosted "$VICTIM")" known
check "ritz0 is not excused by a ritz1 entry" eq "$(verdict ritz0 "$VICTIM")" hard
unset RITZ_KNOWN_FAILURES

echo "RITZ_REGRESSION_INJECT_SELFHOSTED_REJECT"
export RITZ_REGRESSION_INJECT_SELFHOSTED_REJECT="$VICTIM"
worker ritz1_selfhosted "$VICTIM_DIR"
check "ritz1_selfhosted records the victim rejected" \
      recorded ritz1_selfhosted "$VICTIM" rejected
check "without compiling it" not compiled ritz1_selfhosted 01_hello
check "and not accepted" not recorded ritz1_selfhosted "$VICTIM" accepted
check "the stage reports the injected rejection as a failure" \
      grep -q "$VICTIM: ritz1_selfhosted compile failed" "$SCRATCH/worker.log"
worker ritz1_selfhosted "$OTHER_DIR"
check "any other example still compiles" compiled ritz1_selfhosted 02_other
check "and is recorded accepted" recorded ritz1_selfhosted "$OTHER" accepted
worker ritz1 "$VICTIM_DIR"
check "ritz1 (Stage 3) still compiles the victim" compiled ritz1 01_hello
check "and records it accepted" recorded ritz1 "$VICTIM" accepted
unset RITZ_REGRESSION_INJECT_SELFHOSTED_REJECT

echo "prove-stage5-divergence.sh against a regression.sh without the hooks"
# A stand-in suite that has neither hook and leaves a marker if it is run.
FAKE="$SCRATCH/regression.sh"
printf '#!/bin/bash\ntouch "%s/suite-ran"\nexit 0\n' "$SCRATCH" > "$FAKE"
chmod +x "$FAKE"
PROVE_STAGE5_REGRESSION_SH="$FAKE" timeout 20 \
    bash "$SCRIPT_DIR/prove-stage5-divergence.sh" > "$SCRATCH/prove.log" 2>&1
PROVE_RC=$?
check "the proof exits 2" eq "$PROVE_RC" 2
check "without running the suite" not test -e "$SCRATCH/suite-ran"
check "and names the missing hook" \
      grep -qE 'no RITZ_[A-Z0-9_]+ hook' "$SCRATCH/prove.log"

echo ""
echo "$TESTS_RUN checks, $TESTS_FAILED failed"
[[ $TESTS_FAILED -eq 0 ]]
