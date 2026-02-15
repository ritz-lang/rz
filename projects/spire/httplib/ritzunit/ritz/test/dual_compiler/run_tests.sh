#!/bin/bash
# Dual-compiler test runner for ritz0 and ritz1
#
# Runs the same tests through both compilers and compares outputs.
# Each test is a .ritz file with a corresponding .expected file.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LANG_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Compiler paths
RITZ0="python3 $LANG_ROOT/ritz0/ritz0.py"
RITZ1="$LANG_ROOT/ritz1/build/ritz1"

# Runtime components for ritz1
RITZ1_CRT0="$LANG_ROOT/ritz1/runtime/ritz_crt0.o"

# Build directory - use within project to avoid /tmp noexec issues
BUILD_DIR="$SCRIPT_DIR/.build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Stats
declare -i ritz0_pass=0 ritz0_fail=0
declare -i ritz1_pass=0 ritz1_fail=0
declare -i skipped=0

# Options
VERBOSE=0
RITZ0_ONLY=0
RITZ1_ONLY=0
LEVEL_FILTER=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose) VERBOSE=1; shift ;;
        --ritz0-only) RITZ0_ONLY=1; shift ;;
        --ritz1-only) RITZ1_ONLY=1; shift ;;
        [0-9]*) LEVEL_FILTER="$1"; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Check if ritz1 is built
RITZ1_AVAILABLE=1
if [ ! -f "$RITZ1" ]; then
    echo -e "${YELLOW}Warning: ritz1 not built at $RITZ1${NC}"
    RITZ1_AVAILABLE=0
fi

# Compile and run a test with ritz0
run_ritz0() {
    local src="$1"
    local name="$2"
    local expected_file="$3"

    local ll_file="$BUILD_DIR/${name}_ritz0.ll"
    local obj_file="$BUILD_DIR/${name}_ritz0.o"
    local bin_file="$BUILD_DIR/${name}_ritz0"

    # Compile to LLVM IR
    if ! $RITZ0 "$src" -o "$ll_file" 2>"$BUILD_DIR/${name}_ritz0.err"; then
        if [ $VERBOSE -eq 1 ]; then
            echo -e "  ${RED}ritz0 compile error:${NC}"
            cat "$BUILD_DIR/${name}_ritz0.err"
        fi
        return 1
    fi

    # Compile to object file
    if ! llc -O2 "$ll_file" -filetype=obj -o "$obj_file" 2>/dev/null; then
        if [ $VERBOSE -eq 1 ]; then
            echo -e "  ${RED}llc error for ritz0 output${NC}"
        fi
        return 1
    fi

    # Link - ritz0 includes its own _start, so use -nostartfiles
    if ! gcc -nostartfiles -no-pie "$obj_file" -o "$bin_file" 2>/dev/null; then
        if [ $VERBOSE -eq 1 ]; then
            echo -e "  ${RED}link error for ritz0${NC}"
        fi
        return 1
    fi

    # Run and capture output + exit code
    local output exit_code
    set +e
    output=$("$bin_file" 2>&1)
    exit_code=$?
    set -e

    # Compare with expected
    compare_output "$output" "$exit_code" "$expected_file"
}

# Compile and run a test with ritz1
run_ritz1() {
    local src="$1"
    local name="$2"
    local expected_file="$3"

    local ll_file="$BUILD_DIR/${name}_ritz1.ll"
    local asm_file="$BUILD_DIR/${name}_ritz1.s"
    local obj_file="$BUILD_DIR/${name}_ritz1.o"
    local bin_file="$BUILD_DIR/${name}_ritz1"

    # Compile to LLVM IR
    if ! timeout 10s $RITZ1 "$src" -o "$ll_file" -I "$LANG_ROOT" 2>"$BUILD_DIR/${name}_ritz1.err"; then
        if [ $VERBOSE -eq 1 ]; then
            echo -e "  ${RED}ritz1 compile error:${NC}"
            cat "$BUILD_DIR/${name}_ritz1.err"
        fi
        return 1
    fi

    # Compile to assembly then object
    if ! llc -O2 "$ll_file" -o "$asm_file" 2>/dev/null; then
        if [ $VERBOSE -eq 1 ]; then
            echo -e "  ${RED}llc error for ritz1 output${NC}"
        fi
        return 1
    fi

    if ! clang -c "$asm_file" -o "$obj_file" 2>/dev/null; then
        if [ $VERBOSE -eq 1 ]; then
            echo -e "  ${RED}clang error for ritz1${NC}"
        fi
        return 1
    fi

    # Link with crt0
    if ! ld -dynamic-linker /lib64/ld-linux-x86-64.so.2 -lc \
        -o "$bin_file" "$RITZ1_CRT0" "$obj_file" 2>/dev/null; then
        if [ $VERBOSE -eq 1 ]; then
            echo -e "  ${RED}link error for ritz1${NC}"
        fi
        return 1
    fi

    # Run and capture output + exit code
    local output exit_code
    set +e
    output=$("$bin_file" 2>&1)
    exit_code=$?
    set -e

    # Compare with expected
    compare_output "$output" "$exit_code" "$expected_file"
}

