#!/bin/bash
# Build Nexus HTTP server
set -e

cd "$(dirname "$0")"
NEXUS=$(pwd)

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
    python3 ritz/build.py build . --release
else
    python3 ritz/build.py build .
fi

echo ""
echo "Build complete: build/$BUILD_TYPE/nexus"
echo ""
echo "To run locally:"
echo "  ./build/$BUILD_TYPE/nexus"
echo ""
echo "To run with Docker Compose:"
echo "  cd docker && docker compose -f dev-compose.yml up -d"
