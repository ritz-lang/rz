#!/bin/bash
# Self-test for regression.sh's parallel stages and Stage 1 baseline cache —
# AGAST #1806.
#
# regression.sh used to build and run 88 examples one at a time, three times
# over, through one shared sandbox directory and one server port.  Stages 1, 3
# and 4 now run each example in a bounded pool (REGRESSION_JOBS), each with its
# own sandbox and, for the server examples, its own port.  Stage 1's ritz0
# observations are cached, keyed on everything they depend on.  And the
# examples that never exit get a short budget and an explicit verdict instead
# of burning the full 5 s run timeout.
#
# What this file pins:
#
#   1. Output is in corpus order and identical serial vs parallel, so gate
#      logs stay diffable and the verdicts do not depend on REGRESSION_JOBS.
#   2. The pool really runs in parallel.
#   3. Sandboxes are per example and stable across stages; concurrent
#      examples cannot see each other's files.
#   4. Ports are per example and only server examples (those that read
#      RITZ_EXAMPLE_PORT) see one, so 31_env-style output does not change
#      from run to run.
#   5. The baseline cache: a hit skips the build; changing one example
#      invalidates only it; changing ritz0 invalidates all; failures are never
#      cached; --no-baseline-cache bypasses it.
#   6. Declared non-terminating examples: short budget, "ran until killed, as
#      expected", red if one exits on its own, and no "File size limit
#      exceeded" noise from the output cap.
#   7. Stage 3 through the pool: same verdicts serial vs parallel, and a real
#      mismatch is still red.
#
# Hermetic: sources regression.sh as a library, stubs compile_with with a
# "compiler" that copies a shell script, and uses a scratch project root.
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
BASELINE_CACHE_DIR="$SCRATCH/baseline-cache"
mkdir -p "$ROOT_DIR/ritz0" "$ROOT_DIR/ritzlib" "$ROOT_DIR/runtime" \
         "$ROOT_DIR/ritz1/build" "$BUILD_DIR" "$EXAMPLES_DIR"
echo "# fake ritz0" > "$ROOT_DIR/ritz0/ritz0.py"
echo "fn lib() -> i32" > "$ROOT_DIR/ritzlib/lib.ritz"
# An empty allowlist pair, so no real entry can match a synthetic key.
KNOWN="$SCRATCH/known.txt"; : > "$KNOWN"
known_failures_file() { echo "$KNOWN"; }

COMPILES="$SCRATCH/compiles.log"

# The stub compiler: the "binary" is the example's src/prog.sh.  A
# src/broken.<compiler> file makes that compiler reject it; a
# src/prog.<compiler>.sh overrides the program for that compiler (to fake a
# miscompile).
compile_with() {
    local compiler="$1" dir="$2" out="$3"
    echo "$compiler $(example_key "$dir")" >> "$COMPILES"
    [[ -f "$dir/src/broken.$compiler" ]] && return 1
    local prog="$dir/src/prog.sh"
    [[ -f "$dir/src/prog.$compiler.sh" ]] && prog="$dir/src/prog.$compiler.sh"
    { echo '#!/bin/bash'; cat "$prog"; } > "$out"
    chmod +x "$out"
    mkdir -p "$dir/build/debug"
    cp "$out" "$dir/build/debug/$(resolve_bin_name "$dir")"
}

# Args: $1=key (also the dir name), $2=program body, [$3=test.sh body]
make_example() {
    local dir="$EXAMPLES_DIR/$1"
    mkdir -p "$dir/src"
    printf '[package]\nname = "%s"\n' "$1" > "$dir/ritz.toml"
    echo 'fn main() -> i32' > "$dir/src/main.ritz"
    printf '%s\n' "$2" > "$dir/src/prog.sh"
    [[ -n "${3:-}" ]] && printf '%s\n' "$3" > "$dir/test.sh"
    return 0
}

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
eq() { [[ "$1" == "$2" ]] || { echo "       want: $2"; echo "       got:  $1"; return 1; }; }
has() { grep -qF -- "$2" "$1"; }
hasnt() { ! grep -qF -- "$2" "$1"; }

