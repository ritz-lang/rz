# ritzlib: Standard Library

> **Status:** 🔮 **FUTURE DESIGN** - This document describes the *target* architecture for ritzlib.
>
> **Current State:** ritzlib is a flat 35-file structure. Reorganization into hierarchical modules is
> planned for after Phase 2 (module system) is complete.
>
> **See also:**
> - [Current ritzlib files](../ritzlib/) - What exists now
> - [MODULE_SYSTEM_IMPLEMENTATION.md](../MODULE_SYSTEM_IMPLEMENTATION.md) - Phase 1-2 complete

The Ritz standard library, built on Linux syscalls.

## Current Structure (Flat Module Layout)

Currently (as of January 2026), ritzlib is a flat collection of 35 modules:

**Core types & memory:**
- `types.ritz` - Fundamental types
- `span.ritz` - Generic slice type `Span<T>` (similar to `&[T]`)
- `string.ritz`, `slice.ritz` - String handling
- `heap.ritz`, `box.ritz` - Memory allocation and Box<T>
- `gvec.ritz` - Growable vector (Vec<T>)

**System interface:**
- `sys.ritz` - System calls (read, write, open, close, etc.)
- `io.ritz` - I/O interfaces
- `errno.ritz` - Error codes
- `fs.ritz` - File system operations
- `env.ritz` - Environment variables
- `args.ritz` - Command-line arguments

**Async & networking:**
- `uring.ritz` - Linux io_uring kernel interface (598 lines, 24 functions)
- `async.ritz` - Async types (Poll, Waker, Context)
- `async_tasks.ritz` - Task pool and event loop (499 lines)
- `async_net.ritz` - Async network operations
- `async_runtime.ritz` - Async runtime wrapper
- `async_fs.ritz` - Async file operations
- `executor.ritz` - Task executor

**Utilities:**
- `hashmap.ritz`, `hash.ritz` - Hash tables
- `eq.ritz` - Equality traits
- `buf.ritz` - Buffer utilities
- `elf.ritz` - ELF binary format
- `drop.ritz` - Drop trait
- `crt0.ritz` - C runtime initialization

**Tests & validation:**
- `tests/test_*.ritz` - Module test files

This flat structure works well for small libraries. As ritzlib grows, hierarchical organization (per the next section) will become desirable.

---

## Target Structure (Hierarchical, Future)

This section describes the *ideal* organization after Phase 2 (module system) and Phase 3 (monomorphization) are complete, allowing for proper re-exports and nested module visibility.

```
ritzlib/
  ritz.toml
  src/
    lib.ritz           # re-exports
    core/
      types.ritz       # i32, bool, etc. (compiler-known)
      mem.ritz         # ptr ops, copy, move
      slice.ritz       # &[T], &mut [T]
    alloc/
      alloc.ritz       # Allocator iface
      heap.ritz        # default allocator (mmap-based)
      vec.ritz         # Vec<T>
      str.ritz         # Str, StrBuf
      box.ritz         # Box<T>
    sys/
      linux.ritz       # raw syscall wrappers
      errno.ritz       # error codes
    io/
      io.ritz          # Reader, Writer ifaces
      file.ritz        # File
      stdio.ritz       # stdin, stdout, stderr
      buf.ritz         # BufReader, BufWriter
    fs/
      path.ritz        # Path
      dir.ritz         # read_dir, DirEntry
      ops.ritz         # copy, rename, remove
    proc/
      args.ritz        # command-line args
      env.ritz         # environment
      spawn.ritz       # Command, spawn
    fmt/
      fmt.ritz         # formatting iface
      print.ritz       # print, println, eprint
    net/
      addr.ritz        # IpAddr, SocketAddr
      tcp.ritz         # TcpStream, TcpListener
      udp.ritz         # UdpSocket
  test/
    test_vec.ritz
    test_str.ritz
    test_file.ritz
```

## Core Modules

### ritzlib.sys.linux

Raw syscall wrappers:

```ritz
extern fn syscall(num: i64, ...) -> i64

fn sys_read(fd: i32, buf: *mut u8, len: usize) -> isize
fn sys_write(fd: i32, buf: *const u8, len: usize) -> isize
fn sys_open(path: *const u8, flags: i32, mode: u32) -> i32
fn sys_close(fd: i32) -> i32
fn sys_mmap(addr: *mut u8, len: usize, prot: i32, flags: i32, fd: i32, off: i64) -> *mut u8
# ... etc
```

### ritzlib.io

