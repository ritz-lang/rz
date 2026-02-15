#!/bin/bash
# Test true: exits 0
./true || exit 1

# Test false: exits 1
./false
test $? -eq 1
