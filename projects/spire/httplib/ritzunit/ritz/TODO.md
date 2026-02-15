# Ritz Language Development TODO

## Immediate: Code Quality & Cleanup

Before continuing with the async framework, let's address several inconsistencies discovered during review.

### Documentation Gaps

- [x] **Update LANGUAGE.md** - ✅ Added string interpolation section
- [x] **Close GitHub issues** - ✅ Closed #84 and #86

- [x] **Reconcile RITZLIB.md** - ✅ Updated with clear sections
  - Marked as "Future Design" with target hierarchical structure
  - Added "Current Structure" section documenting all 35 modules
  - Clarified timeline: hierarchical org after Phase 2 complete

### String Type Consolidation ✅ COMPLETE

Consolidated from THREE overlapping string slice types to TWO:

| Type | File | Usage | Status |
|------|------|-------|--------|
| `Span<T>` | span.ritz | 7+ files | ✅ Keep - generic, established |
| ~~`Str`~~ | ~~slice.ritz~~ | ~~2 files~~ | ✅ Removed - was duplicate of Span<u8> |
| `String` | string.ritz | Many | ✅ Keep - owned, growable |

**Decision: Use `Span<u8>` for string slices** - Implemented!

`Span<T>` is the "ritzy" choice:
- Generic (works for any T, not just u8)
- Already established (6+ files use it)
- Consistent with Rust's `&[T]` pattern

**Completed**:
- [x] Add string-specific methods to `span.ritz` for `Span<u8>`:
  - HTTP constants as `Span<u8>` values (`http_200_ok()`, etc.)
  - Comparison helpers: `span_eq_cstr()`, `span_find_byte()`
  - Slicing helpers: `span_take()`, `span_skip()`, `span_from_bytes()`, `span_literal()`
- [x] Migrate `ritzlib/iovec.ritz` from `Str` to `Span<u8>` (`iovec_append_span()`)
- [x] Delete `ritzlib/slice.ritz`
- [ ] Update Valet to use `Span<u8>` (separate project)

### ritzlib Organization

Currently 35 flat files. Reorganization into subdirectories requires completing the module system.

### Module System Implementation ✅ PARSING COMPLETE

The parsing layer for the new module system is complete. See LANGUAGE.md §13 for full documentation.

**Implemented (Parsing):**
- [x] `pub` keyword for visibility (fn, struct, enum, const, type, trait, extern fn)
- [x] `import path as alias` - namespace aliasing
- [x] `import path { item1, item2 }` - selective imports
- [x] `import path { item } as alias` - selective with alias
- [x] `pub import` - re-exports
- [x] `::` qualified access in expressions (`sys::write()`)
- [x] `::` qualified access in types (`sys::Stat`)
- [x] 103 parser tests passing

**Remaining (Semantic Analysis):**
- [ ] Update import resolver to track visibility (only import `pub` items)
- [ ] Update name resolver to handle `alias::symbol` qualified names
- [ ] Update emitter to only emit `pub` items in module metadata

**Syntax Summary:**
```ritz
# Import variants
import ritzlib.sys                      # All pub items to namespace
import ritzlib.sys as sys               # Qualified: sys::write()
import ritzlib.sys { write, read }      # Selective
import ritzlib.sys { write } as io      # Selective with alias: io::write()
pub import ritzlib.sys { write }        # Re-export

# Visibility
pub fn exported() -> i32                # Exported
fn private_helper() -> i32              # Not exported
pub struct Point { x: i32, y: i32 }     # Exported struct
```

### print_int vs String Interpolation

Valet and ritzlib use `print_int(x)` everywhere instead of string interpolation:

```ritz
# Current (ugly):
print("Port: ")
print_int(cfg.port as i64)
print("\n")

# Should be:
"Port: {cfg.port}\n"
```

**Action**: Migrate high-visibility code to use interpolation once documented.

---

## Self-Hosting Journey: ritz1 Bootstrap

### Current Status

| Metric | Status |
|--------|--------|
| ritz0 tests | 324/324 passing |
| dual-compiler tests | 34/35 passing for ritz1 |
| Tier 1 examples | 11/11 compile with ritz1 |
| Tier 2 (generics) | Blocked on monomorphization |

### Bootstrap Phases

**Phase 1: ritz0 (Python Bootstrap) - ✅ COMPLETE**
- Full language implementation in Python
- All examples compile and run
- Test suite comprehensive

