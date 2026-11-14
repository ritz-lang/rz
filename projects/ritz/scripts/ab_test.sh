#!/bin/bash
# A/B Test: Compare ritz0 vs ritz1 compiled outputs
#
# A: compile with ritz0, run
# B: compile ritz1 with ritz0, compile with ritz1, run
#
# Run from projects/ritz.  Scratch is a `mktemp -d` removed on exit, so two
# rooms on one host never share a file (AGAST #3183).

set -e

TEST_FILE=$1
if [ -z "$TEST_FILE" ]; then
  echo "Usage: $0 <test_file.ritz>"
  exit 1
fi

T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT

# Same entry point and link as ritz1/compile.sh (ritz0 --no-runtime output).
RUNTIME=runtime/ritz_start.x86_64.o
[ -f "$RUNTIME" ] || clang -c -o "$RUNTIME" runtime/ritz_start.x86_64.ll
link() { clang "$1" "$RUNTIME" -o "$2" -nostdlib; }

echo "🧪 A/B Testing: $TEST_FILE"
echo "================================"

# A: Compile with ritz0
echo "📦 A: Compiling with ritz0..."
python3 ritz0/ritz0.py "$TEST_FILE" -o "$T/test_a.ll" --no-runtime
link "$T/test_a.ll" "$T/test_a"
echo "✅ A binary ready"

# B: Compile ritz1 with ritz0, then compile test with ritz1
echo ""
echo "📦 B: Compiling ritz1 with ritz0..."
./ritz1/compile.sh "$T/ritz1" > /dev/null 2>&1
echo "✅ ritz1 compiler ready"

echo "📦 B: Compiling test with ritz1..."
"$T/ritz1" "$TEST_FILE" -o "$T/test_b.ll"
link "$T/test_b.ll" "$T/test_b"
echo "✅ B binary ready"

# Run both and compare
echo ""
echo "🏃 Running A (ritz0)..."
set +e  # Allow non-zero exit codes
"$T/test_a"
EXIT_A=$?
set -e  # Re-enable exit on error
echo "Exit code A: $EXIT_A"

echo ""
echo "🏃 Running B (ritz1)..."
set +e  # Allow non-zero exit codes
"$T/test_b"
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
