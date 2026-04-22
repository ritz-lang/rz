# Missing Language Features Specification

> LARB-0013: Formalization of Unimplemented Language Features
>
> Status: DRAFT
> Author: Aaron Sinclair / Adele
> Date: 2026-04-22

This document formalizes language features that are either designed but
unimplemented, or needed but unspecified. Each feature includes syntax,
semantics, interaction with the ownership model, and priority.

---

## 1. `defer` Statement

### 1.1. Motivation

Ritz currently relies on the `Drop` trait for cleanup, which requires wrapping
values in structs. `defer` provides explicit, scope-based cleanup without the
boilerplate — essential for kernel code, file handles, locks, and temporary
allocations.

### 1.2. Syntax

```ritz
fn read_file(path: StrView) -> Result<Vec<u8>, Error>
    let fd: i32 = sys_open(path.ptr, O_RDONLY)
    if fd < 0
        return Err(Error::from_errno(fd))
    defer sys_close(fd)       # Runs when scope exits (any path)

    let buf: *u8 = alloc(4096)
    defer free(buf)           # Runs BEFORE the close (LIFO order)

    let n: i64 = sys_read(fd, buf, 4096)
    if n < 0
        return Err(Error::from_errno(n as i32))
        # defer free(buf) runs, then defer sys_close(fd) runs

    return Ok(Vec::from_raw(buf, n as u64))
    # defer free(buf) runs, then defer sys_close(fd) runs
```

### 1.3. Semantics

- `defer <expr>` registers an expression to execute when the enclosing scope
  exits (return, break, continue, end of block, or early exit via `?`).
- Multiple defers execute in **LIFO order** (last registered, first executed).
- Deferred expressions capture variables **by reference** at defer site.
- Deferred expressions execute even on error paths (`?` operator, explicit
  `return Err(...)`).
- `defer` is a statement, not an expression. It has no return value.

### 1.4. Interaction with Ownership

- Deferred expressions must not move owned values out of scope — they run
  after normal cleanup but before the scope's variables are dropped.
- If a deferred expression takes a reference, the reference must be valid at
  defer execution time. The compiler should check this.

### 1.5. Lowering

The compiler lowers `defer` to a cleanup block at each scope exit point:

```
fn example()
    let a = acquire()
    defer release(a)      # defer #1
    let b = acquire()
    defer release(b)      # defer #2
    ...
    return result

# Lowered to:
fn example()
    let a = acquire()
    let b = acquire()
    ...
    release(b)            # defer #2 (LIFO)
    release(a)            # defer #1
    return result
```

For multiple exit points (early returns, `?`), the compiler duplicates the
cleanup chain at each exit. This is simple and predictable — no runtime
overhead, no hidden allocations.

### 1.6. Priority

**Medium.** Drop trait covers most cases. `defer` is a convenience for
non-RAII resources (raw fds, raw pointers, locks acquired via FFI).

---

## 2. `alignof` Builtin

### 2.1. Motivation

`sizeof` already exists as a compiler builtin. `alignof` is its natural
companion — needed for correct struct layout, SIMD types, MMIO regions,
page-aligned allocations, and kernel data structures.

### 2.2. Syntax

```ritz
let size: u64 = sizeof(PageTableEntry)   # Existing
let align: u64 = alignof(PageTableEntry) # New

# Also useful in const context
const PAGE_SIZE: u64 = 4096
const PTE_ALIGN: u64 = alignof(PageTableEntry)
```

### 2.3. Semantics

- `alignof(T)` returns the alignment requirement of type `T` in bytes as `u64`.
- Must be evaluable at compile time (constant expression).
- For primitive types: follows the ABI (i8=1, i16=2, i32=4, i64=8, f32=4, f64=8).
- For structs: maximum alignment of any field (unless `[[packed]]`).
- For `[[packed]]` structs: 1 (no alignment).
- For arrays `[N]T`: same as `alignof(T)`.
- For pointers `*T`: 8 (on x86-64).
- For SIMD types: matches vector width (v4f32 = 16, v4f64 = 32).

### 2.4. Priority

**Medium.** Required for correct low-level code. Currently worked around by
hardcoding alignment values.

---

