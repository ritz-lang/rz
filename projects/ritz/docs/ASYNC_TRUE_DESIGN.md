# True Async Implementation Design

## Current State (BROKEN)

```ritz
# This is NOT real async - it's synchronous code with syntax sugar
async fn fetch(x: i32) -> i32
    let a = await get_value(x)  # get_value is NOT async!
    a + 1

fn main() -> i32
    let result = fetch(5)  # Called directly, no executor!
```

Problems:
1. `await` just evaluates the inner expression synchronously
2. No executor polls futures
3. Awaiting non-async functions is meaningless
4. No actual suspension or resumption

## Goal: Real Async

```ritz
# A proper async function that can suspend
async fn read_file(path: *u8) -> i64
    let fd = await async_open(path, O_RDONLY)  # Suspends until I/O completes
    var buf: [1024]u8
    let n = await async_read(fd, &buf[0], 1024)  # Suspends again
    await async_close(fd)
    n

fn main() -> i32
    # block_on runs the future to completion
    let result = block_on(read_file("test.txt\0".ptr))
    print_int(result)
    0
```

## Core Concepts

### 1. Future Trait (Conceptual)

Every async function returns a Future that can be polled:

```ritz
# Conceptual trait (not actual syntax)
trait Future<T>
    fn poll(self: &mut Self, cx: &mut Context) -> Poll<T>

enum Poll<T>
    Ready(T)
    Pending
```

### 2. State Machine Transformation

An async function becomes:
- A struct holding state and locals
- A `poll()` function that switches on state

```ritz
# Source:
async fn add_values(x: i32) -> i32
    let a = await async_get(x)
    let b = await async_get(a)
    a + b

# Transformed to:
struct add_values_Future
    state: i32
    x: i32
    a: i32
    b: i32
    inner_future: *u8  # Currently polling inner future

fn add_values(x: i32) -> add_values_Future
    add_values_Future { state: 0, x: x, a: 0, b: 0, inner_future: 0 as *u8 }

fn add_values_poll(self: *add_values_Future, cx: *Context) -> Poll<i32>
    match (*self).state
        0 =>
            # State 0: Start first await
            let inner = async_get((*self).x)
            (*self).inner_future = &inner as *u8
            (*self).state = 1
            # Poll inner future
            let result = async_get_poll((*self).inner_future as *async_get_Future, cx)
            match result
                Ready(v) =>
                    (*self).a = v
                    (*self).state = 2
                    # Continue to next await...
                Pending => return Poll::Pending
        1 =>
            # State 1: Waiting for first await to complete
            let result = async_get_poll((*self).inner_future as *async_get_Future, cx)
            match result
                Ready(v) =>
                    (*self).a = v
                    (*self).state = 2
                Pending => return Poll::Pending
        2 =>
            # State 2: Start second await
            ...
        3 =>
            # State 3: Complete
            return Poll::Ready((*self).a + (*self).b)
```

### 3. Executor

The executor polls futures until completion:

```ritz
fn block_on<T>(future: impl Future<T>) -> T
    var ctx: Context
    var waker: Waker
    ctx.waker = &waker

    loop
        match future.poll(&ctx)
            Ready(value) => return value
            Pending =>
                # Wait for I/O events via io_uring
                wait_for_io_completion()
```

### 4. Async I/O with io_uring

The key: I/O operations submit to io_uring and return `Pending`:

```ritz
async fn async_read(fd: i32, buf: *u8, len: i32) -> i64
    # Submit read to io_uring
    let sqe = get_sqe()
    prep_read(sqe, fd, buf, len)
    submit()

    # Register waker to be called when CQE arrives
    register_waker(current_context().waker, sqe.user_data)

    # Return Pending - executor will poll again when I/O completes
    return Pending  # Special: compiler knows this suspends
```

When io_uring completes the operation:
1. Executor notices CQE ready
2. Finds associated waker
3. Calls waker.wake()
4. Polls the future again
5. This time, check CQE result and return Ready(n)

## Implementation Plan

### Phase 1: Proper poll() Generation

1. Change async fn transformation to generate actual poll() functions
2. poll() returns `Poll<T>` not just `T`
3. State machine switches on state field

### Phase 2: Executor Implementation

1. `block_on()` function that polls in a loop
2. Simple single-future executor first
3. Integrate with io_uring for waiting

### Phase 3: Async I/O Primitives

1. `async_open()`, `async_read()`, `async_write()`, `async_close()`
2. These submit to io_uring and return Pending
3. Track in-flight operations

### Phase 4: Waker Integration

1. When io_uring CQE arrives, wake associated future
2. Executor tracks which futures are waiting on which operations

## Test Cases

### Test 1: Simple Async (No Actual I/O)

```ritz
async fn immediate() -> i32
    42

fn test_immediate()
    let result = block_on(immediate())
    assert(result == 42)
```

### Test 2: Async with Await

```ritz
async fn inner() -> i32
    10

async fn outer() -> i32
    let x = await inner()
    x + 1

fn test_await()
    let result = block_on(outer())
    assert(result == 11)
```

### Test 3: Async I/O

```ritz
async fn read_first_byte(path: *u8) -> i32
    let fd = await async_open(path, O_RDONLY)
    var buf: [1]u8
    await async_read(fd, &buf[0], 1)
    await async_close(fd)
    buf[0] as i32

fn test_async_io()
    # Create test file with content "X"
    let result = block_on(read_first_byte("test.txt\0".ptr))
    assert(result == 88)  # ASCII 'X'
```

## Compiler Changes Required

1. **`async_transform.py`**: Generate proper state machine with Poll returns
2. **Emitter**: Handle `Poll<T>` enum correctly
3. **Type checking**: Ensure only async fns can be awaited
4. **Runtime**: Implement block_on() executor

## Success Criteria

1. `await` actually suspends execution
2. Multiple futures can make progress concurrently
3. I/O operations are truly asynchronous (other work can happen while waiting)
4. Test: async echo server handles multiple connections without blocking