# Compare actual output with expected
compare_output() {
    local output="$1"
    local exit_code="$2"
    local expected_file="$3"

    # Read expected file
    local expected_output=""
    local expected_exit=0

    while IFS= read -r line || [ -n "$line" ]; do
        if [[ "$line" =~ ^EXIT:([0-9]+)$ ]]; then
            expected_exit="${BASH_REMATCH[1]}"
        elif [ -n "$line" ]; then
            if [ -n "$expected_output" ]; then
                expected_output="${expected_output}"$'\n'"${line}"
            else
                expected_output="$line"
            fi
        fi
    done < "$expected_file"

    # Compare exit code
    if [ "$exit_code" -ne "$expected_exit" ]; then
        if [ $VERBOSE -eq 1 ]; then
            echo -e "  ${RED}exit code mismatch: got $exit_code, expected $expected_exit${NC}"
        fi
        return 1
    fi

    # Compare output (if expected)
    if [ -n "$expected_output" ] && [ "$output" != "$expected_output" ]; then
        if [ $VERBOSE -eq 1 ]; then
            echo -e "  ${RED}output mismatch:${NC}"
            echo "  Expected: $expected_output"
            echo "  Got: $output"
        fi
        return 1
    fi

    return 0
}

# Run a single test
run_test() {
    local src="$1"
    local name=$(basename "$src" .ritz)
    local dir=$(dirname "$src")
    local expected="${dir}/${name}.expected"

    if [ ! -f "$expected" ]; then
        echo -e "  ${YELLOW}SKIP${NC} (no .expected file)"
        skipped=$((skipped + 1))
        return
    fi

    printf "%-40s" "$name"

    local r0_result="SKIP" r1_result="SKIP"

    # Run ritz0
    if [ $RITZ1_ONLY -eq 0 ]; then
        if run_ritz0 "$src" "$name" "$expected"; then
            r0_result="PASS"
            ritz0_pass=$((ritz0_pass + 1))
        else
            r0_result="FAIL"
            ritz0_fail=$((ritz0_fail + 1))
        fi
    fi

    # Run ritz1
    if [ $RITZ0_ONLY -eq 0 ] && [ $RITZ1_AVAILABLE -eq 1 ]; then
        if run_ritz1 "$src" "$name" "$expected"; then
            r1_result="PASS"
            ritz1_pass=$((ritz1_pass + 1))
        else
            r1_result="FAIL"
            ritz1_fail=$((ritz1_fail + 1))
        fi
    fi

    # Print results
    if [ "$r0_result" = "PASS" ]; then
        printf "${GREEN}ritz0:PASS${NC} "
    elif [ "$r0_result" = "FAIL" ]; then
        printf "${RED}ritz0:FAIL${NC} "
    else
        printf "${YELLOW}ritz0:SKIP${NC} "
    fi

    if [ "$r1_result" = "PASS" ]; then
        printf "${GREEN}ritz1:PASS${NC}"
    elif [ "$r1_result" = "FAIL" ]; then
        printf "${RED}ritz1:FAIL${NC}"
    else
        printf "${YELLOW}ritz1:SKIP${NC}"
    fi

    echo ""
}

# Main
echo "=== Dual-Compiler Test Suite ==="
echo "LANG_ROOT: $LANG_ROOT"
echo "BUILD_DIR: $BUILD_DIR"
echo ""

# Find and run tests
for level_dir in "$SCRIPT_DIR"/level*; do
    if [ ! -d "$level_dir" ]; then
        continue
    fi

    level_name=$(basename "$level_dir")
    level_num="${level_name#level}"

    # Apply level filter
    if [ -n "$LEVEL_FILTER" ] && [ "$level_num" != "$LEVEL_FILTER" ]; then
        continue
    fi

    echo -e "${BLUE}=== $level_name ===${NC}"

    for test_file in "$level_dir"/*.ritz; do
        if [ -f "$test_file" ]; then
            run_test "$test_file"
        fi
    done
    echo ""
done

# Summary
echo "=== Summary ==="
if [ $RITZ1_ONLY -eq 0 ]; then
    echo -e "ritz0: ${GREEN}$ritz0_pass passed${NC}, ${RED}$ritz0_fail failed${NC}"
fi
if [ $RITZ0_ONLY -eq 0 ]; then
    echo -e "ritz1: ${GREEN}$ritz1_pass passed${NC}, ${RED}$ritz1_fail failed${NC}"
fi
if [ $skipped -gt 0 ]; then
    echo -e "Skipped: $skipped"
fi

# Cleanup
rm -rf "$BUILD_DIR"

# Exit with failure if any tests failed
if [ $ritz0_fail -gt 0 ] || [ $ritz1_fail -gt 0 ]; then
    exit 1
fi
exit 0
