# ritz1 Self-Hosting Implementation Plan

## Goal
Make ritz1 compile itself: `ritz1 src/*.ritz → ritz1_new`

## Current State (as of this plan)
- **6/9 tier1 examples work**: 01_hello, 02_exitcode, 03_echo, 05_cat, 06_head, 09_yes
- **Recent additions**: phi nodes, @ address-of, pub fn, and/or/not, [[attr]], u16/u32/i16, syscalls

## Blockers for Self-Hosting

| Blocker | Uses in ritz1 | Status |
|---------|--------------|--------|
| `for i in 0..n` loops | ~86 occurrences | Not implemented |
| Generic calls (`vec_new$u8`) | ~50+ | Partial - needs call emission |
| Method calls (`v.len`, `v.push`) | ~100+ | Partial - needs type lookup |
| Monomorphized structs | ~30+ | Partial - needs field access |
| `loop` keyword | ~5 | Not implemented |

---

## Phase 1: For-Loop Support (CRITICAL)
**Estimated: 2-3 days**

ritz1's own source uses `for i in 0..n` in 86 places. Without this, self-hosting is impossible.

### 1.1 AST Changes (`ast.ritz`)
```ritz
# Add constants
const STMT_FOR: i32 = 14
const EXPR_RANGE: i32 = 14

# Add fields to Stmt struct
for_var: *u8
for_var_len: i32
for_start: *Expr
for_end: *Expr
for_body: *Stmt
```

### 1.2 Parser Changes (`parser_stmt.ritz`)
```ritz
fn parse_for_stmt(p: *Parser) -> i32
    # Parse: for IDENT in EXPR .. EXPR BLOCK
    # 1. Consume TOK_FOR
    # 2. Parse IDENT (loop variable)
    # 3. Consume TOK_IN
    # 4. Parse start expression
    # 5. Consume TOK_DOTDOT
    # 6. Parse end expression
    # 7. Parse body block
```

### 1.3 Emitter Changes (`emitter.ritz`)
Desugar `for i in start..end` to while-loop pattern:
```llvm
%i = alloca i64
store i64 %start, ptr %i
br label %for.cond
for.cond:
  %i.val = load i64, ptr %i
  %cmp = icmp slt i64 %i.val, %end
  br i1 %cmp, label %for.body, label %for.end
for.body:
  ; ... body statements ...
  %i.next = add i64 %i.val, 1
  store i64 %i.next, ptr %i
  br label %for.cond
for.end:
```

---

## Phase 2: Generic Function Instantiation
**Estimated: 1-2 days**

### Current State
- `monomorph.ritz` exists (720 lines) and collects instantiations
- Creates specialized functions by cloning and type substitution
- **Problem**: Call sites may not emit correct mangled names

### Required Fix
In `emit_expr()` for `EXPR_CALL`:
- Check if `e.call_type_suffix_len > 0` (generic call)
- Emit: `call i64 @vec_new$u8(...)` with mangled name
- Ensure monomorphization creates the function body

---

## Phase 3: Method Call Emission
**Estimated: 2 days**

### Current State
- `EXPR_METHOD` is parsed
- `emit_expr()` handles method calls, mangles to `Type_method`
- **Problem**: Receiver type lookup limited

### Required Fix
Extend receiver type inference:
1. Track struct types through expressions
2. Support chained access: `tokens.data[i]`
3. Handle pointer-to-struct receivers

---

## Phase 4: Monomorphized Struct Field Access
**Estimated: 1-2 days**

### Problem
For `Vec$u8` (monomorphized type), field access `.len`, `.data`, `.cap` needs to resolve the mangled struct name.

### Fix
- `find_struct()` should handle both `Vec` and `Vec$u8`
- Track type suffix in LocalVar when needed

---

## Phase 5: Additional Features
**Estimated: 1 day**

### 5.1 `loop` Keyword
```ritz
loop
    # infinite loop
    if done
        break
```
Emit as `while(true)` pattern.

### 5.2 Continue Statement
Verify `STMT_CONTINUE` emits correct `br` to loop condition/increment.

---

## Phase 6: Testing & Validation
**Estimated: 2-3 days**

### Incremental Strategy
1. Start with smallest file: `tokens_gen.ritz` (108 lines)
2. Gradually add files in dependency order
3. Compare output with ritz0-compiled version

### Bootstrap Test
```bash
# Stage 1: ritz0 compiles ritz1
ritz0 src/*.ritz -o ritz1_stage1

# Stage 2: ritz1_stage1 compiles ritz1
./ritz1_stage1 src/*.ritz -o ritz1_stage2

# Stage 3: ritz1_stage2 compiles ritz1
./ritz1_stage2 src/*.ritz -o ritz1_stage3

# Verify: stage2 and stage3 should be identical
diff ritz1_stage2 ritz1_stage3  # Should match!
```

---

## Priority Order

| P# | Feature | Effort | Why |
|----|---------|--------|-----|
| P0 | For-loops | 2-3 days | 86 uses in ritz1 source |
| P1 | Generic calls | 1-2 days | Vec operations everywhere |
| P2 | Method calls | 2 days | .len, .push, etc. |
| P3 | Struct fields | 1-2 days | Vec field access |
| P4 | loop keyword | 0.5 day | Used in gvec.ritz |
| P5 | Continue | 0.5 day | Loop control |
| P6 | Testing | 2-3 days | Validation |

**Total: ~10-14 days**

---

## Dependency Graph

```
Phase 1 (for-loops) ─────────────────────┐
                                         │
Phase 2 (generic calls) ─────────────────┼─→ Phase 6 (Testing)
                                         │
Phase 3 (method calls) ──────────────────┤
                                         │
Phase 4 (generic structs) ───────────────┤
                                         │
Phase 5 (misc) ──────────────────────────┘
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `ast.ritz` | Add STMT_FOR, EXPR_RANGE, for_* fields |
| `parser_stmt.ritz` | Add parse_for_stmt() |
| `parser_gen.ritz` | Wire for-loop into statement parsing |
| `emitter.ritz` | Add emit for STMT_FOR, fix generic/method calls |
| `monomorph.ritz` | Verify instantiation works |

---

## Success Criteria

1. All tier1 examples compile and run correctly
2. ritz1 compiles ritz1 source → working compiler
3. Stage 2 and Stage 3 binaries are identical (fixed point)

---

*Created: Session on ritz1 self-hosting planning*
