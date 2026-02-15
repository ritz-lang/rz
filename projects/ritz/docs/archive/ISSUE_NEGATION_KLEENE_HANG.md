# Issue: Negation + Kleene Star Pattern Causes Infinite Loop

## Priority: MEDIUM (Blocks string literal support)

## Symptom
Pattern `"[^\"]*\""` (match string literals) causes infinite loop during NFA construction or lexer initialization.

## Evidence

Pattern in `lexer_setup.ritz`:
```ritz
# String literals - DISABLED due to hang
# lexer_add_pattern(lex, "\"[^\"]*\"", 10, TOK_STRING, 0)
```

**With pattern enabled:** Compiler hangs before any output (during `setup_lexer()`)
**With pattern disabled:** Compiler works perfectly

## What Works
- ✅ Simple negation: `[^a]` matches any character except 'a'
- ✅ Kleene star alone: `[a-z]*` matches zero or more letters
- ✅ **UPDATED:** Combined `[^a]*` works in isolation!
- ✅ **UPDATED:** Pattern `[^"]*` works in isolation!
- ❌ Hang occurs only in full lexer setup with ALL 44 patterns

## Implementation Details

Negation was implemented in:
- `regex.ritz`: Detects `^` at start of character class
- `nfa.ritz`: `thompson_negated_class()` creates complement ranges

For `[^"]`:
1. Detect quote (ASCII 34)
2. Create `[0-33]` (characters before quote)
3. Create `[35-255]` (characters after quote)
4. Combine with alternation: `[0-33]|[35-255]`

When combined with Kleene star `[^"]*`:
- Creates deeply nested alternation structure
- Possibly creates epsilon cycles in NFA
- Causes infinite loop during simulation or construction

## Root Cause Hypothesis
**UPDATED:** The pattern itself works fine. The hang occurs when combining the string pattern with the other 43 patterns during `lexer_finalize()`.

Likely causes:
1. **NFA state/transition limit exceeded** - 44 patterns may create too many states
2. **Epsilon transition explosion** - Combining negation alternations with other patterns
3. **Array bounds issue** - States/transitions arrays too small for all patterns
4. **Pattern interaction bug** - String pattern conflicts with another pattern

## Next Steps
1. Test `setup_lexer()` with 43 patterns (without string pattern) - WORKS ✅
2. Test `setup_lexer()` with progressively fewer patterns to find threshold
3. Increase state/transition array sizes
4. Add debug output during `lexer_finalize()` to see where it hangs

## Workaround
String literals temporarily disabled. Can re-enable once fixed.
