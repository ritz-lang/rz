# Issue: alloca() Used for Data Outliving Function Scope

## Priority: CRITICAL (Blocks multi-statement functions)

## Status: ✅ RESOLVED - Fixed in commit fd3a52b

**This was NOT a ritz0 bug! This was a fundamental design error in ritz1's parser!**

## Root Cause

**Problem:** Parser uses `__builtin_alloca()` to allocate AST nodes, then returns pointers to that stack memory. When the function returns, the stack frame is popped and that memory becomes invalid.

## Evidence

In `parser.ritz` (line 171):
```ritz
fn parser_parse_return(p: *Parser) -> *Stmt
  parser_expect(p, TOK_RETURN)
  let value: *Expr = parser_parse_expr(p)
  let s: *Stmt = __builtin_alloca(256)  # ← Stack allocation!
  *s = stmt_return(value)
  (*s).next = 0
  s  # ← Returning pointer to stack memory that's about to be freed!
```

**Every parser function does this:**
- `parser_parse_return()` - line 171
- `parser_parse_if()` - line 198
- `parser_parse_while()` - line 212
- `parser_parse_assignment()` - lines 224, 234, 239
- `parser_parse_var_decl()` - line 273
- `parser_parse_let_decl()` - line 303
- `parser_parse_params()` - line 397
- `parser_parse_fn()` - line 448
- `parser_parse_module()` - line 480
- All expression creation functions

## Why First Statement Works

The first statement's stack memory might still be valid (or not yet overwritten) when accessed immediately. Subsequent statements' memory gets clobbered as more parser functions are called and the stack is reused.

## Proof ritz0 Is Correct

Created `test_struct_assignment_simple.ritz` that tests struct assignment via pointer:
```ritz
let s: *SimpleNode = __builtin_alloca(128)
*s = create_node_inline(99)  # Returns struct with next=0
if (*s).next != 0
  return 30  # Error: next pointer not null
```

**Result:** Test returns 0 (success) ✅

ritz0's LLVM IR correctly:
- Initializes all struct fields via `insertvalue`
- Sets `next = 0` in `stmt_return()`
- Stores struct properly
- Explicitly sets `next = 0` again in `parser_parse_return()`

## Solution

**Need heap allocator or arena allocator.** Options:

1. **mmap-based bump allocator** (simplest for bootstrap)
   - Call `mmap()` syscall to get memory pages
   - Bump pointer for each allocation
   - Never free (acceptable for compiler - process lifetime)

2. **malloc implementation** (if we add libc)
   - Requires linking against libc
   - Adds dependency

3. **Arena allocator** (cleanest)
   - Allocate large chunks via mmap
   - Sub-allocate from chunks
   - Can free entire arena at once

**For bootstrap: Option 1 is fastest to implement.**

## Resolution

Implemented parser-integrated heap allocator using mmap:

1. **Added to Parser struct:**
   - `heap_base: *i8` - Base address of mmap'd region
   - `heap_offset: i64` - Current offset (bump pointer)

2. **New function `parser_alloc(p: *Parser, size: i64)`:**
   - Aligns to 8-byte boundary
   - Bumps offset
   - Returns pointer into heap
   - Never frees (acceptable for compiler lifetime)

3. **Replaced all `__builtin_alloca()` calls with `parser_alloc()`:**
   - All Stmt, Expr, Param, FnDef, Module allocations now use heap
   - Removed workaround that broke after first statement

4. **Tested successfully:**
   - Multi-statement functions work
   - Parser processes all statements without crashes
   - Memory is persistent across function returns

## Impact
- ✅ Multi-statement functions now work correctly
- ✅ No more garbage pointers in statement lists
- ✅ Parser can build complete ASTs
- **Time taken:** ~2 hours to diagnose and implement
