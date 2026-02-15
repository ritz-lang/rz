# Token DSL Implementation Plan

**Phase**: Phase 3 (Self-hosting)
**Status**: Ready for development
**Estimated Effort**: 3-4 days
**Dependency**: NFA engine (✅ complete)

## Overview

Implement a token DSL parser that converts flex-like pattern declarations into Thompson NFA construction code. This bridges exploratory NFA work with practical lexer implementation.

## Implementation Stages

### Stage 1: DSL Lexer for DSL (Meta-circular)

First, we need a lexer that can tokenize DSL syntax itself.

**Input**: Token DSL source code (pattern rules)
**Output**: Stream of DSL tokens (STRING, KEYWORD, OPERATOR, etc.)

```
DSL Source:
  tokens { INT PLUS }
  rules { [0-9]+ -> INT }

DSL Tokens:
  DSLTOK_KEYWORD("tokens")
  DSLTOK_LBRACE
  DSLTOK_IDENT("INT")
  DSLTOK_IDENT("PLUS")
  DSLTOK_RBRACE
  DSLTOK_KEYWORD("rules")
  DSLTOK_LBRACE
  DSLTOK_PATTERN("[0-9]+")
  DSLTOK_ARROW
  DSLTOK_IDENT("INT")
  DSLTOK_RBRACE
  DSLTOK_EOF
```

**Test File**: `ritz1/test/test_dsl_lexer.ritz`
**Implementation**: `ritz1/src/dsl_lexer.ritz`

### Stage 2: DSL Parser

Parse DSL tokens into structured declarations.

**Input**: DSL tokens
**Output**:
- Token declarations (name -> type ID mapping)
- Pattern rules (pattern regex -> token type)

```ritz
struct TokenDecl
  name: *i8
  name_len: i32
  type_id: i32

struct PatternRule
  pattern: *i8
  pattern_len: i32
  token_type: i32
  skip: i32  # 1 if this token should be skipped

struct DslProgram
  tokens: *TokenDecl
  token_count: i32
  rules: *PatternRule
  rule_count: i32
```

**Test File**: `ritz1/test/test_dsl_parser.ritz`
**Implementation**: `ritz1/src/dsl_parser.ritz`

### Stage 3: Pattern Compiler (Thompson NFA)

Convert pattern strings to Thompson NFA structures.

**Input**: Pattern string (e.g., `"[0-9]+"`)
**Output**: NFA structure ready for matching

Key patterns to support:
- Literals: `"abc"`, `'x'`
- Character classes: `[a-z]`, `[^a-z]`
- Operators: `*`, `+`, `?`, `|`
- Grouping: `(...)`
- Escape sequences: `\n`, `\t`, `\\`

```ritz
fn compile_pattern(nfa: *NFA, pattern: *i8, pattern_len: i32) -> NFAFragment
  # Create parser state
  var parser: PatternParser = PatternParser {
    input: pattern,
    length: pattern_len,
    pos: 0
  }

  # Parse top-level alternation
  parse_alternation(nfa, &parser)
```

**Test File**: `ritz1/test/test_pattern_compiler.ritz`
**Implementation**: `ritz1/src/pattern_compiler.ritz`

### Stage 4: Lexer Generator

Combine patterns into a dispatcher that tries each rule in order.

**Input**: Token declarations + Pattern rules
**Output**: Generated lexer function

```ritz
fn create_lexer_from_dsl(
  token_decls: *TokenDecl,
  token_count: i32,
  pattern_rules: *PatternRule,
  rule_count: i32
) -> DslLexer
  # Create NFA for each rule
  var nfas: *NFA = __builtin_alloca(rule_count * size_of(NFA))

  for i in 0..rule_count
    let nfa: NFA = nfa_new()
    let frag: NFAFragment = compile_pattern(&nfa, rules[i].pattern, rules[i].pattern_len)
    thompson_accept(&nfa, frag, rules[i].token_type)
    nfas[i] = nfa

  # Create dispatcher
  DslLexer {
    nfas: nfas,
    count: rule_count,
    skip_mask: skip_masks,
    source: source,
    length: length,
    pos: 0
  }

fn dsl_lexer_next(lex: *DslLexer) -> Token
  # Skip whitespace first (implicit)
  var start: i32 = (*lex).pos

  # Try each pattern in order
  for i in 0..(*lex).count
    let match_len: i32 = nfa_match_from((*lex).nfas[i], (*lex).source, start)
    if match_len > 0
      (*lex).pos = (*lex).pos + match_len

      # Skip token if marked
      if skip_mask[i] == 1
        return dsl_lexer_next(lex)

      return Token { type: i, start: start, len: match_len }

  # Unknown token
  Token { type: TT_ERROR, start: start, len: 1 }
```

