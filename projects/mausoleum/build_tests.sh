#!/bin/bash
# build_tests.sh - Build and run mausoleum tests using ritzunit
#
# This script:
# 1. Uses ritzunit's runner, reporter, types
# 2. Compiles all mausoleum test files
# 3. Links everything into a single binary
# 4. Runs with ELF symbol discovery

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RITZUNIT_DIR="$SCRIPT_DIR/ritzunit"
RITZ_DIR="$SCRIPT_DIR/ritz"
CRYPTOSEC_DIR="$SCRIPT_DIR/cryptosec"

RITZ0="python3 $RITZ_DIR/ritz0/ritz0.py"
LIST_DEPS="python3 $RITZ_DIR/ritz0/list_deps.py"

# Use main ritz repo runtime if submodule doesn't have it built
if [ -f "$RITZ_DIR/runtime/ritz_start.x86_64.o" ]; then
    RUNTIME="$RITZ_DIR/runtime/ritz_start.x86_64.o"
elif [ -f "/home/aaron/dev/ritz-lang/ritz/runtime/ritz_start.x86_64.o" ]; then
    RUNTIME="/home/aaron/dev/ritz-lang/ritz/runtime/ritz_start.x86_64.o"
else
    echo "Error: runtime object not found. Build it with: cd ritz/runtime && make"
    exit 1
fi

# Set RITZ_PATH for imports
export RITZ_PATH="$SCRIPT_DIR:$RITZ_DIR:$RITZUNIT_DIR:$CRYPTOSEC_DIR"

# Validate ritzunit exists
if [ ! -d "$RITZUNIT_DIR/src" ]; then
    echo "Error: ritzunit not found at $RITZUNIT_DIR"
    echo "Did you init submodules? git submodule update --init --recursive"
    exit 1
fi

# Create build directory
rm -rf .build/test
mkdir -p .build/test

# Build LLVM stub functions (bcmp, etc.)
# LLVM may replace memcmp loops with bcmp calls at -O2, which requires a stub
echo "Building runtime stubs..."
as $SCRIPT_DIR/runtime/bcmp.s -o .build/test/bcmp.o

echo "=== Building Mausoleum Tests with ritzunit ==="
echo "RITZ_PATH=$RITZ_PATH"
echo

# Track compiled files to avoid duplicates
declare -A COMPILED
LL_FILES=""

# Step 1: Compile runner and its dependencies
echo "Collecting ritzunit runner dependencies..."
RUNNER_DEPS=$($LIST_DEPS "$RITZUNIT_DIR/src/runner.ritz")

for SRC in $RUNNER_DEPS; do
    BASENAME=$(basename "$SRC" .ritz)
    OUTFILE=".build/test/${BASENAME}.ll"
    if [ -z "${COMPILED[$BASENAME]}" ]; then
        echo "  Compiling $SRC"
        $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime
        COMPILED[$BASENAME]=1
        LL_FILES="$LL_FILES $OUTFILE"
    fi
done

# Step 2: Compile all test files and their dependencies
echo
echo "Compiling test files..."

for TEST_FILE in test/*.ritz; do
    if [ ! -f "$TEST_FILE" ]; then
        continue
    fi

    BASENAME=$(basename "$TEST_FILE" .ritz)

    # Get dependencies for this test file
    TEST_DEPS=$($LIST_DEPS "$TEST_FILE")

    for SRC in $TEST_DEPS; do
        DEP_BASENAME=$(basename "$SRC" .ritz)
        OUTFILE=".build/test/${DEP_BASENAME}.ll"
        if [ -z "${COMPILED[$DEP_BASENAME]}" ]; then
            echo "  Compiling $SRC"
            $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime
            COMPILED[$DEP_BASENAME]=1
            LL_FILES="$LL_FILES $OUTFILE"
        fi
    done
done

# Step 3: Link everything
echo
echo "Linking $(echo $LL_FILES | wc -w) files..."
# Enable SIMD/crypto instruction sets:
# - SHA for SHA-NI (SHA-256 acceleration)
# - AES for AES-NI (AES acceleration)
clang $RUNTIME .build/test/bcmp.o $LL_FILES -o .build/test/mausoleum_tests -nostdlib -g -Wl,--allow-multiple-definition -msha -maes

echo
echo "=== Running Mausoleum Tests ==="
echo
./.build/test/mausoleum_tests "$@"
