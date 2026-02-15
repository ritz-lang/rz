#!/bin/bash
# build_inventory_tests.sh - Build and run inventory tests with ritzunit reporter
#
# This demonstrates the full ritzunit architecture:
# 1. src/runner.ritz - ELF-based test discovery with PIE support
# 2. src/reporter.ritz - Visual output
# 3. src/types.ritz - TestSummary and status codes
# 4. inventory/test/test_inventory.ritz - 17 @test functions

set -e

# Use RERITZ syntax mode for new attribute syntax ([[test]] instead of @test)
export RITZ_SYNTAX=reritz

RITZ0="python3 ritz/ritz0/ritz0.py"
LIST_DEPS="python3 ritz/ritz0/list_deps.py"
RUNTIME="ritz/runtime/ritz_start.x86_64.o"

# Create build directory
rm -rf build
mkdir -p build

echo "=== Building Inventory Tests with ritzunit ==="
echo

# Step 1: Get all dependencies for the runner (includes reporter, types, ritzlib)
echo "Collecting runner dependencies..."
RUNNER_DEPS=$($LIST_DEPS src/runner.ritz)

# All .ll files we'll link (track to avoid duplicates)
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

# Step 3: Compile inventory test file
echo "Compiling inventory/test/test_inventory.ritz"
$RITZ0 inventory/test/test_inventory.ritz -o build/test_inventory.ll --no-runtime
LL_FILES="$LL_FILES build/test_inventory.ll"

# Step 4: Link everything
echo
echo "Linking..."
clang $RUNTIME $LL_FILES -o build/inventory_tests -nostdlib -g

echo
echo "=== Running Inventory Tests ==="
echo
./build/inventory_tests
