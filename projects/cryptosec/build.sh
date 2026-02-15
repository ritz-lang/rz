#!/bin/bash
# build.sh - Build cryptosec library and tests
#
# Usage:
#   ./build.sh           # Build library
#   ./build.sh test      # Build and run tests
#   ./build.sh clean     # Clean build artifacts

set -e

# Set RITZ_PATH to include both:
# 1. Current directory (.) - for lib.mem, lib.sha256, etc.
# 2. ritz submodule (./ritz) - for ritzlib.sys, ritzlib.io, etc.
if [ -z "$RITZ_PATH" ]; then
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    if [ -d "$SCRIPT_DIR/ritz" ]; then
        export RITZ_PATH="$SCRIPT_DIR:$SCRIPT_DIR/ritz"
    elif [ -d "../langdev" ]; then
        export RITZ_PATH="$SCRIPT_DIR:$(realpath ../langdev)"
    else
        echo "Error: RITZ_PATH not set and neither ./ritz nor ../langdev found"
        exit 1
    fi
fi

echo "Using RITZ_PATH=$RITZ_PATH"

BUILD_DIR="build"

case "${1:-build}" in
    build)
        mkdir -p "$BUILD_DIR"
        echo "Building cryptosec..."
        # TODO: Add compilation commands as modules are implemented
        echo "Build complete."
        ;;
    test)
        echo "Running tests..."
        python3 ritz/ritz0/ritz0.py --test test/*.ritz
        ;;
    clean)
        echo "Cleaning..."
        rm -rf "$BUILD_DIR" *.ll *.o *.s
        echo "Clean complete."
        ;;
    *)
        echo "Usage: $0 [build|test|clean]"
        exit 1
        ;;
esac
