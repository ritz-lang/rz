# Ritz Language Development TODO

## Goal: Eliminate Raw Pointers from User Code

Replace `*T` pointer soup with proper owned types (`Box[T]`, `Vec[T]`, `String`) that have
clear ownership semantics, automatic cleanup, and elegant syntax.

---

## Phase 1: Computed Struct Layouts (ritz0) ✅ COMPLETE

**Goal:** Compiler computes struct field offsets from parsed definitions. No more magic numbers.

- [x] Add `StructRegistry` to track struct layouts with field offsets
- [x] Compute offsets with proper alignment (1/2/4/8 byte rules)
- [x] Replace hardcoded `_type_size_bytes()` with computed sizes
- [x] Add `sizeof(T)` builtin that returns compile-time size
- [x] Test: All 49 examples still pass
- [x] Test: `sizeof(MyStruct)` works in code

**Implementation Notes:**
- `StructRegistry` class added to `ritz0/emitter_llvmlite.py`
- `FieldLayout` and `StructLayout` dataclasses store computed offsets
- `_ritz_type_size_and_align()` returns (size, alignment) for any Ritz type
- `sizeof(T)` builtin returns compile-time constant for primitives and structs
- Proper x86_64 ABI alignment: u8=1, i16=2, i32=4, i64/pointers=8

---

## Phase 2: Basic Generics (ritz0) ✅ COMPLETE

**Goal:** Enable `Vec[T]`, `Box[T]`, `HashMap[K,V]` in ritzlib.

- [x] Design generics syntax: `struct Vec<T>`, `fn push<T>(v: *Vec<T>, item: T)`
- [x] Parse generic struct definitions with type parameters
- [x] Parse generic function definitions with type parameters
- [x] Parse generic instantiation: `Vec<i32>`, `identity<i32>(x)`
- [x] Implement monomorphization (specialize for each concrete type)
- [x] Test: `fn identity<T>(x: T) -> T` works
- [x] Test: `Vec<i64>` with push/get/free works (valgrind clean)

**Implementation Notes:**
- Generics already implemented in ritz0 with `<T>` syntax (not `[T]`)
- Full monomorphization via `ritz0/monomorph.py`
- `Pair<i32>` becomes `Pair_i32`, `swap<i32>` becomes `swap_i32`
- Multiple type params work: `KeyValue<K, V>` -> `KeyValue_i32_i64`
- Pointer types supported: `Box<*u8>` -> `Box_ptr_u8`
- Tests in `ritz0/test/test_level23.ritz` (needs test runner fix for linking)

---

## Phase 3: Box<T> - Owned Heap Allocation ✅ COMPLETE

**Goal:** `Box<T>` replaces `malloc`/`free` for single heap-allocated values.

- [x] Add `Box<T>` struct to ritzlib (ptr: *T)
- [x] Add `box_new<T>(value: T) -> Box<T>` constructor
- [x] Add `box_get<T>`, `box_set<T>`, `box_as_ptr<T>` accessors
- [x] Add `box_drop<T>` for manual cleanup (explicit Drop)
- [x] Add `box_valid<T>` to check if allocation succeeded
- [x] Test: Box<i32>, Box<i64>, Box<Point>, Box<u8> all work
- [x] Test: All 10 allocations freed, valgrind clean
- [x] Add implicit deref: `b.field` works when `b: Box<MyStruct>`
- [x] Add `Drop` trait concept for automatic cleanup
- [x] Implement destructor calls on scope exit

**Implementation Notes:**
- `ritzlib/box.ritz` defines `Box<T>` with heap allocation via `malloc`/`free`
- Test in `ritz0/test/test_level26.ritz` covers i32, i64, struct, u8 types
- Fixed cross-module generics: import resolver skips cache for generic modules
- Fixed monomorphization: specialized functions marked `is_monomorphized=True`
- Implicit deref in `_emit_field_access`: Box types auto-deref through `ptr` field

---

## Phase 4: Vec<T> - Dynamic Arrays ✅ COMPLETE

**Goal:** Replace hand-rolled linked lists with proper dynamic arrays.

