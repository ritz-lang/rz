# Session 10: Pointer Arithmetic Scaling Issue

## Status
Continuing from Session 9. Made significant progress on argument parsing but hit a critical pointer arithmetic issue.

## Key Findings

### Fixed
1. ✅ **Argument parsing now works in bootstrap**
   - main.ritz lines 134, 142, 147, 208 had incorrect `* 8` scaling
   - Fixed by removing the manual scaling since ritz0 uses GEP (which auto-scales)
   - Bootstrap (ritz1) now successfully parses arguments like `ritz1 file.ritz -o output.ll`

### Not Working
2. ❌ **Self-hosted compilation crashes**
   - Bootstrap (ritz1) compiled from ritz0 works fine
   - When ritz1 compiles itself to create ritz1_gen2, the result crashes
   - Crash location: `streq` function, invalid argv pointer
   - This indicates argv parsing is still broken in gen2

### Root Cause Analysis
The issue is a fundamental difference in pointer arithmetic semantics:

**ritz0 (Python/bootstrap) approach:**
- Uses LLVM GEP instruction: `getelementptr i8*, i8** argv, i64 1`
- GEP automatically scales by element size (8 bytes for `i8*`)
- Result: correct offset for pointer-to-pointer access

**ritz1 (self-hosted) approach:**
- Emitter has code at lines 1985-2031 to detect `*(ptr + offset)` pattern
- Should emit: `mul i64 offset, 8` then `add i64 ptr, scaled`
- But this code is NOT being triggered for argv access
- Without scaling, code does: `add i64 argv, 1` (1 byte offset instead of 8)
- Result: reading from wrong memory location, crash

### Why Pattern Matching Fails
The emitter checks for pattern: `*(ptr + offset)` where:
- Outer operation: dereference (TOK_STAR)
- Inner operation: binary plus (TOK_PLUS)
- operand_kind == EXPR_BIN_OP

But the emitter might be receiving AST nodes in a different structure than expected, or the field offsets are wrong.

## Generated IR Comparison

### What ritz0 generates:
```llvm
%".10" = load i8**, i8*** %"argv"              ; Load argv
%".11" = getelementptr i8*, i8** %".10", i64 1 ; Scale by 8 automatically
%".12" = load i8*, i8** %".11"                 ; Dereference
```

### What ritz1 generates (WRONG):
```llvm
%9 = load i64, ptr %2        ; Load argv (as untyped i64)
%10 = add i64 0, 1           ; Load constant 1
%11 = add i64 %9, %10        ; Add without scaling (WRONG!)
%12 = inttoptr i64 %11 to ptr
%13 = load i64, ptr %12      ; Dereference
```

The ritz1 approach is treating pointers as untyped i64, losing the type information needed for proper scaling.

## Technical Issues

1. **Type Information Loss**:
   - ritz doesn't track type info in AST (untyped compiler)
   - At emit time, can't tell if a pointer is `**u8` or `*i64`
   - Without type info, can't scale arithmetic correctly

2. **Pattern Matching Limitation**:
   - The heuristic at lines 1985-2031 tries to detect `*(ptr + offset)` patterns
   - But it relies on specific AST structure that may not match all code patterns
   - Needs debugging to understand why pattern isn't matching

3. **Bootstrap vs Self-Hosted Divergence**:
   - Bootstrap works because ritz0 uses LLVM's type system
   - Self-hosted doesn't have access to type info
   - Need architectural fix to bridge this gap

## Next Steps

### Immediate (Debugging)
1. Add diagnostic output to emitter.ritz to trace pattern matching
2. Verify that argv access code paths are being compiled
3. Check if operand_kind is actually EXPR_BIN_OP when expected
4. Verify field offsets in AST structures

### Medium Term (Fix)
1. **Option A**: Force all pointer arithmetic to use scaling
   - Would affect performance but ensure correctness
   - Could use heuristic: "if adding to a pointer, always scale"

2. **Option B**: Track type information in AST
   - Major refactoring but proper solution
   - Would require changes to parser and emitter

3. **Option C**: Use GEP emulation in ritz1
   - Emit fake "getelementptr" patterns that ritz0 understands
   - But ritz1 wouldn't understand them when self-hosting

### Long Term
Consider whether untyped compilation is fundamentally limiting and if a typed AST would be better.

## Files Modified This Session
- ritz1/src/main.ritz: Removed incorrect `* 8` scaling (lines 134, 142, 147, 208)

## Build Status
- Bootstrap: ✅ Working (ritz1 compiled from ritz0)
- Gen2: ❌ Crashes in argv parsing

## Test Case for Debugging
```ritz
fn main(argc: i32, argv: **u8) -> i32
  if argc >= 2
    let arg1: *i8 = *(argv + 1) as *i8
    return 0
  return 1
```

This simple test shows the issue clearly - argv[1] access fails.

## Key Discovery
The critical finding is that:
1. **Bootstrap (ritz0→ritz1)**: Works perfectly because ritz0 emits GEP instructions with proper type information
2. **Self-hosted (ritz1→ritz1_gen2)**: Crashes because ritz1 manually handles pointer arithmetic without type info
3. **The Catch**: The manual scaling code at emitter.ritz:1985-2031 that tries to detect `*(ptr + offset)` patterns is either:
   - Not being triggered (pattern doesn't match)
   - Not being emitted correctly
   - Or is being emitted but overridden by GEP from the bootstrap

## Conclusion
Session 10 made progress on argument parsing but revealed a fundamental architectural issue: the self-hosted compiler cannot generate correct pointer arithmetic code because:

1. **Type Information Loss**: ritz lacks type information at compile time
2. **GEP Dependency**: Bootstrap works by using ritz0's GEP which has type info
3. **Manual Scaling Limitation**: The manual scaling code can't detect all pointer arithmetic cases reliably
4. **Circular Dependency**: To fix ritz1, we need ritz1 to work, creating a bootstrapping paradox

**The Path Forward**:
- Need to either: (a) add type tracking to ritz compiler, (b) find a way to make GEP detection work for untyped code, or (c) use a different approach to pointer arithmetic that doesn't require type info

The architecture of treating pointers as untyped i64 throughout the compiler is fundamentally limiting for self-hosting.
