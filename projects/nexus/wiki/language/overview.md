# Language Overview

Ritz is a compiled, statically typed systems programming language. It compiles to LLVM IR and produces native binaries with no C runtime dependency.

---

## Philosophy

Ritz is designed around three core ideas:

**1. No Concessions**

If something cannot be expressed cleanly in Ritz, the language is extended. There is no acceptable awkwardness, no C idioms disguised in Ritz syntax, no working around limitations.

**2. Python-like readability with systems-level control**

Code should read naturally. Indentation defines structure. Keywords are English words. But the runtime is bare metal — direct syscalls, manual memory, zero abstraction cost.

**3. Rust-like safety without Rust-like noise**

Ownership is checked at compile time. Borrows prevent data races. But call sites are clean — the semantics live in the function signature, not at every use site.

---

## At a Glance

```ritz
import ritzlib.gvec { Vec }
import ritzlib.hashmap { HashMap }

# Structs are plain data
struct Point
    x: f64
    y: f64

fn distance(a: Point, b: Point) -> f64
    let dx = b.x - a.x
    let dy = b.y - a.y
    sqrt(dx * dx + dy * dy)

# Enums with data
enum Shape
    Circle { center: Point, radius: f64 }
    Rectangle { top_left: Point, bottom_right: Point }

fn area(shape: Shape) -> f64
    match shape
        Circle { radius } => 3.14159 * radius * radius
        Rectangle { top_left, bottom_right } =>
            let w = bottom_right.x - top_left.x
            let h = bottom_right.y - top_left.y
            w * h

# Generic collections
fn find_max(items: Vec<i32>) -> Option<i32>
    if items.is_empty()
        return None
    var max = items[0]
    for item in items
        if item > max
            max = item
    Some(max)

# Error handling with ?
fn load_config(path: StrView) -> Result<HashMap<String, String>, Error>
    let fd = open(path)?
    defer close(fd)
    let content = read_all(fd)?
    parse_config(content)
```

---

## Ownership Model

Ritz uses ownership semantics to guarantee memory safety without garbage collection. The key insight is that ownership qualifiers live in the function signature, not at call sites:

| Syntax | Meaning | Typical Use |
|--------|---------|-------------|
| `x: T` | Const borrow — caller keeps ownership, no mutation | ~70% of parameters |
| `x:& T` | Mutable borrow — caller keeps ownership, mutation allowed | When function modifies `x` |
| `x:= T` | Move — caller gives up ownership | When function takes over `x` |

```ritz
fn read_data(source: DataSource) -> Vec<u8>        # Const borrow
fn update_counter(counter:& i32)                    # Mutable borrow
fn consume_connection(conn:= Connection)            # Move

# Call sites are always clean
let data = read_data(source)     # No &source noise
update_counter(counter)          # No &mut counter noise
consume_connection(conn)         # No move annotation
```

---

## Error Handling

Errors are values. Functions return `Result<T, E>` or `Option<T>`. The `?` operator propagates errors automatically.

```ritz
fn process_file(path: StrView) -> Result<Summary, Error>
    let fd = open(path)?          # Propagate error if open fails
    defer close(fd)                # Always runs when scope exits

    let content = read_all(fd)?   # Propagate read error
    let data = parse(content)?    # Propagate parse error
    Ok(compute_summary(data))
```

There are no exceptions in Ritz. Every error is visible in the type signature.

---

## Pattern Matching

```ritz
# Exhaustive matching on enums
match response.status
    200 => Ok(response.body)
    404 => Err(Error.not_found(response.url))
    500 => Err(Error.server_error("Internal server error"))
    s   => Err(Error.unexpected(s))

# Destructuring
match point
    Point { x: 0, y: 0 } => print("Origin\n")
    Point { x, y: 0 }    => print("On x-axis at {x}\n")
    Point { x, y }        => print("At ({x}, {y})\n")

# Option handling
match find_user(42)
    Some(user) => greet(user)
    None       => print("User not found\n")
```

---

## Structs and Enums

```ritz
# Plain data struct
struct User
    id: i32
    name: String
    email: String

# Enum with variants
enum LoginResult
    Success(User)
    InvalidPassword
    UserNotFound
    AccountLocked { until: Timestamp }

# Pattern match the enum
fn handle_login(result: LoginResult)
    match result
        Success(user) =>
            print("Welcome, {user.name}!\n")
        InvalidPassword =>
            print("Wrong password.\n")
        UserNotFound =>
            print("No account with that email.\n")
        AccountLocked { until } =>
            print("Account locked until {until}.\n")
```

---

## Generics

```ritz
struct Stack<T>
    items: Vec<T>

impl Stack<T>
    fn new() -> Stack<T>
        Stack { items: Vec.new() }

    fn push(self:& Stack<T>, item:= T)
        self.items.push(item)

    fn pop(self:& Stack<T>) -> Option<T>
        self.items.pop()

    fn is_empty(self: Stack<T>) -> bool
        self.items.is_empty()
```

---

## Traits

```ritz
trait Displayable
    fn display(self) -> String

trait Comparable
    fn compare(self, other: Self) -> i32    # -1, 0, 1

struct Temperature
    celsius: f64

impl Displayable for Temperature
    fn display(self) -> String
        String.from("{self.celsius}°C")

impl Comparable for Temperature
    fn compare(self, other: Temperature) -> i32
        if self.celsius < other.celsius
            -1
        else if self.celsius > other.celsius
            1
        else
            0
```

---

## Async/Await

Ritz supports async/await with io_uring for Linux:

```ritz
import ritzlib.async_net { TcpListener, TcpStream }

async fn handle_client(stream:= TcpStream)
    let request = stream.read_line().await?
    let response = process(request)
    stream.write(response).await?

async fn main() -> Result<(), Error>
    let listener = TcpListener.bind(":8080").await?
    loop
        let stream = listener.accept().await?
        spawn handle_client(stream)
```

---

## Memory Management

Ritz allocates memory using `mmap` (no `malloc`, no libc). The standard library provides:

- `Vec<T>` — dynamic heap-allocated array
- `String` — heap-allocated string
- `HashMap<K, V>` — hash table
- `alloc`/`free` primitives for low-level control

When a value goes out of scope, its destructor runs automatically (if defined). There is no garbage collector.

---

## No libc

Ritz programs do not depend on libc. System calls are made directly:

```ritz
import ritzlib.sys { SYS_write }

fn print(msg: StrView)
    syscall(SYS_write, 1, msg.as_ptr(), msg.len())
```

This means Ritz programs are self-contained. No glibc version dependency. No dynamic linker. Just the kernel and your code.

---

## Continue Learning

- [Syntax Reference](syntax.md) — Complete syntax documentation
- [Ownership and Borrowing](ownership.md) — Deep dive on the memory model
- [Type System](types.md) — All types, generics, and traits
- [Standard Library](stdlib.md) — ritzlib module reference
- [Getting Started](../getting-started.md) — Install and build your first program
