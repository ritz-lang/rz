# Standard Library Reference

The Ritz standard library (ritzlib) provides 35 modules covering system calls, I/O, collections, async I/O, and more.

---

## Module Index

| Module | Purpose |
|--------|---------|
| `sys` | System calls and constants |
| `io` | I/O helpers (print, read) |
| `memory` | Memory allocation (mmap/munmap) |
| `gvec` | Generic Vec<T> — dynamic array |
| `hashmap` | Hash table |
| `fs` | Filesystem operations |
| `str` | String utilities |
| `async` | Async runtime |
| `async_tasks` | Async task management |
| `async_fs` | Async filesystem I/O |
| `async_net` | Async network I/O |
| `uring` | io_uring bindings |
| `args` | Command-line argument parsing |
| `json` | JSON parsing and serialization |
| `process` | Process spawning |

---

## sys — System Calls

The `sys` module provides direct Linux syscall bindings. This is the lowest-level interface.

```ritz
import ritzlib.sys { write, read, open, close, exit, SYS_write }
import ritzlib.sys { O_RDONLY, O_WRONLY, O_CREAT, O_TRUNC }
import ritzlib.sys { STDOUT_FILENO, STDERR_FILENO }

# Write to a file descriptor
fn write_bytes(fd: i32, data: @[u8]) -> isize
    write(fd, data.as_ptr(), data.len())

# Print to stdout
fn print(msg: StrView)
    write(STDOUT_FILENO, msg.as_ptr(), msg.len())

# Open a file
fn open_file(path: StrView, flags: i32) -> Result<i32, i32>
    let fd = open(path.as_cstr(), flags, 0o644)
    if fd < 0
        Err(-fd)
    else
        Ok(fd)

# Exit the process
fn die(code: i32) -> !
    exit(code)
```

**Key constants:**

| Constant | Value | Meaning |
|----------|-------|---------|
| `STDIN_FILENO` | 0 | Standard input |
| `STDOUT_FILENO` | 1 | Standard output |
| `STDERR_FILENO` | 2 | Standard error |
| `O_RDONLY` | 0 | Open for reading |
| `O_WRONLY` | 1 | Open for writing |
| `O_RDWR` | 2 | Open for reading and writing |
| `O_CREAT` | 64 | Create if not exists |
| `O_TRUNC` | 512 | Truncate to zero on open |
| `O_APPEND` | 1024 | Append writes |

---

## io — I/O Helpers

Higher-level I/O built on top of `sys`:

```ritz
import ritzlib.io { print, println, eprint, eprintln, read_line }

print("Hello")             # No newline
println("Hello")           # With newline
eprint("Error: ")          # To stderr
eprintln("Fatal error")    # To stderr with newline

# Read a line from stdin
let line = read_line()?    # Returns Result<String, Error>
```

---

## memory — Memory Allocation

```ritz
import ritzlib.memory { alloc, free, alloc_zeroed, realloc }

# Allocate N bytes (not zero-initialized)
let ptr: *u8 = alloc(1024)?

# Allocate N bytes (zero-initialized)
let ptr: *u8 = alloc_zeroed(1024)?

# Resize an allocation
let new_ptr: *u8 = realloc(ptr, old_size, new_size)?

# Free
free(ptr, size)
```

Ritz uses `mmap`/`munmap` for allocation — no `malloc`, no libc.

---

## gvec — Generic Vec<T>

```ritz
import ritzlib.gvec { Vec }

# Create
var v: Vec<i32> = Vec.new()
var v: Vec<String> = Vec.with_capacity(16)
var v: Vec<i32> = Vec.from([1, 2, 3])

# Mutate
v.push(42)
let last = v.pop()             # Option<i32>
v.insert(0, 99)                # Insert at index
v.remove(0)                    # Remove at index, returns value
v.clear()

# Access
let x = v[0]                   # Panics if out of bounds
let x = v.get(0)               # Option<i32> — safe access
let len = v.len()
let cap = v.capacity()
let is_empty = v.is_empty()

# Iteration
for item in v
    process(item)

for (i, item) in v.enumerate()
    print("{i}: {item}\n")

# Transformation
let doubled: Vec<i32> = v.map(|x| x * 2).collect()
let evens: Vec<i32> = v.filter(|x| x % 2 == 0).collect()
let total: i32 = v.fold(0, |acc, x| acc + x)

# Sorting
v.sort()
v.sort_by(|a, b| b.compare(a))    # Reverse sort

# Slicing
let slice: @[i32] = @v[1..4]
```

---

## hashmap — Hash Table

