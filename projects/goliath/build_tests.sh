#!/bin/bash
# build_tests.sh - Build test binary with ritzunit
#
# This script compiles all source and test files, links with ritzunit,
# and produces a test binary that discovers and runs tests automatically.

set -e

# Configuration
RITZ_PATH="${RITZ_PATH:-$HOME/dev/ritz-lang}"
RITZ0="python3 $RITZ_PATH/ritz/ritz0/ritz0.py"
LIST_DEPS="python3 $RITZ_PATH/ritz/ritz0/list_deps.py"
RUNTIME="$RITZ_PATH/ritz/runtime/ritz_start.x86_64.o"
RITZUNIT="$RITZ_PATH/ritzunit"

# Build directory
BUILD_DIR="build/test"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

echo "=== Building Goliath Tests ==="
echo "RITZ_PATH: $RITZ_PATH"
echo ""

# Track compiled files to avoid duplicates
declare -A COMPILED
LL_FILES=""

compile_file() {
    local SRC="$1"
    local BASENAME=$(basename "$SRC" .ritz)
    local OUTFILE="$BUILD_DIR/${BASENAME}.ll"

    if [ -z "${COMPILED[$BASENAME]}" ]; then
        echo "  Compiling: $SRC"
        $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime 2>&1 | head -20 || true
        COMPILED[$BASENAME]=1
        LL_FILES="$LL_FILES $OUTFILE"
    fi
}

# Step 1: Compile ritzunit runner and dependencies
echo "Step 1: Compiling ritzunit..."
if [ -d "$RITZUNIT" ]; then
    RUNNER_DEPS=$($LIST_DEPS "$RITZUNIT/src/runner.ritz" 2>/dev/null || echo "$RITZUNIT/src/runner.ritz")
    for SRC in $RUNNER_DEPS; do
        compile_file "$SRC"
    done
else
    echo "  WARNING: ritzunit not found at $RITZUNIT"
    echo "  Tests will compile but won't have test discovery"
fi

# Step 2: Compile ritzlib dependencies
echo ""
echo "Step 2: Compiling ritzlib..."
RITZLIB_FILES=(
    "$RITZ_PATH/ritz/ritzlib/sys.ritz"
    "$RITZ_PATH/ritz/ritzlib/memory.ritz"
    "$RITZ_PATH/ritz/ritzlib/str.ritz"
    "$RITZ_PATH/ritz/ritzlib/strview.ritz"
)
for SRC in "${RITZLIB_FILES[@]}"; do
    if [ -f "$SRC" ]; then
        compile_file "$SRC"
    fi
done

# Step 3: Compile goliath source files
echo ""
echo "Step 3: Compiling goliath source..."
for SRC in src/*.ritz; do
    compile_file "$SRC"
done

# Step 4: Compile test files
echo ""
echo "Step 4: Compiling tests..."
for SRC in test/*.ritz; do
    compile_file "$SRC"
done

# Step 5: Link everything
echo ""
echo "Step 5: Linking..."

# Check if we have any .ll files
if [ -z "$(ls $BUILD_DIR/*.ll 2>/dev/null)" ]; then
    echo "ERROR: No .ll files generated"
    exit 1
fi

# Link with clang
if [ -f "$RUNTIME" ]; then
    clang "$RUNTIME" $BUILD_DIR/*.ll -o "$BUILD_DIR/tests" -nostdlib -g -static 2>&1 || {
        echo "ERROR: Linking failed"
        exit 1
    }
else
    echo "WARNING: Runtime not found, linking without it"
    clang $BUILD_DIR/*.ll -o "$BUILD_DIR/tests" -nostdlib -g -static 2>&1 || {
        echo "ERROR: Linking failed"
        exit 1
    }
fi

echo ""
echo "=== Build Complete ==="
echo "Test binary: $BUILD_DIR/tests"
echo ""
echo "Run tests with:"
echo "  ./build/test/tests        # Run all tests"
echo "  ./build/test/tests -v     # Verbose output"
echo "  ./build/test/tests -l     # List tests"
echo "  ./build/test/tests -f X   # Filter tests by name"
