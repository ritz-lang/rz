#!/bin/bash
# test.sh - Build and run Iris tests

set -e
cd "$(dirname "$0")"

IRIS=$(pwd)
RITZ_ROOT=/home/aaron/dev/ritz-lang/ritz
RITZ0=$RITZ_ROOT/ritz0/ritz0.py
LIST_DEPS=$RITZ_ROOT/ritz0/list_deps.py
BUILD_DIR=$IRIS/.build/tests
OUTPUT_DIR=$IRIS/bin/tests

export RITZ_PATH=$IRIS:/home/aaron/dev/ritz-lang/prism:/home/aaron/dev/ritz-lang/angelo:$RITZ_ROOT

mkdir -p $BUILD_DIR
mkdir -p $OUTPUT_DIR

# Build a test file
build_test() {
    local name=$1
    local src=$IRIS/tests/${name}.ritz

    echo "Building test: $name"

    # Find dependencies using list_deps.py
    DEPS=$(python3 $LIST_DEPS $src 2>&1) || {
        echo "Error finding dependencies:"
        echo "$DEPS"
        return 1
    }

    # Compile each dependency
    for dep in $DEPS; do
        local depname=$(basename $dep .ritz)
        local depout=$BUILD_DIR/${depname}.ll
        local depobj=$BUILD_DIR/${depname}.o

        echo "  Compiling $depname..."

        # Check if it's the main test file (needs runtime) or a library
        if [[ "$dep" == *"/tests/"* ]]; then
            python3 $RITZ0 -o $depout $dep
        else
            python3 $RITZ0 -o $depout --no-runtime $dep
        fi

        clang -c -O2 $depout -o $depobj -Wno-override-module -march=native
    done

    # Collect all object files
    OBJ_FILES=$(ls $BUILD_DIR/*.o)

    # Link
    clang $OBJ_FILES -o $OUTPUT_DIR/$name -nostdlib -no-pie

    echo "  -> $OUTPUT_DIR/$name"
}

# Run a test
run_test() {
    local name=$1
    echo ""
    echo "=== Running $name ==="
    $OUTPUT_DIR/$name
    return $?
}

# Main
if [ "$1" == "" ]; then
    # Run all tests
    for test in tests/test_*.ritz; do
        name=$(basename $test .ritz)
        # Clean build dir for each test
        rm -f $BUILD_DIR/*.ll $BUILD_DIR/*.o
        build_test $name && run_test $name
    done
else
    # Run specific test
    rm -f $BUILD_DIR/*.ll $BUILD_DIR/*.o
    build_test $1
    run_test $1
fi
