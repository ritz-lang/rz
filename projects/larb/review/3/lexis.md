# LARB Review: Lexis

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** NEEDS WORK

## Summary

Lexis is a streaming HTML5 and CSS parser library for the Tempest web browser, implementing the HTML5 tokenizer, tree builder, CSS Syntax Level 3 tokenizer and parser, selector matching, and cascade algorithm. The codebase is large (~8100 lines across 28 files) and architecturally sound. It passes well on ownership modifiers and logical operators but has two critical issues: raw pointer usage (`*T`) in non-FFI contexts and the presence of old `@test` attribute syntax in the tree builder comment (harmless) — more critically, `StartTagToken.attrs` and `FormattingEntry.attrs` store `*Attribute` raw pointers instead of proper borrows, and the `selector_map_add_rule` function signature omits the `source_order` argument. Several naming convention issues exist in `cascade.ritz` (a PascalCase function name `Declaration_property`).

## Statistics

- **Files Reviewed:** 28
- **Total SLOC:** ~8100 lines
- **Issues Found:** 14 (Critical: 2, Major: 6, Minor: 6)

## Critical Issues

### CRIT-1: Raw Pointer Fields in Non-FFI Structs (`lib/html/token.ritz`, `lib/html/tree_builder.ritz`)

`StartTagToken.attrs` uses `*Attribute` (raw pointer) and `FormattingEntry.attrs` uses `*Attribute`. These are application-level HTML parsing structs, not FFI wrappers. The spec says `*T` is for FFI/unsafe only. These should be `@Attribute` (immutable reference) or `@&Attribute` (mutable reference).

```ritz
# WRONG - lib/html/token.ritz line 40
pub struct StartTagToken
    name: StrView
    attrs: *Attribute       # Raw pointer - should be @Attribute or @&Attribute
    attr_count: u32
    self_closing: i32

# WRONG - lib/html/tree_builder.ritz line 63-64
pub struct FormattingEntry
    kind: i32
    tag: Tag
    attrs: *Attribute       # Same issue
    attr_count: u32
```

The `push_formatting_element` function on line 159 of `tree_builder.ritz` also takes `attrs: *Attribute`. This pattern propagates throughout the tree builder. The `insert_html_element` call at line 280 passes `null` for attrs, which only works because of the raw pointer type.

### CRIT-2: `selector_map_add_rule` Signature Mismatch (`lib/style/selector_map.ritz`)

The public function `selector_map_add_rule` on line 116 takes only `(map:& SelectorMap, rule: StyleRule)` — two parameters — but the caller in `lib/lexis.ritz` on lines 143-147 passes a third argument `i` (the rule index):

```ritz
# lib/lexis.ritz line 143 - passes 3 args
selector_map_add_rule(engine.ua_map, rule, i)

# lib/style/selector_map.ritz line 116 - only takes 2 params
pub fn selector_map_add_rule(map:& SelectorMap, rule: StyleRule)
```

This would fail to compile. The rule index for source ordering is needed but the function signature ignores it, instead deriving source order from within the `StyleRule`. The caller is passing an extra argument that isn't accepted. One of the two needs to change.

## Major Issues

### MAJ-1: `Declaration_property` Naming Convention (`lib/style/cascade.ritz`)

Line 250 defines a function with PascalCase breaking naming rules:

```ritz
# WRONG - should be snake_case
fn Declaration_property(decl: Declaration) -> StrView
```

Should be `declaration_property` or `decl_get_property`. This is a private function but still violates naming conventions.

### MAJ-2: `selector_map_add_rule` API takes `StyleRule` not individual selectors

The function at `selector_map.ritz` line 116 iterates over `rule.selectors.selector_count` but the `StyleRule` struct has a `source_order` field. However `lexis.ritz` is passing a separate `i` counter. The API is inconsistent — either the `StyleRule` should carry its own order (it does via `source_order`) and the caller should not pass `i`, or the API should accept an order override. Currently both exist simultaneously.

### MAJ-3: `bool` Return Type in `tag.ritz` (`lib/dom/tag.ritz`)

Functions `tag_is_void`, `tag_is_raw_text`, `tag_is_escapable_raw_text`, `tag_is_formatting`, `tag_closes_previous`, and `tag_is_special` all return `bool` instead of `i32`. The rest of the codebase consistently uses `i32` with `return 1`/`return 0` for boolean results. The use of `true`/`false` literals also appears only in this file. This is an inconsistency — either the whole codebase should adopt `bool` or `tag.ritz` should follow the `i32` convention used elsewhere.

