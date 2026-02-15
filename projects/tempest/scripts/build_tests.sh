#!/bin/bash
# build_tests.sh - Build Tempest tests with ritzunit
#
# This script compiles test files and their dependencies with ritzunit runner.

set -e

# Use the local ritz symlink (points to ritzunit's ritz submodule)
# This ensures compatibility with ritzunit which uses RERITZ syntax
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RITZ_PATH="$SCRIPT_DIR/ritz"
RITZUNIT_PATH="${RITZ_ROOT:-$HOME/dev/ritz-lang}/ritzunit"

RITZ0="python3 $RITZ_PATH/ritz0/ritz0.py"
LIST_DEPS="python3 $RITZ_PATH/ritz0/list_deps.py"
RUNTIME="$RITZ_PATH/runtime/ritz_start.x86_64.o"

# Use RERITZ syntax mode for new attribute syntax ([[test]] instead of @test)
export RITZ_SYNTAX=reritz

# Build directory
BUILD_DIR="$SCRIPT_DIR/build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Track compiled files to avoid duplicates
declare -A COMPILED
LL_FILES=""

compile_file() {
    local SRC="$1"
    local BASENAME=$(basename "$SRC" .ritz)
    local OUTFILE="$BUILD_DIR/${BASENAME}.ll"

    if [ -z "${COMPILED[$BASENAME]}" ]; then
        echo "  Compiling $SRC"
        $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime
        if [ $? -eq 0 ]; then
            echo "Compiled $SRC -> $OUTFILE"
            COMPILED[$BASENAME]=1
            LL_FILES="$LL_FILES $OUTFILE"
        else
            echo "FAILED: $SRC"
            return 1
        fi
    fi
}

# Compile ritzunit runner and dependencies
echo "Collecting ritzunit runner dependencies..."
RUNNER_DEPS=$($LIST_DEPS "$RITZUNIT_PATH/src/runner.ritz")

for SRC in $RUNNER_DEPS; do
    compile_file "$SRC"
done

# Compile test files and their dependencies
echo "Compiling Tempest tests..."
for TEST_FILE in "$SCRIPT_DIR"/tests/*.ritz; do
    if [ -f "$TEST_FILE" ]; then
        echo "Getting dependencies for $TEST_FILE..."
        TEST_DEPS=$($LIST_DEPS "$TEST_FILE" 2>&1) || {
            echo "Warning: Failed to get deps for $TEST_FILE: $TEST_DEPS"
            continue
        }

        for SRC in $TEST_DEPS; do
            compile_file "$SRC" || exit 1
        done
    fi
done

# Link everything
echo "Linking..."
clang $RUNTIME $LL_FILES -o "$BUILD_DIR/tempest_tests" -nostdlib -g

echo "Build complete: $BUILD_DIR/tempest_tests"
