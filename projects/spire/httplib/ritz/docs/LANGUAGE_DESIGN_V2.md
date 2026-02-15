# Ritz Language Design v2

## Executive Summary

We have a working bootstrap compiler (ritz0 in Python) that compiles 49 examples. However, the self-hosted compiler (ritz1) is a mess of hardcoded hacks. This document defines the path to a properly designed language.

## Current State

### What Works (ritz0)

| Feature | Status | Notes |
|---------|--------|-------|
| Integers (i8-i64, u8-u64) | ✅ | All sizes working |
| Pointers (*T, **T) | ✅ | Single/double indirection |
| Structs | ✅ | Definition, access, nesting |
| Arrays ([N]T) | ✅ | Stack allocated, fixed size |
| Functions | ✅ | Params, returns, recursion |
| Control flow | ✅ | if/else/while/break/continue |
| Imports | ✅ | Module system with caching |
| Constants | ✅ | Compile-time integers |
| Syscalls | ✅ | Via extern functions |

### What's Missing

| Feature | Priority | Needed For |
|---------|----------|------------|
| **Generics** | P0 | Vec<T>, HashMap<K,V>, Option<T> |
| **Traits/Interfaces** | P0 | Hash, Eq, Drop, Iter |
| **Computed struct layouts** | P0 | Compiler using parsed structs |
| **Ownership/Borrowing** | P1 | Memory safety |
| **Enums (sum types)** | P1 | Option<T>, Result<T,E> |
| **Pattern matching** | P1 | Match on enums |
| **Methods (self)** | P2 | Cleaner API design |
| **String type** | P2 | Beyond raw *u8 |

### ritzlib Inventory

| Module | Purpose | Quality |
|--------|---------|---------|
| sys.ritz | Syscall wrappers | ✅ Solid |
| io.ritz | Print functions | ✅ Solid |
| str.ritz | String utilities | ✅ Solid |
| memory.ritz | Arena allocator, malloc | ✅ Solid |
| buf.ritz | Byte buffer | ✅ Solid |
| args.ritz | CLI arg parsing | ✅ Solid |
| vec.ritz | ByteVec (non-generic) | ⚠️ Needs generics |
| json.ritz | JSON parser | ⚠️ Verbose without enums |
| fs.ritz | Filesystem utilities | ⚠️ Raw stat handling |
| elf.ritz | ELF parsing | ✅ Solid |
| testing.ritz | Test framework | ⚠️ Macro-like needed |
| meta.ritz | Metadata structs | ✅ Solid |

### ritz1 Problems (main_new.ritz = 4438 lines)

1. **Hardcoded struct layouts** (lines 2560-2720+)
   - Manually specifying field offsets instead of computing from parsed structs

2. **Hardcoded type inference** (lines 994-1120+)
   - Manually listing which fields are pointers

3. **No data structures**
   - is_already_imported uses O(n) linked list
   - No HashMap, no Vec<T>

4. **Global state hacks**
   - g_globals passed through globals
   - No proper module context

---

## Language Design Goals

### Goal 1: Generics

```ritz
# Generic struct
struct Vec<T>
  data: *T
  len: i64
  cap: i64

# Generic function
fn vec_push<T>(v: *Vec<T>, item: T)
  if v.len >= v.cap
    vec_grow(v)
  *(v.data + v.len) = item
  v.len = v.len + 1

# Usage
var nums: Vec<i32> = vec_new<i32>()
vec_push(&nums, 42)
```

### Goal 2: Traits

```ritz
trait Hash
  fn hash(self: &Self) -> u64

trait Eq
  fn eq(self: &Self, other: &Self) -> bool

trait Drop
  fn drop(self: &mut Self)

# Implementation
impl Hash for i32
  fn hash(self: &i32) -> u64
    *self as u64

# Trait bounds
fn contains<T: Eq>(haystack: &Vec<T>, needle: &T) -> bool
  var i: i64 = 0
  while i < haystack.len
    if (*haystack.data + i).eq(needle)
      return true
    i = i + 1
  false
```

### Goal 3: Enums (Sum Types)

