#!/bin/bash
# build_tests.sh - Build and run Tome unit tests with ritzunit
#
# Uses the ritzunit framework for test discovery and reporting.
#
# Usage:
#   ./build_tests.sh              # Build and run all tests
#   ./build_tests.sh --list       # List available tests
#   ./build_tests.sh --filter foo # Run tests matching 'foo'
#   ./build_tests.sh --verbose    # Show detailed output

set -e

cd "$(dirname "$0")"

# Use the flat ecosystem structure
RITZ_LANG_DIR="${RITZ_PATH:-/home/aaron/dev/ritz-lang}"

# Set RITZ_PATH to include our lib directory and ritzlib from the ecosystem
export RITZ_PATH=".:$RITZ_LANG_DIR/ritzunit:$RITZ_LANG_DIR/ritz"

RITZ0="python3 $RITZ_LANG_DIR/ritz/ritz0/ritz0.py"
LIST_DEPS="python3 $RITZ_LANG_DIR/ritz/ritz0/list_deps.py"
RUNTIME="$RITZ_LANG_DIR/ritz/runtime/ritz_start.x86_64.o"

# Create build directory
mkdir -p build

echo "=== Building Tome Unit Tests with ritzunit ==="
echo

# Track compiled files to avoid duplicates
declare -A COMPILED
LL_FILES=""

compile_if_needed() {
    local SRC="$1"
    local BASENAME=$(basename "$SRC" .ritz)
    local OUTFILE="build/${BASENAME}.ll"

    if [ -z "${COMPILED[$BASENAME]}" ]; then
        echo "  Compiling $SRC"
        $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime
        COMPILED[$BASENAME]=1
        LL_FILES="$LL_FILES $OUTFILE"
    fi
}

# Step 1: Compile ritzunit framework (runner and its dependencies)
echo "Compiling ritzunit framework..."
RUNNER_DEPS=$($LIST_DEPS ritzunit/src/runner.ritz)
for SRC in $RUNNER_DEPS; do
    compile_if_needed "$SRC"
done

# Step 2: Compile test files
echo
echo "Compiling test files..."
for TEST_FILE in test/test_*.ritz; do
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
clang $RUNTIME $LL_FILES -o build/tome_tests -nostdlib -g

echo
echo "=== Running Tests ==="
echo
./build/tome_tests "$@"
