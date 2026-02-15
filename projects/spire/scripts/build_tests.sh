#!/bin/bash
# build_tests.sh - Build Spire test binary
#
# This script compiles all Spire library code and test files,
# then links them into a single test binary that can be run
# with ritzunit-style test discovery.

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# Compiler settings
RITZ0="python3 ritz/ritz0/ritz0.py"
RUNTIME="ritz/runtime/ritz_start.x86_64.o"

# Directories
BUILD_DIR="build/test"
LIB_DIR="lib"
TEST_DIR="test"

# Create build directory
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

echo -e "${YELLOW}=== Building Spire Tests ===${NC}"

# Track compiled files
declare -A COMPILED
LL_FILES=""

# Function to compile a single file
compile_file() {
    local SRC="$1"
    local BASENAME=$(basename "$SRC" .ritz)
    local OUTFILE="$BUILD_DIR/${BASENAME}.ll"

    if [ -z "${COMPILED[$BASENAME]}" ]; then
        echo "  Compiling $SRC"
        $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime 2>&1 || {
            echo -e "${RED}Failed to compile $SRC${NC}"
            return 1
        }
        COMPILED[$BASENAME]=1
        LL_FILES="$LL_FILES $OUTFILE"
    fi
}

# Step 1: Compile ritzlib dependencies
echo -e "${YELLOW}Step 1: Compiling ritzlib...${NC}"
for SRC in ritz/ritzlib/*.ritz; do
    if [ -f "$SRC" ]; then
        compile_file "$SRC" || true
    fi
done

# Step 2: Compile spire library code
echo -e "${YELLOW}Step 2: Compiling Spire library...${NC}"

# First, compile utils (no dependencies on other spire modules)
compile_file "lib/utils.ritz" || true

# Then compile modules in dependency order
for MODULE in http model repo router app json form service middleware presenter cli test; do
    if [ -d "lib/$MODULE" ]; then
        for SRC in lib/$MODULE/*.ritz; do
            if [ -f "$SRC" ]; then
                compile_file "$SRC" || true
            fi
        done
    fi
done

# Compile mod.ritz last
compile_file "lib/mod.ritz" || true

# Step 3: Compile test files
echo -e "${YELLOW}Step 3: Compiling tests...${NC}"
for SRC in $TEST_DIR/test_*.ritz; do
    if [ -f "$SRC" ]; then
        compile_file "$SRC" || true
    fi
done

# Step 4: Link everything
echo -e "${YELLOW}Step 4: Linking...${NC}"

if [ -z "$LL_FILES" ]; then
    echo -e "${RED}No files to link!${NC}"
    exit 1
fi

# Check if runtime exists
if [ ! -f "$RUNTIME" ]; then
    echo -e "${RED}Runtime not found: $RUNTIME${NC}"
    echo "Make sure ritz submodule is initialized: git submodule update --init"
    exit 1
fi

clang $RUNTIME $LL_FILES -o "$BUILD_DIR/tests" -nostdlib -g 2>&1 || {
    echo -e "${RED}Linking failed${NC}"
    exit 1
}

echo -e "${GREEN}=== Build complete: $BUILD_DIR/tests ===${NC}"

# Show stats
TEST_COUNT=$(grep -rh "@test" $TEST_DIR/*.ritz 2>/dev/null | wc -l || echo 0)
echo ""
echo "Test functions found: ~$TEST_COUNT"
echo "Run tests with: $BUILD_DIR/tests"
echo "Or use: make test"
