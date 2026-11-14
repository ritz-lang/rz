#!/bin/bash
set -e
# Scratch from mktemp -d, removed only by this trap: gates share /tmp
# (AGAST #3178), so a fixed /tmp name is shared with every other gate.
T=$(mktemp -d) || exit 1
trap 'rm -rf "$T"' EXIT

# Get the directory of the test script
DIR="$(cd "$(dirname "$0")" && pwd)"
CSV="$DIR/csv"

echo "Testing csv..."

# Test 1: Simple CSV
echo 'a,b,c
1,2,3
4,5,6' | $CSV > "$T"/csv_out.txt
grep -q '1' "$T"/csv_out.txt || { echo "FAIL: simple csv"; exit 1; }

# Test 2: Field selection
echo 'a,b,c,d
1,2,3,4
5,6,7,8' | $CSV -f 1,3 > "$T"/csv_out.txt
grep -q '1' "$T"/csv_out.txt || { echo "FAIL: field selection"; exit 1; }
grep -q '3' "$T"/csv_out.txt || { echo "FAIL: field selection (field 3)"; exit 1; }

# Test 3: Header mode
echo 'name,age,city
Alice,30,NYC
Bob,25,LA' | $CSV -H > "$T"/csv_out.txt
grep -q 'name=' "$T"/csv_out.txt || { echo "FAIL: header mode"; exit 1; }

# Test 4: TSV mode
printf 'a\tb\tc\n1\t2\t3\n' | $CSV -t > "$T"/csv_out.txt
grep -q '1' "$T"/csv_out.txt || { echo "FAIL: tsv mode"; exit 1; }

# Test 5: Quoted fields
echo '"hello, world",simple,"with ""quotes"""' | $CSV > "$T"/csv_out.txt
grep -q 'hello, world' "$T"/csv_out.txt || { echo "FAIL: quoted fields"; exit 1; }

# Test 6: Custom delimiter
echo 'a;b;c
1;2;3' | $CSV -d ';' > "$T"/csv_out.txt
grep -q '1' "$T"/csv_out.txt || { echo "FAIL: custom delimiter"; exit 1; }

echo "All csv tests passed!"