```ritz
# INCONSISTENT - lib/dom/tag.ritz line 158
pub fn tag_is_void(tag: Tag) -> bool   # uses bool + true/false
    match tag
        Tag.Area => true
        ...

# REST OF CODEBASE - e.g. lib/html/tokenizer.ritz line 101
fn is_ascii_alpha(c: u8) -> i32        # uses i32 + return 1/return 0
```

### MAJ-4: `emit_element_start` Signature Uses Fixed-Size Array Instead of Pointer/Reference (`lib/event.ritz`)

Line 182 of `event.ritz`:

```ritz
pub fn emit_element_start(handler:& EventHandler, tag: Tag, attrs: [64]Attribute, attr_count: u32, self_closing: i32)
```

This passes a `[64]Attribute` by value (copy), which is a 64-element array copy on every element start event. This is a performance hazard in a streaming parser. The tree builder calls this with `null` in some places (lines 280, 321 of `tree_builder.ritz`) but the signature accepts a fixed array, not a pointer. This is inconsistent and suggests the API was designed for pointer-based attrs (`*Attribute`) but was changed to array without updating all callsites.

### MAJ-5: `apply_inheritance` Passes Mutable Borrow but `matched_rule_list_sort` Takes Ownership (`lib/style/cascade.ritz`)

Line 126 in `cascade_apply`:
```ritz
var sorted = matched          # copies matched
matched_rule_list_sort(sorted)  # sorts the copy
```

The function receives `matched: MatchedRuleList` (const borrow / copy) and then copies it to sort. While not syntactically wrong, this is wasteful. The function should take `matched:= MatchedRuleList` (move) or `matched:& MatchedRuleList` (mutable borrow) to sort in place and avoid a copy of a potentially 256-element array.

### MAJ-6: Old `@test` Pattern Mentioned in Comment (Event Handler Trait Usage)

`lib/event.ritz` lines 98-106 contain a documentation comment example that uses the old `@test`-style syntax in its comments (as part of a usage example showing `impl EventHandler for TempestDomBuilder` which is fine), but more importantly the EventHandler trait usage example in the module header shows `self:&` which is correct. No actual `@test` attributes appear anywhere — all test functions correctly use `[[test]]`. This is PASS but worth noting the trait `EventHandler` comment example is clean.

## Minor Issues

### MIN-1: `selector_map_add_rule` Ignores Second Argument (Source Order)

In `selector_map.ritz`, `rule_entry_new` at line 30-36 uses `rule.source_order` from the `StyleRule` directly, which is set during `css_parse_stylesheet`. But the `style_engine_add_stylesheet` in `lexis.ritz` passes an additional `i` counter. Since the StyleRule already has `source_order`, the extra argument should be dropped from the caller, not the callee.

### MIN-2: Magic Number `128` in `cascade.ritz` Line 151

```ritz
if found == 0 and result.count < 128
```

The value `128` is used as a hardcoded limit but `DeclarationBlock` has `const MAX_DECLARATIONS: u32 = 128` defined in `rule.ritz`. Use the named constant, or reference it via import.

### MIN-3: Incomplete `selector_map.ritz` — `selector_map_add_rule` Takes Wrong Argument Type

`selector_map_add_rule` takes `rule: StyleRule` but `StyleRule` is defined in `lib/css/rule.ritz`, while `rule_entry_new` in `selector_map.ritz` takes a `ComplexSelector`. The function signature implies it gets a full `StyleRule` but the docstring says it should index rules by key selector. The API shape is inconsistent with what `lexis.ritz` expects (passing 3 args vs 2).

### MIN-4: `lib/style/cascade.ritz` Has Private Duplicate Value Constructors

`cascade.ritz` defines its own private versions of `css_value_keyword`, `css_value_length`, `css_value_number`, and `copy_str` (lines 316-360) that duplicate functions already exported from `lib/css/value.ritz`. These should be removed in favor of importing the canonical versions.

```ritz
# cascade.ritz line 316 - duplicates value.ritz
fn css_value_keyword(kw: StrView) -> CssValue
    ...

# Should instead import from lib.css.value:
import lib.css.value { CssValue, css_value_keyword, css_value_length, css_value_number, CSS_VALUE_KEYWORD, ... }
```

### MIN-5: `lib/html/tree_builder.ritz` — Missing `@` in some dereferences