## 3. Conditional Compilation (`[[cfg(...)]]`)

### 3.1. Motivation

The compiler currently supports `[[target_os = "linux"]]` as a basic filter.
This needs to be generalized to a full conditional compilation system for:
- Multi-platform support (Linux, Harland, macOS, Windows)
- Architecture-specific code (x86_64, aarch64)
- Feature flags (debug, release, test)
- Optional dependencies

### 3.2. Syntax

```ritz
# On items (functions, structs, constants, imports)
[[cfg(target_os = "linux")]]
fn sys_write(fd: i32, buf: *u8, len: i64) -> i64
    return syscall3(SYS_WRITE, fd as i64, buf as i64, len)

[[cfg(target_os = "harland")]]
fn sys_write(fd: i32, buf: *u8, len: i64) -> i64
    return harland_syscall3(HARLAND_SYS_WRITE, fd as i64, buf as i64, len)

# Boolean combinators
[[cfg(all(target_os = "linux", target_arch = "x86_64"))]]
fn fast_memcpy(dst: *u8, src: *u8, len: u64)
    # AVX2 implementation

[[cfg(any(target_os = "linux", target_os = "harland"))]]
fn use_io_uring() -> bool
    return true

[[cfg(not(debug))]]
fn assert(cond: bool)
    pass  # Compiled out in release

# On imports
[[cfg(target_os = "linux")]]
import ritzlib.sys.linux as sys

[[cfg(target_os = "harland")]]
import ritzlib.sys.harland as sys

# On struct fields (for platform-specific layouts)
pub struct Thread
    tid: u64
    [[cfg(target_os = "linux")]]
    futex_addr: *u32
    [[cfg(target_os = "harland")]]
    chan_handle: u32
```

### 3.3. Predefined Conditions

| Condition | Values | Source |
|-----------|--------|--------|
| `target_os` | `"linux"`, `"harland"`, `"macos"`, `"windows"` | `--target` flag |
| `target_arch` | `"x86_64"`, `"aarch64"` | `--target` flag |
| `debug` | (boolean) | `--debug` flag |
| `test` | (boolean) | `--test` flag |
| `feature = "..."` | user-defined | `--feature` flag or `ritz.toml` |

### 3.4. Semantics

- `[[cfg(...)]]` is evaluated **before parsing the item body**. If the
  condition is false, the entire item is excluded from compilation.
- `all(a, b, c)` — all conditions must be true.
- `any(a, b, c)` — at least one condition must be true.
- `not(a)` — condition must be false.
- Conditions nest: `all(target_os = "linux", not(test))`.
- Unknown conditions are an error (prevents typos like `target_oss`).
- `cfg` on imports determines which module is loaded — this is the mechanism
  for platform-specific backends.

### 3.5. Interaction with Module System

`[[cfg]]` is the compile-time selection mechanism that replaces runtime
dispatch for platform abstraction:

```ritz
# ritzlib/sys.ritz — the single import point
[[cfg(target_os = "linux")]]
import ritzlib.sys.linux as backend

[[cfg(target_os = "harland")]]
import ritzlib.sys.harland as backend

# Application code uses sys.write() — doesn't know which backend
pub fn write(fd: i32, buf: *u8, len: i64) -> i64
    return backend.write(fd, buf, len)
```

### 3.6. Priority

**High.** Required for the Harland syscall abstraction layer. Currently
hardcoded to `[[target_os = "linux"]]` only.

---

## 4. Async Primitives: `spawn`, `join`, `select`

### 4.1. Motivation

The current async model is fire-and-forget (`spawn_task` returns `i32`).
There's no way to:
- Wait for a spawned task to complete and get its result
- Wait for the first of multiple futures to complete
- Cancel a running task
- Scope tasks to a parent (structured concurrency)

### 4.2. `spawn` — Launch a concurrent task

```ritz
# spawn returns a TaskHandle that can be awaited
let handle: TaskHandle<Response> = spawn async
    let data: Vec<u8> = await fetch(url)
    parse_response(data)

# Later, await the result
let response: Response = await handle
```

