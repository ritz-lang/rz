#!/bin/bash
# build_core_tests.sh - Build and run Prism core tests (standalone)
#
# This builds only the core tests that don't require external dependencies.
# Useful for verifying the build system works.

set -e

# Use RERITZ syntax mode for [[test]] attribute syntax
export RITZ_SYNTAX=reritz

# Set up paths
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Use the system-wide ritz-lang directory since submodule doesn't have compiled runtime
RITZ_LANG_DIR="${RITZ_LANG_DIR:-/home/aaron/dev/ritz-lang}"
RITZ_DIR="$RITZ_LANG_DIR/ritz"
RITZUNIT_DIR="$SCRIPT_DIR/ritzunit"

RITZ0="python3 $RITZ_DIR/ritz0/ritz0.py"
LIST_DEPS="python3 $RITZ_DIR/ritz0/list_deps.py"
RUNTIME="$RITZ_DIR/runtime/ritz_start.x86_64.o"

# Set RITZ_PATH so imports resolve correctly
# Use ritzunit's ritz submodule for ritzlib since it has matching versions
export RITZ_PATH="$RITZUNIT_DIR/ritz:$RITZUNIT_DIR:$SCRIPT_DIR"

# Create build directory
rm -rf build
mkdir -p build

echo "=== Building Prism Core Tests ==="
echo

# Track compiled files to avoid duplicates
declare -A COMPILED
LL_FILES=""

# Step 1: Compile ritzunit runner and its dependencies
echo "Compiling ritzunit framework..."
RUNNER_DEPS=$($LIST_DEPS "$RITZUNIT_DIR/src/runner.ritz")

for SRC in $RUNNER_DEPS; do
    BASENAME=$(basename "$SRC" .ritz)
    OUTFILE="build/${BASENAME}.ll"
    if [ -z "${COMPILED[$BASENAME]}" ]; then
        echo "  $BASENAME"
        $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime
        COMPILED[$BASENAME]=1
        LL_FILES="$LL_FILES $OUTFILE"
    fi
done

# Step 2: Compile test_core.ritz (standalone, no imports)
echo
echo "Compiling test_core.ritz..."
$RITZ0 "test/test_core.ritz" -o "build/test_core.ll" --no-runtime
LL_FILES="$LL_FILES build/test_core.ll"

# Step 3: Link everything
echo
echo "Linking..."
clang $RUNTIME $LL_FILES -o build/core_tests -nostdlib -g

echo
echo "=== Running Core Tests ==="
echo
./build/core_tests "$@"
