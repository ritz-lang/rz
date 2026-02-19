#!/bin/bash
# Compile ritz1 compiler with ritz0 using separate compilation
#
# Uses the same build model as build.py:
# 1. Discover all source files via import resolution
# 2. Compile each source file to .ll
# 3. Link all .ll files together with clang

set -e

RITZ0="python3 ritz0/ritz0.py"
LIST_DEPS="python3 ritz0/list_deps.py"
SRC_DIR="ritz1/src"
BUILD_DIR="ritz1/build"
OUT=${1:-ritz1/ritz1}

echo "🔨 Compiling ritz1 with ritz0..."

# Create build directory
mkdir -p $BUILD_DIR

# Discover all source files
echo "  📦 Discovering imports..."
SOURCES=$($LIST_DEPS $SRC_DIR/main.ritz)

# Compile each source file to LLVM IR
LL_FILES=""
for SRC in $SOURCES; do
    # Get unique name for this source file
    BASENAME=$(basename $SRC .ritz)
    HASH=$(echo $SRC | md5sum | cut -c1-8)
    LL_FILE="$BUILD_DIR/${BASENAME}_${HASH}.ll"

    echo "  🔧 $SRC -> $LL_FILE"
    $RITZ0 $SRC -o $LL_FILE --no-runtime

    LL_FILES="$LL_FILES $LL_FILE"
done

echo "  ✅ Generated $(echo $LL_FILES | wc -w) .ll files"

# Link all .ll files with clang
echo "  🔗 Linking..."
# Use envp variant since main() uses 3 arguments (argc, argv, envp)
RUNTIME=runtime/ritz_start_envp.x86_64.o
# Build runtime if needed
if [ ! -f "$RUNTIME" ]; then
    echo "  📦 Building runtime..."
    clang -c -o runtime/ritz_start_envp.x86_64.o runtime/ritz_start_envp.x86_64.ll
fi
clang $LL_FILES $RUNTIME -o $OUT -nostdlib -g

echo ""
echo "✨ ritz1 compiler ready: $OUT"
echo "Usage: $OUT [-v] input.ritz -o output.ll [-I ritz_path]"
