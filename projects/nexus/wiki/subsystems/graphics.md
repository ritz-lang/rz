# Graphics Subsystem

The graphics subsystem provides everything needed to render a desktop graphical environment on Harland — from the low-level display server to high-quality font rendering.

---

## Projects in This Subsystem

| Project | Role | Status |
|---------|------|--------|
| [Prism](../projects/prism.md) | Display server and window compositor | Active |
| [Angelo](../projects/angelo.md) | Font loading, shaping, and rasterization | Active |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Application Layer                                │
│            (Tempest browser, rzsh terminal, etc.)                   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ WindowCapability (ring buffers)
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           PRISM                                      │
│                    Display Server / Compositor                       │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                   PROTOCOL LAYER                             │    │
│  │     Ring buffer IPC, capability management, serialization   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│  ┌───────────────────────────┴───────────────────────────────┐      │
│  │                   RENDER ENGINE                            │      │
│  │    FillRect, DrawLine, DrawText, BlitImage, SubmitBuffer   │      │
│  └───────────────────────────────────────────────────────────┘      │
│                              │                                       │
│  ┌───────────────────────────┴───────────────────────────────┐      │
│  │                    COMPOSITOR                              │      │
│  │    Async scanline, damage tracking, triple buffering      │      │
│  └───────────────────────────────────────────────────────────┘      │
│                              │                                       │
│  ┌───────────────────────────┴───────────────────────────────┐      │
│  │                     BACKEND                               │      │
│  │    MockBackend (tests) / VirtioGpuBackend (QEMU)          │      │
│  └───────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ DrawText calls
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           ANGELO                                     │
│                   Font Loading and Rendering                         │
│                                                                      │
│  FontManager → Loader → Shaper → Rasterizer → GlyphCache            │
│                                                                      │
│  TrueType/OpenType parsing, ligatures, kerning, antialiasing        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Prism in Detail

### Scanline Compositor

The async scanline model allows multiple workers to render non-overlapping screen regions simultaneously:

```
┌─────────────────┐
│█████████████████│  LOCKED: scanline has passed — committed to frame
│█████████████████│  LOCKED
│─────────────────│  <- virtual scanline (advances at frame_rate × height)
│░░░░░░░░░░░░░░░░░│  OPEN: still time to render here
│░░░░░░░░░░░░░░░░░│  OPEN
└─────────────────┘
```

The scanline advances at `frame_rate × screen_height` pixels per second. Components race to render their regions before the scanline passes.

### Window Events

```ritz
enum WindowEvent
    Resize { new_size: Size }
    Focus { focused: bool }
    KeyPress { key: KeyCode, mods: Modifiers }
    KeyRelease { key: KeyCode, mods: Modifiers }
    MouseMove { pos: Point }
    MouseButton { button: Button, pressed: bool, pos: Point }
    FrameCallback { frame: u64 }
    Close
```

### Shell Layer (Planned)

The Prism shell layer will provide the desktop environment:

- Tiling and floating window management
- Smooth animations
- Meta+Enter command launcher
- Global hotkeys
- Desktop widgets (clock, calendar, etc.)

---

## Angelo in Detail

### Character to Pixels Pipeline

```
"A" (U+0041)
    │
    ▼ CMAP table
GlyphID: 36
    │
    ▼ GSUB table (ligature check)
GlyphID: 36 (no ligature for single char)
    │
    ▼ GPOS/KERN tables
Kerning offset: +1 unit
    │
    ▼ GLYF table
Bezier outline: [curve data]
    │
    ▼ Rasterizer (scanline fill)
Pixel bitmap: 11×13 @ 16px
    │
    ▼ GlyphCache
Stored at key: (font_id=1, glyph_id=36, size=16, subpixel=0)
```

### Cache Key Design

Glyphs are cached by a four-part key to support subpixel rendering:

```ritz
struct GlyphCacheKey
    font_id: u32
    glyph_id: u16
    size_px: u16
    subpixel_x: u8     # 0-3 for 1/4 pixel positioning
```

### TTF Table Support

| Table | Purpose |
|-------|---------|
| `head` | Font metrics (units per em, bounds) |
| `hhea` | Horizontal header (ascender, descender) |
| `hmtx` | Glyph advance widths |
| `cmap` | Unicode to glyph ID mapping |
| `loca` | Glyph location index |
| `glyf` | Glyph outlines (Bezier curves) |
| `kern` | Basic kerning pairs |
| `GPOS` | OpenType advanced positioning |
| `GSUB` | OpenType substitution (ligatures) |

---

## Rendering Workflow

When an application calls `DrawText`, this is what happens:

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

## Display Backends

Prism supports multiple backends for portability:

| Backend | Environment | Purpose |
|---------|-------------|---------|
| `MockBackend` | Tests | In-memory pixel buffer, no display needed |
| `VirtioGpuBackend` | QEMU | Full graphical output in emulation |
| DRM/KMS | Future | Direct hardware framebuffer |

---

## See Also

- [Prism project page](../projects/prism.md)
- [Angelo project page](../projects/angelo.md)
- [Kernel Subsystem](kernel.md) — Harland provides the underlying OS
- [Tempest](../projects/tempest.md) — Browser that uses Prism for display
