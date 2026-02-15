#!/bin/bash
# Test env: should print environment variables
# Compare first 5 lines of env output with system env
./env | head -5 > /tmp/ritz_env.out
env | head -5 > /tmp/sys_env.out
diff -q /tmp/ritz_env.out /tmp/sys_env.out
