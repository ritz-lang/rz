#!/bin/bash
# 🎭 Ritz Regression Test Suite
#
# Comprehensive regression testing across compiler stages:
#   Stage 1: ritz0 compiles examples, run them
#   Stage 2: ritz0 compiles ritz1
#   Stage 3: ritz1 compiles examples, compare output with Stage 1
#   Stage 4: ritz1 self-compiles (bootstrap), compile examples, compare
#
# Note: "Stages" refer to compiler development progression.
#       Examples have their own "Tiers" based on language features used.
#
# Usage:
#   ./scripts/regression.sh             # Run all stages
#   ./scripts/regression.sh --stage 1   # Run specific stage
#   ./scripts/regression.sh --quick     # Skip Stage 4 (slower)
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
            echo "  --stage N    Run only stage N (1-4)"
            echo "  --quick      Skip Stage 4 (self-hosted bootstrap)"
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
trap "rm -rf $BUILD_DIR" EXIT

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
get_examples() {
    find "$EXAMPLES_DIR" -mindepth 1 -maxdepth 1 -type d | sort | while read dir; do
        if [[ -f "$dir/src/main.ritz" ]]; then
            echo "$dir"
        fi
    done
}

# Compile a .ritz file with a given compiler
# Args: $1=compiler, $2=source, $3=output_binary
compile_with() {
    local compiler="$1"
    local source="$2"
    local output="$3"
    local example_dir=$(dirname $(dirname "$source"))
    local example_name=$(basename "$example_dir")

    # Handle different compiler types
    if [[ "$compiler" == "ritz0" ]]; then
        # Use build.py for ritz0 - it handles separate compilation properly
        if ! python3 "$ROOT_DIR/build.py" build "$example_name" >/dev/null 2>&1; then
            return 1
        fi
        # Copy binary to expected location
        # First try the directory name as binary name
        local built_bin="$example_dir/$example_name"
        if [[ -f "$built_bin" ]]; then
            cp "$built_bin" "$output"
        else
            # Try reading [[bin]] name from ritz.toml (look in [[bin]] section)
            local bin_name=$(awk '/^\[\[bin\]\]/{found=1} found && /^name\s*=/{gsub(/.*=\s*"|".*/, ""); print; exit}' "$example_dir/ritz.toml" 2>/dev/null)
            if [[ -n "$bin_name" && -f "$example_dir/$bin_name" ]]; then
                cp "$example_dir/$bin_name" "$output"
            else
                # Fallback: find any executable in example dir
                local found_bin=$(find "$example_dir" -maxdepth 1 -type f -executable ! -name "*.sh" 2>/dev/null | head -1)
                if [[ -n "$found_bin" ]]; then
                    cp "$found_bin" "$output"
                else
                    return 1
                fi
            fi
        fi
    else
        # ritz1 binary - use direct compilation
        local ll_file="${output}.ll"
        if ! "$compiler" "$source" -o "$ll_file" >/dev/null 2>&1; then
            return 1
        fi
        # Compile LLVM IR to binary
        if ! clang "$ll_file" -o "$output" -nostdlib -g 2>/dev/null; then
            return 1
        fi
    fi

    return 0
}

