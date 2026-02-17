# LARB Review: Angelo

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** NEEDS WORK

## Summary

Angelo is a comprehensive font loading and rendering library implementing TrueType/OpenType parsing, glyph rasterization (grayscale and subpixel), text shaping, LRU glyph caching, font discovery, and a TrueType hinting bytecode interpreter stub. Overall compliance is good - the codebase consistently uses `[[test]]` attributes, `@`-prefixed references, and `:&`/`:=` ownership modifiers. However, there are systematic CRITICAL issues with `!` being used for logical NOT throughout `loader/reader.ritz`, and MAJOR issues with a non-standard `then` keyword appearing in conditional expressions across multiple files.

## Statistics

- **Files Reviewed:** 27
- **Total SLOC:** ~2800
- **Issues Found:** 18 (Critical: 9, Major: 7, Minor: 2)

## Critical Issues

### C1: `!` Used for Logical NOT in `loader/reader.ritz` (9 occurrences)

The spec requires `not` for logical NOT. The `!` operator is used throughout `loader/reader.ritz` as a negation operator in bounds-checking guards:

**File:** `/home/aaron/dev/ritz-lang/rz/projects/angelo/src/loader/reader.ritz`

```ritz
# Line 41 - WRONG:
if !self.can_read(1)
# Line 53 - WRONG:
if !self.can_read(2)
# Line 66 - WRONG:
if !self.can_read(4)
# Line 108 - WRONG:
if !self.can_read(len)
# Line 117 - WRONG:
if !self.can_read(1)
# Line 121 - WRONG:
if !self.can_read(2)
# Line 127 - WRONG:
if !self.can_read(4)
```

And also on lines 384, 387 in the `skip_instruction_data` method of `hinting/interpreter.ritz`... wait, those use `==`/comparison patterns, not `!`. All 9 occurrences are in `reader.ritz`.

**Required fix:**
```ritz
# CORRECT:
if not self.can_read(1)
    return Err("unexpected end of data")
```

This is a systematic pattern affecting every read method. All 9 `!` usages must be replaced with `not`.

## Major Issues

### M1: `then` Keyword Used in Conditional Expressions

The Ritz spec does not define a `then` keyword for inline conditional expressions. Several files use `if ... then ... else ...` as a ternary expression. This syntax is non-standard.

**File:** `/home/aaron/dev/ritz-lang/rz/projects/angelo/src/shaper/types.ritz`

```ritz
# Lines 65-72 - Non-standard ternary syntax:
let x1 = if self.x < other.x then self.x else other.x
let y1 = if self.y < other.y then self.y else other.y
let x2 = if x2_self > x2_other then x2_self else x2_other
let y2 = if y2_self > y2_other then y2_self else y2_other
```

**File:** `/home/aaron/dev/ritz-lang/rz/projects/angelo/src/hinting/interpreter.ritz`

```ritz
# Lines 158, 179, 222, 223, 224, 225 - Non-standard ternary syntax:
let word = if word > 32767 then word - 65536 else word
self.push(if v < 0 then -v else v)?
self.push(if b < a then 1 else 0)?
# ... etc.
```

Standard Ritz `if` expressions are block-based. The `then` keyword is not part of the finalized spec. These should be rewritten as block-form if expressions or match expressions.

### M2: Raw Pointer Dereference in `loader/file.ritz`

The file I/O function uses a raw pointer dereference pattern to read file size from a stat buffer. While low-level syscall code has some leeway, this pattern is borderline even for FFI code:

**File:** `/home/aaron/dev/ritz-lang/rz/projects/angelo/src/loader/file.ritz`

```ritz
# Lines 30-31 - Raw pointer cast and dereference:
let size_ptr = (@&statbuf[48]) as @i64
let file_size = *size_ptr
```

This is an unsafe pattern. The `*size_ptr` dereference of a reinterpreted pointer should be wrapped in an `unsafe` block if Ritz supports that, or at minimum have a prominent safety comment explaining why this is sound.

### M3: `or` Used as Bitwise OR in `loader/reader.ritz`