- [x] Add `Vec<T>` struct to ritzlib (data: *T, len: i64, cap: i64)
- [x] `vec_new<T>() -> Vec<T>` - create empty vec
- [x] `vec_push<T>(v: *Vec<T>, item: T)` - append item
- [x] `vec_pop<T>(v: *Vec<T>) -> T` - remove and return last
- [x] `vec_get<T>(v: *Vec<T>, idx: i64) -> T` - get by index
- [x] `vec_with_cap<T>`, `vec_grow<T>`, `vec_ensure_cap<T>` - capacity management
- [x] `vec_set<T>`, `vec_get_ptr<T>`, `vec_first<T>`, `vec_last<T>` - accessors
- [x] `vec_drop<T>` - explicit Drop (frees backing array)
- [x] Test: Vec<i32>, Vec<i64>, Vec<Point>, Vec<u8> all work
- [x] Test: Push 100 items, verify all values, valgrind clean (15 allocs, 15 frees)
- [x] `v[i]` syntax sugar for `vec_get(&v, i)` (Phase 9.5)
- [x] Implement `Drop` trait for automatic cleanup (Phase 5.5)

**Implementation Notes:**
- `ritzlib/gvec.ritz` defines generic `Vec<T>` with malloc/realloc/free
- Test in `ritz0/test/test_level27.ritz` covers 11 test functions
- Fixed monomorphizer to iterate until fixpoint (handles transitive generic calls)
- `vec_push<T>` calls `vec_ensure_cap<T>` calls `vec_grow<T>` - all properly specialized

---

## Phase 5: String Type ✅ COMPLETE

**Goal:** `String` replaces `*u8` for owned text data.

- [x] Add `String` struct based on `Vec<u8>` to ritzlib
- [x] `string_new() -> String` - create empty string
- [x] `string_from(cstr: *u8) -> String` - from C string literal
- [x] `string_len(s: *String) -> i64` - byte length
- [x] `string_as_ptr(s: *String) -> *u8` - for syscall interop
- [x] `string_push(s: *String, b: u8)` - push byte
- [x] `string_push_str(s: *String, cstr: *u8)` - append C string
- [x] `string_push_string(s: *String, other: *String)` - append String
- [x] `string_eq(a: *String, b: *String) -> i32` - compare Strings
- [x] `string_eq_cstr(s: *String, cstr: *u8) -> i32` - compare to C string
- [x] `string_clone(s: *String) -> String` - deep copy
- [x] `string_starts_with`, `string_ends_with`, `string_contains` - predicates
- [x] `string_clear(s: *String)`, `string_pop(s: *String) -> u8` - mutation
- [x] `string_drop(s: *String)` - explicit Drop (frees Vec<u8>)
- [x] Test: 14 test functions in test_level28.ritz, all pass
- [x] Test: Valgrind clean (19 allocs, 19 frees)
- [x] String literal syntax: `var s: String = "hello"` creates `String` (Phase 9.5)
- [x] Implement `Drop` trait for automatic cleanup (Phase 5.5)

**Implementation Notes:**
- `ritzlib/string.ritz` wraps `Vec<u8>` for storage
- Fixed monomorphizer to rewrite non-generic structs containing generic fields
  (e.g., `String.data: Vec<u8>` → `String.data: Vec_u8`)
- Refactored test_runner.py to use proper separate compilation pipeline
- Removed deprecated `separate_compilation=False` mode from emitter

---

## Phase 5.5: Generic Impl Blocks and Drop Trait ✅ COMPLETE

**Goal:** Add `impl<T> Trait for Type<T>` syntax for generic trait implementations.

- [x] Add `type_params` and `impl_type` fields to `ImplBlock` AST node
- [x] Update parser to handle `impl<T>` syntax
- [x] Update monomorphizer to collect and specialize generic impl blocks
- [x] Use `linkonce_odr` linkage for monomorphized functions (avoids duplicate symbols)
- [x] Add `trait Drop { fn drop(self: *Self) }` to ritzlib
- [x] Add `impl<T> Drop for Box<T>` to ritzlib/box.ritz
- [x] Add `impl<T> Drop for Vec<T>` to ritzlib/gvec.ritz
- [x] Add `impl Drop for String` to ritzlib/string.ritz
- [x] Test: 260 tests pass, valgrind clean
- [x] Automatic destructor calls at scope exit (RAII)

**Implementation Notes:**
- Generic impl blocks: `impl<T> Drop for Box<T>` specializes to `impl Drop for Box_i32`
- Monomorphization creates specialized impl blocks like `Box_i32_drop`, `Vec_u8_drop`
- Uses `linkonce_odr` linkage so linker merges duplicate definitions
- Debug info (`!dbg` metadata) only attached to function definitions, not declarations

---

## Phase 5.6: Automatic Drop (RAII) ✅ COMPLETE

**Goal:** Variables with Drop implementations are automatically cleaned up at scope exit.

