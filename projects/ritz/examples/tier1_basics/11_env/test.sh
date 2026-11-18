#!/bin/bash
# Test env: prints the environment it was given, then one variable by name
test "$(env -i GREETING=hi FOO=1 ./env)" = "GREETING=hi
FOO=1
greeting: hi"
