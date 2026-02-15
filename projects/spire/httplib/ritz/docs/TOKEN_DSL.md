# Token DSL Design Document

## Overview

The Token DSL is a domain-specific language for declaring lexical tokens in a flex/lex-like style. It provides an ergonomic way to specify token patterns that will be compiled into NFA-based lexer code.

## Design Goals

1. **Ergonomic**: Familiar syntax for developers coming from lex/flex
2. **Efficient**: Compiles to Thompson NFA construction for fast tokenization
3. **Debuggable**: Tests verify each token type independently
4. **Modular**: Token definitions can be organized by category
5. **Bootstrappable**: Written in Ritz, compiled by ritz0

## Token DSL Syntax

### Basic Structure

```ritz
# Token type constants
tokens {
  KEYWORD "keyword"
  IDENTIFIER
  NUMBER "number"
  OPERATOR
  WHITESPACE
  STRING
  COMMENT
  LPAREN "("
  RPAREN ")"
  EOF
}

# Pattern rules (order matters - first match wins)
rules {
  # Keywords (must come before identifiers)
  "if" | "else" | "while" | "for"     -> KEYWORD
  "fn" | "let" | "var" | "return"     -> KEYWORD

  # Identifiers
  [a-zA-Z_][a-zA-Z0-9_]*              -> IDENTIFIER

  # Numbers
  [0-9]+                              -> NUMBER
  0x[0-9a-fA-F]+                      -> NUMBER
  0b[01]+                             -> NUMBER

  # Operators
  "+" | "-" | "*" | "/"               -> OPERATOR
  "==" | "!=" | "<=" | ">="           -> OPERATOR

  # Punctuation
  "("                                 -> LPAREN
  ")"                                 -> RPAREN

  # Strings
  "\"" (!["\"\\] | "\\" .)* "\""      -> STRING

  # Comments
  "#" ![\n]* "\n"                     -> COMMENT

  # Whitespace (skip these)
  [ \t\n]+                            -> WHITESPACE (skip)

  # EOF
  EOF                                 -> EOF
}
```

### Pattern Syntax

#### Character Classes

- **Literal characters**: `'a'`, `'('`, `'\n'`
- **Character ranges**: `[a-z]`, `[0-9]`, `[a-zA-Z_]`
- **Negated ranges**: `[^a-z]`, `[^\n]`
- **Predefined classes**:
  - `\d` = `[0-9]`
  - `\w` = `[a-zA-Z0-9_]`
  - `\s` = `[ \t\n\r]`
  - `\D`, `\W`, `\S` = negated versions

#### Operators

- **Alternation**: `a | b` - matches either a or b
- **Concatenation**: `a b` - matches a followed by b (implicit)
- **Kleene star**: `a*` - zero or more
- **Plus**: `a+` - one or more
- **Optional**: `a?` - zero or one
- **String literals**: `"hello"` - literal string
- **Grouping**: `(a | b) c` - groups alternation

#### Escape Sequences

- `\.` - literal dot
- `\*` - literal star
- `\+` - literal plus
- `\|` - literal pipe
- `\[` - literal bracket
- `\n`, `\t`, `\r` - special whitespace
- `\\` - literal backslash

### Example Token Specifications

#### Minimal Calculator

```ritz
tokens {
  INT "number"
  PLUS "+"
  MINUS "-"
  STAR "*"
  SLASH "/"
  LPAREN "("
  RPAREN ")"
  WHITESPACE
  EOF
}

rules {
  [0-9]+         -> INT
  "+"            -> PLUS
  "-"            -> MINUS
  "*"            -> STAR
  "/"            -> SLASH
  "("            -> LPAREN
  ")"            -> RPAREN
  [ \t\n]+       -> WHITESPACE (skip)
  EOF            -> EOF
}
```

#### Python-like Keywords and Operators