**Implementation**: `ritz1/src/dsl_lexer_generator.ritz`

## Test Cases by Stage

### Stage 1: DSL Lexer Tests

```ritz
@test
fn test_dsl_lex_simple_pattern() -> i32
  let dsl: *i8 = "[0-9]+"
  let tokens: *Token = dsl_tokenize(dsl, 5)

  # Should recognize as a pattern token
  assert tokens[0].type == TT_PATTERN_CHAR_CLASS
  0

@test
fn test_dsl_lex_string_pattern() -> i32
  let dsl: *i8 = "\"hello\""
  let tokens: *Token = dsl_tokenize(dsl, 7)

  assert tokens[0].type == TT_PATTERN_STRING
  0

@test
fn test_dsl_lex_alternation() -> i32
  let dsl: *i8 = "a | b"
  let tokens: *Token = dsl_tokenize(dsl, 5)

  # Should see: PATTERN, PIPE, PATTERN
  assert tokens[0].type == TT_PATTERN_CHAR
  assert tokens[1].type == TT_PIPE
  assert tokens[2].type == TT_PATTERN_CHAR
  0
```

### Stage 2: DSL Parser Tests

```ritz
@test
fn test_parse_token_decls() -> i32
  let dsl: *i8 = "tokens { INT PLUS }"
  let prog: DslProgram = dsl_parse(dsl, 18)

  assert prog.token_count == 2
  assert strcmp(prog.tokens[0].name, "INT") == 0
  assert strcmp(prog.tokens[1].name, "PLUS") == 0
  0

@test
fn test_parse_simple_rule() -> i32
  let dsl: *i8 = "rules { [0-9]+ -> INT }"
  let prog: DslProgram = dsl_parse(dsl, 23)

  assert prog.rule_count == 1
  assert prog.rules[0].token_type == 0  # INT
  0
```

### Stage 3: Pattern Compiler Tests

```ritz
@test
fn test_compile_literal() -> i32
  var nfa: NFA = nfa_new()
  let frag: NFAFragment = compile_pattern(&nfa, "hello", 5)

  assert nfa_accepts(&nfa, "hello", 5) == 1
  assert nfa_accepts(&nfa, "hell", 4) == 0
  0

@test
fn test_compile_char_class() -> i32
  var nfa: NFA = nfa_new()
  let frag: NFAFragment = compile_pattern(&nfa, "[0-9]", 5)

  assert nfa_accepts(&nfa, "0", 1) == 1
  assert nfa_accepts(&nfa, "9", 1) == 1
  assert nfa_accepts(&nfa, "a", 1) == 0
  0

@test
fn test_compile_plus() -> i32
  var nfa: NFA = nfa_new()
  let frag: NFAFragment = compile_pattern(&nfa, "[0-9]+", 6)

  assert nfa_accepts(&nfa, "123", 3) == 1
  assert nfa_accepts(&nfa, "", 0) == 0  # Plus requires at least one
  0

@test
fn test_compile_alternation() -> i32
  var nfa: NFA = nfa_new()
  let frag: NFAFragment = compile_pattern(&nfa, "if|else", 7)

  assert nfa_accepts(&nfa, "if", 2) == 1
  assert nfa_accepts(&nfa, "else", 4) == 1
  assert nfa_accepts(&nfa, "while", 5) == 0
  0
```

### Stage 4: Integration Tests

