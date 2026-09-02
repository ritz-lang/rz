#!/bin/bash
# 🎭 Ritz Regression Test Suite
#
# Comprehensive regression testing across compiler stages:
#   Stage 1: ritz0 compiles examples, run them
#   Stage 2: ritz0 compiles ritz1
#   Stage 3: ritz1 compiles examples, compare output with Stage 1
#   Stage 4: ritz1 self-compiles (bootstrap), compile examples, compare
#   Stage 5: assert stage 3 and stage 4 accepted the *same* set of examples
#
# Note: "Stages" refer to compiler development progression.
#       Examples have their own "Tiers" based on language features used.
#
# Usage:
#   ./scripts/regression.sh             # Run all stages
#   ./scripts/regression.sh --stage 1   # Run specific stage
#   ./scripts/regression.sh --quick     # Skip Stages 4 and 5 (slower)
#   ./scripts/regression.sh --verbose   # Show detailed output
#
# Exit codes:
#   0 - All tests passed
#   1 - Some tests failed
#   2 - Critical failure (compiler couldn't build)

# Don't use set -e - we handle errors explicitly

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Paths
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
RITZ0="python3 $ROOT_DIR/ritz0/ritz0.py"
BUILD_DIR="$ROOT_DIR/.regression"
EXAMPLES_DIR="$ROOT_DIR/examples"

# Set RITZ_PATH for import resolution (ritz1 needs this to find ritzlib)
export RITZ_PATH="$ROOT_DIR"

# Counters
TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_SKIPPED=0
STAGE_RESULTS=()

# Options
RUN_STAGE=""
QUICK_MODE=0
VERBOSE=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --stage)
            RUN_STAGE="$2"
            shift 2
            ;;
        --quick)
            QUICK_MODE=1
            shift
            ;;
        --verbose|-v)
            VERBOSE=1
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --stage N    Run only stage N (1-5)"
            echo "  --quick      Skip Stage 4 (self-hosted bootstrap) and Stage 5"
            echo "  --verbose    Show detailed output"
            echo "  --help       Show this message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Setup
mkdir -p "$BUILD_DIR"

# Keep the captured stdout/exit files when anything failed.  This used to be an
# unconditional `rm -rf` on EXIT, which meant a failing run in CI destroyed the
# only evidence of *why* it failed -- you got "output mismatch" and nothing to
# diff.  On success there is nothing worth keeping, so clean up as before.
cleanup_build_dir() {
    if [[ ${KEEP_ARTIFACTS:-0} -eq 1 ]]; then
        echo ""
        echo "Captured stdout/exit files kept for inspection:"
        echo "  $BUILD_DIR"
        return
    fi
    rm -rf "$BUILD_DIR"
}
trap cleanup_build_dir EXIT

log() {
    echo -e "${BLUE}==>${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

fail() {
    echo -e "${RED}✗${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Examples that require special handling (stdin input, file arguments, etc.)
# These will use their test.sh if available, otherwise skip
INTERACTIVE_EXAMPLES="05_cat 06_grep 07_wc 08_echo 09_head 10_tail"

# Check if example needs special handling
is_interactive_example() {
    local name="$1"
    for ex in $INTERACTIVE_EXAMPLES; do
        if [[ "$name" == "$ex" ]]; then
            return 0
        fi
    done
    return 1
}

# Get list of example directories with main.ritz
#
# Examples are NOT all at examples/<name>/ — the tier5_async corpus lives one
# level deeper at examples/tier5_async/<name>/.  A `-maxdepth 1` walk (what
# this used to do) saw 17 of 85 example dirs, and the 11 of those with a
# src/main.ritz happened to be exactly the known-broken set.  Every stage
# then skipped everything and the suite exited 0 having asserted nothing.
# Walk the whole tree and let the src/main.ritz probe decide.
get_examples() {
    find "$EXAMPLES_DIR" -mindepth 1 -type f -path '*/src/main.ritz' \
        -not -path '*/build/*' -printf '%h\n' | sed 's|/src$||' | sort -u
}

# Examples ritz0 is known not to compile yet, one key per line (`#` comments
# allowed).  These are reported and excluded rather than failing the suite —
# but anything NOT on the list that fails to compile is a hard failure.
#
# Previously every ritz0 compile failure was a silent `skip`, so the suite
# could not go red no matter how much broke.  The allowlist is the difference
# between "we know about these" and "we assert nothing".
# One file per compiler: ritz0 and ritz1 have genuinely different gaps, and a
# shared list would let a ritz1 regression hide behind a ritz0 entry.
#
# ritz1_selfhosted deliberately shares ritz1's list, and that sharing is SAFE
# only because of Stage 5.  The reasoning matters, so read it before changing
# either the file layout or the resolution below.
#
# The header of the allowlist files states the design rule: compile failures
# may be allowlisted, behavioural mismatches never.  That rule was written for
# ritz0-vs-ritzN *behaviour*.  It said nothing about ritz1-vs-ritz1_selfhosted
# *compile* divergence — and because both stages resolved to the same file,
# each stage independently skipped a listed entry.  "ritz1 accepts it,
# ritz1_selfhosted rejects it" was therefore indistinguishable from "both are
# known-broken": the divergence never reached a comparison and the suite exited
# 0.  Real instance (CI 33679700130, commit eef15af): stage 3 reported 50
# passed / 35 skipped, stage 4 reported 49 passed / 36 skipped, and the single
# example in the difference — tier5_async_49_ritzgen — compiled under ritz1 and
# failed under the compiler ritz1 had built from its own source.  The
# self-hosting fixed point was not reached and the gate said 🎉.
#
# An allowlist may say "this program is known not to compile."  It must never
# be able to say "these two compilers may disagree."  Stage 5 enforces exactly
# that distinction: it compares the accepted sets of stages 3 and 4 directly,
# consulting NO allowlist, so no entry in any list can silence a divergence.
#
# Consequently, do not "fix" a red Stage 5 by editing an allowlist — adding the
# example to the list, or removing it, cannot change the Stage 5 verdict by
# construction.  A red Stage 5 is a self-hosting bug in the compiler.
known_failures_file() {
    case "$1" in
        ritz1|ritz1_selfhosted) echo "$SCRIPT_DIR/regression-known-failures-ritz1.txt" ;;
        *)                      echo "$SCRIPT_DIR/regression-known-failures.txt" ;;
    esac
}

