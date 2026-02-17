# LARB Review: Iris

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** NEEDS WORK

## Summary

Iris is the rendering engine for the Tempest browser, responsible for maintaining a render tree, performing CSS layout (block, inline, flex, grid stubs), compositing layer management, hit testing, and painting. The project is architecturally well-organized and largely follows modern Ritz idioms, with correct use of `@` reference syntax, `[[test]]` attributes, and keyword logical operators. However, it contains a mix of two competing internal representation styles (integer constants vs. proper enum types), uses `c"..."` string literals in test code, and has one file (`lib/layout/block.ritz`) with several compliance violations including old Rust-style `&T`/`&mut T` ownership modifiers in function parameters and `true`/`false` boolean literals where `i32` 1/0 is the established convention for this codebase.

## Statistics

- **Files Reviewed:** 17
- **Total SLOC:** ~850
- **Issues Found:** 12 (Critical: 0, Major: 8, Minor: 4)

## Critical Issues

None. No code was found that would fail to compile outright or introduce memory safety hazards not already expected for this project type.

## Major Issues

### 1. Old Rust-Style Ownership Modifiers in `lib/layout/block.ritz`

**File:** `/home/aaron/dev/ritz-lang/rz/projects/iris/lib/layout/block.ritz`

All four internal functions in this file use Rust-style `&T` and `&mut T` ownership syntax instead of the Ritz colon-modifier idiom:

```ritz
# WRONG - Rust-style borrows
pub fn layout_block(
    tree:& RenderTree,       # OK - this is actually correct Ritz :& syntax
    node_id: NodeId,
    constraints: LayoutConstraints
) -> LayoutResult

fn layout_block_node(
    tree:& RenderTree,       # OK
    node:& RenderNode,       # OK - correct :& syntax
    constraints: LayoutConstraints
) -> LayoutResult
```

Wait - on closer inspection, `tree:& RenderTree` IS the correct Ritz `:&` mutable borrow syntax. However, this file also passes these parameters to functions expecting `@&T` reference types (e.g., `render_tree_get_mut(tree, node_id)` where the tree parameter is `:& RenderTree` rather than `@&RenderTree`). This is an inconsistency in how owned mutable borrows vs. reference-to-mutable are used.

**File:** `/home/aaron/dev/ritz-lang/rz/projects/iris/lib/layout/block.ritz`, lines 65-66

```ritz
# WRONG - using bool literals true/false inconsistently with the rest of the codebase
width_definite: true,
height_definite: dimension_is_auto(node.style.height) == false,
```

The `LayoutConstraints` struct defines `width_definite: i32` and `height_definite: i32` (0/1 integers), but this code assigns `true`/`false` boolean literals. The rest of the codebase consistently uses `1`/`0` for boolean-as-integer. This will either fail to compile or silently coerce.

**Correct form:**
```ritz
width_definite: 1,
height_definite: if dimension_is_auto(node.style.height) == 1 { 0 } else { 1 },
```

### 2. `c"..."` String Literal in Test Code

**File:** `/home/aaron/dev/ritz-lang/rz/projects/iris/tests/test_render_tree.ritz`, line 30

```ritz
# WRONG - old c"..." prefix
let text: *u8 = c"Hello"
```

Per spec, the modern form for FFI C strings is `"Hello".as_cstr()`. The `c"..."` prefix is deprecated application-level syntax. Although the INSTRUCTIONS note that `c"..."` is "acceptable in low-level code," test files are application-level and should use the modern form.

**Correct form:**
```ritz
let text: *u8 = "Hello".as_cstr()
```

### 3. Enum vs. Integer Constant Inconsistency

The codebase uses a dual representation strategy: `lib/style/types.ritz` defines both integer constants (e.g., `DISPLAY_BLOCK: i32 = 1`) AND exports named enum types (`Display`, `Position`, `BoxSizing`, etc.) via `lib/style/mod.ritz`. However, the actual `ComputedStyle` struct fields store `i32` values and are compared against the integer constants throughout all modules.

Meanwhile, `lib/layout/block.ritz` (which imports the higher-level `lib.style` module) matches against proper enum variants:

```ritz
# In lib/layout/block.ritz - uses enum variants
match child.style.display
    Display.Block => layout_block_node(...)
    Display.Flex  => layout_block_node(...)
    Display.Inline => layout_inline(...)
```

But `ComputedStyle.display` is declared as `i32`, not `Display`. This is a type mismatch - either `ComputedStyle` fields should use the enum types (preferred), or all match/comparison code should use integer constants consistently.

