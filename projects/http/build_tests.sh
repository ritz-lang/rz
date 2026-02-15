#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RITZ0="python3 ritz/ritz0/ritz0.py"
LIST_DEPS="python3 ritz/ritz0/list_deps.py"
RUNTIME="ritz/runtime/ritz_start.x86_64.o"

export RITZ_PATH="$SCRIPT_DIR:$SCRIPT_DIR/ritz:$SCRIPT_DIR/ritzunit"
export RITZ_SYNTAX=reritz  # Use new RERITZ syntax (@x, [[test]], etc.)

mkdir -p build
rm -f build/*.ll

echo "========================================"
echo "  Building HTTP Library Tests"
echo "========================================"

# Collect all unique source files
SOURCES=""
SEEN_FILES=""

add_deps() {
    local SRC="$1"
    local DEPS=$($LIST_DEPS "$SRC" 2>/dev/null || echo "$SRC")
    for DEP in $DEPS; do
        # Skip json_reporter (has duplicate print_char symbol)
        if [[ "$DEP" == *"json_reporter"* ]]; then
            continue
        fi
        # Check if already seen
        if [[ ! " $SEEN_FILES " =~ " $DEP " ]]; then
            SEEN_FILES="$SEEN_FILES $DEP"
            SOURCES="$SOURCES $DEP"
        fi
    done
}

# Collect runner dependencies
echo "Collecting ritzunit runner dependencies..."
add_deps "ritzunit/src/runner.ritz"

# Add our json stub to replace the conflicting json_reporter
SOURCES="$SOURCES lib/json_stub.ritz"
SEEN_FILES="$SEEN_FILES lib/json_stub.ritz"

# Collect test file dependencies
echo "Collecting test dependencies..."
for TEST_FILE in test/test_*.ritz; do
    if [ -f "$TEST_FILE" ]; then
        add_deps "$TEST_FILE"
    fi
done

# Count and compile
COUNT=$(echo $SOURCES | wc -w)
echo ""
echo "Compiling $COUNT modules..."

for SRC in $SOURCES; do
    # Generate unique output name based on path
    BASENAME=$(basename "$SRC" .ritz)
    PARENT=$(basename "$(dirname "$SRC")")
    OUTNAME="${PARENT}_${BASENAME}"
    echo "  $SRC -> build/${OUTNAME}.ll"
    $RITZ0 "$SRC" -o "build/${OUTNAME}.ll" --no-runtime
done

# Link
echo ""
echo "Linking..."
clang $RUNTIME build/*.ll -o build/http_tests -nostdlib -g -mavx2 -mpclmul -msha -maes

echo ""
echo "========================================"
echo "  Running Tests"
echo "========================================"
./build/http_tests "$@"
