# Iris

Rendering engine for the Tempest web browser - layout, painting, and compositing of styled DOM content.

**Part of the [Ritz Ecosystem](../ritz/docs/ECOSYSTEM.md)**

## Overview

Iris is the rendering engine that transforms styled DOM content into pixels on screen. It sits between the Tempest browser process (which owns the DOM) and the Prism display server (which owns the compositor). Iris receives `StyleEvent` streams from Tempest whenever the DOM changes, computes layout, paints the render tree, and submits composited layers to Prism.

Iris maintains a render tree that mirrors the visible DOM, computing box layout (block, inline, flex) for each element and tracking dirty flags for incremental updates. Certain CSS properties (transforms, opacity, fixed positioning) trigger the creation of dedicated compositor layers, enabling fast scrolling and animation without full repaints.

Angelo provides all font rasterization and text shaping for Iris text rendering.

## Features

- Render tree construction and incremental updates via dirty flags
- CSS box model layout (block, inline, flexbox)
- Layer tree for compositing (transforms, opacity, fixed positioning)
- Incremental layout - only recomputes dirty subtrees
- Paint commands generated from computed styles
- Hit testing for mouse event routing
- Scrolling and scroll offset management
- Text layout using Angelo for shaping and rasterization
- IPC protocol for submitting frames to Prism

## Installation

```bash
# Build from source (run from the monorepo root; `rz` sets RITZ_PATH itself)
./rz build iris

# Run tests (3 files, 30 assertions)
./rz test iris
```

## Usage

```ritz
import iris { RenderEngine, StyleEvent }

# Create render engine, connected to Prism
let engine = RenderEngine.new(prism_connection)

# Process DOM style events from Tempest
fn handle_style_event(event: StyleEvent)
    engine.apply_style_event(event)

# After all events, request a frame
engine.request_frame()

# Iris will compute layout, paint, and submit to Prism
```

```ritz
# Render tree node structure
struct RenderNode
    id: NodeId
    tag: ElementTag
    style: ComputedStyle
    layout: LayoutResult
    dirty: DirtyFlags

# Layer for compositing
struct Layer
    id: LayerId
    node_id: NodeId
    reason: LayerReason  # Transform, Opacity, FixedPosition
    bounds: Rect
    transform: Transform
    opacity: f32
```

## Dependencies

- `prism` - Display server for submitting rendered frames
- `angelo` - Font rasterization and text shaping

## Status

**Alpha, with a passing suite.** Measured 2026-09-12: `./rz build iris` exits 0
producing `build/debug/iris`, and `./rz test iris` exits 0 with
`30 passed, 0 failed` across 3 test files (`test_layout_box`, `test_render_tree`,
`test_style_types`).

Render tree construction and block layout are implemented. Full CSS layout
(flex, grid), layer compositing and Prism IPC integration are still planned.
Note that iris's upstream, [lexis](../lexis), does not currently compile
(AGAST #1289), so the parse → layout path cannot be exercised end to end.

## License

MIT License - see LICENSE file
