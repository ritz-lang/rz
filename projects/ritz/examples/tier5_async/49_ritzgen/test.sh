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
echo "Test 2: Lexing simple file..."
./ritzgen grammars/ritz.grammar ../01_hello/src/main.ritz > /dev/null 2>&1
echo "  OK: 01_hello lexed successfully"

# Test 3: Lex all example files (spot check a few)
echo "Test 3: Lexing example files..."
for dir in ../01_hello ../10_structs ../20_bytevec ../30_arena; do
    if [ -d "$dir/src" ]; then
        for f in "$dir"/src/*.ritz; do
            OUTPUT=$(./ritzgen grammars/ritz.grammar "$f" 2>&1)
            if echo "$OUTPUT" | grep -q "error:"; then
                echo "FAIL: Error lexing $f"
                echo "$OUTPUT"
                exit 1
            fi
        done
        echo "  OK: $dir lexed successfully"
    fi
done

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
