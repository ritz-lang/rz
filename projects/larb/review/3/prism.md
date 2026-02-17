# LARB Review: Prism

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** NEEDS WORK

## Summary

Prism is a graphics compositor / display server project with a well-structured codebase covering window management, damage tracking, input routing, a client API, text rendering, and a mock backend for testing. The majority of the modern Ritz source files (`src/`) are in excellent shape - they consistently use `impl` blocks, `[[test]]` attributes, `@`/`@&` syntax, and keyword logical operators. However, two test files (`test/test_core.ritz` and `test/test_damage.ritz`) and one tool file (`tools/render_test.ritz`) contain pervasive old-style syntax including `&&`/`||` logical operators, `&T`/`*T` in function parameters (non-FFI context), `c"..."` string prefixes, and raw pointer arithmetic - pulling the overall score down significantly. There is also one isolated duplication issue: `src/damage.ritz` is a standalone procedural module that duplicates geometry types already defined in `src/types/rect.ritz`.

## Statistics

- **Files Reviewed:** 43
- **Total SLOC:** ~3,500
- **Issues Found:** 22 (Critical: 6, Major: 10, Minor: 6)

## Critical Issues

### 1. Old `&&` / `||` Logical Operators - `test/test_core.ritz`

Lines 55, 56, 63, 64, 84, 343, 346, 349, 387, 388 use `&&` and `||` instead of the required `and` / `or` keywords.

```ritz
# WRONG (test_core.ritz:55-56, 84, etc.)
fn rect_contains_point(r: *Rect, px: i32, py: i32) -> i32
    if px >= r.x && px < r.x + r.width as i32
        if py >= r.y && py < r.y + r.height as i32

if a.x < b.x + b.width as i32
    if a.x + a.width as i32 > b.x
        if a.y < b.y + b.height as i32

if color_r(&black) as u32 != 0 || color_g(&black) as u32 != 0 || color_b(&black) as u32 != 0

# CORRECT
fn rect_contains_point(r: @Rect, px: i32, py: i32) -> bool
    p.x >= r.x and p.x < r.x + r.width as i32 and
    p.y >= r.y and p.y < r.y + r.height as i32
```

Also appears in `tools/render_test.ritz` lines 189, 61, 63, 65.

### 2. Rust-Style `&T` Reference Parameters (non-FFI) - `test/test_core.ritz`

Functions like `size_area`, `rect_contains_point`, `rect_intersects`, `rect_intersection`, `color_r/g/b/a`, `color_lerp` all use `*T` raw pointer parameters in application code where `@T` or value parameters should be used.

```ritz
# WRONG (test_core.ritz:51-56)
fn size_area(s: *Size) -> u32
fn rect_contains_point(r: *Rect, px: i32, py: i32) -> i32
fn rect_intersects(a: *Rect, b: *Rect) -> i32
fn color_r(c: *Color) -> u8

# CORRECT
fn size_area(s: Size) -> u64         # or s: @Size
fn rect_contains_point(r: @Rect, px: i32, py: i32) -> bool
fn rect_intersects(a: @Rect, b: @Rect) -> bool
fn color_r(c: @Color) -> u8
```

Callers then pass `&s`, `&r`, `&a`, `&b` etc. instead of `@s`, `@r`, etc. This is the Rust-style address-of pattern that is strictly prohibited outside of FFI.

### 3. `c"..."` String Prefixes - `test/test_core.ritz`, `test/test_damage.ritz`, `tools/render_test.ritz`

These files make heavy use of `c"..."` string literals for calls to `sys_write`. While low-level syscall code is borderline acceptable per the instructions (which note compiler use of `c"..."` is OK for FFI), these are **application-level test files**, not FFI/compiler internals. The strings should use `"...".as_cstr()`.

```ritz
# WRONG (test_core.ritz:360, test_damage.ritz:316-317, etc.)
sys_write(1, c"\n=== Prism Core Tests ===\n\n", 27)
sys_write(1, c"test_point_creation       ", result)
print_result(c"test_rect_new                           ", result)

# CORRECT
sys_write(1, "\n=== Prism Core Tests ===\n\n".as_cstr(), 27)
```

### 4. Raw Pointer `*u8` Parameters - `tools/render_test.ritz`

The entire render_test.ritz tool uses raw C-style pointer arithmetic (`*u8` buffers, `*(buffer + offset)` dereference syntax). This is appropriate only in FFI/kernel/unsafe contexts, not in a standalone test tool.

