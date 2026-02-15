# Array Literal Initialization in Struct Literals - Design Blocker

**Status**: 🚫 BLOCKING NFA lexer development
**Severity**: Medium (exploratory work blocked, core bootstrap unaffected)
**Date**: 2024-12-23

## Problem Statement

The current parser does not support array literals as field values in struct literals.

### Current Error
```
Expected field name in struct literal at line 167:23
```

### Code Attempting to Compile
```ritz
struct NFA
  states: [64]NFAState
  state_count: i32

fn nfa_new() -> NFA
  var nfa: NFA = NFA {
    states: [NFAState { id: 0, is_accept: 0, token_type: 0 },
             NFAState { id: 0, is_accept: 0, token_type: 0 },
             // ... 62 more elements
    ],
    state_count: 0
  }
```

### Error Point
The parser sees:
1. `states:` - field name ✅
2. `[` - expects value but sees array literal start
3. Parser fails with "Expected field name" (confusing error)

## Root Cause Analysis

### Parser Logic
The struct literal parser in `ritz0/parser.py` (around line ~650) expects:
```python
field_name : expr
```

Where `expr` is parsed by `parse_expression()`, which correctly handles array literals (`[expr, expr, ...]`).

However, the parser may be failing because:
1. After seeing `:`, it expects a value
2. The `[` is parsed as start of array literal
3. But the literal contains complex struct initializers
4. Parser state gets confused

### Likely Bug Location
In `parser.py` struct literal parsing:
- Need to check if `parse_expression()` correctly delegates to `parse_primary()` for array literals
- May need to handle nested struct initialization in array elements

## Proposed Solutions

### Solution 1: Default Value Approach (Recommended)
Instead of trying to initialize array in struct literal, use helper function:

```ritz
struct NFA
  states: [64]NFAState
  state_count: i32

fn nfa_state_empty() -> NFAState
  NFAState { id: 0, is_accept: 0, token_type: 0 }

fn nfa_new() -> NFA
  var nfa: NFA = NFA {
    states: [nfa_state_empty(),
             nfa_state_empty(),
             // ... repeat 64 times
    ],
    state_count: 0
  }
```

**Pros**: Works with current parser
**Cons**: Verbose, repetitive

### Solution 2: Array Fill Syntax
Add new syntax for array initialization:

```ritz
fn nfa_new() -> NFA
  var nfa: NFA = NFA {
    states: [64]NFAState,  # Array filled with default values
    state_count: 0
  }
```

Would require:
- New parser support for `[N]Type` as value (vs just type)
- Default value semantics for struct types

**Pros**: Clean, ergonomic
**Cons**: Requires language feature implementation

### Solution 3: Constructor Function
Use a dedicated initialization function:

```ritz
fn nfa_new() -> NFA
  // Internal helper
  fn init_state() -> NFAState
    NFAState { id: 0, is_accept: 0, token_type: 0 }

  NFA {
    states: [init_state(), init_state(), // ... x64
    ],
    state_count: 0
  }
```

**Pros**: Works today, relatively clean
**Cons**: Still repetitive

### Solution 4: Macro-like Syntax
If we had macro support:

```ritz
fn nfa_new() -> NFA
  NFA {
    states: $repeat(NFAState { id: 0, is_accept: 0, token_type: 0 }, 64),
    state_count: 0
  }
```

**Pros**: Most ergonomic
**Cons**: Requires full macro system

## Recommended Path Forward

### For Bootstrap (Short-term)
**Use Solution 1 (Helper Function)** for NFA work:
- Solves the immediate blocker
- No language changes needed
- Allows NFA lexer exploration to continue

### For Phase 4+ (Long-term)
**Implement Solution 2 (Array Fill Syntax)**:
- Properly designed array initialization
- Better ergonomics
- Aligns with languages like Rust

## Implementation Plan (Solution 1)

1. Add helper function in test_nfa.ritz:
```ritz
fn nfa_state_default() -> NFAState
  NFAState { id: 0, is_accept: 0, token_type: 0 }

fn nfa_transition_default() -> Transition
  Transition { from: 0, to: 0, on: 0 }
```

2. Use in struct initialization:
```ritz
fn nfa_new() -> NFA
  NFA {
    states: [nfa_state_default(),
             nfa_state_default(),
             // ... x64 (probably need helper macro or Python generator)
    ],
    transitions: [nfa_transition_default(),
                  nfa_transition_default(),
                  // ... x128
    ],
    state_count: 0,
    trans_count: 0,
    start_state: 0
  }
```

## Impact Assessment

### Blocks
- ❌ NFA-based advanced lexer exploration
- ❌ Any complex array initialization patterns

### Doesn't Block
- ✅ Core bootstrap (Phase 3)
- ✅ Basic lexer tests
- ✅ Phase 1 tests
- ✅ Example programs

## Decision

**Recommendation**: Implement Solution 1 to unblock NFA work, plan Solution 2 for Phase 4.

The core bootstrap path doesn't need complex array initialization - this is exploratory NFA work that can use workarounds until better language support is available.

---

## Related Issues

- Array initialization ergonomics
- Struct default initialization
- Nested struct initialization
- Error messages for complex parsing failures

## Next Steps

1. Document workaround in test_nfa.ritz
2. Update NFA implementation to use helper functions
3. File improvement tracking for Phase 4 (array fill syntax)
4. Continue with parser implementation (unaffected)
