# Ritz Concurrency

High-performance async I/O with explicit, opt-in threading for CPU-bound work.

## Design Philosophy

1. **Async-first for I/O** — io_uring-based, zero-copy where possible
2. **Threads for CPU parallelism** — explicit, when you need it
3. **No colored functions** — async doesn't infect your entire API
4. **Ownership-aware** — borrow checker prevents data races

## Async I/O (Primary Model)

Ritz uses Linux's io_uring for maximum I/O throughput. This is the gold standard for:
- Network servers (thousands of concurrent connections)
- File I/O (parallel reads/writes)
- Any I/O-bound workload

### Basic Usage

```ritz
import ritzlib.async

fn main() -> Result<(), IoErr]
  # Run async code from sync main
  async.run(fn()
    let listener = TcpListener.bind("0.0.0.0:8080").await?

    loop
      let (stream, addr) = listener.accept().await?
      # Spawn concurrent handler (not a thread)
      async.spawn(handle_client(stream))
  )

fn handle_client(stream: TcpStream) -> Result<(), IoErr]
  var buf = [u8; 4096]
  loop
    let n = stream.read(&mut buf).await?
    if n == 0
      break
    stream.write(&buf[0..n]).await?
  Ok(())
```

### How It Works

```
┌─────────────────────────────────────────────┐
│                  User Code                   │
│   async.spawn(...)  stream.read().await     │
└─────────────────────┬───────────────────────┘
                      │
┌─────────────────────▼───────────────────────┐
│              Async Runtime                   │
│   Task queue, wakers, completion handling   │
└─────────────────────┬───────────────────────┘
                      │
┌─────────────────────▼───────────────────────┐
│               io_uring                       │
│   Submission queue → Kernel → Completion    │
└─────────────────────────────────────────────┘
```

No syscall per I/O operation. Batch submissions, batch completions.

### Async API

```ritz
# Run async code from sync context
fn async.run<T>(f: fn() -> T) -> T

# Spawn a concurrent task (cooperative, not a thread)
fn async.spawn<T>(f: fn() -> T) -> Task<T>

# Wait for task completion
fn Task<T>.await(self) -> T

# Yield to other tasks
fn async.yield()

# Sleep without blocking a thread
fn async.sleep(duration: Duration)

# Wait for multiple tasks
fn async.join(tasks: &[Task<T>]) -> Vec<T>
fn async.select(tasks: &[Task<T>]) -> (usize, T)  # first to complete
```

### Async File I/O

```ritz
import ritzlib.async.fs

fn main() -> Result<(), IoErr]
  async.run(fn()
    # Parallel file reads
    let t1 = async.spawn(fs.read("file1.txt"))
    let t2 = async.spawn(fs.read("file2.txt"))
    let t3 = async.spawn(fs.read("file3.txt"))

    let results = async.join(&[t1, t2, t3])

    for data in results
      process(data?)
  )
```

### No Colored Functions

Unlike Rust, Ritz async doesn't require `async fn` declarations:

```ritz
# This function works in both sync and async contexts
fn read_config(path: &Str) -> Result<Config, IoErr]
  let data = fs.read(path)?  # blocks in sync, yields in async
  parse_config(data)

# Sync context
fn main()
  let cfg = read_config("config.toml")?

# Async context
fn server_main()
  async.run(fn()
    let cfg = read_config("config.toml")?  # same function!
    start_server(cfg)
  )
```

The runtime detects context automatically. In sync context, I/O blocks. In async context, I/O yields.

**Tradeoff:** Slightly more runtime magic, but dramatically simpler APIs. No `.await` everywhere, no `async` keyword infection.

## Channels (Async + Sync)

MPSC channels work in both contexts:

```ritz
import ritzlib.sync.chan

fn main()
  async.run(fn()
    let (tx, rx) = chan[i32](cap: 100)

    # Producer task
    async.spawn(fn()
      for i in 0..1000
        tx.send(i)  # yields if buffer full
      tx.close()
    )

    # Consumer (main task)
    var sum = 0
    while let Some(x) = rx.recv()  # yields if buffer empty
      sum += x

    print(sum)
  )
```

### Channel API

```ritz
fn chan<T>() -> (Sender<T>, Receiver<T>)           # unbounded
fn chan<T>(cap: usize) -> (Sender<T>, Receiver<T>) # bounded

fn Sender<T>.send(self: &Sender<T>, val: T)
fn Sender<T>.try_send(self: &Sender<T>, val: T) -> Result<(), SendErr<T>]
fn Sender<T>.close(self: Sender<T>)

fn Receiver<T>.recv(self: &Receiver<T>) -> Option<T>
fn Receiver<T>.try_recv(self: &Receiver<T>) -> Result<T, RecvErr]
```

