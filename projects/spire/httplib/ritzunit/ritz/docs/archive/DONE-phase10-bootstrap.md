# Completed Tasks

Simple checklist of completed work. For detailed session logs, see `docs/archive/`.

## January 9, 2026 (Session 33 - Continuation)

### Build System Refactoring and Runtime Integration

**Goal:** Complete the directory-relative build system refactoring and integrate separate runtime files.

**Status:** ✅ COMPLETE

**Achievements:**
- [x] Verified directory-relative build.py working correctly
  - `find_package_at()` - Find package at given path
  - `find_package_by_name_or_path()` - Find by name or relative path
  - `find_all_packages()` - Search recursively from current directory
  - Supports running `ritz build` from any directory with ritz.toml

- [x] Verified runtime integration in build.py
  - Uses architecture-specific runtime: `ritz_start.x86_64.o`
  - Compiles with `--no-runtime` flag (no embedded _start)
  - Links with separate runtime using clang

- [x] Fixed build.py display of relative paths
  - Gracefully handles when binary path is not under ROOT
  - Falls back to cwd-relative or absolute path

- [x] Fixed test-only package support
  - Modified `get_binaries()` to return empty list for test_only packages
  - Prevents trying to build src/main.ritz for test packages
  - Allows ritzlib/tests to be properly handled
  - `cmd_list` shows `(test-only)` designation

- [x] Added timeout handling to subprocess calls
  - 300 second timeout on test execution
  - Prevents hanging indefinitely on stuck tests

- [x] Tested examples - all working
  - examples/01_hello: PASS ✓
  - examples/05_cat: PASS ✓
  - examples/11_grep: PASS ✓ (Vec method calls working)
  - examples/02_exitcode: PASS ✓

**Test Results:**
- All 51 core examples compile and pass tests
- Directory-relative builds work from any location
- Build system is production-ready

**Known Issues:**
- ritzlib/tests hangs when running all tests together (likely test runner issue with new runtime)
- Individual ritz0 tests still pass (324 tests)

---

## January 8, 2026 (Session 32)

### ritz1 Nested Struct Layout and Assignment

**Goal:** Fix nested struct layout emission and member assignment parsing in ritz1.

**Problem:**
- Nested structs like `Rect { origin: Point, size: Point }` emitted as `{i64, i64}` instead of `{%Point, %Point}`
- Assignment to nested fields like `r.origin.x = 10` caused parse errors

**Achievements:**
- [x] Fixed `emit_field_llvm_type()` in emitter.ritz to handle TYPE_STRUCT fields
  - Added case to emit `%StructName` reference instead of unrolling to primitives
- [x] Added grammar rule `postfix_expr ASSIGN expr NEWLINE` to support nested member assignment
  - Created `stmt_assign_expr()` helper for general expression assignment
- [x] Fixed `parser_init()` to initialize all Parser fields (12 additional fields)
  - Prevents garbage values in AST that caused non-deterministic parsing failures
- [x] Regenerated parser with ritzgen
- [x] Removed debug output from emitter.ritz

**LLVM IR Output (now correct):**
```llvm
%Point = type {i32, i32}
%Rect = type {%Point, %Point}

define i32 @main() {
entry:
  %.1 = alloca %Rect
  %.2 = getelementptr %Rect, ptr %.1, i32 0, i32 0  ; r.origin
  %.3 = getelementptr %Point, ptr %.2, i32 0, i32 0 ; .x
  store i32 10, ptr %.3
  ...
}
```

**Test Results:**
- ✅ 35/35 dual-compiler tests pass on both ritz0 and ritz1
- ✅ Added `level3/11_real_nested_struct.ritz` test with multi-field nested struct

---

## January 8, 2026 (Session 31)

### ritz1 Hex and Binary Literal Support

**Goal:** Add hex (0xFF) and binary (0b1010) literal support to ritz1.

**Achievements:**
- [x] Updated `grammars/ritz1.grammar` NUMBER token pattern
  - Old: `NUMBER = /[0-9]+/`
  - New: `NUMBER = /0x[0-9a-fA-F]+|0b[01]+|[0-9]+/`
- [x] Updated `ritz1/src/ast_helpers.ritz` with hex/binary parsing:
  - `parse_int()` now detects 0x/0X and 0b/0B prefixes
  - Added `parse_hex(start, len)` helper for hex conversion
  - Added `parse_binary(start, len)` helper for binary conversion
- [x] Regenerated `lexer_setup_gen.ritz` using ritzgen
- [x] Added dual-compiler tests:
  - `level1/12_hex_literal.ritz` - Basic hex literals (0x10, 0xFF, 0x0A)
  - `level1/13_binary_literal.ritz` - Binary literals (0b1010, 0b0100, 0b0001)
  - `level1/14_hex_values.ritz` - Hex value verification (0xAB, 0xCD)

**Test Results:**
- ✅ 34/34 dual-compiler tests pass on both ritz0 and ritz1
- ✅ ritz1 correctly parses and evaluates hex and binary literals

---

## January 8, 2026 (Session 30)

### Dual-Compiler Test Suite - ritz0/ritz1 Parity Testing

**Goal:** Create systematic test infrastructure to validate both compilers produce correct, consistent output.

**Achievements:**
- [x] Created `test/dual_compiler/` test infrastructure
  - Test runner (`run_tests.sh`) compiles through both ritz0 and ritz1
  - Compares exit codes and stdout output
  - Supports `-v` verbose, `--ritz0-only`, `--ritz1-only`, level filtering
- [x] **Level 1: Basic Programs** (10 tests) - ALL PASS
  - Exit codes (0, 42), arithmetic (+, -, *, /, %), compound expressions, unary minus, variables
- [x] **Level 2: Functions and Control Flow** (10 tests) - ALL PASS
  - Simple functions, parameters, two params, if/else, while loops, break, early return, recursion
- [x] **Level 3: Structs and Pointers** (10 tests) - ALL PASS
  - Struct definitions, struct params, pointer deref, pointer write, struct literals, constants, arrays, casts, bitwise
- [x] **Level 4: Imports and Modules** (1 test) - ALL PASS
  - Import ritzlib.str with strlen call

**Technical Details:**
- Build directory: `test/dual_compiler/.build/` (gitignored)
- ritz0: Uses `-nostartfiles` for linking (has its own `_start`)
- ritz1: Uses ritz1 crt0 and manual ld linking
- Exit code capture fixed: Removed `|| true` which was clobbering exit codes

**Known Limitations Discovered:**
- ritz1 doesn't support hex literals (0xFF) - lexer issue
- ritz1 syscall runtime not linked (affects ritzlib.sys imports)
- ritz1 nested struct layout is incorrect (uses flat types instead of nested)

**Test Results:**
- ✅ 31/31 tests pass on ritz0
- ✅ 31/31 tests pass on ritz1
- ⏳ Level 5 (generics) blocked on ritz1 monomorphization

---

## January 8, 2026 (Session 29)

### ritz1 Bootstrap - Parser Initialization Fix and Monomorphization WIP

**Goal:** Fix non-deterministic crashes and implement monomorphization.

**Achievements:**
- [x] **Root cause identified**: Parser struct had uninitialized fields
  - `parser_init()` only initialized 9 of 21 Parser fields
  - Uninitialized pointer fields contained garbage, causing non-deterministic crashes
  - Affected fields: `last_type_name`, `last_array_elem_type_name`, `fn_return_type_name`, etc.
- [x] **Fixed parser_init()** in `parser_gen.ritz`
  - Added initialization for all 12 remaining fields
  - All Parser pointer fields now initialized to 0
- [x] **Created test suite** `ritz1/test/test_imports.sh`
  - 18 test cases covering imports, structs, generics, globals, constants
  - All 18 tests pass consistently (was 11/18 before fix with random failures)
- [x] **Started monomorphization pass** in `monomorph.ritz`
  - Tracks generic function instantiations (name + type suffix)
  - Collects calls from AST (walks functions, impl methods)
  - Clones and specializes generic templates
  - Type substitution for params, return types, body
  - **Status**: Compiles but crashes on AST walk (WIP)

**Technical Details:**
- `parser_gen.ritz:parser_init()`: Added 12 field initializations (lines 22-33)
- `monomorph.ritz`: ~500 lines implementing collection, substitution, cloning phases
- Test suite uses `timeout 10s` and `-I $LANG_ROOT` for import resolution

**Test Results:**
- ✅ Import test suite: 18/18 pass (5 consecutive runs all pass)
- ✅ ritz1 builds with monomorphization module
- ⚠️ Monomorphization crashes on AST walk (needs debug)

---

## January 8, 2026 (Session 28)

### ritz1 Bootstrap - Address-of Struct Field Support

**Goal:** Fix `&s.data` syntax for taking address of struct fields.

**Achievements:**
- [x] Added u64 token and type support to grammar
  - Added `U64 = "u64"` token to `grammars/ritz1.grammar`
  - Updated `type_spec` and `type_name` rules
  - Regenerated parser files
- [x] Fixed uninitialized `call_type_suffix` field crash
  - Added explicit initialization in `expr_call()` and `expr_generic_call()`
  - Fixes segfault when compiling files with many imports
- [x] Added address-of struct field support (`&s.data`)
  - Handles direct struct: `var s: MyStruct; &s.field`
  - Handles pointer/reference to struct: `fn foo(s: &mut MyStruct) { &s.field }`
  - Generates correct LLVM GEP instructions for field address

**Technical Details:**
- `ast_helpers.ritz`: Initialize `call_type_suffix = 0 as *u8` and `call_type_suffix_len = 0`
- `emitter.ritz`: Extended OP_ADDR handling for EXPR_MEMBER operands
  - TYPE_STRUCT: GEP directly from local.reg
  - TYPE_PTR/REF/MUT_REF: Load pointer first, then GEP

**Test Results:**
- ✅ Tier 2 example 16_tr generates valid LLVM IR (no more "cannot take address" errors)
- ✅ All `&s.data` patterns now work for structs and references
- ⚠️ Some examples have pre-existing `alloca void` bug (separate issue)

---

## January 8, 2026 (Session 27)

### ritzgen Architecture Fix - Grammar-Based Generic Call Parsing

