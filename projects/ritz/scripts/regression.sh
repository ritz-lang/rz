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
#   ./scripts/regression.sh --jobs 4    # Examples built/run at once (default 8)
#   ./scripts/regression.sh --no-baseline-cache   # Recompute Stage 1
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

# A block of TCP ports per regression run, for the server examples (AGAST
# #1535, per example since #1806).
#
# 74_async_tiers, 75_tier2_uring and 76_tier3_http used to bind fixed ports.
# Rooms gate in parallel on one host, so the second run to reach 75 found 9002
# taken, printed "Failed to bind", exited 0 -- and compare_runs called that a
# termination change: a false red that teaches people to rerun until green.
#
# Examples now run in parallel (AGAST #1806), so each server needs its own
# port: example number i (its position in the sorted corpus) gets base + i.
# The port reaches the program as RITZ_EXAMPLE_PORT in run_binary's fixed
# `env -i` environment, and ONLY for examples whose source reads
# RITZ_EXAMPLE_PORT (example_port).  31_env and 33_printenv print their
# environment verbatim; handing them a random per-run port would make their
# output differ from run to run, which the Stage 1 baseline cache cannot have.
# The index is the same in every stage, so a server sees the same port in each.
#
# The block's base is picked at random from 20000-32767 -- below Linux's
# ephemeral range (32768-60999), so an outgoing connection elsewhere on the
# host cannot be handed one -- and every port in it is probed free.  Nothing holds it between the
# probe and the bind, so a collision is still possible, just rare; when it
# happens run_binary classifies it as an infrastructure error (see there),
# never as a compiler result.  A caller-supplied RITZ_EXAMPLE_PORT wins, so a
# failing run can be reproduced exactly.
# Args: [$1=block size, default 1].  Prints the base of a free block.
pick_example_port() {
    python3 - "${1:-1}" <<'PY'
import random, socket, sys
n = int(sys.argv[1])
def free(p):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", p))
        return True
    except OSError:
        return False
    finally:
        s.close()
for _ in range(200):
    p = random.randint(20000, 32768 - n)
    if all(free(p + i) for i in range(n)):
        print(p)
        break
PY
}
# Ports per run; example i uses base + (i % EXAMPLE_PORT_BLOCK).
EXAMPLE_PORT_BLOCK=256
REGRESSION_EXAMPLE_PORT="${RITZ_EXAMPLE_PORT:-$(pick_example_port "$EXAMPLE_PORT_BLOCK")}"
if [[ ! "$REGRESSION_EXAMPLE_PORT" =~ ^[0-9]+$ ]]; then
    echo "regression.sh: could not choose a free port for the server examples" >&2
    exit 1
fi

# Counters
TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_SKIPPED=0
STAGE_RESULTS=()

# Options
RUN_STAGE=""
QUICK_MODE=0
VERBOSE=0

# Examples built and run at once in Stages 1, 3 and 4 (AGAST #1806).  Output
# is still printed in corpus order, so a log does not depend on this.
REGRESSION_JOBS="${REGRESSION_JOBS:-8}"

# Stage 1 baseline cache (AGAST #1806): ritz0's observation of an example
# (built? test.sh result, stdout, exit) depends only on inputs that
# regression_baseline_keys.py hashes, so it is reused until one changes.
# Outside BUILD_DIR, which the gate wipes.  Only clean passes are cached.
BASELINE_CACHE_DIR="${RITZ_REGRESSION_BASELINE_CACHE:-$ROOT_DIR/.regression-cache}"
USE_BASELINE_CACHE=1

# Run budget for an ordinary example, and for one declared below as never
# exiting.  A server or generator is killed either way; the short budget just
# stops it costing 5 s per stage.
RUN_BUDGET=5s
NONTERM_BUDGET="${REGRESSION_NONTERM_BUDGET:-2s}"

# Examples that never exit on their own: servers waiting for a client, and
# 09_yes, which writes until the 1 MiB output cap kills it.  Each gets
# NONTERM_BUDGET and the verdict "ran until killed, as expected".  The list
# cannot rot quietly: a declared example that exits on its own, or that is no
# longer in the corpus, fails Stage 1.  An undeclared example that has to be
# killed is still compared as non-terminating, with a warning to declare it.
NONTERMINATING_EXAMPLES=(
    tier1_basics_09_yes
    tier5_async_50_http
    74_async_tiers
    75_tier2_uring
    76_tier3_http
)

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
        --jobs|-j)
            REGRESSION_JOBS="$2"
            shift 2
            ;;
        --no-baseline-cache)
            USE_BASELINE_CACHE=0
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --stage N    Run only stage N (1-5)"
            echo "  --quick      Skip Stage 4 (self-hosted bootstrap) and Stage 5"
            echo "  --verbose    Show detailed output"
            echo "  --jobs N     Examples built and run at once (default \$REGRESSION_JOBS or 8)"
            echo "  --no-baseline-cache"
            echo "               Recompute Stage 1 instead of reusing cached ritz0 results"
            echo "  --help       Show this message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [[ ! "$REGRESSION_JOBS" =~ ^[1-9][0-9]*$ ]]; then
    echo "regression.sh: --jobs / REGRESSION_JOBS must be a positive integer, got '$REGRESSION_JOBS'" >&2
    exit 1
fi

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

