#!/bin/bash
# Bootstrap Testing Suite
# Tests ritz1 (compiled by ritz0) against all Tier 1 examples

set -e

# Run from projects/ritz.  Scratch is a `mktemp -d` removed on exit, so two
# rooms on one host never share a file (AGAST #3183).
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT

# Same entry point and link as ritz1/compile.sh (ritz0 --no-runtime output).
RUNTIME=runtime/ritz_start.x86_64.o
[ -f "$RUNTIME" ] || clang -c -o "$RUNTIME" runtime/ritz_start.x86_64.ll
link() { clang "$1" "$RUNTIME" -o "$2" -nostdlib > /dev/null 2>&1; }

# Run a binary with no stdin, for at most 5s, keeping 64K of output (09_yes
# never stops on its own).  Echoes the exit code.
run() {
  timeout 5 "$1" < /dev/null 2>&1 | head -c 65536 > "$2"
  echo "${PIPESTATUS[0]}"
}

echo "🎯 Bootstrap Testing Suite"
echo "======================================"
echo ""

PASSED=0
FAILED=0
SKIPPED=0

# Compile ritz1 once
echo "📦 Compiling ritz1 with ritz0..."
./ritz1/compile.sh "$T/ritz1" > /dev/null 2>&1
echo "✅ ritz1 compiler ready"
echo ""

# Test a single source file
test_file() {
  local name=$1
  local file=$2

  if [ ! -f "$file" ]; then
    echo "  ⚠️  SKIP: $name (file not found)"
    SKIPPED=$((SKIPPED + 1))
    return
  fi

  # Path A: Compile with ritz0
  if ! python3 ritz0/ritz0.py "$file" -o "$T/test_a.ll" --no-runtime > /dev/null 2>&1; then
    echo "  ⚠️  SKIP: $name (ritz0 compile failed)"
    SKIPPED=$((SKIPPED + 1))
    return
  fi
  # One file, no imports linked: an example that imports ritzlib can't link.
  if ! link "$T/test_a.ll" "$T/test_a"; then
    echo "  ⚠️  SKIP: $name (link failed: single-file compile, imports not linked)"
    SKIPPED=$((SKIPPED + 1))
    return
  fi

  # Path B: Compile with ritz1
  if ! "$T/ritz1" "$file" -o "$T/test_b.ll" > /dev/null 2>&1; then
    echo "  ❌ FAIL: $name (ritz1 compile failed)"
    FAILED=$((FAILED + 1))
    return
  fi
  if ! link "$T/test_b.ll" "$T/test_b"; then
    echo "  ❌ FAIL: $name (ritz1 output does not link; ritz0's did)"
    FAILED=$((FAILED + 1))
    return
  fi

  # Run both
  EXIT_A=$(run "$T/test_a" "$T/out_a.txt")
  EXIT_B=$(run "$T/test_b" "$T/out_b.txt")

  # Compare
  if [ $EXIT_A -eq $EXIT_B ]; then
    echo "  ✅ PASS: $name (exit: $EXIT_A)"
    PASSED=$((PASSED + 1))
  else
    echo "  ❌ FAIL: $name (A: $EXIT_A, B: $EXIT_B)"
    FAILED=$((FAILED + 1))
  fi
}

# Tier 1 examples
echo "🧪 Testing Tier 1 Examples"
echo "--------------------------------------"

test_file "01_hello" "examples/tier1_basics/01_hello/src/main.ritz"
test_file "02_exitcode" "examples/tier1_basics/02_exitcode/src/main.ritz"
test_file "03_echo" "examples/tier1_basics/03_echo/src/main.ritz"
test_file "04_true" "examples/tier1_basics/04_true_false/src/true.ritz"
test_file "04_false" "examples/tier1_basics/04_true_false/src/false.ritz"
test_file "05_cat" "examples/tier1_basics/05_cat/src/main.ritz"
test_file "06_head" "examples/tier1_basics/06_head/src/main.ritz"
test_file "07_wc" "examples/tier1_basics/07_wc/src/main.ritz"
test_file "08_seq" "examples/tier1_basics/08_seq/src/main.ritz"
test_file "09_yes" "examples/tier1_basics/09_yes/src/main.ritz"
test_file "10_sleep" "examples/tier1_basics/10_sleep/src/main.ritz"

echo ""
echo "======================================"
echo "📊 Results:"
echo "  ✅ Passed:  $PASSED"
echo "  ❌ Failed:  $FAILED"
echo "  ⚠️  Skipped: $SKIPPED"
echo ""

if [ $FAILED -eq 0 ]; then
  echo "🎉 All tests passed!"
  exit 0
else
  echo "💥 Some tests failed"
  exit 1
fi
