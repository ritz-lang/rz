# Tier 3 Preparation: Analysis and Recommendations

Pre-Tier 3 checkpoint analysis covering GitHub issues, code review, language design, and tooling improvements.

---

## 1. GitHub Issues Review

### Issues to Close (Pivoted Away)

| Issue | Title | Recommendation |
|-------|-------|----------------|
| #8 | Phase 5: Implement multi-argument function calls | **Close** - This was for ritz1 (self-hosted). ritz0 handles multi-arg calls. |
| #9 | Fix string literal parsing (NFA pattern hang) | **Close** - This was for ritz1's regex-based lexer. ritz0 handles strings fine. |
| #3 | Replace magic struct offset constants with typed pointers | **Close** - This was for ritz1. Keep as reference if we return to self-hosting. |
| #7 | Add proper error handling with source locations | **Close** - ritz0 now has error locations via Span. |
| #10 | Add comprehensive error reporting with line/column | **Close** - Same as above, ritz0 has this now. |
| #11 | Clean up project structure and remove deprecated files | **Keep** - Still valid, should do cleanup. |
| #12 | Implement ritz.toml packaging format | **Keep** - Future roadmap item. |
| #13 | Optimize variable lookup with hash table | **Close** - This was ritz1 specific. |
| #14 | Create comprehensive test suite for ritz1 | **Close** - We have 130+ tests for ritz0 now. |

### Issues to Keep (Still Relevant)

| Issue | Title | Priority | Notes |
|-------|-------|----------|-------|
| #31 | No type checking pass | **Critical** | ritz0 needs a type checker before ritz2 |
| #11 | Clean up project structure | Medium | Remove deprecated files |
| #12 | Implement ritz.toml packaging | Low | Future feature |

### Suggested New Issues

1. **Add `<<` and `>>` bit shift operators** - Blocked 16_tr implementation, had to use 256-byte arrays instead
2. **Implement `for` loops** - Currently only `while` loops work
3. **Add `match` expression support** - Useful for many patterns
4. **Implement module/import system** - Allow code reuse across examples
5. **Add `const` expressions** - Compile-time constant evaluation

---

## 2. Code Review: ritz0 Codebase

### Overview

| File | Lines | Purpose | Quality |
|------|-------|---------|---------|
| `emitter_llvmlite.py` | 1704 | LLVM IR generation | Good, but large |
| `parser.py` | 890 | Syntax parsing | Good |
| `emitter.py` | 918 | Legacy text-based emitter | **Deprecated?** |
| `ritz_ast.py` | 452 | AST definitions | Excellent |
| `lexer.py` | 439 | Tokenization | Good |
| `test_runner.py` | 324 | Test infrastructure | Good |
| `test_parser.py` | 339 | Parser tests | Good |
| `import_resolver.py` | 229 | Import handling | Incomplete |
| `test_lexer.py` | 214 | Lexer tests | Good |
| `ritz0.py` | 181 | CLI entry point | Good |
| `tokens.py` | 150 | Token definitions | Good |

### Observations

**Good:**
- Clean dataclass-based AST (mechanism-oriented, matches talk principles)
- Proper separation of concerns (lexer → parser → emitter)
- DWARF debug info integration is excellent
- 130+ tests across 15 levels

**Issues to Address:**

1. **Deprecated `emitter.py`** - 918 lines of unused code. Should be removed or clearly marked.

2. **Large `emitter_llvmlite.py`** - 1704 lines is manageable but could be split:
   - `emitter_types.py` - Type conversion
   - `emitter_expr.py` - Expression emission
   - `emitter_stmt.py` - Statement emission
   - `emitter_debug.py` - DWARF handling

3. **No type checking pass** - The emitter does ad-hoc type coercion but no proper type checking. This causes:
   - Silent incorrect behavior (u8 sign extension bug we fixed)
   - No error messages for type mismatches
   - No warning for unused variables

4. **`import_resolver.py` is incomplete** - Has TODO comments, not fully functional.

5. **Missing operators** - `<<`, `>>`, `%=`, `+=`, etc.

---

## 3. Language Design Review

### Current State

ritz0 is a "C with nicer syntax" - raw pointers, manual memory management, no safety checks. This is appropriate for bootstrap, but we should decide the direction for ritz1+.

### Your Suggestions Analysis

#### References vs Pointers

**Current:** Everything uses `*T` (raw pointers)
```ritz
fn read(fd: i32, buf: *u8, count: i64) -> i64
```

**Proposed:** Default to `&T` (references), reserve `*T` for unsafe
```ritz
fn read(fd: i32, buf: &[u8]) -> i64  # Safe reference
fn mmap_raw(addr: *u8, len: usize) -> *u8  # Unsafe, rare
```

**Recommendation:**
- ritz0: Keep `*T` only - it's bootstrap, keep it simple
- ritz1+: Introduce `&T` as default, `*T` requires `unsafe` block
- This aligns with "mechanism over policy" - provide the safe mechanism by default, allow escape hatch when needed

#### Stack vs Heap Allocation

**Current:** Examples use mmap for dynamic allocation
```ritz
let buf: *u8 = mmap(0, 65536, PROT_READ | PROT_WRITE, MAP_ANON, -1, 0)
```