- [x] Add `drop_scope_stack` to emitter for tracking variables needing Drop
- [x] Register variables with Drop types when declared (`VarStmt`)
- [x] Emit Drop calls before return statements
- [x] Handle implicit returns (trailing expressions)
- [x] Exclude returned variables from Drop (move semantics)
- [x] Add `ImplMeta` to metadata cache for impl block persistence
- [x] Update import resolver to handle cached impl blocks
- [x] Skip cache for modules with generic impl blocks (need bodies for monomorphization)
- [x] Test: 268 tests pass, valgrind clean (0 leaks)

**Implementation Notes:**
- `drop_scope_stack` tracks (var_name, alloca, ritz_type) tuples per scope
- Variables are dropped in reverse declaration order (LIFO)
- Return statements check if returning a local variable - if so, skip Drop (move semantics)
- Metadata cache now includes `impls` field for impl block metadata
- Non-generic `impl Drop for String` properly cached and restored

---

## Phase 5.7: Implicit Deref for Box<T> ✅ COMPLETE

**Goal:** Enable `b.field` syntax for Box<T> types, automatically dereferencing through the pointer.

- [x] Add `_is_box_type()` helper to detect monomorphized Box types
- [x] Add `_get_box_inner_type_name()` to extract inner type from Box_T
- [x] Add `_struct_has_field()` to check field existence without exceptions
- [x] Modify `_emit_field_access()` to auto-deref Box types
- [x] Handle both value and pointer-to-Box cases
- [x] Test: `b.x` works when `b: Box<Point>` (4 tests in test_level32.ritz)
- [x] Test: All 272 tests pass

**Implementation Notes:**
- When accessing `b.field` on `Box<T>`, if `field` doesn't exist on Box, auto-deref through `ptr`
- Extracts `ptr` field (index 0), then GEPs to the field on the inner type
- Works for both Box values and pointers-to-Box

---

## Phase 6: HashMapI64 ✅ COMPLETE

**Goal:** O(1) lookup replaces O(n) linked list searches.

- [x] Add FNV-1a hash functions (`hash.ritz`): `hash_i32`, `hash_i64`, `hash_u64`
- [x] Add equality functions (`eq.ritz`): `eq_i32`, `eq_i64`, `eq_u64`, `eq_string`
- [x] Add `string_hash()` to String type
- [x] Add `HashMapI64` struct with open addressing (specialized for i64 keys/values)
- [x] `hashmap_i64_new()`, `hashmap_i64_with_cap()` - constructors
- [x] `hashmap_i64_insert()`, `hashmap_i64_get()`, `hashmap_i64_contains()` - core ops
- [x] `hashmap_i64_remove()` with tombstone handling for probe continuity
- [x] `hashmap_i64_grow()` with automatic resize at 75% load factor
- [x] `impl Drop for HashMapI64` for automatic cleanup
- [x] Fix: Initialize struct fields to null before malloc (prevents Drop on garbage)
- [x] Fix: Set entries to null in drop function (prevents double-free)
- [x] Test: 10 tests in test_level33.ritz, all pass
- [x] Test: 282 total tests pass, valgrind clean

**Implementation Notes:**
- Generic `HashMap<K,V>` deferred due to parser limitation with multi-param generic casts
- Parser disallows `as *Type<K, V>` to avoid ambiguity with comparison operators
- Used specialized `HashMapI64` with non-generic types as workaround
- Open addressing with linear probing, power-of-2 capacity for fast modulo
- Entry states: EMPTY(0), OCCUPIED(1), TOMBSTONE(2)
- FNV-1a hash: offset basis 14695981039346656037, prime 1099511628211

---

## Phase 7: Option<T> and Result<T,E> ✅ COMPLETE

**Goal:** Proper error handling, no null pointers.

- [x] Add generic enum syntax: `enum Option<T> { Some(T), None }`
- [x] Add enum codegen (LLVM struct with tag + data)
- [x] Add variant construction: `Some(42)`, `None`
- [x] Handle unit variants as identifiers (no parentheses)
- [x] Add VariantPattern matching in match expressions
- [x] Add `Option<T>` to ritzlib (`option_is_some`, `option_is_none`, `option_unwrap_or`)
- [x] Add `Result<T,E>` to ritzlib (`result_is_ok`, `result_is_err`, `result_unwrap_or`)
- [x] Test: Option and Result with various types (test_level34.ritz, ritzlib/tests/test_option.ritz)

