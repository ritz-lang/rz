#!/bin/bash
# build_simple_tests.sh - Build and run simple standalone tests
#
# Uses the system ritz compiler and doesn't require ritzunit framework.

set -e

export RITZ_SYNTAX=reritz

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RITZ_LANG_DIR="${RITZ_LANG_DIR:-/home/aaron/dev/ritz-lang}"
RITZ_DIR="$RITZ_LANG_DIR/ritz"

RITZ0="python3 $RITZ_DIR/ritz0/ritz0.py"
LIST_DEPS="python3 $RITZ_DIR/ritz0/list_deps.py"
RUNTIME="$RITZ_DIR/runtime/ritz_start.x86_64.o"

# Use system ritzlib
export RITZ_PATH="$RITZ_DIR:$SCRIPT_DIR"

# Create build directory
mkdir -p build

echo "=== Building Simple Tests ==="
echo

# Get dependencies
echo "Collecting dependencies..."
DEPS=$($LIST_DEPS "test/simple_test.ritz" 2>&1) || {
    echo "Error collecting dependencies:"
    echo "$DEPS"
    exit 1
}

# Track compiled files
declare -A COMPILED
LL_FILES=""

for SRC in $DEPS; do
    BASENAME=$(basename "$SRC" .ritz)
    OUTFILE="build/${BASENAME}.ll"
    if [ -z "${COMPILED[$BASENAME]}" ]; then
        echo "  Compiling $BASENAME"
        $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime 2>&1 || {
            echo "ERROR compiling $SRC"
            exit 1
        }
        COMPILED[$BASENAME]=1
        LL_FILES="$LL_FILES $OUTFILE"
    fi
done

# Link
echo
echo "Linking..."
clang $RUNTIME $LL_FILES -o build/simple_tests -nostdlib -g

echo
echo "=== Running Tests ==="
./build/simple_tests
EXIT_CODE=$?

echo
if [ $EXIT_CODE -eq 0 ]; then
    echo "SUCCESS: All tests passed"
else
    echo "FAILURE: $EXIT_CODE test(s) failed"
fi

exit $EXIT_CODE
