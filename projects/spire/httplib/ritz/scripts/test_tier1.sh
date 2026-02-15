#!/bin/bash
# Test all Tier 1 examples with ritz1

echo "🧪 Testing all Tier 1 examples with ritz1"
echo "========================================"
echo ""

declare -a TESTS=(
  "examples/02_exitcode/src/main.ritz"
  "examples/04_true_false/src/true.ritz"
  "examples/04_true_false/src/false.ritz"
)

PASS=0
FAIL=0

for test in "${TESTS[@]}"; do
  name=$(basename $(dirname $(dirname $test)))
  printf "%-20s " "$name:"

  if ./scripts/ab_test.sh "$test" > /dev/null 2>&1; then
    echo "✅ PASS"
    ((PASS++))
  else
    echo "❌ FAIL"
    ((FAIL++))
  fi
done

echo ""
echo "========================================"
echo "Results: $PASS passed, $FAIL failed"
