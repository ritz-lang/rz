#!/bin/bash
set -e

# Get the directory of the test script
DIR="$(cd "$(dirname "$0")" && pwd)"
TOML="$DIR/toml"

echo "Testing toml..."

# Test 1: Simple key-value
echo 'name = "test"
version = "1.0"' | $TOML > /tmp/toml_out.txt
grep -q 'name = "test"' /tmp/toml_out.txt || { echo "FAIL: simple key-value"; exit 1; }

# Test 2: Get specific key
echo 'name = "myapp"
version = "2.0"' | $TOML -g name > /tmp/toml_out.txt
grep -q 'myapp' /tmp/toml_out.txt || { echo "FAIL: get key"; exit 1; }

# Test 3: Section
echo '[package]
name = "test"' | $TOML > /tmp/toml_out.txt
grep -q 'package.name' /tmp/toml_out.txt || { echo "FAIL: section"; exit 1; }

# Test 4: Get nested key
echo '[package]
name = "nested"' | $TOML -g package.name > /tmp/toml_out.txt
grep -q 'nested' /tmp/toml_out.txt || { echo "FAIL: get nested key"; exit 1; }

# Test 5: List keys
echo 'a = 1
b = 2
c = 3' | $TOML -k > /tmp/toml_out.txt
test $(wc -l < /tmp/toml_out.txt) -eq 3 || { echo "FAIL: list keys"; exit 1; }

# Test 6: Validate only
echo 'valid = true' | $TOML -v > /tmp/toml_out.txt
test ! -s /tmp/toml_out.txt || { echo "FAIL: validate only"; exit 1; }

# Test 7: Numbers
echo 'int = 42
float = 3.14' | $TOML > /tmp/toml_out.txt
grep -q '42' /tmp/toml_out.txt || { echo "FAIL: numbers"; exit 1; }

# Test 8: Boolean
echo 'enabled = true
disabled = false' | $TOML > /tmp/toml_out.txt
grep -q 'true' /tmp/toml_out.txt || { echo "FAIL: boolean"; exit 1; }

# Test 9: Comments
echo '# This is a comment
key = "value"  # inline comment' | $TOML > /tmp/toml_out.txt
grep -q 'key = "value"' /tmp/toml_out.txt || { echo "FAIL: comments"; exit 1; }

# Test 10: Multiple sections
echo '[server]
host = "localhost"
[database]
name = "mydb"' | $TOML -k > /tmp/toml_out.txt
grep -q 'server.host' /tmp/toml_out.txt || { echo "FAIL: multiple sections"; exit 1; }
grep -q 'database.name' /tmp/toml_out.txt || { echo "FAIL: multiple sections (2)"; exit 1; }

rm -f /tmp/toml_out.txt
echo "All toml tests passed!"
