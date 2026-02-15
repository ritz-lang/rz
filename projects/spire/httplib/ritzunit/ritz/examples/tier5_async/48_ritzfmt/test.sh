#!/bin/bash
set -e

# Get the directory of the test script
DIR="$(cd "$(dirname "$0")" && pwd)"
FMT="$DIR/ritzfmt"

echo "Testing ritzfmt..."

# Test 1: Trailing whitespace removal
result=$(printf "fn foo()   \n    return 0  \n" | $FMT)
echo "$result" | grep -q "fn foo()$" || { echo "FAIL: trailing ws"; exit 1; }

# Test 2: Normalize multiple blank lines
result=$(printf "fn foo()\n\n\n\n    x\n" | $FMT)
lines=$(echo "$result" | wc -l)
[ "$lines" -le "4" ] || { echo "FAIL: blank lines"; exit 1; }

# Test 3: Ensure newline at end
result=$(printf "fn foo()" | $FMT | xxd | tail -1)
echo "$result" | grep -q "0a" || { echo "FAIL: trailing newline"; exit 1; }

# Test 4: Preserve comments
result=$(printf "# comment\nfn foo()\n" | $FMT)
echo "$result" | grep -q "# comment" || { echo "FAIL: preserve comment"; exit 1; }

# Test 5: Preserve strings
result=$(printf 'let s: *u8 = "hello world"\n' | $FMT)
echo "$result" | grep -q '"hello world"' || { echo "FAIL: preserve string"; exit 1; }

# Test 6: Check mode - already formatted
printf "fn foo()\n    return 0\n" > /tmp/fmt_test.ritz
$FMT -c /tmp/fmt_test.ritz || { echo "FAIL: check formatted"; exit 1; }

# Test 7: Check mode - needs formatting
printf "fn foo()   \n    return 0\n" > /tmp/fmt_test.ritz
! $FMT -c /tmp/fmt_test.ritz 2>/dev/null || { echo "FAIL: check unformatted"; exit 1; }

# Test 8: Write mode
printf "fn foo()   \n" > /tmp/fmt_test.ritz
$FMT -w /tmp/fmt_test.ritz
result=$(cat /tmp/fmt_test.ritz)
echo "$result" | grep -q "fn foo()$" || { echo "FAIL: write mode"; exit 1; }

# Test 9: Custom indent width - 2 space indents
result=$(printf "fn foo()\n  x\n" | $FMT -i 2)
echo "$result" | grep -q "^  x" || { echo "FAIL: custom indent"; exit 1; }

rm -f /tmp/fmt_test.ritz
echo "All ritzfmt tests passed!"
