#!/bin/bash
set -e

# Get the directory of the test script
DIR="$(cd "$(dirname "$0")" && pwd)"
REGEX="$DIR/regex"

echo "Testing regex..."

# Test 1: Simple literal
result=$(echo -e "hello\nworld" | $REGEX 'hello')
[ "$result" = "hello" ] || { echo "FAIL: literal match"; exit 1; }

# Test 2: Dot matches any
result=$(echo -e "cat\ncar\ncan" | $REGEX 'ca.')
[ "$(echo "$result" | wc -l)" = "3" ] || { echo "FAIL: dot match"; exit 1; }

# Test 3: Character class
result=$(echo -e "a1\nb2\nc3" | $REGEX '[0-9]')
[ "$(echo "$result" | wc -l)" = "3" ] || { echo "FAIL: character class"; exit 1; }

# Test 4: Negated character class
result=$(echo -e "abc\n123\nxyz" | $REGEX '[^0-9]+')
[ "$(echo "$result" | wc -l)" = "2" ] || { echo "FAIL: negated class"; exit 1; }

# Test 5: Start anchor
result=$(echo -e "#comment\n code\n#another" | $REGEX '^#')
[ "$(echo "$result" | wc -l)" = "2" ] || { echo "FAIL: start anchor"; exit 1; }

# Test 6: End anchor
result=$(echo -e "hello.\nworld\ntest." | $REGEX '\.$')
[ "$(echo "$result" | wc -l)" = "2" ] || { echo "FAIL: end anchor"; exit 1; }

# Test 7: Plus quantifier (one or more)
result=$(echo -e "123\nabc\n456def" | $REGEX '[0-9]+')
[ "$(echo "$result" | wc -l)" = "2" ] || { echo "FAIL: plus quantifier"; exit 1; }

# Test 8: Star quantifier (zero or more)
result=$(echo -e "ac\nabc\nabbc" | $REGEX 'ab*c')
[ "$(echo "$result" | wc -l)" = "3" ] || { echo "FAIL: star quantifier"; exit 1; }

# Test 9: Question mark (zero or one)
result=$(echo -e "color\ncolour\ncolouur" | $REGEX 'colou?r')
[ "$(echo "$result" | wc -l)" = "2" ] || { echo "FAIL: question mark"; exit 1; }

# Test 10: Escape sequences
result=$(echo -e "abc\n123\na1b" | $REGEX '\d')
[ "$(echo "$result" | wc -l)" = "2" ] || { echo "FAIL: digit escape"; exit 1; }

# Test 11: Word chars
result=$(echo -e "hello_world\nhello world\nhello-world" | $REGEX '^\w+$')
[ "$result" = "hello_world" ] || { echo "FAIL: word escape"; exit 1; }

# Test 12: Range in character class
result=$(echo -e "abc\nABC\n123" | $REGEX '[a-z]+')
[ "$result" = "abc" ] || { echo "FAIL: range"; exit 1; }

echo "All regex tests passed!"
