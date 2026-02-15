#!/bin/bash
# Build ritz1 compiler using ritz0
set -e

cd "$(dirname "$0")/.."

echo "🔨 Building ritz1 compiler..."
./ritz1/compile.sh

echo "✅ ritz1 built successfully: /tmp/ritz1"