# An example's test.sh is the ONLY thing in this suite that asserts a program
# produces the *right* answer.  Everything else compares stage against stage,
# which three compilers agreeing on the same wrong output passes.
#
# This used to be gated on a hardcoded name list:
#
#     INTERACTIVE_EXAMPLES="05_cat 06_grep 07_wc 08_echo 09_head 10_tail"
#
# Four of those six names no longer existed (the corpus was renumbered: 08_echo
# is 03_echo, 09_head is 06_head, 06_grep and 10_tail are gone).  So of the 68
# examples that ship a test.sh, exactly 2 ever had it executed.  66 files of
# real assertions -- 06_head/test.sh checks default-10-lines, `-n 5` and the
# stdin path against `seq` output and exits 1 on mismatch -- had never run in
# CI.  See AGAST #1359.
#
# The trigger is now the file's existence.  There is no list to rot, and
# assert_test_scripts_all_ran() below fails the suite if the number executed
# ever drops below the number on disk, so adding an example with a test.sh
# cannot silently opt out of correctness checking.
has_test_script() {
    [[ -f "$1/test.sh" ]]
}

# Examples whose test.sh we actually executed this run, one key per line.
# Written to a file rather than a shell array because the stage loops run in
# `$(...)` subshells in some invocations.
TEST_SCRIPTS_RAN_FILE=""

note_test_script_ran() {
    [[ -n "$TEST_SCRIPTS_RAN_FILE" ]] && echo "$1" >> "$TEST_SCRIPTS_RAN_FILE"
}

# Resolve the binary name build.py will emit for an example: [[bin]] name if
# present, else [package] name.  50 of 81 examples have no [[bin]] section, so
# the [package] branch is the common case.  basename($dir) is NOT a valid
# fallback -- the dir is `02_exitcode`, the package is `exitcode` -- and using
# it made run_test_script symlink the binary under a name test.sh never looks
# for, producing empty output that scored as a failure (or, for a test
# expecting empty output, as a false pass).
#
# resolve_bin_names emits ALL of them, one per line; resolve_bin_name emits the
# first.  An example may declare several: 04_true_false builds `true` and
# `false` from src/true.ritz and src/false.ritz, and its test.sh exercises both.
resolve_bin_names() {
    local toml="$1/ritz.toml"
    local n
    n=$(awk '/^\[\[bin\]\]/{inbin=1; next} /^\[/{inbin=0} inbin && /^name[[:space:]]*=/{gsub(/.*=[[:space:]]*"|".*/, ""); print}' "$toml" 2>/dev/null)
    if [[ -z "$n" ]]; then
        n=$(awk '/^\[package\]/{found=1} found && /^name[[:space:]]*=/{gsub(/.*=[[:space:]]*"|".*/, ""); print; exit}' "$toml" 2>/dev/null)
    fi
    echo "$n"
}

resolve_bin_name() {
    resolve_bin_names "$1" | head -1
}

