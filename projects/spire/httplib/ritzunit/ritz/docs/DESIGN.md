# Ritz Language Design

Ritz is a minimalistic, type-safe systems programming language with implicit typing, Rust-style ownership/borrowing, and no inheritance. It compiles to LLVM IR and is designed to be useful for everything from scripting to operating system development.

## Core Design Pillars

### P0: Small Language, Big Library

Keep the core tiny:
- Expressions, structs/enums, functions, modules
- Generics, ownership/borrowing, pattern matching
- Minimal defer/drop model

Everything else is library: collections, async, processes, GPU, reflection.

### P1: Type-Safe + Implicit by Default

- Inference everywhere (locals, generics, lifetimes via elision + region inference)
- No implicit numeric coercions (explicit `as` casts)
- Default immutability

### P2: Ownership First; No GC Required

- Value semantics + deterministic destruction (RAII)
- Explicit shared ownership types (`Rc`, `Arc`) in stdlib
- Borrowing is the default way to use data without copying

### P3: Interfaces Are Just Structs

No special "trait object" runtime. An interface is literally a struct of function pointers + an erased self pointer.

- Static dispatch via generics
- Dynamic dispatch via passing interface struct values

### P4: Composition Only

- No inheritance
- Struct embedding is just a field + optional forwarding sugar

### P5: Target Everything

- Baseline: LLVM IR for CPU
- GPU: LLVM backends (NVPTX/AMDGPU) and/or SPIR-V

## Syntax

Indentation-based blocks, no semicolons, no braces. Python-style minimalism.

### Hello World

```ritz
fn main() -> i32
  print("Hello, Ritz\n")
  0
```

### Bindings

```ritz
let x = 42        # immutable
var y = 0         # mutable
```

### Structs

```ritz
struct Vec3
  x: f32
  y: f32
  z: f32
```

### Enums (Sum Types)

```ritz
enum Option<T>
  Some(T)
  None
```

### Functions

```ritz
fn add(a: i32, b: i32) = a + b

fn id<T>(x: T) -> T = x
```

### Methods

```ritz
fn Vec3.length(self: &Vec3) -> f32
  sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

fn Vec3.scale(self: &mut Vec3, factor: f32)
  self.x *= factor
  self.y *= factor
  self.z *= factor
```

## Ownership & Borrowing

### Reference Kinds

| Syntax | Meaning |
|--------|---------|
| `T` | Owned value (move semantics) |
| `&T` | Immutable borrow (const reference) |
| `&mut T` | Mutable borrow (exclusive reference) |
| `*const T` | Raw pointer, read-only (unsafe) |
| `*mut T` | Raw pointer, mutable (unsafe) |

### Rules

- Assigning an owned value moves it (unless type is `Copy`)
- Lifetimes are inferred via region analysis
- No explicit lifetime annotations in common cases
- Restrict expressible patterns to enable full inference

### Copy Types

```ritz
copy struct Handle
  raw: u64
```

## Error Handling

`Result[T, E]` + `?` operator is the primary story:

```ritz
fn read_file(path: &Str) -> Result[Bytes, IoErr]
  let f = File.open(path)?
  let b = f.read_all()?
  Ok(b)
```

## Interfaces

Interfaces expand to structs of function pointers:

```ritz
iface Writer
  fn write(self: &mut Self, data: &Bytes) -> Result[usize, IoErr]
  fn flush(self: &mut Self) -> Result[(), IoErr]
```

### Static Dispatch (Generics)

```ritz
fn log[T: Writer](w: &mut T, msg: &Str) -> Result[(), IoErr]
  w.write(msg.bytes())?
  w.flush()?
  Ok(())
```

### Dynamic Dispatch

```ritz
fn log(w: Writer, msg: &Str) -> Result[(), IoErr]
  w.write(msg.bytes())?
  w.flush()?
  Ok(())
```

## Unsafe Code

For kernel/systems work:

```ritz
fn write_vga(pos: i32, c: u8)
  unsafe
    let base = 0xB8000 as *mut u16
    *base.offset(pos) = (0x0F << 8) | (c as u16)
```

## External Functions

For FFI and syscalls:

```ritz
extern fn write(fd: i32, buf: *const u8, len: usize) -> isize
extern fn mmap(addr: *mut u8, len: usize, prot: i32, flags: i32, fd: i32, offset: i64) -> *mut u8
```

## Modules and Imports

```ritz
import ritzlib.fs
import ritzlib.io.File

fn main() -> Result[(), IoErr]
  let content = fs.read("hello.txt")?
  print(content)
  Ok(())
```

## Built-in Types

### Integers
- Signed: `i8`, `i16`, `i32`, `i64`
- Unsigned: `u8`, `u16`, `u32`, `u64`
- Pointer-sized: `isize`, `usize`

### Floats
- `f32`, `f64`

### Other
- `bool`
- `Str` (string slice)
- `StrBuf` (owned string)
- `Bytes` (byte slice)

## Testing

Built into the language:

```ritz
fn parse_int(s: &Str) -> Result[i32, ParseErr]
  # ...

#[test]
fn test_parse_int_positive()
  assert parse_int("42") == Ok(42)

#[test]
fn test_parse_int_negative()
  assert parse_int("-7") == Ok(-7)

#[test]
#[should_panic]
fn test_parse_int_overflow()
  let _ = parse_int("99999999999").unwrap()
```

Run with:
```bash
ritz test                    # JIT, fast
ritz test test_parse         # filter by name
ritz test --release          # AOT, optimized
```
