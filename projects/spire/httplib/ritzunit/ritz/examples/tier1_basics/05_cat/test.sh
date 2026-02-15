#!/bin/bash
# Test cat: read from file
echo "test content" > /tmp/ritz_test_cat.txt
./cat /tmp/ritz_test_cat.txt | grep -q "test content" || exit 1

# Test cat: read from stdin
echo "stdin test" | ./cat | grep -q "stdin test" || exit 1

rm -f /tmp/ritz_test_cat.txt