# Args: $1=compiler, $2=example key
is_known_failure() {
    local f=$(known_failures_file "$1")
    [[ -f "$f" ]] || return 1
    grep -qxF "$2" <(sed 's/#.*//; s/[[:space:]]*$//; /^$/d' "$f")
}

# --- Differential accept-set recording (feeds Stage 5) ----------------------
#
# Deliberately independent of the allowlist machinery above.  These record the
# raw, observed outcome of `compile_with` — did this compiler accept this
# program, yes or no — *before* any allowlist is consulted, so an allowlisted
# entry is recorded as rejected exactly like an unlisted one.  That is the
# whole point: Stage 5 must see the truth, not the filtered view each stage
# reports to the user.
#
# Args: $1=compiler, $2=example key, $3="accepted"|"rejected"
record_compile_outcome() {
    echo "$2" >> "$BUILD_DIR/acceptset_$1.$3"
}

# Declare that a stage ran to completion over the example corpus, so Stage 5
# can tell "this compiler accepted nothing" from "this stage never ran".
# Without this an aborted or skipped stage would present an empty accept set,
# and comparing two empty sets trivially succeeds — a green built out of two
# things that never happened, which is the exact failure mode this suite keeps
# being bitten by.
#
# Call this *after* the corpus loop, never before: a stage that dies partway
# through must not be able to claim it ran.  The empty-file creation matters
# for the legitimate zero-accept case, where no append ever happened.
mark_stage_ran() {
    : >> "$BUILD_DIR/acceptset_$1.accepted"
    : >> "$BUILD_DIR/acceptset_$1.rejected"
    echo "1" > "$BUILD_DIR/acceptset_$1.ran"
}

# Stable, collision-free key for an example dir.  basename() is not unique
# across tiers (and silently overwrote baselines when it collided), so key on
# the path relative to examples/ with separators flattened.
example_key() {
    local rel="${1#$EXAMPLES_DIR/}"
    echo "${rel//\//_}"
}

# Compile an example with a given compiler.
#
# Args: $1=compiler ("ritz0" | "ritz1" | "ritz1_selfhosted"), $2=source,
#       $3=output_binary
#
# All three compilers go through build.py.  The old ritz1 path hand-rolled
#     $compiler main.ritz -o out.ll && clang out.ll -o bin -nostdlib
# which links neither the runtime `_start` shim nor any ritzlib object, so it
# could only ever have worked for a single-file program with no imports.  In
# practice every multi-module example failed to link and the handful that did
# link segfaulted immediately for want of an entry point (exit 139).  That is
# a property of the harness, not of ritz1 — measuring it told us nothing.
compile_with() {
    local compiler="$1"
    local source="$2"
    local output="$3"
    local example_dir=$(dirname $(dirname "$source"))
    local example_name=$(basename "$example_dir")

    {
        # Clear the output dir first.  All three stages build into the same
        # <pkg>/build/debug, so a stage-3 build failure would otherwise leave
        # stage 1's ritz0-built binary sitting there for us to pick up and
        # "verify" — a stale artifact masquerading as a ritz1 pass.  That is
        # the same class of bug that made `make matrix-full` report a phantom
        # failure on main and a phantom 0/50 on the 1269 branch.
        rm -rf "$example_dir/build/debug"

        # Build by *path*, not by basename.  Example dir names are not package
        # names (and are not unique across tiers), so resolving by name picked
        # the wrong package — or none — for the tier5_async corpus.
        if ! python3 "$ROOT_DIR/build.py" build "$example_dir" \
                --compiler "$compiler" >/dev/null 2>&1; then
            return 1
        fi
        # build.py emits to <pkg>/build/debug/<bin>.  Locate that, and *only*
        # that: the old fallback globbed any executable sitting in the example
        # dir, which meant a stale committed binary could stand in for a build
        # that never happened.
        #
        # The binary name comes from [[bin]] name, else [package] name.  Most
        # examples have no [[bin]] section at all, so the [package] fallback is
        # the common case, not the exception.
        local bin_name=$(awk '/^\[\[bin\]\]/{found=1} found && /^name[[:space:]]*=/{gsub(/.*=[[:space:]]*"|".*/, ""); print; exit}' "$example_dir/ritz.toml" 2>/dev/null)
        if [[ -z "$bin_name" ]]; then
            bin_name=$(awk '/^\[package\]/{found=1} found && /^name[[:space:]]*=/{gsub(/.*=[[:space:]]*"|".*/, ""); print; exit}' "$example_dir/ritz.toml" 2>/dev/null)
        fi
        local built_bin=""
        for cand_name in "$bin_name" "$example_name"; do
            # Skip an empty name: "$dir/build/debug/" is the *directory*, and
            # `-x` is true for directories, so an empty bin_name used to select
            # the build dir itself.  `cp` then failed with "omitting directory"
            # and the caller sailed on to `return 0` -- a build reported as
            # successful with no binary produced.  Downstream, `timeout` on the
            # missing path yielded exit 127, which every stage happily recorded
            # as a legitimate baseline.  41 of 68 stage-1 "passes" were that.
            [[ -n "$cand_name" ]] || continue
            local cand="$example_dir/build/debug/$cand_name"
            if [[ -f "$cand" && -x "$cand" ]]; then
                built_bin="$cand"
                break
            fi
        done
        if [[ -z "$built_bin" ]]; then
            built_bin=$(find "$example_dir/build/debug" -maxdepth 1 -type f -executable 2>/dev/null | head -1)
        fi
        if [[ -z "$built_bin" ]]; then
            return 1
        fi
        # Propagate cp's status.  This used to be the last command in the
        # block, followed by an unconditional `return 0`, so a failed copy was
        # indistinguishable from a successful build.
        cp "$built_bin" "$output" || return 1
        [[ -f "$output" && -x "$output" ]] || return 1
    }

    return 0
}

