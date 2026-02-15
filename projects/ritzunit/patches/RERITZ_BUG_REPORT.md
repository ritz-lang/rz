# RERITZ Compiler Bug: Mutable Reference Field Access

## Summary

Commit 0f13519 ("Remove legacy &mut syntax - complete RERITZ migration") introduces a bug where accessing a field through a mutable reference (`@@T`) and then taking a reference to that field produces an incorrect type with an extra level of indirection.

## Reproduction

```ritz
struct Inner
    value: i32

struct Outer
    inner: Inner

fn modify_inner(i: @@Inner)
    i.value = 42

fn test_field_ref(o: @@Outer)
    modify_inner(@o.inner)  # BUG: This produces @@@Inner instead of @@Inner

fn main() -> i32
    var o: Outer
    o.inner.value = 0
    test_field_ref(@@o)
    return 0
```

## Error

```
Compiler error: Cannot access field on type: %"struct.ritz_module_1.Outer"***
```

Or in functions that call generic vec functions:

```
TypeError: Type of #1 arg mismatch: %"struct.ritz_module_1.Vec$u8"** != %"struct.ritz_module_1.Vec$u8"*
```

## Expected Behavior

When `o: @@Outer` (mutable reference to Outer):
- `o.inner` should auto-dereference and access the `inner` field, yielding `Inner`
- `@o.inner` should take a mutable reference to that field, yielding `@@Inner`

## Actual Behavior

The compiler produces `@@@Inner` (triple pointer) or similar incorrect types.

## Affected Files

- `ritzlib/string.ritz` - functions like `string_as_ptr`, `string_drop` that use `@s.data` where `s: @@String`
- `ritzlib/io.ritz` - functions using print_string with local String variables
- Any code that accesses nested fields through mutable references

## Workaround

Use the pre-RERITZ commit `b078d54` which uses the old `&` and `@&` syntax for references.

## Root Cause

The RERITZ migration changed:
- `&x` -> `@x` (immutable reference)
- `&mut x` / `@&x` -> `@@x` (mutable reference)

The emitter's handling of field access through references doesn't correctly handle the new syntax, adding an extra level of indirection.

## Impact

This blocks migration to the RERITZ syntax for any code that:
1. Uses nested structs
2. Passes field references to functions that take `@@T` parameters
3. Uses Vec<T> inside structs (very common pattern)

## Commits

- **Broken**: 0f13519 (RERITZ migration)
- **Working**: b078d54 (pre-RERITZ)
