# Ritz Parser Architecture: Gold Standard Design

## Executive Summary

This document outlines the ideal architecture for the Ritz parser system. The goal is to define a clean, modular, maintainable parser that:

1. **Never requires hand-editing generated code** - all changes flow from grammar → generator → output
2. **Keeps files under 500 lines** (1000 acceptable, 2000+ is a red flag)
3. **Separates concerns clearly** - lexer, parser, AST, helpers, emitter
4. **Scales predictably** - adding new syntax doesn't require architectural changes

---

## Current State Analysis

### File Inventory (by line count)

| File | Lines | Status | Notes |
|------|-------|--------|-------|
| `parser.ritz` | 3,569 | ⚠️ **TOO LARGE** | AUTO-GENERATED - needs splitting |
| `ast_helpers.ritz` | 1,171 | ⚠️ Large | Hand-written, called by parser |
| `emit_min.ritz` | 982 | OK | Minimal emitter for bootstrap |
| `ir.ritz` | 751 | OK | IR types and operations |
| `emitter.ritz` | 696 | OK | Full emitter (unused in bootstrap) |
| `lexer_nfa.ritz` | 467 | OK | NFA-based lexer |
| `ast.ritz` | 333 | ✅ | AST types and constants |
| `nfa.ritz` | 289 | ✅ | NFA primitives |
| `main.ritz` | 242 | ✅ | Entry point |
| `regex.ritz` | 206 | ✅ | Regex → NFA |
| `layout.ritz` | 143 | ✅ | Struct layout computation |
| `tokens.ritz` | 135 | ✅ | Token constants (generated) |
| `lexer_setup_gen.ritz` | 107 | ✅ | Lexer pattern registration (generated) |

### Current Pipeline

```
ritz1.grammar (515 lines)
    ↓
ritz_generator.py + grammar_parser.py
    ↓
├── tokens.ritz (generated, 135 lines)
├── parser.ritz (generated, 3,569 lines) ← PROBLEM
├── lexer_setup_gen.ritz (generated, 107 lines)
└── ast_helpers.ritz (hand-written, 1,171 lines)
```

### Key Problem: The Generated Parser is 3,569 Lines

The generator produces a single monolithic parser file. This violates our modularity principle. The grammar has 50+ rules, each generating a `parse_*` function, all in one file.

---

## Proposed Architecture

### 1. Grammar Organization

The grammar (`ritz1.grammar`) is well-organized at 515 lines. It defines:

- **50+ grammar rules** covering all language constructs
- **100+ token definitions** for lexer
- **Semantic actions** using `$N` notation for AST construction

The grammar is the **single source of truth** for syntax. This is correct.

### 2. Generator Improvements

**Current:** Single parser.ritz output
**Proposed:** Split into logical modules

```
ritz1.grammar
    ↓
ritz_generator.py (enhanced)
    ↓
├── tokens.ritz          (107 lines) - constants
├── lexer_setup_gen.ritz (135 lines) - pattern registration
├── parser_core.ritz     (~100 lines) - p_peek, p_advance, parser_init
├── parser_toplevel.ritz (~200 lines) - module, item, fn_def, struct_def
├── parser_stmt.ritz     (~300 lines) - stmt, if_stmt, while_stmt, assign_stmt
├── parser_expr.ritz     (~400 lines) - expr, binary ops, postfix ops
├── parser_type.ritz     (~150 lines) - type_spec, generic_params
└── parser_helpers.ritz  (~100 lines) - utility functions
```

**Split Criteria:**
- `parser_toplevel.ritz` - Module-level constructs (fn, struct, const, import, impl)
- `parser_stmt.ritz` - Statement parsing (let, var, return, if, while, assign)
- `parser_expr.ritz` - Expression parsing (the bulk of complexity)
- `parser_type.ritz` - Type parsing (type_spec, generic params)
- `parser_core.ritz` - Core parser infrastructure

