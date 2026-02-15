#!/bin/bash
# A/B Test: Compare ritz0 vs ritz1 compiled outputs
#
# A: compile with ritz0, run
# B: compile ritz1 with ritz0, compile with ritz1, run

set -e

TEST_FILE=$1
if [ -z "$TEST_FILE" ]; then
  echo "Usage: $0 <test_file.ritz>"
  exit 1
fi

echo "🧪 A/B Testing: $TEST_FILE"
echo "================================"

# A: Compile with ritz0
echo "📦 A: Compiling with ritz0..."
python3 ritz0/ritz0.py "$TEST_FILE" -o /tmp/test_a.ll --no-runtime
llc /tmp/test_a.ll -o /tmp/test_a.s
gcc /tmp/test_a.s ritz1/runtime/ritz_crt0.o -o /tmp/test_a -nostartfiles -static
echo "✅ A binary ready: /tmp/test_a"

# B: Compile ritz1 with ritz0, then compile test with ritz1
echo ""
echo "📦 B: Compiling ritz1 with ritz0..."
./ritz1/compile.sh > /dev/null 2>&1
echo "✅ ritz1 compiler ready"

echo "📦 B: Compiling test with ritz1..."
/tmp/ritz1 "$TEST_FILE" -o /tmp/test_b.ll
llc /tmp/test_b.ll -o /tmp/test_b.s
gcc /tmp/test_b.s ritz1/runtime/ritz_crt0.o -o /tmp/test_b -nostartfiles -static
echo "✅ B binary ready: /tmp/test_b"

# Run both and compare
echo ""
echo "🏃 Running A (ritz0)..."
set +e  # Allow non-zero exit codes
/tmp/test_a
EXIT_A=$?
set -e  # Re-enable exit on error
echo "Exit code A: $EXIT_A"

echo ""
echo "🏃 Running B (ritz1)..."
set +e  # Allow non-zero exit codes
/tmp/test_b
EXIT_B=$?
set -e  # Re-enable exit on error
echo "Exit code B: $EXIT_B"

echo ""
echo "================================"
if [ $EXIT_A -eq $EXIT_B ]; then
  echo "✅ PASS: Both compilers produce same result ($EXIT_A)"
else
  echo "❌ FAIL: Different results! A=$EXIT_A, B=$EXIT_B"
  exit 1
fi
