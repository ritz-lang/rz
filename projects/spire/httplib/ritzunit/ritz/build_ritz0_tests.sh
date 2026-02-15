#!/bin/bash
# build_ritz0_tests.sh - Build ritz0 test suite using ritzunit
#
# Compiles all dependencies and test files to LLVM IR, then links them
# together into a single binary that uses ELF-based test discovery.
#
# Usage:
#   ./build_ritz0_tests.sh           # Build and show summary
#   ./build_ritz0_tests.sh -v        # Verbose output
#   ./build_ritz0_tests.sh -r        # Build and run

set -e

RITZ0="python3 ritz0/ritz0.py"
LIST_DEPS="python3 ritz0/list_deps.py"
RITZUNIT_DIR="../ritzunit"
RUNTIME="runtime/ritz_start.x86_64.o"
BUILD_DIR="build/ritz0_tests"

VERBOSE=0
RUN_AFTER=0

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose) VERBOSE=1; shift ;;
        -r|--run)     RUN_AFTER=1; shift ;;
        *)            echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Check ritzunit exists
if [ ! -d "$RITZUNIT_DIR" ]; then
    echo "Error: ritzunit not found at $RITZUNIT_DIR"
    echo "Clone it with: git clone https://github.com/ritz-lang/ritzunit ../ritzunit"
    exit 1
fi

# Check runtime exists
if [ ! -f "$RUNTIME" ]; then
    echo "Building runtime..."
    make -C runtime/
fi

# Create build directory
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

echo "=== Building ritz0 Test Suite ==="
echo

# Track compiled files (associative array: basename -> ll_path)
declare -A COMPILED

# Helper function to compile a source file if not already done
compile_source() {
    local SRC="$1"
    local BASENAME=$(basename "$SRC" .ritz)
    local OUTFILE="$BUILD_DIR/${BASENAME}.ll"

    # Skip if already compiled
    if [ -n "${COMPILED[$BASENAME]}" ]; then
        return 0
    fi

    # Try to compile
    if $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime 2>/dev/null; then
        COMPILED[$BASENAME]="$OUTFILE"
        if [ $VERBOSE -eq 1 ]; then
            echo "  ✓ $BASENAME"
        fi
        return 0
    else
        if [ $VERBOSE -eq 1 ]; then
            echo "  ✗ $BASENAME (compile error)"
        fi
        return 1
    fi
}

# Step 1: Compile the runner and its dependencies
echo "Compiling runner..."
RUNNER="$RITZUNIT_DIR/test/runner_test_v2.ritz"
RUNNER_DEPS=$($LIST_DEPS "$RUNNER" 2>/dev/null || echo "$RUNNER")

for DEP in $RUNNER_DEPS; do
    compile_source "$DEP"
done

RUNNER_COUNT=${#COMPILED[@]}
echo "  $RUNNER_COUNT module(s)"

# Step 2: Compile all test files and their dependencies
#
# Note: Files with main() are excluded - runner_test_v2 provides main.
# All conflicting helper functions have been prefixed (e.g., l4_strlen, l14_alloc)
#
EXCLUDED=""

echo
echo "Compiling test files..."
TEST_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

for TEST_SRC in ritz0/test/test_level*.ritz; do
    BASENAME=$(basename "$TEST_SRC" .ritz)

    # Skip files with main() - runner provides main
    if grep -q "^fn main" "$TEST_SRC"; then
        if [ $VERBOSE -eq 1 ]; then
            echo "  - $BASENAME (has main)"
        fi
        ((SKIP_COUNT++)) || true
        continue
    fi

    # Skip excluded files with conflicting function names
    if [[ " $EXCLUDED " == *" $BASENAME "* ]]; then
        if [ $VERBOSE -eq 1 ]; then
            echo "  - $BASENAME (conflicts)"
        fi
        ((SKIP_COUNT++)) || true
        continue
    fi

    # Get dependencies for this test file
    TEST_DEPS=$($LIST_DEPS "$TEST_SRC" 2>/dev/null || echo "")

    # Compile dependencies first
    for DEP in $TEST_DEPS; do
        compile_source "$DEP" || true
    done

    # Compile the test file itself
    if compile_source "$TEST_SRC"; then
        ((TEST_COUNT++)) || true
    else
        ((FAIL_COUNT++)) || true
    fi
done

echo "  $TEST_COUNT test file(s) compiled ($FAIL_COUNT failed, $SKIP_COUNT skipped)"
echo "  ${#COMPILED[@]} total module(s)"

if [ $TEST_COUNT -eq 0 ]; then
    echo
    echo "Error: No test files compiled successfully!"
    exit 1
fi

# Step 3: Link all compiled files
echo
echo "Linking..."

# Collect all .ll files
LL_FILES=""
for BASENAME in "${!COMPILED[@]}"; do
    LL_FILES="$LL_FILES ${COMPILED[$BASENAME]}"
done

# Link with clang
if clang $RUNTIME $LL_FILES -o "$BUILD_DIR/tests" -nostdlib -g 2>&1; then
    SIZE=$(ls -lh "$BUILD_DIR/tests" | awk '{print $5}')
    echo "  Binary: $BUILD_DIR/tests ($SIZE)"
else
    echo
    echo "=== Link Failed ==="
    echo "Run with -v for verbose output"
    exit 1
fi

echo
echo "=== Build Complete ==="
echo "Run with: ./$BUILD_DIR/tests"

# Optionally run
if [ $RUN_AFTER -eq 1 ]; then
    echo
    ./"$BUILD_DIR/tests"
fi