```ritz
tokens {
  KEYWORD
  IDENTIFIER
  NUMBER
  STRING
  OPERATOR
  INDENT
  DEDENT
  NEWLINE
  COMMENT
  EOF
}

rules {
  # Keywords (checked before identifiers)
  "if" | "else" | "elif" | "while" | "for" | "def" | "class"   -> KEYWORD
  "import" | "from" | "as" | "in" | "is" | "and" | "or" | "not" -> KEYWORD
  "True" | "False" | "None"                                      -> KEYWORD

  # Identifiers (after keywords)
  [a-zA-Z_]\w*                                                   -> IDENTIFIER

  # Numbers
  [0-9]+ ("." [0-9]+)?                                           -> NUMBER
  0x[0-9a-fA-F]+                                                 -> NUMBER

  # Strings
  "\"" ([^"\\] | "\\" .)* "\""                                  -> STRING
  "'" ([^'\\] | "\\" .)* "'"                                    -> STRING

  # Operators
  "+" | "-" | "*" | "/" | "//" | "%" | "**"                    -> OPERATOR
  "==" | "!=" | "<" | ">" | "<=" | ">="                        -> OPERATOR
  "=" | "+=" | "-=" | "*=" | "/="                              -> OPERATOR

  # Comments
  "#" [^\n]* "\n"                                               -> COMMENT (skip)

  # Newlines
  "\n"                                                           -> NEWLINE

  # Whitespace
  [ \t]+                                                         -> (skip)
}
```

## Implementation Strategy

### Phase 1: DSL Parser (Ritz)

Create a parser that reads token DSL syntax and generates:

1. **Token type constants** - integer constants for each token type
2. **Pattern NFA generators** - calls to Thompson construction functions
3. **Lexer dispatcher** - function that tries each pattern in order

```ritz
fn create_lexer_from_dsl(dsl_text: *i8, dsl_len: i32) -> Lexer
  # Parse DSL
  let tokens: *TokenDecl = parse_token_decls(dsl_text, dsl_len)
  let rules: *PatternRule = parse_pattern_rules(dsl_text, dsl_len)

  # Create NFAs for each rule
  var nfas: *NFA = __builtin_alloca(MAX_RULES * size_of(NFA))
  for i in 0..rule_count
    nfas[i] = compile_pattern(rules[i].pattern)

  # Return lexer with NFA list
  Lexer { nfas: nfas, count: rule_count, ... }
```

### Phase 2: Pattern Compiler

Convert regex patterns to Thompson NFAs:

```ritz
fn compile_pattern(pattern: *i8) -> NFA
  var nfa: NFA = nfa_new()

  # Parse pattern string
  let frag: NFAFragment = parse_regex(&nfa, pattern)

  # Add accept state
  thompson_accept(&nfa, frag, token_type)

  nfa
```

### Phase 3: Lexer Dispatcher

High-level lexer that tries patterns in order:

```ritz
fn lexer_next_dsl(lex: *DslLexer) -> Token
  let start: i32 = (*lex).pos

  # Try each pattern in order
  for i in 0..(*lex).nfa_count
    if nfa_accepts((*lex).nfas[i], source_at(lex, start), ...) == 1
      let len: i32 = match_length((*lex).nfas[i], source_at(lex, start))
      (*lex).pos = (*lex).pos + len

      # Handle skip tokens
      if (*lex).skip_mask[i] == 1
        return lexer_next_dsl(lex)  # Skip and continue

      return Token { type: i, start: start, len: len }

  # Unknown token
  Token { type: TT_ERROR, start: start, len: 1 }
```

## Integration with ritz1

### File Structure

```
ritz1/
  src/
    token_dsl.ritz        # DSL parser and compiler
    nfa.ritz              # NFA engine (already exists)
    lexer.ritz            # Updated lexer using DSL
  test/
    test_dsl_parser.ritz  # DSL parser tests
    test_dsl_lexer.ritz   # Integration tests
```

### Usage Example

