# Type System

Ritz's type system: primitives, compounds, generics, and traits.

---

## Primitive Types

### Integers

| Type | Size | Range |
|------|------|-------|
| `i8` | 1 byte | -128 to 127 |
| `i16` | 2 bytes | -32,768 to 32,767 |
| `i32` | 4 bytes | -2,147,483,648 to 2,147,483,647 |
| `i64` | 8 bytes | -9.2×10^18 to 9.2×10^18 |
| `u8` | 1 byte | 0 to 255 |
| `u16` | 2 bytes | 0 to 65,535 |
| `u32` | 4 bytes | 0 to 4,294,967,295 |
| `u64` | 8 bytes | 0 to 18.4×10^18 |
| `usize` | pointer-sized | 0 to 2^64-1 on 64-bit |
| `isize` | pointer-sized | -2^63 to 2^63-1 on 64-bit |

```ritz
let a: i32 = -42
let b: u8 = 255
let c: usize = 4096
```

### Floats

| Type | Size | Precision |
|------|------|-----------|
| `f32` | 4 bytes | ~7 decimal digits |
| `f64` | 8 bytes | ~15 decimal digits |

```ritz
let pi: f64 = 3.14159265358979
let e: f32 = 2.71828
```

### Boolean

```ritz
let t: bool = true
let f: bool = false
```

### Numeric Literals

```ritz
let decimal = 1_000_000      # Underscores for readability
let hex = 0xFF_00_FF
let binary = 0b1010_0101
let octal = 0o777
let float = 1.5e-3           # Scientific notation
```

---

## String Types

### StrView (default)

`StrView` is a non-owning view into a string — a pointer and length. All string literals produce `StrView`.

```ritz
let s: StrView = "hello"     # No allocation
let len = s.len()            # 5
let sub = s[1..4]            # "ell" — zero copy
```

### String (owned)

`String` is a heap-allocated, owned string.

```ritz
let s = String.from("hello")
var builder = String.new()
builder.push_str("hello ")
builder.push_str("world")
# builder == "hello world"
```

### Conversion

```ritz
let view: StrView = "hello"
let owned: String = String.from(view)    # StrView → String (allocates)
let view2: StrView = owned.as_view()     # String → StrView (zero-copy)
```

Never use `c"string"` except for C FFI.

---

## Compound Types

### Arrays (fixed size)

```ritz
let arr: [4]i32 = [1, 2, 3, 4]
let zeros: [8]u8 = [0; 8]     # [0, 0, 0, 0, 0, 0, 0, 0]

let len = arr.len()            # 4 (compile-time constant)
let first = arr[0]             # 1
```

### Tuples

```ritz
let pair: (i32, bool) = (42, true)
let triple = (1, "hello", 3.14)

let (x, y) = pair              # Destructure
let first = pair.0             # Access by index
let second = pair.1
```

### Slices

A slice is a view into an array or Vec:

```ritz
let arr = [1, 2, 3, 4, 5]
let slice: @[i32] = @arr[1..4]    # [2, 3, 4]
let len = slice.len()              # 3
```

---

## Standard Collections

### Vec<T>

Dynamic array. Heap-allocated, owned.

```ritz
import ritzlib.gvec { Vec }

var v: Vec<i32> = Vec.new()
v.push(1)
v.push(2)
v.push(3)

let len = v.len()      # 3
let first = v[0]       # 1
v.pop()                # Remove last — returns Option<i32>

let slice: @[i32] = @v[1..3]    # Slice view
```

### HashMap<K, V>

Hash table. Heap-allocated, owned.

```ritz
import ritzlib.hashmap { HashMap }

var map: HashMap<String, i32> = HashMap.new()
map.insert(String.from("one"), 1)
map.insert(String.from("two"), 2)

let val: Option<i32> = map.get("one")    # Some(1)
let has = map.contains_key("three")      # false

map.remove("one")
let len = map.len()    # 1
```

---

## Option<T>

Represents a value that may or may not be present. Replaces null pointers.

