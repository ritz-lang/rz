# ritz1 Code Review

Date: 2024-12-24
Reviewer: Adele (AI)

## Overview

ritz1 is the bootstrap self-hosting Ritz compiler, compiled by ritz0 (Python).
It consists of ~19 source files implementing lexer, parser, type checker, borrow checker, and IR emitter.

## Summary

| Aspect | Rating | Notes |
|--------|--------|-------|
| Code Organization | Good | Clear module separation |
| Naming Conventions | Mixed | Some inconsistencies |
| Documentation | Good | Header comments helpful |
| Memory Safety | Needs Work | `__builtin_alloca` issues |
| Architecture | Good | Clean pipeline design |
| Error Handling | Minimal | Return codes, no messages |
| Testability | Good | Separate test files exist |

---

## Critical Issues

### 1. **extern fn libc dependencies** (main.ritz:32-35)

```ritz
extern fn read(fd: i32, buf: *mut u8, count: i64) -> i64
extern fn write(fd: i32, buf: *u8, count: i64) -> i64
extern fn open(path: *u8, flags: i32, mode: i32) -> i32
extern fn close(fd: i32) -> i32
```

**Problem:** Links to libc, violating the "no external dependencies" design goal.

**Fix:** Use syscall builtins like ritz0's test_level11.ritz:
```ritz
fn sys_read(fd: i32, buf: *i8, count: i64) -> i64
  syscall3(0, fd, buf, count)
```

### 2. **Stack allocation abuse** (types.ritz:92, symbols.ritz:55, 78)

```ritz
fn type_new(kind: i32) -> *Type
  let ty: *Type = __builtin_alloca(128) as *Type  # BAD
```

**Problem:** Returns pointer to stack-allocated memory. Undefined behavior when function returns.

**Fix:** Use arena allocation consistently:
```ritz
fn type_new(arena: *Arena, kind: i32) -> *Type
  let ty: *Type = arena_alloc(arena, 128) as *Type
```

### 3. **Magic number struct offsets** (emitter.ritz:76-77, 96-98, 127-145)

```ritz
let next: *i8 = *((cur + 24) as **i8)  # ConstDef.next at offset 24
let next: *i8 = *((cur + 32) as **i8)  # StructDef.next at offset 32
```

**Problem:** Hardcoded offsets break when struct layouts change. Error-prone and unmaintainable.

**Fix:** Use constants or compute offsets from field sizes:
```ritz
const CONST_DEF_NEXT_OFFSET: i32 = 24  # name(8) + name_len(8) + value(8)
```

Or better: pass typed pointers, not raw `*i8`:
```ritz
fn ir_add_consts(b: *IRBuilder, consts: *ConstDef) -> i32
```

---

## Naming Inconsistencies

### Function Prefixes

| Module | Pattern | Example |
|--------|---------|---------|
| nfa.ritz | `nfa_*`, `thompson_*` | `nfa_add_state`, `thompson_char` |
| lexer.ritz | `lexer_*` | `lexer_next`, `lexer_init` |
| parser.ritz | `parse_*`, `parser_*` | `parse_expr`, `parser_advance` |
| types.ritz | `type_*` | `type_new`, `type_is_integer` |
| emitter.ritz | `ir_*`, `emit_*` | `ir_put_str`, `emit_ast_fn` |

**Issue:** `parser.ritz` mixes `parse_*` and `parser_*` prefixes.

**Recommendation:** Use consistent prefix per module:
- Queries/state: `parser_*` (e.g., `parser_at`, `parser_advance`)
- Actions: `parse_*` (e.g., `parse_expr`, `parse_stmt`)

This is actually good separation - keep it, just document the convention.

### Struct Field Names

**Good:**
- Consistent use of `next` for linked list pointers
- Clear naming: `is_accept`, `token_type`, `name_len`

**Inconsistent:**
- `TypeExpr` uses `inner` for nested type pointer
- `Expr` uses `left`, `right`, `val1`, `val2` (generic/overloaded)

**Recommendation:** Document the semantic meaning of overloaded fields in `Expr`:
```ritz
struct Expr
  kind: i64
  # For INT_LIT: val1 = integer value
  # For IDENT/STRING: val1 = source position, val2 = length
  # For BIN_OP: val2 = operator token type
  val1: i64
  val2: i64
```

---

