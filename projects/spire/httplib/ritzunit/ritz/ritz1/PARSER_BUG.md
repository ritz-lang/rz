# Critical Parser Bug: Dereference Assignment in Nested If Statements

## Issue Description

The ritz1 parser fails to parse dereference assignment statements when they appear in deeply nested if blocks.

## Example That Fails

```ritz
fn lexer_match_from(lex: *Lexer, state: i32, pos: i64, best_type: *i32, best_len: *i32, best_priority: *i64) -> i32
  let nfa: *NFA = (*lex).nfa
  let state_ptr: *NFAState = (*nfa).states + state
  let current_len: i32 = (pos - (*lex).pos) as i32
  
  if (*state_ptr).is_accept == 1
    if current_len > (*best_len) || (current_len == (*best_len) && ((*best_type) < 0 || (*state_ptr).token_type < (*best_type)))
      (*best_type) = (*state_ptr).token_type  # FAILS HERE
      (*best_len) = current_len
  0
```

When the ritz1 parser encounters this file, it successfully parses the first 38 functions but then returns 0 from `parse_item()`, terminating the module parsing loop. Only 38 out of 193 functions get added to the module.

## Minimal Reproduction

```ritz
struct Node
  token_type: i32

fn test(ptr: *i32, node_ptr: *Node) -> i32
  if (*node_ptr).token_type == 1
    if 1 > 0
      (*ptr) = (*node_ptr).token_type  # FAILS TO PARSE
  0
```

## What Works (Comparisons)

- ✓ Single-level if with dereference assignment
- ✓ Dereference assignment in function body (no if)
- ✓ Complex nested if conditions (without assignment)
- ✓ Simple assignments in nested if
- ✓ Dereference read in nested if (`let x = (*ptr).field`)

## What Fails

- ✗ Dereference assignment in nested if: `(*ptr) = value`
- ✗ Member dereference assignment in nested if: `(*ptr).member = value`

## Impact

- **Blocking**: 155+ functions cannot be parsed
- **Severity**: Critical - prevents self-hosting bootstrap completion
- **Current State**: First 38 functions compile, then parser exits
- **Test Case**: src/lexer_nfa.ritz::lexer_match_from (line 781, function #39)

## Suspected Root Cause

The parser likely has an issue with:
1. Statement parsing state management after parsing if bodies
2. Block-level variable scoping interfering with statement type detection
3. Parser position or error flag not being properly managed in nested contexts
4. Lookahead or backtracking logic in statement parsing

## Debugging Strategy

1. Enable detailed debug output in parser to trace statement parsing
2. Compare parser state before/after parsing nested if blocks
3. Check statement parsing alternatives for dereference assignment
4. Verify block context depth management
5. Check if variable shadowing or scope tracking affects statement type detection

## Code Locations

- Parser: `src/parser_gen.ritz` (generated from grammar)
- Statement parsing: Lines with `parse_stmt`, `parse_block`, statement alternatives
- Problem statement type: `STMT_MEMBER_ASSIGN` or assignment statement parsing

## Workaround (Temporary)

Functions containing dereference assignments in deeply nested if statements would need refactoring to:
- Move assignments to shallower nesting levels
- Use intermediate variables
- Avoid nested if structures where possible
