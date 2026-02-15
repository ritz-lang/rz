#!/bin/bash
# build_damage_tests.sh - Build and run damage tracking tests

set -e

export RITZ_SYNTAX=reritz

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RITZ_LANG_DIR="${RITZ_LANG_DIR:-/home/aaron/dev/ritz-lang}"
RITZ_DIR="$RITZ_LANG_DIR/ritz"

RITZ0="python3 $RITZ_DIR/ritz0/ritz0.py"
LIST_DEPS="python3 $RITZ_DIR/ritz0/list_deps.py"
RUNTIME="$RITZ_DIR/runtime/ritz_start.x86_64.o"

# Use system ritzlib and local src
export RITZ_PATH="$RITZ_DIR:$SCRIPT_DIR"

mkdir -p build

echo "=== Building Damage Tracking Tests ==="
echo

echo "Collecting dependencies..."
DEPS=$($LIST_DEPS "test/test_damage.ritz" 2>&1) || {
    echo "Error collecting dependencies:"
    echo "$DEPS"
    exit 1
}

declare -A COMPILED
LL_FILES=""

for SRC in $DEPS; do
    BASENAME=$(basename "$SRC" .ritz)
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

echo
echo "Linking..."
clang $RUNTIME $LL_FILES -o build/test_damage -nostdlib -g

echo
echo "=== Running Tests ==="
./build/test_damage
EXIT_CODE=$?

echo
if [ $EXIT_CODE -eq 0 ]; then
    echo "SUCCESS: All tests passed"
else
    echo "FAILURE: $EXIT_CODE test(s) failed"
fi

exit $EXIT_CODE
