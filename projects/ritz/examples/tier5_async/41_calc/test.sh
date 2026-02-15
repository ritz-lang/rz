#!/bin/bash
# Test calc: expression evaluator

# Test basic arithmetic
[ "$(./calc '2 + 3')" = "5" ] || { echo "FAIL: 2+3"; exit 1; }
[ "$(./calc '10 - 4')" = "6" ] || { echo "FAIL: 10-4"; exit 1; }
[ "$(./calc '3 * 7')" = "21" ] || { echo "FAIL: 3*7"; exit 1; }
[ "$(./calc '20 / 4')" = "5" ] || { echo "FAIL: 20/4"; exit 1; }
[ "$(./calc '17 % 5')" = "2" ] || { echo "FAIL: 17%5"; exit 1; }

# Test precedence
[ "$(./calc '2 + 3 * 4')" = "14" ] || { echo "FAIL: precedence"; exit 1; }
[ "$(./calc '10 - 2 * 3')" = "4" ] || { echo "FAIL: precedence 2"; exit 1; }

# Test parentheses
[ "$(./calc '(2 + 3) * 4')" = "20" ] || { echo "FAIL: parens"; exit 1; }
[ "$(./calc '((1 + 2) * (3 + 4))')" = "21" ] || { echo "FAIL: nested parens"; exit 1; }

# Test unary minus (use -- to stop option parsing)
[ "$(./calc -- '-5')" = "-5" ] || { echo "FAIL: unary minus"; exit 1; }
[ "$(./calc -- '3 * -2')" = "-6" ] || { echo "FAIL: unary in expr"; exit 1; }

# Test larger numbers
[ "$(./calc '1000 + 2000')" = "3000" ] || { echo "FAIL: large nums"; exit 1; }

echo "All calc tests passed!"
