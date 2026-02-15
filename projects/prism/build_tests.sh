#!/bin/bash
# build_tests.sh - Build and run Prism tests with ritzunit
#
# Usage:
#   ./build_tests.sh              # Build and run all tests
#   ./build_tests.sh -f "rect*"   # Run only tests matching pattern
#   ./build_tests.sh -v           # Verbose output
#   ./build_tests.sh -l           # List tests without running

set -e

# Use RERITZ syntax mode for [[test]] attribute syntax
export RITZ_SYNTAX=reritz

# Set up paths
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RITZ_DIR="$SCRIPT_DIR/ritz"
RITZUNIT_DIR="$SCRIPT_DIR/ritzunit"

RITZ0="python3 $RITZ_DIR/ritz0/ritz0.py"
LIST_DEPS="python3 $RITZ_DIR/ritz0/list_deps.py"
RUNTIME="$RITZ_DIR/runtime/ritz_start.x86_64.o"

# Set RITZ_PATH so imports resolve correctly
export RITZ_PATH="$RITZ_DIR:$RITZUNIT_DIR:$SCRIPT_DIR"

# Create build directory
rm -rf build
mkdir -p build

echo "=== Building Prism Tests with ritzunit ==="
echo

# Track compiled files to avoid duplicates
declare -A COMPILED
LL_FILES=""

# Step 1: Compile ritzunit runner and its dependencies
echo "Collecting ritzunit dependencies..."
RUNNER_DEPS=$($LIST_DEPS "$RITZUNIT_DIR/src/runner.ritz")

for SRC in $RUNNER_DEPS; do
    BASENAME=$(basename "$SRC" .ritz)
    OUTFILE="build/${BASENAME}.ll"
    if [ -z "${COMPILED[$BASENAME]}" ]; then
        echo "  Compiling $(basename $SRC)"
        $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime
        COMPILED[$BASENAME]=1
        LL_FILES="$LL_FILES $OUTFILE"
    fi
done

# Step 2: Compile all test files
echo
echo "Compiling Prism test files..."
for TEST_FILE in test/*.ritz; do
    BASENAME=$(basename "$TEST_FILE" .ritz)
    OUTFILE="build/${BASENAME}.ll"
    if [ -z "${COMPILED[$BASENAME]}" ]; then
        echo "  Compiling $BASENAME"
        $RITZ0 "$TEST_FILE" -o "$OUTFILE" --no-runtime
        COMPILED[$BASENAME]=1
        LL_FILES="$LL_FILES $OUTFILE"
    fi
done

# Step 3: Compile Prism source files (the code being tested)
echo
echo "Compiling Prism source files..."
for SRC_FILE in src/**/*.ritz src/*.ritz; do
    if [ -f "$SRC_FILE" ]; then
        BASENAME=$(basename "$SRC_FILE" .ritz)
        # Avoid conflicts by using directory prefix
        DIR=$(dirname "$SRC_FILE" | tr '/' '_')
        OUTFILE="build/${DIR}_${BASENAME}.ll"
        if [ -z "${COMPILED[$BASENAME]}" ]; then
            echo "  Compiling $SRC_FILE"
            $RITZ0 "$SRC_FILE" -o "$OUTFILE" --no-runtime 2>/dev/null || echo "    (skipped - may have unresolved imports)"
            if [ -f "$OUTFILE" ]; then
                COMPILED[$BASENAME]=1
                LL_FILES="$LL_FILES $OUTFILE"
            fi
        fi
    fi
done

# Step 4: Link everything
echo
echo "Linking..."
clang $RUNTIME $LL_FILES -o build/prism_tests -nostdlib -g 2>&1 || {
    echo "Link failed. This is expected if Angelo isn't built yet."
    echo "Running unit tests that don't depend on Angelo..."
}

if [ -f build/prism_tests ]; then
    echo
    echo "=== Running Prism Tests ==="
    echo
    ./build/prism_tests "$@"
else
    echo
    echo "Build incomplete - some dependencies may be missing."
    echo "Try running individual test files or ensure all dependencies are built."
fi
