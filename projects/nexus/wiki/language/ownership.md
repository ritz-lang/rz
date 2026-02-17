# Ownership and Borrowing

Ritz's memory safety model. No garbage collector. No use-after-free. No data races.

---

## Core Concept

Ritz tracks ownership of values at compile time. Every value has exactly one owner at any point in time. When the owner goes out of scope, the value is freed.

The key difference from Rust: ownership qualifiers live in the function signature, not at call sites. This keeps call sites clean.

---

## The Three Ownership Modes

| Syntax | Name | Semantics |
|--------|------|-----------|
| `param: T` | Const borrow | Caller retains ownership, function gets read-only access |
| `param:& T` | Mutable borrow | Caller retains ownership, function gets read-write access |
| `param:= T` | Move | Caller transfers ownership to function |

**Note: No space between `:` and the modifier.** Write `:&` not `: &`.

---

## Const Borrow (Default)

The default. Used for ~70% of function parameters. The caller keeps ownership and the value is not modified.

```ritz
fn describe(point: Point) -> String
    String.from("({point.x}, {point.y})")

fn total_length(items: Vec<String>) -> usize
    var total = 0
    for item in items
        total = total + item.len()
    total
```

After calling a const-borrow function, the caller still has the value:

```ritz
let p = Point { x: 1.0, y: 2.0 }
let desc = describe(p)      # p is still valid here
print("{p.x}\n")             # OK
```

---

## Mutable Borrow

Used when the function needs to modify the value. The caller still owns it.

```ritz
fn increment(counter:& i32)
    counter = counter + 1

fn push_many(vec:& Vec<i32>, items: Vec<i32>)
    for item in items
        vec.push(item)
```

After calling a mutable-borrow function, the caller has the (modified) value back:

```ritz
var counter = 0
increment(counter)      # counter is now 1
increment(counter)      # counter is now 2
print("{counter}\n")    # Prints: 2
```

**Borrow rules:**
- At most one mutable borrow at a time
- No const borrows while a mutable borrow is active

---

## Move

The caller transfers ownership to the function. The value cannot be used by the caller afterward.

```ritz
fn consume_connection(conn:= Connection)
    # conn is fully owned here
    conn.close()
    # conn is dropped when this function returns

fn store(cache:& HashMap<String, Vec<u8>>, key: String, value:= Vec<u8>)
    cache.insert(key, value)   # value is moved into the map
    # value cannot be used after this
```

Use move when:
- The function will store the value (in a struct, map, etc.)
- The function's job is to consume and free the value
- You want to transfer responsibility for cleanup

---

## Call Site Cleanliness

One of Ritz's design choices is that call sites require no annotations. The ownership contract is stated once, in the function signature.

```ritz
# Signatures state the contract:
fn process(data: Vec<u8>) -> Summary        # Const borrow
fn fill(buffer:& Vec<u8>, size: usize)      # Mutable borrow
fn send(packet:= Packet)                    # Move

# Call sites are always clean:
let summary = process(data)      # NOT process(&data)
fill(buffer, 1024)               # NOT fill(&mut buffer, 1024)
send(packet)                     # NOT send(move packet)
```

This reduces visual noise without sacrificing safety.

---

## References

References are explicit in Ritz using `@`:

```ritz
let p = Point { x: 1.0, y: 2.0 }
let ref_p: @Point = @p        # Immutable reference to p
let mut_ref: @&Point = @&p    # Mutable reference to p
```

Reference types:

| Type | Meaning |
|------|---------|
| `@T` | Immutable reference to T |
| `@&T` | Mutable reference to T |

---

## Lifetimes

Ritz tracks lifetimes to ensure references don't outlive the values they point to:

```ritz
# This would be a compile error — ref would outlive p
fn get_ref() -> @Point
    let p = Point { x: 1.0, y: 2.0 }
    @p      # ERROR: p is freed when function returns, ref dangles

# This is fine — ref lifetime bounded by caller
fn first_element(vec: Vec<i32>) -> Option<@i32>
    if vec.is_empty()
        None
    else
        Some(@vec[0])       # OK — ref lives as long as vec
```

---

## Ownership and Structs

When a struct is owned, all its fields are owned:

```ritz
struct Server
    host: String          # Owned
    connections: Vec<Connection>   # Owned — owns all connections

fn shutdown(server:= Server)
    # server is moved in, including all connections
    for conn in server.connections
        conn.close()
    # connections dropped
    # server dropped
```

---

## Copy Types

Some types are `Copy` — they are implicitly duplicated on assignment or function call:

- All integer types (`i8`, `i32`, `u64`, etc.)
- Floating point (`f32`, `f64`)
- `bool`
- Tuples of Copy types
- Fixed-size arrays of Copy types

```ritz
let x: i32 = 42
let y = x       # x is COPIED to y
print("{x}\n")  # x is still valid (copy)
```

Non-copy types (like `String`, `Vec<T>`, `Connection`) must be explicitly borrowed or moved.

---

## Practical Patterns

### Builder Pattern

```ritz
struct ServerConfig
    host: String
    port: u16
    max_connections: u32

struct ServerBuilder
    config: ServerConfig

impl ServerBuilder
    fn new() -> ServerBuilder
        ServerBuilder {
            config: ServerConfig {
                host: String.from("0.0.0.0"),
                port: 8080,
                max_connections: 100,
            }
        }

    fn host(self:= ServerBuilder, host: String) -> ServerBuilder
        ServerBuilder { config: ServerConfig { host, ..self.config } }

    fn port(self:= ServerBuilder, port: u16) -> ServerBuilder
        ServerBuilder { config: ServerConfig { port, ..self.config } }

    fn build(self:= ServerBuilder) -> ServerConfig
        self.config

# Usage — each step moves self
let config = ServerBuilder.new()
    .host(String.from("127.0.0.1"))
    .port(9000)
    .build()
```

### Returning Owned Data

```ritz
fn load_users(db: Database) -> Vec<User>
    # Return owned Vec
    db.query_all("users")

# Caller owns the returned vec
let users = load_users(db)
for user in users
    print("{user.name}\n")
```

### Avoiding Copies with References

```ritz
struct Config
    host: String
    port: u16
    options: HashMap<String, String>

# Return reference to field — no copy
fn get_host(config: Config) -> @String
    @config.host

fn main()
    let config = load_config()?
    let host = get_host(config)   # Reference, not copy
    print("Host: {host}\n")
```

---

## Common Mistakes

### Using After Move

```ritz
fn process(data:= Vec<u8>) -> Summary { ... }

let data = Vec.new()
let summary = process(data)    # data is moved
print("{data.len()}\n")        # ERROR: data was moved
```

Fix: Either borrow instead of move, or clone:

```ritz
# Option 1: Change to borrow
fn process(data: Vec<u8>) -> Summary { ... }

# Option 2: Clone before move
let data_copy = data.clone()
let summary = process(data)
print("{data_copy.len()}\n")   # OK — using the clone
```

### Mutable and Immutable Borrows

```ritz
var v = Vec.from([1, 2, 3])
let first = @v[0]       # Immutable borrow of v

v.push(4)               # ERROR: v is mutably borrowed via push
                        # while first still holds an immutable borrow
print("{first}\n")
```

Fix: Use the immutable borrow before mutating:

```ritz
var v = Vec.from([1, 2, 3])
let first_val = v[0]    # Copy the value, don't hold a reference
v.push(4)               # OK — no outstanding borrow
print("{first_val}\n")
```

---

## See Also

- [Language Overview](overview.md)
- [Syntax Reference](syntax.md)
- [Type System](types.md)
