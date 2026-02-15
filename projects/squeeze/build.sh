#!/bin/bash
# Build script for Squeeze compression library

set -e

SQUEEZE=$(dirname "$(readlink -f "$0")")
RITZ=$SQUEEZE/ritz/ritz0/ritz0.py

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

if [ ! -f "$RITZ" ]; then
    echo -e "${RED}Error: Ritz compiler not found at $RITZ${NC}"
    echo "Run: git submodule update --init"
    exit 1
fi

echo "Building Squeeze..."

# Build main library (when we have source files)
# python3 $RITZ src/main.ritz -o squeeze

echo -e "${GREEN}Build complete${NC}"