# Get the list of example directories.
#
# Examples are NOT all at examples/<name>/ — the tier5_async corpus lives one
# level deeper at examples/tier5_async/<name>/.  A `-maxdepth 1` walk (what
# this used to do) saw 17 of 85 example dirs, and the 11 of those with a
# src/main.ritz happened to be exactly the known-broken set.  Every stage
# then skipped everything and the suite exited 0 having asserted nothing.
# Walk the whole tree and let the per-directory probe decide.
#
# src/main.ritz is the usual entry point but NOT the only one.  An example that
# declares its binaries explicitly is free to name their sources anything:
# 04_true_false builds `true` from src/true.ritz and `false` from src/false.ritz
# and has no main.ritz at all.  Keying discovery on main.ritz made that example
# invisible to every stage of this suite -- never compiled, never run, and its
# test.sh (which checks `./true` exits 0 and `./false` exits 1) never executed.
# It was reported neither as a pass nor a failure; it simply did not appear.
#
# So: a directory is an example if it has src/main.ritz, OR if its ritz.toml
# declares at least one [[bin]].  A ritz.toml with neither (test_deps/squeeze,
# a library dependency) is correctly still excluded.
get_examples() {
    {
        find "$EXAMPLES_DIR" -mindepth 1 -type f -path '*/src/main.ritz' \
            -not -path '*/build/*' -printf '%h\n' | sed 's|/src$||'
        while read -r toml; do
            grep -q '^\[\[bin\]\]' "$toml" 2>/dev/null && dirname "$toml"
        done < <(find "$EXAMPLES_DIR" -mindepth 1 -type f -name ritz.toml -not -path '*/build/*')
    } | sort -u
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

# Strict xpass: an allowlisted example that COMPILES fails the stage.
#
# This used to be a warn().  A warning does not force anything: the entry stays,
# the suite stays green, and the list drifts from the compiler it claims to
# describe.  That is the same "advisory gate is not a gate" shape main.yml
# rejects for continue-on-error, and this file's own header already asserts the
# stricter rule -- "The list should shrink" -- without enforcing it.  rz.toml's
# [ci.known_failing.build] has enforced strict-xpass all along; this list, which
# guards the compiler corpus, was the weaker of the two.
#
# Discovered 2026-09-07 (AGAST #1365): 74_async_tiers and 75_tier2_uring were
# allowlisted as "async/uring corpus -- unmigrated against the current async
# framework".  Both were in fact blocked only on the legacy `&x` address-of
# syntax that commit 6da1440 migrated everywhere else; 76_tier3_http, the third
# member of the same ladder, was migrated and is not on the list.  Two lines of
# sed made both compile.  Nothing told anyone, because the check only warned.
#
# Args: $1=compiler, $2=example key.  Returns 0 if this is an xpass.
report_xpass() {
    fail "$2: on the $1 known-failure allowlist but COMPILES — delete the line in $(basename "$(known_failures_file "$1")")"
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
# Args: $1=compiler, $2=example_dir, $3=output_binary
#
# Takes the example DIRECTORY, not a source path.  It used to take
# "$example_dir/src/main.ritz" and recover the directory with
# dirname(dirname(...)) -- which happened to work even for examples that have
# no main.ritz, but only by accident, and it made the callers assert a file
# exists that for 04_true_false does not.  build.py builds the package by path
# and decides for itself which sources to compile.
compile_with() {
    local compiler="$1"
    local example_dir="$2"
    local output="$3"
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
        # the common case, not the exception.  Shared with run_test_script so
        # the two cannot drift apart -- they did, and run_test_script's copy
        # (which fell back to basename) is what #1359 records.
        local bin_name
        bin_name=$(resolve_bin_name "$example_dir")
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

# Per-run settings, read by run_binary.  A stage worker sets them as locals
# for its one example (bash locals are dynamically scoped, and every worker is
# its own subshell), so parallel examples cannot see each other's:
#   RUN_SANDBOX  the example's own sandbox dir (default: a shared one)
#   RUN_PORT     RITZ_EXAMPLE_PORT for a server example (default: none)
#   RUN_TIMEOUT  kill budget (default: RUN_BUDGET)
RUN_SANDBOX=""
RUN_PORT=""
RUN_TIMEOUT=""

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
    rm -f "${exit_file}.nonterminating" "${exit_file}.infra"

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
    # nondeterminism this is meant to remove.  Per example since #1806
    # ($BUILD_DIR/sandbox/<key>, set by the stage worker): the same path in
    # every stage, and never shared with an example running alongside.
    local sandbox="${RUN_SANDBOX:-$BUILD_DIR/sandbox/default}"
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
    # Fixed process environment, for exactly the reason the fixture tree above
    # exists.  31_env and 33_printenv print `environ` verbatim, so their output
    # is a function of the ambient environment rather than of the compiled
    # program -- and the harness itself perturbs that environment between
    # stages: stage 2 does `cd "$ritz1_dir"` then `cd "$ROOT_DIR"` to build
    # ritz1, which changes OLDPWD.  Stage 1 captured
    #     OLDPWD=/home/aaron/dev/ritz-lang/rz
    # and stage 3 ran with
    #     OLDPWD=/home/aaron/dev/ritz-lang/rz/projects/ritz
    # so the byte comparison reported "output mismatch" on line 50 for a
    # compiler that was behaving perfectly.  It only surfaced at all because
    # the invocation cwd happened to differ from ROOT_DIR that run, which makes
    # it worse, not better: the suite's verdict depended on where you typed the
    # command from.
    #
    # `env -i` with an explicit allowlist rather than unsetting OLDPWD alone:
    # unsetting the one variable that bit us today is whack-a-mole, and the
    # whole point of the sandbox above is that we make the environment
    # identical and KEEP the strict comparison instead of allowlisting the
    # programs that notice.  PWD is omitted deliberately -- `cd` sets it, and
    # to the fixed sandbox path.
    #
    # RITZ_EXAMPLE_PORT only when the worker assigned one (a server example;
    # see example_port), so it is not part of every program's environment.
    local -a port_env=()
    [[ -n "$RUN_PORT" ]] && port_env=(RITZ_EXAMPLE_PORT="$RUN_PORT")
    #
    # The `{ ...; } 2>/dev/null` is for bash, not the program (whose stderr
    # goes to $raw): when the output cap kills 09_yes with SIGXFSZ, bash
    # reports "File size limit exceeded" with the whole command line on its
    # own stderr, three times per gate.  That death is the expected outcome
    # and is recorded below as exit 153 / non-terminating.
    { ( cd "$sandbox" && ulimit -f 1024 && \
      exec env -i \
        PATH=/usr/local/bin:/usr/bin:/bin \
        HOME=/nonexistent \
        LANG=C \
        LC_ALL=C \
        TZ=UTC \
        SHELL=/bin/sh \
        TERM=dumb \
        "${port_env[@]}" \
        timeout --signal=KILL "${RUN_TIMEOUT:-$RUN_BUDGET}" "$binary" < /dev/null > "$raw" 2>&1 ); } 2>/dev/null
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

    # A server that could not bind its port never ran: what we captured says
    # something about the host (another process, another regression run),
    # nothing about the compiler.  Record that separately so compare_runs can
    # say so, rather than reading "exited at once" as a termination change --
    # AGAST #1535.  Matches every server's wording ("Failed to bind",
    # "Failed to bind to port N") at the start of a line.
    if grep -q '^Failed to bind' "$stdout_file" 2>/dev/null; then
        echo "1" > "${exit_file}.infra"
    fi
    return 0
}

# Run example's test.sh if it exists
# Args: $1=example_dir, $2=binary_path
run_test_script() {
    local example_dir="$1"
    local binary="$2"
    local test_script="$example_dir/test.sh"

    if [[ ! -f "$test_script" ]]; then
        return 200  # No test script -- sentinel, see below
    fi

    # Sentinels are 200/201, not 2/3.  A test.sh is free to `exit 2`, and the
    # callers distinguish "no test script" from "test failed" by return value;
    # overlapping the two ranges would let a genuinely failing test be reported
    # as an absent one.  Nothing in the corpus exits 200+.

    # Invoke through `bash`, not by executing the file, so a lost +x bit is not
    # silently equivalent to "this example has no tests".  Four test.sh files
    # (52_uring, 53_async, 54_async_fs, 55_async_state_machine) are committed
    # mode 100644; under the old `[[ ! -x ]]` guard they returned 2 and were
    # counted as skips.  The +x bits are being restored too, but the harness
    # should not depend on a file mode to decide whether assertions exist.
    # Resolve before cd: $binary is given relative to the caller's cwd.
    local abs_binary
    abs_binary=$(cd "$(dirname "$binary")" && pwd)/$(basename "$binary")

    local bin_name
    bin_name=$(resolve_bin_name "$example_dir")
    if [[ -z "$bin_name" ]]; then
        return 201  # ritz.toml declares no usable name -- NOT a pass
    fi

    local orig_dir=$(pwd)
    cd "$example_dir"

    # Link EVERY declared binary, not just the first.  04_true_false's test.sh
    # runs `./true` and `./false`; linking only `./true` would leave `./false`
    # missing, the script would exit 127, and the example would be reported as
    # a behavioural failure of the compiler rather than of the harness.
    #
    # Each name resolves to build/debug/<name>, which compile_with just
    # produced with the compiler under test (it rm -rf's that dir first, so
    # nothing stale can survive there).  $abs_binary is the copy compile_with
    # took of the primary binary and stands in if the build dir has moved on.
    local -a linked=()
    local n
    while read -r n; do
        [[ -n "$n" ]] || continue
        if [[ -x "build/debug/$n" ]]; then
            ln -sf "$PWD/build/debug/$n" "./$n" 2>/dev/null || cp "build/debug/$n" "./$n"
        else
            ln -sf "$abs_binary" "./$n" 2>/dev/null || cp "$abs_binary" "./$n"
        fi
        linked+=("$n")
    done < <(resolve_bin_names "$example_dir")

    timeout --signal=KILL 30s bash "$test_script" >/dev/null 2>&1
    local result=$?

    for n in "${linked[@]}"; do rm -f "./$n"; done
    cd "$orig_dir"
    return $result
}

# Run an example's test.sh, if it has one, and report.
# Args: $1=example_dir, $2=example_key, $3=binary
# Returns 0 if there is nothing to run or the test passed; 1 if it failed.
# Records the example in the "ran" ledger so assert_test_scripts_all_ran() can
# prove no example silently dropped out of correctness checking.
check_test_script() {
    local example_dir="$1"
    local name="$2"
    local bin="$3"

    has_test_script "$example_dir" || return 0

    run_test_script "$example_dir" "$bin"
    local rc=$?

    case $rc in
        0)
            note_test_script_ran "$name"
            return 0
            ;;
        201)
            # Present but unrunnable: ritz.toml gives no binary name, so the
            # symlink test.sh expects could not be created.  Deliberately NOT
            # recorded as "ran" and deliberately a failure -- an example whose
            # assertions cannot be executed is the exact shape of the defect
            # this whole change exists to stop reporting as green.
            fail "$name: test.sh present but ritz.toml declares no package/bin name"
            return 1
            ;;
        200)
            return 0  # has_test_script said yes; unreachable
            ;;
        *)
            note_test_script_ran "$name"
            fail "$name: test.sh failed (exit $rc)"
            return 1
            ;;
    esac
}

