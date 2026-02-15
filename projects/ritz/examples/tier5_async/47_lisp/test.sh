#!/bin/bash
set -e

# Get the directory of the test script
DIR="$(cd "$(dirname "$0")" && pwd)"
LISP="$DIR/lisp"

echo "Testing lisp..."

# Test 1: Simple addition
result=$(echo "(+ 1 2)" | $LISP)
test "$result" = "3" || { echo "FAIL: (+ 1 2) = $result, expected 3"; exit 1; }

# Test 2: Subtraction
result=$(echo "(- 10 4)" | $LISP)
test "$result" = "6" || { echo "FAIL: (- 10 4) = $result, expected 6"; exit 1; }

# Test 3: Multiplication
result=$(echo "(* 3 4)" | $LISP)
test "$result" = "12" || { echo "FAIL: (* 3 4) = $result, expected 12"; exit 1; }

# Test 4: Division
result=$(echo "(/ 15 3)" | $LISP)
test "$result" = "5" || { echo "FAIL: (/ 15 3) = $result, expected 5"; exit 1; }

# Test 5: Nested expressions
result=$(echo "(+ (* 2 3) (- 10 5))" | $LISP)
test "$result" = "11" || { echo "FAIL: nested = $result, expected 11"; exit 1; }

# Test 6: Comparison
result=$(echo "(< 1 2)" | $LISP)
test "$result" = "#t" || { echo "FAIL: (< 1 2) = $result, expected #t"; exit 1; }

# Test 7: Equality
result=$(echo "(= 5 5)" | $LISP)
test "$result" = "#t" || { echo "FAIL: (= 5 5) = $result, expected #t"; exit 1; }

# Test 8: Quote
result=$(echo "'(1 2 3)" | $LISP)
test "$result" = "(1 2 3)" || { echo "FAIL: quote = $result, expected (1 2 3)"; exit 1; }

# Test 9: If true
result=$(echo "(if (> 5 3) 1 2)" | $LISP)
test "$result" = "1" || { echo "FAIL: if true = $result, expected 1"; exit 1; }

# Test 10: If false
result=$(echo "(if (< 5 3) 1 2)" | $LISP)
test "$result" = "2" || { echo "FAIL: if false = $result, expected 2"; exit 1; }

# Test 11: Define and use
result=$(echo "(define x 42)
x" | $LISP | tail -1)
test "$result" = "42" || { echo "FAIL: define = $result, expected 42"; exit 1; }

# Test 12: Car
result=$(echo "(car '(1 2 3))" | $LISP)
test "$result" = "1" || { echo "FAIL: car = $result, expected 1"; exit 1; }

# Test 13: Cdr
result=$(echo "(cdr '(1 2 3))" | $LISP)
test "$result" = "(2 3)" || { echo "FAIL: cdr = $result, expected (2 3)"; exit 1; }

# Test 14: Cons
result=$(echo "(cons 1 '(2 3))" | $LISP)
test "$result" = "(1 2 3)" || { echo "FAIL: cons = $result, expected (1 2 3)"; exit 1; }

# Test 15: null?
result=$(echo "(null? '())" | $LISP)
test "$result" = "#t" || { echo "FAIL: null? = $result, expected #t"; exit 1; }

echo "All lisp tests passed!"
