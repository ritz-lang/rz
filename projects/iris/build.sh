#!/bin/bash
# Build Iris rendering engine
set -e

cd "$(dirname "$0")"
IRIS=$(pwd)
RITZ_ROOT=/home/aaron/dev/ritz-lang/ritz

# Include dependencies (prism, angelo)
export RITZ_PATH=$IRIS:/home/aaron/dev/ritz-lang/prism:/home/aaron/dev/ritz-lang/angelo:$RITZ_ROOT

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
        --check|-c)
            # Just check syntax/types, don't link
            BUILD_TYPE="check"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./build.sh [--debug|-d] [--release|-r] [--check|-c]"
            exit 1
            ;;
    esac
done

echo "Building iris ($BUILD_TYPE mode)..."

mkdir -p $IRIS/.build

# Get all dependencies
echo "Finding dependencies..."
DEPS=$(python3 $RITZ_ROOT/ritz0/list_deps.py $IRIS/src/main.ritz 2>&1) || {
    echo "Error finding dependencies:"
    echo "$DEPS"
    exit 1
}

echo "Dependencies found:"
echo "$DEPS" | head -20

if [[ "$BUILD_TYPE" == "check" ]]; then
    echo "Check mode - just parsing/type checking..."
    for DEP in $DEPS; do
        echo "Checking $(basename $DEP)..."
        python3 $RITZ_ROOT/ritz0/ritz0.py $DEP -o /dev/null --no-runtime 2>&1 || true
    done
    exit 0
fi

# Compile each dependency to LLVM IR and object file
OBJECTS=""
for DEP in $DEPS; do
    BASENAME=$(basename $DEP .ritz)
    OUT=$IRIS/.build/$BASENAME

    echo "Compiling $BASENAME..."

    # Check if it's the main file (needs runtime) or a library
    if [[ "$DEP" == *"/src/main.ritz" ]]; then
        python3 $RITZ_ROOT/ritz0/ritz0.py $DEP -o $OUT.ll
    else
        python3 $RITZ_ROOT/ritz0/ritz0.py $DEP -o $OUT.ll --no-runtime
    fi

    clang -c $OPT_LEVEL $OUT.ll -o $OUT.o -Wno-override-module -march=native
    OBJECTS="$OBJECTS $OUT.o"
done

# Link all objects
echo "Linking iris..."
clang $OBJECTS -o $IRIS/iris -nostdlib -no-pie

echo "Build complete: $IRIS/iris ($BUILD_TYPE)"
ls -la $IRIS/iris
