# Ritz Style Guide

This document defines the canonical code style for Ritz source files.

## Indentation

**Standard: 4 spaces** (no tabs)

```ritz
fn example(x: i32) -> i32
    if x > 0
        let result: i32 = x * 2
        return result
    else
        return 0
```

## Line Length

- Maximum 100 characters per line
- Break long expressions at operators

## Naming Conventions

| Item | Convention | Example |
|------|------------|---------|
| Functions | snake_case | `hash_i64`, `vec_push` |
| Variables | snake_case | `token_count`, `current_indent` |
| Types/Structs | PascalCase | `HashMapI64`, `Parser`, `Token` |
| Enums | PascalCase | `Option`, `Result` |
| Enum Variants | PascalCase | `Some`, `None`, `Ok`, `Err` |
| Constants | SCREAMING_SNAKE | `TOK_EOF`, `MAX_TOKENS` |
| Type Parameters | Single uppercase | `T`, `K`, `V`, `E` |

## Spacing

- One space after commas: `fn foo(a: i32, b: i32)`
- One space around binary operators: `x + y`, `a == b`
- No space after unary operators: `-x`, `!flag`, `*ptr`
- No space inside parentheses: `foo(x)` not `foo( x )`
- No space inside brackets: `arr[i]` not `arr[ i ]`

## Blank Lines

- Two blank lines between top-level items (functions, structs, etc.)
- One blank line to separate logical sections within functions
- Maximum 2 consecutive blank lines

## Comments

```ritz
# Single-line comment

# Multi-line comments
# use multiple single-line
# comment markers

# Section headers with separators
# ============================================================================
# Section Name
# ============================================================================
```

## Imports

- Group imports by category
- Sort alphabetically within groups

```ritz
# Standard library imports
import ritzlib.io
import ritzlib.memory
import ritzlib.sys

# Local imports
import ast
import parser
import tokens
```

## Function Definitions

```ritz
fn function_name(param1: Type1, param2: Type2) -> ReturnType
    # Function body with 4-space indent
    let result: ReturnType = compute()
    return result
```

## Struct Definitions

```ritz
struct StructName
    field1: Type1
    field2: Type2
    field3: Type3
```

## Trait Implementations

Use mutable borrows (`&mut Self`) for trait method receivers, not raw pointers:

```ritz
impl<T> Drop for Vec<T>
    fn drop(self: &mut Vec<T>)
        if self.data != 0 as *T
            free(self.data as *u8)
        self.cap = 0
        self.len = 0

impl<T> Clone for Vec<T>
    fn clone(self: &Vec<T>) -> Vec<T>
        # shared borrow for read-only access
        ...
```

**Method Receiver Conventions:**

| Method Type | Receiver | Example |
|-------------|----------|---------|
| Read-only | `self: &Self` | `fn len(self: &Vec<T>) -> i64` |
| Mutating | `self: &mut Self` | `fn push(self: &mut Vec<T>, item: T)` |
| Consuming | `self: Self` | `fn into_iter(self: Vec<T>) -> Iter<T>` |

**Note:** ritzlib currently uses `*Self` (raw pointers) for historical reasons. Migration to `&mut Self` is tracked in the hardening phase.

## Error Handling

Prefer `Result<T, E>` and the `?` operator:

```ritz
fn read_file(path: *u8) -> Result<String, i32>
    let fd: i32 = open(path)?
    let content: String = read_all(fd)?
    close(fd)
    return Ok(content)
```

## Tools

- **ritzfmt**: Automatic code formatter (`examples/48_ritzfmt/`)
  - `ritzfmt -w file.ritz` - Format in place
  - `ritzfmt -c file.ritz` - Check formatting (exit 1 if not formatted)
  - Default indent: 4 spaces

---

## Implemented Language Features

This section documents syntax features that have been implemented. Use these patterns:

### Negative Integer Literals ✅ Implemented

Use negative literals directly:

```ritz
return -1
var sentinel: i64 = -1
let error_code: i32 = -12  # ENOMEM
```

Avoid the old pattern `0 - 1` which is less readable.

### Compound Assignment Operators ✅ Implemented

