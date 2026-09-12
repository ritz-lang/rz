# Code Review & Issue Analysis - December 26, 2024

Thorough code review before continuing ritz1 bootstrap work.

## Executive Summary

| Category | Issues Found | Critical | High | Medium | Low |
|----------|--------------|----------|------|--------|-----|
| ritz0 Compiler | 48 | 1 | 4 | 16 | 27 |
| Example Duplicates | 25+ | 0 | 3 | 10 | 12 |
| ritzgen Codegen | 1 | 1 | 0 | 0 | 0 |
| ritz1 Architecture | 1 | 0 | 1 | 0 | 0 |

---

## Critical Issues (Must Fix Before ritz1 Bootstrap)

### 1. ritzgen: `SYM_STAR`/`SYM_PLUS` Not Handled in AST Rules

**File:** `examples/49_ritzgen/src/codegen.ritz`
**Function:** `emit_rule_parser_ast()` (lines 272-500)

**Problem:** The AST-building parser generator only handles `SYM_TERMINAL`, `SYM_NONTERMINAL`, and `SYM_OPTIONAL`. It does NOT generate loops for `SYM_STAR` (zero or more) or `SYM_PLUS` (one or more).

**Evidence:** The grammar `module: item* { module_new(p) }` generates:
```ritz
fn parse_module(p: *Parser) -> *Module
    let start_pos: i32 = p.pos
    # Alternative 1
    if p.error == 0
        return  module_new(p)   # <-- NO LOOP! item* is ignored!
```

**Impact:** Parser cannot parse any functions - `module.functions == 0` always.

**Fix Required:** Add handling for `SYM_STAR` and `SYM_PLUS` in `emit_rule_parser_ast()` similar to how `emit_rule_parser()` handles them (lines 580-640).

### 2. ritz0: Duplicate `_emit_struct_lit` Method

**File:** `ritz0/emitter_llvmlite.py`
**Lines:** 1473-1503 and 1731-1775

**Problem:** Method defined twice - second overwrites first. This is a merge/refactor artifact.

**Fix:** Remove the duplicate definition (keep the more complete one).

---

## High Priority Issues

### 3. ritz0: Short-Circuit Evaluation Not Implemented

**File:** `ritz0/emitter_llvmlite.py` (lines 1373-1388)

**Problem:** `&&` and `||` operators evaluate both sides, not short-circuit. Comments claim short-circuit but implementation doesn't use conditional branches.

**Impact:** `ptr != nil && ptr.value > 0` will crash if `ptr` is nil.

**Fix:** Use basic blocks with conditional branches for proper short-circuit.

### 4. ritz0: `ImportError` Shadows Python Builtin

**File:** `ritz0/import_resolver.py` (lines 27-29)

**Problem:** `class ImportError` shadows Python's builtin `ImportError`.

**Fix:** Rename to `RitzImportError` or `ImportResolutionError`.

### 5. ritz0: Silent Duplicate Function Handling

**File:** `ritz0/import_resolver.py` (lines 219-225)

**Problem:** Comment says "warn about duplicates" but no warning is emitted. Last definition silently wins.

**Fix:** Add actual warning output or raise error for conflicts.

### 6. Example Duplication: PATH Search (5+ Examples)

**Files:** 32_which, 35_nohup, 36_timeout, 37_xargs, 39_time

**Problem:** Each example implements its own `search_path`/`find_in_path` function.

**Fix:** Create `ritzlib/exec.ritz` with:
- `find_in_path(envp, name, buf, bufsize) -> *u8`
- `spawn(path, argv, envp) -> i32`
- `run_command(path, argv, envp) -> i32`

---

## Medium Priority Issues

### ritz0 Issues

| Issue | File | Description |
|-------|------|-------------|
| Match exhaustiveness | emitter_llvmlite.py:2218 | No check that all union variants are covered |
| `_is_signed_type` stub | emitter_llvmlite.py:1184 | Always returns True, effectively dead code |
| Platform assumptions | emitter_llvmlite.py:155,185,275 | Hardcoded x86_64/Linux (64-bit pointers, triple) |
| Missing hex escapes | lexer.py:167 | No `\xNN` or `\uNNNN` escape sequences |
| Struct padding | emitter_llvmlite.py:142 | `_type_size_bytes` ignores alignment |
| AST `type` field | ritz_ast.py:331 | Shadows Python builtin `type()` |
| Unused tokens | tokens.py:37,104 | `UNSAFE` and `ERROR` never used |
| Generic error messages | parser.py:563,683 | "Expected expression" - no context |
| Windows path sep | import_resolver.py:54 | Uses `:` for RITZ_PATH (Unix only) |
| Mutable default | ritz_ast.py:145 | `type_args: List[Type] = None` pattern |
| Missing FnType | import_resolver.py:322 | `_types_equal` doesn't handle function types |
| O(n) list pop | lexer.py:377 | Should use deque for pending tokens |
| Empty array error | emitter_llvmlite.py:1505 | `[]` not allowed, no alternative suggested |
| nil as magic string | emitter_llvmlite.py:1264 | Should be proper keyword/token |