# Run a stage into $SCRATCH/<tag>.out (a file, not $(...): STAGE_RESULTS and
# the totals must survive).  Strips the timing-dependent cache line.
run_stage() {
    local tag="$1" fn="$2"
    TOTAL_PASSED=0; TOTAL_FAILED=0; TOTAL_SKIPPED=0; STAGE_RESULTS=()
    "$fn" > "$SCRATCH/$tag.raw" 2>&1
    grep -v 'baseline cache:' "$SCRATCH/$tag.raw" > "$SCRATCH/$tag.out"
    printf '%s\n' "${STAGE_RESULTS[@]}" > "$SCRATCH/$tag.summary"
}
compiles_of() { grep -c "^$1 " "$COMPILES" 2>/dev/null || true; }
reset_build() { rm -rf "$BUILD_DIR"; mkdir -p "$BUILD_DIR"; : > "$COMPILES"; }

echo "regression.sh parallel stages + baseline cache self-test (AGAST #1806)"
echo "======================================================================"

# --- corpus -----------------------------------------------------------------
make_example a01_hello   'echo hello; exit 3'
make_example a02_pwd     'pwd'
make_example a03_env     'env | sort'
make_example a04_tested  'echo tested' './a04_tested | grep -q tested'
make_example a05_iso     'echo mine > own.txt; sleep 0.3; ls'
make_example a06_iso     'echo mine > own.txt; sleep 0.3; ls'
make_example a07_server1 '# reads RITZ_EXAMPLE_PORT
echo "port=$RITZ_EXAMPLE_PORT"; exec sleep 30'
make_example a08_server2 '# reads RITZ_EXAMPLE_PORT
echo "port=$RITZ_EXAMPLE_PORT"; exec sleep 30'
make_example a09_yes     'exec yes'
make_example a10_failing 'echo x' 'exit 1'
NONTERMINATING_EXAMPLES=(a07_server1 a08_server2 a09_yes)
REGRESSION_EXAMPLE_PORT=24000
# Shorter than the real 2 s: this file runs a dozen Stage 1s over three
# never-exiting examples.
NONTERM_BUDGET=1s

# ---------------------------------------------------------------------------
echo "1. corpus order, serial == parallel"
USE_BASELINE_CACHE=0
reset_build; REGRESSION_JOBS=1; run_stage s1_serial run_stage1
reset_build; REGRESSION_JOBS=8; run_stage s1_par run_stage1
check "Stage 1 output is identical with 1 and 8 jobs" \
    diff -u "$SCRATCH/s1_serial.out" "$SCRATCH/s1_par.out"
check "Stage 1 summary is identical with 1 and 8 jobs" \
    diff -u "$SCRATCH/s1_serial.summary" "$SCRATCH/s1_par.summary"
order=$(grep -oE 'a[0-9]{2}_[a-z0-9]+' "$SCRATCH/s1_par.out" | awk '!s[$0]++' | tr '\n' ' ')
check "results are printed in corpus order" eq "$order" \
    "a01_hello a02_pwd a03_env a04_tested a05_iso a06_iso a07_server1 a08_server2 a09_yes a10_failing "
check "the failing test.sh is still red" has "$SCRATCH/s1_par.out" "a10_failing: test.sh failed"
check "the summary counts it" has "$SCRATCH/s1_par.summary" "1 failed"

# ---------------------------------------------------------------------------
echo "2. the pool runs in parallel"
SAVED_EX="$EXAMPLES_DIR"
EXAMPLES_DIR="$SCRATCH/slow_examples"
for i in 1 2 3 4 5 6 7 8; do
    d="$EXAMPLES_DIR/s$i"; mkdir -p "$d/src"
    printf '[package]\nname = "s%s"\n' "$i" > "$d/ritz.toml"
    echo 'fn main() -> i32' > "$d/src/main.ritz"
    echo 'sleep 1; echo done' > "$d/src/prog.sh"
done
NONTERMINATING_EXAMPLES=()
reset_build; REGRESSION_JOBS=8
t0=$(date +%s.%N); run_stage slow run_stage1; t1=$(date +%s.%N)
check "8 one-second examples with 8 jobs take under 4 s" \
    awk -v a="$t0" -v b="$t1" 'BEGIN { exit !((b - a) < 4) }'
check "and all 8 pass" has "$SCRATCH/slow.summary" "8 passed, 0 failed"
EXAMPLES_DIR="$SAVED_EX"
NONTERMINATING_EXAMPLES=(a07_server1 a08_server2 a09_yes)

# ---------------------------------------------------------------------------
echo "3. per-example sandboxes"
reset_build; REGRESSION_JOBS=8; run_stage s1 run_stage1
pwd_out=$(cat "$BUILD_DIR/stage1_a02_pwd.stdout")
check "an example runs in its own sandbox under BUILD_DIR" \
    eq "$pwd_out" "$BUILD_DIR/sandbox/a02_pwd"