**Affected files:**
- `/home/aaron/dev/ritz-lang/rz/projects/iris/lib/style/types.ritz` - defines `ComputedStyle` with `i32` fields
- `/home/aaron/dev/ritz-lang/rz/projects/iris/lib/layout/block.ritz` - matches against enum variants on those same `i32` fields

### 4. `*node` Raw Pointer Dereference in Application Code

**File:** `/home/aaron/dev/ritz-lang/rz/projects/iris/lib/iris.ritz`, line 362

```ritz
Option.Some(node) =>
    Option.Some(render_node_absolute_rect(*node, iris.render_tree))
```

The `*node` dereference uses raw pointer syntax. This is application-level code and `node` here comes from an `Option.Some` match binding - it should be accessed as a value directly, or via `@node` if it's a reference. Raw pointer dereference (`*node`) is marked as FFI/unsafe only by the spec.

### 5. Missing `render_tree_remove` Implementation

**File:** `/home/aaron/dev/ritz-lang/rz/projects/iris/lib/tree/render_node.ritz`

`render_tree_remove` is exported in `lib/tree/mod.ritz` (line 36) and called in `lib/iris.ritz` (line 145), but its implementation is absent from `render_node.ritz`. This is a missing function that will cause a link/compile failure.

### 6. `render_tree_get` Signature Inconsistency

**File:** `/home/aaron/dev/ritz-lang/rz/projects/iris/lib/tree/render_node.ritz`, lines 278-285

```ritz
# Declared to take @RenderTree, @NodeId but called with plain values in iris.ritz
pub fn render_tree_get(tree: @RenderTree, id: @NodeId) -> @RenderNode
```

In `lib/iris.ritz`, this function is called as:
```ritz
match render_tree_get(iris.render_tree, event.id)   # line 138 - no @ sigil
```

But the parameter types require reference inputs (`@RenderTree`, `@NodeId`). The call sites in `lib/iris.ritz` inconsistently pass bare values without the `@` reference operator at multiple locations (lines 138, 152, 280, 360).

### 7. Unused `id_val` Variables

**File:** `/home/aaron/dev/ritz-lang/rz/projects/iris/lib/composite/layer.ritz`, lines 188 and 203

```ritz
let id_val = tree.next_id   # Assigned but never read
tree.next_id = tree.next_id + 1
```

This pattern appears twice (`layer_tree_create_root` and `layer_tree_create`). The `id_val` binding is dead code.

### 8. `layout_constraints_shrink_to_fit` Exported but Not Implemented

**File:** `/home/aaron/dev/ritz-lang/rz/projects/iris/lib/layout/mod.ritz`, line 7

`layout_constraints_shrink_to_fit` is re-exported but no implementation exists in `lib/layout/box.ritz`. This is a missing function.

## Minor Issues

### 1. Naming Convention: `box` as Variable Name (Reserved Word Risk)

**File:** `/home/aaron/dev/ritz-lang/rz/projects/iris/lib/layout/block.ritz`, line 48
**File:** `/home/aaron/dev/ritz-lang/rz/projects/iris/tests/test_layout_box.ritz`, lines 59, 72, etc.

```ritz
let box = resolve_box_model(node.style, constraints)
```

`box` is a keyword in many languages and is a likely future reserved word in Ritz. Use `box_dims` or `dims` instead.

### 2. `TAG_*` Constants Not `pub` but Used Across Modules

**File:** `/home/aaron/dev/ritz-lang/rz/projects/iris/lib/tree/render_node.ritz`, lines 131-141

The `TAG_DIV`, `TAG_SPAN`, etc. constants are used in test files and `src/main.ritz` but are not declared `pub`. They are also not re-exported from `lib/tree/mod.ritz`. This is likely working by accident through some import behavior but should be made explicit.

### 3. Missing Module Header Documentation in Some Files

**Files:** `/home/aaron/dev/ritz-lang/rz/projects/iris/lib/tree/mod.ritz`, `/home/aaron/dev/ritz-lang/rz/projects/iris/lib/layout/mod.ritz`, `/home/aaron/dev/ritz-lang/rz/projects/iris/lib/composite/mod.ritz`, `/home/aaron/dev/ritz-lang/rz/projects/iris/lib/style/mod.ritz`

Module export files lack documentation headers explaining the module's purpose. The standard file header comment is missing from all four `mod.ritz` files.

### 4. `DirtyFlags` Struct Uses `i32` for Boolean Fields

**File:** `/home/aaron/dev/ritz-lang/rz/projects/iris/lib/tree/render_node.ritz`, lines 31-38

