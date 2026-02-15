#!/bin/bash
# Bootstrap Testing Suite
# Tests ritz1 (compiled by ritz0) against all Tier 1 examples

set -e

echo "🎯 Bootstrap Testing Suite"
echo "======================================"
echo ""

PASSED=0
FAILED=0
SKIPPED=0

# Compile ritz1 once
echo "📦 Compiling ritz1 with ritz0..."
./ritz1/compile.sh > /dev/null 2>&1
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
  if ! python3 ritz0/ritz0.py "$file" -o /tmp/test_a.ll --no-runtime > /dev/null 2>&1; then
    echo "  ⚠️  SKIP: $name (ritz0 compile failed)"
    SKIPPED=$((SKIPPED + 1))
    return
  fi
  llc -filetype=obj /tmp/test_a.ll -o /tmp/test_a.o 2>&1 > /dev/null
  ld.lld --nostdlib /tmp/test_a.o ritz1/runtime/ritz_crt0.o -o /tmp/test_a -e _start 2>&1 > /dev/null

  # Path B: Compile with ritz1
  if ! /tmp/ritz1 "$file" -o /tmp/test_b.ll > /dev/null 2>&1; then
    echo "  ❌ FAIL: $name (ritz1 compile failed)"
    FAILED=$((FAILED + 1))
    return
  fi
  llc -filetype=obj /tmp/test_b.ll -o /tmp/test_b.o 2>&1 > /dev/null
  ld.lld --nostdlib /tmp/test_b.o ritz1/runtime/ritz_crt0.o -o /tmp/test_b -e _start 2>&1 > /dev/null

  # Run both
  set +e
  /tmp/test_a > /tmp/out_a.txt 2>&1
  EXIT_A=$?
  /tmp/test_b > /tmp/out_b.txt 2>&1
  EXIT_B=$?
  set -e

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

test_file "01_hello" "examples/01_hello/src/main.ritz"
test_file "02_exitcode" "examples/02_exitcode/src/main.ritz"
test_file "03_echo" "examples/03_echo/src/main.ritz"
test_file "04_true" "examples/04_true_false/src/true.ritz"
test_file "04_false" "examples/04_true_false/src/false.ritz"
test_file "05_cat" "examples/05_cat/src/main.ritz"
test_file "06_head" "examples/06_head/src/main.ritz"
test_file "07_wc" "examples/07_wc/src/main.ritz"
test_file "08_seq" "examples/08_seq/src/main.ritz"
test_file "09_yes" "examples/09_yes/src/main.ritz"
test_file "10_sleep" "examples/10_sleep/src/main.ritz"

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
