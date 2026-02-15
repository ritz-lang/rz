# Ritz Token DSL Syntax

## Overview

The token DSL provides a declarative way to define lexical tokens using regex-like patterns.
The DSL compiles to NFAs using Thompson's construction, enabling flex-style first-match priority.

## Syntax

```
# Comments start with #

# Token definitions: NAME = pattern
IDENT   = [a-z_][a-z0-9_]*
INT     = [0-9]+
HEX     = 0x[0-9a-fA-F]+
STRING  = "([^"\\]|\\.)*"

# Keyword shorthand (literal strings)
FN      = "fn"
LET     = "let"
IF      = "if"

# Operators (literal strings)
PLUS    = "+"
ARROW   = "->"
EQEQ    = "=="

# Whitespace/comments (can be marked @skip)
@skip WS      = [ \t]+
@skip COMMENT = #[^\n]*

# Special synthetic tokens (no pattern)
@synthetic INDENT
@synthetic DEDENT
@synthetic NEWLINE
@synthetic EOF
```

## Pattern Syntax

### Character Classes
- `[abc]`     - match any of a, b, c
- `[a-z]`     - match range a through z (inclusive)
- `[^abc]`    - negated: match anything except a, b, c
- `[a-zA-Z]`  - multiple ranges
- `.`         - match any character (except newline)

### Quantifiers
- `a*`        - zero or more
- `a+`        - one or more
- `a?`        - zero or one

### Grouping
- `(ab)+`     - group for quantifiers
- `a|b`       - alternation

### Escapes
- `\n`        - newline
- `\t`        - tab
- `\r`        - carriage return
- `\\`        - backslash
- `\"`        - double quote
- `\[`        - literal bracket
- `\+`        - literal plus (escape regex metachar)

### Literal Strings
- `"fn"`      - matches exact string "fn"
- `"->"`      - matches exact string "->"

## Semantics

### Match Priority
1. **Longest match wins** - among patterns that match, choose the longest
2. **First definition wins** - for equal-length matches, earlier token wins

This means keywords should be defined before identifiers:
```
FN    = "fn"      # First
LET   = "let"
IDENT = [a-z_]+   # Later (so "fn" matches FN, not IDENT)
```

### Special Markers
- `@skip` - token is recognized but not emitted (whitespace, comments)
- `@synthetic` - token has no pattern, emitted by lexer logic (INDENT, DEDENT, NEWLINE)

### Reserved Token Names
These have special meaning in the lexer:
- `EOF` - end of file
- `ERROR` - lexer error
- `NEWLINE` - line terminator
- `INDENT` - indentation increase
- `DEDENT` - indentation decrease

## Full Ritz Token Definitions

```
# === Keywords (first, to take priority) ===
FN      = "fn"
LET     = "let"
VAR     = "var"
IF      = "if"
ELSE    = "else"
WHILE   = "while"
FOR     = "for"
IN      = "in"
MATCH   = "match"
RETURN  = "return"
STRUCT  = "struct"
ENUM    = "enum"
IMPORT  = "import"
EXTERN  = "extern"
TRUE    = "true"
FALSE   = "false"
UNSAFE  = "unsafe"
CONST   = "const"
ASSERT  = "assert"

# === Literals ===
HEX     = 0x[0-9a-fA-F_]+
BIN     = 0b[01_]+
FLOAT   = [0-9][0-9_]*\.[0-9_]+([eE][+-]?[0-9_]+)?
INT     = [0-9][0-9_]*
STRING  = "([^"\\]|\\.)*"
CHAR    = '([^'\\]|\\.)'

# === Identifiers ===
IDENT   = [a-zA-Z_][a-zA-Z0-9_]*

# === Multi-char operators (before single-char) ===
EQEQ      = "=="
NEQ       = "!="
LEQ       = "<="
GEQ       = ">="
ARROW     = "->"
FATARROW  = "=>"
DOTDOT    = ".."
AMPAMP    = "&&"
PIPEPIPE  = "||"
PLUSEQ    = "+="
MINUSEQ   = "-="
STAREQ    = "*="
SLASHEQ   = "/="
COLONCOLON = "::"

# === Single-char operators ===
PLUS    = "+"
MINUS   = "-"
STAR    = "*"
SLASH   = "/"
PERCENT = "%"
AMP     = "&"
PIPE    = "|"
CARET   = "^"
TILDE   = "~"
BANG    = "!"
LT      = "<"
GT      = ">"
EQ      = "="
DOT     = "."
QUESTION = "?"

# === Delimiters ===
LPAREN   = "("
RPAREN   = ")"
LBRACKET = "["
RBRACKET = "]"
LBRACE   = "{"
RBRACE   = "}"
COMMA    = ","
COLON    = ":"
SEMI     = ";"
AT       = "@"

# === Whitespace/comments (skipped) ===
@skip WS      = [ \t]+
@skip COMMENT = #[^\n]*

# === Synthetic (no pattern, emitted by lexer logic) ===
@synthetic NEWLINE
@synthetic INDENT
@synthetic DEDENT
@synthetic EOF
@synthetic ERROR
```

## Implementation Notes

### NFA Construction
1. Parse DSL into list of (name, pattern, flags)
2. For each pattern, build NFA using Thompson's construction
3. Combine all NFAs into single multi-pattern NFA with priority
4. Each accepting state records token type and priority

### Lexer Algorithm
```
fn next_token():
  start = pos
  best_match = None
  best_len = 0
  best_priority = MAX_INT

  # Try each pattern from current position
  for pattern in patterns:
    if nfa_match(pattern.nfa, src, pos):
      match_len = matched_length
      if match_len > best_len ||
         (match_len == best_len && pattern.priority < best_priority):
        best_match = pattern
        best_len = match_len
        best_priority = pattern.priority

  if best_match:
    pos += best_len
    if not best_match.skip:
      return Token(best_match.type, src[start:pos])
  else:
    error("unexpected character")
```

### Indentation Handling
The lexer maintains an indent stack. After each NEWLINE:
1. Count leading spaces
2. Compare to current indent level
3. Emit INDENT if deeper, DEDENT(s) if shallower

This is handled outside the NFA matching since it's stateful.