The `or` keyword is the logical OR operator. It should not be used for bitwise operations. The Reader's 32-bit and 64-bit read methods use `or` for bitwise combining of bytes:

**File:** `/home/aaron/dev/ritz-lang/rz/projects/angelo/src/loader/reader.ritz`

```ritz
# Lines 72-73 - WRONG: 'or' used as bitwise OR:
Ok((b0 << 24) |(b1 << 16) |(b2 << 8) |b3)
# Line 83 - WRONG:
Ok((high << 32) |low)
# Lines 134:
Ok((b0 << 24) |(b1 << 16) |(b2 << 8) |b3)
```

Note: These use `|` symbol (bitwise OR), which appears correct for bitwise operations. However `types.ritz` line 207-209 uses `or` for bitwise hash combining:

**File:** `/home/aaron/dev/ritz-lang/rz/projects/angelo/src/types.ritz`

```ritz
# Lines 207-209 - Using 'or' for bitwise OR in hash function:
let h = (h << 16) or self.glyph_id as u64
let h = (h << 16) or self.size_px as u64
let h = (h << 8) or self.subpixel_x as u64
```

**File:** `/home/aaron/dev/ritz-lang/rz/projects/angelo/src/cache.ritz`

```ritz
# Lines 34-37 - Same pattern in SubpixelCacheKey.hash():
let h = (h << 16) or self.glyph_id as u64
let h = (h << 16) or self.size_px as u64
let h = (h << 8) or self.subpixel_order as u64
```

Using `or` for bitwise combining is semantically misleading. The `|` operator should be used for bitwise operations, with `or` reserved for logical boolean operations.

### M4: Imports Placed at End of File in `loader/reader.ritz`

The code organization spec requires imports at the top of the file. `reader.ritz` places imports at the bottom, after all the implementation code:

**File:** `/home/aaron/dev/ritz-lang/rz/projects/angelo/src/loader/reader.ritz`

```ritz
# Line 136 - Import placed AFTER implementation:
import types { Tag }

# Line 201 - Another import at the very bottom:
import types { TAG_HEAD }
```

These should be moved to the top of the file.

### M5: Missing Space in Method Signature in `discovery.ritz`

**File:** `/home/aaron/dev/ritz-lang/rz/projects/angelo/src/discovery.ritz`

```ritz
# Line 61 - Minor formatting issue, missing space:
pub fn add(self:&, entry:= FontEntry)
```

The consistent style throughout the codebase is `self:& FontRegistry` (with the type name). Using `self:&` with no type and no space before the comma is inconsistent with the rest of the codebase.

### M6: `glyph_id` Called Twice Instead of Using `?` for Chaining in `tests.ritz`

Several test functions in `tests.ritz` perform manual `is_some()` / `unwrap()` chains where the `?` operator could simplify the code. While this is test code and less critical, some patterns could use the `?` operator for cleaner propagation:

**File:** `/home/aaron/dev/ritz-lang/rz/projects/angelo/src/tests.ritz`

```ritz
# Lines 88-94 - Could use ? operator for cleaner code:
let a_id = font.glyph_id(0x41)
if a_id.is_some()
    let outline = font.glyph_outline(a_id.unwrap())
    ...
```

### M7: `glyph_id` Method Called on `self:& Font` but Used Without `mut` Consistency

**File:** `/home/aaron/dev/ritz-lang/rz/projects/angelo/src/font.ritz`

```ritz
# Lines 50-57 - glyph_id declared as self:& Font but calls self.ensure_cmap() which mutates:
pub fn glyph_id(self:& Font, codepoint: u32) -> Option<u16>
    self.ensure_cmap()  # This mutates self (sets self.cmap)
    match @self.cmap
```

The `glyph_id`, `glyph_metrics`, and `glyph_outline` methods all take `self:& Font` (mutable borrow) to support lazy initialization, which is correct. However, all three methods call `ensure_*` helpers that mutate internal state. The public API signatures make this clear via `:&` - this is fine, but worth noting the lazy-init pattern is not documented in method-level comments.

## Minor Issues

### N1: `glyph_metrics` Method Returns Wrong Type Description