# Fail the suite if any example that ships a test.sh did not have it executed.
#
# The point of this is that the fix above must not itself rot.  The previous
# mechanism was correct on the day it was written and matched 2 of 68 examples
# by the time anyone looked; #1327 and #1333 are two more allowlists that
# decayed the same way.  A floor keyed off the filesystem cannot drift: add an
# example with a test.sh and either it runs or the suite goes red.
#
# Legitimate non-runs are compile failures, which are already reported (or
# allowlisted) by the caller.  Those are passed in as $@ and excluded.
assert_test_scripts_all_ran() {
    local -a excused=("$@")
    local on_disk ran missing=0

    while read -r ts; do
        local dir="${ts%/test.sh}"
        local key
        key=$(example_key "$dir")
        local is_excused=0
        for e in "${excused[@]}"; do
            [[ "$e" == "$key" ]] && is_excused=1 && break
        done
        [[ $is_excused -eq 1 ]] && continue
        if ! grep -qxF "$key" "$TEST_SCRIPTS_RAN_FILE" 2>/dev/null; then
            fail "$key: ships a test.sh that was never executed"
            missing=$((missing + 1))
        fi
    done < <(find "$EXAMPLES_DIR" -mindepth 2 -name test.sh -not -path '*/build/*')

    on_disk=$(find "$EXAMPLES_DIR" -mindepth 2 -name test.sh -not -path '*/build/*' | wc -l)
    ran=$(sort -u "$TEST_SCRIPTS_RAN_FILE" 2>/dev/null | wc -l)
    echo "test.sh coverage: $ran executed / $on_disk on disk (${#excused[@]} excused: compile failure)"

    if [[ $missing -gt 0 ]]; then
        fail "$missing example(s) ship assertions that never ran — see AGAST #1359"
        return 1
    fi
    return 0
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

    # Infrastructure first (see run_binary): a side that could not bind its
    # port never really ran, so no behavioural verdict -- termination, exit
    # code or bytes -- can be drawn from it.  Still a failure, since nothing
    # was verified, but a distinct one: rerunning is the right response here
    # and ONLY here.
    local side
    for side in A:"$exit_a" B:"$exit_b"; do
        if [[ -f "${side#*:}.infra" ]]; then
            fail "$name: infrastructure error — side ${side%%:*} could not bind its port (its RITZ_EXAMPLE_PORT, from base $REGRESSION_EXAMPLE_PORT, in use?); not a compiler result"
            return 1
        fi
    done

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
# Parallel corpus runs (AGAST #1806)
# ============================================================================
#
# Stages 1, 3 and 4 each build and run every example.  One at a time that was
# 4-6 minutes a stage locally.  Each example's work is now a worker function
# run in a bounded pool of REGRESSION_JOBS background subshells.  A worker
# writes everything it reports to its own log and its verdict to its own
# file; once the pool drains, the stage prints the logs in corpus order and
# tallies the verdicts.  So the output of a stage is the same, byte for byte,
# for any REGRESSION_JOBS: gate logs stay diffable, and a parallel run can be
# diffed against a serial one (REGRESSION_JOBS=1).
#
# What made the examples unsafe to run side by side, and what fixed it:
#   * one $BUILD_DIR/sandbox for every run      -> RUN_SANDBOX per example
#   * one RITZ_EXAMPLE_PORT for every server    -> base + example index
#   * build.py's shared .ritz-cache rewritten   -> cache.py merges entries
#     wholesale, in place                          under a lock, atomically
# Anything a worker appends to a shared ledger (accept sets, test.sh ledger)
# is one short line, which O_APPEND writes whole.

# A worker records its verdict.  Args: $1=result prefix, $2=pass|fail|skip
_verdict() { echo "$2" > "$1.verdict"; }

# Args: $1=results dir, $2=worker fn, rest=example dirs.  Runs
# "$fn <index> <example_dir> <result prefix>" for each, REGRESSION_JOBS at
# a time; stdout and stderr go to "<result prefix>.log".
run_pool() {
    local rdir="$1" fn="$2"; shift 2
    rm -rf "$rdir"
    mkdir -p "$rdir"
    local i=0 running=0 dir out
    for dir in "$@"; do
        if (( running >= REGRESSION_JOBS )); then
            wait -n
            running=$((running - 1))
        fi
        out="$rdir/$(printf '%05d' "$i")"
        echo "$dir" > "$out.dir"
        ( "$fn" "$i" "$dir" "$out" ) > "$out.log" 2>&1 &
        running=$((running + 1))
        i=$((i + 1))
    done
    wait
}

# Print a pool's logs in corpus order and tally its verdicts into the
# caller's `passed`/`failed`/`skipped` (bash dynamic scope).
collect_pool() {
    local rdir="$1" f v
    for f in "$rdir"/*.log; do
        [[ -e "$f" ]] || continue
        cat "$f"
        v=$(cat "${f%.log}.verdict" 2>/dev/null)
        case "$v" in
            pass) passed=$((passed + 1)) ;;
            skip) skipped=$((skipped + 1)) ;;
            fail) failed=$((failed + 1)) ;;
            *)
                # A worker that died before recording a verdict asserted
                # nothing; it must not vanish from the count.
                fail "worker $(basename "${f%.log}") ($(head -c 200 "${f%.log}.dir" 2>/dev/null)) recorded no verdict"
                failed=$((failed + 1))
                ;;
        esac
    done
}

is_declared_nonterminating() {
    local k
    for k in "${NONTERMINATING_EXAMPLES[@]}"; do
        [[ "$k" == "$1" ]] && return 0
    done
    return 1
}

# The port a server example is given, or nothing for any other example.
# Args: $1=example_dir, $2=corpus index
example_port() {
    if grep -rqs --exclude-dir=build 'RITZ_EXAMPLE_PORT' "$1"/src; then
        echo $((REGRESSION_EXAMPLE_PORT + $2 % EXAMPLE_PORT_BLOCK))
    fi
}

# Set a worker's run_binary settings for one example.  Must be called as
# `local RUN_SANDBOX RUN_PORT RUN_TIMEOUT; example_run_settings ...` so they
# stay local to that worker.  Args: $1=example_dir, $2=key, $3=index
example_run_settings() {
    RUN_SANDBOX="$BUILD_DIR/sandbox/$2"
    RUN_PORT=$(example_port "$1" "$3")
    RUN_TIMEOUT="$RUN_BUDGET"
    is_declared_nonterminating "$2" && RUN_TIMEOUT="$NONTERM_BUDGET"
    return 0
}

# ============================================================================
# STAGE 1: Compile all examples with ritz0 and run them
# ============================================================================
#
# Split in two so the expensive half can be cached:
#
#   stage1_observe  build with ritz0, run test.sh, run the binary.  Raw facts
#                   only, into an observation dir: `compiled`, `testrc` (only
#                   if a test.sh ran), `ran`, `stdout`, `exit` and its
#                   markers.  Consults no allowlist.
#   stage1_judge    turn an observation into a verdict with the allowlist,
#                   the declared non-terminating list and the test.sh ledger,
#                   and publish stage1_<key>.{stdout,exit} -- the baseline
#                   Stages 3 and 4 compare against -- only for a pass.
#
# The judge runs every time; only the observation comes from the cache.  So
# an allowlist edit takes effect at once, and a cache hit reports exactly
# what a cold run would.

# Args: $1=example_dir, $2=key, $3=observation dir.  Uses the caller's
# RUN_* settings.  Stops where the old serial loop stopped: no test.sh run
# without a binary, no binary run after a failed test.sh.
stage1_observe() {
    local example_dir="$1" name="$2" obs="$3"
    local bin="$BUILD_DIR/stage1_$name"
    rm -rf "$obs"
    mkdir -p "$obs"
    if ! compile_with "ritz0" "$example_dir" "$bin"; then
        echo 0 > "$obs/compiled"
        return 0
    fi
    echo 1 > "$obs/compiled"
    if has_test_script "$example_dir"; then
        run_test_script "$example_dir" "$bin"
        local rc=$?
        echo "$rc" > "$obs/testrc"
        [[ $rc -eq 0 ]] || return 0
    fi
    if run_binary "$bin" "$obs/stdout" "$obs/exit"; then
        echo 1 > "$obs/ran"
    else
        echo 0 > "$obs/ran"
    fi
}

# A clean pass, safe to cache: built, test.sh (if any) passed, ran, and no
# infrastructure error (a port collision is about the host, not ritz0).
# Failures are never cached, so a flaky failure cannot outlive its run.
stage1_cacheable() {
    local obs="$1"
    [[ "$(cat "$obs/compiled" 2>/dev/null)" == 1 ]] || return 1
    [[ ! -f "$obs/testrc" || "$(cat "$obs/testrc")" == 0 ]] || return 1
    [[ "$(cat "$obs/ran" 2>/dev/null)" == 1 ]] || return 1
    [[ ! -f "$obs/exit.infra" ]]
}

# Args: $1=example_dir, $2=key, $3=observation dir, $4=result prefix
stage1_judge() {
    local example_dir="$1" name="$2" obs="$3" out="$4"

    if [[ "$(cat "$obs/compiled" 2>/dev/null)" != 1 ]]; then
        # Excused from the test.sh coverage floor: you cannot run a binary
        # that was never produced.  The compile failure itself is reported
        # (or allowlisted) here.
        : > "$out.nocompile"
        if is_known_failure ritz0 "$name"; then
            warn "$name: ritz0 compile failed (known, allowlisted)"
            _verdict "$out" skip
        else
            fail "$name: ritz0 compile failed"
            _verdict "$out" fail
        fi
        return 0
    fi
    if is_known_failure ritz0 "$name"; then
        report_xpass ritz0 "$name"
        _verdict "$out" fail
        return 0
    fi

    # Correctness gate: the example's own test.sh, if it ships one.
    #
    # This no longer REPLACES the run-and-record below -- it precedes it.
    # The old code, for the 2 examples it reached, wrote the literal string
    # "TESTED_VIA_SCRIPT" as the stage-1 baseline, which removed those
    # examples from the cross-stage differential entirely.  Running both
    # means an example with a test.sh is checked for the right answer here
    # AND for ritz0/ritz1/ritz1_selfhosted agreement in stages 3 and 4.
    # (Reported as check_test_script does; see there.)
    if [[ -f "$obs/testrc" ]]; then
        local rc
        rc=$(cat "$obs/testrc")
        case "$rc" in
            0) note_test_script_ran "$name" ;;
            201)
                fail "$name: test.sh present but ritz.toml declares no package/bin name"
                _verdict "$out" fail
                return 0
                ;;
            *)
                note_test_script_ran "$name"
                fail "$name: test.sh failed (exit $rc)"
                _verdict "$out" fail
                return 0
                ;;
        esac
    fi

    if [[ "$(cat "$obs/ran" 2>/dev/null)" != 1 ]]; then
        fail "$name: ritz0 build reported success but produced no runnable binary"
        _verdict "$out" fail
        return 0
    fi

    local exit_code
    exit_code=$(cat "$obs/exit")
    if is_declared_nonterminating "$name"; then
        if [[ ! -f "$obs/exit.nonterminating" && ! -f "$obs/exit.infra" ]]; then
            fail "$name: declared non-terminating but exited on its own (exit=$exit_code) — fix it, or remove it from NONTERMINATING_EXAMPLES"
            _verdict "$out" fail
            return 0
        fi
    fi

    # Publish the baseline for Stages 3 and 4.
    local f
    for f in stdout exit exit.nonterminating exit.infra; do
        [[ -f "$obs/$f" ]] && cp "$obs/$f" "$BUILD_DIR/stage1_${name}.$f"
    done

    if [[ -f "$obs/exit.nonterminating" ]]; then
        if is_declared_nonterminating "$name"; then
            success "$name (ran until killed, as expected)"
        else
            warn "$name: ran until killed (exit=$exit_code) but is not in NONTERMINATING_EXAMPLES; declare it so it gets the short budget"
            success "$name (exit=$exit_code)"
        fi
    else
        success "$name (exit=$exit_code)"
    fi
    _verdict "$out" pass
}

# Stage 1 cache keys, by example key.  Filled once per Stage 1 run.
declare -gA BASELINE_KEYS=()

compute_baseline_keys() {
    BASELINE_KEYS=()
    local -a pairs=()
    local d
    for d in "$@"; do
        pairs+=("$(example_key "$d")=$d")
    done
    local name key
    while IFS=$'\t' read -r name key; do
        [[ -n "$name" ]] && BASELINE_KEYS[$name]="$key"
    done < <(python3 "$SCRIPT_DIR/regression_baseline_keys.py" \
                "$ROOT_DIR" "$BUILD_DIR" "$SCRIPT_DIR/regression.sh" \
                "run=$RUN_BUDGET nonterm=$NONTERM_BUDGET declared=${NONTERMINATING_EXAMPLES[*]}" \
                -- "${pairs[@]}")
}

# Args: $1=index, $2=example_dir, $3=result prefix
stage1_worker() {
    local idx="$1" example_dir="$2" out="$3"
    local name
    name=$(example_key "$example_dir")
    local RUN_SANDBOX RUN_PORT RUN_TIMEOUT
    example_run_settings "$example_dir" "$name" "$idx"

    local obs="$BUILD_DIR/stage1_obs/$name"
    local key="${BASELINE_KEYS[$name]:-}"
    local entry=""
    [[ $USE_BASELINE_CACHE -eq 1 && -n "$key" ]] && entry="$BASELINE_CACHE_DIR/stage1/$key"

    if [[ -n "$entry" && -f "$entry/complete" ]]; then
        rm -rf "$obs"
        mkdir -p "$(dirname "$obs")"
        cp -r "$entry" "$obs"
        touch "$entry/complete"  # last used, for pruning
        : > "$out.hit"
    else
        stage1_observe "$example_dir" "$name" "$obs"
        if [[ -n "$entry" ]] && stage1_cacheable "$obs"; then
            # Atomic publish: a reader sees a complete entry or none.
            local tmp="$BASELINE_CACHE_DIR/stage1/.tmp.$key.$$.$BASHPID"
            mkdir -p "$BASELINE_CACHE_DIR/stage1"
            rm -rf "$tmp"
            cp -r "$obs" "$tmp" && : > "$tmp/complete" \
                && mv -T "$tmp" "$entry" 2>/dev/null
            rm -rf "$tmp"
        fi
    fi
    stage1_judge "$example_dir" "$name" "$obs" "$out"
}

run_stage1() {
    log "STAGE 1: Compile examples with ritz0 & run"
    echo "----------------------------------------"

    local passed=0
    local failed=0
    local skipped=0
    local -a nocompile=()

    TEST_SCRIPTS_RAN_FILE="$BUILD_DIR/test_scripts_ran.txt"
    : > "$TEST_SCRIPTS_RAN_FILE"

    local -a examples
    mapfile -t examples < <(get_examples)

    if [[ $USE_BASELINE_CACHE -eq 1 ]]; then
        compute_baseline_keys "${examples[@]}"
    else
        BASELINE_KEYS=()
    fi

    local rdir="$BUILD_DIR/results/stage1"
    run_pool "$rdir" stage1_worker "${examples[@]}"
    collect_pool "$rdir"

    local f
    for f in "$rdir"/*.nocompile; do
        [[ -e "$f" ]] || continue
        nocompile+=("$(example_key "${examples[$((10#$(basename "$f" .nocompile)))]}")")
    done

    # The declared list must describe the corpus.
    local k
    for k in "${NONTERMINATING_EXAMPLES[@]}"; do
        local found=0 d
        for d in "${examples[@]}"; do
            [[ "$(example_key "$d")" == "$k" ]] && found=1 && break
        done
        if [[ $found -eq 0 ]]; then
            fail "$k: declared non-terminating but not in the corpus — remove it from NONTERMINATING_EXAMPLES"
            failed=$((failed + 1))
        fi
    done

    if [[ $USE_BASELINE_CACHE -eq 1 ]]; then
        local hits
        hits=$(find "$rdir" -name '*.hit' | wc -l)
        echo "Stage 1 baseline cache: $hits hit, $(( ${#examples[@]} - hits )) recomputed ($BASELINE_CACHE_DIR)"
        # Entries unused for two weeks belong to compilers long gone.
        find "$BASELINE_CACHE_DIR/stage1" -mindepth 1 -maxdepth 1 \
            \( -name '.tmp.*' -o ! -newermt '-14 days' \) -exec rm -rf {} + 2>/dev/null
    fi

    echo ""
    if ! assert_test_scripts_all_ran "${nocompile[@]}"; then
        failed=$((failed + 1))
    fi

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
    make_output=$(make -j"$(sh "$SCRIPT_DIR/ritz1-jobs.sh")" ritz1 2>&1)
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
# STAGES 3 and 4: the differential, one worker per example
# ============================================================================
#
# Same per-example steps for ritz1 (Stage 3) and ritz1_selfhosted (Stage 4):
# compile, record the raw accept/reject for Stage 5 (before any allowlist),
# run the example's test.sh, run it and compare with the Stage 1 baseline.

# Set by run_differential for its workers.
DIFF_COMPILER=""
DIFF_PREFIX=""
DIFF_LABEL=""

# Args: $1=index, $2=example_dir, $3=result prefix
differential_worker() {
    local idx="$1" example_dir="$2" out="$3"
    local name
    name=$(example_key "$example_dir")
    local bin="$BUILD_DIR/${DIFF_PREFIX}_$name"
    local RUN_SANDBOX RUN_PORT RUN_TIMEOUT
    example_run_settings "$example_dir" "$name" "$idx"

    # Check if we have Stage 1 results to compare against
    if [[ ! -f "$BUILD_DIR/stage1_${name}.exit" ]]; then
        warn "$name: no Stage 1 baseline"
        _verdict "$out" skip
        return 0
    fi

    if ! compile_with "$DIFF_COMPILER" "$example_dir" "$bin" 2>/dev/null; then
        record_compile_outcome "$DIFF_COMPILER" "$name" rejected
        if is_known_failure "$DIFF_COMPILER" "$name"; then
            warn "$name: $DIFF_LABEL compile failed (known, allowlisted)"
            _verdict "$out" skip
        else
            fail "$name: $DIFF_LABEL compile failed"
            _verdict "$out" fail
        fi
        return 0
    fi
    record_compile_outcome "$DIFF_COMPILER" "$name" accepted
    if is_known_failure "$DIFF_COMPILER" "$name"; then
        report_xpass "$DIFF_COMPILER" "$name"
        _verdict "$out" fail
        return 0
    fi

    # Correctness gate, then the differential.  Same shape as Stage 1: a
    # ritz1-built binary must satisfy the example's own assertions AND
    # agree byte-for-byte with the ritz0 baseline.
    if ! check_test_script "$example_dir" "$name" "$bin"; then
        _verdict "$out" fail
        return 0
    fi

    if ! run_binary "$bin" "$BUILD_DIR/${DIFF_PREFIX}_${name}.stdout" "$BUILD_DIR/${DIFF_PREFIX}_${name}.exit"; then
        fail "$name: $DIFF_LABEL build reported success but produced no runnable binary"
        _verdict "$out" fail
        return 0
    fi

    if compare_runs "$name" \
        "$BUILD_DIR/stage1_${name}.stdout" "$BUILD_DIR/stage1_${name}.exit" \
        "$BUILD_DIR/${DIFF_PREFIX}_${name}.stdout" "$BUILD_DIR/${DIFF_PREFIX}_${name}.exit"; then
        _verdict "$out" pass
    else
        _verdict "$out" fail
    fi
}

# Run the differential over the corpus, tallying into the caller's
# passed/failed/skipped.  Args: $1=compiler, $2=file prefix, $3=label
run_differential() {
    DIFF_COMPILER="$1" DIFF_PREFIX="$2" DIFF_LABEL="$3"
    local -a examples
    mapfile -t examples < <(get_examples)
    local rdir="$BUILD_DIR/results/$2"
    run_pool "$rdir" differential_worker "${examples[@]}"
    collect_pool "$rdir"
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

    run_differential ritz1 stage3 "ritz1"
    mark_stage_ran ritz1

    echo ""
    echo "Stage 3: $passed passed, $failed failed, $skipped skipped"
    STAGE_RESULTS+=("Stage 3: $passed passed, $failed failed, $skipped skipped")
    TOTAL_PASSED=$((TOTAL_PASSED + passed))
    TOTAL_FAILED=$((TOTAL_FAILED + failed))
    TOTAL_SKIPPED=$((TOTAL_SKIPPED + skipped))

    return 0
}

# --- Per-stage timing (AGAST #1802) -----------------------------------------
# Nobody could say where the gate's time went: every baseline in the
# fast-iteration review had to be reconstructed from log timestamps.  Each
# stage the suite runs goes through run_timed, and the Summary prints the list.
STAGE_TIMES=()

# Args: $1=label, rest=command.  Returns the command's exit code.
run_timed() {
    local label="$1"; shift
    local t0=$SECONDS
    "$@"
    local rc=$?
    STAGE_TIMES+=("$label: $((SECONDS - t0))s")
    return $rc
}

print_stage_times() {
    [[ ${#STAGE_TIMES[@]} -eq 0 ]] && return 0
    echo "Stage timings:"
    local t
    for t in "${STAGE_TIMES[@]}"; do
        echo "  $t"
    done
}

# ============================================================================
# STAGE 4: Self-hosted ritz1 compiles examples, compare with Stage 1
# ============================================================================
run_stage4() {
    log "STAGE 4: Self-hosted ritz1 (bootstrap) & compare"
    echo "----------------------------------------"

    local ritz1_dir="$ROOT_DIR/ritz1"
    local ritz1_selfhosted="$ROOT_DIR/ritz1/build/ritz1_selfhosted"

    # Make ritz1_selfhosted current, reusing the one matrix-full (or
    # `make ritz1-bootstrap`) already built -- AGAST #1802.
    #
    # This used to be `make -s bootstrap BUILD_DIR="$BUILD_DIR" 2>/dev/null`.
    # A command-line BUILD_DIR overrides ritz1/Makefile's for every object and
    # .d file (only build/ritz1 and build/ritz1_selfhosted are hard-coded), so
    # Stage 4 recompiled all of ritz1 into an empty .regression/, relinked
    # build/ritz1 mid-run and rebuilt ritz1_selfhosted from scratch: 55 s on
    # CI, 3-4 min locally, with the build's stderr thrown away.  Now make
    # decides: the -q probe answers "current" and nothing is built; otherwise
    # it is an ordinary incremental build in ritz1/build, -j capped by
    # RITZ1_JOBS, with its output in the log.
    if make -C "$ritz1_dir" -q build/ritz1_selfhosted 2>/dev/null; then
        success "ritz1_selfhosted is current; reusing it"
    elif make -C "$ritz1_dir" -s -j"$(sh "$SCRIPT_DIR/ritz1-jobs.sh")" bootstrap; then
        success "ritz1 self-hosted bootstrap complete"
    else
        fail "ritz1 bootstrap failed (make output above)"
        STAGE_RESULTS+=("Stage 4: FAILED - bootstrap error")
        TOTAL_FAILED=$((TOTAL_FAILED + 1))
        return 2
    fi

    if [[ ! -x "$ritz1_selfhosted" ]]; then
        warn "Self-hosted ritz1 not available"
        STAGE_RESULTS+=("Stage 4: SKIPPED - self-hosted binary not available")
        return 0
    fi

    local passed=0
    local failed=0
    local skipped=0

    run_differential ritz1_selfhosted stage4 "self-hosted ritz1"
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
# Known blind spot, worth stating because it has already cost us once:
# this check compares ACCEPT sets, so it can only see divergence among
# examples at least one compiler handles.  Wherever BOTH compilers reject
# the same program, the name is absent from both sets, the sets match, and
# Stage 5 goes green — agreement-by-shared-breakage, not a fixed point.
# That is exactly how AGAST #1325 (a monomorphization divergence) hid behind
# #1309's phi bug: the phi bug made both compilers reject 49_ritzgen, so the
# sets agreed.  Fixing the phi bug made ritz1 accept it, ritz1_selfhosted
# still rejected it, and only then did Stage 5 correctly go red.
#
# It is the same failure shape as the S3/S4 allowlist hole one level up: a
# gate that passes because two things are equally broken.  A green Stage 5
# means "the two compilers agree on what they accept", never "the compiler
# is correct".  Shrinking the known-failures lists is what narrows the blind
# spot; nothing inside this function can.
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

# Run selected stages.  Every stage goes through run_timed so the Summary can
# say where the time went (scripts/test-regression-stage4.sh checks this).
if [[ -n "$RUN_STAGE" ]]; then
    case $RUN_STAGE in
        1) run_timed "Stage 1" run_stage1 ;;
        2) run_timed "Stage 2" run_stage2 ;;
        3) run_timed "Stage 1" run_stage1; run_timed "Stage 2" run_stage2
           run_timed "Stage 3" run_stage3 ;;
        4) run_timed "Stage 1" run_stage1; run_timed "Stage 2" run_stage2
           run_timed "Stage 4" run_stage4 ;;
        # Stage 5 compares stages 3 and 4, so selecting it runs both.  It
        # cannot be run standalone: there is nothing to compare.
        5) run_timed "Stage 1" run_stage1; run_timed "Stage 2" run_stage2
           run_timed "Stage 3" run_stage3; run_timed "Stage 4" run_stage4
           echo ""; run_timed "Stage 5" run_stage5 ;;
        *)
            echo "Invalid stage: $RUN_STAGE (must be 1-5)"
            exit 1
            ;;
    esac
else
    # Run all stages
    run_timed "Stage 1" run_stage1
    echo ""
    run_timed "Stage 2" run_stage2
    echo ""
    run_timed "Stage 3" run_stage3
    echo ""

    if [[ $QUICK_MODE -eq 0 ]]; then
        run_timed "Stage 4" run_stage4
        echo ""
        run_timed "Stage 5" run_stage5
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
print_stage_times
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
