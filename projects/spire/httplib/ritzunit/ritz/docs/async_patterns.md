# Idiomatic Async Patterns in Ritz

This document describes the idiomatic patterns for async/await in Ritz. These patterns should be used in Valet and other async applications.

## Reference Example

See `examples/75_async_reference/src/main.ritz` for the gold standard implementation with 7 passing tests.

## Core Concepts

### Poll Encoding
- `-1` = Pending (operation not complete, will be resumed)
- `>= 0` = Ready (operation complete, result is the return value)

### Future Generation
When you write:
```ritz
async fn my_func(x: i32) -> i32
    x + 1
```

The compiler generates:
- `my_func_Future` struct (holds parameters and state)
- `my_func_poll(*my_func_Future) -> i32` function (state machine)

## Pattern 1: Simple Async Function

```ritz
async fn add_values(a: i32, b: i32) -> i32
    a + b
```

Usage:
```ritz
var future: add_values_Future = add_values(10, 32)
let result: i32 = add_values_poll(&future)
```

## Pattern 2: Async Calling Async (Chaining)

```ritz
async fn compute_base(x: i32) -> i32
    x * 3

async fn compute_derived(x: i32) -> i32
    let base: i32 = await compute_base(x)
    base + 10

async fn compute_final(x: i32) -> i32
    let derived: i32 = await compute_derived(x)
    derived * 2
```

The `await` keyword suspends until the inner async completes. The compiler handles state machine transitions automatically.

## Pattern 3: Multiple Sequential Awaits

```ritz
async fn pipeline(x: i32) -> i32
    let a: i32 = await step_a(x)
    let b: i32 = await step_b(a)
    let c: i32 = await step_c(b)
    c
```

Each `await` is a potential suspension point. The state machine tracks which await we're at.

## Pattern 4: Async I/O with io_uring (CRITICAL FOR VALET)

This is the pattern Valet should use for socket operations:

### Step 1: State Struct
```ritz
struct IoReadState
    exec: *Executor
    fd: i32
    buf: *u8
    len: i32
    result: i32
```

### Step 2: Poll Function
**IMPORTANT**: Must check `waker_io_result` BEFORE submitting new I/O!

```ritz
fn poll_io_read(state: *IoReadState) -> i32
    let exec: *Executor = state.exec

    # Check if we already have a result from io_uring completion
    if exec.waker_io_result != 0
        let res: i32 = exec.waker_io_result
        exec.waker_io_result = 0
        state.result = res
        return res

    # Submit async read to io_uring
    return exec_async_read(exec, state.fd, state.buf, state.len, 0)
```

### Step 3: Async Wrapper
```ritz
async fn do_async_read(state: *IoReadState) -> i32
    let result: i32 = await poll_io_read(state)
    result
```

### Step 4: Poll Wrapper for block_on
```ritz
fn do_async_read_wrapper(future_ptr: *u8) -> i32
    let future: *do_async_read_Future = future_ptr as *do_async_read_Future
    return do_async_read_poll(future)
```

### Step 5: Usage with Executor
```ritz
fn main() -> i32
    var exec: Executor
    executor_init(&exec)

    var state: IoReadState
    state.exec = &exec
    state.fd = some_fd
    state.buf = &buffer[0]
    state.len = buffer_size

    var future: do_async_read_Future = do_async_read(&state)
    let poll_fn: fn(*u8) -> i32 = do_async_read_wrapper
    let result: i32 = block_on(&exec, &future as *u8, poll_fn)

    executor_destroy(&exec)
    result
```

## Available Async I/O Primitives

From `ritzlib/executor.ritz`:

| Function | Purpose |
|----------|---------|
| `exec_async_read(exec, fd, buf, len, offset)` | Async file/pipe read |
| `exec_async_write(exec, fd, buf, len, offset)` | Async file/pipe write |
| `exec_async_accept(exec, fd, addr, addrlen, flags)` | Async socket accept |
| `exec_async_recv(exec, fd, buf, len, flags)` | Async socket recv |
| `exec_async_send(exec, fd, buf, len, flags)` | Async socket send |
| `exec_async_close(exec, fd)` | Async close |

## Valet Refactoring Guide