```ritz
# ritz1/src/token_dsl.ritz

# Parse token DSL and create lexer
fn create_ritz_lexer(source: *i8, len: i32) -> Lexer
  # Built-in Ritz token DSL (hardcoded for now)
  let dsl: *i8 =
    "tokens {
       KEYWORD IDENTIFIER NUMBER STRING OPERATOR
       LPAREN RPAREN LBRACE RBRACE LBRACKET RBRACKET
       COLON SEMICOLON COMMA DOT ARROW EQUAL
       PLUS MINUS STAR SLASH COMMENT WHITESPACE EOF
     }
     rules {
       'if' | 'else' | 'while' | 'for' | 'fn' ... -> KEYWORD
       [a-zA-Z_][a-zA-Z0-9_]*                     -> IDENTIFIER
       [0-9]+                                      -> NUMBER
       ...
     }"

  create_lexer_from_dsl(dsl, strlen(dsl))
```

## Testing Strategy

### Unit Tests (test_dsl_parser.ritz)

```ritz
@test
fn test_parse_simple_token_decl() -> i32
  let dsl: *i8 = "tokens { INT PLUS }"
  let tokens: *TokenDecl = parse_token_decls(dsl, strlen(dsl))

  assert tokens[0].name == "INT"
  assert tokens[1].name == "PLUS"
  0

@test
fn test_parse_character_pattern() -> i32
  let pattern: *i8 = "[0-9]+"
  let nfa: NFA = compile_pattern(pattern, TT_NUMBER)

  assert nfa_accepts(&nfa, "123", 3) == 1
  assert nfa_accepts(&nfa, "0", 1) == 1
  assert nfa_accepts(&nfa, "abc", 3) == 0
  0

@test
fn test_parse_string_pattern() -> i32
  let pattern: *i8 = "\"if\" | \"else\""
  let nfa: NFA = compile_pattern(pattern, TT_KEYWORD)

  assert nfa_accepts(&nfa, "if", 2) == 1
  assert nfa_accepts(&nfa, "else", 4) == 1
  assert nfa_accepts(&nfa, "while", 5) == 0
  0
```

### Integration Tests (test_dsl_lexer.ritz)

```ritz
@test
fn test_dsl_lexer_basic() -> i32
  let src: *i8 = "42 + x"
  var lex: Lexer = create_ritz_lexer(src, 6)

  let t1: Token = lexer_next(&lex)
  assert t1.type == TT_NUMBER

  let t2: Token = lexer_next(&lex)
  assert t2.type == TT_PLUS

  let t3: Token = lexer_next(&lex)
  assert t3.type == TT_IDENTIFIER

  0
```

## Benefits Over Current Approach

| Aspect | Current | DSL |
|--------|---------|-----|
| **Pattern Definition** | Manual NFA construction in code | Declarative regex syntax |
| **Readability** | Low (manual state/transition code) | High (familiar regex patterns) |
| **Maintainability** | Hard (easy to introduce bugs) | Easy (changes are localized) |
| **Performance** | Excellent (no overhead) | Excellent (same NFA backend) |
| **Extensibility** | Manual code changes | DSL updates only |

## Future Enhancements

1. **Precedence Rules**: Explicit priority specification
   ```ritz
   rules {
     @priority(100) "if" | "else" -> KEYWORD
     @priority(10) [a-zA-Z_]\w* -> IDENTIFIER
   }
   ```

2. **Actions**: Execute code on token match
   ```ritz
   rules {
     [0-9]+ -> NUMBER {
       value = parse_i64(text)
     }
   }
   ```

3. **Automatic Skip**: Simpler syntax for skipped tokens
   ```ritz
   skip [ \t\n]+
   skip "#" [^\n]* "\n"
   ```

4. **Context-Sensitive Tokens**: Indentation tracking
   ```ritz
   indent_based {
     indent_char: ' '
     indent_width: 1
     track_indent: true
   }
   ```

## Migration Path

1. **Phase 1** (Current): Manual lexer using Thompson NFA construction
2. **Phase 2** (Post-bootstrap): Implement DSL parser
3. **Phase 3** (ritz2): Full DSL-based token definition
4. **Phase 4** (ritz3): Optimizations (DFA conversion, table generation)

## Conclusion

The Token DSL provides a clear path to making lexer definition more ergonomic while maintaining the performance and flexibility of the Thompson NFA approach. It bridges the gap between the exploratory NFA work and practical lexer implementation, making the self-hosting compiler more maintainable as complexity increases.

---

**Status**: Design phase complete. Ready for implementation in next session.
