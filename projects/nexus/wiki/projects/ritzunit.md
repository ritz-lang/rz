# Ritzunit

JUnit/pytest-style unit testing framework for Ritz. Production ready.

---

## Overview

Ritzunit is the official test framework for the Ritz ecosystem. It provides automatic test discovery (no registration), fork-based isolation, rich assertions, and a powerful CLI.

---

## Where It Fits

Ritzunit is a direct dependency of almost every project in the ecosystem:

```
ritz
└── (foundation)

ritzunit
└── ritz

squeeze → ritzunit
cryptosec → ritzunit
mausoleum → ritzunit
valet (test suite) → ritzunit
```

---

## Key Features

### ELF Self-Discovery

Ritzunit discovers tests by scanning the ELF symbol table of the compiled binary. Functions annotated with `[[test]]` are automatically registered — there is no test registry or `main` function to write.

This means you never write:
```ritz
# NEVER needed:
register_test("test_something", test_something)
```

You just write:
```ritz
[[test]]
fn test_something() -> i32
    assert 2 + 2 == 4
    0
```

And Ritzunit finds it.

### Fork-Based Isolation

Each test runs in a forked child process. This provides:

- **Crash isolation** — A segfault in one test does not abort the entire run
- **Timeout enforcement** — Tests that hang are killed
- **Clean state** — Each test starts with fresh memory

### Rich Assertions

Ritzunit provides 18+ assertion functions:

| Function | Description |
|----------|-------------|
| `assert(cond)` | Boolean assertion |
| `assert_eq(a, b)` | Equality |
| `assert_ne(a, b)` | Not equal |
| `assert_lt(a, b)` | Less than |
| `assert_gt(a, b)` | Greater than |
| `assert_le(a, b)` | Less than or equal |
| `assert_ge(a, b)` | Greater than or equal |
| `assert_str_eq(a, b)` | String equality |
| `assert_str_contains(s, sub)` | String contains substring |
| `assert_ok(result)` | Result is Ok |
| `assert_err(result)` | Result is Err |
| `assert_some(option)` | Option is Some |
| `assert_none(option)` | Option is None |

---

## Writing Tests

### Basic Test

```ritz
[[test]]
fn test_addition() -> i32
    assert 2 + 2 == 4
    0   # 0 = PASS, non-zero = FAIL
```

### Test with Setup

```ritz
[[test]]
fn test_vec_push() -> i32
    var v: Vec<i32> = Vec.new()
    v.push(1)
    v.push(2)
    v.push(3)
    assert v.len() == 3
    assert v[0] == 1
    assert v[2] == 3
    0

[[test]]
fn test_hashmap_insert() -> i32
    var map: HashMap<String, i32> = HashMap.new()
    map.insert(String.from("key"), 42)
    let value = map.get("key")
    assert value.is_some()
    assert value.unwrap() == 42
    0
```

### Error Tests

```ritz
[[test]]
fn test_parse_error() -> i32
    let result = parse_int("not_a_number")
    assert result.is_err()
    0

[[test]]
fn test_bounds_check() -> i32
    let v = Vec.from([1, 2, 3])
    let result = v.get(10)
    assert result.is_none()
    0
```

### Testing String Behavior

```ritz
[[test]]
fn test_string_contains() -> i32
    let s = "Hello, World!"
    assert s.contains("World")
    assert s.starts_with("Hello")
    assert s.ends_with("!")
    0
```

---

## Running Tests

```bash
# Run all tests in current project
ritz test .

# Run specific test by name
ritz test . --filter test_addition

# Run tests matching a pattern
ritz test . --filter "test_vec_"

# List all available tests
ritz test . --list

# Verbose output (show stdout from tests)
ritz test . --verbose

# Custom timeout
ritz test . --timeout 30
```

### Output Format

```
Running 12 tests...

  PASS  test_addition          (0.001s)
  PASS  test_vec_push          (0.002s)
  PASS  test_hashmap_insert    (0.001s)
  FAIL  test_parse_error       (0.001s)
    Expected: Err
    Got: Ok(0)
  PASS  test_bounds_check      (0.001s)

Results: 11 passed, 1 failed
```

---

## Current Status

Production ready. Ritzunit is used across the entire ecosystem:

| Project | Tests |
|---------|-------|
| ritz | 324 language + 201 unit |
| squeeze | 132 |
| cryptosec | 331 |
| valet | 85 |
| mausoleum | ~100+ |

---

## Related Projects

- [Ritz](ritz.md) — The compiler Ritzunit is built on
- [Squeeze](squeeze.md) — Uses Ritzunit for all 132 tests
- [Cryptosec](cryptosec.md) — Uses Ritzunit for all 331 tests
- [Language Reference — Testing](../language/overview.md)