**Semantics:**
- `spawn <async-expr>` creates a new task on the current executor.
- Returns `TaskHandle<T>` where `T` is the return type of the async block.
- The task runs concurrently (not in parallel — single-threaded executor).
- `TaskHandle<T>` is a future — `await handle` yields `T`.
- Dropping a `TaskHandle` without awaiting it **cancels** the task.

### 4.3. `join` — Wait for multiple futures

```ritz
# Wait for both to complete, return tuple
let (users, posts) = await join(
    fetch_users(db),
    fetch_posts(db)
)

# join3, join4, etc. for more futures
let (a, b, c) = await join3(future_a, future_b, future_c)
```

**Semantics:**
- `join(f1, f2)` returns a future that completes when **both** complete.
- If either future errors, the other is cancelled and the error propagates.
- Result is a tuple of the individual results.
- `join` is a library function, not a keyword. It's generic over the future
  types.

### 4.4. `select` — Wait for first of multiple futures

```ritz
# Wait for whichever completes first
match await select(
    recv_message(chan),
    timeout(Duration::from_secs(30))
)
    Select::First(msg) =>
        process(msg)
    Select::Second(_) =>
        return Err(Error::Timeout)
```

**Semantics:**
- `select(f1, f2)` returns a future that completes when **either** completes.
- The other future is cancelled.
- Result is `Select<A, B>` enum indicating which completed.
- Essential for timeouts, graceful shutdown, multiplexing.

### 4.5. Cancellation

```ritz
let handle: TaskHandle<Response> = spawn async
    await long_running_operation()

# Cancel explicitly
handle.cancel()

# Or cancel implicitly via drop
fn example()
    let handle = spawn async { ... }
    if should_abort
        return  # handle dropped, task cancelled
```

**Semantics:**
- Cancellation is cooperative — the runtime sets a cancellation flag and the
  task checks it at the next `await` point.
- io_uring operations are cancelled via `IORING_OP_ASYNC_CANCEL`.
- `defer` blocks still run on cancellation.
- Cancellation is not instant — it happens at the next yield point.

### 4.6. Structured Concurrency (Future Work)

```ritz
# All spawned tasks are scoped to the block
async fn handle_request(req: Request) -> Response
    scope |s|
        s.spawn(log_request(req))
        s.spawn(update_metrics(req))
        let response = await process(req)
        return response
    # Both spawned tasks are cancelled/joined here
```

This is not in scope for the initial implementation but should inform the
design of `spawn` and `TaskHandle`.

### 4.7. Priority

**High.** The async model is incomplete without these. `spawn`/`join` are
needed for concurrent I/O. `select` is needed for timeouts and multiplexing.

---

## 5. Module System Redesign (Separate Compilation)

### 5.1. Current Problem

The compiler currently uses **AST merging** — all imported modules are parsed,
their ASTs are merged into a single flat AST, and the entire program is
compiled as one unit. This:

- Prevents incremental compilation (any change recompiles everything)
- Doesn't scale (ritz0 already struggles with large projects)
- Makes circular imports impossible
- Bloats binary size (no dead code elimination across modules)
- Is the #1 architectural blocker for self-hosting

### 5.2. Proposed Design: Symbol Tables + Separate Object Files

```
# Current (AST merging):
main.ritz + lib.ritz → merged AST → single .o → binary

# Proposed (separate compilation):
main.ritz → main.o  (imports only signatures from lib.ritz.sig)
lib.ritz  → lib.o   (exports signatures to lib.ritz.sig)
main.o + lib.o → binary (linked by ld)
```

### 5.3. Module Interface Files (`.ritz.sig`)

When compiling a module, the compiler emits a **signature file** containing:
- Public function signatures (name, params, return type)
- Public struct/enum definitions
- Public constant values
- Public type aliases
- Trait definitions and impls

```ritz
# Generated: ritzlib/io.ritz.sig
pub fn read(fd: i32, buf: *u8, len: i64) -> i64
pub fn write(fd: i32, buf: *u8, len: i64) -> i64
pub fn prints(s: StrView) -> i32
pub struct StrView
    ptr: *u8
    len: i64
```

When another module imports `ritzlib.io`, the compiler reads the `.sig` file
instead of parsing the full source. This enables:
- Parallel compilation (modules compile independently)
- Incremental compilation (only recompile changed modules)
- Faster compilation (signature files are tiny)

