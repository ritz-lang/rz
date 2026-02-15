# Angelo - Font Rendering

Font loading and rendering for Prism.

---

## Project Overview

Angelo is a font library that handles loading, parsing, and rendering fonts. Built for Prism (the display server) but usable standalone.

### Responsibilities

- **Font Loading** — TrueType/OpenType parsing, font file discovery
- **Glyph Rendering** — Rasterization, hinting, antialiasing
- **Text Shaping** — Unicode handling, ligatures, kerning
- **Font Caching** — Glyph cache, font metric cache

### Non-Responsibilities

Angelo does NOT handle:
- Window management (use Prism)
- Layout/text wrapping (use Iris)
- UI widgets (separate libraries)

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    PRISM / IRIS                      │
│               (Display / Rendering)                  │
└───────────────────────┬─────────────────────────────┘
                        │ (render text)
                        ▼
┌─────────────────────────────────────────────────────┐
│                     ANGELO                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │   Loader    │ │  Shaper     │ │ Rasterizer  │   │
│  │ TTF/OTF/etc │ │  Unicode    │ │   Glyphs    │   │
│  └─────────────┘ └─────────────┘ └─────────────┘   │
│  ┌─────────────────────────────────────────────┐   │
│  │              Glyph Cache                     │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## Ritz Coding Guidelines

### Parameter Syntax

| Syntax | Meaning | Usage |
|--------|---------|-------|
| `x: T` | Const borrow | Default (~70% of params) |
| `x:& T` | Mutable borrow | When modifying the value |
| `x:= T` | Move ownership | When taking ownership |

**NO SPACE between `:` and modifier!** Write `:&` not `: &`

```ritz
fn load_font(path: StrView) -> Result<Font, Error>
fn render_glyph(font: Font, codepoint: u32, cache:& GlyphCache) -> Glyph
fn shape_text(font: Font, text: StrView) -> Vec<ShapedGlyph>
```

### Reference Syntax

| Syntax | Meaning |
|--------|---------|
| `@x` | Take immutable reference |
| `@&x` | Take mutable reference |
| `@T` | Immutable reference type |
| `@&T` | Mutable reference type |

### Logical Operators

Use **words**, not symbols:
- `and` not `&&`
- `or` not `||`
- `not` not `!`

```ritz
if font.is_valid() and glyph.has_outline()
    render(glyph)
```

### String Literals

```ritz
"hello"              # StrView (zero-copy) — DEFAULT
String.from("hello") # String (heap-allocated)
c"hello"             # *u8 for FFI ONLY
```

### Testing

```ritz
[[test]]
fn test_font_loading() -> i32
    let font = load_font("test/fixtures/DejaVuSans.ttf").unwrap()
    assert font.family_name() == "DejaVu Sans"
    0
```

---

## Core Doctrines

### No Concessions Doctrine

> "Never make concessions for the language — we are MAKING the language."

If Ritz can't express something cleanly, fix Ritz. Don't work around limitations.

### Test-Driven Development

1. Write failing tests first
2. Implement to make tests pass
3. Refactor with confidence
4. All tests must pass before committing

---

## Project Structure

```
angelo/
├── src/
│   ├── loader/
│   │   ├── ttf.ritz       # TrueType parser
│   │   ├── otf.ritz       # OpenType parser
│   │   └── discovery.ritz # Font file discovery
│   ├── shaper/
│   │   ├── unicode.ritz   # Unicode handling
│   │   ├── ligatures.ritz # Ligature substitution
│   │   └── kerning.ritz   # Kerning pairs
│   ├── raster/
│   │   ├── outline.ritz   # Outline rendering
│   │   ├── hinting.ritz   # Font hinting
│   │   └── antialias.ritz # Antialiasing
│   └── cache.ritz         # Glyph caching
├── tests/
└── ritz.toml
```

---

## Style Guidelines

- **Indentation:** 4 spaces (no tabs)
- **Line length:** 100 characters max
- **Naming:** `snake_case` for functions, `PascalCase` for types
- **Immutable by default:** Use `let`, only `var` when mutation needed
- **Use `defer`** for resource cleanup

---

*Part of the Ritz ecosystem. See `larb/AGENT.md` for full guidelines.*
