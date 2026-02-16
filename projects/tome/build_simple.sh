#!/bin/bash
# build_simple.sh - Simple build script for Tome using flat ecosystem
#
# This script bypasses ritz.toml and builds directly with the ritz0 compiler.

set -e

cd "$(dirname "$0")"

# Monorepo structure: projects/ritz, projects/tome, etc.
# Find the monorepo root (parent of projects directory)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MONOREPO_ROOT="${SCRIPT_DIR}/../.."
PROJECTS_DIR="${MONOREPO_ROOT}/projects"

# Set RITZ_PATH for import resolution (projects directory for cross-project imports)
export RITZ_PATH="$PROJECTS_DIR/ritz:$SCRIPT_DIR"

RITZ0="python3 $PROJECTS_DIR/ritz/ritz0/ritz0.py"
LIST_DEPS="python3 $PROJECTS_DIR/ritz/ritz0/list_deps.py"
RUNTIME="$PROJECTS_DIR/ritz/runtime/ritz_start.x86_64.o"

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
        compile_binary "bin/tome_cli.ritz" "tome-cli"
        compile_binary "test/run_tests.ritz" "run_tests"
        ;;
    *)
        echo "Usage: $0 [server|cli|tests|all]"
        exit 1
        ;;
esac
