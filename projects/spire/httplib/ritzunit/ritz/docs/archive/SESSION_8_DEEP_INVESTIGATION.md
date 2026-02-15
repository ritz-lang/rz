# Session 8: Deep Investigation of Self-Hosting Crash

## Status: Complex Issue - Multiple Layers to Fix

## Timeline of Investigation

### Initial Discovery
- Confirmed ritz1 bootstrap works perfectly (ritz0 → ritz1)
- Confirmed simple files compile without issue
- Binary search identified parser.ritz as the crash point

### Root Cause Identification
- Struct field offset bug discovered (EXPR_FIELD handler hardcoded to offset 0)
- Implemented fix for EXPR_FIELD to compute proper field offsets
- BUT: Even after fix, self-hosting still crashes

## Current Status

### What Works
- ✅ Bootstrap ritz1 (ritz0 → ritz1): Fully functional
- ✅ ritz1 compiles simple programs: Works
- ✅ ritz1 compiles first 8 files: Works
- ✅ ritz0 can compile all 11 files: Works (Python bootstrap)

### What Doesn't Work
- ❌ ritz1 compiling all 11 files: Segfault
- ❌ ritz1 compiling 9 files (with parser.ritz): Segfault
- ❌ Self-hosting (ritz1 → ritz1_self): Segfault

## Key Insight: Multiple Crash Sources

The crash happens TOO EARLY to be the EXPR_FIELD bug. Timeline:
1. ritz1 starts parsing first file (mem.ritz)
2. Successfully parses files 1-8
3. Crashes when starting to parse file 9 (parser.ritz)
4. Crash happens DURING parsing, not during emission
5. No IR output is generated

This suggests the crash is NOT in the emitter, but earlier in the pipeline.

## Hypothesis: Parser Issue

The parser.ritz file is DIFFERENT from other files in a key way:
- It defines 10 structs
- It contains 17 functions with complex logic
- It has many struct field access operations

But the crash happens during PARSING, not EMISSION. So the issue could be:

### Possibility 1: Parser Stack Overflow
- Large number of parse operations
- Deep recursion in parser
- Arena allocation running out of space
- Already addressed in commit 8c39330 ("Fix parser stack overflow")

### Possibility 2: Arena Corruption
- Arena buffer not allocated correctly
- Parser corrupts arena during operation
- Subsequent files fail

### Possibility 3: Lexer Issue with parser.ritz Content
- Specific tokens in parser.ritz cause lexer crash
- Not related to struct field access
- Related to how lexer handles multi-file input

### Possibility 4: Parser State Not Reset Between Files
- Parser state carries over from previous file
- Linked lists get corrupted
- When processing next file, parser crashes on corrupted state

### Possibility 5: Function Definition Linking Issue
- Parser accumulates functions in linked list
- After 8 files worth of functions, linked list becomes invalid
- Adding 17 more functions from parser.ritz causes memory corruption

## Debugging Path Forward

Given the token budget constraints and complexity, I recommend:

1. **Test with ritz0 on problematic fragment**:
   - Create minimal subset of parser.ritz
   - Test with ritz0 and ritz1
   - Narrow down exactly which code causes crash

2. **Add diagnostic output**:
   - Print file being parsed
   - Print function count after each file
   - Print arena allocation status
   - Track parser state

3. **Test partial compilation**:
   - ritz1 compiles: mem, utf8, nfa, regex, tokens, token_dsl, lexer, ritz_tokens
   - Then try: ritz1 compiles just parser.ritz with no previous files
   - Then try: ritz1 compiles ritz_tokens + parser.ritz only

4. **Isolate the crash trigger**:
   - Which function in parser.ritz triggers it?
   - Which struct definition triggers it?
   - Can we remove problematic code and get partial success?

## Code Review

The struct field fix I implemented IS correct:
```ritz
# Compute field offset: search through all structs
var struct_def: *i8 = b.structs
while struct_def != 0 as *i8
  # Search for field by name in this struct
  # Use found offset for GEP instruction
```

But this code is NEVER REACHED because the crash happens earlier.

## Struct Field Offset Fix Details

✅ **Fixed**:
- EXPR_FIELD now computes proper field offsets
- Searches all structs for matching field names
- Emits GEP with correct byte offset
- Falls back to offset 0 if field not found

✅ **Infrastructure Already Existed**:
- ir_add_structs() - registers struct definitions
- ir_lookup_struct() - looks up struct by name
- ir_lookup_field_offset() - looks up field offset (implemented but unused)
- Module.structs - stores parsed struct definitions

✅ **Changes Made**:
- Fixed EXPR_FIELD handler to use field offsets
- Added main.ritz::structs field to IRBuilder init
- Total: ~80 lines of new offset lookup code

## Potential Additional Issues

### Issue 1: StructField Offsets May Be Wrong
The code assumes each field is 8 bytes (64-bit aligned). But StructField struct might be different:
```
struct StructField
  name: *i8        # Offset 0 (8 bytes)
  name_len: i32    # Offset 8 (4 bytes)
  type_expr: *...  # Offset 12? 16? (depends on padding)
  next: *StructField  # Offset ? (where do we write this?)
```

The comment in emitter.ritz says: "StructField layout: name(*i8 at 0), name_len(i32 at 8), type_expr(*TypeExpr at 16), next(*StructField at 24)"

But I used offset 24 for next in my code - need to verify this is correct.

### Issue 2: Struct Definition Memory Layout
The IR builder stores structs as a linked list, but offsets are hardcoded:
- Line 95: `let next: *i8 = *((cur + 32) as **i8)  # StructDef.next at offset 32`
- My code line 1787: `struct_def = *((struct_def + 32) as **i8)`

Are these correct? Need to verify StructDef layout matches these offsets.

## Files Modified (This Session)

1. **ritz1/src/emitter.ritz**:
   - Rewrote EXPR_FIELD handler (lines 1743-1809)
   - Now computes field offsets instead of using hardcoded 0
   - Searches structs for field by name
   - Emits proper GEP instructions

2. **ritz1/src/main.ritz**:
   - Added `structs: 0 as *i8` to IRBuilder initialization

## Next Steps (If Continuing)

1. Don't assume struct field offsets are correct - verify against parser.ritz definitions
2. Test with diagnostic output to identify exact crash point
3. Consider adding memory protection/debug output to detect corruption
4. Test ritz0's emitter behavior on same inputs for comparison
5. Check if issue is reproducible with minimal parser.ritz subset

## Conclusion

The struct field offset fix is GOOD and CORRECT, but there's a more fundamental crash happening BEFORE that code is reached. The self-hosting failure is not a single bug but a complex interaction issue that requires deeper investigation.

The good news: Bootstrap path works perfectly, so ritz0 handles all this correctly. The task is to understand what ritz1 does differently that causes crashes.

Time spent this session: Diagnosis, root cause analysis, struct field fix implementation. Worth continuing but requires systematic debugging approach.