All four fields (`structure`, `style`, `layout`, `paint`) are declared as `i32` but function as booleans. This is consistent with the rest of the codebase's i32-as-bool pattern, but per the language spec and `lib/style/event.ritz` which uses proper `bool` in some structs (e.g., `ImageChangedEvent.loaded: bool`), the codebase is inconsistent. The `DirtyFlags` fields should use `bool` or the `bool` usage in events should be replaced with `i32`.

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | ISSUE | `block.ritz` uses `true`/`false` assigned to `i32` fields; `@` reference call-site mismatches in `iris.ritz` |
| Reference Types (@) | ISSUE | `*node` raw pointer dereference in `iris.ritz` L362; inconsistent `@` at call sites for `render_tree_get` |
| Attributes ([[...]]) | OK | All tests correctly use `[[test]]`; no old `@test` syntax found |
| Logical Operators | OK | `and`, `or`, `not` used consistently; no `&&`, `\|\|`, `!` found |
| String Types | ISSUE | `c"Hello"` in `test_render_tree.ritz` L30 should be `"Hello".as_cstr()` |
| Error Handling | OK | No Result types used (not applicable - this is a pure computation library with no I/O errors) |
| Naming Conventions | ISSUE | `box` as variable name (potential reserved word); `TAG_*` visibility issue |
| Code Organization | OK | File structure is logical; modules are well-separated by concern |

## Files Needing Attention

1. `/home/aaron/dev/ritz-lang/rz/projects/iris/lib/layout/block.ritz` - `true`/`false` bool literal assignment to `i32` fields; enum-vs-integer type mismatch in match
2. `/home/aaron/dev/ritz-lang/rz/projects/iris/lib/iris.ritz` - `*node` raw pointer dereference (L362); `render_tree_get` called without `@` sigils (L138, L152, L280, L360)
3. `/home/aaron/dev/ritz-lang/rz/projects/iris/lib/tree/render_node.ritz` - Missing `render_tree_remove` implementation; `TAG_*` constants not `pub`
4. `/home/aaron/dev/ritz-lang/rz/projects/iris/lib/layout/mod.ritz` - Exports `layout_constraints_shrink_to_fit` with no implementation
5. `/home/aaron/dev/ritz-lang/rz/projects/iris/lib/composite/layer.ritz` - Dead `id_val` variables in two functions
6. `/home/aaron/dev/ritz-lang/rz/projects/iris/tests/test_render_tree.ritz` - `c"Hello"` old string syntax (L30)

## Recommendations

Prioritized by severity:

1. **[Major - Blocking]** Implement `render_tree_remove` in `lib/tree/render_node.ritz` and `layout_constraints_shrink_to_fit` in `lib/layout/box.ritz` - these are exported and called but missing.

2. **[Major]** Fix `true`/`false` boolean literals assigned to `i32` fields in `lib/layout/block.ritz` lines 65-66. Use `1`/`0` to match the `LayoutConstraints` struct definition.

3. **[Major]** Resolve the enum-vs-integer duality: either update `ComputedStyle` to use typed enum fields (`display: Display`, `position: Position`, etc.) throughout, or remove the enum exports and use integer constants uniformly. The current split between `lib/style/types.ritz` (integer fields) and `lib/layout/block.ritz` (enum variant matching) is inconsistent.

4. **[Major]** Replace `*node` raw pointer dereference in `lib/iris.ritz` L362 with the appropriate owned/reference access pattern.

5. **[Major]** Audit all `render_tree_get` and `render_tree_get_mut` call sites in `lib/iris.ritz` - add `@` address-of operators where reference parameters are expected.

6. **[Major]** Update `tests/test_render_tree.ritz` L30: replace `c"Hello"` with `"Hello".as_cstr()`.

7. **[Minor]** Rename `box` variable to `box_dims` or `dims` in `lib/layout/block.ritz` and test files to avoid potential reserved word conflicts.

8. **[Minor]** Mark `TAG_DIV`, `TAG_SPAN`, etc. as `pub` in `render_node.ritz` and add them to the `lib/tree/mod.ritz` re-export list.

9. **[Minor]** Standardize boolean representation: choose either `bool` or `i32` for boolean-valued fields and apply consistently. Currently `ImageChangedEvent.loaded` uses `bool` while `DirtyFlags` fields use `i32`.

10. **[Minor]** Remove dead `id_val` variable assignments in `layer_tree_create_root` and `layer_tree_create` in `lib/composite/layer.ritz`.