```ritz
import ritzlib.hashmap { HashMap }

# Create
var map: HashMap<String, i32> = HashMap.new()
var map: HashMap<String, i32> = HashMap.with_capacity(32)

# Insert and access
map.insert(String.from("key"), 42)
let val: Option<i32> = map.get("key")   # Borrows key
let val: Option<i32> = map.remove("key")

# Existence check
let has = map.contains_key("key")

# Iteration
for (key, val) in map
    print("{key}: {val}\n")

let len = map.len()
let is_empty = map.is_empty()
map.clear()

# Entry API (insert if missing)
map.entry(String.from("counter")).or_insert(0)
```

---

## fs — Filesystem Operations

```ritz
import ritzlib.fs { read_file, write_file, exists, list_dir, remove_file }

# Read entire file
let content: Vec<u8> = read_file("config.json")?
let text: String = read_file_text("config.json")?

# Write entire file
write_file("output.txt", content)?
write_file_text("output.txt", "Hello, World!")?

# Check existence
if exists("config.json")
    ...

# List directory
let entries: Vec<DirEntry> = list_dir("src/")?
for entry in entries
    print("{entry.name}\n")

# Remove
remove_file("temp.txt")?
```

---

## str — String Utilities

```ritz
import ritzlib.str { split, join, trim, parse_int, parse_float }

# Split
let parts: Vec<StrView> = split("a,b,c", ",")    # ["a", "b", "c"]

# Join
let joined: String = join(parts, ", ")    # "a, b, c"

# Trim
let trimmed: StrView = trim("  hello  ")    # "hello"
let left = trim_start("  hello  ")
let right = trim_end("  hello  ")

# Parse numbers
let n: i32 = parse_int("42")?
let f: f64 = parse_float("3.14")?
```

**StrView methods:**

```ritz
let s: StrView = "Hello, World!"

s.len()                   # 13
s.is_empty()              # false
s.starts_with("Hello")    # true
s.ends_with("!")          # true
s.contains("World")       # true
s.find("World")           # Some(7)

s[0..5]                   # "Hello"
s[7..]                    # "World!"
s[..5]                    # "Hello"

s.to_uppercase()          # Returns String "HELLO, WORLD!"
s.to_lowercase()          # Returns String "hello, world!"
```

---

## args — Argument Parsing

```ritz
import ritzlib.args { Args, Arg }

fn main()
    let args = Args.parse()

    let verbose = args.flag("--verbose", "-v")
    let output = args.option("--output", "-o").unwrap_or("out.txt")
    let input = args.positional(0).unwrap_or_error("Missing input file")

    if verbose
        print("Input: {input}, Output: {output}\n")
```

---

## json — JSON

```ritz
import ritzlib.json { parse_json, to_json, Value }

# Parse
let value: Value = parse_json("{\"name\": \"Alice\", \"age\": 30}")?

# Access
let name = value["name"].as_str()?    # "Alice"
let age = value["age"].as_i32()?      # 30

# Serialize
let obj = Value.object()
obj["name"] = Value.string("Bob")
obj["active"] = Value.bool(true)
let json_str = to_json(obj)
```

---

## uring — io_uring

Low-level io_uring interface. Most users should use `async_net` or `async_fs` instead.

```ritz
import ritzlib.uring { Ring, Op }

let ring = Ring.new(256)?    # Queue depth of 256

# Submit a read operation
let read_op = Op.read(fd, buffer, offset)
ring.submit(read_op)?

# Wait for completion
let result = ring.wait()?
```

---

## async_net — Async Networking

```ritz
import ritzlib.async_net { TcpListener, TcpStream, UdpSocket }

# TCP server
async fn serve()
    let listener = TcpListener.bind(":8080").await?
    loop
        let (stream, addr) = listener.accept().await?
        spawn handle_client(stream)

async fn handle_client(stream:= TcpStream)
    let request = stream.read_until(b'\n').await?
    stream.write("HTTP/1.1 200 OK\r\n\r\nHello!\r\n").await?

# TCP client
async fn fetch(host: StrView, port: u16) -> Result<String, Error>
    let mut stream = TcpStream.connect(host, port).await?
    stream.write("GET / HTTP/1.1\r\nHost: {host}\r\n\r\n").await?
    let response = stream.read_all().await?
    Ok(String.from_utf8(response)?)
```

---

## process — Process Spawning

```ritz
import ritzlib.process { spawn, Command }

# Simple spawn
let child = spawn("ls", ["-la", "/home"])?
let exit_code = child.wait()?

# Builder API
let output = Command.new("grep")
    .arg("fn ")
    .arg("main.ritz")
    .output()?

print("{output.stdout}\n")
```

---

## See Also

- [Language Overview](overview.md)
- [Getting Started](../getting-started.md)
- [Ritz project page](../projects/ritz.md) — Compiler and ritzlib