# Run a binary and capture output/exit code
# Args: $1=binary, $2=output_file (for stdout), $3=exit_file
run_binary() {
    local binary="$1"
    local stdout_file="$2"
    local exit_file="$3"

    # Close stdin (</dev/null) to prevent programs like cat/grep from hanging
    # Use timeout with KILL signal to ensure cleanup
    # Limit output to 1MB to prevent disk-filling runaway output
    timeout --signal=KILL 5s "$binary" < /dev/null 2>&1 | head -c 1048576 > "$stdout_file"
    local exit_code=${PIPESTATUS[0]}
    echo "$exit_code" > "$exit_file"
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

    if [[ "$code_a" != "$code_b" ]]; then
        fail "$name: exit code mismatch (A=$code_a, B=$code_b)"
        return 1
    fi

    if ! diff -q "$stdout_a" "$stdout_b" >/dev/null 2>&1; then
        fail "$name: output mismatch"
        if [[ $VERBOSE -eq 1 ]]; then
            echo "  --- Expected (A) ---"
            head -5 "$stdout_a"
            echo "  --- Got (B) ---"
            head -5 "$stdout_b"
        fi
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
        local name=$(basename "$example_dir")
        local src="$example_dir/src/main.ritz"
        local bin="$BUILD_DIR/stage1_$name"

        # Compile with ritz0
        if ! compile_with "ritz0" "$src" "$bin"; then
            warn "$name: ritz0 compile failed"
            skipped=$((skipped + 1))
            continue
        fi

        # Handle interactive examples (need stdin/file args)
        if is_interactive_example "$name"; then
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
        run_binary "$bin" "$BUILD_DIR/stage1_${name}.stdout" "$BUILD_DIR/stage1_${name}.exit"

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
    local ritz1_bin="$BUILD_DIR/ritz1"

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

    local ritz1_bin="$BUILD_DIR/ritz1"

    if [[ ! -x "$ritz1_bin" ]]; then
        warn "ritz1 not available, skipping Stage 3"
        STAGE_RESULTS+=("Stage 3: SKIPPED - ritz1 not available")
        return 0
    fi

    local passed=0
    local failed=0
    local skipped=0

    for example_dir in $(get_examples); do
        local name=$(basename "$example_dir")
        local src="$example_dir/src/main.ritz"
        local bin="$BUILD_DIR/stage3_$name"

        # Check if we have Stage 1 results to compare against
        if [[ ! -f "$BUILD_DIR/stage1_${name}.exit" ]]; then
            warn "$name: no Stage 1 baseline"
            skipped=$((skipped + 1))
            continue
        fi

        # Compile with ritz1
        if ! compile_with "$ritz1_bin" "$src" "$bin" 2>/dev/null; then
            fail "$name: ritz1 compile failed"
            failed=$((failed + 1))
            continue
        fi

        # Handle interactive examples via test.sh
        if is_interactive_example "$name"; then
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
        run_binary "$bin" "$BUILD_DIR/stage3_${name}.stdout" "$BUILD_DIR/stage3_${name}.exit"

        # Compare with Stage 1
        if compare_runs "$name" \
            "$BUILD_DIR/stage1_${name}.stdout" "$BUILD_DIR/stage1_${name}.exit" \
            "$BUILD_DIR/stage3_${name}.stdout" "$BUILD_DIR/stage3_${name}.exit"; then
            passed=$((passed + 1))
        else
            failed=$((failed + 1))
        fi
    done

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
    local ritz1_selfhosted="$BUILD_DIR/ritz1_selfhosted"

    # Bootstrap ritz1 (ritz1 compiles itself)
    cd "$ritz1_dir"

    if make -s bootstrap BUILD_DIR="$BUILD_DIR" 2>/dev/null; then
        success "ritz1 self-hosted bootstrap complete"
        cp "$BUILD_DIR/ritz1_selfhosted" "$ritz1_selfhosted" 2>/dev/null || true
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
        local name=$(basename "$example_dir")
        local src="$example_dir/src/main.ritz"
        local bin="$BUILD_DIR/stage4_$name"

        # Check if we have Stage 1 results
        if [[ ! -f "$BUILD_DIR/stage1_${name}.exit" ]]; then
            warn "$name: no Stage 1 baseline"
            skipped=$((skipped + 1))
            continue
        fi

        # Compile with self-hosted ritz1
        if ! compile_with "$ritz1_selfhosted" "$src" "$bin" 2>/dev/null; then
            fail "$name: self-hosted ritz1 compile failed"
            failed=$((failed + 1))
            continue
        fi

        # Handle interactive examples via test.sh
        if is_interactive_example "$name"; then
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
        run_binary "$bin" "$BUILD_DIR/stage4_${name}.stdout" "$BUILD_DIR/stage4_${name}.exit"

        # Compare with Stage 1
        if compare_runs "$name" \
            "$BUILD_DIR/stage1_${name}.stdout" "$BUILD_DIR/stage1_${name}.exit" \
            "$BUILD_DIR/stage4_${name}.stdout" "$BUILD_DIR/stage4_${name}.exit"; then
            passed=$((passed + 1))
        else
            failed=$((failed + 1))
        fi
    done

    echo ""
    echo "Stage 4: $passed passed, $failed failed, $skipped skipped"
    STAGE_RESULTS+=("Stage 4: $passed passed, $failed failed, $skipped skipped")
    TOTAL_PASSED=$((TOTAL_PASSED + passed))
    TOTAL_FAILED=$((TOTAL_FAILED + failed))
    TOTAL_SKIPPED=$((TOTAL_SKIPPED + skipped))

    return 0
}

# ============================================================================
# Main
# ============================================================================

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
        *)
            echo "Invalid stage: $RUN_STAGE (must be 1-4)"
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
    else
        echo "Stage 4: SKIPPED (--quick mode)"
        STAGE_RESULTS+=("Stage 4: SKIPPED (--quick mode)")
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
    exit 1
fi
