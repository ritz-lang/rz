#!/bin/bash
# build_cli.sh - Build the Tome CLI binary
#
# Usage:
#   ./build_cli.sh    # Build tome-cli

set -e

cd "$(dirname "$0")"

# Set RITZ_PATH
export RITZ_PATH=.:ritz

RITZ0="python3 ritz/ritz0/ritz0.py"
LIST_DEPS="python3 ritz/ritz0/list_deps.py"
RUNTIME="ritz/runtime/ritz_start.x86_64.o"

# Create build directory
mkdir -p build

echo "=== Building Tome CLI ==="
echo

# Track compiled files to avoid duplicates
declare -A COMPILED
LL_FILES=""

compile_if_needed() {
    local SRC="$1"
    local BASENAME=$(basename "$SRC" .ritz)
    local OUTFILE="build/${BASENAME}.ll"

    if [ -z "${COMPILED[$BASENAME]}" ]; then
        echo "  Compiling $SRC"
        $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime
        COMPILED[$BASENAME]=1
        LL_FILES="$LL_FILES $OUTFILE"
    fi
}

# Get dependencies for the CLI binary
echo "Compiling CLI and dependencies..."
CLI_DEPS=$($LIST_DEPS bin/tome_cli.ritz)
for SRC in $CLI_DEPS; do
    compile_if_needed "$SRC"
done

# Link
echo
echo "Linking..."
clang -O1 $RUNTIME $LL_FILES -o build/tome-cli -nostdlib -g

echo
echo "=== Build Complete ==="
echo "Binary: build/tome-cli"
