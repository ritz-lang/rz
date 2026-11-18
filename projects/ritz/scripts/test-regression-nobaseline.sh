#!/bin/bash
# Self-test: examples with no ritz0 (Stage 1) baseline still reach Stage 5
# (AGAST #1341).
#
# Stages 3 and 4 used to open each example with
#     no stage1_<key>.exit?  ->  warn "no Stage 1 baseline"; skip
# BEFORE compile_with and BEFORE record_compile_outcome.  An example ritz0
# cannot compile (allowlisted in regression-known-failures.txt) was therefore
# never shown to ritz1 or ritz1_selfhosted at all: absent from both accept
# sets, so the sets agreed and Stage 5 printed "fixed point holds (N
# examples)" with N silently short of the corpus.  On 2026-09-04 that was 9
# of 80 examples, and nothing anywhere recorded that their ritz1 behaviour was
# unknown.
#
# The fix keeps the baseline gate (there is no ritz0 output to diff, and
# inventing one is worse than skipping) but still asks both compilers to
# COMPILE such an example and records accept/reject for Stage 5.  These checks
# drive the real run_stage3 / run_stage4 / run_stage5 / differential_worker
# over a three-example corpus, one without a baseline; only compile_with and
# the run steps are stubbed.  Holds them to:
#
#   * a no-baseline example is compiled by ritz1 and by ritz1_selfhosted, its
#     outcome is recorded, and the stage still skips it (no comparison)
#   * a ritz1 vs ritz1_selfhosted divergence on it turns Stage 5 RED -- before
#     the fix this exact setup was green
#   * Stage 5's line states its denominator, and that denominator is the same
#     number as Stage 3's and Stage 4's passed+failed+skipped
#
# Runs in about a second.  Exit codes: 0 all assertions held, 1 otherwise.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

unset RITZ_REGRESSION_RITZ1_ALLOWLIST RITZ_REGRESSION_INJECT_SELFHOSTED_REJECT

export RITZ_REGRESSION_LIB_ONLY=1
# shellcheck source=/dev/null
source "$SCRIPT_DIR/regression.sh"

trap - EXIT
SCRATCH=$(mktemp -d)
trap 'rm -rf "$SCRATCH"' EXIT

ROOT_DIR="$SCRATCH/root"
BUILD_DIR="$SCRATCH/regression"
EXAMPLES_DIR="$ROOT_DIR/examples"
mkdir -p "$ROOT_DIR/ritz1/build" "$SCRATCH/bin"
for ex in t/a_base t/b_base t/c_nobase; do
    mkdir -p "$EXAMPLES_DIR/$ex/src"
    : > "$EXAMPLES_DIR/$ex/src/main.ritz"
done
NOBASE="t_c_nobase"
for c in ritz1 ritz1_selfhosted; do
    printf '#!/bin/sh\n' > "$ROOT_DIR/ritz1/build/$c"
    chmod +x "$ROOT_DIR/ritz1/build/$c"
done

# Stage 4's `make -q` probe: ritz1_selfhosted is current.
cat > "$SCRATCH/bin/make" <<'EOF'
#!/bin/bash
for a in "$@"; do [[ "$a" == "-q" ]] && exit 0; done
exit 1
EOF
chmod +x "$SCRATCH/bin/make"
export PATH="$SCRATCH/bin:$PATH"

# Stubs.  compile_with logs "<compiler> <key>" and accepts, unless the key is
# listed in $SCRATCH/reject_<compiler>.  The run steps always agree.
COMPILE_LOG="$SCRATCH/compiles"
compile_with() {
    local k
    k=$(example_key "$2")
    echo "$1 $k" >> "$COMPILE_LOG"
    grep -qxF "$k" "$SCRATCH/reject_$1" 2>/dev/null && return 1
    : > "$3"
}
check_test_script() { return 0; }
run_binary()        { : > "$2"; echo 0 > "$3"; }
compare_runs()      { return 0; }

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
        sed 's/^/       | /' "$SCRATCH/out"
    fi
}

# Fresh build dir with Stage 1 baselines for the two *_base examples only,
# then Stages 3, 4, 5.  Output to a file: a $(...) subshell would discard
# STAGE_RESULTS and the TOTAL_* counters.
run_suite() {
    rm -rf "$BUILD_DIR" "$COMPILE_LOG"
    mkdir -p "$BUILD_DIR"
    local k
    for k in t_a_base t_b_base; do
        echo 0 > "$BUILD_DIR/stage1_${k}.exit"
        : > "$BUILD_DIR/stage1_${k}.stdout"
    done
    TOTAL_PASSED=0; TOTAL_FAILED=0; TOTAL_SKIPPED=0; STAGE_RESULTS=()
    { run_stage3; run_stage4; run_stage5; } > "$SCRATCH/out" 2>&1
    RC5=$?
}

