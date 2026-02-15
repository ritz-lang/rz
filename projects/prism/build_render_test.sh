#!/bin/bash
# build_render_test.sh - Build and run the bitmap render test
#
# Renders "Hello World!" to a PPM file for visual inspection.

set -e

export RITZ_SYNTAX=reritz

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RITZ_LANG_DIR="${RITZ_LANG_DIR:-/home/aaron/dev/ritz-lang}"
RITZ_DIR="$RITZ_LANG_DIR/ritz"
RITZUNIT_DIR="$SCRIPT_DIR/ritzunit"

RITZ0="python3 $RITZ_DIR/ritz0/ritz0.py"
LIST_DEPS="python3 $RITZ_DIR/ritz0/list_deps.py"
RUNTIME="$RITZ_DIR/runtime/ritz_start.x86_64.o"

# Use ritzunit's ritz submodule for ritzlib
export RITZ_PATH="$RITZUNIT_DIR/ritz:$SCRIPT_DIR"

# Create build directory
mkdir -p build

echo "=== Building Render Test ==="
echo

# Track compiled files
declare -A COMPILED
LL_FILES=""

# Get dependencies for render_test.ritz
echo "Collecting dependencies..."
DEPS=$($LIST_DEPS "tools/render_test.ritz")

for SRC in $DEPS; do
    BASENAME=$(basename "$SRC" .ritz)
    OUTFILE="build/${BASENAME}.ll"
    if [ -z "${COMPILED[$BASENAME]}" ]; then
        echo "  Compiling $BASENAME"
        $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime
        COMPILED[$BASENAME]=1
        LL_FILES="$LL_FILES $OUTFILE"
    fi
done

# Link
echo
echo "Linking..."
clang $RUNTIME $LL_FILES -o build/render_test -nostdlib -g

echo
echo "=== Running Render Test ==="
echo
./build/render_test

if [ -f hello.ppm ]; then
    echo
    echo "SUCCESS! Created hello.ppm"
    echo "View with: feh hello.ppm  (or any image viewer)"
    echo "File size: $(ls -la hello.ppm | awk '{print $5}') bytes"
else
    echo
    echo "ERROR: hello.ppm was not created"
    exit 1
fi