Line 724 of `tree_builder.ritz`:
```ritz
let tag = current_node(@tb)
```
This is correct (`@tb` takes reference). However lines 145, 853, 854 call `current_node(@tb)` in some places but `current_node(tb)` elsewhere (e.g. line 135 `fn current_node(tb: TreeBuilder)`). The function takes a const borrow but it receives the struct value directly from stack copies in some calls. The `@` usage is consistent where needed. This is a style note only.

### MIN-6: File Organization — `lib/lexis.ritz` Has Imports After Re-exports

Per the code organization spec, imports should come before public re-exports, or at minimum be grouped at the top. `lib/lexis.ritz` places `pub import` statements (lines 28-53) before internal `import` statements (lines 66-79), which is the correct order (re-exports first, then private imports). However, the `pub const VERSION_*` block (lines 58-60) is placed between re-exports and imports. Convention calls for constants after imports. This is minor.

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | OK | `:&` and `:=` used correctly throughout; const borrows are sigil-free |
| Reference Types (@) | ISSUE | `*Attribute` used in `StartTagToken`, `FormattingEntry`, `push_formatting_element` — non-FFI structs using raw pointers |
| Attributes ([[...]]) | OK | All test functions use `[[test]]` correctly; no `@test` or `@inline` found |
| Logical Operators | OK | `and`, `or`, `not` keywords used throughout; no `&&`, `\|\|`, `!` found in logic |
| String Types | OK | `StrView` used as default string type throughout; no `s"..."` or `c"..."` prefixes in application code |
| Error Handling | OK | No Result types used (low-level parser returns values directly); consistent with the style |
| Naming Conventions | ISSUE | `Declaration_property` (PascalCase function) in `cascade.ritz`; otherwise consistent snake_case |
| Code Organization | OK | Files are well-structured with clear section headers; minor re-export/const ordering issue |

## Files Needing Attention

1. **`/home/aaron/dev/ritz-lang/rz/projects/lexis/lib/html/token.ritz`** — `StartTagToken.attrs: *Attribute` (CRIT-1)
2. **`/home/aaron/dev/ritz-lang/rz/projects/lexis/lib/html/tree_builder.ritz`** — `FormattingEntry.attrs: *Attribute`, `push_formatting_element` raw pointer parameter (CRIT-1)
3. **`/home/aaron/dev/ritz-lang/rz/projects/lexis/lib/lexis.ritz`** — `selector_map_add_rule` called with 3 args vs 2-arg signature (CRIT-2)
4. **`/home/aaron/dev/ritz-lang/rz/projects/lexis/lib/style/selector_map.ritz`** — API mismatch with callers (CRIT-2, MAJ-2)
5. **`/home/aaron/dev/ritz-lang/rz/projects/lexis/lib/style/cascade.ritz`** — `Declaration_property` naming (MAJ-1), duplicate value constructors (MIN-4)
6. **`/home/aaron/dev/ritz-lang/rz/projects/lexis/lib/dom/tag.ritz`** — `bool` return type inconsistency (MAJ-3)
7. **`/home/aaron/dev/ritz-lang/rz/projects/lexis/lib/event.ritz`** — `emit_element_start` takes `[64]Attribute` by value (MAJ-4)

## Recommendations

Priority order for fixes:

1. **(CRIT-1)** Replace `*Attribute` with `@Attribute` in `StartTagToken` and `FormattingEntry`. Update `push_formatting_element` to take `attrs: @Attribute`. The `null` initialization sites need to be refactored — consider making `attr_count: 0` sufficient to indicate "no attributes" and use a sentinel reference or `Option`-like pattern.

2. **(CRIT-2)** Fix the `selector_map_add_rule` API mismatch. The `StyleRule` already has `source_order` set by the parser. Remove the third `i` argument from the three call sites in `lexis.ritz` and let the function use `rule.source_order` directly (which it already does via `rule_entry_new`).

3. **(MAJ-1)** Rename `Declaration_property` to `decl_get_property` or `declaration_property_str` in `cascade.ritz`.

4. **(MAJ-3)** Decide on a consistent boolean return convention. The cleanest fix is to change `tag.ritz` functions to return `i32` with `1`/`0`, consistent with the rest of the codebase. Alternatively, adopt `bool` everywhere — but that requires broader changes.

5. **(MAJ-4)** Change `emit_element_start` to take `attrs: @Attribute` (a reference to the first element of the array) rather than a fixed-size array copy. Update `ElementStartEvent.attrs` similarly.

6. **(MIN-4)** Remove duplicate value constructors from `cascade.ritz` and import them from `lib.css.value`.

7. **(MIN-2)** Replace the magic `128` with the named constant `MAX_DECLARATIONS` from `rule.ritz`.
