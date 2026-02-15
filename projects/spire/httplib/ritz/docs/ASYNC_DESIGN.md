# Async/Await Design for Ritz

## Overview

This document describes the design of async/await support in Ritz, enabling high-performance asynchronous I/O with io_uring on Linux.

## Design Principles

1. **Zero runtime overhead** - No Go-style scheduler, no green threads
2. **Stackless coroutines** - State machine transformation like Rust
3. **Explicit async** - Functions must be marked `async`, awaits are explicit
4. **Single-threaded by default** - Event loop runs on main thread

## Syntax

### Async Functions

```ritz
async fn read_file(path: &str) -> Result<String, Error>
    let file = await File::open(path)?
    let content = await file.read_to_string()?
    Ok(content)
```

The `async` keyword precedes `fn` and transforms the function into a state machine that returns a `Future<T>`.

### Await Expression

```ritz
let result = await some_async_call()
```

The `await` keyword:
- Can only appear inside `async fn`
- Suspends execution until the future completes
- Returns the inner value of `Future<T>`

### Spawning Tasks

```ritz
fn main()
    let executor = Executor::new()

    # Spawn returns a handle
    let handle = executor.spawn(read_file("data.txt"))

    # Run until complete
    let result = executor.block_on(handle)
```

## Type System

### Future Trait

```ritz
trait Future<T>
    fn poll(self: &mut Self, cx: &mut Context) -> Poll<T>

enum Poll<T>
    Ready(T)
    Pending
```

### Async Function Return Type

An `async fn foo() -> T` has the signature:
- External: `fn foo() -> impl Future<T>`
- Internal: Returns an anonymous state machine struct

## Compilation Strategy

### State Machine Transformation

Each `async fn` is transformed into:

1. A struct holding all locals that live across await points
2. A `poll()` method implementing the Future trait
3. State tracking via an integer field

Example transformation:

```ritz
# Source
async fn example() -> i32
    let x = await get_value()
    let y = await get_other(x)
    x + y

# Transformed (conceptual)
struct ExampleFuture
    state: i32
    x: Option<i32>
    y: Option<i32>
    fut0: Option<GetValueFuture>
    fut1: Option<GetOtherFuture>

impl Future<i32> for ExampleFuture
    fn poll(self: &mut Self, cx: &mut Context) -> Poll<i32>
        match self.state
            0 =>
                self.fut0 = Some(get_value())
                self.state = 1
                # fall through
            1 =>
                match self.fut0.as_mut().unwrap().poll(cx)
                    Poll::Pending => return Poll::Pending
                    Poll::Ready(val) =>
                        self.x = Some(val)
                        self.fut1 = Some(get_other(val))
                        self.state = 2
            2 =>
                match self.fut1.as_mut().unwrap().poll(cx)
                    Poll::Pending => return Poll::Pending
                    Poll::Ready(val) =>
                        self.y = Some(val)
                        return Poll::Ready(self.x.unwrap() + self.y.unwrap())
```

### LLVM IR Representation

The state machine compiles to:
- A struct type for the future state
- A poll function with a switch on state
- Tail calls to nested futures

## Runtime Components

### Executor (`ritzlib/async.ritz`)

```ritz
struct Executor
    ready_queue: Vec<Task>
    io_context: IoContext

impl Executor
    fn new() -> Self
    fn spawn<F: Future<T>>(self: &mut Self, fut: F) -> JoinHandle<T>
    fn block_on<F: Future<T>>(self: &mut Self, fut: F) -> T
    fn run(self: &mut Self)  # Run until all tasks complete
```

### I/O Context (`ritzlib/uring.ritz`)

```ritz
struct IoContext
    ring: io_uring  # Raw io_uring instance

impl IoContext
    fn new(entries: u32) -> Result<Self, Error>
    fn submit_read(self: &mut Self, fd: i32, buf: &mut [u8]) -> ReadFuture
    fn submit_write(self: &mut Self, fd: i32, buf: &[u8]) -> WriteFuture
    fn wait(self: &mut Self) -> Vec<Completion>
```

### io_uring Syscalls

Required syscalls:
- `io_uring_setup(entries, params)` - Create ring
- `io_uring_enter(fd, to_submit, min_complete, flags)` - Submit/wait
- Memory-mapped submission/completion queues

## Implementation Phases

### Phase 1: Parser Changes
- Add `ASYNC` and `AWAIT` tokens to lexer
- Parse `async fn` in function definitions
- Parse `await` as unary prefix operator

### Phase 2: AST Changes
- Add `is_async: bool` field to `FnDef`
- Add `AwaitExpr` AST node

### Phase 3: Type Checking
- Verify `await` only in `async fn`
- Track async context in type checker
- Return type wrapping: `T` -> `Future<T>`

### Phase 4: State Machine Generation
- Identify await points
- Compute live variables across awaits
- Generate state struct
- Generate poll function

### Phase 5: Runtime Library
- Implement `Future` trait
- Implement `Executor`
- Implement io_uring bindings

### Phase 6: Async I/O
- Async file operations
- Async socket operations
- Integration tests

## Open Questions

1. **Pin semantics** - Do we need Rust-style `Pin<&mut Self>`?
   - Decision: Defer. Start without pinning, add if needed.

2. **Cancellation** - How to cancel in-flight operations?
   - Decision: Drop cancels. Executor drops tasks on shutdown.

3. **Timeout** - How to implement timeouts?
   - Decision: `select!`-style macro or `timeout(duration, future)` wrapper.

4. **Error handling** - Propagate errors through `?` in async?
   - Decision: Yes, `?` works normally on `Result<T, E>`.

## References

- [io_uring documentation](https://kernel.dk/io_uring.pdf)
- [Rust async book](https://rust-lang.github.io/async-book/)
- [Linux io_uring man page](https://man7.org/linux/man-pages/man7/io_uring.7.html)

---

*Created: 2026-01-09*