# The fixture tree plus the one file this example wrote.
FIXTURE_LS=$'alpha\nbeta\nown.txt\nreadme.txt'
check "concurrent examples see only their own files (a05)" \
    eq "$(cat "$BUILD_DIR/stage1_a05_iso.stdout")" "$FIXTURE_LS"
check "concurrent examples see only their own files (a06)" \
    eq "$(cat "$BUILD_DIR/stage1_a06_iso.stdout")" "$FIXTURE_LS"
check "sandboxes are removed after the run" \
    bash -c '[[ -z "$(ls -A "$1" 2>/dev/null)" ]]' _ "$BUILD_DIR/sandbox"

# ---------------------------------------------------------------------------
echo "4. per-example ports, server examples only"
grep -h 'port=' "$BUILD_DIR"/stage1_a07_server1.stdout "$BUILD_DIR"/stage1_a08_server2.stdout \
    > "$SCRATCH/ports" 2>/dev/null
# Non-terminating output is not published as a baseline byte-for-byte, but
# the server still saw its port; read it from the observation.
p1=$(sed -n 's/^port=//p' "$BUILD_DIR/stage1_obs/a07_server1/stdout")
p2=$(sed -n 's/^port=//p' "$BUILD_DIR/stage1_obs/a08_server2/stdout")
check "server 1 got a port" bash -c '[[ "$1" =~ ^[0-9]+$ ]]' _ "$p1"
check "server 2 got a different port" bash -c '[[ "$1" =~ ^[0-9]+$ && "$1" != "$2" ]]' _ "$p2" "$p1"
check "ports come from the run's block" \
    bash -c '(( $1 >= 24000 && $1 < 24000 + 256 ))' _ "$p1"
check "a non-server example does not see RITZ_EXAMPLE_PORT" \
    hasnt "$BUILD_DIR/stage1_a03_env.stdout" "RITZ_EXAMPLE_PORT"

# ---------------------------------------------------------------------------
echo "5. the Stage 1 baseline cache"
rm -rf "$BASELINE_CACHE_DIR"; USE_BASELINE_CACHE=1; REGRESSION_JOBS=8
reset_build; run_stage c1 run_stage1
check "a cold run builds every example" eq "$(compiles_of ritz0)" 10
reset_build; run_stage c2 run_stage1
check "a warm run rebuilds only the failing example (failures are not cached)" \
    eq "$(grep '^ritz0 ' "$COMPILES" | sort | tr '\n' ' ')" "ritz0 a10_failing "
check "a warm run prints the same verdicts as a cold one" \
    diff -u "$SCRATCH/c1.out" "$SCRATCH/c2.out"
check "and the same summary" diff -u "$SCRATCH/c1.summary" "$SCRATCH/c2.summary"
check "a hit still publishes the baseline Stage 3 compares against" \
    eq "$(cat "$BUILD_DIR/stage1_a01_hello.stdout"):$(cat "$BUILD_DIR/stage1_a01_hello.exit")" "hello:3"
check "a hit still records the test.sh as run" \
    grep -qx a04_tested "$BUILD_DIR/test_scripts_ran.txt"
check "the run reports its hit count" has "$SCRATCH/c2.raw" "baseline cache: 9 hit"

echo 'echo hello again; exit 3' > "$EXAMPLES_DIR/a01_hello/src/prog.sh"
reset_build; run_stage c3 run_stage1
check "changing one example invalidates only that example" \
    eq "$(grep '^ritz0 ' "$COMPILES" | sort | tr '\n' ' ')" "ritz0 a01_hello ritz0 a10_failing "
check "and its new output is what gets published" \
    eq "$(cat "$BUILD_DIR/stage1_a01_hello.stdout")" "hello again"

echo "x = 1" > "$ROOT_DIR/ritzlib/new.ritz"
reset_build; run_stage c4 run_stage1
check "changing ritzlib invalidates every example" eq "$(compiles_of ritz0)" 10

echo "# changed fake ritz0" > "$ROOT_DIR/ritz0/ritz0.py"
reset_build; run_stage c5 run_stage1
check "changing ritz0 invalidates every example" eq "$(compiles_of ritz0)" 10

reset_build; RITZ_VERIFY_IR=1 run_stage c5v run_stage1
check "turning on RITZ_VERIFY_IR (build.py's IR verifier) invalidates every example" \
    eq "$(compiles_of ritz0)" 10

reset_build; USE_BASELINE_CACHE=0; run_stage c6 run_stage1
check "--no-baseline-cache rebuilds every example" eq "$(compiles_of ritz0)" 10
USE_BASELINE_CACHE=1

