# Ritz Async/Await Design Review

**LARB Document** | **Status:** Draft | **Date:** 2026-02-13

This document provides a deep-dive into Ritz's async capabilities for building scalable server software.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current Architecture](#2-current-architecture)
3. [What's Working Well](#3-whats-working-well)
4. [Design Issues](#4-design-issues)
5. [Comparison with Other Systems](#5-comparison-with-other-systems)
6. [Proposed Improvements](#6-proposed-improvements)
7. [ritzlib Pointer Audit](#7-ritzlib-pointer-audit)
8. [Roadmap](#8-roadmap)

---

## 1. Executive Summary

### Current State

Ritz has a **functional async system** based on:
- **io_uring** for high-performance non-blocking I/O (Linux 5.6+)
- **State machine transformation** of `async fn` to `_Future` structs + `_poll` functions
- **TaskPool** for concurrent connection handling
- **No external runtime** - direct kernel interface

### Strengths

| Aspect | Status |
|--------|--------|
| io_uring integration | ✅ Excellent - multishot accept, vectored I/O |
| Zero-copy I/O | ✅ Built-in with iovecs |
| Poll-based futures | ✅ Working, simple model |
| Connection pooling | ✅ Fixed-size TaskPool |
| SIMD/AVX for cryptosec | ✅ Great (per your feedback) |

### Weaknesses

| Aspect | Issue |
|--------|-------|
| **Pointer overuse** | `*Task`, `*TaskPool`, `*Runtime` everywhere |
| **Manual state machines** | `echo_handler` is manual `handler_state` matching |
| **No spawn/join/select** | Primitives documented but not implemented |
| **No cancellation** | io_uring supports it, Ritz doesn't expose it |
| **No structured concurrency** | Tasks are fire-and-forget |

### Goal

Transform from:
```ritz
fn echo_handler(task: *Task) -> i32
    if task.handler_state == 0
        task_recv(task)
        task.handler_state = 1
        return -1
    # ... 50 more lines of state machine
```

To:
```ritz
async fn echo_handler(conn: &mut Connection) -> Result<(), Error>
    loop
        let data = await conn.recv()?
        await conn.send(data)?
```

---

## 2. Current Architecture

### 2.1 Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Application                          │
│  async fn handler() -> i32                                  │
│      let x = await some_io()                                │
└────────────────────────────┬────────────────────────────────┘
                             │ Compiler transforms to:
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   Generated Future                          │
│  handler_Future { state: i32, ... }                         │
│  handler_poll(*handler_Future) -> i32                       │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                      TaskPool / TaskServer                  │
│  - Fixed array of Task structs                              │
│  - Event loop: poll READY tasks, wait on io_uring           │
│  - Match CQE user_data to task ID                           │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                        io_uring                             │
│  - SQE ring for submissions                                 │
│  - CQE ring for completions                                 │
│  - Multishot accept, vectored I/O                           │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Key Files

| File | Purpose |
|------|---------|
| `ritzlib/uring.ritz` | io_uring syscall bindings |
| `ritzlib/async_tasks.ritz` | TaskPool, TaskServer, event loop |
| `ritzlib/async_runtime.ritz` | Runtime, block_on |
| `ritzlib/async_net.ritz` | Socket helpers |
| `ritzlib/executor.ritz` | Alternative executor design |
| `ritz0/async_transform.py` | Compiler transformation |

### 2.3 Poll Convention

```ritz
# Return value encoding:
#   -1  = Pending (operation not complete)
#   >= 0 = Ready (operation complete, value is result)

fn my_poll(future: *MyFuture) -> i32
    if some_condition
        return -1  # Pending
    return 42      # Ready with value 42
```

This is simpler than Rust's `Poll<T>` enum but loses type safety.

### 2.4 Task Lifecycle

```
IDLE ──spawn_task──▶ READY ──poll──▶ WAITING ──CQE──▶ READY ──...──▶ Complete
                        │                                              │
                        └───────────── poll returns >= 0 ──────────────┘
```

---

## 3. What's Working Well

### 3.1 io_uring Integration

The io_uring bindings are comprehensive:

```ritz
# From ritzlib/uring.ritz
uring_prep_read(sqe, fd, buf, len, offset, user_data)
uring_prep_write(sqe, fd, buf, len, offset, user_data)
uring_prep_accept(sqe, fd, addr, addrlen, flags, user_data)
uring_prep_accept_multishot(sqe, ...)  # Kernel 5.19+
uring_prep_recv(sqe, fd, buf, len, flags, user_data)
uring_prep_send(sqe, fd, buf, len, flags, user_data)
uring_prep_close(sqe, fd, user_data)
uring_prep_writev(sqe, fd, iov, iovcnt, offset, user_data)  # Vectored I/O
uring_prep_timeout(sqe, ts, count, flags, user_data)
```

**Multishot accept** is especially nice - submit once, get continuous CQEs.

### 3.2 Vectored I/O (Zero-Copy)

```ritz
# From async_echo_server.ritz - build response without copying
var builder: IoVecBuilder
iovec_push_static(&builder, "HTTP/1.1 200 OK\r\n")
iovec_push_static(&builder, headers)
iovec_push(&builder, body_ptr, body_len)
task_sendv_builder(task)  # Single writev syscall
```

This is critical for high-performance servers.

### 3.3 Connection Pooling

```ritz
struct TaskPool
    tasks: [256]Task     # Fixed array, no allocation per connection
    next_id: i64
    active_count: i32
    ring: *IoUring
```

Fixed-size pool avoids allocation churn during request handling.

### 3.4 Idle Timeout Support

```ritz
task_server_set_idle_timeout(&srv, 30)  # 30 second idle timeout
```

Automatic cleanup of idle connections.

---

## 4. Design Issues

### 4.1 Pointer Overuse (Critical)

Nearly every async API uses raw pointers:

```ritz
# Current (problematic)
fn echo_handler(task: *Task) -> i32
fn spawn_task(pool: *TaskPool, fd: i32, handler: fn(*Task) -> i32) -> i32
fn task_pool_find(pool: *TaskPool, task_id: i64) -> *Task
fn runtime_read(rt: *Runtime, fd: i32, buf: *u8, count: i32, offset: i64) -> i64
```

**Problems:**
1. No null-safety guarantees
2. No borrow checking
3. Manual memory management
4. Confusing for Ritz developers

**Should be:**
```ritz
async fn echo_handler(task: &mut Task) -> Result<(), Error>
fn spawn_task(pool: &mut TaskPool, fd: i32, handler: ...) -> Result<(), Error>
fn task_pool_find(pool: &TaskPool, task_id: i64) -> Option<&Task>
```

### 4.2 Manual State Machines

The `async fn` transformation is incomplete. Real handlers still use manual state:

```ritz
# From async_echo_server.ritz - this is manual, not generated!
fn echo_handler(task: *Task) -> i32
    if task.handler_state == ECHO_STATE_RECV
        if task.io_result == 0
            task_recv(task)
            return -1
        task.handler_state = ECHO_STATE_SEND
        # ... manual state transition

    if task.handler_state == ECHO_STATE_SEND
        # ... more manual state
```

The `async/await` syntax exists but isn't used in the main server examples.

### 4.3 Missing Concurrency Primitives

From `async_patterns.md`, these are planned but not implemented:

| Primitive | Status | Priority |
|-----------|--------|----------|
| `spawn()` | Documented, not wired | High |
| `join()` | Documented, not implemented | High |
| `select()` | Documented, not implemented | High |
| `timeout()` | Partial (io_uring timeout) | Medium |
| `cancel()` | Not implemented | Medium |

### 4.4 No Structured Concurrency

Tasks are fire-and-forget:

```ritz
spawn_task(&pool, fd, handler)  # No way to wait for completion
                                 # No way to cancel
                                 # No way to propagate errors
```

**Goal:** Structured concurrency where child tasks are scoped to parents.

### 4.5 Error Handling

Current: Return codes scattered through the codebase.

```ritz
fn spawn_task(...) -> i32  # Returns 0 or -1
fn task_recv(task: *Task) -> i32  # Returns 0 or negative errno
```

**Should be:**
```ritz
fn spawn_task(...) -> Result<TaskHandle, SpawnError>
async fn recv(conn: &mut Connection) -> Result<usize, IoError>
```

---

## 5. Comparison with Other Systems

### 5.1 vs Rust async

| Aspect | Rust | Ritz (Current) | Ritz (Goal) |
|--------|------|----------------|-------------|
| Future type | `Future<Output=T>` trait | `_Future` struct + `_poll` fn | Same but cleaner |
| Pinning | Required (`Pin<&mut Self>`) | Not needed (no self-ref) | Keep it simple |
| Wakers | Complex `Waker` + `Context` | `user_data` matching | Same |
| Runtime | tokio/async-std | Custom io_uring | Same |
| Cancellation | Drop-based | Not implemented | io_uring cancel |

**Ritz advantage:** No Pin complexity, direct io_uring (no epoll layer).

### 5.2 vs Go goroutines

| Aspect | Go | Ritz |
|--------|-----|------|
| Model | M:N scheduling, goroutines | 1:1, io_uring completion |
| Memory | Stack per goroutine (~2KB min) | State struct per task |
| Channels | Built-in | Not yet |
| Select | Built-in | Planned |

**Ritz advantage:** No scheduler overhead, direct kernel interface.

### 5.3 vs io_uring liburing (C)

| Aspect | liburing | Ritz |
|--------|----------|------|
| Bindings | Manual SQE/CQE | Same (we wrap it) |
| Async syntax | None (manual callbacks) | `async fn` / `await` |
| Type safety | None | Ritz type system |

**Ritz advantage:** Higher-level syntax with same performance.

---

## 6. Proposed Improvements

### 6.1 Reference-Based Async APIs

**Phase 1: Core types**

```ritz
# New Connection type (replaces Task for user code)
struct Connection
    fd: i32
    read_buf: [8192]u8
    write_buf: [8192]u8
    # ... internal fields

impl Connection
    async fn recv(self: &mut Connection) -> Result<usize, IoError>
    async fn send(self: &mut Connection, data: StrView) -> Result<usize, IoError>
    async fn close(self: &mut Connection) -> Result<(), IoError>
```

**Phase 2: Server API**

```ritz
# High-level server
fn main() -> i32
    let server = Server.bind("0.0.0.0:8080")?

    server.run(|conn: &mut Connection| async
        loop
            let data = await conn.recv()?
            if data.len() == 0
                break
            await conn.send(data)?
        Ok(())
    )
```

### 6.2 Implement spawn/join/select

**spawn:**
```ritz
# Fire-and-forget concurrent task
let handle: TaskHandle = spawn(async
    await some_work()
)
```

**join:**
```ritz
# Wait for multiple tasks
let (a, b) = await join(
    async { compute_a() },
    async { compute_b() },
)
```

**select:**
```ritz
# Wait for first to complete
match await select(recv_future, timeout(30.seconds()))
    Select::First(data) => process(data)
    Select::Second(_) => return Err(Timeout)
```

### 6.3 Structured Concurrency

```ritz
# Child tasks scoped to parent
async fn handle_request(req: &Request) -> Response
    # These tasks are cancelled if handle_request returns/errors
    scope |s|
        s.spawn(log_request(req))
        s.spawn(update_metrics(req))

        let result = await process(req)
        result
```

### 6.4 Cancellation

```ritz
# Cancel in-flight operations
let handle = spawn(long_running_task())

# Later...
handle.cancel()  # Uses io_uring IORING_OP_CANCEL

# Or with timeout
let result = await handle.with_timeout(30.seconds())
```

---

## 7. ritzlib Pointer Audit

This section audits ritzlib modules for pointer usage that should be references.

### 7.1 async_tasks.ritz

| Current | Should Be | Priority |
|---------|-----------|----------|
| `fn echo_handler(task: *Task) -> i32` | `async fn handler(conn: &mut Connection) -> Result<(), Error>` | Critical |
| `fn spawn_task(pool: *TaskPool, ...)` | `fn spawn(pool: &mut TaskPool, ...)` | High |
| `fn task_pool_find(...) -> *Task` | `fn find(...) -> Option<&Task>` | High |
| `fn task_recv(task: *Task)` | `async fn recv(self: &mut Connection)` | Critical |
| `pool.ring: *IoUring` | `pool.ring: &mut IoUring` | Medium |
| `task.user_data: *u8` | Remove (use generics or closures) | Low |

### 7.2 async_runtime.ritz

| Current | Should Be | Priority |
|---------|-----------|----------|
| `fn runtime_init(rt: *Runtime)` | `fn Runtime.new() -> Result<Runtime, Error>` | High |
| `fn runtime_read(rt: *Runtime, ..., buf: *u8, ...)` | `fn read(rt: &mut Runtime, ..., buf: &mut [u8])` | High |
| `fn block_on_i32(rt: *Runtime, future_ptr: *u8, poll_fn: ...)` | Generic `fn block_on<F: Future>(rt: &mut Runtime, f: F)` | High |
| `var g_runtime: Runtime` (global) | Thread-local or explicit passing | Medium |

### 7.3 uring.ritz

| Current | Should Be | Priority |
|---------|-----------|----------|
| `fn uring_get_sqe(ring: *IoUring) -> *IoUringSqe` | `fn get_sqe(ring: &mut IoUring) -> Option<&mut IoUringSqe>` | High |
| `fn uring_prep_read(..., buf: *u8, ...)` | `fn prep_read(..., buf: &mut [u8])` | High |
| `fn uring_peek_cqe(...) -> *IoUringCqe` | `fn peek_cqe(...) -> Option<&IoUringCqe>` | High |

### 7.4 io.ritz

| Current | Should Be | Priority |
|---------|-----------|----------|
| `fn read(fd: i32, buf: *u8, len: i64) -> i64` | `fn read(fd: i32, buf: &mut [u8]) -> Result<usize, Error>` | High |
| `fn write(fd: i32, buf: *u8, len: i64) -> i64` | `fn write(fd: i32, buf: &[u8]) -> Result<usize, Error>` | High |
| `fn prints(s: *u8)` | `fn print(s: StrView)` | High |

### 7.5 gvec.ritz

| Current | Should Be | Priority |
|---------|-----------|----------|
| `fn vec_get(v: *GVec, i: i64) -> *u8` | `fn get(v: &GVec<T>, i: usize) -> Option<&T>` | High |
| `fn vec_push(v: *GVec, elem: *u8)` | `fn push(v: &mut GVec<T>, elem: T)` | High |

### 7.6 Estimated Effort

| Phase | Scope | Effort |
|-------|-------|--------|
| 1 | New Connection API (wrap Task) | 2-3 days |
| 2 | Convert async_tasks.ritz | 3-5 days |
| 3 | Convert async_runtime.ritz | 2-3 days |
| 4 | Convert io.ritz, gvec.ritz | 3-5 days |
| 5 | Implement spawn/join/select | 5-7 days |

**Total:** ~3-4 weeks for full async cleanup.

---

## 8. Roadmap

### Phase 1: Foundation (1 week)

- [ ] Define `Connection` struct with reference-based methods
- [ ] Create async `recv`/`send`/`close` that wrap Task internals
- [ ] Write migration guide for existing handlers
- [ ] Update echo server to use new API

### Phase 2: Core Primitives (2 weeks)

- [ ] Implement `spawn()` that returns `TaskHandle`
- [ ] Implement `join2()`, `join3()` for waiting
- [ ] Implement `select2()`, `select3()` with io_uring cancel
- [ ] Add `timeout()` wrapper

### Phase 3: Structured Concurrency (1 week)

- [ ] Design scope API
- [ ] Implement automatic cancellation on scope exit
- [ ] Add tests for cancellation behavior

### Phase 4: Error Handling (1 week)

- [ ] Define `IoError` enum
- [ ] Replace i32 return codes with `Result<T, E>`
- [ ] Propagate errors through async boundaries

### Phase 5: ritzlib Audit (2 weeks)

- [ ] Convert high-priority functions per §7
- [ ] Update all examples
- [ ] Deprecate pointer-based APIs
- [ ] Document new patterns

---

## Appendix A: Valet Integration

Valet (the HTTP server) should be the first production user of the new async APIs.

**Current Valet:**
```ritz
# Manual state machine, pointers everywhere
fn http_handler(task: *Task) -> i32
    match task.handler_state
        0 => ...  # Recv
        1 => ...  # Parse
        2 => ...  # Send headers
        3 => ...  # Send body
        # ... 100+ lines
```

**Target Valet:**
```ritz
async fn handle_http(conn: &mut Connection) -> Result<(), HttpError>
    loop
        let request = await recv_request(conn)?

        let response = match request.method
            Method::GET => handle_get(request)?
            Method::POST => handle_post(request)?
            _ => Response::method_not_allowed()

        await send_response(conn, response)?

        if !request.keep_alive
            break

    Ok(())
```

---

## Appendix B: Performance Notes

### io_uring Batching

Current code submits one SQE at a time:

```ritz
uring_prep_recv(sqe, ...)
uring_sqe_submit(&ring)  # Individual submit
```

Better: Batch submissions:

```ritz
# Prepare multiple SQEs
uring_prep_recv(sqe1, ...)
uring_prep_recv(sqe2, ...)
uring_prep_recv(sqe3, ...)

# Single submit for all
uring_submit(&ring)
```

### Fixed Buffers (io_uring)

io_uring supports pre-registered buffers for zero-copy:

```ritz
# Register buffers once at startup
uring_register_buffers(&ring, buffers, count)

# Use registered buffer (index into pre-registered array)
uring_prep_read_fixed(sqe, fd, buf_index, len, offset, user_data)
```

This eliminates kernel buffer copies. Not yet implemented in Ritz.

---

*This document is maintained by LARB. It will be updated as the async system evolves.*