**Implementation Notes:**
- Enums use tagged union layout: `{ i8 tag, [max_size x i8] data }`
- Monomorphization specializes generic enums: `Option<i32>` → `Option_i32`
- Variant constructors resolve using type context from variable declarations
- Pattern matching extracts payload and binds to pattern variables
- Tests in `test_level34.ritz` and `ritzlib/tests/test_option.ritz` cover all functionality

---

## Phase 8: Try Operator (`?`) for Ergonomic Error Handling ✅ COMPLETE

**Goal:** Add the `?` operator for automatic error propagation with Result types.

- [x] Implement try operator (`?`) as postfix expression modifier
- [x] Parse `?` token after expressions in parser.py
- [x] Add `TryOp` AST node wrapping inner expression
- [x] Implement `_emit_try_op()` in emitter_llvmlite.py
  - Check Result discriminant tag (0=Ok, 1=Err)
  - If Err: extract error payload, construct Err result, emit Drop calls, return early
  - If Ok: extract value payload and continue execution
- [x] Add proper scope management and early return with phi nodes
- [x] Support chaining multiple `?` operators
- [x] Handle generic Result<T,E> specialization
- [x] Test: 5 comprehensive tests in test_level35.ritz
  - Basic success with `?`
  - Basic error propagation
  - Chained operators with all success
  - Chained operators with first error
  - Chained operators with second error

**Results:**
- 308 tests pass (297 level + 4 import + 7 option tests)
- All try operator tests passing (5/5)
- Full backward compatibility maintained

**Implementation Notes:**
- Try operator is lowest precedence postfix modifier
- Early return on error uses phi nodes to safely unwind scopes
- Enum discriminant checking: 0 = Ok(T), 1 = Err(E)
- Error value extracted from enum data buffer via bitcast
- Proper Drop behavior on early return

---

## Phase 9: Ownership & Borrowing ✅ COMPLETE

**Goal:** Memory safety without garbage collection.

- [x] Move semantics: values move by default (non-Copy types)
- [x] Borrow syntax: `&T` (shared), `&mut T` (exclusive) - already in parser
- [x] Implement move checker (use-after-move = error)
- [x] Implement borrow checker (aliased mut borrow = error)
- [x] Integrate move checker into compiler pipeline
- [x] Make ownership checking enabled by default (`--no-check-ownership` to disable)
- [x] Handle early returns in control flow (dead code after return)
- [x] Type alias resolution for union types (Copy detection)
- [x] Test: Use-after-move is compile error (16 tests)
- [x] Test: Aliased mutable borrow is compile error
- [ ] Lifetime inference for simple cases (deferred)

**Implementation Notes:**
- `move_checker.py` implements `MoveChecker` class for semantic analysis
- Tracks variable states: `OWNED`, `MOVED`, `BORROWED`, `MUT_BORROWED`
- Copy types (i32, i64, bool, pointers, refs, union types of Copy) don't move
- Use-after-move detected for non-Copy types (structs, etc.)
- Conflicting borrows detected: `&mut` + `&`, `&mut` + `&mut`
- Early return handling: code after `return` is dead, moves in returning branches don't affect other paths
- 16 tests in `test_move_checker.py` covering moves and borrows

---

## Phase 9.5: Syntax Sugar ✅ COMPLETE

**Goal:** Ergonomic syntax for common operations.

- [x] Vec indexing: `v[i]` → `vec_get(&v, i)`
- [x] String indexing: `s[i]` → `string_get(&s, i)`
- [x] String literal inference: `var s: String = "hello"` → `string_from("hello")`
- [x] HashMap indexing: `m[key]` → `hashmap_i64_get(&m, key)`
- [x] HashMap indexed assignment: `m[key] = val` → `hashmap_i64_insert(&m, key, val)`
- [x] Python-style slicing: `s[1:5]` → `string_slice(&s, 1, 5)`
- [x] Slice syntax variants: `s[:5]`, `s[1:]`, `s[:]` with default bounds

**Implementation Notes:**
- Index sugar in `_emit_index()` detects Vec_T, String, and HashMapI64 types
- Slice sugar in `_emit_slice()` handles String and Vec<T> types
- Indexed assignment sugar in `_emit_stmt()` for HashMapI64
- String literal inference in VarStmt/LetStmt when declared type is String
- Monomorphizer auto-registers `vec_slice<T>` and `vec_len<T>` for slice expressions
- All require importing respective ritzlib modules

---

## Phase 10: Complete ritz1 Bootstrap (GH #72)

**Goal:** Self-hosted compiler that compiles itself and produces identical output.