check "regression.sh accepts --no-baseline-cache" \
    bash -c 'RITZ_REGRESSION_LIB_ONLY=1 RITZ_EXAMPLE_PORT=24000 bash -c "source \"$1\" --no-baseline-cache; trap - EXIT; [[ \$USE_BASELINE_CACHE == 0 ]]"' _ "$REGRESSION_SH"
check "regression.sh accepts --jobs N" \
    bash -c 'RITZ_REGRESSION_LIB_ONLY=1 RITZ_EXAMPLE_PORT=24000 bash -c "source \"$1\" --jobs 3; trap - EXIT; [[ \$REGRESSION_JOBS == 3 ]]"' _ "$REGRESSION_SH"

# ---------------------------------------------------------------------------
echo "6. declared non-terminating examples"
check "a never-exiting server is reported as killed, as expected" \
    has "$SCRATCH/s1.out" "a07_server1 (ran until killed, as expected)"
check "so is an infinite generator" \
    has "$SCRATCH/s1.out" "a09_yes (ran until killed, as expected)"
check "no 'File size limit exceeded' noise" hasnt "$SCRATCH/s1.raw" "File size limit exceeded"
SAVED_EX="$EXAMPLES_DIR"
EXAMPLES_DIR="$SCRATCH/nt_examples"
make_example n1_server 'exec sleep 30'
make_example n2_exits  'echo bye'
NONTERMINATING_EXAMPLES=(n1_server n2_exits n9_gone)
reset_build; USE_BASELINE_CACHE=0
t0=$(date +%s); run_stage nt run_stage1; t1=$(date +%s)
check "a declared server costs the short budget, not 5 s" \
    test $((t1 - t0)) -lt 5
check "a declared example that exits on its own is red" \
    has "$SCRATCH/nt.out" "n2_exits: declared non-terminating but exited on its own"
check "a declared example missing from the corpus is red" \
    has "$SCRATCH/nt.out" "n9_gone: declared non-terminating but not in the corpus"
EXAMPLES_DIR="$SAVED_EX"
NONTERMINATING_EXAMPLES=(a07_server1 a08_server2 a09_yes)

# ---------------------------------------------------------------------------
echo "7. Stage 3 through the pool"
printf '#!/bin/sh\n' > "$ROOT_DIR/ritz1/build/ritz1"; chmod +x "$ROOT_DIR/ritz1/build/ritz1"
echo 'echo HELLO; exit 3' > "$EXAMPLES_DIR/a01_hello/src/prog.ritz1.sh"
touch "$EXAMPLES_DIR/a03_env/src/broken.ritz1"
for j in 1 8; do
    reset_build; REGRESSION_JOBS=$j; run_stage s1_$j run_stage1; run_stage s3_$j run_stage3
done
check "Stage 3 output is identical with 1 and 8 jobs" \
    diff -u "$SCRATCH/s3_1.out" "$SCRATCH/s3_8.out"
check "Stage 3 summary is identical with 1 and 8 jobs" \
    diff -u "$SCRATCH/s3_1.summary" "$SCRATCH/s3_8.summary"
check "a miscompile is still an output mismatch" \
    has "$SCRATCH/s3_8.out" "a01_hello: output mismatch"
check "a ritz1 compile failure is still red" \
    has "$SCRATCH/s3_8.out" "a03_env: ritz1 compile failed"
check "the accept set is recorded for Stage 5" \
    bash -c 'grep -qx a02_pwd "$1" && ! grep -qx a03_env "$1"' _ "$BUILD_DIR/acceptset_ritz1.accepted"
check "servers compare as non-terminating" \
    has "$SCRATCH/s3_8.out" "a07_server1 (non-terminating; output not byte-compared)"

# ---------------------------------------------------------------------------
echo "8. a worker that dies without a verdict is a failure, not a gap"
_dying_worker() { echo "started $2"; [[ "$1" == 1 ]] && exit 0; _verdict "$3" pass; }
passed=0; failed=0; skipped=0
run_pool "$SCRATCH/pool" _dying_worker /ex/one /ex/two /ex/three
collect_pool "$SCRATCH/pool" > "$SCRATCH/pool.out" 2>&1
check "the other two still pass" eq "$passed" 2
check "the dead one counts as failed" eq "$failed" 1
check "and is named by its example dir" has "$SCRATCH/pool.out" "(/ex/two) recorded no verdict"

echo ""
echo "$TESTS_RUN checks, $TESTS_FAILED failed"
[[ $TESTS_FAILED -eq 0 ]]