### Current (Manual State Machine - BAD)
```ritz
fn connection_handler(task: *Task) -> i32
    match task.handler_state
        0 =>
            task_recv(task)
            task.handler_state = 1
            return -1
        1 =>
            # Process and send
            task_send(task, response)
            task.handler_state = 2
            return -1
        2 =>
            return 0
    return 0
```

### Target (Idiomatic Async - GOOD)
```ritz
async fn connection_handler(state: *ConnectionState) -> i32
    let bytes_read: i32 = await do_async_recv(state)
    if bytes_read <= 0
        return bytes_read

    process_request(state)

    let bytes_sent: i32 = await do_async_send(state)
    bytes_sent
```

## Key Differences from Rust

1. **No Future trait** - Ritz uses generated `_Future` structs and `_poll` functions
2. **No Pin** - Futures are regular stack values
3. **No async runtime** - Use `block_on` with `Executor` directly
4. **Poll encoding** - Uses i32 (-1 = Pending, >= 0 = Ready) not enum

## Testing

Run the reference example:
```bash
cd examples/75_async_reference
../../ritz build
./async_reference
```

Expected output:
```
=== Async Reference Tests ===
Demonstrating idiomatic async Ritz patterns

test_simple_async... OK
test_async_with_await... OK
test_async_chain... OK
test_sequential_awaits... OK
test_await_in_sync... OK
test_block_on... OK
test_async_io... OK

All async reference tests PASSED!

This is the GOLD STANDARD for async Ritz code.
Valet and other async apps should follow these patterns.
```

## Roadmap: spawn / join / select

These primitives are planned to complete the async story:

### `spawn()` - Planned (Priority 1)

Fire-and-forget concurrent task creation:

```ritz
# Target API:
fn spawn(pool: *TaskPool, future_ptr: *u8, poll_fn: fn(*u8) -> i32)

# Usage:
spawn(&pool, &my_future as *u8, my_poll_fn)
```

**Implementation**: Wire `async fn` futures to existing `TaskPool.spawn_task()`.
Infrastructure exists in `async_tasks.ritz`, needs adapter layer.

**Effort**: 1-2 days

### `join()` - Planned (Priority 2)

Wait for multiple futures, return when ALL complete:

```ritz
# Target API:
async fn join2(a: *Future, b: *Future) -> (i32, i32)

# Usage:
let (res_a, res_b) = await join2(&future_a, &future_b)
```

**Implementation**: Pure library code. `JoinFuture` struct polls all children,
returns Ready only when all children are Ready.

**Effort**: 1 day

### `select()` - Planned (Priority 3)

Wait for multiple futures, return when ANY completes:

```ritz
# Target API:
async fn select2(a: *Future, b: *Future) -> SelectResult

# Usage - timeout pattern:
match await select2(&recv_future, &timeout_future)
    0 => # recv completed first
    1 => # timeout fired

# Usage - graceful shutdown:
match await select2(&work_future, &shutdown_signal)
    0 => # work done
    1 => # shutdown requested
```

**Implementation**: More complex due to cancellation semantics.
When one future wins, others must be cancelled. io_uring has `IORING_OP_CANCEL`
for in-flight I/O operations.

**Effort**: 3-5 days

### Target: Idiomatic Valet

With these primitives, Valet's connection handler becomes:

```ritz
async fn handle_connection(ctx: &mut ConnContext) -> i32
    loop
        # select: either recv data OR timeout after 30s
        match await select(do_recv(ctx), timeout(30))
            0 =>
                let req = parse_request(ctx)
                let resp = process(req)
                await do_send(ctx, resp)
            1 =>
                return 0  # Idle timeout

fn main() -> i32
    let server = listen(8080)
    loop
        let client_fd = await async_accept(server)
        var ctx = new_context(client_fd)
        spawn handle_connection(&mut ctx)
```

**Note**: Using `&mut ConnContext` instead of `*ConnContext` because:
- Borrow checker ensures no aliasing or use-after-free
- References are always valid (no null checks)
- Clear intent that the function mutates the context
- More idiomatic Ritz

Compare to the current 100+ line manual state machine. This is the goal.

## Current Limitations

1. **Manual wrappers** - Need poll wrapper functions for block_on (will be simplified)
2. **No tuple returns** - `join()` will need struct returns until tuples are implemented
3. **No async closures** - Must use explicit state structs for now
