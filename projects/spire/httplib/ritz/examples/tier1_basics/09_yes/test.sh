#!/bin/bash
# Test yes

# Test default "y" - take first 5 lines
result=$(./yes | head -5)
expected="y
y
y
y
y"
test "$result" = "$expected" || { echo "Failed: yes default"; exit 1; }

# Test with argument
result=$(./yes hello | head -3)
expected="hello
hello
hello"
test "$result" = "$expected" || { echo "Failed: yes hello"; exit 1; }
