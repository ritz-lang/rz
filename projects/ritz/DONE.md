# Completed Phases

Historical record of completed work. For detailed session logs, see `docs/archive/`.

---

## AES-NI and SHA-NI Hardware Crypto Intrinsics (February 14, 2026)

**Issue #119: Hardware crypto acceleration for cryptosec TLS 1.3 library**

Implemented hardware crypto intrinsics following TDD approach.

**AES-NI Intrinsics (5 functions):**
- ✅ `aesenc(state: v4i32, key: v4i32) -> v4i32` - One AES encryption round
- ✅ `aesenclast(state: v4i32, key: v4i32) -> v4i32` - Final AES encryption round
- ✅ `aesdec(state: v4i32, key: v4i32) -> v4i32` - One AES decryption round
- ✅ `aesdeclast(state: v4i32, key: v4i32) -> v4i32` - Final AES decryption round
- ✅ `aesimc(key: v4i32) -> v4i32` - Inverse MixColumns for key schedule

**SHA-NI Intrinsics (3 functions):**
- ✅ `sha256rnds2(cdgh: v4i32, abef: v4i32, wk: v4i32) -> v4i32` - Two SHA-256 rounds
- ✅ `sha256msg1(w0: v4i32, w1: v4i32) -> v4i32` - Message schedule part 1
- ✅ `sha256msg2(w0: v4i32, w1: v4i32) -> v4i32` - Message schedule part 2

**Implementation Details:**
- Added to `_try_emit_simd_builtin()` in `emitter_llvmlite.py`
- Maps to LLVM intrinsics: `llvm.x86.aesni.*` and `llvm.x86.sha256*`
- Uses v4i32 ↔ v2i64 bitcasts for AES (LLVM intrinsics use <2 x i64>)
- Runtime tests require hardware support (AES-NI: Westmere+, SHA-NI: Goldmont/IceLake+)

**Tests:**
- `ritz0/test/test_aesni.ritz` - 6 runtime tests (requires AES-NI CPU flag)
- `ritz0/test/test_shani.ritz` - 4 runtime tests (requires SHA-NI CPU flag)
- `ritz0/test_crypto_intrinsics.py` - 8 Python tests (LLVM IR validation + runtime)

**Files Modified:**
- `ritz0/emitter_llvmlite.py` - Added 8 crypto intrinsic handlers (~180 lines)
- `ritz0/test/test_aesni.ritz` - New AES-NI runtime tests
- `ritz0/test/test_shani.ritz` - New SHA-NI runtime tests
- `ritz0/test_crypto_intrinsics.py` - New Python test suite
- `ritz0/test_asm.py` - Fixed hardcoded path issue

---

## ritz1 Generics Monomorphization (February 13, 2026)

**Struct Monomorphization:**
- ✅ Implemented struct instantiation tracking in `monomorph.ritz` (parallel arrays)
- ✅ Added `add_struct_instantiation()`, `find_generic_struct()`, `clone_and_specialize_struct()`
- ✅ Added `add_struct_from_mangled_name()` to extract base name and suffix from mangled names
- ✅ Updated `monomorphize_module()` to generate specialized structs before functions
- ✅ Generic type annotations work: `var p: Pair<i32>` → `%Pair$i32 = type {i32, i32}`

**Generic Struct Literal Parsing:**
- ✅ Added grammar rule to `ritz1.grammar`: `IDENT LT type_spec GT struct_lit`
- ✅ Added `generic_struct_lit()` helper function to `ast_helpers.ritz`
- ✅ Updated `parser_gen.ritz` with new Alternative 5 for generic struct literals
- ✅ Full syntax support: `Pair<i32> { first: 10, second: 32 }`

**Verification:**
- ✅ Test: `var p: Pair<i32>; p.first = 10; p.second = 32; p.first + p.second` → exit 42
- ✅ Test: `var p: Pair<i32> = Pair<i32> { first: 10, second: 32 }; p.first + p.second` → exit 42
- ✅ ritz1 builds successfully with all changes
- ✅ Basic functionality test passes (simple fn main() -> 42)

**Files Modified:**
- `ritz1/src/monomorph.ritz` - Added struct monomorphization logic
- `ritz1/src/ast_helpers.ritz` - Added `generic_struct_lit()` function
- `ritz1/src/parser_gen.ritz` - Added Alternative 5 for generic struct literal parsing
- `grammars/ritz1.grammar` - Added grammar rule for generic struct literals

**ritzlib Import Testing (February 13, 2026):**
- ✅ ritz0 successfully compiles code using `import ritzlib.gvec` with `Vec<i32>`
- ✅ Generic function calls work: `vec_new<i32>()`, `vec_push<i32>()`, `vec_get<i32>()`
- ⚠️ ritz1 import resolution works (`-I /path/to/ritz`)
- ⚠️ Blocked by ritz1 lexer bug: escaped character literals (`'\n'`) not recognized
- Known issue: ritz1 requires explicit type args (no inference): `vec_push<i32>(...)` not `vec_push(...)`

---

## Packaging RFC #107 Phase 2: Lock Files and Vendoring (February 2026)

**Lock File Generation (`ritz lock`):**
- ✅ Implemented `LockEntry` dataclass for pinning dependencies
- ✅ Implemented `LockFile` class for reading/writing `ritz.lock`
- ✅ Lock file format follows RFC spec (TOML with `[[package]]` arrays)
- ✅ Each entry includes: name, version, source, sha256 checksum
- ✅ `generate_lock_entries()` resolves all deps including transitive

**Vendoring (`ritz vendor`):**
- ✅ Implemented `vendor_dependencies()` function
- ✅ Copies all dependency sources to `vendor/` directory
- ✅ Includes transitive dependencies
- ✅ Excludes build artifacts: `build/`, `.ritz-cache/`, `vendor/`, `.git/`
- ✅ Only copies source files (`.ritz`, `.toml`, `.md`, `.txt`, `.json`)

**CLI Commands:**
- ✅ `ritz lock [path]` - Generate `ritz.lock` for a package
- ✅ `ritz vendor [path]` - Copy dependencies to `vendor/`

