# Ritzlib

The standard library for the Ritz programming language - system calls, I/O, collections, async I/O, and more.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

## Overview

Ritzlib is the standard library that ships with the Ritz compiler. It provides the foundational modules that Ritz programs need to interact with the operating system and work with data. Ritzlib is written in Ritz itself, making it both a practical library and a showcase of the language's capabilities.

The library is organized as individual `.ritz` files, each providing a focused set of functionality. Programs import specific modules they need rather than pulling in a monolithic standard library. Ritzlib is found automatically by the Ritz compiler via the `RITZ_PATH` environment variable.

Ritzlib spans from low-level syscall wrappers to high-level abstractions like async I/O with io_uring, JSON parsing, and hash maps. The same library works for both bare-metal kernel targets and standard Linux userspace programs.

## Features

- System call wrappers for Linux and Harland targets
- String and string view operations
- Dynamic arrays (`gvec`) and hash maps
- Memory allocation and management
- File system operations
- Async I/O using Linux io_uring
- Network socket operations
- JSON parsing and serialization
- ELF binary parsing (used by ritzunit for test discovery)
- Process management and environment access
- Option and Result types for error handling
- Timer and async task primitives

## Usage

```ritz
import ritzlib.io

fn main() -> i32
    print("Hello, world!\n")
    0
```

```ritz
import ritzlib.sys
import ritzlib.str
import ritzlib.gvec

fn main(argc: i32, argv: **u8) -> i32
    # String operations
    let s: *u8 = "hello"
    let len: i64 = strlen(s)

    # Dynamic array
    var items: GVec
    gvec_init(&items, 8)
    gvec_push(&items, 42)

    0
```

## Module Reference

| Module | Description |
|--------|-------------|
| `sys.ritz` | Raw syscall wrappers |
| `io.ritz` | High-level I/O (print, read) |
| `str.ritz` | String operations (strlen, strcmp, etc.) |
| `string.ritz` | Owned heap-allocated strings |
| `strview.ritz` | Zero-copy string slice views |
| `memory.ritz` | Memory allocation (malloc, free) |
| `heap.ritz` | Heap allocator internals |
| `gvec.ritz` | Generic dynamic array (Vec) |
| `hashmap.ritz` | Hash map data structure |
| `hash.ritz` | Hash functions |
| `fs.ritz` | File system operations |
| `env.ritz` | Environment variables and args |
| `args.ritz` | Command-line argument parsing |
| `process.ritz` | Process control (fork, exec, wait) |
| `net.ritz` | Network socket operations |
| `uring.ritz` | Linux io_uring async I/O |
| `async.ritz` | Async/await primitives |
| `json.ritz` | JSON parsing and serialization |
| `elf.ritz` | ELF binary parsing |
| `buf.ritz` | Buffered I/O |
| `span.ritz` | Slice/span type |
| `option.ritz` | Option type |
| `result.ritz` | Result type |
| `box.ritz` | Heap-allocated single values |
| `drop.ritz` | Drop trait for cleanup |
| `eq.ritz` | Equality trait |
| `testing.ritz` | Test support utilities |
| `timer.ritz` | Timer operations |
| `iovec.ritz` | Scatter-gather I/O vectors |
| `meta.ritz` | Compiler metadata |
| `crt0.ritz` | C runtime zero (program entry) |

## Dependencies

- Ritz compiler (ritzlib is part of the compiler distribution)
- Linux kernel 5.1+ for io_uring features

## Status

**Active development** - Core modules (sys, io, str, memory, gvec, hashmap) are stable and used by the full ecosystem. Async I/O, JSON, and collections are actively evolving alongside the compiler and ecosystem projects.

## License

MIT License - see LICENSE file
