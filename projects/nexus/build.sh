#!/bin/bash
# Build Nexus HTTP server
set -e

cd "$(dirname "$0")"
NEXUS=$(pwd)

# Monorepo layout: projects/nexus, projects/ritz
RITZ_DIR="../ritz"
RITZ_BUILD="$RITZ_DIR/build.py"

if [ ! -f "$RITZ_BUILD" ]; then
    echo "Error: Cannot find $RITZ_BUILD"
    echo "Are you running from the rz monorepo projects/nexus directory?"
    exit 1
fi

# Create symlinks for build.py import resolution (if not present)
# These are gitignored so they won't be committed
if [ ! -L "ritz" ]; then
    ln -sf "$RITZ_DIR" ritz
fi
if [ ! -L "ritzlib" ]; then
    ln -sf "$RITZ_DIR/ritzlib" ritzlib
fi

# Parse arguments
BUILD_TYPE="debug"
while [[ $# -gt 0 ]]; do
    case $1 in
        --release|-r)
            BUILD_TYPE="release"
            shift
            ;;
        --debug|-d)
            BUILD_TYPE="debug"
            shift
            ;;
        --help|-h)
            echo "Usage: ./build.sh [--debug|-d] [--release|-r]"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "Building Nexus ($BUILD_TYPE mode)..."

# Build using ritz build.py
if [ "$BUILD_TYPE" == "release" ]; then
    python3 "$RITZ_BUILD" build . --release
else
    python3 "$RITZ_BUILD" build .
fi

echo ""
echo "Build complete: build/$BUILD_TYPE/nexus"
echo ""
echo "To run locally:"
echo "  ./build/$BUILD_TYPE/nexus"
echo ""
echo "To run with Docker Compose:"
echo "  cd docker && docker compose -f dev-compose.yml up -d"