### Example Duplications to Consolidate

| Function | Examples | Recommendation |
|----------|----------|----------------|
| `heap_alloc/heap_free` | 11_grep, 47_lisp | Use `import ritzlib.mem` |
| `mode_to_str` / `print_mode` | 21_ls, 27_stat | Add to `ritzlib/fs.ritz` |
| `parse_octal` | 22_mkdir, 28_chmod | Add to `ritzlib/str.ritz` |
| `print_octal` | 27_stat, 28_chmod | Add to `ritzlib/io.ritz` |
| `copy_file` | 24_cp, 25_mv | Already in `ritzlib/fs.ritz` - use it |
| `to_lower` | 14_uniq | Use `tolower` from `ritzlib/str.ritz` |
| `parse_int` | 17_expand, 30_find | Use `atoi` from `ritzlib/str.ritz` |
| `TimeSpec` struct | 36_timeout, 40_watch | Use from `ritzlib/sys.ritz` |
| `write_all` | 38_tee | Add to `ritzlib/io.ritz` |
| Wait macros | 36_timeout, 37_xargs | Add to `ritzlib/sys.ritz` |
| `isatty` | 35_nohup | Add to `ritzlib/io.ritz` |
| `is_executable` | 32_which | Add to `ritzlib/fs.ritz` |

---

## Action Items for ritz1 Bootstrap

### Phase 1: Fix Critical Blockers

1. **Fix ritzgen SYM_STAR/SYM_PLUS handling** (BLOCKING)
   - Add loop generation in `emit_rule_parser_ast()`
   - Regenerate `parser_gen.ritz`
   - Test that `parse_module` actually parses functions

2. **Remove duplicate `_emit_struct_lit`** in emitter_llvmlite.py

### Phase 2: Address High Priority

3. **Create `ritzlib/exec.ritz`** - PATH search, spawn, run_command
4. **Implement short-circuit `&&`/`||`** in emitter
5. **Rename `ImportError`** class

### Phase 3: Clean Up Examples

6. **Update 11_grep** to use `import ritzlib.mem`
7. **Update 14_uniq** to use `tolower` from ritzlib
8. **Update 17_expand** to use `atoi` from ritzlib
9. **Update 24_cp, 25_mv** to use `copy_file` from ritzlib
10. **Add `mode_to_str`** to ritzlib/fs.ritz, update 21_ls and 27_stat

### Phase 4: Long-term Improvements

- Add match exhaustiveness checking
- Implement proper signed/unsigned type tracking
- Add hex escape sequences
- Make platform-specific code configurable
- Add `ritzlib/term.ritz` for terminal utilities
- Add `ritzlib/glob.ritz` for pattern matching

---

## Files Requiring Modification

### Immediate (for ritz1)
- `examples/49_ritzgen/src/codegen.ritz` - Add SYM_STAR/SYM_PLUS to AST rules
- `ritz0/emitter_llvmlite.py` - Remove duplicate method
- `ritz1/src/parser_gen.ritz` - Regenerate after codegen fix

### Short-term
- `ritz0/import_resolver.py` - Rename ImportError, add warnings
- `ritz0/emitter_llvmlite.py` - Short-circuit evaluation

### Medium-term
- New file: `ritzlib/exec.ritz` - Process execution utilities
- `ritzlib/fs.ritz` - Add mode_to_str, is_executable
- `ritzlib/io.ritz` - Add write_all, print_octal, isatty
- `ritzlib/str.ritz` - Add parse_octal
- `ritzlib/sys.ritz` - Add wait status macros

---

## Verified Working

The following have been verified working with separate compilation:
- All 48 examples (Tier 1-5) compile and run correctly
- ritzlib modules compile to separate .o files
- Symbol linking works across object files
- `--separate` flag properly emits declare vs define

---

## Summary

**Blocking Issue:** ritzgen doesn't generate loops for `item*` in AST-building rules.

Once fixed, the ritz1 bootstrap can proceed. The other issues are important for code quality but don't block bootstrapping.