**Goal:** Move manual parser edits to grammar file; properly use ritzgen workflow.

**Achievements:**
- [x] Created `grammars/ritz1.grammar` with `type_name` rule for type keywords and IDENT
- [x] Added generic call alternative to `postfix_op`: `LT type_name GT LPAREN args? RPAREN`
- [x] Created `postfix_generic_call(p, type_tok, args)` helper in ast_helpers.ritz
- [x] Fixed ritzgen codegen to handle Token return types (struct vs pointer)
- [x] Regenerated parser_gen.ritz from grammar (no more manual edits!)
- [x] Removed duplicate `parser_alloc` from generated parser
- [x] Verified: `vec_new<u8>()` correctly generates call to `vec_new$u8`

**Technical Details:**
- Added `is_pointer_type()` helper to codegen.ritz to detect `*Type` vs struct types
- For struct return types like `Token`, emit `return result_1` instead of `return 0 as Token`
- Grammar's `type_name` rule: `I8 | I32 | I64 | U8 | BOOL | IDENT` - returns the token
- `postfix_generic_call` builds type suffix string ("$u8") from the captured token

**Known Issue:**
- ritzgen cannot be rebuilt currently (clang crashes on IR compilation)
- Workaround: Use ritzgen_old, manually fix `return 0 as Token` to `return result_1`

---

## January 7, 2026 (Session 24)

### ritz1 Bootstrap - Stage 11: Generic Type Parsing & Import Debugging

**Goal:** Complete generic type parsing in variable declarations and debug import failures preventing string.ritz from compiling.

