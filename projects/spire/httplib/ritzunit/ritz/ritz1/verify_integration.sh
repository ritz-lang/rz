#!/bin/bash
echo "=== RITZ1 TOKEN & PARSER INTEGRATION VERIFICATION ==="
echo ""

echo "1. Token Definitions Check:"
LEXER_TOKENS=$(grep "^const TOK_" src/tokens.ritz | wc -l)
PARSER_TOKENS=$(grep "^const TOK_" src/parser_gen.ritz | wc -l)
echo "   - tokens.ritz: $LEXER_TOKENS token definitions"
echo "   - parser_gen.ritz: $PARSER_TOKENS token definitions"
echo ""

echo "2. Critical Token ID Alignment:"
echo "   Checking FN, VAR, RETURN token IDs match:"
grep "TOK_FN: i32\|TOK_VAR: i32\|TOK_RETURN: i32" src/tokens.ritz | grep -v "//"
echo "   Generated parser uses same IDs (from parser_gen.ritz):"
grep "const TOK_FN:\|const TOK_VAR:\|const TOK_RETURN:" src/parser_gen.ritz
echo ""

echo "3. Struct Definition Consolidation:"
echo "   Token struct definitions:"
grep -l "^struct Token" src/*.ritz
echo "   Parser struct definitions:"  
grep -l "^struct Parser" src/*.ritz
echo ""

echo "4. Compilation Check:"
python3 ../ritz0/ritz0.py src/compile_all.ritz -o compile_all.ll 2>&1 | tail -1
echo ""

echo "5. DWARF Debug Info Support:"
echo "   - emitter_llvmlite.py has DILocation support: $(grep -q 'DILocation' ../ritz0/emitter_llvmlite.py && echo 'YES' || echo 'NO')"
echo "   - _set_debug_loc implemented: $(grep -q '_set_debug_loc' ../ritz0/emitter_llvmlite.py && echo 'YES' || echo 'NO')"
echo "   - Debug info enabled by default: $(grep -q 'emit_debug = True' ../ritz0/emitter_llvmlite.py && echo 'YES' || echo 'NO')"
echo ""

echo "=== INTEGRATION VERIFICATION COMPLETE ==="
