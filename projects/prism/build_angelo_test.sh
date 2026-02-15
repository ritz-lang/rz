#!/bin/bash
# build_angelo_test.sh - Build and run the Angelo text render test
#
# Renders "Hello World!" using Angelo font library to a PPM file.

set -e

export RITZ_SYNTAX=reritz

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RITZ_LANG_DIR="${RITZ_LANG_DIR:-/home/aaron/dev/ritz-lang}"
RITZ_DIR="$RITZ_LANG_DIR/ritz"
ANGELO_DIR="$RITZ_LANG_DIR/angelo"
RITZUNIT_DIR="$SCRIPT_DIR/ritzunit"

RITZ0="python3 $RITZ_DIR/ritz0/ritz0.py"
LIST_DEPS="python3 $RITZ_DIR/ritz0/list_deps.py"
RUNTIME="$RITZ_DIR/runtime/ritz_start.x86_64.o"

# Set up module paths
# - ritzunit/ritz for ritzlib
# - angelo parent for angelo module (angelo/src contains the files)
# - prism for local modules
# Create a symlink to make angelo accessible as a module
mkdir -p build/modules
ln -sf "$ANGELO_DIR/src" build/modules/angelo
export RITZ_PATH="$RITZUNIT_DIR/ritz:$SCRIPT_DIR/build/modules:$SCRIPT_DIR"

# Create build directory
mkdir -p build

echo "=== Building Angelo Render Test ==="
echo

# Track compiled files
declare -A COMPILED
LL_FILES=""

# Get dependencies for angelo_render_test.ritz
echo "Collecting dependencies..."
DEPS=$($LIST_DEPS "tools/angelo_render_test.ritz" 2>&1) || {
    echo "Error collecting dependencies:"
    echo "$DEPS"
    exit 1
}

echo "Dependencies:"
echo "$DEPS" | head -20
echo "..."

for SRC in $DEPS; do
    BASENAME=$(basename "$SRC" .ritz)
    # Create unique names for files with same basename
    DIRNAME=$(dirname "$SRC" | tr '/' '_')
    OUTFILE="build/${DIRNAME}_${BASENAME}.ll"
    KEY="${DIRNAME}_${BASENAME}"
    if [ -z "${COMPILED[$KEY]}" ]; then
        echo "  Compiling $SRC"
        $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime 2>&1 || {
            echo "ERROR compiling $SRC"
            exit 1
        }
        COMPILED[$KEY]=1
        LL_FILES="$LL_FILES $OUTFILE"
    fi
done

# Link
echo
echo "Linking..."
clang $RUNTIME $LL_FILES -o build/angelo_render_test -nostdlib -lm -g

echo
echo "=== Running Angelo Render Test ==="
echo
./build/angelo_render_test

if [ -f hello_angelo.ppm ]; then
    echo
    echo "SUCCESS! Created hello_angelo.ppm"
    echo "View with: feh hello_angelo.ppm  (or any image viewer)"
    echo "File size: $(ls -la hello_angelo.ppm | awk '{print $5}') bytes"
else
    echo
    echo "ERROR: hello_angelo.ppm was not created"
    exit 1
fi
