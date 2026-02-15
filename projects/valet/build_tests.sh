#!/bin/bash
# build_tests.sh - Build and run valet unit tests with ritzunit
#
# This uses the ritzunit framework for test discovery and reporting.
# Tests are compiled together with the runner, reporter, and types modules.
#
# Usage:
#   ./build_tests.sh              # Build and run all tests
#   ./build_tests.sh --list       # List available tests
#   ./build_tests.sh --filter foo # Run tests matching 'foo'
#   ./build_tests.sh --no-fork    # Run without fork isolation (for debugging)
#   ./build_tests.sh --verbose    # Show detailed output

set -e

cd "$(dirname "$0")"

# Set RITZ_PATH to include submodules for compression and crypto support
# The current directory (.) provides ritzlib symlink -> ritz/ritzlib
# The squeeze directory provides lib/* imports from squeeze
# The cryptosec directory provides cryptographic primitives
export RITZ_PATH=.:squeeze:cryptosec

RITZ0="python3 ritz/ritz0/ritz0.py"
LIST_DEPS="python3 ritz/ritz0/list_deps.py"

# Create build directory
mkdir -p build

echo "=== Building Valet Unit Tests with ritzunit ==="
echo

# Track compiled files to avoid duplicates
declare -A COMPILED
OBJ_FILES=""

compile_if_needed() {
    local SRC="$1"
    local WITH_RUNTIME="${2:-no}"
    local BASENAME=$(basename "$SRC" .ritz)
    local LLFILE="build/${BASENAME}.ll"
    local OBJFILE="build/${BASENAME}.o"

    if [ -z "${COMPILED[$BASENAME]}" ]; then
        echo "  Compiling $SRC"
        if [ "$WITH_RUNTIME" = "yes" ]; then
            $RITZ0 "$SRC" -o "$LLFILE"
        else
            $RITZ0 "$SRC" -o "$LLFILE" --no-runtime
        fi
        clang -c "$LLFILE" -o "$OBJFILE" -Wno-override-module -march=native
        COMPILED[$BASENAME]=1
        OBJ_FILES="$OBJ_FILES $OBJFILE"
    fi
}

# Step 1: Compile ritzunit framework (runner and its dependencies)
echo "Compiling ritzunit framework..."
RUNNER_DEPS=$($LIST_DEPS ritzunit/runner.ritz)
for SRC in $RUNNER_DEPS; do
    # runner.ritz contains main(), so it needs runtime (includes _start)
    if [[ "$SRC" == *"runner.ritz" ]]; then
        compile_if_needed "$SRC" "yes"
    else
        compile_if_needed "$SRC"
    fi
done

# Step 2: Compile test files
echo
echo "Compiling test files..."
for TEST_FILE in tests/test_*.ritz; do
    if [ -f "$TEST_FILE" ]; then
        # Get dependencies for this test file
        TEST_DEPS=$($LIST_DEPS "$TEST_FILE" 2>/dev/null || echo "$TEST_FILE")
        for SRC in $TEST_DEPS; do
            compile_if_needed "$SRC"
        done
    fi
done

# Step 3: Link everything
echo
echo "Linking..."
clang $OBJ_FILES -o build/valet_tests -nostdlib -no-pie

echo
echo "=== Running Tests ==="
echo
./build/valet_tests "$@"