Each file imports what it needs. The generator needs to understand these boundaries.

### 3. AST Helpers Organization

Currently `ast_helpers.ritz` at 1,171 lines handles:
- Parser allocation (bump allocator)
- Module helpers (module_new, module_add_*)
- Function/param helpers
- Statement helpers
- Expression helpers
- Binary/postfix chain helpers
- Struct literal helpers
- Numeric parsing

**Proposed split:**

```
ast_helpers/
├── alloc.ritz       (~50 lines)  - parser_alloc, bump allocation
├── module.ritz      (~100 lines) - module_*, impl_block_*, global_var_*
├── fn.ritz          (~150 lines) - fn_def_*, param_*, type_param_*
├── stmt.ritz        (~250 lines) - stmt_* functions
├── expr.ritz        (~300 lines) - expr_* functions
├── postfix.ritz     (~150 lines) - postfix_*, apply_postfix_p
├── binary.ritz      (~50 lines)  - binary_op_*, apply_binary_opt_p
├── struct_lit.ritz  (~100 lines) - field_init_*, ident_or_struct
└── parse.ritz       (~50 lines)  - parse_int, parse_hex, parse_binary
```

### 4. Clear Separation of Concerns

```
┌─────────────────────────────────────────────────────────────────┐
│                          GRAMMAR LAYER                          │
│  ritz1.grammar - Single source of truth for syntax              │
└─────────────────────────────────────────────────────────────────┘
                              ↓ generates
┌─────────────────────────────────────────────────────────────────┐
│                         TOKEN LAYER                             │
│  tokens.ritz - Token kind constants                             │
│  lexer_setup_gen.ritz - Pattern registration                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓ uses
┌─────────────────────────────────────────────────────────────────┐
│                          LEXER LAYER                            │
│  lexer_nfa.ritz - NFA-based lexer (hand-written)               │
│  nfa.ritz - NFA primitives (hand-written)                      │
│  regex.ritz - Regex to NFA (hand-written)                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓ produces tokens
┌─────────────────────────────────────────────────────────────────┐
│                         PARSER LAYER                            │
│  parser_*.ritz - Generated recursive descent parser             │
│  (NEVER hand-edit these files)                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓ calls
┌─────────────────────────────────────────────────────────────────┐
│                         AST LAYER                               │
│  ast.ritz - AST struct definitions (hand-written)              │
│  ast_helpers/*.ritz - AST constructors (hand-written)          │
└─────────────────────────────────────────────────────────────────┘
                              ↓ produces
┌─────────────────────────────────────────────────────────────────┐
│                        EMITTER LAYER                            │
│  emit_min.ritz - Minimal bootstrap emitter                     │
│  emitter.ritz - Full emitter (optional)                        │
│  ir.ritz - IR types                                            │
│  layout.ritz - Struct layout computation                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Language Features Inventory

From the grammar, these language features are defined:

### Top-Level Constructs
- **Function definitions** (`fn`, `pub fn`) with optional generic params
- **Extern functions** (`extern fn`) - forward declarations
- **Struct definitions** with optional generic params
- **Const definitions** (`const NAME: type = value`)
- **Global variables** (`var NAME: type = value`)
- **Import statements** (`import module.path`)
- **Impl blocks** (`impl Trait for Type`, `impl Type`)

### Statements
- **Variable declarations** (`let`, `var`) with optional type annotation
- **Return statements** (`return` with optional value)
- **If/else statements** (with block bodies)
- **While loops**
- **Break/continue**
- **Assignment statements** (simple, indexed, deref, member, compound)
- **Expression statements**

### Expressions
- **Literals** - integers (decimal, hex, binary), strings, chars, nil
- **Identifiers**
- **Binary operations** - arithmetic, comparison, logical, bitwise
- **Unary operations** - negation, not, deref, address-of
- **Cast expressions** (`expr as type`)
- **Function calls** with optional generic type args
- **Method calls** (`expr.method(args)`)
- **Indexing** (`expr[index]`)
- **Member access** (`expr.field`)
- **Struct literals** (`Type { field: value, ... }`)

### Types
- **Primitives** - i8, i16, i32, i64, u8, u16, u32, u64, bool
- **Pointers** - `*T`, `**T`
- **Arrays** - `[N]T`
- **References** - `@T` (immutable), `@&T` (mutable)
- **Named types** (structs)
- **Generic types** (`Vec<T>`)

---

## Traps to Avoid

### 1. Hand-Editing Generated Code
**Problem:** Changes get lost on regeneration
**Solution:** All parser changes must go through the grammar and generator

### 2. Massive Single Files
**Problem:** parser.ritz at 3,569 lines is unmaintainable
**Solution:** Generator must split output into logical modules

### 3. Tight Coupling
**Problem:** Parser directly calls emitter functions
**Solution:** Parser produces AST only; emitter walks AST separately

### 4. Inconsistent Naming
**Problem:** Mix of `OP_ADD`/`UOP_NEG` vs `OP_NEG` naming
**Solution:** Define clear naming conventions:
- `EXPR_*` for expression kinds
- `STMT_*` for statement kinds
- `TYPE_*` for type kinds
- `OP_*` for binary operators
- `UOP_*` for unary operators
- `TOK_*` for token kinds

### 5. Magic Numbers
**Problem:** Hard-coded allocation sizes (e.g., `parser_alloc(p, 128)`)
**Solution:** Define constants like `SIZEOF_EXPR`, `SIZEOF_STMT`

### 6. Parser State Pollution
**Problem:** `last_type_name`, `last_pointee_type` etc. are global parser state
**Solution:** This is acceptable for a single-threaded recursive descent parser, but document clearly

---

## Implementation Plan

### Phase 1: Generator Enhancement (1-2 hours)
1. Modify `ritz_generator.py` to emit split files
2. Add `--split-output` flag (default on)
3. Generate import statements between parser modules

### Phase 2: AST Helpers Refactor (2-3 hours)
1. Split `ast_helpers.ritz` into logical modules
2. Create `ast_helpers/` directory structure
3. Update imports in all consumers

### Phase 3: Validation (1 hour)
1. Regenerate all parser files
2. Rebuild ritz1
3. Run test suite
4. Verify all examples compile

### Phase 4: Documentation (30 min)
1. Update README with new structure
2. Document generator usage
3. Add architecture diagram to docs

---

## Grammar Extension Guidelines

When adding new syntax to Ritz:

1. **Add token definitions** to `%tokens` section if new keywords/operators
2. **Add grammar rules** in appropriate section (toplevel, stmt, expr, type)
3. **Add AST types** in `ast.ritz` if new node kinds needed
4. **Add helper functions** in appropriate `ast_helpers/*.ritz` file
5. **Add emitter support** in `emit_min.ritz`
6. **Regenerate** parser files
7. **Test** with example code

The key is: **grammar is the source of truth, everything flows from it**.

---

## File Size Guidelines

| Category | Target | Acceptable | Scrutinize |
|----------|--------|------------|------------|
| Generated | <300 | <500 | >500 |
| Core logic | <500 | <1000 | >1000 |
| Complex modules | <800 | <1500 | >2000 |

---

## Conclusion

The current architecture is mostly sound but suffers from one major issue: the generated parser.ritz is too large. The solution is to enhance the generator to produce modular output. The grammar-driven approach is correct and should be preserved - we just need better tooling to manage the generated code's size.

The AST helpers are hand-written by design (semantic actions need human understanding) but should also be split into logical modules for maintainability.

With these changes, the Ritz parser system will be:
- **Modular** - logical separation into files under 500 lines
- **Maintainable** - never hand-edit generated code
- **Extensible** - grammar changes flow cleanly through the pipeline
- **Understandable** - clear separation of concerns
