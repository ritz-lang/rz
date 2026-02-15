#!/bin/bash
# Build Mausoleum database server
set -e

cd "$(dirname "$0")"
M7M=$(pwd)
RITZ=$M7M/ritz

# Include submodules for crypto support
export RITZ_PATH=$M7M:$M7M/cryptosec:$RITZ

# Parse arguments
OPT_LEVEL="-O2"
BUILD_TYPE="release"
while [[ $# -gt 0 ]]; do
    case $1 in
        --debug|-d)
            OPT_LEVEL="-O0"
            BUILD_TYPE="debug"
            shift
            ;;
        --release|-r)
            OPT_LEVEL="-O2"
            BUILD_TYPE="release"
            shift
            ;;
        --profile|-p)
            OPT_LEVEL="-O2 -g"
            BUILD_TYPE="profile"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./build.sh [--debug|-d] [--release|-r] [--profile|-p]"
            exit 1
            ;;
    esac
done

echo "Building mausoleum ($BUILD_TYPE mode, $OPT_LEVEL)..."

mkdir -p $M7M/.build

# Check for runtime
if [ -f "$RITZ/runtime/ritz_start.x86_64.o" ]; then
    RUNTIME="$RITZ/runtime/ritz_start.x86_64.o"
elif [ -f "/home/aaron/dev/ritz-lang/ritz/runtime/ritz_start.x86_64.o" ]; then
    RUNTIME="/home/aaron/dev/ritz-lang/ritz/runtime/ritz_start.x86_64.o"
else
    echo "Error: runtime object not found. Build it with: cd ritz/runtime && make"
    exit 1
fi

# Build LLVM stub functions (bcmp, etc.)
# LLVM may replace memcmp loops with bcmp calls, which requires a stub
echo "Building runtime stubs..."
as $M7M/runtime/bcmp.s -o $M7M/.build/bcmp.o

# Get all dependencies
DEPS=$(python3 $RITZ/ritz0/list_deps.py $M7M/src/main.ritz)

# Compile each dependency to LLVM IR and object file
OBJECTS="$M7M/.build/bcmp.o"
for DEP in $DEPS; do
    BASENAME=$(basename $DEP .ritz)
    OUT=$M7M/.build/$BASENAME

    echo "Compiling $BASENAME..."

    # Check if it's the main file (needs runtime) or a library
    if [[ "$DEP" == *"/src/main.ritz" ]]; then
        python3 $RITZ/ritz0/ritz0.py $DEP -o $OUT.ll
    else
        python3 $RITZ/ritz0/ritz0.py $DEP -o $OUT.ll --no-runtime
    fi

    clang -c $OPT_LEVEL $OUT.ll -o $OUT.o -Wno-override-module -fno-builtin
    OBJECTS="$OBJECTS $OUT.o"
done

# Link all objects (nostdlib because Ritz provides its own _start)
# Enable hardware crypto instructions
echo "Linking mausoleum..."
clang $OBJECTS -o $M7M/mausoleum -nostdlib -no-pie -msha -maes

echo "Build complete: $M7M/mausoleum ($BUILD_TYPE)"
ls -la $M7M/mausoleum
