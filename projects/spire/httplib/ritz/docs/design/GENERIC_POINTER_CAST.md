# RFC: Generic Types in Cast Expressions

**Status:** Proposed
**Author:** Tome (Adele)
**Date:** 2026-02-13

---

## Executive Summary

This RFC proposes supporting cast expressions with generic types like `*Vec<T>`, enabling idiomatic null pointer checks and type coercions for generic container pointers.

---

## 1. Problem Statement

### Current Behavior

Casting to non-generic pointer types works:

```ritz
var node: *Node = store_get(&s, &id)
if node == 0 as *Node    # Works - casts 0 to *Node
    return -1
```

But casting to generic pointer types fails:

```ritz
fn create_node(title: *Vec<u8>) -> i32
    if title == 0 as *Vec<u8>    # FAILS: "Expected expression, got COMMA"
        # handle null
```

The parser fails when it sees the `<` in the cast expression.

### Impact

| Problem | Effect |
|---------|--------|
| **No null checks for generic pointers** | Can't idiomatically check if `*Vec<T>` is null |
| **Workaround required** | Must cast pointer to i64 for comparison |
| **Inconsistent** | Non-generic pointers work, generic ones don't |

### Current Workaround

Cast the pointer to `i64` for comparison:

```ritz
fn create_node(title: *Vec<u8>) -> i32
    let title_ptr: i64 = title as i64
    if title_ptr == 0
        # handle null
```

This works but is verbose and non-idiomatic.

---

## 2. Proposed Solution

### 2.1 Support Generic Types in Cast Expressions

Allow cast expressions with generic pointer types:

```ritz
if title == 0 as *Vec<u8>
    # handle null

if title != null as *Vec<u8>
    store_update_title(&server.store, &node_id, title)
```

### 2.2 Grammar Changes

Current cast expression grammar (informal):
```
cast_expr := expr 'as' type
type := '*'? NAME
```

Proposed grammar:
```
cast_expr := expr 'as' type
type := '*'? NAME ('<' type_args '>')?
type_args := type (',' type)*
```

The key change is allowing `<type_args>` after the type name in cast expressions.

### 2.3 Parser Disambiguation

The parser must distinguish:

```ritz
x as *Vec<u8>     # Cast to *Vec<u8>
x < y             # Less-than comparison
```

Context: After `as TYPE`, if we see `<`, it's the start of type arguments, not a comparison.

---

## 3. Implementation

### Parser Changes (ritz0/parser.py)

In `parse_cast_expr()` or `parse_type()`:

```python
def parse_type(self):
    is_ptr = self.match(TokenKind.STAR)
    name = self.expect(TokenKind.NAME)

    type_args = []
    if self.match(TokenKind.LT):  # NEW: Parse generic args
        type_args.append(self.parse_type())
        while self.match(TokenKind.COMMA):
            type_args.append(self.parse_type())
        self.expect(TokenKind.GT)

    return TypeNode(name, is_ptr, type_args)
```

### Type Checker Changes

The type checker already handles generic types; it just needs to receive them from cast expressions.

### Codegen Changes

For null pointer casts (`0 as *Vec<T>`), emit the same LLVM IR as for non-generic pointers:
```llvm
%ptr = inttoptr i64 0 to ptr
```

---

## 4. Examples

### Before
```ritz
# Verbose workaround
fn mcp_create_node(server: *McpServer, title: *Vec<u8>, content: *Vec<u8>) -> Uuid
    var node_id: Uuid = store_create(&server.store, kind, parent_id)

    let title_ptr: i64 = title as i64
    let content_ptr: i64 = content as i64
    if title_ptr != 0
        store_update_title(&server.store, &node_id, title)
    if content_ptr != 0
        store_update_content(&server.store, &node_id, content)

    return node_id
```

### After
```ritz
# Clean, idiomatic
fn mcp_create_node(server: *McpServer, title: *Vec<u8>, content: *Vec<u8>) -> Uuid
    var node_id: Uuid = store_create(&server.store, kind, parent_id)

    if title != 0 as *Vec<u8>
        store_update_title(&server.store, &node_id, title)
    if content != 0 as *Vec<u8>
        store_update_content(&server.store, &node_id, content)

    return node_id
```

---

## 5. Related: `null` Keyword

A complementary approach is a `null` keyword that infers type from context:

```ritz
if title != null
    store_update_title(&server.store, &node_id, title)
```

This would require:
- Adding `null` as a keyword
- Type inference for null in comparison context
- Could coexist with explicit casts

**Recommendation:** Both should be implemented. Generic pointer casts solve the general case (any generic type in cast position), while `null` provides ergonomic shorthand for the common null-check pattern. Consider tracking `null` in a separate RFC.

---

## 6. Compatibility

- **Backward compatible** - No existing syntax changes meaning
- **No runtime changes** - Pure parser/type-checker enhancement

---

## 7. Alternatives Considered

| Alternative | Reason Rejected |
|------------|-----------------|
| Cast to i64 | Verbose, non-idiomatic |
| Special null keyword only | Doesn't solve the general case |
| Implicit null coercion | Too magical, hides intent |

---

## 8. Test Cases

```ritz
# Should compile and work
fn test_null_vec_ptr() -> i32
    var v: Vec<u8> = vec_new<u8>()
    var ptr: *Vec<u8> = &v

    # Null check
    if ptr == 0 as *Vec<u8>
        return -1

    # Non-null
    if ptr != 0 as *Vec<u8>
        return 0

    return 1

fn test_null_nested_generic() -> i32
    var ptr: *Vec<Vec<u8>> = 0 as *Vec<Vec<u8>>
    if ptr == 0 as *Vec<Vec<u8>>
        return 0
    return 1

# Pointer coercion between generic types
fn test_generic_pointer_coercion() -> i32
    var raw: *u8 = alloc(32)
    var vec_ptr: *Vec<u8> = raw as *Vec<u8>
    return 0
```