# Run a binary and capture output/exit code
# Args: $1=binary, $2=output_file (for stdout), $3=exit_file
# Build a small, deterministic directory tree for a binary to run inside.
#
# Every stage gets a byte-identical tree, so filesystem-inspecting programs
# (du, find, ls, wc -c) produce stable output that is genuinely a function of
# the compiled program.  Kept deliberately small and flat-ish: entries are
# created in a fixed order with fixed sizes and fixed content, and the
# directory name is fixed, so nothing about the host leaks into the output.
#
# Sizes are exact multiples chosen so `du`'s block rounding is stable across
# filesystems.  Do not add entries with host-dependent content (timestamps,
# hostnames, $USER) -- that would silently reintroduce the nondeterminism this
# exists to eliminate.
_build_fixture_tree() {
    local root="$1"
    rm -rf "$root"
    mkdir -p "$root/alpha/nested" "$root/beta"

    # Fixed-size files: 1024, 2048 and 512 bytes of a constant byte.
    head -c 1024 /dev/zero | tr '\0' 'a' > "$root/alpha/one.txt"
    head -c 2048 /dev/zero | tr '\0' 'b' > "$root/alpha/nested/two.txt"
    head -c 512  /dev/zero | tr '\0' 'c' > "$root/beta/three.txt"
    printf 'line one\nline two\nline three\n' > "$root/readme.txt"

    # Fixed mtimes so anything printing timestamps stays stable.
    find "$root" -exec touch -t 202001010000.00 {} + 2>/dev/null || true
}

