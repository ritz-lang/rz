#!/bin/bash
# Test ritzgen by lexing all example files

set -e

cd "$(dirname "$0")"

# Test 1: Verify grammar loads correctly
echo "Test 1: Loading grammar..."
OUTPUT=$(./ritzgen grammars/ritz.grammar 2>&1)
if ! echo "$OUTPUT" | grep -q "Loaded 90 token definitions"; then
    echo "FAIL: Expected 90 token definitions"
    echo "$OUTPUT"
    exit 1
fi
if ! echo "$OUTPUT" | grep -q "Parsed 64 grammar rules"; then
    echo "FAIL: Expected 64 grammar rules"
    echo "$OUTPUT"
    exit 1
fi
echo "  OK: Grammar loaded (90 tokens, 64 rules)"

# Test 2: Lex a simple file
# Paths below are relative to examples/tier5_async/49_ritzgen.
#
# They used to be ../01_hello, ../10_structs, ../20_bytevec, ../30_arena --
# from a flat examples/ layout that no longer exists.  01_hello moved to
# tier1_basics/ and the other three are simply gone.  The consequences were
# different for each test and both were bad:
#
#   Test 2 hard-failed on a missing file (`set -e`), and the message it printed
#          was "OK: 01_hello lexed successfully" -- for a file that isn't there.
#   Test 3 guarded on `[ -d "$dir/src" ]`, so all four misses were skipped and
#          the loop asserted nothing while still printing its way to success.
#
# Neither was ever noticed because regression.sh's example allowlist meant this
# test.sh had not been executed in CI at all (AGAST #1359).
HELLO=../../tier1_basics/01_hello

echo "Test 2: Lexing simple file..."
./ritzgen grammars/ritz.grammar "$HELLO/src/main.ritz" > /dev/null 2>&1
echo "  OK: 01_hello lexed successfully"

# Test 3: Lex all example files (spot check a few)
echo "Test 3: Lexing example files..."
LEXED=0
for dir in "$HELLO" ../../tier1_basics/07_wc ../../tier2_stdlib/13_sort ../../tier3_coreutils/21_ls; do
    # A missing directory is now a FAILURE, not a silent skip.  The whole point
    # of this test is that it lexed real Ritz sources; a run that lexed none of
    # them must not report success.
    if [ ! -d "$dir/src" ]; then
        echo "FAIL: fixture directory $dir/src does not exist"
        exit 1
    fi
    for f in "$dir"/src/*.ritz; do
        OUTPUT=$(./ritzgen grammars/ritz.grammar "$f" 2>&1)
        if echo "$OUTPUT" | grep -q "error:"; then
            echo "FAIL: Error lexing $f"
            echo "$OUTPUT"
            exit 1
        fi
        LEXED=$((LEXED + 1))
    done
    echo "  OK: $dir lexed successfully"
done
if [ "$LEXED" -lt 4 ]; then
    echo "FAIL: expected to lex at least 4 sources, lexed $LEXED"
    exit 1
fi
echo "  ($LEXED sources lexed)"

# Test 4: Generate parser code
echo "Test 4: Generating parser code..."
OUTPUT=$(./ritzgen -g grammars/ritz.grammar 2>&1)
if ! echo "$OUTPUT" | grep -q "fn parse_module"; then
    echo "FAIL: Expected parse_module function in generated code"
    exit 1
fi
if ! echo "$OUTPUT" | grep -q "fn parse(tokens: \*Token"; then
    echo "FAIL: Expected parse entry point in generated code"
    exit 1
fi
echo "  OK: Parser code generated"

echo "All tests passed!"
