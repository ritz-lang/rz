# Delegates and Closures Design for Ritz

## Overview

This document describes the design of delegates (first-class functions with captures) in Ritz. Unlike simple function pointers, delegates can capture variables from their enclosing scope.

## Design Goals

1. **Type-safe** - Full type checking for function signatures
2. **Captures** - Support capturing variables from enclosing scope
3. **Efficient** - Zero overhead when no captures (bare function pointer)
4. **Interoperable** - Compatible with C function pointers when no captures
5. **Generic** - Work with generic type parameters

## Syntax

### Function Pointer Types (No Captures)

```ritz
# Bare function pointer type
let f: fn(i32, i32) -> i64

# As a parameter
fn apply(x: i32, f: fn(i32) -> i32) -> i32
    f(x)

# Usage
fn double(x: i32) -> i32
    x * 2

let result: i32 = apply(5, double)  # 10
```

### Closures (With Captures)

```ritz
fn make_adder(n: i32) -> fn(i32) -> i32
    # Closure captures 'n' from enclosing scope
    |x| x + n

let add5: fn(i32) -> i32 = make_adder(5)
let result: i32 = add5(10)  # 15
```

### Closure Syntax Options

| Syntax | Example | Notes |
|--------|---------|-------|
| **Pipe syntax** | `|x, y| x + y` | Rust-style, clean |
| **Lambda keyword** | `lambda(x, y) x + y` | Explicit |
| **Arrow syntax** | `(x, y) => x + y` | JavaScript/C# style |
| **fn block** | `fn(x, y) { x + y }` | Consistent with fn |

**Recommendation**: Pipe syntax `|args| expr` - clean and familiar from Rust.

## Implementation Strategy

### Phase 1: Bare Function Pointers

First, implement function pointers without captures:

1. **Type representation**: `FnType` compiles to LLVM function pointer
2. **Function reference**: `&fn_name` or just `fn_name` gets address
3. **Indirect call**: Call through function pointer

```ritz
fn callback(x: i32) -> i32
    x * 2

fn apply(f: fn(i32) -> i32, x: i32) -> i32
    f(x)  # Indirect call

let result: i32 = apply(callback, 5)  # 10
```

### Phase 2: Closures with Captures

Closures that capture variables need a "fat pointer" representation:

```
Delegate<Args, Ret> = {
    fn_ptr: fn(*Environment, Args...) -> Ret,
    env_ptr: *Environment
}
```

The closure conversion transform:
1. Identifies captured variables
2. Generates an environment struct
3. Converts the closure body to take env as first parameter
4. Returns a delegate struct

**Example transformation:**

```ritz
# Source
fn make_adder(n: i32) -> fn(i32) -> i32
    |x| x + n

# Transformed
struct make_adder_closure_env
    n: i32

fn make_adder_closure_fn(env: *make_adder_closure_env, x: i32) -> i32
    x + (*env).n

fn make_adder(n: i32) -> Delegate<(i32,), i32>
    let env: *make_adder_closure_env = alloc(sizeof(make_adder_closure_env))
    (*env).n = n
    Delegate {
        fn_ptr: make_adder_closure_fn,
        env_ptr: env as *u8
    }
```

### Phase 3: Delegate Type

Define a built-in delegate type:

```ritz
# Built-in delegate struct (conceptual)
struct Delegate<Args, Ret>
    fn_ptr: fn(*u8, Args...) -> Ret
    env_ptr: *u8

impl<Args, Ret> Delegate<Args, Ret>
    fn call(self: &Self, args: Args...) -> Ret
        self.fn_ptr(self.env_ptr, args...)
```

## Memory Management

### Capture Modes

| Mode | Syntax | Behavior |
|------|--------|----------|
| **Copy** | `|x| ...` | Copy value into closure |
| **Reference** | `|&x| ...` | Capture reference (borrowing) |
| **Move** | `|move x| ...` | Move ownership into closure |

### Lifetime Considerations

- Closures that capture by reference must not outlive the captured variables
- Move captures transfer ownership, safe for returning closures
- Copy captures are always safe

### Allocation Strategy

1. **Stack allocation**: For closures that don't escape
2. **Heap allocation**: For closures returned from functions
3. **No allocation**: For bare function pointers (no captures)

## Type System Integration

### Subtyping

- `fn(A) -> B` is a subtype of `Delegate<(A,), B>` (bare fn can be used as delegate)
- Delegates with same signature are compatible regardless of capture type

### Generic Delegates

```ritz
fn map<T, U>(items: &[T], f: fn(T) -> U) -> Vec<U>
    var result: Vec<U> = Vec::new()
    for item in items
        result.push(f(*item))
    result
```

## LLVM IR Representation

### Bare Function Pointer

```llvm
; Function type
%fn_i32_to_i32 = type i32 (i32)*

; Call through function pointer
%result = call i32 %fn_ptr(i32 %arg)
```

### Delegate (Fat Pointer)

```llvm
; Delegate struct
%Delegate = type { i32 (i8*, i32)*, i8* }

; Call through delegate
%fn_ptr = extractvalue %Delegate %delegate, 0
%env_ptr = extractvalue %Delegate %delegate, 1
%result = call i32 %fn_ptr(i8* %env_ptr, i32 %arg)
```

## Implementation Phases

### Phase 1: Bare Function Pointers (MVP)
- [x] Parse `fn(T) -> R` type syntax
- [ ] Emit LLVM function pointer type
- [ ] Emit indirect calls through function pointers
- [ ] Allow passing function names as values
- [ ] Test with callbacks

### Phase 2: Closure Syntax
- [ ] Parse closure syntax `|args| expr`
- [ ] Identify captured variables
- [ ] Type check closures

### Phase 3: Closure Conversion
- [ ] Generate environment struct
- [ ] Transform closure body
- [ ] Generate delegate struct
- [ ] Handle copy/move captures

### Phase 4: Memory Management
- [ ] Stack allocation for non-escaping closures
- [ ] Heap allocation for escaping closures
- [ ] Integrate with ownership system

## Use Cases

### Callbacks

```ritz
fn on_complete(callback: fn(i32) -> ())
    let result: i32 = do_work()
    callback(result)
```

### Higher-Order Functions

```ritz
fn filter<T>(items: &[T], predicate: fn(&T) -> bool) -> Vec<T>
    var result: Vec<T> = Vec::new()
    for item in items
        if predicate(item)
            result.push(*item)
    result
```

### Event Handlers

```ritz
struct Button
    on_click: fn() -> ()

impl Button
    fn click(self: &Self)
        (self.on_click)()
```

### Async Runtime (block_on)

```ritz
fn block_on<T>(future_ptr: *u8, poll_fn: fn(*u8) -> Poll<T>) -> T
    loop
        match poll_fn(future_ptr)
            Poll::Ready(value) => return value
            Poll::Pending => wait_for_io()
```

## Open Questions

1. **Closure syntax**: `|x| expr` vs `\x -> expr` vs `fn(x) expr`?
   - Decision: Use `|x| expr` (Rust-style)

2. **Capture inference**: Infer copy vs reference vs move?
   - Decision: Default to copy for small types, require explicit for others

3. **Type syntax**: `fn(T) -> R` vs `Fn<T, R>` for delegates?
   - Decision: `fn(T) -> R` for both, compiler handles fat pointer internally

4. **Calling convention**: How to call delegates uniformly?
   - Decision: `delegate(args)` syntax works for both bare fn and closures

---

*Created: 2026-01-09*