run_binary() {
    local binary="$1"
    local stdout_file="$2"
    local exit_file="$3"

    # A missing binary must never become a baseline.  `timeout` reports 127
    # ("command not found") for a path that does not exist, which is
    # indistinguishable from a program that genuinely exited 127 -- so an
    # absent binary used to be recorded as "exit=127, no output", and the next
    # stage's equally-absent binary matched it perfectly.  Two things that
    # never ran comparing equal is not a passing test.
    if [[ ! -f "$binary" || ! -x "$binary" ]]; then
        return 1
    fi

    # Clear any marker left by a previous run before recording this one.  A
    # stale `.nonterminating` file would silently downgrade this run's strict
    # byte comparison to the weaker "still non-terminating" property check --
    # a state-dependent weakening of the assertion, which is the same
    # stale-artifact class this suite exists to catch.
    rm -f "${exit_file}.nonterminating"

    # Run inside a freshly built, byte-identical fixture tree.
    #
    # Programs that inspect their working directory -- 29_du, 30_find, 21_ls --
    # produce output that is a function of the filesystem, not of the compiled
    # program.  Stages run minutes apart with builds in between (stage 2 builds
    # ritz1), so CWD differs every time and byte-comparing their output across
    # stages compares the build tree, not the compiler.  That is how 29_du and
    # 30_find reported "output mismatch" for a compiler that was behaving
    # perfectly: `.ritz-cache/objects` had grown from 11128 to 11480 KB between
    # stage 1 and stage 3.
    #
    # Allowlisting them would silence a whole category of program -- anything
    # that reads the filesystem -- and those are exactly the programs where a
    # miscompile matters most.  So instead we make the environment identical
    # and keep the strict comparison: same fixture, same expected output, and a
    # real difference is now genuinely attributable to the compiler.
    # A *fixed* path, not mktemp: a random directory name would leak into the
    # output of any program that prints its own cwd, reintroducing the very
    # nondeterminism this is meant to remove.
    local sandbox="$BUILD_DIR/sandbox"
    _build_fixture_tree "$sandbox"

    # Close stdin (</dev/null) to prevent programs like cat/grep from hanging.
    # Use timeout with KILL signal to ensure cleanup.
    #
    # Write straight to a file.  Do NOT reintroduce a pipe here.  The original
    # form was:
    #
    #     ( timeout --signal=KILL 5s "$binary" ) | head -c 1048576 > "$stdout_file"
    #
    # `timeout` signals only its *direct* child.  A program that forks and then
    # exits -- a server that daemonises, anything that spawns a helper -- leaves
    # a grandchild holding the pipe's write end open.  `head` then blocks on an
    # EOF that never arrives, and because the 5s timeout has already fired there
    # is no outer bound left: the suite hangs forever.  That is a deadlock, not
    # a slow test.  It stalled the CI job past 110 minutes against a 6m25s
    # baseline, and it only shows up where a forking example actually forks --
    # which is why it never reproduced locally.
    #
    # No pipe means nothing can hold an EOF hostage.  The runaway-output cap
    # that `head -c` used to provide is now an RLIMIT_FSIZE (`ulimit -f`),
    # enforced by the kernel on the process itself.  bash counts `ulimit -f` in
    # 1024-byte blocks (not the 512 that POSIX names for some other tools), so
    # 1024 here is 1 MiB -- the same cap `head -c 1048576` applied, kept in
    # agreement with the truncation check below.
    local raw="${stdout_file}.raw"
    rm -f "$raw"
    ( cd "$sandbox" && ulimit -f 1024 && \
      exec timeout --signal=KILL 5s "$binary" < /dev/null > "$raw" 2>&1 )
    local exit_code=$?

    # Reap anything the program forked and left behind.  Orphans are harmless
    # to *this* measurement now that the pipe is gone, but a surviving server
    # still holds its listening port and would break a later stage's run of the
    # same example.  Binary paths are stage-prefixed and unique, so matching on
    # the full path cannot hit an unrelated process.
    pkill -KILL -f "^${binary}$" 2>/dev/null || true

    head -c 1048576 "$raw" > "$stdout_file" 2>/dev/null || : > "$stdout_file"
    rm -f "$raw"
    rm -rf "$sandbox"
    echo "$exit_code" > "$exit_file"

    # Mark runs whose observed behaviour is a function of wall-clock time
    # rather than of the program.  Servers and infinite generators (50_http,
    # 76_tier3_http, 09_yes) never terminate: what we capture is however much
    # they managed to emit before the 5s KILL or the 1MB cap cut them off, and
    # whether the kill or the SIGPIPE won the race.  On a loaded runner those
    # differ run to run.
    #
    # Byte-comparing that against another stage is a coin flip, and behavioural
    # mismatches are deliberately NOT allowlistable -- so left alone these would
    # flake the suite red for reasons having nothing to do with the compiler.
    # Record the fact instead: for these, the assertion downgrades from "same
    # output" to "still non-terminating", which is the strongest claim the data
    # actually supports.  See compare_runs.
    #
    # 153 is 128+25 (SIGXFSZ): the kernel killed the program for exceeding the
    # `ulimit -f` output cap.  That is the rlimit's way of saying what `head -c`
    # used to say by closing the pipe -- a runaway generator -- so it belongs in
    # the same bucket as 124/137 rather than being reported as a crash.
    local truncated=0
    [[ $(wc -c < "$stdout_file") -ge 1048576 ]] && truncated=1
    if [[ "$exit_code" == "124" || "$exit_code" == "137" || "$exit_code" == "153" || $truncated -eq 1 ]]; then
        echo "1" > "${exit_file}.nonterminating"
    fi
    return 0
}

# Run example's test.sh if it exists
# Args: $1=example_dir, $2=binary_path
run_test_script() {
    local example_dir="$1"
    local binary="$2"
    local test_script="$example_dir/test.sh"

    if [[ ! -x "$test_script" ]]; then
        return 2  # No test script
    fi

    # Run test.sh from the example's directory with the binary
    local orig_dir=$(pwd)
    cd "$example_dir"

    # Get the actual binary name from ritz.toml (bin.name field)
    # test.sh scripts reference ./cat, ./ls, etc., not ./05_cat, ./21_ls
    local bin_name
    if [[ -f "ritz.toml" ]]; then
        bin_name=$(grep -A1 '^\[\[bin\]\]' ritz.toml 2>/dev/null | grep '^name' | head -1 | sed 's/.*=[ ]*"\([^"]*\)".*/\1/')
    fi
    # Fallback to directory-based name if not found
    if [[ -z "$bin_name" ]]; then
        bin_name=$(basename "$example_dir")
    fi

    # Create a temp symlink so test.sh can find the binary at expected location
    ln -sf "$binary" "./$bin_name" 2>/dev/null || cp "$binary" "./$bin_name"

    timeout --signal=KILL 30s bash "$test_script" >/dev/null 2>&1
    local result=$?

    rm -f "./$bin_name"
    cd "$orig_dir"
    return $result
}

