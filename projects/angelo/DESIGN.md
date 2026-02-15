# Angelo Design Document

Font loading and rendering library for Prism.

---

## Overview

Angelo handles everything font-related:
- **Loading**: Parse TrueType/OpenType font files
- **Shaping**: Unicode handling, ligatures, kerning
- **Rasterizing**: Convert outlines to pixels
- **Caching**: Efficient glyph storage

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          PRISM                                       │
│                    (RenderCommand.DrawText)                          │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          ANGELO                                      │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                        FontManager                             │  │
│  │  - Font discovery (system fonts, custom fonts)                │  │
│  │  - Font loading on demand                                      │  │
│  │  - Font handles (lightweight references)                       │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                │                                     │
│           ┌────────────────────┼────────────────────┐               │
│           ▼                    ▼                    ▼               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │     Loader      │  │     Shaper      │  │   Rasterizer    │     │
│  │                 │  │                 │  │                 │     │
│  │  - TTF parser   │  │  - Codepoint    │  │  - Outline      │     │
│  │  - OTF parser   │  │    to glyph     │  │    rasterizer   │     │
│  │  - Table access │  │  - Ligatures    │  │  - Hinting      │     │
│  │  - Glyph data   │  │  - Kerning      │  │  - Antialiasing │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
│           │                    │                    │               │
│           └────────────────────┼────────────────────┘               │
│                                ▼                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                       GlyphCache                               │  │
│  │  - Rasterized glyph bitmaps                                   │  │
│  │  - Keyed by (font_id, glyph_id, size, subpixel_offset)       │  │
│  │  - LRU eviction                                                │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## TTF File Format

TrueType fonts are table-based. Key tables:

| Table | Description |
|-------|-------------|
| `head` | Font header (units per em, bounds, flags) |
| `hhea` | Horizontal header (ascender, descender, line gap) |
| `hmtx` | Horizontal metrics (advance width, left side bearing) |
| `cmap` | Character to glyph mapping (Unicode → glyph ID) |
| `maxp` | Maximum profile (number of glyphs) |
| `loca` | Glyph location index (offsets into glyf) |
| `glyf` | Glyph outlines (the actual shapes) |
| `name` | Naming table (font name, family, etc.) |
| `kern` | Kerning pairs (optional) |
| `GPOS` | OpenType positioning (advanced kerning) |
| `GSUB` | OpenType substitution (ligatures) |

### File Structure

```
┌──────────────────────────────────────┐
│         Offset Table                  │
│  - sfntVersion (0x00010000 for TTF)  │
│  - numTables                          │
│  - searchRange, entrySelector, etc.  │
├──────────────────────────────────────┤
│         Table Directory               │
│  - tag (4 bytes, e.g., "cmap")       │
│  - checksum                           │
│  - offset (into file)                │
│  - length                             │
├──────────────────────────────────────┤
│         Table Data                    │
│  - Each table at its offset          │
│  - Tables can be in any order        │
└──────────────────────────────────────┘
```

---

## Data Flow: Character → Pixels

```
"Hello" → Unicode codepoints
        ↓
   [0x48, 0x65, 0x6C, 0x6C, 0x6F]
        ↓
   ┌─────────────────────────────┐
   │         CMAP Table          │ → Unicode → Glyph ID
   └─────────────────────────────┘
        ↓
   [GlyphID: 43, 72, 79, 79, 82]
        ↓
   ┌─────────────────────────────┐
   │         GSUB Table          │ → Ligature substitution
   └─────────────────────────────┘   (e.g., "ff" → single glyph)
        ↓
   ┌─────────────────────────────┐
   │         GPOS/KERN           │ → Kerning adjustments
   └─────────────────────────────┘
        ↓
   ┌─────────────────────────────┐
   │         GLYF Table          │ → Get outline data
   └─────────────────────────────┘
        ↓
   Bezier curves + contours
        ↓
   ┌─────────────────────────────┐
   │        Rasterizer           │ → Scanline fill
   └─────────────────────────────┘
        ↓
   Pixel bitmap (alpha values)
```

---

## Core Types

```ritz
# Lightweight handle to a loaded font
struct FontHandle
    id: u32

# Font metrics (from hhea/head tables)
struct FontMetrics
    units_per_em: u16
    ascender: i16
    descender: i16
    line_gap: i16
    bbox: Rect

# A single glyph
struct Glyph
    id: u16
    advance_width: u16
    left_side_bearing: i16
    outline: GlyphOutline    # bezier curves

struct GlyphOutline
    contours: Vec<Contour>
    bounds: Rect

struct Contour
    points: Vec<OutlinePoint>

struct OutlinePoint
    x: i16
    y: i16
    on_curve: bool           # true = line endpoint, false = control point

# Rasterized glyph (cached)
struct RasterizedGlyph
    bitmap: Vec<u8>          # alpha values (0-255)
    width: u32
    height: u32
    bearing_x: i32           # offset from origin
    bearing_y: i32
    advance: u32

# Cache key
struct GlyphCacheKey
    font_id: u32
    glyph_id: u16
    size_px: u16
    subpixel_x: u8           # 0-3 for 1/4 pixel positioning
```

