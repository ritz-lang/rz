#!/bin/bash
# build_tests.sh - Build and run iris unit tests
#
# Uses ritzunit for test discovery and execution.

set -e

export RITZ_SYNTAX=reritz

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RITZ_DIR="$SCRIPT_DIR/ritzunit/ritz"
RITZUNIT_DIR="$SCRIPT_DIR/ritzunit"

RITZ0="python3 $RITZ_DIR/ritz0/ritz0.py"
LIST_DEPS="python3 $RITZ_DIR/ritz0/list_deps.py"
RUNTIME="$RITZ_DIR/runtime/ritz_start.x86_64.o"

# Use local ritzlib and iris lib
export RITZ_PATH="$RITZ_DIR:$RITZUNIT_DIR:$SCRIPT_DIR"

mkdir -p build

echo "=== Building Iris Tests ==="
echo

# First compile ritzunit runner dependencies
echo "Compiling ritzunit runner..."
RUNNER_DEPS=$($LIST_DEPS "$RITZUNIT_DIR/src/runner.ritz" 2>&1) || {
    echo "Error collecting runner dependencies:"
    echo "$RUNNER_DEPS"
    exit 1
}

declare -A COMPILED
LL_FILES=""

for SRC in $RUNNER_DEPS; do
    # Use hash of full path to avoid collision between modules with same name
    HASH=$(echo "$SRC" | md5sum | cut -c1-8)
    BASENAME=$(basename "$SRC" .ritz)
    OUTFILE="build/${BASENAME}_${HASH}.ll"
    if [ -z "${COMPILED[$SRC]}" ]; then
        echo "  Compiling $BASENAME"
        $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime 2>&1 || {
            echo "ERROR compiling $SRC"
            exit 1
        }
        COMPILED[$SRC]=1
        LL_FILES="$LL_FILES $OUTFILE"
    fi
done

# Now compile the test file
TEST_FILE="${1:-tests/test_style_types.ritz}"
echo
echo "Compiling test: $TEST_FILE"
TEST_DEPS=$($LIST_DEPS "$TEST_FILE" 2>&1) || {
    echo "Error collecting test dependencies:"
    echo "$TEST_DEPS"
    exit 1
}

for SRC in $TEST_DEPS; do
    # Use hash of full path to avoid collision between modules with same name
    HASH=$(echo "$SRC" | md5sum | cut -c1-8)
    BASENAME=$(basename "$SRC" .ritz)
    OUTFILE="build/${BASENAME}_${HASH}.ll"
    if [ -z "${COMPILED[$SRC]}" ]; then
        echo "  Compiling $BASENAME"
        $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime 2>&1 || {
            echo "ERROR compiling $SRC"
            exit 1
        }
        COMPILED[$SRC]=1
        LL_FILES="$LL_FILES $OUTFILE"
    fi
done

echo
echo "Linking..."
clang $RUNTIME $LL_FILES -o build/iris_tests -nostdlib -g

echo
echo "=== Running Tests ==="
./build/iris_tests
EXIT_CODE=$?

echo
if [ $EXIT_CODE -eq 0 ]; then
    echo "SUCCESS: All tests passed"
else
    echo "FAILURE: Tests failed with code $EXIT_CODE"
fi

exit $EXIT_CODE
