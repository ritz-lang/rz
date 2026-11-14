#!/bin/bash
# Test env: should print environment variables
# Compare first 5 lines of env output with system env
# Scratch from mktemp -d, removed only by this trap: gates share /tmp
# (AGAST #3178), so a fixed /tmp name is shared with every other gate.
T=$(mktemp -d) || exit 1
trap 'rm -rf "$T"' EXIT

./env | head -5 > "$T"/ritz_env.out
env | head -5 > "$T"/sys_env.out
diff -q "$T"/ritz_env.out "$T"/sys_env.out
