#!/bin/bash
set -e
# Scratch from mktemp -d, removed only by this trap: gates share /tmp
# (AGAST #3178), so a fixed /tmp name is shared with every other gate.
T=$(mktemp -d) || exit 1
trap 'rm -rf "$T"' EXIT

# Get the directory of the test script
DIR="$(cd "$(dirname "$0")" && pwd)"
TOML="$DIR/toml"

echo "Testing toml..."

# Test 1: Simple key-value
echo 'name = "test"
version = "1.0"' | $TOML > "$T"/toml_out.txt
grep -q 'name = "test"' "$T"/toml_out.txt || { echo "FAIL: simple key-value"; exit 1; }

# Test 2: Get specific key
echo 'name = "myapp"
version = "2.0"' | $TOML -g name > "$T"/toml_out.txt
grep -q 'myapp' "$T"/toml_out.txt || { echo "FAIL: get key"; exit 1; }

# Test 3: Section
echo '[package]
name = "test"' | $TOML > "$T"/toml_out.txt
grep -q 'package.name' "$T"/toml_out.txt || { echo "FAIL: section"; exit 1; }

# Test 4: Get nested key
echo '[package]
name = "nested"' | $TOML -g package.name > "$T"/toml_out.txt
grep -q 'nested' "$T"/toml_out.txt || { echo "FAIL: get nested key"; exit 1; }

# Test 5: List keys
echo 'a = 1
b = 2
c = 3' | $TOML -k > "$T"/toml_out.txt
test $(wc -l < "$T"/toml_out.txt) -eq 3 || { echo "FAIL: list keys"; exit 1; }

# Test 6: Validate only
echo 'valid = true' | $TOML -v > "$T"/toml_out.txt
test ! -s "$T"/toml_out.txt || { echo "FAIL: validate only"; exit 1; }

# Test 7: Numbers
echo 'int = 42
float = 3.14' | $TOML > "$T"/toml_out.txt
grep -q '42' "$T"/toml_out.txt || { echo "FAIL: numbers"; exit 1; }

# Test 8: Boolean
echo 'enabled = true
disabled = false' | $TOML > "$T"/toml_out.txt
grep -q 'true' "$T"/toml_out.txt || { echo "FAIL: boolean"; exit 1; }

# Test 9: Comments
echo '# This is a comment
key = "value"  # inline comment' | $TOML > "$T"/toml_out.txt
grep -q 'key = "value"' "$T"/toml_out.txt || { echo "FAIL: comments"; exit 1; }

# Test 10: Multiple sections
echo '[server]
host = "localhost"
[database]
name = "mydb"' | $TOML -k > "$T"/toml_out.txt
grep -q 'server.host' "$T"/toml_out.txt || { echo "FAIL: multiple sections"; exit 1; }
grep -q 'database.name' "$T"/toml_out.txt || { echo "FAIL: multiple sections (2)"; exit 1; }

echo "All toml tests passed!"
