# Ritz

The Ritz programming language compiler and standard library.

---

## Overview

Ritz is a compiled, statically typed systems programming language that targets LLVM IR. It provides Python-like syntax, Rust-like memory safety through ownership and borrowing, and zero-cost abstractions — all without a dependency on libc.

**Core design goals:**
- No libc — direct Linux syscalls only
- Indentation-based syntax (no braces, no semicolons)
- Ownership semantics encoded at the call site
- Self-hosting: the language compiles itself

---

## Where It Fits

Ritz is the foundation of the entire ecosystem. Every other project depends on it.

```
ritz (compiler)
└── (no dependencies — pure foundation)

Everything else:
├── ritzunit → ritz
├── squeeze → ritz
├── cryptosec → ritz
├── valet → ritz
└── ...
```

---

## Key Features

### Python-like Syntax

```ritz
fn add(a: i32, b: i32) -> i32
    a + b

fn greet(name: StrView)
    let message = "Hello, {name}!"
    print(message)
    print("\n")
```

No braces, no semicolons, significant indentation.

### Ownership Modifiers

Ownership is encoded in the function signature, not at the call site:

```ritz
fn read_data(source: DataSource) -> Vec<u8>    # Const borrow (default)
fn update(counter:& i32)                        # Mutable borrow
fn consume(conn:= Connection)                   # Move ownership

# Call sites are always clean
let data = read_data(source)
update(counter)
consume(conn)
```

### Result and Option

```ritz
fn find_user(id: i32) -> Option<User>
    db.lookup(id)

fn load_config(path: StrView) -> Result<Config, Error>
    let fd = open(path)?
    defer close(fd)
    let content = read_all(fd)?
    parse_config(content)
```

### Logical Keywords

```ritz
if a and b or not c
    do_something()
```

Not `&&`, `||`, or `!`.

### Defer

```ritz
fn process(path: StrView) -> Result<(), Error>
    let fd = open(path)?
    defer close(fd)     # Runs when scope exits, even on error
    process_file(fd)?
    Ok(())
```

---

## Compiler Components

| Component | Language | Description |
|-----------|----------|-------------|
| `ritz0/` | Python | Bootstrap compiler — Python source to LLVM IR |
| `ritz1/` | Ritz | Self-hosted compiler — Ritz source to LLVM IR |
| `ritzlib/` | Ritz | Standard library (35 modules) |
| `examples/` | Ritz | 75+ example programs in 5 tiers |
| `grammars/` | EBNF | Canonical grammar specification |
| `runtime/` | LLVM IR | Program startup code |

---

## Standard Library (ritzlib)

### System Interface

```ritz
import ritzlib.sys { write, read, open, close, exit }
import ritzlib.sys { SYS_write, SYS_exit }

fn print(msg: StrView)
    write(1, msg.as_ptr(), msg.len())
```

### Collections

```ritz
import ritzlib.gvec { Vec }
import ritzlib.hashmap { HashMap }

var items: Vec<i32> = Vec.new()
items.push(1)
items.push(2)

var map: HashMap<String, i32> = HashMap.new()
map.insert("key", 42)
```

### Async I/O

```ritz
import ritzlib.uring { Ring }
import ritzlib.async_net { TcpListener }

async fn serve()
    let listener = TcpListener.bind(":8080")?
    loop
        let conn = listener.accept().await?
        spawn handle_conn(conn)
```

---

## Type System

| Type | Description |
|------|-------------|
| `i8`, `i16`, `i32`, `i64` | Signed integers |
| `u8`, `u16`, `u32`, `u64` | Unsigned integers |
| `f32`, `f64` | Floating point |
| `bool` | Boolean |
| `StrView` | String slice (default for string literals) |
| `String` | Owned heap string |
| `Vec<T>` | Dynamic array |
| `HashMap<K, V>` | Hash table |
| `Option<T>` | Optional value (Some or None) |
| `Result<T, E>` | Success or error |
| `@T` | Immutable reference |
| `@&T` | Mutable reference |
| `*T` | Raw pointer (FFI only) |
| `[N]T` | Fixed-size array |

---

## Example Programs

Ritz ships with 75+ examples organized in tiers by complexity:

| Tier | Examples | Description |
|------|----------|-------------|
| 0 | hello world, fibonacci | Language basics |
| 1 | structs, enums, pattern matching | Core features |
| 2 | files, processes, networking | System programming |
| 3 | HTTP servers, JSON parsing | Library usage |
| 4 | async I/O, io_uring | Advanced patterns |

---

## Current Status

| Metric | Value |
|--------|-------|
| Language tests | 324 passing |
| Unit tests | 201 passing |
| Examples compiling | 48/48 |
| Self-hosting (ritz1) | 47/48 examples |

---

## Project Configuration

```toml
[package]
name = "myapp"
version = "0.1.0"

sources = ["src"]

[[bin]]
name = "myapp"
entry = "main::main"

[dependencies]
squeeze = { path = "../squeeze" }
```

---

## Related Projects

- [Ritzunit](ritzunit.md) — Test framework, always used alongside Ritz
- [Ritz-LSP](ritz-lsp.md) — IDE integration
- [Harland](harland.md) — Kernel written in Ritz
- [Getting Started](../getting-started.md) — Tutorial
- [Language Reference](../language/overview.md)