## Threads (Explicit, for CPU-Bound Work)

For CPU parallelism, use explicit threads:

```ritz
import ritzlib.thread

fn main()
  # CPU-intensive work benefits from threads
  let handles = Vec.new()

  for chunk in data.chunks(4)
    let c = chunk.clone()
    handles.push(thread.spawn(fn() -> i64
      expensive_computation(c)
    ))

  var total = 0i64
  for h in handles
    total += h.join()?

  print(total)
```

### Thread API

```ritz
fn thread.spawn<T>(f: fn() -> T) -> JoinHandle<T>
fn JoinHandle<T>.join(self) -> Result<T, ThreadErr]

fn thread.current() -> Thread
fn thread.sleep(duration: Duration)
fn thread.yield_now()

# Number of CPUs (for work partitioning)
fn thread.available_parallelism() -> usize
```

### Thread Pool (For Mixed Workloads)

```ritz
import ritzlib.thread.pool

fn main()
  let pool = ThreadPool.new(thread.available_parallelism())

  # Submit CPU work
  let future = pool.submit(fn() -> i64
    heavy_computation()
  )

  # Meanwhile, do async I/O
  async.run(fn()
    let data = fetch_from_network().await?

    # Wait for CPU work
    let result = future.get()

    combine(data, result)
  )
```

## Multi-Core Parallelism (IPC)

When you genuinely need multiple cores for CPU-bound work, Ritz provides efficient IPC mechanisms:

### Work Stealing Thread Pool

For data-parallel workloads:

```ritz
import ritzlib.thread.pool

fn main()
  let pool = WorkPool.new()  # one worker per core

  # Parallel map
  let results = pool.map(items, fn(item) -> Result
    expensive_transform(item)
  )

  # Parallel reduce
  let sum = pool.reduce(numbers, 0, fn(acc, x) -> i64
    acc + x
  )
```

### Shared Memory Regions

For zero-copy data sharing between workers:

```ritz
import ritzlib.shm

fn main()
  # Allocate shared memory region
  let region = Shm.create(size: 1_000_000)?

  # Get typed views (no copy, same memory)
  let data = region.as_slice::<f64>()

  # Spawn workers that all read from shared data
  let pool = WorkPool.new()
  let results = pool.map(0..num_chunks, fn(chunk_id) -> f64
    let start = chunk_id * chunk_size
    let end = start + chunk_size
    process_chunk(&data[start..end])
  )
```

### Message Passing (Structured Parallelism)

For pipeline-style parallelism:

```ritz
import ritzlib.sync.chan

fn main()
  # Pipeline: reader → parser → processor → writer
  let (raw_tx, raw_rx) = chan[Bytes](cap: 64)
  let (parsed_tx, parsed_rx) = chan[Record](cap: 64)
  let (result_tx, result_rx) = chan[Output](cap: 64)

  # Each stage runs on its own thread
  thread.spawn(fn() reader(raw_tx))
  thread.spawn(fn() parser(raw_rx, parsed_tx))
  thread.spawn(fn() processor(parsed_rx, result_tx))
  writer(result_rx)  # main thread
```

### Parallel Iterators

Declarative parallelism for collections:

```ritz
import ritzlib.iter.par

fn main()
  let results = items
    .par_iter()                    # switch to parallel
    .filter(fn(x) x.is_valid())
    .map(fn(x) expensive_transform(x))
    .collect()                     # back to sequential
```

Under the hood: work-stealing, automatic chunk sizing, preserves order.

### When to Use What

| Pattern | Use Case | Mechanism |
|---------|----------|-----------|
| **Async** | I/O-bound (network, files) | io_uring, single thread |
| **Thread pool** | CPU-bound, independent items | work stealing |
| **Shared memory** | Large datasets, read-heavy | mmap, no copy |
| **Channels** | Pipeline stages, producers/consumers | bounded queues |
| **Par iterators** | Transform collections | work stealing + channels |

### Example: Image Processing Pipeline

