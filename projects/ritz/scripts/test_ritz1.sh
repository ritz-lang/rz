#!/bin/bash
# Test ritz1 compiler with unit tests
set -e

cd "$(dirname "$0")/.."

echo "🧪 Testing ritz1 compiler..."

# Run A/B tests
echo ""
echo "📊 Running A/B tests..."
for test in tests/ritz1/ab/*.ritz; do
    if [ -f "$test" ]; then
        echo "  Testing: $(basename $test)"
        ./scripts/ab_test.sh "$test"
    fi
done

echo ""
echo "✅ All tests passed!"
