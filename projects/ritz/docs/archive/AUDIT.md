# Ritz Project Audit - January 2026

## Executive Summary

This audit reviews the entire Ritz project including ritz0 (Python bootstrap compiler), ritzlib (standard library), test infrastructure, and examples. The goal is to identify cleanup opportunities, broken functionality, and establish a solid foundation for continued development.

**Focus: ritz0 stabilization only** - ritz1 (self-hosted compiler) is deferred until ritz0 is fully stable.

---

## 1. Example Status

### Compilation Status (ritz0) - ✅ ALL WORKING

| Status | Count | Examples |
|--------|-------|----------|
| **Working** | 51 | All examples (01-51) |
| **Special** | 1 | 04_true_false (two separate binaries) |

### Previously Broken (Now Fixed)

| Example | Issue | Fix |
|---------|-------|-----|
| 11_grep | `Vec$u8.len()` not found | UFCS method fallback in monomorphizer |
| 13_sort | `Vec$LineBounds.swap()` not found | UFCS method fallback in monomorphizer |
| 15_cut | `Vec$u8.clear()` not found | UFCS method fallback in monomorphizer |
| 50_http | `Vec$u8.len()` not found | UFCS method fallback in monomorphizer |
| 51_loadtest | `Vec$u8.len()` not found | UFCS method fallback in monomorphizer |

### Fix Applied

Added UFCS (Uniform Function Call Syntax) method resolution in two places:
1. **`ritz0/monomorph.py`**: `_register_method_instantiation()` - triggers monomorphization of `vec_method<T>` when `v.method()` is called on `Vec<T>`
2. **`ritz0/emitter_llvmlite.py`**: `_find_method_fallback()` - maps `Vec$T.method()` to `vec_method$T(&self)` at emit time

---

## 2. ritz0 Codebase Analysis

### File Inventory

| File | Lines | Purpose |
|------|-------|---------|
| emitter_llvmlite.py | 4,284 | LLVM IR generation (largest file) |
| monomorph.py | 1,500+ | Generic monomorphization |
| parser.py | 1,400+ | Recursive descent parser |
| type_checker.py | 838 | Type checking pass |
| import_resolver.py | 675 | Module imports |
| move_checker.py | 461 | Ownership checking |
| lexer.py | 475 | Tokenization |
| metadata.py | 454 | Incremental compilation cache |
| ritz_ast.py | 490 | 69 AST node types |
| name_resolver.py | 389 | Symbol resolution |
| ritz0.py | 337 | Main entry point |

### Dead Code Identified

| File | Function | Status |
|------|----------|--------|
| monomorph.py | `_generate_specializations()` | Replaced by iterative version |
| parser.py | `parse()` | Unused, `parse_module()` is actual entry |
| emitter_llvmlite.py | `emit()` | Unused, `emit_module()` is actual entry |

### Duplicate Logic

Type equality checking appears in 3 places:
- `emitter_llvmlite.py::_types_equal()`
- `import_resolver.py::_types_equal()`
- `type_checker.py::_types_compatible()`

**Recommendation:** Create shared `ritz_types.py` utility module.

---

## 3. ritzlib Analysis

### Module Inventory

| Module | Purpose | Has Tests |
|--------|---------|-----------|
| sys | Syscall wrappers | Indirect |
| str | C-string utilities | Indirect |
| memory | malloc/free/arena | Yes |
| gvec | Generic Vec<T> | Yes |
| string | Owned String type | Yes |
| span | Non-owning Span<T> | Yes |
| buf | Buffer/GrowBuf | Yes |
| io | Print/file I/O | Indirect |
| fs | Filesystem ops | Yes |
| args | Arg parsing | No |
| json | JSON parsing | Yes |
| net | TCP sockets | No |
| hash | FNV-1a hashing | No |
| hashmap | HashMap<K,V> | **INCOMPLETE** |
| option | Option<T> | Yes |
| result | Result<T,E> | Indirect |
| box | Box<T> | No |
| drop | Drop trait | N/A |
| eq | Eq trait | N/A |

### Issues Found

1. **hashmap.ritz is incomplete** - Stub functions that don't work
2. ~~**Duplicate @test attribute** in test_buf.ritz line 15-16~~ ✅ FIXED
3. **Commented impl blocks** in string.ritz lines 37-128

### Missing Tests

- args.ritz
- net.ritz
- hash.ritz
- box.ritz

---

## 4. Test Infrastructure

### Test Locations

| Location | Type | Count |
|----------|------|-------|
| ritz0/test/test_level*.ritz | Language features | 36 levels |
| ritz0/test_*.py | Python unit tests | 7 files |
| ritzlib/tests/ | Library tests | 12 files |
| examples/*/test.sh | Integration | 29 scripts |

### Makefile Targets

| Target | Status |
|--------|--------|
| `make test` | ✅ Works |
| `make unit` | ✅ Works |
| `make ritz` | ✅ Works |
| `make examples` | ✅ Works (all 51 pass) |
| `make valgrind` | ✅ Works |
| `make regression` | ✅ Works |

### Missing Targets

- `make ritzlib-tests` - Run ritzlib tests
- `make coverage` - Code coverage

---

## 5. Grammar Status

**No formal grammar file for ritz0.** Grammar is encoded directly in recursive descent parser.

### ritz1 Grammar

File: `grammars/ritz1.grammar`

This grammar is used by ritzgen to generate the ritz1 parser. It's well-documented but separate from ritz0's parser.

---

## 6. Priority Fixes

### Completed ✅

1. ~~**Add Vec method syntax to ritz0 emitter**~~ ✅
   - UFCS fallback in monomorphizer + emitter
   - All 51 examples now compile and pass tests

2. ~~**Fix duplicate @test in test_buf.ritz**~~ ✅

### High Priority

3. ~~**Create unified `ritz` CLI tool**~~ ✅ Already exists!
   - `ritz build` - compile project
   - `ritz test` - run tests
   - `ritz run` - build and run
   - Reads `ritz.toml` for configuration

4. **Remove or complete hashmap.ritz**

### Medium Priority

5. **Consolidate type equality logic** (3 duplicate implementations)
6. **Remove dead code from ritz0**
7. **Add tests for untested ritzlib modules** (args, net, hash, box)
8. **Remove commented code from string.ritz**

### Low Priority

9. **Create formal grammar for ritz0**
10. **Standardize C-string vs String APIs in fs.ritz**

---

## 7. Recommended Next Steps

1. **Implement `ritz` CLI tool** - Unified build interface
2. **Clean up hashmap.ritz** - Remove stub or implement
3. **Add ritzlib test coverage** - args, net, hash, box modules

---

*Generated: January 8, 2026*