```ritz
# WRONG (render_test.ritz:188-200)
fn set_pixel(buffer: *u8, x: u32, y: u32, color: u32)
    *(buffer + offset) = ((color >> 16) as u32 % 256) as u8
fn fill_rect(buffer: *u8, x: u32, y: u32, w: u32, h: u32, color: u32)
fn draw_char(buffer: *u8, ch: u8, x: u32, y: u32, color: u32, scale: u32)
fn draw_string(buffer: *u8, text: *u8, text_len: i64, x: u32, y: u32, ...)
```

This tool predates the modern Ritz idioms and needs a complete rewrite or removal.

### 5. Old `&x` Address-Of Syntax - `test/test_core.ritz`

Function call sites use `&s`, `&r`, `&a`, `&b`, `&c`, `&black`, etc. (Rust-style address-of) throughout `test_core.ritz`.

```ritz
# WRONG (test_core.ritz:195-197, 229-291, 382-390)
if size_area(&s) != 200
if rect_contains_point(&r, 50, 50) != 1
if rect_intersects(&a, &b) != 1
rect_intersection(&a, &b, &i)
var gray: Color = color_lerp(&black, &white, 128)
if color_r(&c) as u32 != 255
```

### 6. Duplicate Struct Definitions - `src/damage.ritz`

`src/damage.ritz` redefines `Rect` and `DamageRegion` as standalone structs with procedural-style free functions (`rect_new`, `rect_zero`, `rect_union`, etc.) that duplicate functionality already in `src/types/rect.ritz` (which uses idiomatic `impl` blocks). Both `test/test_damage.ritz` and `test/simple_test.ritz` import and test this parallel implementation. This is an architectural inconsistency.

## Major Issues

### 7. Non-Idiomatic Procedural Style - `src/damage.ritz`

`src/damage.ritz` uses free-function procedural style (`damage_region_new()`, `damage_region_add()`, etc.) rather than `impl` blocks. All the equivalent types in `src/types/rect.ritz` and `src/compositor/damage.ritz` use `impl` blocks correctly.

```ritz
# WRONG (src/damage.ritz) - procedural style
pub fn damage_region_new() -> DamageRegion
pub fn damage_region_add(region:& DamageRegion, r: Rect)
pub fn rect_union(a: @Rect, b: @Rect) -> Rect

# CORRECT - use impl blocks as done in src/compositor/damage.ritz
impl DamageRegion
    pub fn new() -> DamageRegion
    pub fn add(self:&, r: Rect)
```

### 8. Non-Idiomatic Procedural Style - `test/test_core.ritz`

`test_core.ritz` redefines `Point`, `Size`, `Rect`, `Color` from scratch with procedural C-style helper functions instead of using the types from `src/types/`. This creates a maintenance burden and diverges from the project's idiomatic types.

### 9. Missing `?` Error Propagation - `src/text/font_manager.ritz`

`load_from_file` and `load_from_data` use nested `match` where `?` could be used.

```ritz
# CURRENT (font_manager.ritz:45-65)
pub fn load_from_file(self:&, path: StrView) -> Option<FontId>
    match load_font(path)
        Ok(font) =>
            ...
            Some(id)
        Err(_) =>
            None

# PREFERRED - or return Result<FontId, FontError> and use ?
pub fn load_from_file(self:&, path: StrView) -> Result<FontId, FontError>
    let font = load_font(path)?
    ...
    Ok(id)
```

### 10. `String` Allocations Where `StrView` Suffices - `src/text/font_manager.ritz`

Lines 54-55 convert a `StrView` path to `String` unconditionally with `String.from(path)` for storing in `LoadedFont.name` and `path`. If the name is only used for display/lookup, a `StrView` would suffice, though storing long-lived references may require `String` here - worth reviewing.

### 11. Duplicate `cos_f32` / `sin_f32` Stubs - `src/api/draw.ritz` and `src/api/layer.ritz`

Both `src/api/draw.ritz` (lines 371-377) and `src/api/layer.ritz` (lines 264-268) define identical placeholder `cos_f32` and `sin_f32` stub functions that return constant values. These should be in a shared math utility module.

### 12. Duplicate `min_i32` / `max_i32` helpers

`min_i32` and `max_i32` are defined independently in at least 4 files:
- `src/types/rect.ritz`
- `src/compositor/damage.ritz` (via `should_merge`)
- `src/backend/mock.ritz`
- `test/simple_test.ritz`
- `src/damage.ritz`