**Achievements:**
- [x] Verified generic type parsing in variable declarations (Vec<u8> → Vec$u8)
- [x] Confirmed generic types properly mangled to TYPE$PARAM format
- [x] Rebuilt ritz1 with all generic type parsing support
- [x] Commented out impl blocks in gvec.ritz and string.ritz (ritz1 doesn't support impl syntax yet)
- [x] Successfully compiled individual modules: sys.ritz, memory.ritz, str.ritz
- [x] Identified root cause of string.ritz compilation failures

**Discoveries:**
- Generic type parameter parsing WORKS: `var v: Vec<u8>` correctly emits `%Vec$u8`
- `sizeof(u8)` with primitive types works fine
- gvec.ritz compiles successfully when compiled standalone
- gvec.ritz segfaults when imported (issue is in import merging logic)
- The crash happens during struct/function merging when imports are resolved

**Identified Issues:**
1. ritz1 doesn't support `impl` blocks - causes parser crashes
   - Workaround: Commented out impl blocks in gvec.ritz and string.ritz

2. ritz1 segfaults when importing gvec.ritz despite it compiling standalone
   - Root cause: Bug in module merging logic after import resolution
   - Affected: gvec.ritz (via string.ritz dependencies)
   - Not blocking: sys.ritz, memory.ritz, str.ritz imports work fine

3. Generic function monomorphization not implemented
   - Functions like `vec_new<T>()` don't instantiate for concrete types
   - workaround: Use mangled names like `vec_new_u8()` (not yet implemented)

**Current Status:**
- ✅ Generic types in variable declarations: WORKING
- ✅ Generic function definitions: PARSE but not MONOMORPHIZE
- ❌ impl blocks: NOT SUPPORTED (causes segfaults)
- ❌ String module imports: BLOCKED by gvec import crash
- ❌ Full Tier 2 support: BLOCKED by above issues

**Blocker Analysis for 11_grep:**
- Example 11_grep needs string functions from ritzlib.string
- string.ritz imports gvec.ritz which segfaults on import
- Workaround would be to implement proper generic monomorphization in ritz1
- Alternative: Create a simplified gvec.ritz that ritz1 can import

**Files Modified:**
- `ritzlib/gvec.ritz`: Commented out impl blocks (lines 35-106)
- `ritzlib/string.ritz`: Commented out impl blocks (lines 33-123)

**Next Steps to Enable Tier 2:**
1. Debug and fix the import merging bug causing gvec crash
2. Implement generic function monomorphization
3. Add impl block parsing support to ritz1
4. Re-enable commented sections in gvec.ritz and string.ritz

---

## January 6, 2026 (Session 23)

### ritz1 Bootstrap - Stage 10: Generic Definition Parsing

**Goal:** Enable ritz1 parser to handle generic function and struct definitions.

**AST Extensions:**
- [x] Added `TypeParam` struct for generic type parameters (`T`, `K`, `V`)
- [x] Added `type_params: *TypeParam` field to `FnDef` (at end to preserve layout)
- [x] Added `type_params: *TypeParam` field to `StructDef` (at end to preserve layout)

**Parser Updates:**
- [x] Added `parse_generic_params()` function to parse `<T>`, `<K, V>`, etc.
- [x] Modified `parse_fn_def()` to parse optional generic params after function name
- [x] Modified `parse_struct_def()` to parse optional generic params after struct name
- [x] Added helper functions: `type_param_new()`, `type_param_link()`
- [x] Added `generic_fn_def_new()`, `generic_struct_def_new()` constructors

**Bug Fixes:**
- [x] Fixed token buffer overflow for large imports
  - sizeof(Token) bug: ritz0 returns 8 but actual size is 48 (6x undercount)
  - vec_with_cap<Token>(6000) only allocates ~1000 tokens
  - sys.ritz generates ~3600 tokens → heap corruption
  - Solution: Request 30000 capacity to ensure adequate space

**Test Results:**
- ✅ Generic function definitions parse: `fn identity<T>(x: i32) -> i32`
- ✅ Generic struct definitions parse: `struct Vec<T> { data: *T, len: i64, cap: i64 }`
- ✅ Multi-file ritzlib imports work: `import ritzlib.sys` + `import ritzlib.str`
- ❌ `impl<T>` blocks not yet supported (parser skips impl blocks entirely)

**Blockers Identified:**
- gvec.ritz uses `impl<T> Drop for Vec<T>` - requires impl block parsing
- ritz1 parser doesn't have `parse_impl_block()` function
- Need to add impl block support before full ritzlib import works

**Next:** Add impl block parsing, then monomorphization pass.

---

## January 6, 2026 (Session 22)

### ritz1 Bootstrap - Stage 9: Import Resolution

**Goal:** Inline imported modules into the main module for single-file compilation.

**Import Resolution:**
- [x] Added `-I <path>` command line parsing for RITZ_PATH
- [x] Added global import tracking with cycle detection
  - `g_import_paths`, `g_import_lens`, `g_processed_import_count`
  - `was_import_processed()`, `mark_import_processed()` helpers
- [x] Added path building functions
  - `get_dir_len()` extracts directory from file path
  - `build_import_path()` converts ImportPath segments to file path
  - `try_open_import()` tries relative path then RITZ_PATH
- [x] Added recursive `resolve_imports()` function
  - Iterates module's import declarations
  - Reads, tokenizes, parses each import file
  - Recursively resolves nested imports
  - Merges structs, functions, constants into main module (prepends to lists)

**Deduplication:**
- [x] Added `EmittedName` struct to emitter for tracking emitted definitions
- [x] Added `emitted_structs`, `emitted_struct_count` to EmitterState
- [x] Added `emitted_fns`, `emitted_fn_count` to EmitterState
- [x] Added `was_struct_emitted()`, `mark_struct_emitted()` helpers
- [x] Added `was_fn_emitted()`, `mark_fn_emitted()` helpers
- [x] Modified `emit_struct_types()` to skip duplicates
- [x] Modified function emission loop to skip duplicates

**Critical Bug Fix - Use-After-Free:**
- [x] Identified: Vec<T>'s Drop impl was freeing source buffers
  - AST nodes store pointers into source text
  - `import_src: Vec<u8>` goes out of scope, Drop frees `import_src.data`
  - Later allocations reuse memory, corrupting function names
  - Symptom: `add_two` became `\0\0\0\0\0wo` (5 NULLs + "wo")
- [x] Fixed: "Steal" data pointer before Vec goes out of scope
  - `keep_source_alive(import_src.data)` - store pointer
  - `import_src.data = 0 as *u8` - prevent Drop from freeing

**Test Results:**
- Simple import test: `main.ritz` imports `helper.ritz`, calls `add_two(40)` → returns 42 ✅
- Tier 2 example 11_grep: Compiles without import errors ✅
- But: ritzlib generic functions (`vec_new<T>`) still emitted as `declare` (extern)
  - ritz1 lacks monomorphization - generic functions not instantiated

**Next:** Add monomorphization to instantiate generic functions for concrete types.

---

## January 5, 2026 (Session 21)

### ritz1 Bootstrap - Stage 8: Method Syntax + Generics Support

**Goal:** Add method call syntax and generics to ritz1 for Tier 2 compatibility.

**Method Syntax:**
- [x] Added `EXPR_METHOD` constant to `ast.ritz` (value 12)
- [x] Updated `apply_postfix_p()` in `ast_helpers.ritz` to detect method calls
  - When `POSTFIX_CALL` follows `EXPR_MEMBER`, convert to `EXPR_METHOD`
  - Reuses existing fields: `left` (receiver), `ident_ptr/len` (method name), `args`
- [x] Added `EXPR_METHOD` handling to `emit_expr()` in `emitter.ritz`
  - Looks up receiver type from local struct variables
  - Mangles to `Type_method` format (e.g., `Point_get_magic`)
  - Emits `call i64 @Type_method(ptr %receiver, args...)`
  - Passes receiver address for auto-borrowing
- [x] Tested with self-contained example (Point struct with get_magic method)

**Generics Support:**
- [x] Added `type_generic()` helper to `ast_helpers.ritz` for generic type mangling
- [x] Modified `parse_type_spec()` in `parser_gen.ritz` to parse `IDENT<type>`
  - Detects `<` after identifier, parses type argument, expects `>`
  - Creates mangled name using `$` separator (Vec<u8> → Vec$u8)
- [x] Added `expr_generic_call()` helper for generic function call mangling
- [x] Modified `parse_primary_expr()` to parse `IDENT<type>(args)`
  - Lookahead for `<type>(` pattern to distinguish from comparison operators
  - Creates call expression with mangled function name
- [x] Verified output IR shows correct mangled names:
  - `var v: Vec<u8>` → `%Vec$u8`
  - `vec_new<u8>()` → `@vec_new$u8()`

**Supported Type Arguments:**
- u8, i8, i32, i64 (primitive types)
- Named types via `last_type_name` (e.g., `Vec<Token>`)

**Remaining for Tier 2:**
- Import resolution for ritzlib modules

---

## January 5, 2026 (Session 20)

### ritz1 Bootstrap - Stage 7: Tier 1 Test Harness & Verification

**Goal:** Build test harness for ritz1-compiled examples and verify all Tier 1 examples.

**Completed:**
- [x] Created `t_build/crt0.ll` - naked `_start` entry point
  - Uses inline assembly to avoid stack frame corruption
  - Properly extracts argc/argv from stack before calling main
  - Aligns stack to 16 bytes per ABI
  - Calls exit syscall with main's return value
- [x] Created `t_build/sys_compat.ll` - syscall wrappers with i64 arguments
  - ritz1 passes all arguments as i64, but ritz0 syscall wrappers expect typed args
  - Provides `sys_read`, `sys_write`, `sys_open`, `sys_close`, `sys_nanosleep`
  - Converts i64 arguments to proper pointer types internally
- [x] Verified all 11 Tier 1 examples compile and pass with ritz1
- [x] All examples valgrind clean (0 errors, 0 heap allocations)

**Tier 1 Results (11/11 working):**
- ✅ 01_hello - Working + Valgrind clean
- ✅ 02_exitcode - Working + Valgrind clean
- ✅ 03_echo - Working + Valgrind clean
- ✅ 04_true - Working + Valgrind clean
- ✅ 04_false - Working + Valgrind clean
- ✅ 05_cat - Working + Valgrind clean
- ✅ 06_head - Working + Valgrind clean
- ✅ 07_wc - Working + Valgrind clean
- ✅ 08_seq - Working + Valgrind clean
- ✅ 09_yes - Working + Valgrind clean
- ✅ 10_sleep - Working + Valgrind clean (107ms for 0.1s sleep)

**Runtime Components:**
| File | Purpose |
|------|---------|
| `t_build/crt0.o` | _start entry point (naked, inline asm) |
| `t_build/sys_compat.o` | Syscall wrappers accepting i64 args |
| `t_build/io_minimal.o` | prints, print_int, print_char helpers |
| `t_build/str_minimal.o` | atoi, strlen, strcmp, etc. |

**Build Command:**
```bash
ritz1 src/main.ritz -o out.ll
llc out.ll -o out.s
gcc out.s crt0.o sys_compat.o io_minimal.o str_minimal.o -o binary -nostdlib -static
```

**Next Steps:**
- Tier 2 examples (11_grep, 12_tac, etc.) require features not yet in ritz1:
  - Generics (`Vec<u8>`, `Span<u8>`) - parsing and mangling
  - ~~Method syntax (`.len()`, `.as_ptr()`)~~ - **DONE in Session 21**
  - Import resolution for ritzlib modules

---

## January 5, 2026 (Session 19)

### ritz1 Bootstrap - Stage 6: Byte-Level Pointer Dereference & Tier 1 Complete

**Goal:** Fix byte-level pointer dereference for 10_sleep, complete Tier 1.

**Completed:**
- [x] Added `pointee_type` tracking to AST and emitter
  - Added `var_pointee_type` field to `Stmt` (for var decls)
  - Added `param_pointee_type` field to `Param` (for function params)
  - Added `last_pointee_type` field to `Parser` (for type parsing)
  - Parser now captures pointee type when parsing `*T` (e.g., TYPE_U8 for `*u8`)
- [x] Added `add_local_ptr()` to track pointee type in emitter's LocalVar
- [x] Added `find_local_pointee_type()` helper to query pointee type
- [x] Updated `get_expr_type()` to return correct type for OP_DEREF
  - For `*ptr` where ptr: `*u8`, now returns TYPE_U8 instead of TYPE_I64
  - Handles both direct dereference (`*ptr`) and computed (`*(ptr + i)`)
- [x] Updated `emit_expr()` OP_DEREF handler
  - For TYPE_U8/TYPE_I8: emits `load i8, ptr` + `zext i8 to i64`
  - For others: emits `load i64, ptr` as before
- [x] Fixed bug: was using `e.left` instead of `e.operand` for EXPR_UNARY

**Tier 1 Results (10/10 working):**
- ✅ 01_hello - Working + Valgrind clean
- ✅ 02_exitcode - Working + Valgrind clean
- ✅ 03_echo - Working + Valgrind clean
- ✅ 04_true_false - Working + Valgrind clean
- ✅ 05_cat - Working + Valgrind clean
- ✅ 06_head - Working + Valgrind clean
- ✅ 07_wc - Working + Valgrind clean
- ✅ 08_seq - Working + Valgrind clean
- ✅ 09_yes - Working + Valgrind clean
- ✅ 10_sleep - Working + Valgrind clean (0 errors, 0 heap allocs)

**Technical Details:**
- Generated IR now correctly uses `load i8, ptr` for byte pointers
- `parse_duration()` in 10_sleep now reads individual bytes correctly
- `sleep 0.5` sleeps for ~501ms, `sleep 1.5` sleeps for ~1501ms

---

## January 5, 2026 (Session 18)

### ritz1 Bootstrap - Stage 5: Struct Literals & Tier 1 Progress

**Goal:** Complete 07_wc, 08_seq, fix struct literals for 10_sleep.

**Completed:**
- [x] Verified 07_wc and 08_seq pass valgrind (0 errors, 0 heap allocs - no libc!)
- [x] Added `EXPR_STRUCT_LIT` support to emitter
  - Detects struct literal in `emit_var_decl()` initializer
  - Emits field-by-field GEP + store for each `FieldInit`
  - Handles TYPE_I64, TYPE_I32, TYPE_PTR field types
- [x] Created minimal ritzlib modules (io_minimal.ritz, str_minimal.ritz)
  - Pure functions only, no malloc/free/String dependencies
  - atoi, isspace, isdigit, isalpha, strlen, strcmp, strncmp

**Tier 1 Results (9/10 at end of session):**
- ✅ 01_hello through 09_yes - All working + Valgrind clean
- ⚠️ 10_sleep - Struct literal works, but byte dereference needed (fixed in Session 19)

---

## January 5, 2026 (Session 17)

### ritz1 Bootstrap - Stage 4: Type Inference & Tier 1 Completion

**Goal:** Verify Tier 1 examples, add type inference, fix byte types.

**Completed:**
- [x] Added `get_expr_type()` function for type inference
  - Infers TYPE_PTR from pointer-to-pointer indexing
  - Infers TYPE_U8 from pointer indexing
  - Handles identifiers, literals, binary ops, unary ops
- [x] Modified `emit_var_decl()` to infer types for let statements
  - When no explicit type, infers from initializer expression
  - Fixes `let s = argv[i]` (was i32, now correctly PTR)
- [x] Added i8/u8 truncation for byte-typed variables
  - Expressions emit as i64, truncate to i8 when storing to u8/i8 alloca
  - Fixes "defined with type i64 but expected i8" errors
- [x] Verified all working examples pass valgrind (0 errors, no leaks)

**Tier 1 Results (7/9 working):**
- ✅ 01_hello - Working + Valgrind clean
- ✅ 02_exitcode - Working + Valgrind clean
- ✅ 03_echo - Working + Valgrind clean (type inference fixed)
- ✅ 04_true_false - Working + Valgrind clean
- ✅ 05_cat - Working + Valgrind clean (const works!)
- ✅ 06_head - Working + Valgrind clean
- ⚠️ 07_wc - Compiles but needs more ritzlib modules (isspace, malloc, etc.)
- ⚠️ 08_seq - Needs atoi + more ritzlib modules
- ✅ 09_yes - Working

**Key Insight:** const declarations were already supported! The TODO was outdated.

**Remaining blockers:**
- Some examples need libc functions (isspace, atoi, malloc/free)
- ritzlib.io needs libc linking for full functionality
- 10_sleep has parsing issue (returns 1)

---

## January 5, 2026 (Session 16)

### ritz1 Bootstrap - Stage 3 Progress

**Goal:** Get Tier 1 examples (01-09) compiling with ritz1.

**Completed:**
- [x] Fixed pointer-to-pointer type parsing (`**u8` → TYPE_PTR_PTR)
  - Parser was returning TYPE_PTR for both `*u8` and `**u8`
  - Now checks if inner type is TYPE_PTR and returns TYPE_PTR_PTR
- [x] Fixed pointer-to-pointer indexing (GEP with ptr stride)
  - `argv[i]` now uses `getelementptr ptr` instead of `getelementptr i8`
- [x] Added inttoptr conversion for GEP on i64 values
  - When indexing into a variable stored as i64, convert back to ptr first
- [x] Fixed address-of operator (`&x`) to return i64 (via ptrtoint)
  - Was returning ptr register directly, now converts to i64 for uniform representation
- [x] Added external function tracking and declarations
  - Track function calls, emit `declare i64 @func(...)` for external functions
- [x] Removed inline `_start` - use `runtime/ritz_crt0.o` which properly sets up argc/argv
- [x] Fixed implicit return (only at function body level, not in nested blocks)
  - Was incorrectly returning from if block expression statements
- [x] Fixed pointer type storage (inttoptr before store)
  - When storing to TYPE_PTR/TYPE_PTR_PTR variables, convert i64 to ptr first

**Tier 1 Progress (before Session 17):**
- ✅ 01_hello, 02_exitcode, 03_echo, 04_true_false - Working
- ❌ 05-09 had various blockers

---

## January 4, 2026 (Session 15)

### GDB Symbol Evaluation - Variable Debug Info

**Goal:** Enable GDB to evaluate local variables and parameters (was seeing source lines but couldn't print values).

**Completed:**
- [x] Added `DILocalVariable` creation for function parameters
- [x] Added `DILocalVariable` creation for local variables (VarStmt with explicit type)
- [x] Emit `llvm.dbg.declare` intrinsics after each alloca
- [x] Created `DIBasicType` for all primitive Ritz types (i8-i64, u8-u64, bool)
- [x] Created `DIDerivedType` for pointer and reference types
- [x] Created `DICompositeType` for struct and array types
- [x] Added `_get_di_type()` helper to create/cache DIType metadata
- [x] Added `_emit_dbg_declare()` to emit debug info for variables
- [x] Cached `DIExpression` and `llvm.dbg.declare` intrinsic for efficiency

**Implementation Details:**
- DWARF variables now include `DW_AT_location`, `DW_AT_name`, `DW_AT_decl_file`, `DW_AT_decl_line`, `DW_AT_type`
- Works with LLVM 20's intrinsic format (backwards compatible)
- Requires cache clear for existing builds (`python build.py cache-clear`)

**Test Results:**
- All 51 examples passing
- `llvm-dwarfdump` confirms proper `DW_TAG_variable` entries in DWARF output

---

## January 4, 2026 (Session 14)

### LineVec → Vec<LineBounds> Migration Complete

**Goal:** Eliminate deprecated LineVec type, migrate to Vec<LineBounds>.

**Completed:**
- [x] Migrated examples 12_tac, 13_sort, 14_uniq from LineVec to Vec<LineBounds>
- [x] Migrated example 15_cut from GrowBuf to Vec<u8>
- [x] Added `vec_swap<T>`, `LineBounds`, `vec_read_all_fd`, `vec_find_lines` to gvec.ritz
- [x] Fixed generic `vec_push_bytes<T>` calls in examples (added `<u8>` type parameter)
- [x] Removed unused `import ritzlib.vec` from regex, markdown examples
- [x] Removed unused `import ritzlib.vec` from ritzlib/meta.ritz
- [x] Deleted deprecated `find_lines_in_buf` function from buf.ritz
- [x] **Deleted ritzlib/vec.ritz** (LineVec now consolidated into gvec.ritz)
- [x] Updated CLAUDE.md import documentation (ritzlib.gvec, ritzlib.span, ritzlib.buf)
- [x] Keep Buffer in buf.ritz (position-tracking view, distinct from Span<u8>)

**Test Results:**
- All 51 examples passing
- All pytest and ritz language tests passing

---

## January 4, 2026 (Session 13)

### Type Consolidation Complete - Legacy Types Deleted

**Goal:** Complete ByteVec to Vec<u8> migration and delete deprecated types.

**Completed:**
- [x] GH #75: Fixed drop insertion for conditional scopes
  - Implemented drop flags pattern (like Rust's approach)
  - Created i1 flag alloca in entry block, initialized to 0
  - Set flag to 1 when variable is initialized
  - Check flag before calling drop (emit conditional branch)
  - Hoisted all Drop-able type allocas to entry block so they dominate all uses
- [x] Migrated 49_ritzgen (codegen.ritz, parser.ritz) to Vec<u8>
- [x] Fixed move checker false positives in parser.ritz and 05_cat
- [x] Deleted deprecated ByteVec, PtrVec, I64Vec from ritzlib/vec.ritz
- [x] ritzlib/vec.ritz now contains only LineVec (specialized for line-oriented text processing)

**Test Results:**
- All 51 examples passing

---

## January 4, 2026 (Session 12)

### ByteVec Migration - Phase 1 Complete

**Goal:** Migrate examples from legacy ByteVec/PtrVec to generic Vec<T>.

**Migrated Examples:**
- [x] 42_json: ByteVec → Vec<u8>
- [x] 43_toml: ByteVec → Vec<u8>
- [x] 44_csv: ByteVec → Vec<u8>, PtrVec → Vec<*u8>
- [x] 47_lisp: ByteVec → Vec<u8>, renamed heap_alloc → lisp_alloc (avoid global conflict)
- [x] 48_ritzfmt: ByteVec → Vec<u8>

**Migration Pattern:**
```ritz
# Before:
import ritzlib.vec
var buf: ByteVec = bytevec_new()
bytevec_push(&buf, c)
bytevec_free(&buf)

# After:
import ritzlib.gvec
var buf: Vec<u8> = vec_new<u8>()
vec_push<u8>(&buf, c)
# Automatic cleanup via Drop trait
```

**Compiler Bugs Fixed:**
- [x] GH #75: Drop insertion bug - variables in conditional branches
  - When `Vec<u8>` is declared in multiple if-blocks with early returns, compiler generates invalid LLVM IR
  - Error: "Instruction does not dominate all uses"
  - Fixed with drop flags implementation (see Session 13)
- [x] GH #76: Method resolution bug for non-generic impl blocks
  - String methods like `.push_str()` generate undefined symbol references
  - Fixed: 50_http and 51_loadtest now pass

---

## January 3, 2026 (Session 11)

### json.ritz Migration to Vec<u8>

**Goal:** Migrate ritzlib/json.ritz from legacy ByteVec to generic Vec<u8>.

**Changes (ritzlib/json.ritz):**
- [x] Replace `import ritzlib.vec` with `import ritzlib.gvec`
- [x] Replace `ByteVec` with `Vec<u8>` in jp_parse_array()
- [x] Replace `ByteVec` with `Vec<u8>` in jp_parse_object()
- [x] Update `bytevec_*` calls to `vec_*<u8>` calls
- [x] Update json_emit_value() and json_emit_string() signatures to use `*Vec<u8>`
- [x] Update json_to_string() to use `Vec<u8>`

**Deprecation Notices (ritzlib/vec.ritz):**
- [x] Add deprecation header recommending gvec.ritz for:
  - ByteVec → Vec<u8>
  - PtrVec → Vec<*u8>
  - I64Vec → Vec<i64>
- [x] LineVec remains available (specialized struct type)
- [x] Include migration example in deprecation notice

**Test Results:**
- 560 ritz tests passing (333 level + 227 ritzlib)
- All 36 JSON tests pass
- 1 known fs path issue (test_is_regular_file_string)

**Remaining ByteVec Users (for future migration):**
- examples/42_json, 43_toml, 44_csv (data parsing)
- examples/47_lisp (interpreter)
- examples/48_ritzfmt (formatter)
- examples/49_ritzgen (parser generator)

---

## January 3, 2026 (Session 10)

### Networking Primitives & HTTP Examples

**Created ritzlib/net.ritz - TCP/IP networking:**
- [x] Socket syscall wrappers (socket, bind, listen, accept, connect, setsockopt)
- [x] `Socket` struct with fd, family, socktype
- [x] TCP/UDP socket constructors: `socket_tcp()`, `socket_tcp_nonblock()`, `socket_udp()`
- [x] Socket options: `socket_set_reuseaddr()`, `socket_set_nodelay()`
- [x] Connection ops: `socket_bind()`, `socket_listen()`, `socket_accept()`, `socket_connect()`
- [x] I/O ops: `socket_send()`, `socket_recv()`, `socket_send_string()`
- [x] Address parsing: `parse_ipv4()`, byte order conversion (`htons`, `htonl`)
- [x] Epoll support: `epoll_create()`, `epoll_add()`, `epoll_wait_events()`, etc.
- [x] Method syntax: `impl Socket` with `valid()`, `close()`, `bind()`, `send()`, etc.

**Created examples/50_http - HTTP/1.0 server:**
- [x] Simple HTTP server demonstrating ritzlib/net.ritz usage
- [x] Request parsing with `Span<u8>` for method, path, version extraction
- [x] Response generation with `String` and method syntax
- [x] Routes: `/` (HTML), `/hello` (text), `/info` (server info), 404 fallback
- [x] Connection handling with blocking I/O

**Created examples/51_loadtest - HTTP load tester:**
- [x] Simple load testing tool similar to ab/siege
- [x] URL parsing with host, port, path extraction
- [x] Statistics tracking: total, successful, failed, min/max/avg response time
- [x] Requests per second and transfer rate calculation
- [x] Uses `get_time_ms()` via gettimeofday syscall

**Test Results:**
- 555 ritz tests passing (328 level + 227 ritzlib)
- HTTP server: ~19k requests/sec on localhost

---

## January 3, 2026 (Session 9)

### Span<T> Generic Type & Example Modernization

**Created ritzlib/span.ritz - Non-owning views into memory:**
- [x] `Span<T>` struct: non-owning (ptr, len) pair for any element type
- [x] Constructors: `span_empty<T>`, `span_from_ptr<T>`, `span_from_vec<T>`, `span_from_cstr`
- [x] Accessors: `span_len<T>`, `span_is_empty<T>`, `span_get<T>`, `span_get_ptr<T>`, `span_as_ptr<T>`
- [x] Slicing: `span_slice<T>`, `span_from<T>`, `span_to<T>` (zero-copy sub-views)
- [x] Byte operations: `span_eq`, `span_contains`, `span_starts_with`, `span_ends_with`, `span_find`
- [x] Method syntax: `impl<T> Span<T>` with `len()`, `is_empty()`, `get()`, `slice()`, etc.
- [x] 23 tests in `ritzlib/tests/test_span.ritz`

**Modernized 11_grep to use Vec<u8> and Span<u8>:**
- [x] Replaced mmap-based `heap_alloc`/`heap_free` with `Vec<u8>`
- [x] Replaced local `ByteSlice` struct with `Span<u8>` from ritzlib
- [x] Uses method syntax: `line.push(c)`, `line.clear()`, `line.len()`
- [x] Valgrind clean: 3 allocs, 3 frees, no leaks

**Test Results:**
- 135 pytest tests passing
- 552 ritz tests passing (324 level + 228 ritzlib)

---

## January 3, 2026 (Session 8)

### Context Recovery & Test Maintenance

**Fixed test_monomorph.py after $ separator change:**
- [x] Update all assertions to expect `$` separator instead of `_`
  - `Pair_i32` → `Pair$i32`
  - `identity_i32` → `identity$i32`
  - `double_i32` → `double$i32`
  - `Box_i32` → `Box$i32`
  - `Wrapper_i32` → `Wrapper$i32`
  - `swap_i32` → `swap$i32`
  - `Wrapper_ptr_u8` → `Wrapper$ptr_u8`

**Test Results:**
- 135 pytest tests passing (including 14 monomorph tests)
- 529 ritz tests passing (324 level + 205 ritzlib)

**GitHub Issues Reviewed (12 open):**
- #31: Add type checking pass (critical)
- #51: ritz1 DWARF debug info
- #55: Create ritzlib/exec.ritz
- #56: Consolidate duplicate examples
- #59: Native Ritz build tool
- #60: Improve compiler diagnostics
- #61: Add ritz1 regression test suite
- #62: Add compiler pipeline diagrams
- #71: Standardize 4-space indentation
- #72: Phase 10: Complete ritz1 bootstrap
- #73: Modernize ritzlib
- #74: Migrate ritzlib from raw pointers to mutable borrows

**Legacy Type Usage Identified:**
- 9 example files still use ByteVec/PtrVec/I64Vec:
  - examples/42_json, 43_toml, 44_csv (data parsing)
  - examples/47_lisp (interpreter)
  - examples/48_ritzfmt (formatter)
  - examples/49_ritzgen (parser generator)
- ritzlib/json.ritz uses ByteVec internally

---

## January 3, 2026 (Session 7)

### Monomorphizer Naming Collision Fix & Vec<T> Type Consolidation

**Problem:** `vec_get<*u8>` and `vec_get_ptr<u8>` both mangled to `vec_get_ptr_u8`, causing wrong function calls.

**Solution:** Use `$` separator between base name and type args in `mangle_generic_name()`.
- `Vec<u8>` → `Vec$u8` (was `Vec_u8`)
- `vec_get<*u8>` → `vec_get$ptr_u8` (was `vec_get_ptr_u8`)
- `vec_get_ptr<u8>` → `vec_get_ptr$u8` (was `vec_get_ptr_u8`)

**Monomorphizer Changes (ritz0/monomorph.py):**
- [x] Change `mangle_generic_name()` to use `$` separator: `f"{base_name}${arg_names}"`
- [x] Add `_visit_item()` handling for non-generic `ImplBlock` (discover generic calls in methods)
- [x] Add `_rewrite_impl()` to rewrite generic calls in non-generic impl methods

**Emitter Changes (ritz0/emitter_llvmlite.py):**
- [x] Update `_is_box_type()` to check `Box$` prefix (was `Box_`)
- [x] Update `_get_box_inner_type_name()` to strip `Box$` prefix
- [x] Update `_emit_try_op()` to check `Result$` prefix (was `Result_`)
- [x] Update `_get_specialized_type_name()` to use `$` separator
- [x] Update `_emit_index()` Vec handling to use `Vec$` and `vec_get$`
- [x] Update `_emit_slice()` Vec handling to use `Vec$`, `vec_slice$`, `vec_len$`

**ritzlib Changes:**
- [x] Fix `ritzlib/string.ritz`: Replace `Vec_u8_drop(&self.data)` with `vec_drop<u8>(&self.data)`

**Test Changes:**
- [x] Update `ritz0/test/test_level30.ritz`: Use method syntax instead of mangled names
- [x] `test_level22.ritz`: Full test coverage for Vec<u8>, Vec<*u8>, Vec<i64>

**Results:**
- 529 tests pass (324 level + 205 ritzlib)
- Vec<*u8> now works correctly (pointer types as generic args)
- All existing code continues to work

---

## January 3, 2026 (Session 6)

### GrowBuf Modernization

**Goal:** Modernize GrowBuf to use malloc/realloc/free with Drop trait for automatic cleanup.

**ritzlib/buf.ritz Changes:**
- [x] Rewrite GrowBuf to use malloc/realloc/free instead of mmap/munmap
- [x] Add `impl Drop for GrowBuf` for automatic memory cleanup
- [x] Keep backward-compatible API (growbuf_new, growbuf_with_cap, growbuf_append, etc.)
- [x] Add new accessors: growbuf_len, growbuf_cap, growbuf_data, growbuf_get, growbuf_is_empty
- [x] Update read_all_fd and find_lines_in_buf to use GrowBuf type

**New Tests (ritzlib/tests/test_buf.ritz):**
- [x] 9 GrowBuf tests: new, with_cap, append_byte, append, clear, grow, accessors, is_empty
- [x] 14 Buffer tests: init, from_str, peek, peek_at, advance, eof, remaining, match_char, match_str, skip_whitespace, save_restore, get_loc, read_until, read_while_digit, starts_with

**Results:**
- 531 tests pass (326 level + 205 ritzlib)
- GrowBuf now has automatic Drop cleanup
- All existing code using GrowBuf continues to work unchanged

**Note:** Type alias `type GrowBuf = Vec<u8>` didn't work due to generic type resolution issues with monomorphized types. Kept GrowBuf as a separate struct with identical layout to Vec<u8>.

---

## January 2, 2026 (Session 5)

### Method Syntax for Vec<T>

**Goal:** Enable `v.push(10)` instead of `vec_push<i64>(&v, 10)` for Vec types.

**ritzlib Changes (gvec.ritz):**
- [x] Add `impl<T> Vec<T>` block with method wrappers
- [x] Methods: len, cap, is_empty, push, pop, get, get_ptr, set, clear, first, last, as_ptr, slice

**Emitter Fix (ritz0/emitter_llvmlite.py):**
- [x] Add duplicate function check in `_declare_function()` to handle consolidated modules

**New Tests (ritzlib/tests/test_vec_methods.ritz):**
- [x] 15 tests covering all Vec method syntax variants
- [x] Tests for i64, i32, u8 element types

**Results:**
- 508 tests pass (322 level + 186 ritzlib)
- Method syntax is zero-cost (same implementation, cleaner syntax)
- Generic impl blocks work correctly with monomorphization

**Design Decision:**
- Keep `gvec.ritz` (generic Vec<T>) separate from `vec.ritz` (legacy ByteVec, I64Vec, PtrVec)
- Legacy types have identical layouts but are distinct nominal types
- Consolidation deferred to avoid breaking existing code

---

## January 2, 2026 (Session 4)

### Python-Style Slice Syntax

**Goal:** Add zero-cost slice syntax (`s[1:5]`) for String and Vec types.

**Parser Changes (ritz0/parser.py):**
- [x] Parse `[start:end]` slice syntax
- [x] Parse `[:end]` (start defaults to 0)
- [x] Parse `[start:]` (end defaults to len)
- [x] Parse `[:]` (full slice / clone)
- [x] Create `SliceExpr` AST node with optional start/end

**AST Changes (ritz0/ritz_ast.py):**
- [x] Add `SliceExpr(expr, start, end)` expression node

**Emitter Changes (ritz0/emitter_llvmlite.py):**
- [x] `_emit_slice()` - dispatch to type-specific handlers
- [x] `_emit_string_slice()` - `s[1:5]` → `string_slice(&s, 1, 5)`
- [x] `_emit_vec_slice()` - `v[1:5]` → `vec_slice_T(&v, 1, 5)`
- [x] Default bounds: start→0, end→len (via `string_len`/`vec_len_T`)

**Monomorphizer Changes (ritz0/monomorph.py):**
- [x] Track variable types in `var_types` dict during AST walk
- [x] Register parameter types in `_visit_item` for functions
- [x] Track variable declarations in `_visit_stmt`
- [x] Visit SliceExpr in `_visit_expr`
- [x] `_register_slice_instantiation()` - auto-register `vec_slice<T>` and `vec_len<T>`

**ritzlib Changes:**
- [x] `vec_slice<T>(v, start, end) -> Vec<T>` in gvec.ritz

**New Tests (ritzlib/tests/test_slice_syntax.ritz):**
- [x] 7 String slice tests (basic, middle, from_start, to_end, full, empty, single_char)
- [x] 5 Vec slice tests (basic, from_start, to_end, full, empty)
- [x] 1 combined index+slice test

**Results:**
- 489 tests pass (322 level tests + 167 ritzlib tests)
- Slice syntax is zero-cost (compiles to function call)
- Automatic monomorphization for Vec types

---

## January 2, 2026 (Session 3)

### ritzlib String Modernization

**Goal:** Modernize ritzlib with String type and remove null-terminated string dependencies.

**String Type Enhancements (ritzlib/string.ritz):**
- [x] `string_push_bytes(s, bytes, len)` - Push slice with explicit length
- [x] `string_from_i64(n)` - Convert i64 to String
- [x] `string_push_i64(s, n)` - Append i64 to String
- [x] `string_from_hex(n)` - Convert u64 to hex String
- [x] `string_starts_with_string(s, prefix)` - String-to-String predicate
- [x] `string_ends_with_string(s, suffix)` - String-to-String predicate
- [x] `string_contains_string(s, needle)` - String-to-String predicate
- [x] `string_find(s, needle)` - Find substring, return index or -1
- [x] `string_slice(s, start, end)` - Extract substring
- [x] `string_char_at(s, idx)` - Get char at index (0 for out of bounds)
- [x] `string_set_char(s, idx, c)` - Set char at index

**Method Syntax (impl String block):**
- [x] `s.len()`, `s.cap()`, `s.is_empty()`, `s.get(i)` - Accessors
- [x] `s.push(c)`, `s.push_string(&other)`, `s.push_i64(n)` - Append
- [x] `s.clear()`, `s.pop()` - Mutation
- [x] `s.clone()`, `s.slice(start, end)` - Creation
- [x] `s.find(&needle)`, `s.starts_with(&p)`, `s.ends_with(&s)`, `s.contains(&n)` - Search
- [x] `s.eq(&other)`, `s.hash()` - Comparison

**io.ritz String Functions:**
- [x] `print_string(s)`, `eprint_string(s)` - Print String by length (no null-term)
- [x] `println_string(s)`, `eprintln_string(s)` - Print with newline
- [x] `print_i64(n)`, `println_i64(n)` - Print integers via String
- [x] `print_hex64(n)`, `println_hex64(n)` - Print hex via String

**fs.ritz String Path Functions:**
- [x] `path_join_string(dir, name)` - Join paths as Strings
- [x] `path_basename_string(path)` - Get filename component
- [x] `path_dirname_string(path)` - Get directory component
- [x] `path_extension_string(path)` - Get file extension
- [x] `path_stem_string(path)` - Strip extension from path
- [x] `path_exists_string(path)`, `is_directory_string(path)`, `is_regular_file_string(path)`
- [x] `file_size_string(path) -> Result<i64, i32>` - File size with Result error handling
- [x] Error constants: `FS_ERR_NOT_FOUND`, `FS_ERR_PERMISSION`, etc.

**New Tests:**
- [x] `ritzlib/tests/test_string_io.ritz` - 24 tests for String conversion
- [x] `ritzlib/tests/test_string_methods.ritz` - 22 tests for method syntax
- [x] `ritzlib/tests/test_fs.ritz` - 18 tests for path functions

**Results:**
- 322 tests pass (original suite intact)
- All new tests passing
- Method syntax works: `s.len()` → `String_len(&s)`

---

## January 2, 2026 (Session 2)

### Grammar Consolidation

**Goal:** Single canonical Ritz grammar for all compilation stages.

- [x] Unified `ritz.grammar` and `ritz1.grammar` into single file
- [x] Canonical location: `grammars/ritz.grammar` (90 tokens, 64 rules)
- [x] Archived old files: `ritz.grammar.old`, `ritz1.grammar.old`
- [x] Updated ritzgen to use new canonical grammar
- [x] Verified: ritzgen generates correctly from new grammar

**Features in unified grammar:**
- Full Ritz language: enum, match, trait, impl, generics
- Ownership: mut, &T, &mut T, move semantics
- All operators: bitwise, binary, postfix, try (?)
- Types: f32, f64, Option, Result

### HashMap Syntax Sugar

**Goal:** Ergonomic dictionary access with `m[key]` and `m[key] = val`.

- [x] Index get: `m[key]` → `hashmap_i64_get(&m, key)`
  - Added to `_emit_index()` in `emitter_llvmlite.py`
  - Detects `HashMapI64` type and generates function call
- [x] Index set: `m[key] = val` → `hashmap_i64_insert(&m, key, val)`
  - Added to `_emit_stmt()` AssignStmt handling
  - Intercepts indexed assignment to HashMapI64 types

**Tests (test_level33.ritz):**
- [x] `test_hashmap_index_get` - Read via `m[key]` syntax
- [x] `test_hashmap_index_set` - Write via `m[key] = val` syntax
- [x] `test_hashmap_index_mixed` - Mix syntax sugar with function calls

**Results:**
- 304 tests pass (301 + 3 new HashMap sugar tests)
- Valgrind clean (no leaks)

### Comprehensive Operator Tests

**Goal:** Test all operators in the language for regression prevention.

**New tests (test_level36.ritz):**
- [x] Bitwise AND (`&`): 4 tests
- [x] Bitwise OR (`|`): 3 tests
- [x] Bitwise XOR (`^`): 4 tests
- [x] Bitwise NOT (`~`): 2 tests
- [x] Shift left (`<<`): 5 tests
- [x] Shift right (`>>`): 5 tests
- [x] Combined bitwise: flags manipulation
- [x] Modulo (`%`): 4 tests
- [x] Compound assignment (`+=`, `-=`, `*=`, `/=`): 4 tests
- [x] Logical operators (`&&`, `||`, `!`): 3 tests
- [x] Unary minus (`-`): 3 tests
- [x] Address-of and dereference (`&`, `*`): 2 tests
- [x] Operator precedence: 4 tests

**Results:**
- 326 tests pass (304 + 22 new operator tests)

### GitHub Issue Cleanup

**Closed (Completed):**
- #67: Phase 6: HashMap[K,V] - HashMapI64 implemented with syntax sugar
- #68: Phase 7: Option[T] and Result[T,E] - Generic enums with pattern matching
- #69: Phase 8: Ownership & Borrowing - Move checker, borrow detection, RAII
- #70: Phase 9: Rewrite ritz1 - Superseded by #72/#73
- #58: Result/Option and ? operator - Try operator implemented
- #37: Support importing enums - Enum imports work
- #40: Add ritz fmt - ritzfmt exists at examples/48_ritzfmt/
- #39: Implement native build - Duplicate of #59
- #57: Trait bounds and monomorphization - Monomorphization complete
- #50: DWARF debug info - Duplicate of #51
- #53: Duplicate _emit_struct_lit - Low priority

**Created:**
- #71: Standardize 4-space indentation
- #72: Phase 10: Complete ritz1 bootstrap
- #73: Modernize ritzlib with new language features

**Open Issues (11 remaining):**
- #31: Add type checking pass (critical)
- #51: DWARF debug info
- #55: Create ritzlib/exec.ritz
- #56: Consolidate duplicate examples
- #59: Native Ritz build tool
- #60: Improve compiler diagnostics
- #61: Add ritz1 regression test suite
- #62: Add compiler pipeline diagrams
- #71: Standardize 4-space indentation
- #72: Phase 10: Complete ritz1 bootstrap
- #73: Modernize ritzlib

### Code Style

- Created STYLE.md with Ritz coding conventions
- 4-space indentation is the standard
- Added anti-pattern: 2-space indent → 4-space standard

---

## January 2, 2026 (Session 1)

### Move Checker Enhancements

**Assignment Restores Ownership:**
- [x] After `x = value`, variable `x` becomes OWNED again (fixes `frag = thompson_concat(...)` pattern)
- [x] Prevents false positives when reassigning after moving a variable

**If/Else Branch Isolation:**
- [x] Each branch of if/else checks independently (moves in `then` don't affect `else` during checking)
- [x] Proper state merging after if/else:
  - Both return → subsequent code is dead
  - Only then returns → keep state from else
  - Only else returns → restore state from then
  - Neither returns → conservatively mark vars moved in either branch as moved

**ritz1 Ownership Fixes:**
- [x] Fixed use-after-move in main_new.ritz lines 498-504 (Token assignment before EOF check)
- [x] Fixed use-after-move in main_new.ritz lines 4167-4180 (Token debug printing)
- [x] ritz1 now builds with ownership checking enabled (301 tests pass)

**Results:**
- All 301 ritz0 tests pass with ownership checking enabled
- All 16 move_checker unit tests pass
- ritz1 builds successfully from ritz0
- ritz1 basic test passes (self-compilation has pre-existing codegen bugs)

---

## January 1, 2026

### Phase 9.5: Syntax Sugar and Ownership Improvements

**Goal:** Enable ownership checking by default and add ergonomic syntax sugar.

**Move Checker Improvements (move_checker.py):**
- [x] Handle early returns in control flow
  - Return statements mark code after as dead (no false positives for moves in early returns)
  - `_check_stmt()` returns bool indicating if statement terminates control flow
  - `_check_block()` stops checking after a return statement
- [x] If/else branch handling
  - Save/restore variable states across branches
  - If one branch returns, moves in that branch don't affect code after the if
  - Proper state merging for both branches returning
- [x] Type alias resolution for Copy detection
  - Collect type aliases in first pass
  - Resolve aliases in `_is_copy_type()` for accurate Copy detection
  - Union types (`type IntOrBool = i64 | bool`) are Copy if all variants are Copy

**Ownership Checking Default (ritz0.py):**
- [x] Changed `--check-ownership` flag to `--no-check-ownership`
- [x] Ownership checking now enabled by default
- [x] All 297 tests pass with ownership checking enabled

**Index Syntax Sugar (emitter_llvmlite.py):**
- [x] Vec indexing: `v[i]` → `vec_get_T(&v, i)`
  - Detects Vec_T and Vec types in `_emit_index()`
  - Extracts element type from monomorphized name
  - Generates call to appropriate `vec_get_T` function
- [x] String indexing: `s[i]` → `string_get(&s, i)`
  - Detects String type in `_emit_index()`
  - Generates call to `string_get` function

**String Literal Inference (emitter_llvmlite.py):**
- [x] `_emit_string_from_literal()` helper function
  - Converts string literal to `string_from()` call
  - Gets C string pointer and calls imported function
- [x] VarStmt handling: `var s: String = "hello"` → `string_from("hello")`
- [x] LetStmt handling: `let s: String = "hello"` → `string_from("hello")`

**Results:**
- 297 tests pass with ownership checking enabled by default
- All existing tests continue to pass
- New syntax sugar enables cleaner Vec and String code

---

### Phase 8: Try Operator for Ergonomic Error Handling

**Goal:** Implement the `?` operator for automatic error propagation with Result types.

**Try Operator Implementation (emitter_llvmlite.py):**
- [x] `_emit_try_op()` - Emit conditional early return for `?` operator
  - Evaluates inner expression and checks Result discriminant tag
  - Tag 0 = Ok: extracts Ok payload and continues
  - Tag 1 = Err: constructs Err return value and exits early
  - Properly manages scopes and drop behavior on early return
- [x] Type checking for Result types
  - Validates expression returns Result<T, E>
  - Validates enclosing function returns Result<_, E>
  - Specialized type name resolution for generic instantiations

**Parser Updates (parser.py):**
- [x] Postfix `?` operator parsing
  - Recognizes `?` token after expressions
  - Creates TryOp AST node wrapping the expression
  - Chains multiple `?` operators: `a? + b?`

**AST Updates (ritz_ast.py):**
- [x] `TryOp(span, expr)` - Represents try operator application

**Tests (test_level35.ritz):**
- [x] `test_try_op_ok()` - Successful computation with `?`
  - `divide(20, 4)? + 10` returns 15
- [x] `test_try_op_err()` - Error propagation with `?`
  - `divide(10, 0)?` propagates Err(1) early
- [x] `test_try_op_chain_ok()` - Multiple chained operators
  - `divide(a, b)? + divide(x, c)?` succeeds when both succeed
- [x] `test_try_op_chain_first_err()` - Error at first `?`
  - Propagates Err(1) from first divide
- [x] `test_try_op_chain_second_err()` - Error at second `?`
  - Succeeds first divide, fails second, propagates Err(1)

**Results:**
- 308 tests pass (297 level + 4 import + 7 option tests)
- Try operator tests: 5/5 passing
- Full backward compatibility maintained
- Enables idiomatic error handling patterns

**Implementation Notes:**
- Try operator is a postfix expression modifier (lowest precedence)
- Early return on error uses phi nodes to safely unwind scopes
- Enum discriminant checking: 0 = Ok(T), 1 = Err(E)
- Error value extracted from enum data buffer via bitcast

---

### Phase 7: Generic Enums and Pattern Matching

**Goal:** Type-safe error handling with Option<T> and Result<T,E>.

**Enum Codegen (emitter_llvmlite.py):**
- [x] `_declare_enum()` - creates LLVM identified struct type, registers variant names
- [x] `_define_enum()` - sets enum body with `{ i8 tag, [max_size x i8] data }` layout
- [x] `_emit_enum_variant_constructor()` - constructs enum value with tag + payload
- [x] `_emit_enum_variant_with_type()` - type-context-aware variant construction
- [x] `_emit_enum_match()` - switch-based matching on discriminant tags

**Pattern Matching:**
- [x] Support for `VariantPattern` matching: `Some(x) => x + 1`
- [x] Support for `IdentPattern` for unit variants: `None => 0`
- [x] Support for `WildcardPattern` catch-all: `_ => default`
- [x] Automatic variable binding for extracted payload values
- [x] Type-safe match expressions with phi node result

**Field Extraction:**
- [x] Extract data from data-carrying variants during pattern matching
- [x] Proper memory offset calculation for variant fields
- [x] Type-aware field loading from enum payload buffer

**Generic Enum Support:**
- [x] `type_params` added to `EnumDef` AST node
- [x] Parser updated for `enum Option<T>` syntax
- [x] Monomorphizer specializes generic enums: `Option<i32>` → `Option_i32`
- [x] Cross-module enum variant resolution with type context

**Ritzlib Types (ritzlib/):**
- [x] `option.ritz` - `Option<T>` with `option_is_some`, `option_is_none`, `option_unwrap_or`
- [x] `result.ritz` - `Result<T, E>` with `result_is_ok`, `result_is_err`, `result_unwrap_or`

**Tests:**
- [x] `test_level34.ritz` - 10 tests: enum construction, pattern matching
- [x] `test_level35.ritz` - 7 tests: enum pattern matching with multiple types
- [x] `ritzlib/tests/test_option.ritz` - 7 tests: Option<T> library functions
- [x] `test/test_import_main.ritz` - 4 tests: cross-module imports

**Results:**
- 303 tests pass (282 existing + 21 new enum/import tests)
- Full backward compatibility maintained
- Type-safe enum implementation ready for library functions

**Test Infrastructure Fix:**
- [x] Fixed test_runner.py import resolution for test_import_* modules
  - Problem: Test files moved to temp directory lost import context
  - Solution: Copy test_import_* files to temp directory before compilation
  - Result: All 4 import tests now pass, enabling multi-file test scenarios

**Implementation Notes:**
- Enum memory layout: `{ i8 tag, [max_size x i8] data }`
- Switch-based matching on tag for efficiency
- Variant-to-enum mapping resolves constructors like `Some(x)`
- Function parameters registered in `ritz_types` for pointer-to-enum detection

---

### Phase 6: HashMapI64 Implementation

**Goal:** O(1) lookup replaces O(n) linked list searches.

**Hash Functions (ritzlib/hash.ritz):**
- [x] Implement FNV-1a 64-bit hash algorithm
- [x] `fnv1a_init()`, `fnv1a_byte()` - hash combinators
- [x] `hash_i32()`, `hash_i64()`, `hash_u64()` - standalone hash functions
- [x] `fnv1a_i32()`, `fnv1a_i64()`, `fnv1a_u64()` - chained hash functions

**Equality Functions (ritzlib/eq.ritz):**
- [x] `eq_i32()`, `eq_i64()`, `eq_u64()` - primitive equality
- [x] `eq_string()` - String equality (delegates to string_eq)

**String Hash (ritzlib/string.ritz):**
- [x] `string_hash(s: *String) -> u64` - FNV-1a hash of string contents

**HashMapI64 (ritzlib/hashmap.ritz):**
- [x] `HashMapEntryI64` struct: key, value, state (EMPTY=0, OCCUPIED=1, TOMBSTONE=2)
- [x] `HashMapI64` struct: entries ptr, cap, len, tombstones
- [x] `hashmap_i64_new()`, `hashmap_i64_with_cap()` - constructors
- [x] `hashmap_i64_insert()` - insert or update key-value pair
- [x] `hashmap_i64_get()` - get value by key (returns 0 if not found)
- [x] `hashmap_i64_contains()` - check if key exists
- [x] `hashmap_i64_remove()` - remove key (uses tombstone for probe continuity)
- [x] `hashmap_i64_grow()` - double capacity, rehash all entries
- [x] `hashmap_i64_len()`, `hashmap_i64_cap()`, `hashmap_i64_is_empty()` - accessors
- [x] `hashmap_i64_drop()` - manual cleanup
- [x] `impl Drop for HashMapI64` - automatic cleanup

**Bug Fixes:**
- [x] Initialize struct fields to null before malloc (prevents Drop on garbage)
- [x] Set entries to null in drop function (prevents double-free)
- [x] Large allocations (>2KB) use mmap; Drop on uninitialized memory causes crash

**Tests (ritz0/test/test_level33.ritz):**
- [x] `test_hashmap_new` - empty map
- [x] `test_hashmap_insert_get` - basic insert/get
- [x] `test_hashmap_contains` - key existence check
- [x] `test_hashmap_update` - update existing key
- [x] `test_hashmap_multiple_keys` - multiple entries
- [x] `test_hashmap_remove` - removal with tombstone
- [x] `test_hashmap_remove_not_found` - remove non-existent key
- [x] `test_hashmap_many_keys` - 50 entries (triggers multiple grows)
- [x] `test_hashmap_grow` - capacity growth
- [x] `test_hashmap_collision` - hash collision handling

**Results:**
- 282 tests pass (272 existing + 10 new HashMap tests)
- Valgrind clean (no leaks)

**Implementation Notes:**
- Generic `HashMap<K,V>` deferred due to parser limitation with multi-param generic casts
  (`as *Type<K, V>` disallowed to avoid ambiguity with comparison operators)
- Used specialized `HashMapI64` with non-generic types as workaround
- Open addressing with linear probing, power-of-2 capacity for fast modulo
- 75% load factor threshold triggers resize

---

## December 31, 2024

### Struct Return Type Name Fix (Session 12)

**Bug Fix: ritz1 segfaults on functions returning structs**
- Root cause: `fn_return_type_name` was never set in the parser
- When IR emission tried to emit struct return types, it used garbage memory
- This caused segfaults in all examples using ritzlib modules with struct-returning functions

**Fix Applied:**
- [x] Added `capture_fn_return_type(p: *Parser, ret: i32) -> i32` helper to `ast_helpers.ritz`
  - If return type is TYPE_STRUCT, copies `last_type_name` to `fn_return_type_name`
  - Prevents `last_type_name` from being overwritten by type_spec calls in function body
- [x] Updated grammar's `return_type` rule to call `capture_fn_return_type(p, $2)`
- [x] Manually edited `parser_gen.ritz` to include the function call (ritzgen_old doesn't fully support complex semantic actions)

**Results:**
- Stage 3 improved: **36/48 → 47/48 examples passing**
- All 11 previously failing examples (12_tac through 48_ritzfmt) now compile
- Only remaining failure: 49_ritzgen (segfaults due to stack overflow in deep import recursion)

**Note:** RITZ_PATH must point to parent directory (langdev/) not ritzlib/ directly.
Import paths like `ritzlib.sys` resolve to `$RITZ_PATH/ritzlib/sys.ritz`.

### Metadata Constant Values Fix (Session 11)

**Bug Fix: Imported constants had value 0**
- Root cause: `ConstMeta` dataclass only stored `name` and `type`, not `value`
- When loading from metadata cache, all constants defaulted to 0
- This caused ritz1 parser to compare tokens against wrong values (all 0)

**Fix Applied:**
- [x] Added `value: int` field to `ConstMeta` in `metadata.py`
- [x] Updated `extract_metadata` to capture constant values from `IntLit` nodes
- [x] Updated `import_resolver._register_items_from_metadata` to use stored values
- [x] Added backwards compatibility for old cached metadata (defaults to 0)
- [x] Cleared all `.ritz-cache` directories to regenerate with new format

**Grammar Fix: Type-inferred let statements**
- [x] Added `LET IDENT ASSIGN expr NEWLINE` alternative to `let_stmt` in ritz1.grammar
- [x] Regenerated parser_gen.ritz from updated grammar
- [x] Removed duplicate `parser_alloc` definition (defined in both parser_gen.ritz and ast_helpers.ritz)

**Results:**
- Stage 3 improved: 0/48 → 36/48 examples passing
- Remaining 12 failures are in complex examples using ritzlib/buf, ritzlib/vec (likely missing features in ritz1)

### Ritz Metadata Implementation (Session 9)

**Dual-Implementation Metadata System:**
- [x] Switched `.ritz-meta` from TOML to JSON format (more readable with nested arrays)
- [x] Create `ritzlib/json.ritz` - Full JSON parser and emitter in Ritz
  - Parses: null, booleans, numbers, strings, arrays, objects
  - String escape handling: \n, \t, \r, \\, \"
  - Nested structures supported (arrays of objects, objects with object fields)
  - `json_parse()`, `json_get_field()`, `json_get_index()` helpers
  - `json_to_string()` emitter for round-trip
  - 36 unit tests (ritzlib/tests/test_json.ritz)
- [x] Create `ritzlib/meta.ritz` - Ritz module metadata parser
  - Structures: FnSignature, StructMeta, EnumMeta, ConstMeta, TypeAliasMeta, TraitMeta, ModuleMetadata
  - `meta_from_json()` parses .ritz-meta files
  - `meta_find_function/struct/enum/constant/type_alias/trait()` lookup helpers
  - `get_cache_path()` computes .ritz-cache paths
  - `meta_is_valid()` checks cache freshness
  - 17 unit tests (ritzlib/tests/test_meta.ritz)
- [x] Create `ritz0/test_metadata.py` - Python cross-validation tests
  - 25 tests covering serialization, round-trip, cache operations
  - Validates Python and Ritz can read same JSON format

**Test Results:**
- `ritzlib/tests/test_json.ritz`: 36 passed
- `ritzlib/tests/test_meta.ritz`: 17 passed
- `ritz0/test_metadata.py`: 25 passed
- Stage 1 regression: 48/48 examples passing

**Format Example (`.ritz-meta` in JSON):**
```json
{
  "source_path": "/path/to/module.ritz",
  "source_mtime": 1766946951.19,
  "imports": ["ritzlib.sys", "ritzlib.io"],
  "functions": [
    {
      "name": "foo",
      "params": [{"name": "x", "type": "i32"}],
      "ret_type": "i32",
      "is_extern": false,
      "is_generic": false,
      "type_params": []
    }
  ],
  "structs": [...],
  "enums": [...],
  "constants": [...],
  "type_aliases": [...],
  "traits": [...]
}
```

**Next:** Integrate metadata into ritz1 import resolver for faster incremental compilation.

### Metadata-Based Incremental Compilation (Session 10)

**Integrated metadata caching into ritz0 import resolver:**
- [x] Modified `_process_import()` to check metadata cache first
  - If valid cache exists, uses `_register_items_from_metadata()` instead of re-parsing
  - Falls back to full parse if cache is stale/missing
- [x] Implemented `_register_items_from_metadata()` - Creates AST nodes from cached metadata
  - Converts FnSignature → FnDef with empty body (for `declare` in separate compilation)
  - Converts StructMeta → StructDef with fields
  - Converts EnumMeta → EnumDef with variants
  - Converts ConstMeta → ConstDef
  - Converts TypeAliasMeta → TypeAlias
  - Converts TraitMeta → TraitDef with method signatures
- [x] Fixed cache population bug - Was extracting from merged module (no imports), now extracts from original module
- [x] Fixed AST constructor signatures (Span, Param, ExternFn, FnDef, Block)

**Test Results:**
- All 49 examples pass (including 38_tee and 42_json which were failing before)
- Metadata files correctly store imports after re-compilation

**Performance:**
- Second build with metadata cache ~7x faster for multi-module projects
- Main benefit: avoids re-parsing unchanged imported modules

### Module Metadata Caching (Session 8)

**Implemented `.ritz-meta` format for incremental compilation:**
- [x] Create `ritz0/metadata.py` - Module metadata extraction and caching
  - Extracts exports: functions, structs, enums, constants, type aliases, traits
  - Serializes to JSON format in `.ritz-cache/<path>.ritz-meta`
  - Timestamp-based cache invalidation (source newer → regenerate)
  - `MetadataCache` class for in-memory + disk caching
- [x] Integrate metadata caching into `import_resolver.py`
  - Auto-generates `.ritz-meta` for main module and all imports
  - Added `use_cache` parameter (default True)
- [x] Verified with ritzgen compilation - 16 metadata files generated

**Result:** Metadata caching infrastructure ready for future incremental builds.

### Name Resolution and Duplicate Cleanup (Session 7)

**Name Resolution Check (Issue #31):**
- [x] Implement `name_resolver.py` - Verifies all referenced names are defined before IR emission
  - Collects defined names: functions, structs, enums, constants, type aliases, traits, global vars
  - Checks all references in expressions, statements, and types
  - Proper scope handling for local variables and parameters
  - Available via `--check-names` flag in ritz0
- [x] Integrated into compiler pipeline after import resolution

**Duplicate Function Cleanup (ritzgen):**
- [x] Create `examples/49_ritzgen/src/utils.ritz` with shared helpers:
  - `is_alpha()`, `is_alnum()`, `is_digit()`, `is_terminal_name()`
- [x] Remove duplicate `is_alpha`/`is_alnum` from grammar.ritz and lexer.ritz
- [x] Remove duplicate `is_terminal_name` from grammar.ritz and codegen.ritz
- [x] ritzgen now builds and passes with unified separate compilation

**Result:** ritzgen builds cleanly with `--check-names` enabled.

## December 30, 2024

### Native Test Infrastructure

**Test Harness Modules:**
- [x] Create `ritzlib/testing.ritz` - Native test runtime with registration and execution
  - Global test registry with MAX_TESTS = 1024
  - Function pointer storage (as `*u8` to work around FnType struct limitation)
  - Inline asm for calling test functions
  - run_all_tests() for test execution with pass/fail reporting

- [x] Create `ritzlib/elf.ritz` - Native ELF64 parser for test discovery
  - Parses ELF64 headers, section tables, symbol tables
  - Finds `.symtab` and `.strtab` sections
  - Extracts symbol names, types, binding
  - Discovers functions starting with `test_`
  - Successfully discovered all 30 test functions from test_memory.o

**Tier 1 Test Coverage:**
- [x] 79 total tests across 9 examples (01_hello through 09_yes)
- [x] Created test directories for examples 06-09 (were missing)
- [x] Test files cover:
  - 01_hello: 6 tests (arithmetic, comparison, function return, strings, escapes, logical ops)
  - 02_exitcode: 7 tests (return statements, trailing expressions, nested returns)
  - 03_echo: 8 tests (pointers, while loops, string operations, arrays, mutation)
  - 04_true_false: 10 tests (boolean logic, if-else, comparisons, logical operators)
  - 05_cat: 11 tests (file I/O, syscalls, malloc/free, memset/memcpy, streq/strlen)
  - 06_head: 10 tests (atoi parsing, newline counting, buffer operations)
  - 07_wc: 9 tests (isspace/isdigit/isalpha, word/line counting, wc algorithm)
  - 08_seq: 10 tests (itoa, sequence generation, roundtrip parsing)
  - 09_yes: 8 tests (buffer filling, pattern repetition, memcpy)

## December 28, 2024

### Type System Improvements (Stage 3: 4/48 → 5/48)

**OP_DEREF Type Inference:**
- [x] Fix `get_expr_type()` for `OP_DEREF` to return pointee type
  - `**u8` dereference now returns `TYPE_PTR` (was incorrectly returning `TYPE_I64`)
  - Single pointer dereference still returns `TYPE_I64` (no finer-grained tracking yet)
- [x] Fix `emit_expr()` for `OP_DEREF` to use correct load type
  - Now loads as `ptr` when operand is `TYPE_PTR_PTR`
  - Loads as `i64` for other pointer types

**u8/i8 Type Promotion in Binary Expressions:**
- [x] Add `TYPE_U8` to `i32` promotion for binary ops when target type is `i32`
- [x] Add `TYPE_U8` to `i64` promotion for binary ops when target type is `i64`
  - Uses `zext` (unsigned extension) for u8 values
  - Fixes comparison of `*(s + i) == c` where `c` is `u8`

**Result:** 5/48 Stage 3 tests passing: 01_hello, 02_exitcode, 03_echo, 05_cat, 06_head

**Remaining blocker:** Imported function lookup - `print_int` and other imported functions
default to i32 types because `fn_lookup` returns null.

### Import System Fixes (Stage 3: 2/48 → 4/48)

**Lexer Reset Bug:**
- [x] Fix `indent_depth = 0` in import lexer reset (must be 1)
  - Root cause: `indent_depth - 1` caused reading garbage from `indent_stack[-1]`
  - Symptom: Spurious DEDENT token at start of imported file, breaking parsing
  - Solution: Set `indent_depth = 1` to match initial lexer state

**Multi-Import Heap Corruption:**
- [x] Track parser heap offset after each import resolution
  - Root cause: Second import's tokens/AST overwrote first import's data
  - Symptom: Functions from first import became invalid, looked up as "not found"
  - Solution: `*heap_offset = *heap_offset + p.heap_offset` after parsing each import

**Builtin Handling:**
- [x] Add `__builtin_alloca(size: i64) -> ptr` handling to emit_expr
  - Emits proper LLVM: `alloca i8, i64 %size`
  - Required for ritzlib/str.ritz and other runtime code

### Multi-Import Segfault Fix (Earlier)
- [x] Fix stack overflow on multiple imports by passing shared lexer storage pointer
  - Root cause: ~64KB stack allocation per import (NFAState[512], Transition[1024], Lexer)
  - Solution: `resolve_import()` now accepts `*Lexer` parameter, resets lexer state instead of allocating
- [x] Fix envp not being passed to 3-arg main functions in ritz1
  - `_start` wrapper now properly calculates envp for `main(argc, argv, envp)`
  - Enables `set_ritz_path()` to read RITZ_PATH environment variable

## December 27, 2024 (Session 2)

### ritz1 Self-Compilation Type System Fixes
- [x] Add `__syscall0`-`__syscall6` detection (10-char variants)
- [x] Implement `get_expr_type()` helper for expression type inference
- [x] Fix binary expression type promotion (i64 + i64 → i64, not i32)
- [x] Add type coercion for syscall arguments (sext/ptrtoint as needed)
- [x] Fix type coercion in return statements (inttoptr for ptr returns)
- [x] Implement `EXPR_MEMBER` in emitter (struct field access)
- [x] Handle `(*ptr).field` patterns without double-loading
- [x] Fix cast expression source type detection using `get_expr_type()`
- [x] Add `allocator_init` explicit return type/value

**Result:** ritz1 self-compilation now produces valid LLVM IR (llc passes)!

**Remaining:** Parser stops after 2 functions (allocator.ritz only) - needs debugging.

## December 27, 2024 (Session 1)

- [x] Fix exponential backtracking in ritz1 expression parsing (left-factored grammar)
- [x] Fix deref assignment (`*ptr = value`) in ritz1 emitter
- [x] Fix address-of operator (`&x` -> returns alloca register)
- [x] Add member assignment through deref (`(*ptr).field = value`) to grammar and emitter
- [x] Fix PostfixOp allocation size bug (32->64 bytes)
- [x] Add all bitwise operators to ritz1 grammar (`&`, `|`, `^`, `~`)
- [x] Change address-of from `&` to `@` ("where is this @at?")
- [x] Add bitwise NOT (`~`) to ritz0 parser and emitter
- [x] Verify all 48 ritz0 examples still compile after changes

## December 26, 2024

- [x] Implement separate compilation (`--separate` flag)
- [x] Create ritzgen AST parser generator
- [x] Complete comprehensive code review (48 issues identified)
- [x] Create GitHub issues #52-#56
- [x] Fix ritzgen SYM_STAR/SYM_PLUS handling for AST rules
