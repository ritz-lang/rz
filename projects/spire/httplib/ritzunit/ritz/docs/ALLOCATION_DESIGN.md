# Unified Allocation Model for Ritz

## Philosophy

**"Where memory lives is an implementation detail; ownership is the semantic contract."**

The programmer thinks in terms of:
1. **Ownership** - who is responsible for cleanup?
2. **Borrowing** - who can read/write temporarily?
3. **Lifetime** - how long does this exist?

The programmer should NOT need to think about:
- Stack vs heap (except for performance tuning)
- Manual malloc/free
- Pointer arithmetic (except for hardware/allocators)

## Current State

### Stack Allocation
```ritz
var p: Point      # Inline on stack, tied to scope
p.x = 10          # Direct field access
# p is dropped at scope end
```

### Heap Allocation (Box)
```ritz
var b: Box<Point> = box_new(Point{x: 10, y: 20})
let x = b.x       # Implicit deref through ptr field
# b.ptr freed at scope end via Drop
```

### Heap Allocation (Vec)
```ritz
var v: Vec<i32> = vec_new<i32>()
v.push(42)        # Backing array on heap
# v.data freed at scope end via Drop
```

## Problems with Current Model

1. **Explicit heap syntax** - `box_new`, `vec_new` are verbose
2. **Separate types** - `Point` vs `Box<Point>` are different types
3. **Pointer soup in ritzlib** - Uses `*Self` everywhere instead of `&mut Self`
4. **No unified construction** - Stack vs heap have different APIs

## Proposed Unified Model

### Principle 1: Value Semantics by Default

```ritz
# Stack-allocated, owned by this scope
var p: Point
p.x = 10
p.y = 20

# Return transfers ownership (NRVO - zero copy)
fn make_point() -> Point
    var p: Point
    p.x = 10
    p.y = 20
    return p  # Caller provides destination slot
```

### Principle 2: Borrowing for Access

```ritz
fn update(p: &mut Point)    # Mutable borrow
    p.x = p.x + 1

fn read(p: &Point) -> i32   # Shared borrow
    return p.x

# Usage
var p: Point
update(&mut p)
let x = read(&p)
```

### Principle 3: Explicit Heap When Needed

When you need heap allocation (dynamic lifetime, unknown size, shared ownership):

```ritz
# Option A: Constructor syntax
var p: Point = heap Point{x: 10, y: 20}

# Option B: Allocator trait
var p: Point = allocate()  # Implied: allocate<Point>()

# Option C: Special type (current approach)
var b: Box<Point> = box_new(Point{x: 10, y: 20})
```

### Principle 4: Allocator Abstraction

Different allocation strategies share the same interface:

```ritz
trait Allocator
    fn alloc<T>(self: &mut Self) -> &mut T
    fn dealloc<T>(self: &mut Self, ptr: &mut T)

# Usage with specific allocator
var arena = Arena::new(1024)
var p: &mut Point = arena.alloc<Point>()
p.x = 10
# arena.reset() frees all at once
```

## Implementation Approach

### Phase 1: Borrow Semantics in ritzlib

Replace `*Self` with proper borrows:

```ritz
# Before (current)
impl<T> Vec<T>
    fn push(self: *Vec<T>, item: T) -> i32

# After
impl<T> Vec<T>
    fn push(self: &mut Vec<T>, item: T) -> i32
```

### Phase 2: NRVO (Named Return Value Optimization)

For struct returns, caller allocates:

```ritz
fn vec_new<T>() -> Vec<T>
    var v: Vec<T>
    v.data = 0 as *T
    v.len = 0
    v.cap = 0
    return v  # Actually: write to caller's slot
```

Compiler transforms to:
```llvm
define void @vec_new(%Vec* sret %result) {
  ; Write directly to %result
  store i64 0, i64* getelementptr(%Vec, %Vec* %result, i32 0, i32 1)
  ...
}
```

### Phase 3: Unified Syntax (Future)

```ritz
# Stack (default)
var p: Point = Point{x: 10, y: 20}

# Heap (explicit)
var p: Point = heap Point{x: 10, y: 20}

# Both have same type, same ownership semantics
# Difference is just where bytes live
```

## String and UTF-8

### Current: String = Vec<u8>

```ritz
struct String
    data: Vec<u8>  # Byte storage
```

### Vision: String = Unicode Characters

```ritz
# String holds valid UTF-8
var s: String = "Hello, 世界!"

# Indexing by character (not byte)
let c: char = s[7]  # '世' (U+4E16)

# Iteration by character
for c in s
    print_char(c)  # Yields each Unicode codepoint

# Byte access when needed
let bytes: &[u8] = s.as_bytes()
```

### Implementation

```ritz
struct String
    data: Vec<u8>  # UTF-8 encoded bytes (internal)

# Length in characters (not bytes)
fn len(self: &String) -> i64
    # Count UTF-8 codepoints

# Index by character position
fn char_at(self: &String, idx: i64) -> char
    # Decode UTF-8 at position
```

## Key Insight: Ownership is Orthogonal to Location

| Aspect | Stack | Heap |
|--------|-------|------|
| Ownership | Scope-based | Scope-based (via Drop) |
| Borrowing | `&T`, `&mut T` | `&T`, `&mut T` |
| Lifetime | Until scope end | Until Drop called |
| Performance | Fast alloc/dealloc | Slower, but dynamic |
| Use case | Fixed size, short-lived | Dynamic, shared, long-lived |

The **ownership model is identical**. The only difference is:
- Stack: compiler-managed memory
- Heap: allocator-managed memory

## Pointers: When to Use

Pointers (`*T`) are low-level and should only appear in:
1. **Memory allocators** (malloc, arena_alloc)
2. **FFI / syscall interfaces**
3. **Hardware access** (memory-mapped I/O)

All other code should use:
- `T` - owned value
- `&T` - shared borrow
- `&mut T` - mutable borrow

## Next Steps

1. **GH #74**: Migrate ritzlib from `*Self` to `&mut Self`
2. Implement proper borrow checking in move_checker.py
3. Add NRVO optimization for struct returns
4. Design String UTF-8 semantics
5. Explore unified heap/stack syntax
