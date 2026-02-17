# Iris

Rendering engine for layout, painting, and compositing. Active development.

---

## Overview

Iris transforms a parsed, styled document tree (from Lexis) into pixels. It handles the three phases of the rendering pipeline: layout (computing positions and sizes), painting (producing draw commands), and compositing (layering and blending).

Iris is a library used by Tempest (the browser). It does not handle HTML/CSS parsing, JavaScript, or networking — those are the responsibilities of Lexis, Sage, and Valet respectively.

---

## Where It Fits

```
LEXIS (HTML/CSS parser)
    └── Styled Document Tree
            │
            ▼
         IRIS (rendering engine)
            ├── Layout (box model, flex, grid, text)
            ├── Paint (canvas, text, images)
            └── Composite (layers, GPU)
                    │
                    ▼
             Pixel bitmap
                    │
                    ▼
             PRISM (display server)
```

---

## Three Phases

### 1. Layout

The layout phase computes the position and size of every element in the document:

- **Box model** — Width, height, margin, padding, border
- **Normal flow** — Block and inline formatting contexts
- **Flexbox** — Flexible container layouts
- **CSS Grid** — Two-dimensional grid layouts
- **Text layout** — Line breaking, wrapping, baseline alignment

```ritz
fn layout_box(node: Node, constraints: Constraints) -> LayoutBox
    # Compute intrinsic size
    # Apply constraints
    # Position children
    # Return final box with position and size
```

### 2. Paint

The paint phase produces a list of draw commands:

- Background colors and images
- Borders and outlines
- Text rendering (via Angelo, through Prism)
- Images
- Box shadows

```ritz
fn paint_box(box: LayoutBox, canvas:& Canvas)
    canvas.fill_rect(box.background_rect(), box.background_color)
    canvas.draw_text(box.content_rect(), box.text, box.font, box.font_size)
    for child in box.children
        paint_box(child, canvas)
```

### 3. Compositing

The composite phase takes the paint output and produces the final pixel buffer:

- Z-order management (stacking contexts)
- GPU-accelerated blending (planned)
- Scroll clipping
- Transform and opacity effects
- Layer management for smooth scrolling

```ritz
fn composite_layers(layers:= Vec<Layer>) -> Bitmap
    var output = Bitmap.new(screen_size)
    for layer in layers
        output.blend(layer.bitmap, layer.bounds, layer.opacity)
    output
```

---

## Project Structure

```
iris/
├── src/
│   ├── layout/
│   │   ├── box.ritz       # Box model computation
│   │   ├── flex.ritz      # Flexbox algorithm
│   │   ├── grid.ritz      # CSS Grid algorithm
│   │   └── text.ritz      # Text layout and line breaking
│   ├── paint/
│   │   ├── canvas.ritz    # Drawing primitives (fills, strokes)
│   │   ├── text.ritz      # Text rendering integration
│   │   └── image.ritz     # Image decoding and drawing
│   └── composite/
│       ├── layer.ritz     # Stacking context and layer management
│       └── gpu.ritz       # GPU acceleration (future)
├── tests/
└── ritz.toml
```

---

## Testing Strategy

| Type | Description |
|------|-------------|
| Unit tests | Individual layout algorithms, box model math |
| Integration tests | Full document rendering |
| Layout tests | CSS test suite (subset) |
| Visual regression | Render to PNG, compare golden images (future) |

---

## Current Status

Active development. Layout engine implementation in progress.

---

## Related Projects

- [Lexis](lexis.md) — Provides the styled document tree that Iris renders
- [Sage](sage.md) — JavaScript engine that triggers re-renders via DOM mutations
- [Tempest](tempest.md) — Browser that uses Iris
- [Prism](prism.md) — Display server that receives Iris output