```ritz
enum Option<T>
  Some(T)
  None

enum Result<T, E>
  Ok(T)
  Err(E)

# Pattern matching
fn unwrap_or<T>(opt: Option<T>, default: T) -> T
  match opt
    Some(val) -> val
    None -> default
```

### Goal 4: Computed Struct Layouts

The compiler should:
1. Parse struct definitions
2. Compute field offsets based on types
3. Use those computed offsets in code generation

No more:
```ritz
# BAD: Hardcoded
if str_eq(field_name, "functions", 9) == 1
  field_offset = 24
```

Instead, the compiler maintains a `StructRegistry` with computed layouts.

### Goal 5: Ownership & Borrowing

```ritz
# Owned value - moves on assignment
let v: Vec<i32> = vec_new()

# Shared borrow - read-only reference
fn print_vec(v: &Vec<i32>)

# Mutable borrow - exclusive mutable access
fn vec_push(v: &mut Vec<i32>, item: i32)

# Rules:
# - Many &T OR one &mut T, never both
# - Borrows cannot outlive owner
# - Lifetimes inferred (no annotations in common cases)
```

### Goal 6: Methods

```ritz
# Method syntax
fn Vec.push(self: &mut Vec<i32>, item: i32)
  # self is receiver

# Call syntax
v.push(42)  # Same as Vec.push(&mut v, 42)
```

---

## Implementation Order

### Phase 1: Foundation (ritz0)

1. **Computed struct layouts in ritz0**
   - Maintain struct registry with computed offsets
   - Generate correct GEP instructions

2. **Basic generics in ritz0**
   - Monomorphization (duplicate code for each concrete type)
   - Start with Vec<T>

3. **Basic traits in ritz0**
   - Start with Drop (destructor semantics)
   - Then Hash, Eq

### Phase 2: Collections (ritzlib)

4. **Vec<T>** - Dynamic array
   - push, pop, get, set, len, capacity
   - Implements Drop for cleanup

5. **HashMap<K, V>** - Hash table
   - K: Hash + Eq
   - get, insert, contains, remove
   - Implements Drop for cleanup

6. **String** - Owned string
   - Based on Vec<u8>
   - UTF-8 aware operations

### Phase 3: Error Handling

7. **Enums** - Sum types
   - Discriminated unions
   - Option<T>, Result<T, E>

8. **Pattern matching** - Match expressions
   - Exhaustiveness checking
   - Binding in patterns

### Phase 4: Ownership

9. **Move semantics** - Default for non-Copy types
10. **Borrow checking** - Static analysis pass
11. **Lifetimes** - Inferred in common cases

### Phase 5: Bootstrap

12. **Rewrite ritz1** using new features
13. **Self-host** - ritz1 compiles itself
14. **Deprecate** the Python bootstrap

---

## Specific Anti-Patterns to Eliminate

### From main_new.ritz

| Line(s) | Problem | Solution |
|---------|---------|----------|
| 32-36 | Global state workaround | Proper module context |
| 39+ | O(n) import tracking | HashMap[String, bool] |
| 994-1120 | Hardcoded field types | Computed from StructDef |
| 2560-2720 | Hardcoded field offsets | Computed from StructDef |
| 160+ calls | parser_alloc(p, MAGIC_NUMBER) | sizeof(T) or allocator |

### General

| Pattern | Problem | Solution |
|---------|---------|----------|
| *u8 everywhere | No string safety | String type |
| Linked lists | O(n) operations | Vec, HashMap |
| Manual malloc/free | Memory leaks | Drop trait, RAII |
| Magic numbers | Unmaintainable | sizeof, constants |

---

## Next Steps

1. [ ] Design generics syntax precisely
2. [ ] Design trait syntax precisely
3. [ ] Implement computed struct layouts in ritz0
4. [ ] Implement basic generics in ritz0
5. [ ] Build Vec<T> in ritzlib
6. [ ] Build HashMap<K,V> in ritzlib
7. [ ] Build String type
8. [ ] Implement enums
9. [ ] Implement match
10. [ ] Add ownership/borrowing
11. [ ] Rewrite ritz1
12. [ ] Bootstrap

---

*Document created: 2025-01-01*
*Last updated: 2025-01-01*
