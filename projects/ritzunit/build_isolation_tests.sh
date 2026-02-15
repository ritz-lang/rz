#!/bin/bash
# build_isolation_tests.sh - Build tests to verify fork isolation
#
# These tests demonstrate crash handling, timeout, and assertion failure detection.

set -e

RITZ0="python3 ritz/ritz0/ritz0.py"
LIST_DEPS="python3 ritz/ritz0/list_deps.py"
RUNTIME="ritz/runtime/ritz_start.x86_64.o"

# Create build directory
rm -rf build
mkdir -p build

echo "=== Building Isolation Tests ==="
echo

# Step 1: Get all dependencies for the runner
echo "Collecting runner dependencies..."
RUNNER_DEPS=$($LIST_DEPS src/runner.ritz)

# All .ll files we'll link
declare -A COMPILED
LL_FILES=""

# Step 2: Compile runner and its dependencies
for SRC in $RUNNER_DEPS; do
    BASENAME=$(basename "$SRC" .ritz)
    OUTFILE="build/${BASENAME}.ll"
    if [ -z "${COMPILED[$BASENAME]}" ]; then
        echo "Compiling $SRC"
        $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime
        COMPILED[$BASENAME]=1
        LL_FILES="$LL_FILES $OUTFILE"
    fi
done

# Step 3: Compile isolation test file
echo "Compiling test/test_isolation.ritz"
$RITZ0 test/test_isolation.ritz -o build/test_isolation.ll --no-runtime
LL_FILES="$LL_FILES build/test_isolation.ll"

# Step 4: Link everything
echo
echo "Linking..."
clang $RUNTIME $LL_FILES -o build/isolation_tests -nostdlib -g

echo
echo "Build complete: build/isolation_tests"
echo
echo "Example usage:"
echo "  ./build/isolation_tests                    # Run all tests with fork isolation"
echo "  ./build/isolation_tests -t 100             # Use 100ms timeout (for timeout test)"
echo "  ./build/isolation_tests -f normal          # Only run normal tests"
echo "  ./build/isolation_tests -f crash           # Only run crash tests"
echo "  ./build/isolation_tests --no-fork -f normal  # Without isolation (safe tests only!)"
echo
