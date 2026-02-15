#!/bin/bash
# run_tests.sh - Build and run squeeze tests with ritzunit
#
# Uses ritzunit for:
# - ELF-based test discovery (finds all @test functions automatically)
# - Fork isolation (catches crashes, timeouts)
# - Visual reporter with pass/fail status
#
# Usage:
#   ./run_tests.sh                    # Run all tests
#   ./run_tests.sh --filter crc32     # Run only crc32 tests
#   ./run_tests.sh --verbose          # Verbose output
#   ./run_tests.sh --list             # List available tests

set -e

SQUEEZE=$(dirname "$(readlink -f "$0")")
RITZ0="python3 $SQUEEZE/ritz/ritz0/ritz0.py"
LIST_DEPS="python3 $SQUEEZE/ritz/ritz0/list_deps.py"
RUNTIME="$SQUEEZE/ritz/runtime/ritz_start.x86_64.o"

# Build runtime if needed
if [ ! -f "$RUNTIME" ]; then
    echo "Building runtime..."
    make -C "$SQUEEZE/ritz/runtime" ritz_start.x86_64.o
fi

# Set RITZ_PATH - squeeze first (has ritzlib symlink), then ritzunit for its src/
# This ensures we use squeeze's ritzlib consistently
export RITZ_PATH="$SQUEEZE:$SQUEEZE/ritzunit:$SQUEEZE/ritz"

# Create build directory
rm -rf "$SQUEEZE/build"
mkdir -p "$SQUEEZE/build"

echo "=== Building Squeeze Tests with ritzunit ==="
echo

# Track compiled files to avoid duplicates
declare -A COMPILED
LL_FILES=""

# Step 1: Compile ritzunit runner and dependencies
echo "Collecting ritzunit runner dependencies..."
RUNNER_DEPS=$($LIST_DEPS "$SQUEEZE/ritzunit/src/runner.ritz")

for SRC in $RUNNER_DEPS; do
    BASENAME=$(basename "$SRC" .ritz)
    OUTFILE="$SQUEEZE/build/${BASENAME}.ll"
    if [ -z "${COMPILED[$BASENAME]}" ]; then
        echo "  Compiling $BASENAME"
        $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime
        COMPILED[$BASENAME]=1
        LL_FILES="$LL_FILES $OUTFILE"
    fi
done

# Step 2: Compile squeeze library modules
echo
echo "Compiling squeeze library..."
for SRC in "$SQUEEZE"/lib/*.ritz; do
    BASENAME=$(basename "$SRC" .ritz)
    OUTFILE="$SQUEEZE/build/${BASENAME}.ll"
    if [ -z "${COMPILED[$BASENAME]}" ]; then
        echo "  Compiling $BASENAME"
        $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime
        COMPILED[$BASENAME]=1
        LL_FILES="$LL_FILES $OUTFILE"
    fi
done

# Step 3: Compile test files
echo
echo "Compiling tests..."
for SRC in "$SQUEEZE"/test/*.ritz; do
    BASENAME=$(basename "$SRC" .ritz)
    OUTFILE="$SQUEEZE/build/${BASENAME}.ll"
    echo "  Compiling $BASENAME"
    $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime
    LL_FILES="$LL_FILES $OUTFILE"
done

# Step 4: Link everything
# Note: -msse4.2 -mpclmul enables SIMD intrinsics (PSADBW, PCLMULQDQ)
echo
echo "Linking..."
clang $RUNTIME $LL_FILES -o "$SQUEEZE/build/squeeze_tests" -nostdlib -g -msse4.2 -mpclmul

echo
echo "=== Running Squeeze Tests ==="
echo
"$SQUEEZE/build/squeeze_tests" "$@"