**Test Coverage:**
- ✅ 9 new tests added to `test_packaging.py`
- ✅ LockEntry creation and serialization (3 tests)
- ✅ LockFile read/write operations (2 tests)
- ✅ Lock file format validation (1 test)
- ✅ Vendor directory creation (1 test)
- ✅ Vendor excludes build artifacts (1 test)
- ✅ Vendor includes transitive deps (1 test)

**Example Usage:**
```bash
# Generate lock file
ritz lock examples/test_deps/app

# View generated lock file
cat examples/test_deps/app/ritz.lock
# [[package]]
# name = "squeeze"
# version = "0.1.0"
# source = "path:../squeeze"
# checksum = "sha256:d7b964e8f7300bbf"

# Vendor dependencies for offline builds
ritz vendor examples/test_deps/app
# ✓ Vendored 1 package(s) to examples/test_deps/app/vendor
```

---

## Packaging RFC #107 Phase 1: Global Install System (February 2026)

**Content-Addressed Global Cache:**
- ✅ Created `packaging.py` module for global package management
- ✅ Implemented `~/.ritz/` directory structure:
  - `~/.ritz/cache/` - Content-addressed build cache
  - `~/.ritz/packages/` - Downloaded package sources
  - `~/.ritz/bin/` - Symlinks to installed binaries
- ✅ Implemented `compute_source_hash()` - Hash all .ritz files + ritz.toml
- ✅ Implemented `compute_cache_key()` - Include target triple and optimization level
- ✅ Implemented `GlobalCache` class with store/retrieve/clear operations

**Install Commands:**
- ✅ `ritz install <uri>` - Install from git URL or local path
- ✅ `ritz uninstall <name>` - Remove installed package
- ✅ `ritz global-list` - List all installed packages
- ✅ `ritz global-cache` - Show cache information

**Features:**
- ✅ URI parsing for git URLs with tag/branch/rev specifiers
- ✅ Local path detection for development workflows
- ✅ Automatic symlink creation in `~/.ritz/bin/`
- ✅ Cache hit detection - reuse existing builds
- ✅ `--release` flag for optimized builds
- ✅ `--force` flag for reinstallation

**Test Coverage:**
- ✅ 20 new tests in `test_packaging.py`
- ✅ URI parsing tests (7 tests)
- ✅ Content hashing tests (4 tests)
- ✅ GlobalCache tests (6 tests)
- ✅ PackageMetadata tests (1 test)
- ✅ Target triple tests (2 tests)

**Example Usage:**
```bash
# Install from local path
ritz install examples/tier1_basics/01_hello

# Install with release optimizations
ritz install examples/tier1_basics/01_hello --release

# List installed packages
ritz global-list

# Run installed binary
~/.ritz/bin/hello

# Uninstall
ritz uninstall hello
```

---

## Build System RFC #109 Phase 3: LLVM BC Caching (February 2026)

**LLVM Bitcode Caching for Faster Rebuilds:**
- ✅ Added `get_cached_bc_path()` method to `cache.py` for bitcode cache paths
- ✅ Added `has_valid_bc()` method to check for valid cached bitcode
- ✅ Added `get_cached_bc()` method to retrieve cached bitcode path
- ✅ Added `update_bc_cache()` method to copy bitcode to cache
- ✅ Updated `compile_binary()` in `build.py` to use bitcode caching
- ✅ Graceful fallback: uses .ll files when llvm-as is unavailable
- ✅ Updated cache status to show both .ll and .bc file counts

**Performance Results:**
- Fresh build (wc example with ritzlib imports): 2.7s
- Cached rebuild: 0.8s (3.4x faster)

**Implementation Notes:**
- Bitcode (.bc) is faster to load than text IR (.ll)
- llvm-as converts .ll → .bc; if unavailable, falls back to .ll linking
- Both .ll and .bc files are cached for flexibility
- Works with existing .ll cache infrastructure

**Test Coverage:**
- ✅ All 21 build system tests passing
- ✅ All tier1 examples building correctly
- ✅ Cache status correctly reports .ll and .bc counts

---

## Build System RFC #109 Phase 2: Dependencies (February 2026)

**Dependency Resolution:**
- ✅ Added `DependencySpec` dataclass to `build.py` for dependency metadata
- ✅ Added `parse_dependencies()` - parses `[dependencies]` from ritz.toml
- ✅ Added `get_transitive_dependencies()` - recursively resolves dependencies with cycle detection
- ✅ Added `DependencyMapping` class to `import_resolver.py`
- ✅ Updated `ImportResolver` to accept `dependencies` parameter
- ✅ Updated `_resolve_import_path()` to check dependency namespaces first
- ✅ Updated `list_deps.py` to accept `--deps` JSON argument
- ✅ Updated `ritz0.py` to accept `--deps` and pass to import resolver
- ✅ Updated `build.py` to pass dependencies through build pipeline

**Test Coverage:**
- ✅ 8 new tests in `test_build.py` for dependency parsing and resolution
- ✅ Created test example `examples/test_deps/` with mini "squeeze" dependency
- ✅ All 324 ritz0 tests passing, 21 build system tests passing

**Limitations:**
- Flat import model (functions imported directly, no qualified `module::fn()` syntax yet)
- Qualified syntax pending module system Phase 2 (name resolver update)

---

## Phase 14: Testing Infrastructure & Runtime Linking (February 2026)

**Testing Framework:**
- ✅ Discovered existing `ritzunit` native test runner with ELF-based discovery
- ✅ Created `ritzlib/process.ritz` (270 lines) - Process spawning API for integration tests
  - `spawn()`, `spawn_args()` - Fork/exec with PATH search
  - `process_read_stdout_all()` - Capture output as `Vec<u8>`
  - `process_read_line()` - Line-by-line reading
  - `process_wait()` - Wait for exit with status
  - Ownership-based cleanup (close pipes, reap zombies)
