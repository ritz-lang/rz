#!/bin/bash
# build_zeus.sh - Build the Zeus daemon binary
#
# Usage:
#   ./build_zeus.sh              # Build zeus binary
#   ./build_zeus.sh --release    # Build with optimizations

set -e

cd "$(dirname "$0")"

# Set RITZ_PATH
export RITZ_PATH=.

RITZ0="python3 ritz/ritz0/ritz0.py"
LIST_DEPS="python3 ritz/ritz0/list_deps.py"
RUNTIME="ritz/runtime/ritz_start.x86_64.o"

# Create build directory
mkdir -p build

echo "=== Building Zeus Daemon ==="
echo

# Track compiled files
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

# Compile main and all dependencies
echo "Compiling sources..."
DEPS=$($LIST_DEPS src/main.ritz)
for SRC in $DEPS; do
    compile_if_needed "$SRC"
done

# Link
echo
echo "Linking..."

OPT_FLAGS=""
if [ "$1" == "--release" ]; then
    OPT_FLAGS="-O2"
    echo "  (release mode with optimizations)"
fi

clang $RUNTIME $LL_FILES -o build/zeus -nostdlib -g $OPT_FLAGS

echo
echo "=== Build Complete ==="
echo "Binary: build/zeus"
