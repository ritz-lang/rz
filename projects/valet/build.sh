#!/bin/bash
# Build Valet HTTP server
set -e

cd "$(dirname "$0")"
VALET=$(pwd)
RITZ=$VALET/ritz

# Include submodules for compression and crypto support
export RITZ_PATH=$VALET:$VALET/squeeze:$VALET/cryptosec:$RITZ

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

echo "Building valet ($BUILD_TYPE mode, $OPT_LEVEL)..."

mkdir -p $VALET/.build

# Get all dependencies
DEPS=$(python3 $RITZ/ritz0/list_deps.py $VALET/src/main.ritz)

# Compile each dependency to LLVM IR and object file
OBJECTS=""
for DEP in $DEPS; do
    BASENAME=$(basename $DEP .ritz)
    OUT=$VALET/.build/$BASENAME

    echo "Compiling $BASENAME..."

    # Check if it's the main file (needs runtime) or a library
    if [[ "$DEP" == *"/src/main.ritz" ]]; then
        python3 $RITZ/ritz0/ritz0.py $DEP -o $OUT.ll
    else
        python3 $RITZ/ritz0/ritz0.py $DEP -o $OUT.ll --no-runtime
    fi

    # Enable CPU features for cryptographic intrinsics (AES-NI, SHA-NI, PCLMUL, AVX2)
    clang -c $OPT_LEVEL $OUT.ll -o $OUT.o -Wno-override-module -march=native
    OBJECTS="$OBJECTS $OUT.o"
done

# Link all objects (nostdlib because Ritz provides its own _start)
echo "Linking valet..."
clang $OBJECTS -o $VALET/valet -nostdlib -no-pie

echo "Build complete: $VALET/valet ($BUILD_TYPE)"
ls -la $VALET/valet
