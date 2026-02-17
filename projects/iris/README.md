# Iris

Rendering engine for the Tempest web browser - layout, painting, and compositing of styled DOM content.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

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
# Build from source
export RITZ_PATH=/path/to/ritz
./ritz build .

# Run tests
./run_all_tests.sh
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

**Alpha** - Architecture, render tree design, and layer model are specified. Basic render tree construction and block layout are being implemented. Full CSS layout (flex, grid), layer compositing, and Prism IPC integration are planned for subsequent phases.

## License

MIT License - see LICENSE file