```ritz
@test
fn test_dsl_lexer_integration() -> i32
  # Full workflow: parse DSL, create lexer, tokenize input
  let dsl: *i8 =
    "tokens { INT PLUS }
     rules {
       [0-9]+ -> INT
       '+' -> PLUS
     }"

  let lex: DslLexer = create_lexer_from_dsl(dsl, strlen(dsl))
  let tokens: *Token = lexer_tokenize(&lex, "42+7", 4)

  assert tokens[0].type == 0  # INT
  assert tokens[1].type == 1  # PLUS
  assert tokens[2].type == 0  # INT
  0
```

## File Organization

```
ritz1/
  src/
    dsl_lexer.ritz           # Stage 1: Tokenize DSL syntax
    dsl_parser.ritz          # Stage 2: Parse DSL tokens
    pattern_compiler.ritz    # Stage 3: Compile patterns to NFA
    dsl_lexer_gen.ritz       # Stage 4: Generate lexer from DSL
  test/
    test_dsl_lexer.ritz      # Stage 1 tests
    test_dsl_parser.ritz     # Stage 2 tests
    test_pattern_compiler.ritz # Stage 3 tests
    test_dsl_integration.ritz # Stage 4 tests
```

## Build Process

```bash
# Build individual stages (in order)
make test-dsl-lexer              # Stage 1
make test-dsl-parser             # Stage 2
make test-pattern-compiler       # Stage 3
make test-dsl-integration        # Stage 4

# Build all DSL components
make test-dsl-all                # All 4 stages

# Integrate into ritz1 lexer
make test-ritz1-lexer-dsl        # Full lexer using DSL
```

## Dependency Graph

```
test_pattern_compiler.ritz
    └── pattern_compiler.ritz
        └── nfa.ritz ✅ (already complete)

test_dsl_parser.ritz
    └── dsl_parser.ritz
        └── dsl_lexer.ritz
            └── (basic token recognition)

test_dsl_integration.ritz
    └── dsl_lexer_gen.ritz
        └── pattern_compiler.ritz
            └── dsl_parser.ritz
                └── nfa.ritz ✅
```

## Estimated Timeline

| Stage | Task | Days | Status |
|-------|------|------|--------|
| 1 | DSL Lexer + tests | 0.5 | Pending |
| 2 | DSL Parser + tests | 1.0 | Pending |
| 3 | Pattern Compiler + tests | 1.5 | Pending |
| 4 | Lexer Generator + integration | 1.0 | Pending |
| - | Integration with ritz1 | 0.5 | Pending |
| **Total** | | **4.5 days** | |

## Success Criteria

1. ✅ All Stage 1 DSL lexer tests pass
2. ✅ All Stage 2 DSL parser tests pass
3. ✅ All Stage 3 pattern compiler tests pass
4. ✅ All Stage 4 integration tests pass
5. ✅ ritz1 lexer can be generated from DSL
6. ✅ ritz0 bootstrap can compile DSL -> ritz1 without manual NFA code

## Blockers & Mitigations

### Current Blockers
- None identified for core bootstrap path

### Known Limitations
- **Arrays in DSL**: No array literal syntax for skip masks (deferred to Phase 4)
  - *Mitigation*: Use simple bit flags or linear search for now
- **String patterns**: Limited escape sequence support initially
  - *Mitigation*: Support `\n`, `\t`, `\\` first; extend later

## Next Steps

1. Implement Stage 1 (DSL Lexer) - 4 hours
2. Implement Stage 2 (DSL Parser) - 6 hours
3. Implement Stage 3 (Pattern Compiler) - 8 hours
4. Implement Stage 4 (Lexer Generator) - 4 hours
5. Integration testing - 2 hours

---

**Decision Point**: Should we implement DSL parser now, or focus on ritz1 parser/emitter bootstrap first?

**Recommendation**: The DSL parser is optional for Phase 3 bootstrap. Core bootstrap path is:
1. ritz1 Parser (critical)
2. ritz1 Emitter (critical)
3. Bootstrap verification
4. DSL improvements (nice-to-have for Phase 4)

Current Phase 3 focus should remain on **parser + emitter** to achieve self-hosting. DSL work can follow once bootstrap is solid.
