# Angelo

Font loading and rendering library for Prism - TrueType/OpenType parsing, text shaping, and glyph rasterization.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

## Overview

Angelo handles everything related to text rendering in the Ritz ecosystem. It parses TrueType and OpenType font files, shapes Unicode text (resolving ligatures, kerning, and bidirectional text), rasterizes glyph outlines to pixel bitmaps, and caches the results for efficient reuse.

Angelo is used by Prism (the display server) to render text in all windows and UI elements. It is designed as a pure Ritz library with no C dependencies on freetype or similar external libraries, making it suitable for the freestanding Harland kernel environment where libc is unavailable.

The glyph cache uses LRU eviction and is keyed by font ID, glyph ID, pixel size, and subpixel offset to maximize reuse while supporting smooth animations and variable font sizes.

## Features

- TrueType (TTF) and OpenType (OTF) font file parsing
- Unicode text shaping (ligatures, kerning, bidi)
- Outline rasterization with antialiasing
- Hinting for crisp rendering at small sizes
- LRU glyph cache keyed by (font, glyph, size, subpixel)
- Font discovery for system font directories
- Multiple simultaneous font handles (lightweight references)
- No C dependencies - pure Ritz

## Installation

```bash
# As a dependency in ritz.toml:
# [dependencies]
# angelo = { path = "../angelo" }

# Build and test
export RITZ_PATH=/path/to/ritz
./ritz build .
./build/debug/angelo-test
```

## Usage

```ritz
import angelo { FontManager, Font, GlyphCache }

# Initialize font manager
let fonts = FontManager.new()

# Load a font
let font = fonts.load("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")

# Shape a text string
let glyphs = font.shape("Hello, World!", 14.0)

# Rasterize glyphs (result is cached)
for glyph in glyphs
    let bitmap = fonts.rasterize(glyph)
    blit_bitmap(x + glyph.x_offset, y + glyph.y_offset, bitmap)
```

```ritz
# Integration with Prism DrawText command
fn handle_draw_text(cmd: *DrawTextCommand, framebuffer: *Framebuffer)
    let glyphs = g_font_manager.shape(cmd.text, cmd.font_size)
    var x: i32 = cmd.x
    for glyph in glyphs
        let bitmap = g_font_manager.rasterize(glyph)
        blit_alpha(framebuffer, x + glyph.x_offset, cmd.y + glyph.y_offset, bitmap, cmd.color)
        x = x + glyph.advance_x
```

## Dependencies

Angelo has no required runtime dependencies beyond `ritzlib`. It operates entirely on file I/O for font loading and manual pixel manipulation for rasterization.

## Status

**Alpha** - Font file parser architecture, type definitions, cache design, and the test binary are in place. TTF/OTF table parsing, shaper, and rasterizer are being implemented. The test binary exercises font loading and basic glyph rendering.

## License

MIT License - see LICENSE file
