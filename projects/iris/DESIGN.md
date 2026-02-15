# Iris Design Document

Rendering engine for the Tempest web browser.

## Architecture Overview

Iris is the rendering engine that transforms styled DOM events into pixels via Prism.

```
┌─────────────────────────────────────────────────────────────┐
│                      TEMPEST PROCESS                         │
│                                                              │
│  ┌─────────┐     ┌─────────┐     ┌──────────────────────────┐│
│  │  LEXIS  │────▶│   DOM   │◀────│         SAGE             ││
│  │ (parse) │     │ (owned) │     │     (JS engine)          ││
│  └─────────┘     └────┬────┘     └──────────────────────────┘│
│                       │                                       │
│              StyleEvent stream                                │
│                       │                                       │
│                       ▼                                       │
│              ┌─────────────────┐                             │
│              │      IRIS       │                             │
│              │ (layout, paint) │                             │
│              └────────┬────────┘                             │
└───────────────────────┼──────────────────────────────────────┘
                        │ IPC (Prism protocol)
                        ▼
                 ┌────────────┐
                 │   PRISM    │
                 │(compositor)│
                 └────────────┘
```

## Component Responsibilities

| Component | Owns | Responsibility |
|-----------|------|----------------|
| **Tempest** | DOM tree | Navigation, tabs, JS orchestration |
| **Lexis** | CSS rules | Parsing, cascade, specificity → ComputedStyle |
| **Iris** | Render tree, Layer tree | Layout, painting, hit testing, scrolling |
| **Sage** | JS runtime | JavaScript execution, DOM mutations |
| **Prism** | Windows, compositor | Compositing, display, input dispatch |
| **Angelo** | Font data | Glyph rasterization, text shaping |

## Core Data Structures

### Render Tree

Iris maintains a **render tree** that mirrors the visible DOM:
- One `RenderNode` per visible element (skips `display: none`)
- Stores computed styles (from Lexis via Tempest)
- Stores layout results (computed by Iris)
- Supports incremental updates via dirty flags

```ritz
struct RenderNode
    id: NodeId
    tag: ElementTag
    content: RenderContent      # Element | Text | Image
    style: ComputedStyle
    parent/first_child/...      # Tree structure
    layout: LayoutResult        # Computed box position
    dirty: DirtyFlags           # What needs recompute
```

### Layer Tree

For compositing, Iris maintains a **layer tree**:
- Certain CSS properties require their own layer (transforms, opacity, fixed position)
- Layers map to Prism surfaces for GPU compositing
- Enables fast scrolling (only update scroll offset, no repaint)

```ritz
struct Layer
    id: LayerId
    node_id: NodeId             # Associated render node
    reason: LayerReason         # Why this layer exists
    bounds: Rect
    transform: Transform
    opacity: f32
    scroll_offset: Point        # For scrollable layers
```

## Frame Processing Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ iris_render_frame() - called at vsync                       │
├─────────────────────────────────────────────────────────────┤
│ 1. Process queued StyleEvents                              │
│    - NodeCreated/Removed/Moved → update render tree        │
│    - StyleChanged → mark dirty                              │
│    - TextChanged/ImageChanged → update content              │
├─────────────────────────────────────────────────────────────┤
│ 2. Layout (if dirty)                                        │
│    - Traverse render tree                                   │
│    - Resolve dimensions (px, %, em, rem)                    │
│    - Calculate box positions (block, inline, flex, grid)   │
│    - Handle margin collapsing                               │
├─────────────────────────────────────────────────────────────┤
│ 3. Paint (if dirty)                                         │
│    - Traverse render tree in paint order                    │
│    - Generate draw commands per layer                       │
│    - Send to Prism DrawContext                              │
└─────────────────────────────────────────────────────────────┘
```

## Event Flow

### Input Events (Prism → Iris → Tempest)

```
Mouse click at (x, y)
    │
    ▼
Iris receives WindowEvent from Prism
    │
    ▼
Hit test: (x, y) → NodeId
    │
    ▼
Return HitTestResult to Tempest
    │
    ▼
Tempest dispatches JS event (onclick)
```

### DOM Changes (Tempest → Iris → Prism)

```
JS mutates DOM
    │
    ▼
Tempest queues StyleEvent
    │
    ▼
Iris processes on next frame
    │
    ▼
Layout (if structure/style changed)
    │
    ▼
Paint → DrawCommands to Prism
```

### Scrolling (Fast Path)

```
Scroll event from Prism
    │
    ▼
Iris updates layer scroll_offset
    │
    ▼
Recomposite (no repaint needed)
    │
    ▼
Notify Tempest (for JS scroll listeners)
```

## CSS Box Model

```
┌─────────────────────────────────────┐
│              margin                 │
│  ┌───────────────────────────────┐  │
│  │           border              │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │        padding          │  │  │
│  │  │  ┌───────────────────┐  │  │  │
│  │  │  │     content       │  │  │  │
│  │  │  └───────────────────┘  │  │  │
│  │  └─────────────────────────┘  │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

`box-sizing: content-box` → width/height apply to content only
`box-sizing: border-box` → width/height include padding and border

## Layout Algorithms

### Block Layout
- Children stack vertically
- Each block fills available width
- Vertical margins collapse

### Inline Layout (TODO)
- Content flows left-to-right
- Line breaks when width exceeded
- Baseline alignment

### Flexbox (TODO)
- Main axis / cross axis
- justify-content, align-items
- flex-grow, flex-shrink

### Grid (TODO)
- Explicit/implicit tracks
- Grid lines and areas
- Auto-placement

## Dirty Tracking

Each `RenderNode` has dirty flags:

| Flag | Meaning | Action Required |
|------|---------|-----------------|
| `structure` | Tree changed | Rebuild subtree |
| `style` | ComputedStyle changed | May relayout |
| `layout` | Dimensions changed | Relayout |
| `paint` | Visual change only | Repaint |

Dirty flags propagate up to ancestors (parent needs relayout if child changes).

## Dependencies

- **prism.api** — Drawing primitives, window management
- **angelo** — Font loading and text shaping

## Module Structure

```
iris/
├── lib/
│   ├── iris.ritz           # Main API
│   ├── style/
│   │   ├── types.ritz      # CSS value types
│   │   ├── event.ritz      # StyleEvent protocol
│   │   └── mod.ritz
│   ├── tree/
│   │   ├── render_node.ritz
│   │   └── mod.ritz
│   ├── layout/
│   │   ├── box.ritz        # Box model
│   │   ├── block.ritz      # Block layout
│   │   └── mod.ritz
│   ├── composite/
│   │   ├── layer.ritz      # Layer tree
│   │   └── mod.ritz
│   ├── hit/
│   │   └── mod.ritz        # Hit testing
│   └── paint/
│       └── mod.ritz        # Painting
├── src/
│   └── main.ritz           # CLI (for testing)
└── tests/
    └── *.ritz              # Unit tests
```

## Future Work

- [ ] Inline layout with line breaking
- [ ] Flexbox layout
- [ ] CSS Grid layout
- [ ] Text rendering with Angelo
- [ ] Image loading and display
- [ ] CSS transforms (rotate, scale, translate)
- [ ] CSS filters (blur, etc.)
- [ ] CSS animations and transitions
- [ ] Incremental layout (only dirty subtrees)
- [ ] Parallel paint (multiple layers simultaneously)
