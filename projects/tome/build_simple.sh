#!/bin/bash
# build_simple.sh - Simple build script for Tome using flat ecosystem
#
# This script bypasses ritz.toml and builds directly with the ritz0 compiler.

set -e

cd "$(dirname "$0")"

# Use the flat ecosystem structure
RITZ_LANG_DIR="${RITZ_PATH:-/home/aaron/dev/ritz-lang}"

# Set RITZ_PATH for import resolution
# Put the ecosystem ritz FIRST to avoid finding nested submodule
export RITZ_PATH="$RITZ_LANG_DIR/ritz:."

RITZ0="python3 $RITZ_LANG_DIR/ritz/ritz0/ritz0.py"
LIST_DEPS="python3 $RITZ_LANG_DIR/ritz/ritz0/list_deps.py"
RUNTIME="$RITZ_LANG_DIR/ritz/runtime/ritz_start.x86_64.o"

# Create build directory
mkdir -p build

# Function to compile a binary
compile_binary() {
    local ENTRY="$1"
    local OUTPUT="$2"

    echo "=== Building $OUTPUT ==="

    # Track compiled files to avoid duplicates
    declare -A COMPILED
    LL_FILES=""

    # Get all dependencies
    DEPS=$($LIST_DEPS "$ENTRY")
    for SRC in $DEPS; do
        BASENAME=$(basename "$SRC" .ritz)
        OUTFILE="build/${BASENAME}.ll"

        if [ -z "${COMPILED[$BASENAME]}" ]; then
            echo "  Compiling $SRC"
            $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime
            COMPILED[$BASENAME]=1
            LL_FILES="$LL_FILES $OUTFILE"
        fi
    done

    echo "  Linking..."
    # Use -O1 to work around LLVM 20 crash in SelectionDAGISel
    clang $RUNTIME $LL_FILES -o "build/$OUTPUT" -nostdlib -g -O1
    echo "  Done: build/$OUTPUT"
    echo
}

# Build requested target or all
case "${1:-all}" in
    server)
        compile_binary "bin/tome_server.ritz" "tome-server"
        ;;
    server-blocking)
        compile_binary "bin/tome_server_blocking.ritz" "tome-server-blocking"
        ;;
    cli)
        compile_binary "bin/tome_cli.ritz" "tome-cli"
        ;;
    tests)
        compile_binary "test/run_tests.ritz" "run_tests"
        echo "=== Running Tests ==="
        ./build/run_tests
        ;;
    all)
        compile_binary "bin/tome_server.ritz" "tome-server"
        compile_binary "bin/tome_server_blocking.ritz" "tome-server-blocking"
        compile_binary "bin/tome_cli.ritz" "tome-cli"
        compile_binary "test/run_tests.ritz" "run_tests"
        ;;
    *)
        echo "Usage: $0 [server|server-blocking|cli|tests|all]"
        exit 1
        ;;
esac
