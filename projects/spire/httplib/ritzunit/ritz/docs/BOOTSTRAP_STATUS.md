# Bootstrap Status Report

**Date:** 2024-12-25
**Goal:** Self-hosting ritz1 compiler
**Current Phase:** A/B Testing Tier 1 Examples

---

## Quick Summary

✅ **ritz1 compiles successfully** (ritz0 → ritz1)
✅ **3/11 Tier 1 examples passing** (27%)
❌ **Missing critical features** blocking full bootstrap

---

## Test Results

### Passing ✅ (3)
| Example | Exit Code | Notes |
|---------|-----------|-------|
| 02_exitcode | 42 | Simple integer return |
| 04_true | 0 | Minimal program |
| 04_false | 1 | Returns literal 1 |

### Failing ❌ (1)
| Example | Issue | Error |
|---------|-------|-------|
| 01_hello | Missing `print()` builtin | Invalid IR: unreachable code after ret |

### Skipped ⚠️ (7)
| Example | Blocker |
|---------|---------|
| 03_echo | String handling + command-line args |
| 05_cat | File I/O syscalls |
| 06_head | File I/O + string ops |
| 07_wc | File I/O + counting logic |
| 08_seq | Loops + number formatting |
| 09_yes | Infinite loops + string output |
| 10_sleep | nanosleep syscall + struct args |

---

## Critical Path to Bootstrap

### Immediate Blockers (P0)

#### 1. Fix `print()` Builtin 🔥
**Issue:** ritz1 generates invalid IR for print() calls
**Example failure:** 01_hello

**Current ritz1 output:**
```llvm
define i32 @main() {
entry:
  %1 = load i32, ptr %0          ; ❌ %0 undefined
  ret i32 %1
  %2 = getelementptr ...          ; ❌ Unreachable after ret
  ret i32 %2                      ; ❌ Multiple returns
  %3 = add i32 0, 0
  ret i32 %3                      ; ❌ Multiple returns
}
```

**Expected (ritz0 output):**
```llvm
define i32 @main() {
entry:
  %".2" = getelementptr [14 x i8], [14 x i8]* @".str.0", i64 0, i64 0
  %".3" = ptrtoint i8* %".2" to i64
  %".4" = call i64 asm sideeffect "syscall", "..." (i64 1, i64 1, i64 %".3", i64 13)
  ret i32 0
}
@".str.0" = private constant [14 x i8] c"Hello, Ritz!\0a\00"
```

**Action:** Implement builtin function emission in ritz1's IR emitter

#### 2. String Literal Code Generation
**Issue:** GEP instructions for string constants not generated correctly
**Related:** Issue #9 (NFA pattern hang - actually fixed!)

**Action:** Fix string constant emission and pointer arithmetic

#### 3. Function Call Code Generation
**Status:** Unknown - not tested yet
**Risk:** High - needed for all complex programs

**Action:** Write test, verify call instruction generation

---

### Secondary Blockers (P1)

#### 4. Syscall Inline Assembly
**Needed for:** File I/O, process control, sleep
**Examples blocked:** 05_cat, 06_head, 07_wc, 10_sleep

**Action:** Emit inline asm syscall instructions

#### 5. Control Flow (if/while/for)
**Needed for:** Loops, conditionals
**Examples blocked:** 03_echo, 08_seq, 09_yes

**Action:** Implement branch/phi/label emission

#### 6. Command-Line Arguments (argc/argv)
**Needed for:** 03_echo
**Dependency:** Syscalls, string handling

---

### Nice-to-Have (P2)