compiled()  { grep -qxF "$1 $2" "$COMPILE_LOG" 2>/dev/null; }
recorded()  { grep -qxF "$2" "$BUILD_DIR/acceptset_$1.$3" 2>/dev/null; }
rc5_is()    { [[ "$RC5" -eq "$1" ]]; }
stage_line() {
    local r
    for r in "${STAGE_RESULTS[@]}"; do
        [[ "$r" == "Stage $1:"* ]] && { echo "$r"; return 0; }
    done
    return 1
}
line_is()   { [[ "$(stage_line "$1")" == "$2" ]]; }
# Stage N's "P passed, F failed, S skipped" summed.
tally_total() {
    local l
    l=$(stage_line "$1")
    [[ "$l" =~ ([0-9]+)\ passed,\ ([0-9]+)\ failed,\ ([0-9]+)\ skipped ]] || return 1
    echo $(( BASH_REMATCH[1] + BASH_REMATCH[2] + BASH_REMATCH[3] ))
}
# The denominator Stage 5 states ("over all N examples").
stage5_denominator() {
    [[ "$(stage_line 5)" =~ over\ all\ ([0-9]+)\ examples ]] || return 1
    echo "${BASH_REMATCH[1]}"
}
denominator_matches_tally() {
    local d t3 t4
    d=$(stage5_denominator) || return 1
    t3=$(tally_total 3) || return 1
    t4=$(tally_total 4) || return 1
    [[ "$d" -eq "$t3" && "$d" -eq "$t4" && "$d" -eq "$(get_examples | wc -l)" ]]
}
# "A accepted by both, R rejected by both" must add up to the denominator.
stage5_parts_add_up() {
    local d
    d=$(stage5_denominator) || return 1
    [[ "$(stage_line 5)" =~ ([0-9]+)\ accepted\ by\ both,\ ([0-9]+)\ rejected\ by\ both ]] ||
        return 1
    [[ $(( BASH_REMATCH[1] + BASH_REMATCH[2] )) -eq "$d" ]]
}

echo "Both compilers accept everything"
rm -f "$SCRATCH"/reject_*
run_suite
check "ritz1 is asked to compile the no-baseline example"   compiled ritz1 "$NOBASE"
check "ritz1_selfhosted is asked too"                       compiled ritz1_selfhosted "$NOBASE"
check "ritz1's acceptance is recorded for Stage 5"          recorded ritz1 "$NOBASE" accepted
check "ritz1_selfhosted's acceptance is recorded"           recorded ritz1_selfhosted "$NOBASE" accepted
check "it is still skipped, not compared (no baseline)"     line_is 3 "Stage 3: 2 passed, 0 failed, 1 skipped"
check "Stage 4 likewise"                                    line_is 4 "Stage 4: 2 passed, 0 failed, 1 skipped"
check "the skip says what was recorded" \
      grep -qF "$NOBASE: no Stage 1 baseline; ritz1 accepted it" "$SCRATCH/out"
check "Stage 5 passes"                                      rc5_is 0
check "Stage 5 states its denominator and breakdown" \
      line_is 5 "Stage 5: fixed point holds over all 3 examples (3 accepted by both, 0 rejected by both; 1 without a ritz0 baseline, compile-checked only)"
check "Stage 5's denominator == Stage 3/4 passed+failed+skipped == corpus" \
      denominator_matches_tally
check "accepted + rejected == denominator"                  stage5_parts_add_up

echo "Both compilers reject the no-baseline example"
echo "$NOBASE" > "$SCRATCH/reject_ritz1"
echo "$NOBASE" > "$SCRATCH/reject_ritz1_selfhosted"
run_suite
check "ritz1's rejection is recorded"                       recorded ritz1 "$NOBASE" rejected
check "a rejection without a baseline is a skip, not a fail" \
      line_is 3 "Stage 3: 2 passed, 0 failed, 1 skipped"
check "Stage 5 passes: they agree"                          rc5_is 0
check "and counts it as rejected by both" \
      line_is 5 "Stage 5: fixed point holds over all 3 examples (2 accepted by both, 1 rejected by both; 1 without a ritz0 baseline, compile-checked only)"
check "denominator still == tallies == corpus"              denominator_matches_tally
check "accepted + rejected == denominator"                  stage5_parts_add_up

echo "Constructed divergence on the no-baseline example (the #1341 hole)"
rm -f "$SCRATCH"/reject_*
export RITZ_REGRESSION_INJECT_SELFHOSTED_REJECT="$NOBASE"
run_suite
unset RITZ_REGRESSION_INJECT_SELFHOSTED_REJECT
check "Stage 4 alone cannot see it (skip, 0 failed)" \
      line_is 4 "Stage 4: 2 passed, 0 failed, 1 skipped"
check "Stage 5 goes RED"                                    rc5_is 1
check "naming the example" \
      grep -qF "$NOBASE: accepted by ritz1, REJECTED by ritz1_selfhosted" "$SCRATCH/out"
check "Stage 5 summary reports the divergence" \
      line_is 5 "Stage 5: FAILED - 1 example(s) diverge between ritz1 and ritz1_selfhosted"

echo "Same divergence, other direction"
echo "$NOBASE" > "$SCRATCH/reject_ritz1"
run_suite
rm -f "$SCRATCH"/reject_*
check "Stage 5 goes RED"                                    rc5_is 1
check "naming the example" \
      grep -qF "$NOBASE: REJECTED by ritz1, accepted by ritz1_selfhosted" "$SCRATCH/out"

echo ""
echo "$TESTS_RUN checks, $TESTS_FAILED failed"
[[ $TESTS_FAILED -eq 0 ]]
