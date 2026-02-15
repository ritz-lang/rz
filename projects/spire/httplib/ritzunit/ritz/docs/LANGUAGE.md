# The Ritz Programming Language

A systems programming language that compiles to native code via LLVM. No runtime, no garbage collector, no libc - just your code and syscalls.

---

## Table of Contents

1. [Hello World](#1-hello-world)
2. [Basic Types](#2-basic-types)
3. [Variables](#3-variables)
4. [Functions](#4-functions)
5. [Control Flow](#5-control-flow)
6. [Pointers](#6-pointers)
7. [Arrays](#7-arrays)
8. [Structs](#8-structs)
9. [Type Casting](#9-type-casting)
10. [Syscalls](#10-syscalls)
11. [Memory Management](#11-memory-management)
12. [Testing](#12-testing)
13. [Modules and Visibility](#13-modules-and-visibility)
14. [Complete Example](#14-complete-example)

---

## 1. Hello World

```ritz
fn main() -> i32
    print("Hello, World!\n")
    return 0
```

**Key points:**
- Indentation-based syntax (like Python)
- `fn` declares a function
- `main` is the entry point, returns `i32` (exit code)
- `print` is a built-in for string output

**Compile and run:**
```bash
python3 ritz0/ritz0.py hello.ritz -o hello.ll
llc -filetype=obj hello.ll -o hello.o
ld hello.o -o hello
./hello
```

---

## 2. Basic Types

### Integer Types

| Type | Size | Range |
|------|------|-------|
| `i8` | 8-bit signed | -128 to 127 |
| `i16` | 16-bit signed | -32,768 to 32,767 |
| `i32` | 32-bit signed | -2^31 to 2^31-1 |
| `i64` | 64-bit signed | -2^63 to 2^63-1 |
| `u8` | 8-bit unsigned | 0 to 255 |
| `u16` | 16-bit unsigned | 0 to 65,535 |
| `u32` | 32-bit unsigned | 0 to 2^32-1 |
| `u64` | 64-bit unsigned | 0 to 2^64-1 |

**Signed vs Unsigned Semantics:**

The signedness of a type affects:
- **Comparisons** (`<`, `<=`, `>`, `>=`): Unsigned types use unsigned comparison
- **Division/Modulo** (`/`, `%`): Unsigned types use unsigned division
- **Extension**: When widening to a larger type, unsigned uses zero-extend, signed uses sign-extend

```ritz
let u: u8 = 200 as u8    # Interpreted as 200
let s: i8 = 200 as i8    # Interpreted as -56 (wraps around)

# Unsigned comparison: 200 > 100 is true
let a: u8 = 200 as u8
let b: u8 = 100 as u8
if a > b       # true (unsigned)

# Signed comparison: -56 < 100 is true
let c: i8 = 200 as i8   # -56
let d: i8 = 100 as i8
if c < d       # true (signed, -56 < 100)
```

### Boolean Type

```ritz
let flag: bool = true
let done: bool = false
```

### Pointer Types

```ritz
let ptr: *i32      # Pointer to i32
let buf: *u8       # Pointer to u8 (byte pointer)
let argv: **u8     # Pointer to pointer (for argv)
```

---

## 3. Variables

### Immutable (let)

```ritz
let x: i32 = 42        # Explicit type
let y = 100            # Type inferred as i32
```

### Mutable (var)

```ritz
var count: i32 = 0
count = count + 1      # OK: count is mutable

let fixed: i32 = 10
fixed = 20             # ERROR: fixed is immutable
```

### Null Pointers

```ritz
var ptr: *u8 = 0 as *u8    # Null pointer (cast 0 to pointer type)
```

---

## 4. Functions

### Basic Function

```ritz
fn add(a: i32, b: i32) -> i32
    return a + b
```

### No Return Value

```ritz
fn greet(name: *u8)
    print("Hello, ")
    # No return needed
```

### Multiple Parameters

```ritz
fn clamp(value: i32, min: i32, max: i32) -> i32
    if value < min
        return min
    if value > max
        return max
    return value
```

### External Functions (syscalls)

```ritz
extern fn syscall3(n: i64, a1: i64, a2: i64, a3: i64) -> i64
```

---

## 5. Control Flow

### If/Else

```ritz
if x > 0
    print("positive\n")
else if x < 0
    print("negative\n")
else
    print("zero\n")
```

### While Loop

```ritz
var i: i32 = 0
while i < 10
    print_int(i)
    i = i + 1
```

### Break and Continue

```ritz
var i: i32 = 0
while true
    if i >= 10
        break
    if i % 2 == 0
        i = i + 1
        continue
    print_int(i)
    i = i + 1
```

### Comparison Operators

| Operator | Meaning |
|----------|---------|
| `==` | Equal |
| `!=` | Not equal |
| `<` | Less than |
| `<=` | Less or equal |
| `>` | Greater than |
| `>=` | Greater or equal |

### Logical Operators

| Operator | Meaning |
|----------|---------|
| `&&` | Logical AND |
| `\|\|` | Logical OR |
| `!` | Logical NOT |

---

## 6. Pointers

### Address-of (&)

```ritz
var x: i32 = 42
let ptr: *i32 = &x     # Get address of x
```

### Dereference (*)

```ritz
let value: i32 = *ptr   # Read value at pointer
*ptr = 100              # Write value at pointer
```

### Pointer Arithmetic

```ritz
let buf: *u8 = get_buffer()
let third_byte: u8 = *(buf + 2)   # Access third byte
```

### Array Element Access

```ritz
var arr: [10]i32
arr[0] = 1
arr[5] = arr[0] + 10
```

---

## 7. Arrays

### Stack-Allocated Arrays

```ritz
var buffer: [1024]u8       # 1KB buffer on stack
var numbers: [10]i32       # 10 integers on stack
```

### Accessing Elements

```ritz
buffer[0] = 65             # Set first byte to 'A'
let x: i32 = numbers[5]    # Read sixth element
```

### Getting Array Address

```ritz
var buf: [100]u8
let ptr: *u8 = &buf[0]     # Pointer to first element
```

### Passing Arrays to Functions

```ritz
fn sum_array(arr: *i32, len: i32) -> i32
    var total: i32 = 0
    var i: i32 = 0
    while i < len
        total = total + *(arr + i)
        i = i + 1
    return total

fn main() -> i32
    var nums: [5]i32
    nums[0] = 1
    nums[1] = 2
    nums[2] = 3
    nums[3] = 4
    nums[4] = 5
    let result: i32 = sum_array(&nums[0], 5)
    return result  # Returns 15
```

---

## 8. Structs

### Definition

```ritz
struct Point
    x: i32
    y: i32

struct Person
    name: *u8
    age: i32
```

### Stack Allocation

```ritz
var p: Point
p.x = 10
p.y = 20
```

### Field Access

```ritz
let distance: i32 = p.x * p.x + p.y * p.y
```

### Pointers to Structs

```ritz
fn move_point(p: *Point, dx: i32, dy: i32)
    p.x = p.x + dx
    p.y = p.y + dy

fn main() -> i32
    var pt: Point
    pt.x = 0
    pt.y = 0
    move_point(&pt, 5, 10)
    return pt.x  # Returns 5
```

### Nested Structs

```ritz
struct Rectangle
    top_left: Point
    width: i32
    height: i32
```

---

## 9. Type Casting

### Numeric Casts

```ritz
let small: i8 = 42
let big: i64 = small as i64    # Widen

let large: i64 = 1000000
let truncated: i32 = large as i32  # Narrow (may lose data)
```

### Pointer Casts

```ritz
let bytes: *u8 = get_data()
let ints: *i32 = bytes as *i32   # Reinterpret as i32 pointer
```

### Integer to Pointer

```ritz
let null_ptr: *u8 = 0 as *u8    # Null pointer
let addr: *u8 = 0x1000 as *u8   # Specific address (kernel code)
```

### Pointer to Integer

```ritz
let ptr: *u8 = &buffer[0]
let addr: i64 = ptr as i64     # Get address as integer
```

---

## 10. Syscalls

Ritz uses inline assembly for syscalls. No libc required.

### Syscall Wrappers

```ritz
extern fn syscall1(n: i64, a1: i64) -> i64
extern fn syscall2(n: i64, a1: i64, a2: i64) -> i64
extern fn syscall3(n: i64, a1: i64, a2: i64, a3: i64) -> i64
extern fn syscall6(n: i64, a1: i64, a2: i64, a3: i64, a4: i64, a5: i64, a6: i64) -> i64
```

### Common Syscalls

```ritz
# Read from file descriptor
fn read(fd: i32, buf: *u8, count: i64) -> i64
    return syscall3(0, fd as i64, buf as i64, count)

# Write to file descriptor
fn write(fd: i32, buf: *u8, count: i64) -> i64
    return syscall3(1, fd as i64, buf as i64, count)

# Open file
fn open(path: *u8, flags: i32) -> i32
    return syscall2(2, path as i64, flags as i64) as i32

# Close file descriptor
fn close(fd: i32) -> i32
    return syscall1(3, fd as i64) as i32

# Memory map (for heap allocation)
fn mmap(addr: i64, length: i64, prot: i32, flags: i32, fd: i32, offset: i64) -> *u8
    return syscall6(9, addr, length, prot as i64, flags as i64, fd as i64, offset) as *u8

# Memory unmap
fn munmap(addr: *u8, length: i64) -> i32
    return syscall2(11, addr as i64, length) as i32
```

### File Descriptors

| FD | Name | Purpose |
|----|------|---------|
| 0 | stdin | Standard input |
| 1 | stdout | Standard output |
| 2 | stderr | Standard error |

---

## 11. Memory Management

### Stack Allocation (Preferred)

```ritz
fn process_data() -> i32
    var buffer: [4096]u8   # Stack allocated, automatic cleanup
    # Use buffer...
    return 0               # Buffer automatically freed
```

### Heap Allocation (When Needed)

```ritz
# Allocate with mmap
fn heap_alloc(size: i64) -> *u8
    let prot: i32 = 3      # PROT_READ | PROT_WRITE
    let flags: i32 = 34    # MAP_PRIVATE | MAP_ANONYMOUS
    return mmap(0, size, prot, flags, -1, 0)

# Free with munmap
fn heap_free(ptr: *u8, size: i64)
    munmap(ptr, size)

# Usage
fn main() -> i32
    let buf: *u8 = heap_alloc(65536)
    if buf == 0 as *u8
        return 1  # Allocation failed

    # Use buf...

    heap_free(buf, 65536)
    return 0
```

---

## 12. Testing

### Test Functions

```ritz
@test
fn test_add()
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0

@test
fn test_array_sum()
    var arr: [3]i32
    arr[0] = 1
    arr[1] = 2
    arr[2] = 3
    assert sum_array(&arr[0], 3) == 6
```

### Running Tests

```bash
python3 ritz0/test_runner.py tests/test_math.ritz
```

### Test Attributes

| Attribute | Meaning |
|-----------|---------|
| `@test` | Mark function as a test |
| `@ignore` | Skip this test |

---

## 13. Modules and Visibility

Ritz supports a module system for organizing code across files and controlling what's exported.

### Imports

Import items from other modules:

```ritz
# Import all pub items into current namespace
import ritzlib.sys

# Import with namespace alias - access via alias::item
import ritzlib.sys as sys
sys::write(fd, buf, len)

# Import specific items only
import ritzlib.sys { write, read }

# Import specific items with alias
import ritzlib.sys { write, read } as io
io::write(fd, buf, len)
```

### Visibility with `pub`

By default, items are private to their module. Use `pub` to export them:

```ritz
# Exported items - visible to importers
pub fn my_function() -> i32
    42

pub struct Point
    x: i32
    y: i32

pub const MAX_SIZE: i64 = 1024

pub enum Color
    Red
    Green
    Blue

pub type IntPtr = *i32

pub trait Printable
    fn print(self: *Self) -> i32

# Private items - only visible in this module
fn internal_helper() -> i32
    0

struct InternalState
    data: *u8
```

### Re-exports

Use `pub import` to re-export items from another module:

```ritz
# Re-export everything from sys
pub import ritzlib.sys

# Re-export specific items
pub import ritzlib.sys { write, read }
```

### Qualified Access

When using import aliases, access items with `::`:

```ritz
import ritzlib.sys as sys

fn main() -> i32
    let result: i32 = sys::write(1, buf, len)
    let stat: sys::Stat = ...   # Types also use ::
    0
```

---

## 14. Complete Example

A complete `cat` implementation:

```ritz
# cat - concatenate files to stdout
#
# Usage: cat [FILE...]
#   Copy FILE(s) to standard output.
#   With no FILE, read from standard input.

extern fn syscall1(n: i64, a1: i64) -> i64
extern fn syscall2(n: i64, a1: i64, a2: i64) -> i64
extern fn syscall3(n: i64, a1: i64, a2: i64, a3: i64) -> i64

fn read(fd: i32, buf: *u8, count: i64) -> i64
    return syscall3(0, fd as i64, buf as i64, count)

fn write(fd: i32, buf: *u8, count: i64) -> i64
    return syscall3(1, fd as i64, buf as i64, count)

fn open(path: *u8, flags: i32) -> i32
    return syscall2(2, path as i64, flags as i64) as i32

fn close(fd: i32) -> i32
    return syscall1(3, fd as i64) as i32

fn cat_fd(fd: i32) -> i32
    var buf: [4096]u8
    while true
        let n: i64 = read(fd, &buf[0], 4096)
        if n < 0
            return 1
        if n == 0
            break
        write(1, &buf[0], n)
    return 0

fn main(argc: i32, argv: **u8) -> i32
    if argc == 1
        # No args: read from stdin
        return cat_fd(0)

    var result: i32 = 0
    var i: i32 = 1
    while i < argc
        let path: *u8 = *(argv + i)
        let fd: i32 = open(path, 0)
        if fd < 0
            write(2, "cat: cannot open file\n" as *u8, 22)
            result = 1
        else
            let r: i32 = cat_fd(fd)
            if r != 0
                result = 1
            close(fd)
        i = i + 1

    return result
```

---

## Appendix A: Arithmetic Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `+` | Addition | `a + b` |
| `-` | Subtraction | `a - b` |
| `*` | Multiplication | `a * b` |
| `/` | Division | `a / b` |
| `%` | Modulo | `a % b` |

Note: Bit shift operators (`<<`, `>>`) are planned but not yet implemented.

---

## Appendix B: String and Character Literals

### String Literals

String literals are null-terminated byte arrays (use double quotes):

```ritz
let msg: *u8 = "Hello\n"
```

### Character Literals

Character literals are single bytes (u8 values, use single quotes):

```ritz
let newline: u8 = '\n'        # 10
let letter_a: u8 = 'A'        # 65
let letter_z: u8 = 'Z'        # 90

# Can be used directly in comparisons
if c >= 'a' && c <= 'z'
    # lowercase letter

# Common use: function arguments expecting u8
args_flag(&parser, 'v', "verbose", "Enable verbose output")
```

### Escape Sequences

Both string and character literals support these escapes:

| Escape | Character | Value |
|--------|-----------|-------|
| `\n` | Newline | 10 |
| `\t` | Tab | 9 |
| `\r` | Carriage return | 13 |
| `\\` | Backslash | 92 |
| `\"` | Double quote | 34 |
| `\'` | Single quote | 39 |
| `\0` | Null byte | 0 |

### String Interpolation

Strings can embed expressions using `{...}` syntax:

```ritz
let x: i32 = 42
let name = "World"

# Variable interpolation
"Hello, {name}!\n"        # Prints: Hello, World!

# Integer values
"x = {x}\n"               # Prints: x = 42

# Multiple values
"x = {x}, y = {y}\n"      # Prints: x = 42, y = 17

# Expressions
"Sum: {x + y}\n"          # Prints: Sum: 59
```

**How it works:**
- The compiler transforms interpolated strings into a series of print calls
- `"x = {x}\n"` becomes: `print("x = "); print_i32(x); print("\n")`
- Type-aware formatting is used (integers use `print_i32`, strings use `print`)

**Supported types:**
- Integers (`i8`, `i16`, `i32`, `i64`, `u8`, `u16`, `u32`, `u64`)
- Strings (`*u8`)
- Boolean (`bool`)

**Note:** To print a literal `{`, use `{{`:
```ritz
"Set: {{value}}\n"        # Prints: Set: {value}
```

---

## Appendix C: File Structure

A typical Ritz file structure:

```ritz
# File header comment explaining purpose

# External declarations
extern fn syscall3(n: i64, a1: i64, a2: i64, a3: i64) -> i64

# Struct definitions
struct Options
    verbose: i32
    count: i32

# Helper functions
fn helper(x: i32) -> i32
    return x * 2

# Main entry point
fn main(argc: i32, argv: **u8) -> i32
    # Program logic
    return 0

# Test functions (only in test files)
@test
fn test_helper()
    assert helper(5) == 10
```

---

## What's Next?

### Implemented
- ✅ `for` loops: `for i in 0..10`
- ✅ Bit shift operators: `<<`, `>>`
- ✅ Module system with `pub` visibility and import aliases
- ✅ Generics: `Vec<T>`, `Option<T>`
- ✅ Pattern matching: `match`
- ✅ Error handling: `Result<T, E>`
- ✅ References: `&T`
- ✅ Closures: `|x| x + 1`
- ✅ Async/await

### Future
- Full self-hosting (ritz1 compiling itself)
- DWARF debug info in ritz1
- Package manager integration

---

*This documentation covers ritz0, the bootstrap compiler. See the examples in `examples/` for more usage patterns.*