- ✅ Created `docs/TESTING_DESIGN.md` - Comprehensive testing design document
- ✅ **ritzunit integration working** - `build_ritz0_tests.sh` compiles 14 test files
  - 135 tests discovered and executed via ELF symbol table scanning
  - Multi-file linking with deduplication (associative array tracks compiled modules)
  - Excludes 7 test files with symbol conflicts (to be fixed with unique prefixes)

**Runtime Linking (crt0-style):**
- ✅ Created external runtime files:
  - `runtime/ritz_start_noargs.x86_64.ll` - For `main() -> i32`
  - `runtime/ritz_start.x86_64.ll` - For `main(argc, argv) -> i32`
  - `runtime/ritz_start_envp.x86_64.ll` - For `main(argc, argv, envp) -> i32`
- ✅ Updated `runtime/Makefile` - Builds `.o` files with clang
- ✅ Updated `build.py`:
  - `detect_main_signature()` - Parses source to determine main's parameters
  - `get_runtime_object()` - Returns appropriate runtime based on signature
  - All sources compiled with `--no-runtime`, linked with external `.o`

**Parser Fixes:**
- ✅ Fixed `parser_gen.py` - Added CSTRING (93) and SPAN_STRING (94) token types
- ✅ Fixed `parser_gen.py` lexer - `_lex_string()` now detects `c"..."` and `s"..."` prefixes
- ✅ Fixed `parser_adapter.py` - CharLit returns numeric ASCII value (not quoted string)

---

## Phase 13: Project Infrastructure & Examples Reorganization (February 2026)

**Parser Generator & Compilation:**
- ✅ Created ritzgen-py grammar-driven parser generator
- ✅ Generated Python parser from grammar.txt canonical grammar
- ✅ Built ritz_ast_adapter for parse tree → AST node conversion
- ✅ Achieved 60/75 examples compiling (vs 47/75 with hand-written parser)

**Examples Reorganization:**
- ✅ Created 5 tier directories for 79 example packages
- ✅ Moved all examples into tier1_basics, tier2_stdlib, tier3_coreutils, tier4_applications, tier5_async
- ✅ Updated docs/EXAMPLES.md with tier descriptions and new directory structure
- ✅ Verified build.py already supports tier structure via recursive glob discovery
- ✅ All 79 packages correctly indexed by build system

---

## Phase 1-9: Core Language (December 2024 - January 2026)

All core language features implemented and stable:

- **Phase 1**: Computed struct layouts (`sizeof(T)`, field offsets)
- **Phase 2**: Basic generics (`Vec<T>`, `Box<T>`, monomorphization)
- **Phase 3**: Box<T> - owned heap allocation with RAII
- **Phase 4**: Vec<T> - dynamic arrays with push/pop/get
- **Phase 5**: String type with method syntax
- **Phase 5.5**: Generic impl blocks and Drop trait
- **Phase 5.6**: Automatic Drop (RAII) at scope exit
- **Phase 5.7**: Implicit deref for Box<T>
- **Phase 6**: HashMapI64 with O(1) lookup
- **Phase 7**: Option<T> and Result<T,E> with pattern matching
- **Phase 8**: Try operator (?) for error propagation
- **Phase 9**: Ownership and borrowing (move checker)
- **Phase 9.5**: Syntax sugar (indexing, slicing, string literals)

## Phase 10: ritz1 Bootstrap (January 2026)

Self-hosted compiler progress:

- ✅ ritz1 builds from ritz0
- ✅ 11/11 Tier 1 examples compile and run
- ✅ 35/35 dual-compiler tests pass (both ritz0 and ritz1)
- ✅ Generic type parsing and mangling
- ✅ Method syntax support
- ✅ Character literals with escape sequences
- ✅ Hex and binary literal support
- ✅ Nested struct layout emission
- ✅ Import resolution with cycle detection
- 🔄 Tier 2 blocked on monomorphization

## Phase 10.5: Code Quality (January 2026)

- ✅ Dual-compiler test suite (`test/dual_compiler/`)
- ✅ Trait receiver migration (`self: *Self` → `self: &mut Self`)
- ✅ Type consolidation (ByteVec/PtrVec/I64Vec → Vec<T>)
- ✅ ritzlib modernization (String methods, Span<T>, GrowBuf with Drop)
- ✅ STYLE.md coding conventions
- ✅ Deleted deprecated ritzlib/vec.ritz

## Phase 11: Async I/O Foundation & Closures (January 2026)

**Language Features:**
- ✅ `async fn` / `await` keywords with state machine transformation (AST-level)
- ✅ Function pointer types: `fn(T1, T2) -> R`
- ✅ Closure syntax: `|x, y| expr` with captures (thunk-based implementation)

**io_uring Integration:**
- ✅ io_uring syscall bindings (`ritzlib/uring.ritz`)
- ✅ Async file I/O (`ritzlib/async_fs.ritz`)
- ✅ Async runtime with block_on (`ritzlib/async_runtime.ritz`)
- ✅ TCP networking (`ritzlib/async_net.ritz`) - socket, bind, listen, accept, connect

**Note:** Current async implementation is synchronous MVP - `await` evaluates immediately.
True suspension/resume deferred to Phase 12 (Valet webserver).

**Test Coverage:**
- ✅ examples/52_uring - 4 tests (io_uring syscalls)
- ✅ examples/53_async - 4 tests (async/await syntax)
- ✅ examples/54_async_fs - 3 tests (file I/O)
- ✅ examples/55_async_state_machine - 5 tests (state machine transformation)
- ✅ examples/56_async_runtime - 6 tests (io_uring runtime)
- ✅ examples/57_fn_ptr - 6 tests (function pointers)
- ✅ examples/58_closures - 7 tests (captures, higher-order, compose)
- ✅ examples/59_async_net - 5 tests (TCP with io_uring)
- ✅ examples/60_echo_server - 3 tests (TCP echo server)

## Phase 12: Async Framework Review & Verification (January 13, 2026)

**Status:** ✅ COMPLETE - Comprehensive review and verification of async infrastructure

