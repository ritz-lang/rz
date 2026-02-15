#!/bin/bash
set -e

# Get the directory of the test script
DIR="$(cd "$(dirname "$0")" && pwd)"
CSV="$DIR/csv"

echo "Testing csv..."

# Test 1: Simple CSV
echo 'a,b,c
1,2,3
4,5,6' | $CSV > /tmp/csv_out.txt
grep -q '1' /tmp/csv_out.txt || { echo "FAIL: simple csv"; exit 1; }

# Test 2: Field selection
echo 'a,b,c,d
1,2,3,4
5,6,7,8' | $CSV -f 1,3 > /tmp/csv_out.txt
grep -q '1' /tmp/csv_out.txt || { echo "FAIL: field selection"; exit 1; }
grep -q '3' /tmp/csv_out.txt || { echo "FAIL: field selection (field 3)"; exit 1; }

# Test 3: Header mode
echo 'name,age,city
Alice,30,NYC
Bob,25,LA' | $CSV -H > /tmp/csv_out.txt
grep -q 'name=' /tmp/csv_out.txt || { echo "FAIL: header mode"; exit 1; }

# Test 4: TSV mode
printf 'a\tb\tc\n1\t2\t3\n' | $CSV -t > /tmp/csv_out.txt
grep -q '1' /tmp/csv_out.txt || { echo "FAIL: tsv mode"; exit 1; }

# Test 5: Quoted fields
echo '"hello, world",simple,"with ""quotes"""' | $CSV > /tmp/csv_out.txt
grep -q 'hello, world' /tmp/csv_out.txt || { echo "FAIL: quoted fields"; exit 1; }

# Test 6: Custom delimiter
echo 'a;b;c
1;2;3' | $CSV -d ';' > /tmp/csv_out.txt
grep -q '1' /tmp/csv_out.txt || { echo "FAIL: custom delimiter"; exit 1; }

rm -f /tmp/csv_out.txt
echo "All csv tests passed!"
