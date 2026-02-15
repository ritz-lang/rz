#!/bin/bash
set -e

# Get the directory of the test script
DIR="$(cd "$(dirname "$0")" && pwd)"
JSON="$DIR/json"

echo "Testing json..."

# Test 1: Simple object
echo '{"name":"test"}' | $JSON > /tmp/json_out.txt
grep -q '"name"' /tmp/json_out.txt || { echo "FAIL: simple object"; exit 1; }

# Test 2: Array
echo '[1, 2, 3]' | $JSON > /tmp/json_out.txt
grep -q '\[' /tmp/json_out.txt || { echo "FAIL: array"; exit 1; }

# Test 3: Nested structure
echo '{"arr":[1,2],"obj":{"a":1}}' | $JSON > /tmp/json_out.txt
grep -q '"arr"' /tmp/json_out.txt || { echo "FAIL: nested"; exit 1; }

# Test 4: Boolean and null
echo '{"flag":true,"empty":null}' | $JSON > /tmp/json_out.txt
grep -q 'true' /tmp/json_out.txt || { echo "FAIL: boolean/null"; exit 1; }

# Test 5: Compact output
echo '{"a": 1}' | $JSON -c > /tmp/json_out.txt
# Compact should not have extra newlines in the value
grep -q '{"a":1}' /tmp/json_out.txt || { echo "FAIL: compact"; exit 1; }

# Test 6: Validate only (no output)
echo '{"valid":true}' | $JSON -v > /tmp/json_out.txt
test ! -s /tmp/json_out.txt || { echo "FAIL: validate only"; exit 1; }

# Test 7: Invalid JSON should fail
if echo '{invalid}' | $JSON 2>/dev/null; then
    echo "FAIL: should reject invalid JSON"
    exit 1
fi

# Test 8: Numbers
echo '{"int":42,"neg":-17,"float":3.14,"exp":1e10}' | $JSON > /tmp/json_out.txt
grep -q '42' /tmp/json_out.txt || { echo "FAIL: numbers"; exit 1; }

# Test 9: String escapes (JSON escape sequences are preserved)
echo '{"msg":"hello\\nworld"}' | $JSON > /tmp/json_out.txt
grep -q 'hello' /tmp/json_out.txt || { echo "FAIL: escapes"; exit 1; }

# Test 10: Empty structures
echo '{"empty_obj":{},"empty_arr":[]}' | $JSON > /tmp/json_out.txt
grep -q '{}' /tmp/json_out.txt || { echo "FAIL: empty structures"; exit 1; }

rm -f /tmp/json_out.txt
echo "All json tests passed!"
