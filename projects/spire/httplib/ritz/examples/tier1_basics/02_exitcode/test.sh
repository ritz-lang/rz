#!/bin/bash
# Test exitcode: should exit with code 42
./exitcode
test $? -eq 42
