# Syntax Reference

Complete Ritz syntax reference.

---

## Files and Modules

A Ritz file is a module. The filename is the module name. File `parser.ritz` defines module `parser`.

```ritz
# parser.ritz

# Public exports
pub struct ParseResult
    ...

pub fn parse(source: StrView) -> ParseResult
    ...

# Private — not visible outside this module
fn internal_helper(token: Token) -> Node
    ...
```

---

## Imports

```ritz
import ritzlib.sys              # Import all pub items from sys.ritz
import ritzlib.sys { write }    # Import specific items
import ritzlib.sys as sys       # Alias (use sys.write)
import squeeze.gzip             # From ecosystem package
```

---

## Variables

```ritz
let x = 42              # Immutable, type inferred (i32)
let y: f64 = 3.14       # Immutable, explicit type
var count = 0           # Mutable, type inferred
var name: String        # Mutable, explicit type, uninitialized
```

Use `let` by default. Use `var` only when you need to reassign the variable.

---

## Functions

```ritz
# Basic function
fn add(a: i32, b: i32) -> i32
    a + b           # Last expression is return value

# Explicit return
fn max(a: i32, b: i32) -> i32
    if a > b
        return a
    b

# No return value
fn print_greeting(name: StrView)
    print("Hello, {name}!\n")

# With ownership modifiers
fn process(data: Vec<u8>) -> Summary      # Const borrow
fn increment(counter:& i32)               # Mutable borrow
fn consume(conn:= Connection) -> ()       # Move
```

### Return Value Syntax

The last expression in a function body is implicitly returned. No `return` keyword needed:

```ritz
fn double(x: i32) -> i32
    x * 2       # Returned implicitly

fn add(a: i32, b: i32) -> i32
    let sum = a + b
    sum         # Returned implicitly
```

Use explicit `return` for early exits:

```ritz
fn safe_divide(a: i32, b: i32) -> Option<i32>
    if b == 0
        return None     # Early return
    Some(a / b)
```

---

## Control Flow

### if / else

```ritz
if x > 0
    print("positive\n")
else if x < 0
    print("negative\n")
else
    print("zero\n")
```

`if` is an expression:

```ritz
let label = if x > 0 then "positive" else "non-positive"
```

### while

```ritz
var i = 0
while i < 10
    process(i)
    i = i + 1
```

### loop

```ritz
loop
    let input = read_line()
    if input == "quit"
        break
    process(input)
```

### for

```ritz
# Exclusive range (0, 1, 2, ..., 9)
for i in 0..10
    print("{i}\n")

# Inclusive range (0, 1, 2, ..., 10)
for i in 0..=10
    print("{i}\n")

# Iterate over a collection
for item in items
    process(item)

# Iterate with index
for (i, item) in items.enumerate()
    print("{i}: {item}\n")
```

### match

```ritz
match value
    0 => print("zero\n")
    1 => print("one\n")
    n if n < 0 => print("negative: {n}\n")
    n => print("other: {n}\n")

# Match on enum
match result
    Ok(value) => use(value)
    Err(e) => handle(e)

# Destructuring in match
match point
    Point { x: 0, y } => print("On y-axis at y={y}\n")
    Point { x, y }     => print("At ({x}, {y})\n")
```

---

## Types

### Primitive Types

| Type | Size | Range |
|------|------|-------|
| `bool` | 1 byte | `true` / `false` |
| `i8` | 1 byte | -128 to 127 |
| `i16` | 2 bytes | -32768 to 32767 |
| `i32` | 4 bytes | -2^31 to 2^31-1 |
| `i64` | 8 bytes | -2^63 to 2^63-1 |
| `u8` | 1 byte | 0 to 255 |
| `u16` | 2 bytes | 0 to 65535 |
| `u32` | 4 bytes | 0 to 2^32-1 |
| `u64` | 8 bytes | 0 to 2^64-1 |
| `f32` | 4 bytes | 32-bit float |
| `f64` | 8 bytes | 64-bit float |
| `usize` | 8 bytes | Pointer-sized unsigned |
| `isize` | 8 bytes | Pointer-sized signed |

### Compound Types

```ritz
# Tuple
let pair: (i32, bool) = (42, true)
let (x, y) = pair       # Destructure

# Array (fixed size)
let arr: [4]i32 = [1, 2, 3, 4]

# Slice (view into array)
let slice: @[i32] = @arr[1..3]    # [2, 3]
```

### String Types

