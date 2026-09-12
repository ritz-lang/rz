# Analysis: Negated Character Class Implementation

## Current Implementation

```ritz
# regex.ritz lines 120-127
if negated == 1
  # For [^x], match everything except x
  # Create: [\x00-\x{x-1}] | [\x{x+1}-\xFF]
  var before: NFAFragment = thompson_range((*p).nfa, 0, excluded_char - 1)
  var after: NFAFragment = thompson_range((*p).nfa, excluded_char + 1, 255)
  result = thompson_alt((*p).nfa, before, after)
```

## Problems

1. **Only handles single-character negation** (e.g., `[^a]` works, but `[^abc]` doesn't)
2. **Edge case bugs:**
   - `[^\x00]` creates invalid range `[0, -1]` (matches nothing)
   - `[^\xFF]` creates invalid range `[256, 255]` (matches nothing)
3. **Inefficient:** Creates 2 states + 2 epsilon transitions for every negated class

## Test Results

✅ **Working patterns:**
- `[^"]` (quote) - Creates `[0-33] | [35-255]`
- `[^"]*` (quote with star) - Compiles and works
- `[^a]` (letter a) - Works correctly
- `[^a]*` (letter a with star) - Works correctly

❌ **Edge cases (untested but theoretically broken):**
- `[^\x00]` - Would create invalid range
- `[^\xFF]` - Would create invalid range
- `[^abc]` - Only excludes 'a', ignores 'bc'

## Better Implementation Options

### Option 1: Add TR_NEGATED Transition Type

```ritz
# In nfa.ritz
const TR_NEGATED: i32 = 4  # Negated character match

struct Transition
  kind: i64
  char_val: i64      # Character to NOT match (for TR_NEGATED)
  # ... rest of fields

fn nfa_add_negated_trans(nfa: *NFA, from: i32, to: i32, ch: i32) -> i32
  # Creates transition that matches any char EXCEPT ch

fn trans_matches(trans: *Transition, ch: i32) -> i32
  if (*trans).kind == TR_NEGATED
    if ch != (*trans).char_val
      return 1
    return 0
  # ... existing cases
```

**Pros:**
- Simple, elegant
- Handles edge cases correctly (no invalid ranges)
- Efficient (1 state, 1 transition)
- Easy to extend to multi-char negation

**Cons:**
- Requires NFA changes
- Doesn't generalize to complex negated classes like `[^a-z0-9]`

### Option 2: Fix Range Validation + Multi-Char Support

```ritz
# In nfa.ritz
fn thompson_range(nfa: *NFA, lo: i32, hi: i32) -> NFAFragment
  # Validate range
  if lo > hi
    # Empty range - return epsilon transition
    let s0: i32 = nfa_add_state(nfa, 0, 0)
    return NFAFragment { start: s0, end: s0 }
  # ... existing code

# In regex.ritz - support full character sets
fn regex_parse_class(p: *RegexParser) -> NFAFragment
  # ... parse all chars/ranges in class

  if negated == 1
    # For each unique char value 0-255
    var result: NFAFragment = NFAFragment { start: -1, end: -1 }
    var first: i32 = 1
    var excluded: [256]i32 = [0; 256]  # Track excluded chars

    # Mark all excluded chars
    # ... populate excluded array from parsed class

    # Build alternation of all NON-excluded chars
    var ch: i32 = 0
    while ch < 256
      if excluded[ch] == 0
        let frag: NFAFragment = thompson_char((*p).nfa, ch)
        if first == 1
          result = frag
          first = 0
        else
          result = thompson_alt((*p).nfa, result, frag)
      ch = ch + 1
```

**Pros:**
- Supports full negated character classes `[^abc]`, `[^a-z]`
- No NFA changes needed
- Correct for all edge cases

**Cons:**
- Very inefficient (255 alternations for `[^a]`!)
- Huge NFA state explosion
- Slow to compile

### Option 3: Add TR_NEGATED_SET Transition Type

```ritz
# In nfa.ritz
const TR_NEGATED_SET: i32 = 4

struct Transition
  kind: i64
  excluded_set: *i8  # Pointer to 256-byte bitmap of excluded chars
  # ... rest

fn nfa_add_negated_set_trans(nfa: *NFA, from: i32, to: i32, excluded: *i8) -> i32
  # excluded is 256-byte array where excluded[ch] == 1 means "don't match ch"

fn trans_matches(trans: *Transition, ch: i32) -> i32
  if (*trans).kind == TR_NEGATED_SET
    if *((*trans).excluded_set + ch) == 0
      return 1
    return 0
```

**Pros:**
- Supports full negated classes efficiently
- Handles all edge cases
- Only 1 transition per negated class

**Cons:**
- Requires memory allocation for bitmaps
- More complex implementation

## Recommendation

**For bootstrap (ritz1):** Keep current implementation - it works for our use case (`[^"]`)

**For production (ritz2):** Implement Option 3 (TR_NEGATED_SET) for full support

## Validation Tests Needed

```ritz
# Basic negation
assert nfa_accepts("[^a]", "b") == 1
assert nfa_accepts("[^a]", "a") == 0

# Multi-char negation
assert nfa_accepts("[^abc]", "d") == 1
assert nfa_accepts("[^abc]", "a") == 0

# Range negation
assert nfa_accepts("[^a-z]", "A") == 1
assert nfa_accepts("[^a-z]", "a") == 0

# Edge cases
assert nfa_accepts("[^\x00]", "\x01") == 1
assert nfa_accepts("[^\x00]", "\x00") == 0
assert nfa_accepts("[^\xFF]", "\xFE") == 1
assert nfa_accepts("[^\xFF]", "\xFF") == 0
```
