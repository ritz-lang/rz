#!/bin/bash
# build_multifile_test.sh - Demonstrates multi-file test discovery
#
# This script:
# 1. Collects all dependencies for runner_test_v2.ritz
# 2. Adds test_math.ritz as an additional test file
# 3. Compiles all source files to LLVM IR
# 4. Links them together into one binary
# 5. The runner's ELF discovery should find all test_* functions from BOTH test files
#
# Expected: runner should discover 8 tests (4 from runner_test_v2 + 4 from test_math)

set -e

RITZ0="python3 ritz/ritz0/ritz0.py"
LIST_DEPS="python3 ritz/ritz0/list_deps.py"
RUNTIME="ritz/runtime/ritz_start.x86_64.o"

# Create build directory
rm -rf build
mkdir -p build

echo "=== Building Multi-File Test ==="
echo

# Step 1: Get all dependencies for the main runner
echo "Collecting dependencies..."
DEPS=$($LIST_DEPS test/runner_test_v2.ritz)

# All .ll files we'll link
LL_FILES=""

# Step 2: Compile all dependencies (including runner_test_v2)
for SRC in $DEPS; do
    # Get base name for output
    BASENAME=$(basename "$SRC" .ritz)
    OUTFILE="build/${BASENAME}.ll"

    echo "Compiling $SRC -> $OUTFILE"
    $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime
    LL_FILES="$LL_FILES $OUTFILE"
done

# Step 3: Compile test_math.ritz (additional test file with more tests)
# Note: test_math.ritz has its own imports but they're already covered by runner deps
echo "Compiling test/test_math.ritz -> build/test_math.ll"
$RITZ0 test/test_math.ritz -o build/test_math.ll --no-runtime
LL_FILES="$LL_FILES build/test_math.ll"

# Step 4: Link everything together
echo
echo "Linking: $LL_FILES"
clang $RUNTIME $LL_FILES -o build/multifile_test -nostdlib -g

echo
echo "=== Running Multi-File Test ==="
echo
./build/multifile_test

echo
echo "=========================================="
echo "If you see 8 tests discovered, multi-file discovery works!"
echo "=========================================="