Reader/Writer interfaces:

```ritz
iface Reader
  fn read(self: &mut Self, buf: &mut [u8]) -> Result<usize, IoErr]

iface Writer
  fn write(self: &mut Self, buf: &[u8]) -> Result<usize, IoErr]
  fn flush(self: &mut Self) -> Result<(), IoErr]
```

### ritzlib.io.File

```ritz
struct File
  fd: i32

fn File.open(path: &Str) -> Result<File, IoErr]
fn File.create(path: &Str) -> Result<File, IoErr]
fn File.read(self: &mut File, buf: &mut [u8]) -> Result<usize, IoErr]
fn File.write(self: &File, buf: &[u8]) -> Result<usize, IoErr]
fn File.read_all(self: &mut File) -> Result<Bytes, IoErr]
fn File.close(self: File) -> Result<(), IoErr]
```

### ritzlib.alloc.Vec

```ritz
struct Vec<T>
  ptr: *mut T
  len: usize
  cap: usize

fn Vec<T>.new() -> Vec<T>
fn Vec<T>.with_capacity(cap: usize) -> Vec<T>
fn Vec<T>.push(self: &mut Vec<T>, item: T)
fn Vec<T>.pop(self: &mut Vec<T>) -> Option<T>
fn Vec<T>.get(self: &Vec<T>, idx: usize) -> Option<&T]
fn Vec<T>.len(self: &Vec<T>) -> usize
```

### ritzlib.alloc.Str

```ritz
# Str is a borrowed string slice (&[u8] with UTF-8)
# StrBuf is an owned, growable string

fn Str.len(self: &Str) -> usize
fn Str.bytes(self: &Str) -> &[u8]
fn Str.contains(self: &Str, needle: &Str) -> bool
fn Str.split(self: &Str, delim: u8) -> SplitIter

fn StrBuf.new() -> StrBuf
fn StrBuf.from(s: &Str) -> StrBuf
fn StrBuf.push(self: &mut StrBuf, c: u8)
fn StrBuf.push_str(self: &mut StrBuf, s: &Str)
```

### ritzlib.fs

```ritz
fn read(path: &Str) -> Result<Bytes, IoErr]
fn write(path: &Str, data: &[u8]) -> Result<(), IoErr]
fn exists(path: &Str) -> bool
fn remove(path: &Str) -> Result<(), IoErr]
fn rename(from: &Str, to: &Str) -> Result<(), IoErr]
fn read_dir(path: &Str) -> Result<DirIter, IoErr]
```

### ritzlib.proc

```ritz
fn args() -> Args                    # command-line arguments
fn env(name: &Str) -> Option<Str]    # environment variable
fn exit(code: i32) -> !              # exit process

struct Command
fn Command.new(program: &Str) -> Command
fn Command.arg(self: &mut Command, arg: &Str) -> &mut Command
fn Command.spawn(self: &Command) -> Result<Child, IoErr]
fn Command.output(self: &Command) -> Result<Output, IoErr]
```

### ritzlib.fmt

```ritz
fn print(s: &Str)
fn println(s: &Str)
fn eprint(s: &Str)
fn eprintln(s: &Str)

# Future: format strings
# print(f"value: {x}")
```

### ritzlib.net

```ritz
struct TcpStream
fn TcpStream.connect(addr: &Str) -> Result<TcpStream, IoErr]
fn TcpStream.read(self: &mut TcpStream, buf: &mut [u8]) -> Result<usize, IoErr]
fn TcpStream.write(self: &TcpStream, buf: &[u8]) -> Result<usize, IoErr]

struct TcpListener
fn TcpListener.bind(addr: &Str) -> Result<TcpListener, IoErr]
fn TcpListener.accept(self: &TcpListener) -> Result<TcpStream, IoErr]
```

## No-Std Support

For kernel/embedded use, import only `ritzlib.core`:

```ritz
import ritzlib.core.mem
import ritzlib.core.slice

# No heap, no syscalls, just primitives
```

## Allocator Interface

```ritz
iface Allocator
  fn alloc(self: &mut Self, size: usize, align: usize) -> *mut u8
  fn dealloc(self: &mut Self, ptr: *mut u8, size: usize, align: usize)
  fn realloc(self: &mut Self, ptr: *mut u8, old_size: usize, new_size: usize, align: usize) -> *mut u8
```

Collections accept an allocator parameter:

```ritz
fn Vec<T>.new_in(alloc: &mut Allocator) -> Vec<T>
```