These should be imported from a single utility module.

### 13. Non-Idiomatic Test Runner Pattern - `test/test_damage.ritz` and `test/simple_test.ritz`

These test files use a manual `main()` test runner pattern with `sys_write` for output and manual fail counting, instead of the `[[test]]` attribute + `assert` pattern used consistently in all `src/` test files. The `[[test]]` pattern is far more idiomatic and maintainable.

### 14. Redundant `@` Parameter in `src/text/renderer.ritz` - Line 60

`render_text` calls `render_glyph_run` passing `@run` (taking a reference to a local), but `render_glyph_run`'s parameter is typed `run: GlyphRun` (value). This creates a mismatch that suggests the parameter type or the call site needs review.

```ritz
# render_text (line 60)
self.render_glyph_run(font, font_id, @run, x, y, ...)
# render_glyph_run signature (line 67)
fn render_glyph_run(..., run: GlyphRun, ...)  # expects value, passed reference
```

### 15. `ClientCommand` enum is private - `src/api/client.ritz`

`ClientCommand` (line 221) and its associated structs (`CreateSurfaceCmd`, `ResizeSurfaceCmd`, etc., lines 234-261) are declared without `pub`. Since they are used within `PrismClient`'s public methods, this may cause visibility issues, or at minimum is inconsistent with the rest of the API design.

### 16. `src/input/mod.ritz` not read (likely empty)

Let me note: `src/input/mod.ritz`, `src/text/mod.ritz`, `src/api/mod.ritz`, `src/backend/mod.ritz`, and `src/util/mod.ritz` are module re-export files which were listed but not fully inspected for any issues.

## Minor Issues

### 17. Naming: `usize` as Return Type - `src/text/font_manager.ritz`

`font_count` returns `usize` (line 119) while all other count methods in the project return `u64`. Should be consistent.

### 18. Module Documentation Missing - `src/damage.ritz`

`src/damage.ritz` lacks a proper module-level documentation comment header that explains the relationship between this module and `src/compositor/damage.ritz`.

### 19. `tools/angelo_render_test.ritz` Not Reviewed

The file `tools/angelo_render_test.ritz` was not reviewed as part of this pass. Given `render_test.ritz` uses old syntax, `angelo_render_test.ritz` should be audited separately.

### 20. Inconsistent `self` Parameter Style in `src/text/renderer.ritz`

`blit_glyph` (line 146) takes `self` (value copy, no `:&`) despite mutating `buffer` via a reference parameter. The mutation is via the passed reference, not `self`, so this is technically fine but inconsistent with similar methods in the codebase that would typically use `self:&`.

### 21. `damage_region_add` Uses `i64` Array Index for `u32` Count - `src/damage.ritz` and `test/simple_test.ritz`

```ritz
region.rects[region.count as i64] = r  # Unnecessary cast; u32 -> i64
```

The array index should ideally use `usize` or the appropriate cast. This is a minor type inconsistency.

### 22. Missing `pub` on `TextRenderer.render_glyph_run` - `src/text/renderer.ritz`