**Architecture Review:**
- ✅ `ritzlib/uring.ritz` (598 lines) - io_uring kernel bindings with vectored I/O support
  - 24 functions including uring_prep_readv, uring_prep_writev, uring_prep_accept_multishot
  - Complete SQE/CQE handling
  - All operations compiled and verified in LLVM IR

- ✅ `ritzlib/async_tasks.ritz` (499 lines) - Production-ready task pool
  - Fixed-size task management (256 tasks)
  - Event loop with handler return codes (-1=pending, 0=done, >0=error)
  - State machine support for protocol handling
  - TaskServer for complete async server patterns

- ✅ `ritzlib/async_net.ritz` - Network operations with async runtime
- ✅ `ritzlib/async_runtime.ritz` - Original runtime system (backward compatible)
- ✅ `ritzlib/async/` directory - New modular async patterns

**Documentation Created:**
- ✅ ASYNC_FRAMEWORK_STATUS.md - Architecture overview and design patterns
- ✅ ASYNC_FRAMEWORK_REVIEW_FINAL.md - 350+ line comprehensive technical review
- ✅ SESSION_SUMMARY_2026_01_13.md - Work summary and key findings
- ✅ SESSION_CLOSURE_2026_01_13.md - Final status report with completion verification

**Code Examples:**
- ✅ examples/async_echo_server.ritz - Complete working echo server (150 lines)
  - Demonstrates TaskServer pattern with multishot accept
  - Shows state machine handler implementation
  - Includes proper resource cleanup

**Test Suite:**
- ✅ ritz0/test/test_async_echo.ritz (200 lines, 4 comprehensive tests)
  - test_handler_state_machine - State transition validation
  - test_task_buffers - Buffer management
  - test_multiple_tasks - Concurrent task handling
  - test_request_counter - Connection metrics
- ✅ All 125/125 tests passing (103 parser + 22 export map)
- ✅ Zero regressions

**Module System Integration:**
- ✅ Phase 2C (Re-export handling) verified working
- ✅ Parser correctly extracts all items including new uring functions
- ✅ Export maps built properly
- ✅ Re-exports functional
- ✅ Import aliases working

**Compilation Verification:**
- ✅ All three new uring vectored I/O functions compiled to LLVM IR
- ✅ Functions present in compiled output (/tmp/uring.ll)
- ✅ Fresh compilation resolves initial cache issues
- ✅ Ready for production use

**Key Design Patterns Documented:**
1. Handler return codes for simple state control
2. Task state machines for protocol handling
3. Event loop model for efficient I/O multiplexing
4. Fixed-size task pool for scalable concurrency

---

## String Type Consolidation (January 13, 2026)

**Status:** ✅ COMPLETE - Unified string slice types under `Span<u8>`

**Problem:**
Three overlapping string slice types created confusion:
- `Span<T>` (span.ritz) - Generic, established in 6+ files
- `Str` (slice.ritz) - Non-owning string slice, duplicate of `Span<u8>`
- `String` (string.ritz) - Owned, growable

**Solution:**
Consolidated to TWO types:
- **`Span<u8>`** for non-owning string slices (replaces `Str`)
- **`String`** for owned, growable strings

**Changes:**
- Extended `span.ritz` with `Span<u8>`-specific operations:
  - `span_find_byte()` - Single byte search
  - `span_eq_cstr()` - Compare to C string
  - `span_take()`, `span_skip()` - Slicing helpers
  - `span_from_bytes()`, `span_literal()` - Constructors
  - HTTP constants: `http_200_ok()`, `http_404_not_found()`, etc.
- Updated `iovec.ritz`: `iovec_append_str()` → `iovec_append_span()`
- Deleted `slice.ritz` (Str type)

**Benefits:**
- Single canonical type for string slices (`Span<u8>`)
- Generic: `Span<T>` works for any element type
- Consistent with Rust's `&[T]` pattern
- HTTP constants with pre-computed lengths (no strlen overhead)

---

## Syntax Improvements (January 2026)

### #83 - Match Expressions for Integers ✅

Integer pattern matching now works with literal values and constant references:

```ritz
const ZERO: i32 = 0
const ONE: i32 = 1

fn describe(x: i32) -> i32
    match x
        ZERO => 100
        ONE => 101
        2 => 102       # Literal pattern
        _ => 999       # Wildcard

fn main() -> i32
    describe(1)        # Returns 101
```

**Implementation:** Added `_emit_integer_match()` in emitter that:
- Uses LLVM `switch` instruction for efficient dispatch
- Supports `LitPattern` (integer literals)
- Supports `IdentPattern` as constant reference (looks up in `self.constants`)
- Supports `WildcardPattern` as default case

### #85 - Auto-dereference for Pointer Field Access ✅

Field access on pointers now works without explicit dereference:

```ritz
struct Point { x: i32, y: i32 }

fn get_x(p: *Point) -> i32
    p.x              # No (*p).x needed!

fn main() -> i32
    var pt = Point { x: 42, y: 100 }
    let p: *Point = &pt
    p.x + p.y        # Works directly
```

**Implementation:** Already supported in `_emit_field_access()` - detects pointer-to-struct and loads before accessing field.

**Tests:** `examples/67_autoderef/test/test_autoderef.ritz` (4 tests)

### #74 - Complete `&mut Self` Migration for Trait Impls ✅

Migrated all Drop trait implementations from `*Self` to `&mut Self` pattern:

```ritz
# Old pattern (deprecated):
impl Drop for GrowBuf
    fn drop(self: *GrowBuf)

# New pattern (modern):
impl Drop for GrowBuf
    fn drop(self: &mut GrowBuf)
```

**Files updated:**
- `ritzlib/buf.ritz` - GrowBuf Drop impl migrated
- `ritzlib/drop.ritz` - Documentation updated to show `&mut Self`
- `ritzlib/box.ritz` - Already using `&mut Box<T>` ✅
- `ritzlib/hashmap.ritz` - Already using `&mut HashMapI64` ✅