```ritz
enum Option<T>
    Some(T)
    None

# Pattern matching
match find_user(42)
    Some(user) => greet(user)
    None       => print("Not found\n")

# Chaining
let len = find_user(42)
    .map(|user| user.name.len())
    .unwrap_or(0)

# Unwrap (panics on None)
let user = find_user(42).unwrap()

# Unwrap with default
let user = find_user(42).unwrap_or(default_user)

# Check
if opt.is_some()
    use(opt.unwrap())
```

---

## Result<T, E>

Represents a computation that may succeed or fail.

```ritz
enum Result<T, E>
    Ok(T)
    Err(E)

# Pattern matching
match parse_int("42")
    Ok(n)  => print("Parsed: {n}\n")
    Err(e) => print("Error: {e}\n")

# ? operator for propagation
fn process(input: StrView) -> Result<i32, Error>
    let n = parse_int(input)?     # Returns Err if parse fails
    Ok(n * 2)

# Chaining
let result = parse_int("42")
    .map(|n| n * 2)
    .map_err(|e| Error.custom(e))

# Unwrap
let n = parse_int("42").unwrap()    # Panics on Err
let n = parse_int("42").unwrap_or(0)
```

---

## Generics

```ritz
# Generic function
fn first<T>(vec: Vec<T>) -> Option<@T>
    if vec.is_empty()
        None
    else
        Some(@vec[0])

# Generic struct
struct Pair<A, B>
    first: A
    second: B

# Generic impl
impl Pair<A, B>
    fn swap(self) -> Pair<B, A>
        Pair { first: self.second, second: self.first }

# Generic with constraints
fn sum<T: Add>(items: Vec<T>) -> T
    var total = T.zero()
    for item in items
        total = total + item
    total
```

---

## Traits

Traits define shared behavior across types.

```ritz
trait Display
    fn display(self) -> String

trait Parse
    fn parse(s: StrView) -> Result<Self, ParseError>

trait Iterator<T>
    fn next(self:& Iterator<T>) -> Option<T>
    fn has_next(self) -> bool
```

### Implementing Traits

```ritz
struct Temperature
    celsius: f64

impl Display for Temperature
    fn display(self) -> String
        String.from("{self.celsius}°C")

impl Parse for Temperature
    fn parse(s: StrView) -> Result<Temperature, ParseError>
        let n = s.strip_suffix("°C")?.parse::<f64>()?
        Ok(Temperature { celsius: n })
```

### Trait Bounds

```ritz
# Static dispatch (monomorphized)
fn print_all(items: Vec<impl Display>)
    for item in items
        print("{item.display()}\n")

# Multiple bounds
fn process<T: Display + Clone>(item: T) -> T
    print("{item.display()}\n")
    item.clone()
```

---

## Pointers (Low-Level)

Raw pointers are available for FFI and kernel code. Use them only when necessary.

```ritz
let x: i32 = 42
let ptr: *i32 = @x as *i32    # Raw pointer

# Dereference (unsafe)
let val = *ptr

# Pointer arithmetic (kernel only)
let next = ptr.add(1)
```

Reference types (`@T`, `@&T`) are the safe alternative to raw pointers for normal code.

---

## Type Inference

Ritz infers types in most cases:

```ritz
let x = 42              # i32 inferred
let y = 3.14            # f64 inferred
let v = Vec.new()       # Vec<_> — element type inferred from usage
let map = HashMap.new() # HashMap<_, _> — types inferred from usage

# Sometimes you need to be explicit
let empty: Vec<String> = Vec.new()    # Without usage to infer from
let n: u64 = 0                        # Explicit when default (i32) is wrong
```

---

## Type Casting

Explicit casts are required for type conversions that might truncate:

```ritz
let x: i64 = 1234567890
let y: i32 = x as i32       # Truncate — might lose data
let z: u8 = (x & 0xFF) as u8

let a: f64 = 3.14
let b: i32 = a as i32       # Truncate fractional part (= 3)

# Widening is implicit
let small: i8 = 42
let big: i64 = small        # No cast needed — widens automatically
```

---

## See Also

- [Language Overview](overview.md)
- [Syntax Reference](syntax.md)
- [Ownership and Borrowing](ownership.md)
- [Standard Library](stdlib.md)
