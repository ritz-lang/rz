#!/bin/bash
set -e
# Scratch from mktemp -d, removed only by this trap: gates share /tmp
# (AGAST #3178), so a fixed /tmp name is shared with every other gate.
T=$(mktemp -d) || exit 1
trap 'rm -rf "$T"' EXIT

# Get the directory of the test script
DIR="$(cd "$(dirname "$0")" && pwd)"
JSON="$DIR/json"

echo "Testing json..."

# Test 1: Simple object
echo '{"name":"test"}' | $JSON > "$T"/json_out.txt
grep -q '"name"' "$T"/json_out.txt || { echo "FAIL: simple object"; exit 1; }

# Test 2: Array
echo '[1, 2, 3]' | $JSON > "$T"/json_out.txt
grep -q '\[' "$T"/json_out.txt || { echo "FAIL: array"; exit 1; }

# Test 3: Nested structure
echo '{"arr":[1,2],"obj":{"a":1}}' | $JSON > "$T"/json_out.txt
grep -q '"arr"' "$T"/json_out.txt || { echo "FAIL: nested"; exit 1; }

# Test 4: Boolean and null
echo '{"flag":true,"empty":null}' | $JSON > "$T"/json_out.txt
grep -q 'true' "$T"/json_out.txt || { echo "FAIL: boolean/null"; exit 1; }

# Test 5: Compact output
echo '{"a": 1}' | $JSON -c > "$T"/json_out.txt
# Compact should not have extra newlines in the value
grep -q '{"a":1}' "$T"/json_out.txt || { echo "FAIL: compact"; exit 1; }

# Test 6: Validate only (no output)
echo '{"valid":true}' | $JSON -v > "$T"/json_out.txt
test ! -s "$T"/json_out.txt || { echo "FAIL: validate only"; exit 1; }

# Test 7: Invalid JSON should fail
if echo '{invalid}' | $JSON 2>/dev/null; then
    echo "FAIL: should reject invalid JSON"
    exit 1
fi

# Test 8: Numbers
echo '{"int":42,"neg":-17,"float":3.14,"exp":1e10}' | $JSON > "$T"/json_out.txt
grep -q '42' "$T"/json_out.txt || { echo "FAIL: numbers"; exit 1; }

# Test 9: String escapes (JSON escape sequences are preserved)
echo '{"msg":"hello\\nworld"}' | $JSON > "$T"/json_out.txt
grep -q 'hello' "$T"/json_out.txt || { echo "FAIL: escapes"; exit 1; }

# Test 10: Empty structures
echo '{"empty_obj":{},"empty_arr":[]}' | $JSON > "$T"/json_out.txt
grep -q '{}' "$T"/json_out.txt || { echo "FAIL: empty structures"; exit 1; }

echo "All json tests passed!"
