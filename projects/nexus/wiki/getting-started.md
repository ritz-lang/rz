# Getting Started with Ritz

This guide walks you through installing Ritz, writing your first program, and exploring the ecosystem.

---

## Prerequisites

- **Linux x86-64** — Ritz targets Linux on x86-64. WSL2 on Windows works.
- **Python 3.10+** — Required for the bootstrap compiler (ritz0)
- **clang** — For compiling LLVM IR to native binaries
- **Git** — For cloning repositories

---

## Installation

### Clone the Ecosystem

Ritz uses a flat directory structure — all projects live as siblings:

```bash
mkdir -p ~/dev/ritz-lang
cd ~/dev/ritz-lang
git clone https://github.com/ritz-lang/ritz.git ritz
```

### Set RITZ_PATH

Add to your shell profile (`~/.bashrc` or `~/.zshrc`):

```bash
export RITZ_PATH=~/dev/ritz-lang
export PATH="$RITZ_PATH/ritz:$PATH"
```

Reload your shell:

```bash
source ~/.bashrc
```

### Verify Installation

```bash
ritz --version
```

---

## Hello, World

Create a file called `hello.ritz`:

```ritz
fn main()
    print("Hello, World!\n")
```

Compile and run it:

```bash
ritz build hello.ritz
./build/debug/hello
```

Output:

```
Hello, World!
```

---

## Your First Project

### Create a Project

Create a directory and a `ritz.toml` manifest:

```bash
mkdir myapp
cd myapp
```

Create `ritz.toml`:

```toml
[package]
name = "myapp"
version = "0.1.0"

sources = ["src"]

[[bin]]
name = "myapp"
entry = "main::main"
```

Create `src/main.ritz`:

```ritz
fn main()
    let name = "Ritz"
    print("Welcome to {name}!\n")
```

Build and run:

```bash
ritz build .
./build/debug/myapp
```

---

## Key Language Concepts

### Variables

```ritz
let x: i32 = 42        # Immutable (preferred)
var count: i32 = 0     # Mutable (only when needed)
```

### Functions

```ritz
fn add(a: i32, b: i32) -> i32
    a + b

fn greet(name: StrView)
    print("Hello, {name}!\n")
```

### Ownership

Ritz uses ownership modifiers on parameter declarations rather than call-site annotations:

```ritz
fn read_data(source: DataSource) -> Vec<u8>   # Const borrow (default)
fn update_counter(counter:& i32)               # Mutable borrow
fn consume_connection(conn:= Connection)       # Move ownership
```

Call sites are always clean — no `&x` or `&mut x` noise:

```ritz
let data = read_data(source)
update_counter(counter)
consume_connection(conn)
```

### Pattern Matching

```ritz
match result
    Ok(value) => process(value)
    Err(e) => handle_error(e)

match opt
    Some(x) => use_it(x)
    None => handle_missing()
```

### Error Handling

```ritz
fn load_config(path: StrView) -> Result<Config, Error>
    let fd = open(path)?       # ? propagates errors
    defer close(fd)             # defer runs on scope exit

    let content = read_all(fd)?
    let config = parse(content)?
    Ok(config)
```

---

## Writing Tests

Tests are functions annotated with `[[test]]`:

```ritz
[[test]]
fn test_addition() -> i32
    assert 2 + 2 == 4
    0   # Return 0 = pass, non-zero = fail
```

Run tests:

```bash
ritz test .
```

Ritzunit automatically discovers all `[[test]]` functions via ELF symbol scanning — no manual registration needed.

---

## Adding Dependencies

Edit your `ritz.toml` to add dependencies from the ecosystem:

```toml
[dependencies]
squeeze = { path = "../squeeze" }
cryptosec = { path = "../cryptosec" }
```

Then clone the dependencies:

```bash
cd ~/dev/ritz-lang
git clone https://github.com/ritz-lang/squeeze.git squeeze
git clone https://github.com/ritz-lang/cryptosec.git cryptosec
```

Import in your code:

```ritz
import squeeze.gzip
import cryptosec.sha256
```

---

## Building a Web Server

Valet makes it straightforward to build a high-performance HTTP server:

```ritz
import valet { Server, Request, Response }

fn handle_request(req: Request) -> Response
    if req.path == "/"
        Response.ok("<h1>Hello from Ritz!</h1>")
    else
        Response.not_found("Page not found")

fn main() -> Result<(), Error>
    var server = Server.new()
    server.set_handler(handle_request)
    server.listen(":8080")?
    Ok(())
```

Build and test:

```bash
ritz build .
./build/debug/myserver
curl http://localhost:8080/
```

---

## Next Steps

- [Language Overview](language/overview.md) — Deep dive into the language
- [Syntax Reference](language/syntax.md) — Complete syntax reference
- [Ownership and Borrowing](language/ownership.md) — Memory safety model
- [Type System](language/types.md) — Types, generics, and traits
- [Standard Library](language/stdlib.md) — ritzlib module reference
- [Architecture](architecture.md) — How the ecosystem fits together
- [Contributing](contributing.md) — How to contribute to Ritz

---

## Common Patterns

### Defer for Cleanup

```ritz
fn process_file(path: StrView) -> Result<(), Error>
    let fd = open(path)?
    defer close(fd)         # Always runs, even on early return

    let data = read_all(fd)?
    process(data)
    Ok(())
```

### Option Instead of Null

```ritz
fn find_user(id: UserId) -> Option<User>
    match db.lookup(id)
        Some(user) => Some(user)
        None => None

# Call site
match find_user(42)
    Some(user) => greet(user)
    None => print("User not found\n")
```

### Logical Operators

Ritz uses English keywords, not symbols:

```ritz
if a and b or not c
    do_something()
```

Not `&&`, `||`, or `!`.

---

## Getting Help

- This wiki — the authoritative reference
- [LARB Standards](https://github.com/ritz-lang/larb) — Language Architecture Review Board
- GitHub Issues on each project repository