### 5.4. Build Order

1. Topological sort modules by import dependencies
2. Compile leaf modules first (no imports)
3. Generate `.sig` files alongside `.o` files
4. Compile dependent modules using `.sig` files for type checking
5. Link all `.o` files

For the common case of non-circular dependencies, this is straightforward.
Circular imports require either:
- Prohibiting them (simplest, Ritz should do this)
- Forward declarations (adds complexity)

### 5.5. Impact on Generics

Monomorphization across module boundaries requires the compiler to have access
to the generic function's **full body**, not just its signature. Options:

1. **Inline generic bodies in `.sig` files** — signature files include the
   AST of generic functions. This is what Rust does (monomorphization happens
   in the importing crate).
2. **Pre-monomorphize at known types** — the exporting module generates
   specializations for common types (i32, i64, u8, etc.).
3. **Require explicit instantiation** — the user specifies which types to
   monomorphize in the exporting module.

**Recommendation:** Option 1. Generic function bodies are included in `.sig`
files. The importing module monomorphizes as needed. This matches Rust's model
and is the most ergonomic.

### 5.6. Naming Convention

```
ritzlib/             # Standard library root
  sys.ritz           # Platform abstraction
  sys/
    linux.ritz       # Linux backend
    harland.ritz     # Harland backend
  io.ritz            # I/O utilities
  mem.ritz           # Memory management
  vec.ritz           # Vec<T>
  str.ritz           # String / StrView
  ...

# Import resolves to filesystem path:
import ritzlib.sys        # → $RITZ_PATH/ritzlib/sys.ritz
import ritzlib.sys.linux  # → $RITZ_PATH/ritzlib/sys/linux.ritz
```

### 5.7. Priority

**Critical.** This is the #1 blocker for the compiler rewrite (Phase 3) and
self-hosting (Phase 4). The current AST merging model does not scale.

---

## 6. Additional Missing Features (Lower Priority)

### 6.1. Octal Literals

```ritz
let mode: u32 = 0o755   # File permissions
let mask: u32 = 0o777
```

Spec'd in LANGUAGE_SPEC but not implemented in lexer. Low priority — hex works
as a substitute (`0x1ED` = `0o755`).

### 6.2. Additional Compound Assignment Operators

```ritz
x %= 10
flags &= mask
flags |= new_flag
value ^= key
bits <<= 3
bits >>= 1
```

Spec'd but only `+=`, `-=`, `*=`, `/=` are implemented. Medium priority.

### 6.3. `self` / `Self` as Keywords

Currently treated as identifiers. Should be reserved keywords:
- `self` — reference to current instance in methods
- `Self` — alias for the implementing type in `impl` blocks

Medium priority — methods work via positional `self` parameter but `Self` as a
type alias in impl blocks is missing.

### 6.4. Associated Functions (`Type::method`)

```ritz
impl Vec<T>
    pub fn new() -> Vec<T>
        # ...

let v: Vec<i32> = Vec::new()    # Not supported — no Type::fn syntax
let v: Vec<i32> = vec_new()     # Current workaround
```

High priority for ergonomics, but current workaround is functional.

---

## 7. Feature Priority Matrix

| Feature | Priority | Blocker For | Complexity |
|---------|----------|-------------|------------|
| **Module system redesign** | Critical | Phase 3 (compiler rewrite), Phase 4 (self-hosting) | Very High |
| **`[[cfg(...)]]` generalization** | High | Phase 6 (Harland), multi-platform | Medium |
| **`spawn`/`join`/`select`** | High | Phase 5 (stdlib), Phase 8 (infrastructure) | High |
| **`defer`** | Medium | Phase 6 (Harland kernel), ergonomics | Low |
| **`alignof`** | Medium | Phase 6 (Harland kernel), correctness | Low |
| **Compound assignment ops** | Medium | Completeness | Low |
| **`self`/`Self` keywords** | Medium | Ergonomics | Low |
| **Associated functions** | Medium | Ergonomics | Medium |
| **Octal literals** | Low | Completeness | Trivial |
| **Cancellation** | Medium | Phase 5 (stdlib async) | Medium |
| **Structured concurrency** | Low | Future work | High |