# Compare two runs
# Args: $1=name, $2=stdout_a, $3=exit_a, $4=stdout_b, $5=exit_b
compare_runs() {
    local name="$1"
    local stdout_a="$2"
    local exit_a="$3"
    local stdout_b="$4"
    local exit_b="$5"

    local code_a=$(cat "$exit_a")
    local code_b=$(cat "$exit_b")

    # Non-terminating programs (see run_binary): compare the *property*, not
    # the bytes.  Both sides must agree the program still runs forever; if one
    # side suddenly terminates on its own, that IS a behavioural change and
    # goes red.  What we refuse to assert is how far a killed process got.
    local nt_a=0 nt_b=0
    [[ -f "${exit_a}.nonterminating" ]] && nt_a=1
    [[ -f "${exit_b}.nonterminating" ]] && nt_b=1
    if [[ $nt_a -eq 1 || $nt_b -eq 1 ]]; then
        if [[ $nt_a -ne $nt_b ]]; then
            fail "$name: termination behaviour changed (A non-terminating=$nt_a, B=$nt_b)"
            return 1
        fi
        success "$name (non-terminating; output not byte-compared)"
        return 0
    fi

    if [[ "$code_a" != "$code_b" ]]; then
        fail "$name: exit code mismatch (A=$code_a, B=$code_b)"
        return 1
    fi

    if ! diff -q "$stdout_a" "$stdout_b" >/dev/null 2>&1; then
        fail "$name: output mismatch"
        # Always show the diff, not just under -v.  A behavioural mismatch is
        # the most serious thing this suite can report -- it means one compiler
        # miscompiled the program -- and "output mismatch" with no detail is
        # not actionable, least of all in a CI log you cannot re-run locally.
        # Bounded so a runaway diff cannot bury the summary.
        echo "  --- diff (A=baseline, B=this stage), first 15 lines ---"
        diff "$stdout_a" "$stdout_b" 2>&1 | head -15 | sed 's/^/  /'
        return 1
    fi

    success "$name (exit=$code_a)"
    return 0
}

# ============================================================================
# STAGE 1: Compile all examples with ritz0 and run them
# ============================================================================
run_stage1() {
    log "STAGE 1: Compile examples with ritz0 & run"
    echo "----------------------------------------"

    local passed=0
    local failed=0
    local skipped=0

    for example_dir in $(get_examples); do
        local name=$(example_key "$example_dir")
        local base=$(basename "$example_dir")
        local src="$example_dir/src/main.ritz"
        local bin="$BUILD_DIR/stage1_$name"

        # Compile with ritz0
        if ! compile_with "ritz0" "$src" "$bin"; then
            if is_known_failure ritz0 "$name"; then
                warn "$name: ritz0 compile failed (known, allowlisted)"
                skipped=$((skipped + 1))
            else
                fail "$name: ritz0 compile failed"
                failed=$((failed + 1))
            fi
            continue
        fi
        if is_known_failure ritz0 "$name"; then
            warn "$name: on the known-failure allowlist but COMPILES — remove it"
        fi

        # Handle interactive examples (need stdin/file args)
        if is_interactive_example "$base"; then
            # Try to use test.sh if available
            if run_test_script "$example_dir" "$bin"; then
                success "$name (test.sh passed)"
                # Mark as tested so stage3 knows it was validated
                echo "0" > "$BUILD_DIR/stage1_${name}.exit"
                echo "TESTED_VIA_SCRIPT" > "$BUILD_DIR/stage1_${name}.stdout"
                passed=$((passed + 1))
            elif [[ $? -eq 2 ]]; then
                warn "$name: interactive example, no test.sh"
                skipped=$((skipped + 1))
            else
                fail "$name: test.sh failed"
                failed=$((failed + 1))
            fi
            continue
        fi

        # Non-interactive: run and save results for later comparison
        if ! run_binary "$bin" "$BUILD_DIR/stage1_${name}.stdout" "$BUILD_DIR/stage1_${name}.exit"; then
            fail "$name: ritz0 build reported success but produced no runnable binary"
            failed=$((failed + 1))
            continue
        fi

        local exit_code=$(cat "$BUILD_DIR/stage1_${name}.exit")
        success "$name (exit=$exit_code)"
        passed=$((passed + 1))
    done

    echo ""
    echo "Stage 1: $passed passed, $failed failed, $skipped skipped"
    STAGE_RESULTS+=("Stage 1: $passed passed, $failed failed, $skipped skipped")
    TOTAL_PASSED=$((TOTAL_PASSED + passed))
    TOTAL_FAILED=$((TOTAL_FAILED + failed))
    TOTAL_SKIPPED=$((TOTAL_SKIPPED + skipped))

    return 0
}

# ============================================================================
# STAGE 2: Compile ritz1 with ritz0
# ============================================================================
run_stage2() {
    log "STAGE 2: Compile ritz1 with ritz0"
    echo "----------------------------------------"

    local ritz1_dir="$ROOT_DIR/ritz1"
    local ritz1_bin="$ROOT_DIR/ritz1/build/ritz1"

    # Use the Makefile's approach
    cd "$ritz1_dir"

    # Build ritz1 using the Makefile (it has its own build/ dir)
    local make_output
    make_output=$(make ritz1 2>&1)
    local make_status=$?

    if [[ $make_status -eq 0 ]]; then
        success "ritz1 compiled with ritz0"
        cp build/ritz1 "$ritz1_bin"
        STAGE_RESULTS+=("Stage 2: ritz1 compiled successfully")
        TOTAL_PASSED=$((TOTAL_PASSED + 1))
    else
        fail "ritz1 failed to compile with ritz0"
        if [[ $VERBOSE -eq 1 ]]; then
            echo "$make_output"
        fi
        STAGE_RESULTS+=("Stage 2: FAILED - ritz1 compilation error")
        TOTAL_FAILED=$((TOTAL_FAILED + 1))
        cd "$ROOT_DIR"
        return 2
    fi

    cd "$ROOT_DIR"
    echo ""
    return 0
}