`render_glyph_run` is public (line 63: `pub fn render_glyph_run`) but it is called from `render_text` with a `@run` reference while the declared parameter is by value (see issue #14). Minor public API design concern.

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | ISSUE | `*T` raw pointers and `&x` address-of in test_core.ritz (non-FFI); src/ files are compliant |
| Reference Types (@) | ISSUE | Widespread `&x` / `*T` in test_core.ritz and render_test.ritz; src/ uses `@` consistently |
| Attributes ([[...]]) | OK | All `[[test]]` attributes correct throughout; no old `@test` usage found |
| Logical Operators | ISSUE | `&&` / `\|\|` in test_core.ritz (lines 55,56,63-65,84,343,346,349,387-388) and render_test.ritz (lines 189,61,63,65) |
| String Types | ISSUE | `c"..."` prefix used in test_core.ritz, test_damage.ritz, render_test.ritz (app-level, not FFI) |
| Error Handling | MAJOR | font_manager.ritz uses nested match where `?` is preferred; no silent error ignoring |
| Naming Conventions | OK | PascalCase types, snake_case functions/vars, SCREAMING_SNAKE constants - consistently correct |
| Code Organization | ISSUE | Duplicate geometry types in src/damage.ritz vs src/types/; duplicate math stubs; procedural style in damage.ritz |

## Files Needing Attention

**Critical - Must fix:**
- `/home/aaron/dev/ritz-lang/rz/projects/prism/test/test_core.ritz` - Pervasive `&&`/`||`, `*T`/`&x` patterns, `c"..."` strings throughout
- `/home/aaron/dev/ritz-lang/rz/projects/prism/test/test_damage.ritz` - `c"..."` strings, manual test runner, old `*T` in `print_result`
- `/home/aaron/dev/ritz-lang/rz/projects/prism/tools/render_test.ritz` - Raw pointer arithmetic, `||` operator, `*u8` buffers (entire file is pre-modern idiom)

**Major - Should fix:**
- `/home/aaron/dev/ritz-lang/rz/projects/prism/src/damage.ritz` - Duplicate types, procedural style; consider removing and redirecting imports to `src/types/rect.ritz`
- `/home/aaron/dev/ritz-lang/rz/projects/prism/src/text/font_manager.ritz` - Nested match, `usize` return type inconsistency
- `/home/aaron/dev/ritz-lang/rz/projects/prism/src/text/renderer.ritz` - `@run` vs value parameter mismatch
- `/home/aaron/dev/ritz-lang/rz/projects/prism/src/api/draw.ritz` - Duplicate `cos_f32`/`sin_f32` stubs
- `/home/aaron/dev/ritz-lang/rz/projects/prism/src/api/layer.ritz` - Duplicate `cos_f32`/`sin_f32` stubs
- `/home/aaron/dev/ritz-lang/rz/projects/prism/src/api/client.ritz` - Private `ClientCommand` visibility

**Clean (no issues):**
- `src/main.ritz`, `src/lib.ritz`
- `src/types/color.ritz`, `src/types/rect.ritz`, `src/types/id.ritz`, `src/types/mod.ritz`
- `src/compositor/mod.ritz`, `src/compositor/window.ritz`, `src/compositor/damage.ritz`
- `src/protocol/command.ritz`, `src/protocol/event.ritz`, `src/protocol/mod.ritz`
- `src/input/mouse.ritz`, `src/input/keyboard.ritz`, `src/input/router.ritz`
- `src/api/surface.ritz`, `src/api/image.ritz`, `src/api/text.ritz`, `src/api/layer.ritz` (minor stub issue)
- `src/backend/mock.ritz`
- `src/text/glyph_cache.ritz`
- `src/util/ppm.ritz`
- `test/test_compositor.ritz`, `test/test_color.ritz`, `test/test_rect.ritz`, `test/test_input.ritz`
- `test/test_render_commands.ritz`, `test/test_text_rendering.ritz`

## Recommendations

**Priority 1 (Critical - before merge):**
1. Rewrite `test/test_core.ritz` to use modern idioms: replace `&&`/`||` with `and`/`or`, replace `*T`/`&x` with `@T`/`@x`, replace `c"..."` with `"...".as_cstr()`, replace manual test runner with `[[test]]` + `assert`
2. Rewrite `test/test_damage.ritz` runner to use `[[test]]` pattern and replace `c"..."` strings
3. Evaluate `tools/render_test.ritz` - either rewrite in modern Ritz idioms or explicitly mark as a legacy/pre-spec tool with a prominent comment

**Priority 2 (Major - clean up):**
4. Remove `src/damage.ritz` or convert it to `impl` style and merge it with `src/compositor/damage.ritz`; update `test/test_damage.ritz` imports accordingly
5. Extract `cos_f32`/`sin_f32` stubs to a shared `src/util/math.ritz` module; import in `api/draw.ritz` and `api/layer.ritz`
6. Extract `min_i32`/`max_i32` to `src/util/math.ritz` as well; remove the 5+ duplicate definitions
7. Update `font_manager.ritz` to return `Result<FontId, FontError>` and use `?`; fix `font_count` return type from `usize` to `u64`
8. Add `pub` to `ClientCommand` and its related structs in `src/api/client.ritz`
9. Resolve the `@run` vs value mismatch in `src/text/renderer.ritz`

**Priority 3 (Minor - polish):**
10. Add module documentation header to `src/damage.ritz`
11. Audit `tools/angelo_render_test.ritz` for the same patterns found in `render_test.ritz`
12. Standardize array index casts: replace `region.count as i64` with appropriate `usize` casts

---

*LARB Review conducted 2026-02-17 per LARB Review Instructions v3.0*