## Good Patterns to Keep

### 1. Arena Allocation (mem.ritz)

Excellent design:
- Simple bump allocator
- 8-byte alignment
- Reset capability for reuse
- Clean API: `arena_alloc`, `arena_reset`, `arena_destroy`

### 2. NFA Thompson's Construction (nfa.ritz)

Well-structured:
- Clear separation of primitives (`thompson_char`, `thompson_range`)
- Composable: `thompson_concat`, `thompson_alt`, `thompson_star`
- Fragment pattern works well

### 3. Parser Token Constants (tokens.ritz)

Good organization:
- Grouped by category (keywords, operators, delimiters)
- Sequential numbering
- Clear naming (TOK_* prefix)

### 4. Pratt Parser (parser.ritz)

Clean implementation:
- `get_infix_precedence()` is readable
- Prefix operators handled correctly
- Extensible for new operators

---

## Design Issues

### 1. **Duplicated Constants** (checker.ritz, parser.ritz, types.ritz, symbols.ritz)

Multiple files define the same constants (EXPR_*, STMT_*, TYPE_*, etc.).

**Problem:** Changes must be made in multiple places.

**Fix:** Single source of truth - import from one module:
- `tokens.ritz` for token types
- `ast_kinds.ritz` for AST node kinds
- `type_kinds.ritz` for type kinds

### 2. **No Module System**

Files are concatenated/compiled separately with `--lib` flag.
Forward declarations must be manually maintained.

**Acceptable for bootstrap**, but Phase 2.9 should establish:
- Consistent include order
- Clear dependency graph

### 3. **i64 Everywhere for Alignment**

Every struct field uses i64 to ensure 8-byte alignment:

```ritz
# NOTE: Using i64 for all non-pointer fields to ensure 8-byte alignment for ritz1 self-hosting
struct Token
  type: i64    # Could be i32
  start: i64   # Could be i32
```

**Problem:** Wastes memory, makes code verbose.

**Root cause:** ritz1's IR emitter hardcodes 8-byte field offsets.

**Fix (Phase 2.9):** Implement proper struct layout calculation matching LLVM's alignment rules.

---

## Error Handling

### Current State

```ritz
if parser_at(p, TOK_COLON) == 0
  return 0  # Silent failure
```

- Returns null on error
- No error messages
- No source location tracking
- Caller must check for null

### Recommendation

For bootstrap, this is acceptable. For Phase 2.9+:
1. Add error struct with message + location
2. Propagate errors up
3. Consider Result type pattern

---

## Recommendations Summary

### Immediate (Before Phase 2.9)

1. **Remove `extern fn` libc calls** - Use syscall builtins
2. **Fix `__builtin_alloca` in type_new, symbol_new, scope_new** - Pass arena parameter
3. **Document overloaded Expr fields**

### Phase 2.9

4. **Eliminate magic offset constants** - Use typed pointers or computed offsets
5. **Consolidate constant definitions** - Single source of truth per category
6. **Implement proper struct layout** - Match LLVM alignment rules

### Future

7. **Add error handling** - Error struct with location
8. **Module system** - Explicit imports

---

## Files Reviewed

| File | Lines | Purpose | Quality |
|------|-------|---------|---------|
| main.ritz | 267 | Entry point, CLI | Good (except extern fn) |
| tokens.ritz | 107 | Token types | Good |
| mem.ritz | 131 | Arena allocator | Excellent |
| nfa.ritz | 296 | NFA engine | Excellent |
| lexer.ritz | 350 | Multi-pattern lexer | Good |
| regex.ritz | ~200 | Regex parser | Good |
| parser.ritz | 1213 | Recursive descent parser | Good |
| types.ritz | 302 | Type representation | Good (stack alloc issue) |
| symbols.ritz | 165 | Symbol table | Good (stack alloc issue) |
| emitter.ritz | ~1400+ | LLVM IR generation | Needs refactor (magic offsets) |
| checker.ritz | ~400 | Type checker | Good |

---

## Conclusion

The ritz1 codebase is well-organized for a bootstrap compiler. The main issues are:

1. **libc dependency** - Must be removed for design goals
2. **Stack allocation bugs** - Returning pointers to local allocations
3. **Magic offsets** - Fragile struct field access

These should be addressed before starting Phase 2.9 to avoid propagating technical debt into the new IR generator.