**Note:** `gvec.ritz` and `string.ritz` have Drop impls commented out (ritz1 doesn't support generic impl blocks yet), but their comments already show the correct `&mut` pattern.

### Codebase Migration: `(*p).field` → `p.field` ✅

Systematically migrated ~800 instances of explicit pointer dereference syntax
to the new auto-dereference syntax across the entire codebase:

- **ritzlib:** memory.ritz, elf.ritz, testing.ritz
- **ritz1:** parser.ritz (241→0), lexer_nfa.ritz (151→0), nfa.ritz, ast_helpers.ritz
- **ritz1/ir:** All codegen files (112 patterns)
- **examples:** 61_true_async, 63_executor, 64_async_io
- **tests:** ritz0/test, ritz1/test, dual_compiler

The language implementation now serves as an idiomatic reference for the cleaner `p.field` syntax.

### #73 - Modernize ritzlib with For Loops ✅

Systematically migrated ~60 `while i < n` patterns to idiomatic `for i in 0..n` syntax across ritzlib:

| File | Loops Converted | Examples |
|------|-----------------|----------|
| `str.ritz` | 3 | memset, memcpy, memcmp |
| `fs.ritz` | 5 | path_basename_string, path_dirname_string, path_extension_string, path_stem_string |
| `string.ritz` | 10 | string_from, string_clone, string_hash, string_push_*, string_find, etc. |
| `json.ritz` | 8 | json_free, jp_match_str, jp_parse_array, jp_parse_object, json_emit_value |
| `meta.ritz` | 22 | meta_free, parse_* functions, meta_find_* lookups |
| `span.ritz` | 3 | span_eq, span_starts_with, span_ends_with |
| `gvec.ritz` | 2 | vec_slice, vec_push_bytes |
| `hashmap.ritz` | 3 | hashmap_i64_with_cap, hashmap_i64_grow |
| `buf.ritz` | 4 | buf_match_str, buf_starts_with, buf_get_loc, growbuf_append |
| `env.ritz` | 1 | getenv inner loop |

**Compiler fixes included:**
- `ritz0/name_resolver.py`: Fixed ForStmt attribute names (`stmt.iterable` → `stmt.iter`)
- `ritz0/move_checker.py`: Fixed for loop variable type inference for ownership checks

**Result:** 34 files changed, 77 insertions, 216 deletions - cleaner, more idiomatic code.

### #86 - Type Inference on Let Bindings ✅

Let bindings can now omit type annotations when initializers provide sufficient type information:

```ritz
let x = 42           # Inferred as i64
let s = "hello"      # Inferred as *u8
let flag = true      # Inferred as bool
let ch = 'A'         # Inferred as u8
```

**Implementation:**
- `emitter_llvmlite.py`: Added `_infer_ritz_type()` for type inference from expressions
- `move_checker.py`: Added `_infer_expr_type()` so ownership checker recognizes Copy types
- `lexer.py`: Fixed string literal handling to allow standalone `}` (for JSON strings)

**Fixes:**
- Ownership checker was treating inferred types as 'unknown' (non-Copy), causing false "use-after-move" errors
- String interpolation lexer was too strict about `}` characters in non-interpolated strings

**Migration:** 91 patterns in 15 files converted from `let x: *u8 = "..."` to `let x = "..."`

---

## Test Results (Latest)

| Suite | Passing | Total |
|-------|---------|-------|
| ritz0 language tests | 324 | 324 |
| pytest unit tests | 201 | 201 |

---

## Notable Examples

| Example | Description |
|---------|-------------|
| examples/71_type_inference | Type inference for let bindings |
| examples/70_interp_string | String interpolation with expressions |
| examples/60_echo_server | Async TCP echo server with io_uring |
| examples/59_async_net | TCP socket operations with async runtime |
| examples/58_closures | Closures with captures, compose, higher-order |
| examples/57_fn_ptr | Function pointer types and indirect calls |
| examples/56_async_runtime | io_uring-backed async runtime tests |
| examples/52_uring | io_uring syscall bindings |
| examples/50_http | HTTP/1.0 server with ritzlib/net |
| examples/51_loadtest | HTTP load testing tool |
| examples/49_ritzgen | Parser generator from grammar |
| examples/48_ritzfmt | Code formatter |
| examples/47_lisp | Lisp interpreter |
| examples/42_json | JSON parser |

---

## Phase 12.0: Valet HTTP Server Proof of Concept (January 2026)

**Goal:** Demonstrate Ritz can produce extremely fast code via an HTTP server.

**Result:** **1.47M req/sec** - 4-6x faster than nginx!

### Performance Results

| Configuration | Requests/sec | Notes |
|--------------|-------------|-------|
| `/` (pre-computed) | **1.47M** | Static response, single send() |
| `/iov` (vectored) | **1.26M** | Dynamic response via writev() |
| `/json` (JSON body) | **1.14M** | JSON via vectored I/O |
| nginx (keep-alive) | ~240k | Baseline comparison |

### New ritzlib Modules

| Module | Description |
|--------|-------------|
| `async_tasks.ritz` | Connection pool with manual state machines, TaskServer, TaskPool |
| `iovec.ritz` | IoVecBuilder for scatter/gather I/O (writev) |
| `slice.ritz` | `Str` type (ptr + len) for efficient string handling |
| `timer.ritz` | High-resolution timing via clock_gettime(CLOCK_MONOTONIC) |

### Key Optimizations Discovered

1. **HTTP Keep-alive** - Connection reuse provides 10x throughput boost
2. **Str slices over C strings** - Eliminating strlen() saved 13% CPU
3. **Vectored I/O (writev)** - Zero-copy response building from fragments
4. **TCP_NODELAY + SO_REUSEPORT** - Low latency + kernel load balancing
5. **Multi-process with fork()** - Scales to all CPU cores

### Callgrind Profiling Insights

Before `Str` slices:
- 13% of CPU time in `strlen()` scanning null-terminated strings
- 4 strlen() calls per HTTP request just for response building

After `Str` slices (ptr + len):
- 0% CPU in strlen() - completely eliminated
- 12% improvement in response building path

### Files Created/Modified

**langdev:**
- `ritzlib/async_tasks.ritz` - Connection pool, task spawning, io_uring event loop
- `ritzlib/iovec.ritz` - IoVecBuilder with `iovec_append_str()` for Str slices
- `ritzlib/slice.ritz` - `Str` type, HTTP string constants, comparison functions
- `ritzlib/timer.ritz` - `Timer`, `Stopwatch`, `now_nanos/micros/millis()`
- `ritzlib/sys.ritz` - Added `sys_writev()`, `sys_readv()`
- `ritzlib/uring.ritz` - Added `uring_prep_writev()`, `uring_prep_readv()`, multishot accept

**valet (../valet):**
- `lib/request.ritz` - HTTP request parsing
- `lib/response.ritz` - Response builder with iovec support
- `lib/server.ritz` - Multi-process server with SO_REUSEPORT
- `src/main.ritz` - CLI with argparse
- `build.sh` - Build script with debug/release modes
- `tests/` - Test suite

### Lessons Learned

1. **io_uring is incredibly fast** - Direct kernel interface beats epoll/kqueue
2. **Connection pooling beats task spawning** - For HTTP, pre-allocation wins
3. **C strings are a performance trap** - Length-prefixed strings are essential
4. **Profile first, optimize second** - Callgrind found the strlen() bottleneck
5. **The manual state machine works** - But doesn't use async/await yet

### What's NOT Done

- Valet doesn't use `async fn` / `await` keywords - manual state machines instead
- No proper routing or middleware - just hardcoded paths
- No static file serving
- JSON building is byte-by-byte (needs raw string literals in compiler)

**Next:** Phase 12.1 - Proper Async Framework with `spawn()` and multi-task executor

---

## Module System Parsing (January 2026)

Implemented complete parsing support for the new module system:

**Parser Changes:**
- ✅ `pub` keyword for visibility on fn, struct, enum, const, type, trait, extern fn
- ✅ `import path as alias` - namespace aliasing
- ✅ `import path { item1, item2 }` - selective imports
- ✅ `import path { item } as alias` - selective with alias
- ✅ `pub import` - re-export items from other modules
- ✅ `::` qualified access in expressions (`sys::write()`)
- ✅ `::` qualified access in types (`sys::Stat`)

**AST Changes:**
- `Import` node: added `alias: Optional[str]`, `items: Optional[List[str]]`, `is_pub: bool`
- `FnDef`, `StructDef`, `EnumDef`, `ConstDef`, `VarDef`, `TypeAlias`, `TraitDef`, `ExternFn`: added `is_pub: bool`
- New `QualifiedIdent` expression for `alias::name`

**Token Changes:**
- Added `PUB` keyword

**Tests:**
- 24 new tests in `TestModuleSystem` (103 total parser tests passing)
- Tests cover all import variants, pub on all item types, :: access

**Documentation:**
- LANGUAGE.md §13 - Full module system documentation
- TODO.md - Updated with implementation status

**Remaining:**
- Import resolver: respect `pub` visibility, handle selective imports
- Name resolver: handle `alias::symbol` qualified names
- Emitter: only emit `pub` items in module metadata

---

## Multi-Project Ecosystem Setup (January 2026)

Created CONTRIBUTING.md with comprehensive guidance for the multi-project ecosystem:

**Documentation Sections:**
- Development philosophy (No Concessions & Ghost Doctrines)
- Multi-project ecosystem structure (langdev, valet, cryptosec)
- Git submodule workflow for language patches
- Test-driven development cycle (SPEC → FAIL → IMPL → PASS → REFAC → VERIFY → COMMIT)
- Verification pipeline (make test, make regression, make valgrind)
- Code style guidelines (Ritz and Python)
- Commit message format and conventions
- Pull request process and checklist

**Key Verification Commands:**
- `make test` - Full test suite (unit + ritz + ritz1 + examples)
- `make regression` - 4-stage regression (ritz0 → ritz1 → self-hosted)
- `make regression-quick` - Skip self-hosted bootstrap
- `make valgrind` - Memory leak checking on Tier 1 examples

**Submodule Workflow:**
1. Add `ritz-lang/ritz` as submodule
2. Create feature branch for patches
3. Follow TDD process
4. Push to fork, create PR to upstream
5. Rebase when upstream merges

---

## Phase 12.1: Async Framework Modularization (January 2026)

Refactored Valet's async_tasks infrastructure into clean, reusable ritzlib modules.

**New Modular Structure (`ritzlib/async/`):**
- ✅ `task.ritz` - `Task`, `TaskPool`, `TaskState` types with I/O buffers and IoVecBuilder
- ✅ `io.ritz` - `task_recv()`, `task_send()`, `task_sendv()`, `task_sendv_builder()`, `task_reset_for_recv()`
- ✅ `server.ritz` - `TaskServer` with accept loop patterns, multishot accept (kernel 5.19+)
- ✅ `executor.ritz` - `run_tasks()`, `block_on()`, `AsyncTaskRuntime` convenience wrapper
- ✅ `mod.ritz` - Module re-exports and comprehensive architecture documentation

**io_uring Additions (`ritzlib/uring.ritz`):**
- ✅ `uring_prep_writev()` - Vectored write for zero-copy responses
- ✅ `uring_prep_readv()` - Vectored read (scatter I/O)
- ✅ `uring_prep_accept_multishot()` - Efficient accept loop (one SQE, continuous CQEs)
- ✅ `IOSQE_*` flags for SQE configuration
- ✅ `IORING_ACCEPT_MULTISHOT` constant

**Bug Fixes:**
- Fixed `uring_cqe_seen()` calls missing second argument in async_net, async_runtime, executor, test_uring

**Tests:**
- ✅ `ritzlib/tests/test_async_server.ritz` - 5 comprehensive tests
- ✅ All 324 ritz0 language tests still passing

**Architecture:**
```
ritzlib/async/
├── task.ritz      # Task, TaskPool, spawn_task(), task_complete()
├── io.ritz        # task_recv(), task_send(), task_sendv(), task_sendv_builder()
├── server.ritz    # TaskServer, task_server_run(), task_server_run_multishot()
├── executor.ritz  # run_tasks(), block_on(), AsyncTaskRuntime
└── mod.ritz       # Re-exports, documentation, usage patterns
```

---

## Native String Literals (#89) (January 2026)

**Status:** ✅ COMPLETE - String literals now produce `String` type by default

**The Change:**
- `"hello"` → `String` type (heap-allocated, owned, requires `import ritzlib.string`)
- `c"hello"` → `*u8` type (null-terminated C-string, no import needed)
- Implicit `String → *u8` coercion when calling functions expecting `*u8`

**Implementation:**
- Phase 1: Added `c"..."` syntax for C-string literals (CSTRING token, CStringLit AST node)
- Phase 2: Added `String → *u8` implicit coercion via `string_as_ptr()`
- Phase 3: Changed `"..."` to call `string_from()` and return `String`
- Phase 4: Fixed all tests and ritzlib to use `c"..."` where needed

**Files Changed:**
- `tokens.py`: Added `CSTRING` token type
- `lexer.py`: Added `_lex_cstring()` for `c"..."` prefix
- `ritz_ast.py`: Added `CStringLit` AST node
- `parser.py`: Handle `CSTRING` → `CStringLit`
- `type_checker.py`: `StringLit` returns `String`, `CStringLit` returns `*u8`, added compatibility rule
- `emitter_llvmlite.py`: `StringLit` calls `string_from()`, added `_coerce_string_to_u8_ptr()`
- `move_checker.py`: `StringLit` is now `String` (non-Copy)
- Tests updated: test_level4, test_level11, test_level21-24, ritzlib/json.ritz

**Test Coverage:**
- `test_cstring.ritz`: 6 tests for C-string syntax
- `test_native_string.ritz`: 5 tests for String literal behavior
- `test_string_coercion.ritz`: 3 tests for String → *u8 coercion
- 8 new Python unit tests in test_lexer.py, test_parser.py
- All 178 pytest tests passing
- All level tests passing

---

## Fix sizeof(T) in Generic Functions (PR #91) (January 2026)

**Status:** ✅ COMPLETE - sizeof(T) now correctly returns concrete type size

**The Bug:**
`sizeof(T)` where T is a type parameter was returning 8 (pointer size) instead of the actual type size. This caused heap corruption when `Vec<T>` was used with structs larger than 8 bytes.

**The Fix:**
During monomorphization, substitute type parameters in `sizeof()` arguments, converting `sizeof(T)` to `sizeof(ConcreteType)`:

```python
# In monomorph.py _specialize_expr()
if isinstance(expr.func, rast.Ident) and expr.func.name == 'sizeof':
    if len(expr.args) == 1 and isinstance(expr.args[0], rast.Ident):
        type_param_name = expr.args[0].name
        if type_param_name in subst.mapping:
            concrete_type = subst.mapping[type_param_name]
            concrete_name = mangle_type_name(concrete_type)
            new_args = [rast.Ident(expr.args[0].span, concrete_name)]
```

**Test Coverage:**
- `test_sizeof_generic.ritz`: 4 tests covering:
  - `sizeof(i32)` = 4
  - `sizeof(i64)` = 8
  - `sizeof(BigStruct)` = 32 (4x i64)
  - `vec_alloc_size<BigStruct>(10)` = 320 bytes

---

## Async/Await Improvements (January 13, 2026)

**Status:** ✅ COMPLETE - Idiomatic async reference example and bug fixes

**Bug Fixes:**
- Fixed `__state` field collision in `async_transform_v2.py`:
  - Renamed internal `state` field to `__state` to avoid collision with user parameters named `state`
  - Without this fix, `async fn handler(state: *MyState)` would fail to compile
- Fixed `__await_result_N` fields not being added to Future struct:
  - When await result wasn't captured in a `let`, the synthetic variable wasn't being tracked
  - Now properly added to `current_locals` during analysis so it gets a field in the Future struct

**New I/O Primitives (`ritzlib/executor.ritz`):**
- `exec_async_recv(exec, fd, buf, len, flags)` - Async socket recv via io_uring
- `exec_async_send(exec, fd, buf, len, flags)` - Async socket send via io_uring
- `exec_async_close(exec, fd)` - Async close via io_uring

**Reference Example (`examples/75_async_reference`):**
7 comprehensive tests demonstrating idiomatic async Ritz patterns:

1. `test_simple_async` - Basic async fn without await
2. `test_async_with_await` - Single await in async fn
3. `test_async_chain` - Three-level async calling async
4. `test_sequential_awaits` - Multiple sequential awaits in one function
5. `test_await_in_sync` - Using await outside async fn (generates poll loop)
6. `test_block_on` - Using Executor with block_on
7. `test_async_io` - True async I/O with pipe read via io_uring

**Idiomatic Async I/O Pattern:**
```ritz
# State struct for async read
struct IoReadState
    exec: *Executor
    fd: i32
    buf: *u8
    len: i32
    result: i32

# Poll function - checks for completion before submitting
fn poll_io_read(state: *IoReadState) -> i32
    let exec: *Executor = state.exec
    if exec.waker_io_result != 0
        let res: i32 = exec.waker_io_result
        exec.waker_io_result = 0
        state.result = res
        return res
    return exec_async_read(exec, state.fd, state.buf, state.len, 0)

# Clean async wrapper - this is what user code should look like!
async fn do_async_read(state: *IoReadState) -> i32
    let result: i32 = await poll_io_read(state)
    result
```

**Files Changed:**
- `ritz0/async_transform_v2.py` - Fixed `__state` and `__await_result_N` bugs
- `ritzlib/executor.ritz` - Added `exec_async_recv`, `exec_async_send`, `exec_async_close`
- `examples/75_async_reference/` - New reference example (7 tests)
- `TODO.md` - Updated async/await implementation status

**Test Results:**
- All 259 pytest tests passing
- All async examples passing (62, 64, 65, 75)

---

## Grammar-Driven Parser (February 2026)

**Status:** ✅ COMPLETE - Generated parser now exceeds hand-written parser

**Goal:** Replace hand-written parser with grammar-generated parser for:
1. Single source of truth (grammar file)
2. Easier maintenance and modification
3. Reusable infrastructure for ritz1 self-hosting

**Implementation:**

1. **ritzgen-py tool (`tools/ritzgen-py`):**
   - Python-based parser generator from `grammars/ritz.grammar`
   - Generates recursive-descent parser with operator precedence climbing
   - Produces dict-based parse trees for maximum flexibility

2. **AST Adapter (`ritz0/parser_adapter.py`):**
   - Converts generated parser output to `ritz_ast` nodes
   - Same interface as hand-written `parser.py`
   - 1400+ lines of AST conversion logic

3. **Key Conversions Implemented:**
   - Function definitions (`fn_def`, `async fn`, `extern fn`, `pub fn`)
   - Struct definitions with generics and fields
   - Type system: named types, generics (`Result<T,E>`), pointers, arrays, refs
   - Statements: let, var, return, if, while, for, match, assign
   - Expressions: binary ops, unary ops, postfix (call, index, field), literals
   - Lvalues: `arr[i]`, `ptr.field`, `*ptr`, nested combinations
   - Imports, constants, attributes

**Test Results:**

| Parser | Examples Passing |
|--------|-----------------|
| Hand-written | 47/75 |
| **Generated** | **60/75** |

The generated parser passes **13 more examples** than the hand-written parser!

**Benefits Demonstrated:**
- Single source of truth: `grammars/ritz.grammar`
- Generated parser handles edge cases better than hand-written
- Infrastructure ready for ritz1 bootstrap (generate Ritz parser in Ritz)

**Files:**
- `grammars/ritz.grammar` - Canonical grammar definition
- `tools/ritzgen-py/` - Parser generator tool
- `ritz0/parser_gen.py` - Generated parser
- `ritz0/parser_adapter.py` - AST conversion layer
- `ritz0/ritz0.py` - Now uses generated parser by default

---

## Testing Framework: Runtime & Process Library (February 2026)

**Status:** ✅ COMPLETE - External runtime linking working, process library implemented

**Context:** Migrating from `test.sh` shell scripts to native Ritz `@test` integration tests.

**Design Decisions (TESTING_DESIGN.md v2):**
- Tests near code they test (unit) or integrations they test (integration)
- ELF-based test discovery from compiled symbols (not source parsing)
- Before/after hooks with attributes (`@before_all`, `@after_all`, `@before_each`, `@after_each`)
- Process API with ownership-based cleanup via Drop trait
- Memory allocation: `Vec<u8>` for growable output capture (heap-allocated, owned)

### External crt0-Style Runtime Linking ✅

**Created runtime object files:**
- ✅ `runtime/ritz_start.x86_64.ll` - For `main(argc: i32, argv: **i8)`
- ✅ `runtime/ritz_start_noargs.x86_64.ll` - For `main() -> i32`
- ✅ `runtime/ritz_start_envp.x86_64.ll` - For `main(argc, argv, envp)`
- ✅ `runtime/Makefile` - Builds .o files with clang

**Updated build.py:**
- ✅ `detect_main_signature()` - Parses source to determine main's parameter count
- ✅ `get_runtime_object()` - Returns appropriate runtime .o for main's signature
- ✅ All sources compiled with `--no-runtime`; `_start` comes from external .o
- ✅ Caching now applies uniformly to all files

**Verification:**
- ✅ hello example (0-arg main) works with external runtime
- ✅ echo example (2-arg main with argc/argv) works
- ✅ 8/10 tier1 examples pass; 2 failures are pre-existing ownership bugs

### Process Library ✅

- ✅ `ritzlib/process.ritz` (270 lines) - Process spawning and I/O
  - `spawn(cmd)` - Spawn with PATH search
  - `spawn_args(cmd, argv)` - Spawn with arguments
  - `spawn_full(cmd, argv, envp)` - Full control
  - `process_read_stdout_all()` → `Vec<u8>` - Capture all output
  - `process_read_line()` → `Vec<u8>` - Read single line
  - `process_write()`, `process_write_str()` - Write to stdin
  - `process_wait()` → `ProcessResult` - Wait for exit
  - `process_cleanup()` - Close pipes, reap zombie

### Parser Fixes ✅

- ✅ Fixed `parser_gen.py` for CSTRING and SPAN_STRING tokens
  - Added `TokenType.CSTRING` (93) and `TokenType.SPAN_STRING` (94)
  - Updated lexer `_lex_string()` to detect prefix (`c"..."`, `s"..."`)
  - C-strings and span-strings now correctly parsed

- ✅ Fixed CharLit parsing to return numeric ASCII values
  - `'a'` now returns 97, not `"'a'"`
  - Escape sequences work: `'\n'` → 10, `'\t'` → 9

**Files Changed:**
- `runtime/ritz_start.x86_64.ll` - External _start for 2-arg main
- `runtime/ritz_start_noargs.x86_64.ll` - External _start for 0-arg main
- `runtime/ritz_start_envp.x86_64.ll` - External _start for 3-arg main
- `runtime/Makefile` - Build .o files with clang
- `build.py` - Detect main signature, link with appropriate runtime .o
- `ritzlib/process.ritz` - New process spawning library
- `ritz0/parser_gen.py` - Added CSTRING/SPAN_STRING token handling
- `ritz0/parser_adapter.py` - Fixed CharLit parsing, added CStringLit/SpanStringLit
- `grammars/ritz.grammar` - Added CSTRING/SPAN_STRING token patterns
- `docs/TESTING_DESIGN.md` - Updated with v2 design

**Completed (Feb 2026):**
- [x] Convert `test.sh` to `@test` integration tests - 10 tier1 examples now have native tests
- [x] ELF-based test discovery - runner_test_v2 parses symbol table
- [x] Generic function calls (`func<T>()`) - Already working correctly
- [x] Fixed 7 excluded test files (symbol conflicts) - 204 tests now passing

---

*For archived session logs, see `docs/archive/TODO-phase10-bootstrap.md` and `docs/archive/DONE-phase10-bootstrap.md`*