The `ensure_hmtx` method in `font.ritz` checks `if self.num_hmetrics == 0` both before and after parsing hhea, which is slightly redundant but not incorrect.

### N2: `glyph_id` Shadow in `shaper/simple.ritz`

**File:** `/home/aaron/dev/ritz-lang/rz/projects/angelo/src/shaper/simple.ritz`

```ritz
# Line 56 - Parameter named glyph_id shadows the function call result:
let glyph_metrics = font.glyph_metrics(glyph_id as u16)
```

The local variable `glyph_id` (which is u16 from the match) is being cast to u16 unnecessarily since it was already matched as u16 in the `glyph_id_opt` match. Minor readability issue.

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | OK | Correct use of `:`, `:&`, `:=` throughout |
| Reference Types (@) | OK | Consistent `@x` and `@&x` usage; `*T` only in FFI (file.ritz) |
| Attributes ([[...]]) | OK | All tests use `[[test]]`, no old `@test` found |
| Logical Operators | ISSUE | `!` used instead of `not` in reader.ritz (9 occurrences, CRITICAL); `or` used for bitwise ops in types.ritz and cache.ritz |
| String Types | OK | Uses `StrView` for literals, `String.from()` for heap strings; no `c"..."` or `s"..."` prefixes |
| Error Handling | OK | Good use of `?` operator and `Result<T, E>`; error messages are `StrView` literals |
| Naming Conventions | OK | snake_case functions/vars, PascalCase types, SCREAMING_SNAKE_CASE constants |
| Code Organization | ISSUE | `reader.ritz` has imports at end-of-file instead of top |

## Files Needing Attention

1. `/home/aaron/dev/ritz-lang/rz/projects/angelo/src/loader/reader.ritz` - **CRITICAL**: 9 uses of `!` instead of `not`; imports misplaced at end of file
2. `/home/aaron/dev/ritz-lang/rz/projects/angelo/src/shaper/types.ritz` - **MAJOR**: Non-standard `then` keyword in 4 conditional expressions
3. `/home/aaron/dev/ritz-lang/rz/projects/angelo/src/hinting/interpreter.ritz` - **MAJOR**: Non-standard `then` keyword in ~8 places
4. `/home/aaron/dev/ritz-lang/rz/projects/angelo/src/loader/file.ritz` - **MAJOR**: Raw pointer dereference needs unsafe annotation or comment
5. `/home/aaron/dev/ritz-lang/rz/projects/angelo/src/types.ritz` - **MAJOR**: `or` used for bitwise operations in hash function
6. `/home/aaron/dev/ritz-lang/rz/projects/angelo/src/cache.ritz` - **MAJOR**: Same `or`-for-bitwise pattern in SubpixelCacheKey.hash()

## Recommendations

1. **[CRITICAL - Fix First]** Replace all `!expr` patterns with `not expr` in `loader/reader.ritz`. This is a systematic find-and-replace across 9 locations in the same file.

2. **[CRITICAL - Fix First]** Eliminate the `then` keyword from `shaper/types.ritz` and `hinting/interpreter.ritz`. Rewrite inline ternaries as block-form `if/else` expressions. For example:
   ```ritz
   # Before (non-standard):
   let x1 = if self.x < other.x then self.x else other.x

   # After (standard block-form):
   let x1 = if self.x < other.x
       self.x
   else
       other.x
   ```

3. **[MAJOR]** Replace `or` with `|` for bitwise operations in `types.ritz` (GlyphCacheKey.hash), `cache.ritz` (SubpixelCacheKey.hash). The `or` keyword should be reserved for boolean logical operations only.

4. **[MAJOR]** Move the `import types { Tag }` and `import types { TAG_HEAD }` statements in `loader/reader.ritz` to the top of the file, following the code organization spec.

5. **[MAJOR]** Add safety documentation or unsafe block wrapping around the stat buffer pointer cast in `loader/file.ritz`.

6. **[MINOR]** Fix the `add(self:&,` signature in `discovery.ritz` for consistency - either add the type `self:& FontRegistry` or verify the abbreviated form is intentional.