# ============================================================================
# STAGE 3: Compile examples with ritz1, compare output with Stage 1
# ============================================================================
run_stage3() {
    log "STAGE 3: Compile examples with ritz1 & compare"
    echo "----------------------------------------"

    local ritz1_bin="$ROOT_DIR/ritz1/build/ritz1"

    if [[ ! -x "$ritz1_bin" ]]; then
        warn "ritz1 not available, skipping Stage 3"
        STAGE_RESULTS+=("Stage 3: SKIPPED - ritz1 not available")
        return 0
    fi

    local passed=0
    local failed=0
    local skipped=0

    for example_dir in $(get_examples); do
        local name=$(example_key "$example_dir")
        local base=$(basename "$example_dir")
        local src="$example_dir/src/main.ritz"
        local bin="$BUILD_DIR/stage3_$name"

        # Check if we have Stage 1 results to compare against
        if [[ ! -f "$BUILD_DIR/stage1_${name}.exit" ]]; then
            warn "$name: no Stage 1 baseline"
            skipped=$((skipped + 1))
            continue
        fi

        # Compile with ritz1
        if ! compile_with "ritz1" "$src" "$bin" 2>/dev/null; then
            record_compile_outcome ritz1 "$name" rejected
            if is_known_failure ritz1 "$name"; then
                warn "$name: ritz1 compile failed (known, allowlisted)"
                skipped=$((skipped + 1))
            else
                fail "$name: ritz1 compile failed"
                failed=$((failed + 1))
            fi
            continue
        fi
        record_compile_outcome ritz1 "$name" accepted
        if is_known_failure ritz1 "$name"; then
            warn "$name: on the ritz1 allowlist but COMPILES — remove it"
        fi

        # Handle interactive examples via test.sh
        if is_interactive_example "$base"; then
            if run_test_script "$example_dir" "$bin"; then
                success "$name (test.sh passed)"
                passed=$((passed + 1))
            elif [[ $? -eq 2 ]]; then
                warn "$name: interactive example, no test.sh"
                skipped=$((skipped + 1))
            else
                fail "$name: test.sh failed"
                failed=$((failed + 1))
            fi
            continue
        fi

        # Run
        if ! run_binary "$bin" "$BUILD_DIR/stage3_${name}.stdout" "$BUILD_DIR/stage3_${name}.exit"; then
            fail "$name: ritz1 build reported success but produced no runnable binary"
            failed=$((failed + 1))
            continue
        fi

        # Compare with Stage 1
        if compare_runs "$name" \
            "$BUILD_DIR/stage1_${name}.stdout" "$BUILD_DIR/stage1_${name}.exit" \
            "$BUILD_DIR/stage3_${name}.stdout" "$BUILD_DIR/stage3_${name}.exit"; then
            passed=$((passed + 1))
        else
            failed=$((failed + 1))
        fi
    done

    mark_stage_ran ritz1

    echo ""
    echo "Stage 3: $passed passed, $failed failed, $skipped skipped"
    STAGE_RESULTS+=("Stage 3: $passed passed, $failed failed, $skipped skipped")
    TOTAL_PASSED=$((TOTAL_PASSED + passed))
    TOTAL_FAILED=$((TOTAL_FAILED + failed))
    TOTAL_SKIPPED=$((TOTAL_SKIPPED + skipped))

    return 0
}

