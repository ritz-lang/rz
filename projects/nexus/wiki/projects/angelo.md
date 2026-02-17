# Angelo

Font loading, shaping, and rasterization for Prism. Active development.

---

## Overview

Angelo is the font engine for the Ritz graphics stack. It handles everything between a Unicode string and a pixel bitmap: loading TrueType/OpenType fonts, shaping text (ligatures, kerning), rasterizing outlines, and caching results.

Angelo is a library, not a service. Prism links it directly and calls it during `DrawText` command execution.

---

## Where It Fits

```
PRISM render engine
    │ DrawText { pos, text, font, size }
    ▼
  ANGELO
    ├── FontManager (font discovery and loading)
    ├── Loader (TTF/OTF parsing)
    ├── Shaper (Unicode → Glyph IDs, ligatures, kerning)
    ├── Rasterizer (outlines → pixel bitmaps)
    └── GlyphCache (LRU cache of rasterized glyphs)
```

---

## Key Features

- **TrueType and OpenType** font file parsing
- **Unicode support** via CMAP table
- **Ligatures** via GSUB OpenType substitution
- **Kerning** via KERN and GPOS tables
- **Antialiased rasterization** via scanline fill of Bezier outlines
- **Subpixel positioning** (1/4 pixel precision)
- **LRU glyph cache** keyed by font, glyph ID, size, and subpixel offset
- **Lazy loading** — glyph data parsed on first use, not on font load
- **Zero-copy** — font file is memory-mapped; tables are accessed by offset

---

## Character to Pixels Pipeline

```
"Hello" (UTF-8 string)
    │
    ▼ Decode to Unicode codepoints
[0x48, 0x65, 0x6C, 0x6C, 0x6F]
    │
    ▼ CMAP table: Unicode → Glyph IDs
[GlyphID: 43, 72, 79, 79, 82]
    │
    ▼ GSUB table: Ligature substitution
[GlyphID: 43, 72, 79, 79, 82]  (no ligatures in "Hello")
    │
    ▼ GPOS/KERN: Kerning adjustments
Kerning offsets: [0, +1, 0, 0, 0]
    │
    ▼ GLYF table: Get outline data (Bezier curves)
Per-glyph contours and control points
    │
    ▼ Rasterizer: Scanline fill
Per-glyph pixel bitmaps (alpha values 0-255)
    │
    ▼ GlyphCache: Store for reuse
Cached at (font_id, glyph_id, size_px, subpixel_x)
```

---

## Core Types

```ritz
# A loaded font — just an ID for fast passing
struct FontHandle
    id: u32

# Font-level metrics
struct FontMetrics
    units_per_em: u16
    ascender: i16
    descender: i16
    line_gap: i16

# Individual glyph shape
struct GlyphOutline
    contours: Vec<Contour>
    bounds: Rect

struct Contour
    points: Vec<OutlinePoint>

struct OutlinePoint
    x: i16
    y: i16
    on_curve: bool     # true = endpoint, false = quadratic control point

# Rasterized glyph (cached)
struct RasterizedGlyph
    bitmap: Vec<u8>    # Alpha values 0-255
    width: u32
    height: u32
    bearing_x: i32     # Horizontal offset from baseline origin
    bearing_y: i32     # Vertical offset from baseline origin
    advance: u32       # How far to advance the pen

# Cache key
struct GlyphCacheKey
    font_id: u32
    glyph_id: u16
    size_px: u16
    subpixel_x: u8     # 0-3 for 1/4 pixel precision
```

---

## TTF Table Support

| Table | Description | When Parsed |
|-------|-------------|-------------|
| `head` | Font header (units per em, bbox) | On font load |
| `hhea` | Horizontal header (ascender, descender) | On font load |
| `maxp` | Maximum profile (glyph count) | On font load |
| `cmap` | Unicode to glyph ID mapping | On font load |
| `hmtx` | Glyph advance widths | On first glyph access |
| `loca` | Glyph offset index | On first glyph access |
| `glyf` | Glyph outlines | Per glyph, on demand |
| `kern` | Basic kerning pairs | On first text shaping |
| `GPOS` | OpenType advanced positioning | On first text shaping |
| `GSUB` | OpenType substitution (ligatures) | On first text shaping |

---

## Zero-Copy Design

Font files are memory-mapped. All table access is pointer arithmetic into the mapped region:

```ritz
struct FontFile
    data: @[u8]              # Immutable ref to memory-mapped font data
    tables: HashMap<Tag, TableEntry>

struct TableEntry
    offset: u32
    length: u32

fn read_table(font: FontFile, tag: Tag) -> Option<@[u8]>
    match font.tables.get(tag)
        Some(entry) =>
            let start = entry.offset as usize
            let end = start + entry.length as usize
            Some(@font.data[start..end])
        None => None
```

---

## Integration with Prism

```ritz
# Inside Prism's render engine
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

## MVP Phases

| Phase | Goals |
|-------|-------|
| 1 | Parse offset table, table directory, head, cmap, maxp |
| 2 | Parse loca and glyf; extract outline data |
| 3 | Scanline rasterizer, Bezier flattening, fill, antialiasing |
| 4 | Parse hmtx, basic kerning, string layout |
| 5 | Glyph cache, subpixel rendering, GPOS/GSUB, font discovery |

---

## Current Status

Active development. TTF parsing and initial rasterizer in progress.

---

## Related Projects

- [Prism](prism.md) — Display server that calls Angelo for text rendering
- [Harland](harland.md) — Microkernel providing memory mapping
- [Graphics Subsystem](../subsystems/graphics.md)
