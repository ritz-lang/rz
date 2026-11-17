#!/bin/bash
# Self-test for regression.sh's stage DRIVERS (AGAST #1838).
#
# The other self-tests cover helpers (Stage 5's set comparison, the worker's
# inject hook, the pool, Stage 4's bootstrap make).  Nothing covered what a
# compare stage does with its workers' verdicts: Stages 3 and 4 were the same
# 55 lines with the compiler swapped, and are now one function,
# run_compare_stage <stage> <compiler> <label>.  These checks hold it to:
#
#   * every example in the corpus reaches the worker exactly once, with the
#     stage's compiler, file prefix (stage<N>) and label -- including an
#     example whose path contains a space (no word-splitting)
#   * pass / fail / skip verdicts are tallied, and a worker that dies without
#     a verdict counts as a failure
#   * the stage's summary line, STAGE_RESULTS entry and TOTAL_* counters
#   * the compiler's accept set is marked as run (Stage 5 depends on it)
#   * run_stage3 and run_stage4 go through it with the right compiler
#
# differential_worker is replaced by a stub that reads the verdict from the
# example's name; nothing is compiled.  Runs in about a second.
#
# Exit codes: 0 all assertions held, 1 otherwise.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REGRESSION_SH="$SCRIPT_DIR/regression.sh"

export RITZ_REGRESSION_LIB_ONLY=1
# shellcheck source=/dev/null
source "$REGRESSION_SH"

trap - EXIT
SCRATCH=$(mktemp -d)
trap 'rm -rf "$SCRATCH"' EXIT

ROOT_DIR="$SCRATCH/root"
BUILD_DIR="$SCRATCH/regression"
EXAMPLES_DIR="$ROOT_DIR/examples"
mkdir -p "$ROOT_DIR/ritz1/build" "$BUILD_DIR" "$SCRATCH/bin"

# A corpus of five examples; the name says what the stub worker answers.
for ex in "t/a_pass" "t/b_pass" "t/c_fail" "t/d_skip" "t/e die"; do
    mkdir -p "$EXAMPLES_DIR/$ex/src"
    : > "$EXAMPLES_DIR/$ex/src/main.ritz"
done

# Workers run in subshells, so they report through files.
differential_worker() {
    local example_dir="$2" out="$3"
    printf '%s|%s|%s|%s\n' "$DIFF_COMPILER" "$DIFF_PREFIX" "$DIFF_LABEL" \
        "$example_dir" >> "$SCRATCH/seen"
    case "$example_dir" in
        *_pass) _verdict "$out" pass ;;
        *_fail) _verdict "$out" fail ;;
        *_skip) _verdict "$out" skip ;;
        *) ;;  # dies without a verdict
    esac
}

# The stub make Stage 4 calls: `make -q` says ritz1_selfhosted is current.
cat > "$SCRATCH/bin/make" <<'EOF'
#!/bin/bash
for a in "$@"; do [[ "$a" == "-q" ]] && exit 0; done
exit 1
EOF
chmod +x "$SCRATCH/bin/make"
export PATH="$SCRATCH/bin:$PATH"

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

# Output to a file, not `$(...)`: a subshell would discard STAGE_RESULTS and
# the TOTAL_* counters.
run() {
    : > "$SCRATCH/seen"
    rm -f "$BUILD_DIR"/acceptset_*
    TOTAL_PASSED=0; TOTAL_FAILED=0; TOTAL_SKIPPED=0; STAGE_RESULTS=()
    "$@" > "$SCRATCH/out" 2>&1
    RC=$?
}

seen_count()  { [[ $(grep -c . "$SCRATCH/seen") -eq "$1" ]]; }
seen_all_as() {
    [[ $(grep -c "^$1|$2|$3|" "$SCRATCH/seen") -eq 5 ]] &&
        grep -qF "|$EXAMPLES_DIR/t/e die" "$SCRATCH/seen"
}
result_is()   { [[ "${STAGE_RESULTS[*]}" == "$1" ]]; }
printed()     { grep -qxF "$1" "$SCRATCH/out"; }
totals_are()  { [[ "$TOTAL_PASSED $TOTAL_FAILED $TOTAL_SKIPPED" == "$1" ]]; }
rc_is()       { [[ "$RC" -eq "$1" ]]; }
ran_marked()  { [[ -f "$BUILD_DIR/acceptset_$1.ran" ]]; }
results_in()  { [[ $(find "$BUILD_DIR/results/$1" -name '*.verdict' | wc -l) -eq 4 ]]; }

LINE3="Stage 3: 2 passed, 2 failed, 1 skipped"
LINE4="Stage 4: 2 passed, 2 failed, 1 skipped"

echo "run_compare_stage 3 ritz1 ritz1"
run run_compare_stage 3 ritz1 "ritz1"
check "each example reaches the worker once"        seen_count 5
check "worker sees compiler, prefix, label, spaces" seen_all_as ritz1 stage3 ritz1
check "verdicts land in results/stage3"             results_in stage3
check "summary line printed"                        printed "$LINE3"
check "STAGE_RESULTS entry"                         result_is "$LINE3"
check "TOTAL_* counters (a verdict-less worker fails)" totals_are "2 2 1"
check "ritz1 accept set marked as run"              ran_marked ritz1
check "returns 0"                                   rc_is 0

echo "run_stage3"
run run_stage3
check "no ritz1: skipped, worker never called"  seen_count 0
check "no ritz1: SKIPPED entry"                 result_is "Stage 3: SKIPPED - ritz1 not available"
printf '#!/bin/sh\n' > "$ROOT_DIR/ritz1/build/ritz1"
chmod +x "$ROOT_DIR/ritz1/build/ritz1"
run run_stage3
check "ritz1: worker sees ritz1/stage3"         seen_all_as ritz1 stage3 ritz1
check "ritz1: STAGE_RESULTS entry"              result_is "$LINE3"

echo "run_stage4"
printf '#!/bin/sh\n' > "$ROOT_DIR/ritz1/build/ritz1_selfhosted"
chmod +x "$ROOT_DIR/ritz1/build/ritz1_selfhosted"
run run_stage4
check "worker sees ritz1_selfhosted/stage4"     seen_all_as ritz1_selfhosted stage4 "self-hosted ritz1"
check "STAGE_RESULTS entry"                     result_is "$LINE4"
check "TOTAL_* counters"                        totals_are "2 2 1"
check "ritz1_selfhosted accept set marked"      ran_marked ritz1_selfhosted
check "returns 0"                               rc_is 0

echo ""
echo "$TESTS_RUN checks, $TESTS_FAILED failed"
[[ $TESTS_FAILED -eq 0 ]]