# ============================================================================
# STAGE 4: Self-hosted ritz1 compiles examples, compare with Stage 1
# ============================================================================
run_stage4() {
    log "STAGE 4: Self-hosted ritz1 (bootstrap) & compare"
    echo "----------------------------------------"

    local ritz1_dir="$ROOT_DIR/ritz1"
    local ritz1_selfhosted="$ROOT_DIR/ritz1/build/ritz1_selfhosted"

    # Bootstrap ritz1 (ritz1 compiles itself)
    cd "$ritz1_dir"

    if make -s bootstrap BUILD_DIR="$BUILD_DIR" 2>/dev/null; then
        success "ritz1 self-hosted bootstrap complete"
        # The bootstrap target ignores BUILD_DIR and always emits into
        # ritz1/build/.  The old line here copied "$BUILD_DIR/ritz1_selfhosted"
        # onto $ritz1_selfhosted — the same path — so cp errored, `|| true`
        # swallowed it, and the -x check below always failed.  Stage 4 has
        # therefore never run: it announced "bootstrap complete" and then
        # skipped itself in the same breath.
        local produced=""
        for cand in "$ritz1_dir/build/ritz1_selfhosted" \
                    "$BUILD_DIR/ritz1_selfhosted"; do
            if [[ -x "$cand" ]]; then produced="$cand"; break; fi
        done
        if [[ -n "$produced" && "$produced" != "$ritz1_selfhosted" ]]; then
            cp "$produced" "$ritz1_selfhosted"
        fi
    else
        fail "ritz1 bootstrap failed"
        STAGE_RESULTS+=("Stage 4: FAILED - bootstrap error")
        TOTAL_FAILED=$((TOTAL_FAILED + 1))
        cd "$ROOT_DIR"
        return 2
    fi

    cd "$ROOT_DIR"

    if [[ ! -x "$ritz1_selfhosted" ]]; then
        warn "Self-hosted ritz1 not available"
        STAGE_RESULTS+=("Stage 4: SKIPPED - self-hosted binary not available")
        return 0
    fi

    local passed=0
    local failed=0
    local skipped=0

    for example_dir in $(get_examples); do
        local name=$(example_key "$example_dir")
        local base=$(basename "$example_dir")
        local src="$example_dir/src/main.ritz"
        local bin="$BUILD_DIR/stage4_$name"

        # Check if we have Stage 1 results
        if [[ ! -f "$BUILD_DIR/stage1_${name}.exit" ]]; then
            warn "$name: no Stage 1 baseline"
            skipped=$((skipped + 1))
            continue
        fi

        # Compile with self-hosted ritz1
        if ! compile_with "ritz1_selfhosted" "$src" "$bin" 2>/dev/null; then
            record_compile_outcome ritz1_selfhosted "$name" rejected
            if is_known_failure ritz1_selfhosted "$name"; then
                warn "$name: self-hosted ritz1 compile failed (known, allowlisted)"
                skipped=$((skipped + 1))
            else
                fail "$name: self-hosted ritz1 compile failed"
                failed=$((failed + 1))
            fi
            continue
        fi
        record_compile_outcome ritz1_selfhosted "$name" accepted
        if is_known_failure ritz1_selfhosted "$name"; then
            warn "$name: on the ritz1_selfhosted allowlist but COMPILES — remove it"
        fi

        # Handle interactive examples via test.sh
        if is_interactive_example "$base"; then
            if run_test_script "$example_dir" "$bin"; then
                success "$name (test.sh passed)"
                passed=$((passed + 1))
            elif [[ $? -eq 2 ]]; then
                warn "$name: interactive example, no test.sh"
                skipped=$((skipped + 1))
            else
                fail "$name: test.sh failed"
                failed=$((failed + 1))
            fi
            continue
        fi

        # Run
        if ! run_binary "$bin" "$BUILD_DIR/stage4_${name}.stdout" "$BUILD_DIR/stage4_${name}.exit"; then
            fail "$name: self-hosted ritz1 build reported success but produced no runnable binary"
            failed=$((failed + 1))
            continue
        fi

        # Compare with Stage 1
        if compare_runs "$name" \
            "$BUILD_DIR/stage1_${name}.stdout" "$BUILD_DIR/stage1_${name}.exit" \
            "$BUILD_DIR/stage4_${name}.stdout" "$BUILD_DIR/stage4_${name}.exit"; then
            passed=$((passed + 1))
        else
            failed=$((failed + 1))
        fi
    done

    mark_stage_ran ritz1_selfhosted

    echo ""
    echo "Stage 4: $passed passed, $failed failed, $skipped skipped"
    STAGE_RESULTS+=("Stage 4: $passed passed, $failed failed, $skipped skipped")
    TOTAL_PASSED=$((TOTAL_PASSED + passed))
    TOTAL_FAILED=$((TOTAL_FAILED + failed))
    TOTAL_SKIPPED=$((TOTAL_SKIPPED + skipped))

    return 0
}

