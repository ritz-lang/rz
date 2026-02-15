#!/bin/bash
# Build config test
set -e

LANGDEV=/home/aaron/dev/nevelis/langdev
VALET=/home/aaron/dev/nevelis/valet

export RITZ_PATH=$LANGDEV

echo "Building test_config..."

mkdir -p $VALET/.build

# Get all dependencies
DEPS=$(python3 $LANGDEV/ritz0/list_deps.py $VALET/tests/test_config.ritz)

# Compile each dependency
OBJECTS=""
for DEP in $DEPS; do
    BASENAME=$(basename $DEP .ritz)
    OUT=$VALET/.build/$BASENAME

    echo "  Compiling $BASENAME..."

    if [[ "$DEP" == *"/tests/test_config.ritz" ]]; then
        python3 $LANGDEV/ritz0/ritz0.py $DEP -o $OUT.ll
    else
        python3 $LANGDEV/ritz0/ritz0.py $DEP -o $OUT.ll --no-runtime
    fi

    clang-19 -c -O0 $OUT.ll -o $OUT.o -Wno-override-module
    OBJECTS="$OBJECTS $OUT.o"
done

# Link
echo "Linking..."
clang $OBJECTS -o $VALET/test_config -nostdlib -no-pie

echo "Running test_config..."
$VALET/test_config