- Struct support (needed for 10_sleep's timespec)
- Array indexing (already works in ritz0)
- Better error messages

---

## Self-Compilation Readiness

### Can ritz1 compile itself?
**Answer:** Not yet.

**ritz1 source uses:**
- ✅ Functions
- ✅ Structs
- ✅ Arrays
- ✅ Pointers
- ❌ String literals (broken in ritz1)
- ❌ Function calls (untested in ritz1)
- ✅ Arithmetic
- ✅ Comparisons
- ❌ Control flow (if/while - not implemented)
- ❌ Syscalls (not implemented)

**Blockers for self-compilation:**
1. All P0 issues (print, strings, calls)
2. All P1 issues (syscalls, control flow)
3. All ritz1 source features must work

**Estimated effort:** 2-3 days of focused work

---

## Development Strategy

### Option A: Fix Incrementally (Recommended)
1. ✅ Fix print() → 01_hello passes
2. ✅ Fix strings → More examples pass
3. ✅ Fix function calls → Test ritz1 internals
4. ✅ Fix syscalls → File I/O examples pass
5. ✅ Fix control flow → 8/11 examples pass
6. 🎯 Attempt self-compilation
7. 🐛 Fix whatever breaks
8. ✅ Full bootstrap achieved

**Timeline:** 1-2 weeks

### Option B: Parallel Development
- Work on ritz1 IR emission bugs
- Simultaneously improve ritz0 testing
- Build more examples to stress-test features

**Timeline:** 2-3 weeks (more thorough)

### Option C: Restart with Text IR Backend
- Use ritz1/ir/* text IR emitter (already 38 tests passing)
- Bypass llvmlite complexity
- Might be faster than fixing current emitter

**Timeline:** 1 week (risky - unproven backend)

---

## Next Actions

### Immediate (Today)
1. ✅ Document current status (this file)
2. ✅ Create comprehensive test suite
3. 🔨 **Debug print() emission in main_new.ritz**
4. 🔨 Write failing test for print()
5. 🔨 Fix IR emission for EXPR_CALL with builtin print

### Short-term (This Week)
- Fix all P0 issues
- Get to 6+/11 examples passing
- Test function call generation
- Begin syscall emission

### Medium-term (Next Week)
- Fix all P1 issues
- Pass 10/11 Tier 1 tests (skip 10_sleep if needed)
- Attempt first self-compilation
- Document discovered bugs

---

## GitHub Issue Recommendations

### New Issues to Create
1. ❗ `print()` builtin generates invalid IR (P0, bug)
2. ❗ String GEP emission broken (P0, bug)
3. ❗ Need function call code generation tests (P0, testing)
4. Syscall inline assembly not implemented (P1, enhancement)
5. Control flow IR emission missing (P1, enhancement)

### Existing Issues to Update
- #9: String literal parsing - **Actually works!** (close or rename)
- #15: Multi-arg calls - **Fixed!** (verify and close)
- #16: Assignment statements - **Fixed!** (verify and close)
- #17: Operator precedence - **Fixed!** (verify and close)

### Milestone Suggestion
**Milestone:** "Self-Hosting Bootstrap v1"
- Due: End of December
- Target: ritz1 compiles ritz1
- Issues: All P0 and P1 blockers

---

## Success Metrics

### Phase 1: Tier 1 Complete
- ✅ 10/11 examples pass A/B tests
- ✅ Exit codes match
- ✅ Output matches (where applicable)

### Phase 2: Self-Compilation
- ✅ ritz1_gen1 = compile(ritz1, ritz0)
- ✅ ritz1_gen2 = compile(ritz1, ritz1_gen1)
- ✅ IR(ritz1_gen1) == IR(ritz1_gen2) (bit-for-bit identical)

### Phase 3: Production Ready
- ✅ All Tier 2 examples pass
- ✅ Compiler performance acceptable (<5s for Tier 1)
- ✅ Error messages helpful
- ✅ Documentation complete

---

## Resources

- **A/B Test Script:** `./scripts/bootstrap_test.sh`
- **Compile ritz1:** `./ritz1/compile.sh`
- **Test Single Example:** `./scripts/ab_test.sh <file.ritz>`
- **Compiler Status:** `docs/COMPILER_STATUS.md`
- **GitHub Issues:** https://github.com/ritz-lang/ritz/issues

---

## Conclusion

**We're 27% of the way there!**

The path forward is clear:
1. Fix print() emission (1-2 hours)
2. Fix string literals (2-4 hours)
3. Test and fix function calls (4-6 hours)
4. Add syscalls (4-6 hours)
5. Add control flow (8-12 hours)

**Total estimated effort: 20-30 hours** to full bootstrap.

The good news: No fundamental architectural problems discovered. All failures are "simple" missing features in the IR emitter.

**Recommendation:** Focus on P0 issues first (print, strings, calls). These unlock the most examples and test self-compilation readiness.