# ============================================================================
# STAGE 5: self-hosting fixed-point check (ritz1 vs ritz1_selfhosted)
# ============================================================================
#
# Asserts one thing, and asserts it unconditionally:
#
#     accepted_by_ritz1  ==  accepted_by_ritz1_selfhosted
#
# ritz1_selfhosted is the compiler that ritz1 built from ritz1's own source.
# If the two disagree about whether a given program compiles, then compiling
# the compiler changed the compiler's behaviour — the self-hosting fixed point
# has not been reached.  That is a more serious defect than any single example
# failing to build, because it means the artefact stages 3 and 4 are testing is
# not stable under its own construction.
#
# This stage reads NO allowlist, by design.  Stages 3 and 4 each consult the
# (shared) ritz1 allowlist and downgrade a listed compile failure to a skip;
# that is legitimate for "we know ritz1 can't build this yet", but it made the
# divergence invisible, because each stage skipped its side independently and
# the two sides were never brought together.  Here the two accept sets are
# compared directly, so no allowlist entry — present, absent, or added later in
# a panic — can change the verdict.  There is deliberately no escape hatch:
#
#   * An allowlist may say "this program is known not to compile."
#   * It must never be able to say "these two compilers may disagree."
#
# If this stage is red, do not edit an allowlist.  It will not help, and the
# next reader will have to rediscover why.  Fix the compiler.
run_stage5() {
    log "STAGE 5: self-hosting fixed-point check (ritz1 vs ritz1_selfhosted)"
    echo "----------------------------------------"

    local a="$BUILD_DIR/acceptset_ritz1.accepted"
    local b="$BUILD_DIR/acceptset_ritz1_selfhosted.accepted"

    # Both stages must actually have run over the corpus.  Comparing a set
    # against a set that was never populated is not a check, it is a green.
    if [[ ! -f "$BUILD_DIR/acceptset_ritz1.ran" || \
          ! -f "$BUILD_DIR/acceptset_ritz1_selfhosted.ran" ]]; then
        warn "Stage 3 and/or Stage 4 did not run — fixed-point check not performed"
        STAGE_RESULTS+=("Stage 5: SKIPPED - needs both Stage 3 and Stage 4")
        return 0
    fi

    local only_a only_b
    only_a=$(comm -23 <(sort -u "$a") <(sort -u "$b"))
    only_b=$(comm -13 <(sort -u "$a") <(sort -u "$b"))

    if [[ -z "$only_a" && -z "$only_b" ]]; then
        local n
        n=$(sort -u "$a" | grep -c . || true)
        success "ritz1 and ritz1_selfhosted accept an identical set of $n examples"
        STAGE_RESULTS+=("Stage 5: fixed point holds ($n examples, sets identical)")
        TOTAL_PASSED=$((TOTAL_PASSED + 1))
        return 0
    fi

    local divergent=0
    while IFS= read -r k; do
        [[ -n "$k" ]] || continue
        fail "$k: accepted by ritz1, REJECTED by ritz1_selfhosted"
        divergent=$((divergent + 1))
    done <<< "$only_a"
    while IFS= read -r k; do
        [[ -n "$k" ]] || continue
        fail "$k: REJECTED by ritz1, accepted by ritz1_selfhosted"
        divergent=$((divergent + 1))
    done <<< "$only_b"

    echo ""
    fail "Self-hosting fixed point NOT reached: $divergent example(s) diverge."
    echo "  ritz1_selfhosted is ritz1 compiled by ritz1.  The two disagreeing"
    echo "  about what compiles means compiling the compiler changed it."
    echo "  This is NOT allowlistable — no entry in any known-failures file can"
    echo "  silence it, and adding one will not turn this stage green."

    STAGE_RESULTS+=("Stage 5: FAILED - $divergent example(s) diverge between ritz1 and ritz1_selfhosted")
    TOTAL_FAILED=$((TOTAL_FAILED + divergent))
    return 1
}

# ============================================================================
# Main
# ============================================================================

# Allow a test to source this file for its helper functions without running the
# suite.  Stage 5 is the one check here that no allowlist can silence, which
# makes it exactly the check that must not be allowed to rot silently — but
# exercising it end-to-end costs a full bootstrap (~6 min), so in practice it
# would never be re-verified.  Sourcing lets scripts/test-regression-stage5.sh
# feed it synthetic accept sets and assert the verdict in well under a second.
#
# Sourcers MUST reset BUILD_DIR and clear the EXIT trap installed above; see
# that test for the pattern.
if [[ -n "${RITZ_REGRESSION_LIB_ONLY:-}" ]]; then
    return 0 2>/dev/null || exit 0
fi

echo ""
echo "🎭 Ritz Regression Test Suite"
echo "======================================"
echo ""

# Run selected stages
if [[ -n "$RUN_STAGE" ]]; then
    case $RUN_STAGE in
        1) run_stage1 ;;
        2) run_stage2 ;;
        3) run_stage1; run_stage2; run_stage3 ;;
        4) run_stage1; run_stage2; run_stage4 ;;
        # Stage 5 compares stages 3 and 4, so selecting it runs both.  It
        # cannot be run standalone: there is nothing to compare.
        5) run_stage1; run_stage2; run_stage3; run_stage4; echo ""; run_stage5 ;;
        *)
            echo "Invalid stage: $RUN_STAGE (must be 1-5)"
            exit 1
            ;;
    esac
else
    # Run all stages
    run_stage1
    echo ""
    run_stage2
    echo ""
    run_stage3
    echo ""

    if [[ $QUICK_MODE -eq 0 ]]; then
        run_stage4
        echo ""
        run_stage5
        echo ""
    else
        echo "Stage 4: SKIPPED (--quick mode)"
        STAGE_RESULTS+=("Stage 4: SKIPPED (--quick mode)")
        # Stage 5 needs stage 4's accept set, so --quick necessarily forgoes
        # the fixed-point check.  Say so explicitly rather than letting a
        # quick run look like a full one in the summary.
        echo "Stage 5: SKIPPED (--quick mode: needs Stage 4)"
        STAGE_RESULTS+=("Stage 5: SKIPPED (--quick mode: needs Stage 4)")
    fi
fi

# Summary
echo "======================================"
echo "📊 Summary"
echo "======================================"
for result in "${STAGE_RESULTS[@]}"; do
    echo "  $result"
done
echo ""
echo "Total: $TOTAL_PASSED passed, $TOTAL_FAILED failed, $TOTAL_SKIPPED skipped"
echo ""

if [[ $TOTAL_FAILED -eq 0 ]]; then
    echo -e "${GREEN}🎉 All regression tests passed!${NC}"
    exit 0
else
    echo -e "${RED}💥 Some regression tests failed${NC}"
    # Preserve the captured stdout/exit files so the failure can be diagnosed
    # after the fact.  See cleanup_build_dir.
    KEEP_ARTIFACTS=1
    exit 1
fi