**Phase 2: ritz1 (Ritz Compiler, compiled by ritz0) - 🔄 IN PROGRESS**
- Compiler written in Ritz, compiled by Python bootstrap
- Currently handles basic programs (34/35 dual-compiler tests)
- Missing: Generics monomorphization, some stdlib imports
- NOT self-hosted yet - still depends on ritz0 to build

**Phase 3: ritz2 (Self-Hosted)**
- ritz1 compiles its own source code → produces ritz2
- ritz2 is functionally identical to ritz1
- This is TRUE self-hosting: Ritz compiling Ritz
- Validates compiler correctness (ritz1 == ritz2)

**Phase 4: Canonical Compiler**
- Archive ritz0 (Python bootstrap no longer needed)
- ritz2 becomes the reference implementation
- Future development happens in Ritz only

### Blocking Issues for Phase 2→3

1. **Generics monomorphization** (#72)
   - ritz1 parses generic types
   - ritz1 doesn't instantiate `Vec<i32>` → `Vec_i32_` correctly
   - Blocks all stdlib usage (Vec, Option, Result)

2. **Import resolution edge cases**
   - level4/01_ritzlib_str fails in ritz1
   - Need to debug import chain

3. **Method syntax in codegen**
   - ritz1 doesn't emit proper method dispatch
   - `v.push(x)` doesn't work

---

## Phase 12.1: Proper Async Framework ✅ REVIEWED & VERIFIED

**Status:** ✅ COMPLETE - Comprehensive review and verification completed January 13, 2026

### What We Have (Production Ready)

**io_uring Integration:**
- ✅ `ritzlib/uring.ritz` (598 lines) - Complete kernel bindings with vectored I/O
  - `uring_prep_readv()` - Scatter read operations
  - `uring_prep_writev()` - Gather write operations
  - `uring_prep_accept_multishot()` - Multishot accept (kernel 5.19+)
  - All SQE/CQE handling, 24 total functions

**Async Infrastructure:**
- ✅ `ritzlib/async_tasks.ritz` (499 lines) - Production-ready task pool
  - Fixed-size task management (256 tasks)
  - Event loop with handler callbacks
  - State machine support
  - TaskServer for complete server patterns
  - I/O helpers: task_recv, task_send, task_sendv

**Network Integration:**
- ✅ `ritzlib/async_net.ritz` - Socket operations with async runtime
- ✅ `ritzlib/async_runtime.ritz` - Original runtime system
- ✅ `ritzlib/async/` - New modular async patterns

**Documentation & Testing:**
- ✅ ASYNC_FRAMEWORK_STATUS.md - Architecture and design patterns
- ✅ ASYNC_FRAMEWORK_REVIEW_FINAL.md - 350+ line comprehensive review
- ✅ examples/async_echo_server.ritz - Complete working server
- ✅ ritz0/test/test_async_echo.ritz - 4 comprehensive tests
- ✅ All 125/125 tests passing, zero regressions

### Handler Pattern (Simple & Effective)

```ritz
fn my_handler(task: *Task) -> i32
    match task.handler_state
        0 => # RECV: submit read, advance state
            task_recv(task)
            task.handler_state = 1
            return -1  # pending

        1 => # SEND: echo data back
            let bytes = task.io_result
            if bytes > 0
                task.write_len = bytes
                task_send(task, bytes)
                task.handler_state = 2
                return -1  # pending

        2 => # DONE: task complete
            return 0
```

### Async/Await Implementation Status ✅ WORKING

**Compiler Support (async_transform_v2.py):**
- ✅ `async fn` declarations transformed to Future struct + poll function
- ✅ `await` expressions in async fn suspend and resume correctly
- ✅ `await` in non-async fn generates poll loop
- ✅ Fixed `__state` field collision (was `state`, conflicted with user params)
- ✅ Fixed `__await_result_N` fields now properly added to Future struct

**I/O Primitives (ritzlib/executor.ritz):**
- ✅ `exec_async_read()` - Async file/pipe read
- ✅ `exec_async_write()` - Async file/pipe write
- ✅ `exec_async_accept()` - Async socket accept
- ✅ `exec_async_recv()` - Async socket recv (NEW)
- ✅ `exec_async_send()` - Async socket send (NEW)
- ✅ `exec_async_close()` - Async close (NEW)
- ✅ `block_on()` - Drive future to completion with io_uring

**Reference Examples (examples/75_async_reference):**
- ✅ 7 tests demonstrating idiomatic async patterns
- ✅ test_async_io - True async I/O with pipe read
- ✅ Demonstrates clean async/await vs manual state machines

### Next Phase

When ready to implement Valet with async/await syntax:
- [ ] **spawn() support** - Concurrent task execution
- [ ] **Multi-task executor** - Full async runtime with spawn/join
- [ ] **Update Valet** - Rewrite with `async fn` instead of manual state machines

### Target API
```ritz
async fn handle_connection(client_fd: i32) -> i32
    let request = await recv(client_fd)
    let response = process_request(&request)
    await send(client_fd, &response)
    0

fn main() -> i32
    let server_fd = tcp_socket()
    tcp_bind(server_fd, 0, 8080)
    tcp_listen(server_fd, 1024)

    loop
        let client = await accept(server_fd)
        spawn handle_connection(client)  # Concurrent!
```

---

## Native String Literals (#89) - ✅ COMPLETE

Making `"hello"` produce a `String` type instead of `*u8`.

### Implementation Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Add `c"..."` syntax for C-string literals | ✅ Complete |
| 2 | Add `String → *u8` implicit coercion in function calls | ✅ Complete |
| 3 | Change `"..."` to produce `String` instead of `*u8` | ✅ Complete |
| 4 | Fix ritzlib and tests for new String behavior | ✅ Complete |

### Summary

**Syntax:**
- `"hello"` → `String` type (heap-allocated, owned, requires `import ritzlib.string`)
- `c"hello"` → `*u8` type (null-terminated C-string, no import needed)

**Implicit Coercion:**
- When a function expects `*u8` and receives `String`, compiler automatically calls `string_as_ptr()`
- Works for both user-defined and extern functions

**Migration:**
- Code using `"..."` as `*u8` should change to `c"..."`
- Code wanting String behavior just needs `import ritzlib.string`

**Tests:**
- 14 new Ritz tests (test_cstring.ritz, test_native_string.ritz, test_string_coercion.ritz)
- 8 new Python unit tests
- All 178 pytest tests passing
- All level tests passing

---

## Testing Framework: ritzunit Integration ✅ WORKING

**ritzunit** is a complete native test runner at `../ritzunit/`. Integration now working!

| Feature | Status |
|---------|--------|
| ELF-based self-discovery | ✅ Reads `/proc/self/exe`, parses symbol table |
| PIE/ASLR support | ✅ Detects base from `/proc/self/maps` |
| Fork-based isolation | ✅ Each test runs in forked process |
| Multi-file linking | ✅ **204 tests passing** from all test files |

### How It Works

```bash
./build_ritz0_tests.sh      # Build test binary
./build/ritz0_tests/tests   # Run tests - discovers test_* functions via ELF
```

The runner (`runner_test_v2.ritz`) reads its own ELF symbol table to find all
functions starting with `test_`, then calls each one. Tests return 0 for pass,
non-zero for fail.

### All Test Files Now Included ✅

All 7 previously excluded test files now compile together (204 tests passing):
- `test_level1` - `test_addition` renamed to `test_l1_addition`
- `test_level4` - `strlen/streq` renamed to `l4_strlen/l4_streq`
- `test_level6` - `sys_exit` renamed to `l6_exit`
- `test_level10` - `sum_array` renamed to `l10_sum_array`
- `test_level11` - all syscalls renamed to `l11_*` prefix
- `test_level13` - `test_array_*` renamed to `test_l13_array_*`
- `test_level14` - `heap_alloc/free` renamed to `l14_alloc/l14_free`

### Remaining Work

- [x] **Convert test.sh files to @test functions** - 10 tier1 examples have integration tests
- [x] **Fix generated parser for `func<T>()`** - Already working correctly

### Completed

- [x] Created `ritzlib/process.ritz` (270 lines) - Process spawning with ownership-based cleanup
- [x] Fixed `parser_gen.py` - Added CSTRING/SPAN_STRING token support
- [x] Fixed `parser_adapter.py` - CharLit now returns numeric ASCII value
- [x] Created external runtime files (`runtime/ritz_start*.ll`) for crt0-style linking
- [x] Updated `build.py` to detect main signature and link appropriate runtime
- [x] Fixed `build_ritz0_tests.sh` - Multi-file compilation with dedup, excludes conflicts
- [x] **First integration test** - `test_hello_output` in `examples/tier1_basics/01_hello/test/`
  - Fork/exec/pipe without generics (works with ritz0)
  - Replaces `test.sh` shell script with native Ritz test

---

## Open GitHub Issues

| Issue | Title | Status | Notes |
|-------|-------|--------|-------|
| #31 | Add type checking pass | Open | Critical for ritz1 |
| #51 | ritz1 DWARF debug info | Open | Medium priority |
| #72 | Complete ritz1 bootstrap | Open | Blocked on monomorphization |
| #84 | String interpolation | ✅ Closed | Implemented, documented |
| #86 | Type inference for let | ✅ Closed | Implemented, documented |
| #89 | Native string literals | ✅ Complete | Implemented with c"..." syntax |

---

## Grammar-Driven Parser ✅ COMPLETE

**Status:** Generated parser now exceeds hand-written parser (60/75 vs 47/75 examples)

The grammar-driven parser infrastructure is now the default for ritz0:

- **Grammar file:** `grammars/ritz.grammar` - single source of truth
- **Parser generator:** `tools/ritzgen-py/` - generates recursive-descent parser
- **Generated parser:** `ritz0/parser_gen.py` - dict-based parse trees
- **AST adapter:** `ritz0/parser_adapter.py` - converts to `ritz_ast` nodes

### Benefits Achieved

1. **Single source of truth** - Grammar file defines language syntax
2. **Generated parser outperforms hand-written** - 60 vs 47 examples pass
3. **Easier maintenance** - Change grammar, regenerate parser
4. **Reusable for ritz1** - Same grammar, generate Ritz parser in Ritz

### Remaining 15 Failing Examples

Most failures are in complex features the emitter doesn't fully support yet, not parser issues:
- String interpolation (`70_interp_string`, `71_type_inference`)
- Advanced async patterns (`54_async_fs`, `56_async_runtime`, `52_uring`)
- Complex I/O (`03_echo`, `11_grep`)
- Advanced examples (`42_json`, `43_toml`, `49_ritzgen`)

---

## Packaging Strategy (#107) - RFC ACCEPTED

See `docs/design/PACKAGING_RFC.md` for full specification.

**Decisions Made:**
- URI-based dependencies (path, git, SSH) - no central registry
- C interop as escape hatch only; ritzlib is pure Ritz
- Hybrid binary distribution (binary + LLVM IR + source)
- Ship ritz1 as binary + LLVM IR; deprecate Python bootstrapper

**Implementation Phases:**

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Local content-addressed caching | ✅ Complete |
| 1 | `ritz install` from URI | ✅ Complete |
| 2 | `[dependencies]` in ritz.toml | ✅ Complete (via Build System #109) |
| 2 | `ritz.lock` file generation | [ ] Pending |
| 2 | Dependency resolution algorithm | ✅ Complete (via Build System #109) |
| 2 | `ritz vendor` command | [ ] Pending |
| 3 | Cross-compilation support | [ ] Pending |
| 3 | Shared cache support | [ ] Pending |
| 3 | Binary release artifacts | [ ] Pending |

---

## Build System (#109) - RFC ACCEPTED

See `docs/design/BUILD_SYSTEM_RFC.md` for full specification.

**Key Decisions:**
- `sources = ["src"]` - Directory-based source discovery with glob support
- `entry = "module::main"` - Import-style entry points
- Dependency namespacing (`import squeeze.gzip`)
- `build/debug/` and `build/release/` output structure
- `ritzlib` is implicit dependency (no special `$RITZ` variable)

**Implementation Phases:**

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Multiple `[[bin]]` targets | ✅ Complete |
| 1 | Build profiles (debug/release) | ✅ Complete |
| 1 | Source discovery with globs | ✅ Complete |
| 1 | Entry point resolution (`entry = "module::main"`) | ✅ Complete |
| 2 | `[dependencies]` with namespacing | ✅ Complete |
| 2 | Transitive dependency resolution | ✅ Complete |
| 3 | LLVM BC caching (graceful fallback) | ✅ Complete |
| 3 | External .so FFI support | [ ] Pending |

---

## Principles

1. **Don't compromise language design** - Fix the language, don't work around it
2. **Use existing code** - Reference ritzlib, examples, and docs before writing new code
3. **Follow the style guide** - STYLE.md is authoritative
4. **Test-driven development** - Write tests before implementation
5. **Profile before optimizing** - Measure, don't guess
6. **Single source of truth** - Grammar defines syntax, generate everything else

---

*Last updated: 2026-02-13*
