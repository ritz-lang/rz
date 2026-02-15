#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RITZ0="python3 ritz/ritz0/ritz0.py"
LIST_DEPS="python3 ritz/ritz0/list_deps.py"
RUNTIME="ritz/runtime/ritz_start.x86_64.o"

export RITZ_PATH="$SCRIPT_DIR:$SCRIPT_DIR/ritz"

mkdir -p build

# If a source file is provided, build it
if [ -n "$1" ]; then
    SRC="$1"
    OUT="build/$(basename "$SRC" .ritz)"

    echo "Building $SRC..."
    DEPS=$($LIST_DEPS "$SRC")

    for DEP in $DEPS; do
        BASENAME=$(basename "$DEP" .ritz)
        echo "  Compiling $DEP"
        $RITZ0 "$DEP" -o "build/${BASENAME}.ll" --no-runtime
    done

    echo "  Linking..."
    clang $RUNTIME build/*.ll -o "$OUT" -nostdlib -g -mavx2 -mpclmul -msha -maes

    echo "Built: $OUT"
else
    echo "Usage: ./build.sh <source.ritz>"
    echo "Example: ./build.sh src/main.ritz"
fi