**Proposed:** Stack by default, explicit heap annotation
```ritz
var buf: [1024]u8           # Stack-allocated, automatic
let data = box [0u8; 4096]  # Heap-allocated, explicit
```

**Recommendation:**
- Stack allocation is working great in our examples
- For heap, consider:
  - `Box<T>` for single values
  - `Vec<T>` for growable arrays
  - Both require destructor/drop semantics
  - Defer this to ritz1+ when we have RAII

#### Questions About Heap Usage

Looking at our 20 examples:
- **7 examples** use mmap directly (grep, tac, sort, uniq, cut, base64, xxd)
- **13 examples** are pure stack allocation
- All heap usage is for: line buffers, file contents, growable arrays

**Insight:** We don't need general heap allocation for Tier 2. What we need:
1. `Buffer` - growable byte array (like our manual implementation)
2. `LineVec` - growable array of line references
3. Both could be provided as built-in or stdlib

**Recommendation:**
- Tier 3 (filesystem) can still use stack allocation mostly
- Introduce `Vec<T>` as a built-in for Tier 4+ when generics arrive
- Consider arena allocators for short-lived allocations

---

## 4. Mechanism Over Policy: Language Implications

Reading your talk notes, here's how they apply to Ritz:

### Principle 1: Data is inert; behavior is in operations

**Good in Ritz:**
- Structs are pure data (no methods baked in)
- Functions operate on structs explicitly
- No inheritance hierarchies

**Could improve:**
- Method syntax (`s.len()`) is sugar for `String_len(s)` - this is good!
- Keep methods as syntax sugar, not encapsulation

### Principle 2: Boundaries match change boundaries

**For Ritz language design:**
- Don't bake policy into types (e.g., `SafePtr` vs `UnsafePtr`)
- Instead: one pointer type with context-dependent checking
- Example: `*T` is unsafe in safe code, allowed in `unsafe` blocks

### Principle 3: Compose at call sites, not definition sites

**For stdlib design:**
- Don't create a `FileReader` class hierarchy
- Instead: `open()`, `read()`, `close()` functions that compose
- Pipeline-oriented I/O: `read(fd, buf) |> parse |> validate`

### Principle 4: When in doubt, use plain data + functions

**This is exactly what ritz0 does!** Keep it.

---

## 5. Tooling / DX Improvements

### Already Great
- DWARF debug info (objdump -S, gdb work)
- 130+ tests with levels
- Clean compilation pipeline (ritz0 → llc → ld)

### Suggested Improvements

#### High Priority

1. **Type Checker Pass** (Issue #31)
   - Run before emission
   - Catch type mismatches early
   - Enable better error messages

2. **Error Messages with Source Context**
   ```
   error[E0001]: type mismatch
     --> examples/foo.ritz:42:15
      |
   42 |     let x: i32 = "hello"
      |                  ^^^^^^^ expected i32, found *u8
   ```

3. **`ritz build` command**
   - Wrap ritz0.py + llc + ld
   - Auto-detect output name from input
   - `ritz build examples/05_cat/src/main.ritz` → `examples/build/cat`

4. **`ritz test` command**
   - Run all tests in a project
   - Watch mode for development

#### Medium Priority

5. **LSP Server** (for editor support)
   - Syntax highlighting
   - Go to definition
   - Type on hover

6. **Incremental Compilation**
   - Cache .ll and .o files
   - Only rebuild changed files

7. **Source Maps**
   - Map generated IR back to source
   - Better debugging experience

#### Low Priority (Future)

8. **REPL**
   - JIT compilation for quick testing
   - Expression evaluation

9. **Documentation Generator**
   - Extract doc comments
   - Generate HTML/Markdown

---

## 6. Compliance & Quality Improvements

### Already Done
- DWARF debug info (excellent!)
- Valgrind-clean binaries
- Cross-platform (Linux x86-64)

### Suggested

1. **ASan/MSan Support**
   - Add `-fsanitize=address` option to build
   - Catch memory errors earlier

2. **Fuzz Testing Infrastructure**
   - Fuzz the parser with random input
   - Fuzz the examples with random data

3. **CI Pipeline**
   - Run tests on every commit
   - Valgrind check
   - Build all examples

4. **Code Coverage**
   - Track which lines are tested
   - Identify gaps in test coverage

5. **Benchmark Suite**
   - Compare against C implementations
   - Track performance over time

---

## 7. Recommended Actions Before Tier 3

### Immediate (Do Now)

1. Close stale GitHub issues (9 issues to close)
2. Remove or archive `emitter.py` (deprecated)
3. Create `docs/LANGUAGE.md` tutorial
4. Add missing operators (`<<`, `>>`)

### Short Term (Before Tier 3)

5. Create `ritz build` wrapper script
6. Add type checking pass (at least basic)
7. Improve error messages with source context

### Medium Term (During Tier 3)

8. Implement module/import system
9. Add `for` loop support
10. Consider `const` expressions

---

## Summary

The ritz0 codebase is in good shape. The main gaps are:
1. **Type checking** - Need a proper pass before emission
2. **Missing operators** - `<<`, `>>` blocked some implementations
3. **Developer experience** - Need `ritz build` command

The language design is solid and aligns well with "mechanism over policy":
- Plain data + functions
- No inheritance hierarchies
- Explicit over implicit

For Tier 3, we're ready. The main preparation is cleaning up issues and adding the `ritz build` command for easier iteration.