---

## Parsing Strategy

### Zero-Copy Where Possible

The font file is memory-mapped. Tables are accessed via offsets:

```ritz
struct FontFile
    data: @[u8]              # immutable reference to mapped data
    tables: HashMap<Tag, TableEntry>

struct TableEntry
    offset: u32
    length: u32

# Reading is just pointer arithmetic
fn read_table(font: FontFile, tag: Tag) -> Option<@[u8]>
    match font.tables.get(tag)
        Some(entry) =>
            let start = entry.offset as usize
            let end = start + entry.length as usize
            Some(@font.data[start..end])
        None =>
            None
```

### Lazy Loading

Don't parse everything upfront:
1. Parse offset table and table directory immediately
2. Parse `head`, `hhea`, `maxp` on load (essential metrics)
3. Parse `cmap` on load (need character mapping)
4. Parse `loca` on first glyph access
5. Parse individual glyphs from `glyf` on demand
6. Parse `kern`/`GPOS` only when shaping

---

## Testing Strategy

### Unit Tests

```ritz
[[test]]
fn test_parse_offset_table() -> i32
    let data = include_bytes("fixtures/DejaVuSans.ttf")
    let header = parse_offset_table(data).unwrap()
    assert header.sfnt_version == 0x00010000
    assert header.num_tables > 0
    0

[[test]]
fn test_find_table() -> i32
    let font = load_font("fixtures/DejaVuSans.ttf").unwrap()
    assert font.has_table(Tag.HEAD)
    assert font.has_table(Tag.CMAP)
    assert font.has_table(Tag.GLYF)
    0

[[test]]
fn test_cmap_lookup() -> i32
    let font = load_font("fixtures/DejaVuSans.ttf").unwrap()
    let glyph_id = font.cmap_lookup('A' as u32)
    assert glyph_id.is_some()
    assert glyph_id.unwrap() > 0
    0
```

### Integration Tests

```ritz
[[test]]
fn test_render_glyph() -> i32
    let font = load_font("fixtures/DejaVuSans.ttf").unwrap()
    let glyph = font.get_glyph('A' as u32).unwrap()
    let bitmap = rasterize(glyph, 16)  # 16px size

    assert bitmap.width > 0
    assert bitmap.height > 0
    assert bitmap.data.len() == bitmap.width * bitmap.height
    0
```

### Golden Image Tests (Future)

Render glyphs to PNG, compare against known-good images.

---

## MVP Phases

### Phase 1: TTF Parsing
- Parse offset table
- Parse table directory
- Parse `head` table (font metrics)
- Parse `cmap` table (character → glyph mapping)
- Parse `maxp` table (glyph count)

### Phase 2: Glyph Access
- Parse `loca` table (glyph offsets)
- Parse `glyf` table (glyph outlines)
- Extract outline data for a single glyph

### Phase 3: Rasterization
- Simple scanline rasterizer
- Convert bezier curves to line segments
- Fill algorithm
- Basic antialiasing

### Phase 4: Text Layout
- Parse `hmtx` (glyph advances)
- Basic kerning (kern table)
- Layout a string of characters

### Phase 5: Advanced Features
- Glyph cache (LRU)
- Subpixel rendering
- OpenType features (GPOS, GSUB)
- Font discovery

---

## Prism Integration

Angelo will be called from Prism's render engine when processing `DrawText` commands:

```ritz
# In Prism's render engine
fn execute_draw_text(cmd: DrawText, buffer:& PixelBuffer)
    let font = font_manager.get_font(cmd.font)
    let glyphs = shaper.shape(font, cmd.text)

    var x = cmd.pos.x
    for glyph in glyphs
        let bitmap = cache.get_or_render(font, glyph, cmd.size)
        blit_glyph(buffer, bitmap, x + bitmap.bearing_x, cmd.pos.y - bitmap.bearing_y)
        x = x + bitmap.advance
```

---

## References

- [OpenType Specification](https://docs.microsoft.com/en-us/typography/opentype/spec/)
- [TrueType Reference Manual](https://developer.apple.com/fonts/TrueType-Reference-Manual/)
- [FreeType Glyph Conventions](https://freetype.org/freetype2/docs/glyphs/)

---

*Part of the Ritz ecosystem. See `larb/AGENT.md` for full guidelines.*