**Current Status:**
- ritz1 builds from ritz0 ✅
- ritz1 emitter handles most statements and expressions ✅
- **Tier 1 Examples:** 11/11 working (all complete!) ✅
- **Method syntax:** Implemented! (Type_method mangling) ✅
- **Generics:** Implemented! (Vec<u8>, vec_new<u8>()) ✅
- **Builtin struct types:** Hardcoded Vec, Span, ArgParser for bootstrap ✅
- **Parameter struct tracking:** Fixed for method calls on pointer params ✅
- **Character literals:** Implemented! ('A', '\n', etc.) ✅
- Tier 2 blocked on: ritzlib.sys import resolution

**Completed:**
- [x] Rewrite ritz1/src/main.ritz from scratch (clean implementation)
- [x] Use ritzgen-generated lexer/parser from grammars/ritz.grammar
- [x] Fix Vec<Token> storage bug (workaround: pre-allocate capacity)
- [x] Compile and run true.ritz (exit code 0)
- [x] Add string literal collection and emission (@.str.N constants)
- [x] Add print() built-in handling (inline syscall)
- [x] Add binary operators (+, -, *, /, <, >, ==, !=, etc.)
- [x] Add unary operators (-, !, &, *, ~)
- [x] Add if/else statement emission
- [x] Add while loop emission
- [x] Add break statement emission
- [x] Add var declarations with allocas
- [x] Add assignment statements
- [x] Add function parameters (emit_fn handles params)
- [x] Add function call expressions
- [x] Add index expressions
- [x] Add type inference for let statements (infer from expression type)
- [x] Fix i8/u8 truncation in var declarations
- [x] Add get_expr_type() for type inference support
- [x] Fix pointer-to-pointer indexing (argv[i] gives *u8, not i32)
- [x] Fix byte-level pointer dereference (`*ptr` where ptr: `*u8` loads i8)
- [x] Add pointee type tracking in AST and emitter
- [x] Create crt0.ll - naked _start entry point with inline asm
- [x] Create sys_compat.ll - syscall wrappers accepting i64 args
- [x] Verify all Tier 1 examples (11/11 pass, valgrind clean)

**Tier 1 Runtime Components:**
| File | Purpose |
|------|---------|
| `t_build/crt0.o` | _start entry point (naked, inline asm) |
| `t_build/sys_compat.o` | Syscall wrappers accepting i64 args |
| `t_build/io_minimal.o` | prints, print_int, print_char helpers |
| `t_build/str_minimal.o` | atoi, strlen, strcmp, etc. |

**Bootstrap Tasks (Remaining):**
- [x] Add method syntax support (.len(), .as_ptr()) - Type_method mangling
- [x] Add generics support (for Vec<T>, Span<T>)
  - [x] Parse `IDENT<type>` for generic types (Vec<u8>)
  - [x] Parse `IDENT<type>(args)` for generic function calls (vec_new<u8>())
  - [x] Mangle names with `$` separator (Vec<u8> → Vec$u8)
- [x] Add builtin struct types (Vec$u8, Span$u8, ArgParser) - hardcoded for bootstrap
- [x] Fix parameter struct tracking for method calls on *Struct params
- [x] Register builtin struct AST nodes for field access on imported types
- [x] Add import resolution (inline imports into module)
  - [x] Parse `-I <path>` for RITZ_PATH
  - [x] Recursive import resolution with cycle detection
  - [x] Merge imported structs, functions, constants into main module
  - [x] Struct/function deduplication to avoid duplicate definitions
  - [x] Fix Vec<T> Drop freeing source buffers (use-after-free bug)
- [x] Add character literal support ('A', '\n', '\t', '\\', etc.)
  - [x] Add CHAR token to grammar
  - [x] Regenerate parser with ritzgen
  - [x] Add EXPR_CHAR_LIT kind and expr_char() helper
  - [x] Add EXPR_CHAR_LIT handling in emitter
- [x] Fix parser_init() uninitialized fields (caused non-deterministic crashes)
- [ ] Add monomorphization for generic functions (Vec<T> → Vec$u8, etc.)
  - [x] Created `monomorph.ritz` with collection, substitution, cloning phases
  - [ ] Debug AST walk crash in `collect_from_fn_body()`
  - [ ] Test with simple generic function instantiation
- [ ] Pre-instantiate common generic functions in ritzlib (vec_new$u8, span_from_vec$u8, etc.)
- [ ] Verify bootstrap produces valid LLVM IR
- [ ] Link Tier 2 examples successfully
- [ ] Verify: ritz1_selfhosted produces identical output to ritz1