Use compound assignment for self-modifying operations:

```ritz
i += 1
count -= 1
offset += len
value *= 2
```

Operators: `+=`, `-=`, `*=`, `/=`

Avoid the old pattern `i = i + 1` which is redundant and harder to read.

### Character Literals ✅ Implemented

Character literals using single quotes (`'c'`) are supported.

```ritz
# Preferred - use character literals
if c == '"'
if c == '\\'
buf[0] = 'd'

# Check character ranges
if c >= 'a' && c <= 'z'
    # lowercase letter
```

Supported escapes: `'\n'`, `'\t'`, `'\r'`, `'\\'`, `'\''`, `'\"'`, `'\0'`

### For Loops ✅

Use `for..in` with range syntax for counting loops:

```ritz
# Exclusive range: 0..n means 0, 1, 2, ..., n-1
for i in 0..argc
    process(args[i])

# Inclusive range: 0..=n means 0, 1, 2, ..., n
for i in 1..=10
    sum += i

# Variable bounds
for i in start..end
    process(i)

# Nested loops
for i in 0..rows
    for j in 0..cols
        print_cell(grid[i][j])
```

Range variants:
- `0..n` - exclusive range (0 to n-1)
- `0..=n` - inclusive range (0 to n)

### Null Keyword ✅

Use `null` for null pointer literals instead of `0 as *T`:

```ritz
if ptr == null
sh_argv[3] = null
```

The `null` keyword represents a null pointer of any pointer type. Type is inferred from context.

### Loop Keyword ✅

Use `loop` for infinite loops instead of `while true`:

```ritz
loop
    # ...
    if done { break }
```

The `loop` keyword is syntactic sugar for `while true` and clearly signals infinite iteration.

### Match Expressions ✅ Implemented

Use `match` for multi-way branching:

```ritz
match id
    BUILTIN_PLUS => make_number(s, v1 + v2)
    BUILTIN_MINUS => make_number(s, v1 - v2)
    _ => s.nil_idx

match opt
    Some(x) => x
    None => 0
```

Avoid chained `if/else if` when matching against constants or enum variants.

### String Interpolation ✅ Implemented

Use interpolation for formatted output:

```ritz
import ritzlib.string

let name = "world"
let count = 42
println("Hello {name}, count is {count}")  # requires String type

# Expressions are supported
println("Result: {x + y}")
```

Avoid the old pattern of chained `print`/`print_int` calls.

### Auto-Dereference for Pointers ✅ Implemented

Field access on pointers automatically dereferences:

```ritz
fn get_value(p: *Point) -> i32
    p.x + p.y    # No (*p).x needed

fn update(self: *Counter)
    self.count += 1
```

The old `(*ptr).field` syntax still works but is unnecessary.

### Type Inference on `let` ✅ Implemented

Omit type annotations when the initializer provides sufficient type information:

```ritz
let result = apply(double, 5)   # inferred from function return type
let fd = sys_open(path, O_RDONLY, 0)
let msg = "hello"               # inferred as String
let flag = true                 # inferred as bool
```

Explicit types are still needed for:
- Uninitialized variables (`var x: i32`)
- Ambiguous numeric literals where precision matters
- Function parameters (always required)

### String Literals ✅ Implemented

Three literal forms for different use cases:

```ritz
"hello"      # String type (heap-allocated, owned)
c"hello"     # *u8 (null-terminated C string, no allocation)
s"hello"     # Span<u8> (ptr + len, no allocation)
```

**Implicit coercion**: `String` automatically coerces to `*u8` when passed to functions expecting C strings.

```ritz
import ritzlib.string

let msg = "hello"     # String
sys_write(1, msg, 5)  # msg coerced to *u8 automatically
```

### Async/Await ✅ Implemented

For asynchronous I/O operations:

```ritz
async fn read_data(fd: i32) -> i32
    let result = await do_read(fd)
    result

fn main() -> i32
    let exec = executor_new()
    block_on(&exec, read_data(fd))
```

The compiler transforms `async fn` into a state machine struct with a `poll` function.

---

*Last updated: 2026-02-11*
