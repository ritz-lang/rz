#!/bin/bash
# Self-test for regression.sh Stage 4's bootstrap step, and per-stage timing
# (AGAST #1802).
#
# Stage 4 used to run `make -s bootstrap BUILD_DIR="$BUILD_DIR" 2>/dev/null`.
# A command-line BUILD_DIR overrides ritz1/Makefile's for every object and .d
# file (only build/ritz1 and build/ritz1_selfhosted are hard-coded), so the
# stage recompiled all of ritz1 with ritz0 into an empty .regression/, RELINKED
# build/ritz1 mid-run, self-compiled everything again and relinked
# ritz1_selfhosted -- work matrix-full had already done.  55 s on CI, 3-4 min
# locally, and the build's stderr went to /dev/null, so a failure was a bare
# "bootstrap failed".
#
# What must hold:
#   * no make invocation from Stage 4 passes BUILD_DIR=
#   * when `make -q` says ritz1_selfhosted is current, Stage 4 builds nothing
#   * when it is stale, Stage 4 builds with the RITZ1_JOBS -j cap, and the
#     build's stderr reaches the log
#   * a failed build fails the stage (return 2)
#   * every stage the suite runs is timed, and the summary prints the times
#
# A stub `make` on PATH records its arguments; nothing is compiled.  Runs in
# well under a second.
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

# A fake tree: Stage 4 must only ever touch ROOT_DIR/ritz1/build, and with no
# examples the corpus loop is empty.
ROOT_DIR="$SCRATCH/root"
BUILD_DIR="$SCRATCH/regression"
EXAMPLES_DIR="$ROOT_DIR/examples"
mkdir -p "$ROOT_DIR/ritz1/build" "$BUILD_DIR" "$EXAMPLES_DIR" "$SCRATCH/bin"

# Stub make.  STUB_Q_RC is what `make -q` answers (0 = current); STUB_BUILD_RC
# is what a real build returns.  A successful build "links" ritz1_selfhosted.
cat > "$SCRATCH/bin/make" <<'EOF'
#!/bin/bash
printf '%s\n' "$*" >> "$STUB_MAKE_LOG"
for a in "$@"; do
    if [[ "$a" == "-q" ]]; then exit "${STUB_Q_RC:-1}"; fi
done
echo "STUB-BUILD-STDERR" >&2
rc="${STUB_BUILD_RC:-0}"
if [[ "$rc" -eq 0 ]]; then
    printf '#!/bin/sh\n' > "$STUB_ROOT/ritz1/build/ritz1_selfhosted"
    chmod +x "$STUB_ROOT/ritz1/build/ritz1_selfhosted"
fi
exit "$rc"
EOF
chmod +x "$SCRATCH/bin/make"
export PATH="$SCRATCH/bin:$PATH"
export STUB_MAKE_LOG="$SCRATCH/make.log"
export STUB_ROOT="$ROOT_DIR"

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

# Run Stage 4 against the stub.  Output to a file, not `$(...)`: a subshell
# would discard STAGE_RESULTS/TOTAL_FAILED.
run4() {
    : > "$STUB_MAKE_LOG"
    rm -f "$ROOT_DIR/ritz1/build/ritz1_selfhosted"
    [[ "${1:-}" == "present" ]] && { printf '#!/bin/sh\n' > "$ROOT_DIR/ritz1/build/ritz1_selfhosted"; chmod +x "$ROOT_DIR/ritz1/build/ritz1_selfhosted"; }
    TOTAL_PASSED=0; TOTAL_FAILED=0; TOTAL_SKIPPED=0; STAGE_RESULTS=()
    run_stage4 > "$SCRATCH/out" 2>&1
    RC=$?
}

no_build_dir_override() { ! grep -q 'BUILD_DIR=' "$STUB_MAKE_LOG"; }
make_calls()            { wc -l < "$STUB_MAKE_LOG"; }
only_q_call()           { [[ $(make_calls) -eq 1 ]] && grep -q -- '-q' "$STUB_MAKE_LOG"; }
built_bootstrap_with()  { grep -E -- "(^| )-j$1( |$)" "$STUB_MAKE_LOG" | grep -q 'bootstrap'; }
stderr_kept()           { grep -q 'STUB-BUILD-STDERR' "$SCRATCH/out"; }
rc_is()                 { [[ "$RC" -eq "$1" ]]; }

echo "Stage 4: ritz1_selfhosted already current"
STUB_Q_RC=0 STUB_BUILD_RC=0 run4 present
check "no BUILD_DIR= override"                no_build_dir_override
check "only the make -q probe ran (no build)" only_q_call
check "stage returns 0"                       rc_is 0

echo "Stage 4: ritz1_selfhosted stale"
STUB_Q_RC=1 STUB_BUILD_RC=0 RITZ1_JOBS=3 run4
check "no BUILD_DIR= override"           no_build_dir_override
check "bootstrap built with -j3 (cap)"   built_bootstrap_with 3
check "build stderr reaches the log"     stderr_kept
check "stage returns 0"                  rc_is 0

echo "Stage 4: bootstrap fails"
STUB_Q_RC=1 STUB_BUILD_RC=2 run4
check "stage returns 2"                  rc_is 2
check "build stderr reaches the log"     stderr_kept
check "failure recorded"                 test "$TOTAL_FAILED" -ge 1

echo "Per-stage timing"
STAGE_TIMES=()
_fake_stage() { sleep 1; return 7; }
run_timed "Stage 9" _fake_stage > /dev/null
TIMED_RC=$?
check "run_timed passes the stage's rc through" test "$TIMED_RC" -eq 7
check "run_timed records whole seconds" \
    bash -c '[[ "$1" =~ ^Stage\ 9:\ [0-9]+s$ ]]' _ "${STAGE_TIMES[0]:-}"
print_stage_times > "$SCRATCH/times"
check "summary prints the recorded times" grep -q 'Stage 9: [0-9]*s' "$SCRATCH/times"
# Every stage dispatch goes through run_timed: a bare `run_stageN` call is an
# untimed stage.
untimed_dispatch() {
    ! sed -n '/^# Run selected stages/,/^# Summary/p' "$REGRESSION_SH" \
        | grep -v '^\s*#' | grep -E '(^|[;)]|then|else)\s*run_stage[0-9]'
}
check "no stage is dispatched without run_timed" untimed_dispatch
summary_prints_times() {
    sed -n '/^# Summary/,$p' "$REGRESSION_SH" | grep -q 'print_stage_times'
}
check "the Summary calls print_stage_times" summary_prints_times

echo ""
echo "$TESTS_RUN checks, $TESTS_FAILED failed"
[[ $TESTS_FAILED -eq 0 ]]