---

## Phase 10.5: Code Quality & Hardening

**Goal:** Clean, consistent, well-tested codebase.

**Style Standardization (GH #71):**
- [ ] Standardize 4-space indentation (ritz1 uses 2-space)
- [ ] Run ritzfmt on all .ritz files
- [ ] Add pre-commit hook for formatting check
- [x] Create STYLE.md with coding conventions

**ritzlib Modernization (GH #73):**
- [x] `ritzlib/string.ritz` - Method syntax, String-to-String predicates, slicing
- [x] `ritzlib/io.ritz` - String print functions (print_string, print_i64, etc.)
- [x] `ritzlib/fs.ritz` - String path functions, Result<i64, i32> for file_size
- [x] `ritzlib/buf.ritz` - GrowBuf with Drop trait, malloc/realloc/free, 23 tests
- [x] `ritzlib/json.ritz` - Migrated from ByteVec to Vec<u8>
- [ ] `ritzlib/json.ritz` - Use `Result<JsonValue, JsonError>`
- [ ] `ritzlib/meta.ritz` - Standardize on Result

**Type Consolidation (GH #73):**
- [x] Consolidate ByteVec → Vec<u8> (test_level22.ritz migrated)
- [x] Consolidate I64Vec → Vec<i64> (test_level22.ritz migrated)
- [x] Consolidate PtrVec → Vec<*u8> (test_level22.ritz migrated)
- [x] Fix monomorphizer naming collision (use `$` separator: `vec_get$u8`)
- [x] Update emitter for Box$T, Result$T_E, Vec$T patterns
- [x] Migrate examples 42_json, 43_toml, 44_csv, 47_lisp, 48_ritzfmt to Vec<u8>
- [x] Migrate 49_ritzgen to Vec<u8> (GH #75 fixed - drop flags for conditional scopes)
- [x] Migrate ritzlib/json.ritz to Vec<u8> (was using ByteVec internally)
- [x] Delete deprecated ByteVec, PtrVec, I64Vec types from ritzlib/vec.ritz
- [x] Consolidate LineVec → Vec<LineBounds> (migrated tac, sort, uniq examples)
- [x] Add LineBounds, vec_swap<T>, vec_find_lines, vec_read_all_fd to gvec.ritz
- [x] Delete ritzlib/vec.ritz (LineVec now in gvec.ritz as Vec<LineBounds>)
- [x] Create Span<T> generic type (ritzlib/span.ritz) with 23 tests
- [x] Keep Buffer in buf.ritz (position-tracking view, distinct from Span)

**Trait Receiver Semantics (GH #74):**
- [x] Migrate `self: *Self` to `self: &mut Self` in Drop impls
- [x] Use `&Self` for read-only methods, `&mut Self` for mutating
- [x] Update box.ritz, gvec.ritz, string.ritz
- [x] Update hashmap.ritz - migrated to borrow semantics, added method impl block

**Test Coverage:**
- [x] Comprehensive operator tests (test_level36.ritz)
- [x] Add dual-compiler test suite (test/dual_compiler/) - 31 tests pass on both ritz0 and ritz1
  - Level 1: Exit codes, arithmetic (10 tests)
  - Level 2: Functions, control flow (10 tests)
  - Level 3: Structs, pointers, arrays (10 tests)
  - Level 4: Import system (1 test)
- [ ] Level 5: Generics and monomorphization (blocked on ritz1 monomorph)
- [ ] Test edge cases for all language features
- [ ] Rename test_levelXX.ritz files to descriptive names (e.g., test_generics.ritz, test_box.ritz)
- [ ] Organize tests into tiers matching examples (tier1/, tier2/, etc.)
- [ ] Make unit tests relevant to each example's features

---

## Phase 11: Bootstrap Complete

**Goal:** Self-sufficient Ritz ecosystem.

- [ ] Deprecate ritz0 (Python) as primary compiler
- [ ] Full test suite running on ritz1
- [ ] ritzgen generates ritz1 parser from grammar
- [ ] Documentation complete
- [ ] Release v1.0

---

## Anti-Patterns to Eliminate

| Current Pattern | Problem | Solution |
|-----------------|---------|----------|
| `*T` everywhere | No ownership semantics | `Box[T]`, `Vec[T]`, `&T` |
| `malloc`/`free` | Manual memory management | `Drop` trait, RAII |
| `*u8` for strings | No string safety | `String` type |
| Linked lists | O(n) operations | `Vec[T]`, `HashMap[K,V]` |
| Magic numbers | `parser_alloc(p, 160)` | `sizeof(T)` |
| Hardcoded offsets | Unmaintainable | Computed struct layouts |
| Null pointers | Runtime crashes | `Option[T]` |
| 2-space indent | Inconsistent style | 4-space standard |

---

*Last updated: 2026-01-08*

**Latest**: Nested struct layout and assignment fully working! 35 tests pass on both ritz0 and ritz1.

**Session 32 Progress:**
- Fixed nested struct layout in ritz1 emitter (Rect containing Point fields)
- Fixed nested struct member assignment parsing (`r.origin.x = 10`)
- Added `postfix_expr ASSIGN expr NEWLINE` grammar rule for nested member assignment
- Fixed parser_init to initialize all Parser fields (prevented garbage values)
- All 35 dual-compiler tests pass (levels 1-3)
- Nested structs now emit proper LLVM types: `%Rect = type {%Point, %Point}`

**Session 31 Progress:**
- Added hex literal support (0xFF) to ritz1 lexer and parser
- Added binary literal support (0b1010) to ritz1 lexer and parser
- Created 3 new dual-compiler tests for literal formats
- All 34 tests pass on both compilers

**Session 25 Progress:**
- Created comprehensive test/dual_compiler/ test suite
- Tests Levels 1-4: exit codes, arithmetic, functions, control flow, structs, pointers, imports
- Both ritz0 (Python) and ritz1 (self-hosted) pass all 31 tests
- Discovered known limitations: ~~ritz1 lacks hex literals~~ ✅, syscall runtime, ~~nested struct layouts~~ ✅
- Foundation for systematically advancing toward bootstrap

**Session 24 Progress:**
- Fixed bootstrap pipeline: ritzgen (compiled by ritz0) generates parser files from grammar
- Restored `grammars/ritz1.grammar` as canonical grammar for ritz1
- Added IMPL, FOR, TRAIT tokens to ritz1.grammar
- Added `impl_block` and `generic_params` grammar rules
- Regenerated all `*_gen.ritz` files using ritzgen:
  - `tokens_gen.ritz` - Token constants with IMPL/FOR/TRAIT support
  - `lexer_setup_gen.ritz` - Lexer patterns for all tokens
  - `parser_gen.ritz` - Recursive descent parser with impl block support
- Deleted outdated `tokens.ritz` (was duplicate of tokens_gen.ritz)
- Fixed ritzgen to add missing imports (`nfa`, `lexer_nfa`) to lexer_setup_gen.ritz
- Fixed `impl` keyword collision in ast_helpers.ritz (renamed variable)
- Added `fn_link()` helper for building method lists in impl blocks
- ritz1 compiles successfully and produces valid LLVM IR

**Session 24b Progress (emitter fixes):**
- Fixed pointer-to-struct GEP bug in EXPR_MEMBER handler:
  - When `self: *Point`, the emitter now loads the pointer from alloca before GEP
  - Previously, GEP was done directly on the alloca which is incorrect for pointer types
- Added struct literal return handling:
  - Created `emit_struct_lit_to_alloca()` helper function
  - Modified both `emit_fn` and `emit_impl_method` to handle struct literal implicit returns
  - Properly allocates stack space, initializes fields, loads struct, and returns
- Updated `ritz1/compile.sh` to use single-file compilation with import resolution
- All 179 ritz0 unit tests pass

**Test Results:**
- ✅ ritz1 builds with regenerated parser files
- ✅ `examples/01_hello` compiles and runs correctly with ritz1
- ✅ impl block grammar rules added (parse_impl_block, parse_impl_methods)
- ✅ Generic params grammar rules added (parse_generic_params, parse_type_param_list)
- ✅ Comprehensive impl test passes (struct literal return + pointer method calls)

**Session 25 Progress (character literals):**
- Added CHAR token to `grammars/ritz1.grammar` with pattern `/'([^'\\]|\\.)'/'`
- Regenerated all `*_gen.ritz` files using ritzgen
- Added `EXPR_CHAR_LIT` expression kind to `ast.ritz`
- Added `expr_char()` helper function with escape sequence support:
  - `\n` (newline), `\t` (tab), `\r` (carriage return)
  - `\0` (null), `\\` (backslash), `\'` (single quote)
- Added EXPR_CHAR_LIT handling in emitter (`get_expr_type` and `emit_expr`)
- Fixed lexer pattern: used `is_literal=0` so `.` in `'.'` pattern works as "any char"
- Restored Token struct extended fields (`string_val`, `string_len`) that ritzgen had removed
- ritz1 now compiles character literals correctly

**Test Results (Session 25):**
- ✅ ritz0: 324 tests pass, 47 examples compile, valgrind clean
- ✅ ritz1: Character literal `'A'` compiles to correct value (65)
- ✅ ritz1: Escape sequences work (`\n` = 10, `\t` = 9, etc.)
- ⚠️ Tier 2 examples still blocked on ritzlib.sys import resolution

**Session 26 Progress (generic function call parsing):**
- Fixed ROOT CAUSE of string.ritz functions not being parsed: generic call syntax `vec_new<u8>()` wasn't supported
- Root issue: ritz1 lexer produces `TOK_U8` (keyword) for `u8`, not `TOK_IDENT`
- My initial Alternative 0 in `parse_postfix_op` only checked for `TOK_IDENT` after `<`
- Added `p_is_type_name()` helper to accept both identifiers AND type keywords (i8, i32, i64, u8, u64)
- Generic function calls now parse correctly: `vec_new<u8>()`, `vec_with_cap<i32>()`, etc.
- All string.ritz functions (string_new, string_from, etc.) now being emitted
- Tier 1 examples compile and run correctly with ritz1
- Tier 2 examples (16_tr) generate valid IR with all 200 functions, but:
  - Linking fails due to undefined `vec_ensure_cap$u8` etc.
  - This is expected: monomorphization not yet implemented

**Test Results (Session 26):**
- ✅ Generic call parsing works (`foo<u8>()` syntax)
- ✅ Tier 1 examples: 11/11 compile and run correctly
- ✅ Tier 2 example 16_tr: 200 functions parsed/emitted, IR generated
- ⚠️ Tier 2 linking blocked on monomorphization (generic functions skipped, but calls to `$u8` variants remain)

**Session 27 Progress (ritzgen architecture fix):**
- Fixed the architecture issue: NO LONGER manually editing parser_gen.ritz!
- Added `type_name` grammar rule to `grammars/ritz1.grammar` matching type keywords (i8, i32, u8, etc.) and IDENT
- Added generic call alternative to `postfix_op`: `LT type_name GT LPAREN args? RPAREN`
- Created `postfix_generic_call(p, type_tok, args)` helper in ast_helpers.ritz
- Fixed ritzgen codegen (examples/49_ritzgen/src/codegen.ritz):
  - Added `is_pointer_type()` helper to detect pointer types
  - Modified fallback return to emit `result_1` for struct types instead of `0 as Token`
- Regenerated parser_gen.ritz from grammar using ritzgen_old
- Removed duplicate `parser_alloc` from generated parser (already in ast_helpers)
- Generic call syntax `vec_new<u8>()` correctly generates call to `vec_new$u8`

**NOTE:** ritzgen cannot currently be rebuilt due to clang crash during LLVM IR compilation.
The fix is in the source (codegen.ritz), but ritzgen_old is used for parser generation.
The manual fix (changing `return 0 as Token` to `return result_1`) must be applied after
regenerating parser_gen.ritz until ritzgen is rebuilt.

**Session 28 Progress (address-of struct field):**
- Fixed segfault when compiling files with many imports:
  - Root cause: `call_type_suffix` and `call_type_suffix_len` fields uninitialized in EXPR_CALL nodes
  - Fix: Added explicit initialization to `0` in `expr_call()` and `expr_generic_call()`
- Added u64 type support:
  - Added `U64 = "u64"` token to grammar
  - Updated `type_spec` and `type_name` rules
  - Regenerated parser files with ritzgen_old
- Added address-of struct field support (`&s.data`):
  - Handles direct struct: `var s: MyStruct; &s.field`
  - Handles pointer/reference to struct: `fn foo(s: &mut MyStruct) { &s.field }`
  - Generates correct LLVM GEP instructions for field address

**Test Results (Session 28):**
- ✅ Tier 2 example 16_tr generates valid LLVM IR (8147 lines)
- ✅ No more "cannot take address" errors in generated IR
- ✅ All `&s.data` patterns work for structs and references
- ⚠️ Some examples (03_echo) have pre-existing `alloca void` bug (separate issue)

**Next Steps:**
1. Implement monomorphization in ritz1 (generate Vec$u8, vec_new$u8, etc. from templates)
2. Add nested member access support (s.data.len) - blocked for ritz1 self-compilation
3. Test full Tier 2 examples after monomorphization works
4. Debug clang crash to rebuild ritzgen with the Token return type fix
5. Investigate `alloca void` bug in some examples