```ritz
import ritzlib.thread.pool
import ritzlib.shm

fn process_images(paths: &[Path]) -> Result<(), IoErr]
  let pool = WorkPool.new()

  # Load images in parallel (I/O + decode)
  let images = pool.map(paths, fn(path) -> Image
    Image.load(path)?
  )

  # Process in parallel (CPU-bound)
  let processed = pool.map(&images, fn(img) -> Image
    img.resize(800, 600)
       .adjust_contrast(1.2)
       .sharpen()
  )

  # Encode and write in parallel
  pool.for_each(processed.iter().enumerate(), fn((i, img))
    img.save(format!("out_{}.jpg", i))?
  )

  Ok(())
```

## Sync Primitives

For shared state (use sparingly):

```ritz
import ritzlib.sync

# Mutual exclusion
struct Mutex<T>
fn Mutex<T>.new(val: T) -> Mutex<T>
fn Mutex<T>.lock(self: &Mutex<T>) -> MutexGuard<T>
fn Mutex<T>.try_lock(self: &Mutex<T>) -> Option<MutexGuard<T>]

# Read-write lock
struct RwLock<T>
fn RwLock<T>.read(self: &RwLock<T>) -> ReadGuard<T>
fn RwLock<T>.write(self: &RwLock<T>) -> WriteGuard<T>

# Thread-safe reference counting
struct Arc<T>
fn Arc<T>.new(val: T) -> Arc<T>
fn Arc<T>.clone(self: &Arc<T>) -> Arc<T>

# Atomics
struct AtomicI32, AtomicU64, AtomicBool, AtomicPtr<T>
# with load, store, swap, compare_exchange, fetch_add, etc.
```

## Ownership and Concurrency

The borrow checker prevents data races:

```ritz
fn main()
  var data = Vec.new()
  data.push(1)

  # ERROR: cannot move `data` into task while borrowed elsewhere
  async.spawn(fn()
    data.push(2)
  )

  # OK: move data into task
  async.spawn(fn()
    var d = data  # moved
    d.push(2)
  )

  # OK: share via Arc
  let shared = Arc.new(Mutex.new(data))
  let s = shared.clone()
  async.spawn(fn()
    shared.lock().push(2)
  )
```

### Send and Sync

Types are implicitly `Send` (can cross task/thread boundaries) and `Sync` (can be shared) unless they contain:

- Raw pointers
- Interior mutability without synchronization
- Thread-local state

```ritz
# Explicitly mark as not thread-safe
struct NotSync
  local_cache: *mut u8

# Arc requires T: Send + Sync
let shared = Arc.new(data)  # only compiles if data is Send + Sync
```

## Syscall Layer

| Primitive | Underlying Mechanism |
|-----------|---------------------|
| `async.run` | io_uring setup, event loop |
| `async.spawn` | task queue (no syscall) |
| `.await` on I/O | io_uring SQE submission |
| `thread.spawn` | `clone` syscall |
| `Mutex` | `futex` |
| `chan` | `futex` + ring buffer |

## Performance Characteristics

### io_uring Advantages

- **Batched syscalls**: Submit many I/O ops in one syscall
- **Zero-copy**: Direct buffer registration
- **Kernel-polled**: Optional busy-polling for ultra-low latency
- **Unified API**: Files, sockets, timers — all through one interface

### When to Use What

| Workload | Model | Why |
|----------|-------|-----|
| Web server | async | Thousands of connections, mostly waiting |
| File processing | async | I/O bound, parallel reads |
| Image processing | threads | CPU bound, data parallel |
| Compression | threads | CPU bound |
| Database server | async + thread pool | I/O for network, CPU for queries |

## Implementation Notes

### Phase Order

Concurrency is **Phase 5** (ritzlib). It requires:

1. Generics (`Arc<T>`, `Mutex<T>`, `Task<T>`)
2. Closures (spawn takes `fn() -> T`)
3. Borrow checker with `Send`/`Sync` tracking

### ritz0 Approach

For ritz0 (bootstrap), no concurrency. The compiler is single-threaded.

For ritz1+, implementation order:

1. Basic io_uring wrapper (SQ/CQ management)
2. `async.run` / `async.spawn` / task scheduler
3. Async I/O (`read`, `write`, `accept`)
4. `thread.spawn` / `join` (clone syscall)
5. `Mutex`, `chan` (futex-based)
6. `Arc` (atomic reference counting)

### Fallback for Non-io_uring Systems

For older kernels (< 5.1), fall back to epoll:

```ritz
# Automatic detection at runtime
let backend = if io_uring.available()
  IoBackend.IoUring
else
  IoBackend.Epoll
```

Same API, different performance characteristics.
