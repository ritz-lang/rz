#!/bin/bash
set -e

# Get the directory of the test script
DIR="$(cd "$(dirname "$0")" && pwd)"
MD="$DIR/md"

echo "Testing md..."

# Test 1: Heading
result=$(printf "# Hello\n" | $MD)
[ "$result" = "<h1>Hello</h1>" ] || { echo "FAIL: h1 heading"; exit 1; }

# Test 2: Multiple heading levels
result=$(printf "## Level 2\n" | $MD)
[ "$result" = "<h2>Level 2</h2>" ] || { echo "FAIL: h2 heading"; exit 1; }

# Test 3: Bold
result=$(printf "**bold**\n" | $MD)
echo "$result" | grep -q "<strong>bold</strong>" || { echo "FAIL: bold"; exit 1; }

# Test 4: Italic
result=$(printf "*italic*\n" | $MD)
echo "$result" | grep -q "<em>italic</em>" || { echo "FAIL: italic"; exit 1; }

# Test 5: Inline code
result=$(printf "\`code\`\n" | $MD)
echo "$result" | grep -q "<code>code</code>" || { echo "FAIL: inline code"; exit 1; }

# Test 6: Unordered list
result=$(printf -- "- Item 1\n- Item 2\n" | $MD)
echo "$result" | grep -q "<ul>" || { echo "FAIL: ul tag"; exit 1; }
echo "$result" | grep -q "<li>Item 1</li>" || { echo "FAIL: li tag"; exit 1; }

# Test 7: Ordered list
result=$(printf "1. First\n2. Second\n" | $MD)
echo "$result" | grep -q "<ol>" || { echo "FAIL: ol tag"; exit 1; }

# Test 8: Link
result=$(printf "[text](http://example.com)\n" | $MD)
echo "$result" | grep -q '<a href="http://example.com">text</a>' || { echo "FAIL: link"; exit 1; }

# Test 9: Code block
result=$(printf "\`\`\`\ncode\n\`\`\`\n" | $MD)
echo "$result" | grep -q "<pre><code>" || { echo "FAIL: code block"; exit 1; }

# Test 10: Horizontal rule
result=$(echo "---" | $MD)
[ "$result" = "<hr>" ] || { echo "FAIL: hr"; exit 1; }

# Test 11: Blockquote
result=$(printf "> Quote\n" | $MD)
echo "$result" | grep -q "<blockquote>" || { echo "FAIL: blockquote"; exit 1; }

# Test 12: Paragraph
result=$(printf "Line 1\n\nLine 2\n" | $MD)
echo "$result" | grep -c "<p>" | grep -q "2" || { echo "FAIL: paragraphs"; exit 1; }

# Test 13: HTML escaping
result=$(printf "<script>alert(1)</script>\n" | $MD)
echo "$result" | grep -q "&lt;script&gt;" || { echo "FAIL: html escape"; exit 1; }

echo "All md tests passed!"