```ritz
"hello"                  # StrView — zero-copy string slice (DEFAULT)
String.from("hello")     # String — heap-allocated, owned string
```

Use `StrView` for function parameters and string literals. Use `String` when you need ownership (storing in a struct, building dynamically).

Never use `c"hello"` except for FFI.

---

## Structs

```ritz
struct Point
    x: f64
    y: f64

# Create
let p = Point { x: 1.0, y: 2.0 }
let q = Point { x: p.x, ..p }    # Struct update syntax

# Access fields
print("{p.x}, {p.y}\n")

# Methods
impl Point
    fn length(self) -> f64
        sqrt(self.x * self.x + self.y * self.y)

    fn scale(self:& Point, factor: f64)
        self.x = self.x * factor
        self.y = self.y * factor
```

---

## Enums

```ritz
enum Color
    Red
    Green
    Blue
    Custom { r: u8, g: u8, b: u8 }

enum Option<T>
    Some(T)
    None

enum Result<T, E>
    Ok(T)
    Err(E)

# Match all variants
match color
    Red => print("red\n")
    Green => print("green\n")
    Blue => print("blue\n")
    Custom { r, g, b } => print("rgb({r}, {g}, {b})\n")
```

---

## Traits

```ritz
trait Animal
    fn speak(self) -> String
    fn name(self) -> String

    # Default implementation
    fn describe(self) -> String
        "{self.name()} says: {self.speak()}"

struct Dog
    name: String

impl Animal for Dog
    fn speak(self) -> String
        String.from("Woof!")

    fn name(self) -> String
        self.name.clone()

# Trait as parameter (static dispatch)
fn introduce(animal: impl Animal)
    print("{animal.describe()}\n")

# Trait object (dynamic dispatch)
fn introduce_dynamic(animal:& dyn Animal)
    print("{animal.describe()}\n")
```

---

## Closures

```ritz
let double = |x: i32| x * 2
let add = |a: i32, b: i32| a + b

let nums = Vec.from([1, 2, 3, 4, 5])
let doubled: Vec<i32> = nums.map(|x| x * 2).collect()
let evens: Vec<i32> = nums.filter(|x| x % 2 == 0).collect()
let total: i32 = nums.fold(0, |acc, x| acc + x)
```

---

## Error Handling

```ritz
# Return errors as Result
fn parse_int(s: StrView) -> Result<i32, ParseError>
    ...

# ? propagates errors (early return)
fn compute(input: StrView) -> Result<i32, Error>
    let value = parse_int(input)?    # Returns Err if parse fails
    Ok(value * 2)

# defer runs on scope exit
fn process_file(path: StrView) -> Result<(), Error>
    let fd = open(path)?
    defer close(fd)     # Guaranteed to run even on Err path
    do_work(fd)?
    Ok(())
```

---

## Attributes

```ritz
[[test]]
fn test_something() -> i32
    assert 1 + 1 == 2
    0

[[route("GET", "/users/:id")]]
fn get_user(req: Request) -> Response
    ...
```

---

## Operators

### Arithmetic

```ritz
a + b    # Add
a - b    # Subtract
a * b    # Multiply
a / b    # Divide
a % b    # Modulo
```

### Comparison

```ritz
a == b   # Equal
a != b   # Not equal
a < b    # Less than
a > b    # Greater than
a <= b   # Less than or equal
a >= b   # Greater than or equal
```

### Logical

```ritz
a and b  # Logical AND (not &&)
a or b   # Logical OR (not ||)
not a    # Logical NOT (not !)
```

### Bitwise

```ritz
a and b  # Bitwise AND (context-dependent)
a or b   # Bitwise OR
a xor b  # Bitwise XOR
a << n   # Left shift
a >> n   # Right shift (arithmetic for signed, logical for unsigned)
```

---

## String Interpolation

```ritz
let name = "Alice"
let age = 30
print("Name: {name}, Age: {age}\n")    # Interpolated
print("Literal {name}")                 # {name} is evaluated
```

---

## Comments

```ritz
# This is a line comment
# There are no block comments in Ritz
```

---

## Indentation Rules

Ritz uses significant indentation (like Python). The rules:

- 4 spaces per indent level
- No tabs
- A block is everything at the same indent level under a header
- `fn`, `if`, `else`, `while`, `for`, `loop`, `match`, `struct`, `enum`, `impl`, `trait` all introduce blocks

---

## See Also

- [Language Overview](overview.md)
- [Ownership and Borrowing](ownership.md)
- [Type System](types.md)
- [Standard Library](stdlib.md)
