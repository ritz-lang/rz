# Prism Design Document

Display server and window compositor for Harland.

---

## Overview

Prism is a display server that sits between applications and the hardware (via Harland). It manages windows, routes input, and composites the final display.

### Key Design Decisions

1. **Hybrid Rendering Model** — Clients can choose:
   - **Buffer mode** (Wayland-like): Client renders to shared memory, submits buffer
   - **Command mode** (X11-like): Client sends drawing commands, Prism renders
   - **Hybrid**: Both, for different regions

2. **Capability-Based Security** — Windows are capabilities. Clients receive a `WindowCapability` that grants them:
   - Write access to their buffer region
   - Command ringbuffer for sending draw commands
   - Event ringbuffer for receiving input/lifecycle events

3. **Async Scanline Compositor** — Instead of a traditional render loop:
   - Virtual scanline advances at frame_rate × screen_height per second
   - Components can render to regions the scanline hasn't reached yet
   - Once scanline passes a row, that row is locked for the frame
   - Enables parallel rendering of non-overlapping regions

4. **Triple Buffering** — For smooth animations:
   - Front buffer: currently displayed
   - Back buffer: ready for next vsync
   - Pending buffer: being drawn to

5. **Damage Tracking** — Only redraw what changed:
   - Windows report dirty rectangles
   - Compositor unions dirty rects, subtracts occluded regions
   - Minimal work per frame

6. **Remote-Friendly Protocol** — Commands are serializable:
   - No pointers in protocol messages
   - Use handles/IDs for resources
   - Enables SSH tunneling (like X11 forwarding)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          PRISM                                       │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                   PROTOCOL LAYER                             │    │
│  │  - RingBuffer IPC (shared memory)                           │    │
│  │  - Capability management                                     │    │
│  │  - Command serialization (for remote)                       │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│  ┌───────────────────────────┴───────────────────────────────┐      │
│  │                   RENDER ENGINE                            │      │
│  │  - Command interpreter (FillRect, DrawText, etc.)         │      │
│  │  - Angelo integration (fonts)                              │      │
│  │  - Image handling                                          │      │
│  │  - Buffer compositing                                      │      │
│  └───────────────────────────────────────────────────────────┘      │
│                              │                                       │
│  ┌───────────────────────────┴───────────────────────────────┐      │
│  │                   COMPOSITOR                               │      │
│  │  - Async scanline scheduler                                │      │
│  │  - Damage tracking                                         │      │
│  │  - Triple buffering                                        │      │
│  │  - Parallel render workers                                 │      │
│  └───────────────────────────────────────────────────────────┘      │
│                              │                                       │
│  ┌───────────────────────────┴───────────────────────────────┐      │
│  │                   SHELL (Future)                           │      │
│  │  - Desktop layer                                           │      │
│  │  - Window management (tiling, animations)                  │      │
│  │  - Command prompt (meta+enter)                            │      │
│  │  - Global hotkeys                                          │      │
│  └───────────────────────────────────────────────────────────┘      │
│                              │                                       │
│  ┌───────────────────────────┴───────────────────────────────┐      │
│  │                   BACKEND                                  │      │
│  │  - MockBackend (testing)                                   │      │
│  │  - VirtioGpuBackend (QEMU)                                │      │
│  │  - [Future: DRM/KMS, hardware GPU]                        │      │
│  └───────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Scanline Model

The async scanline compositor allows parallel, non-blocking rendering:

```
┌─────────────────┐
│█████████████████│  ← LOCKED: scanline passed, too late for this frame
│█████████████████│  ← LOCKED
│█████████████████│  ← LOCKED
│─────────────────│  ← virtual scanline (advances with time)
│░░░░░░░░░░░░░░░░░│  ← OPEN: can still render here
│░░░░░░░░░░░░░░░░░│  ← OPEN
└─────────────────┘
```

**Rules:**
1. Scanline advances at `frame_rate × screen_height` pixels/second
2. Components can render to any row below the scanline
3. Once scanline passes a row, it's locked until next frame
4. Multiple workers can render non-overlapping regions in parallel
5. If a component misses its window, it waits for next frame

---

## Protocol

### WindowCapability

What Prism gives to a client when it creates a window:

```ritz
struct WindowCapability
    id: WindowId
    buffer: SharedMemoryHandle      # for direct rendering
    buffer_size: Size
    command_ring: RingBufferHandle  # client → prism commands
    event_ring: RingBufferHandle    # prism → client events
```

### RenderCommand

Commands clients can send:

```ritz
enum RenderCommand
    # Primitives
    FillRect { rect: Rect, color: Color }
    StrokeRect { rect: Rect, color: Color, width: u32 }
    DrawLine { from: Point, to: Point, color: Color }

    # Text (uses Angelo)
    DrawText { pos: Point, text: StrView, font: FontId, size: u32 }

    # Images
    BlitImage { pos: Point, image: ImageHandle }

    # Buffer mode
    SubmitBuffer { damage: Vec<Rect> }

    # Control
    Invalidate { region: Rect }
```

### WindowEvent

Events Prism sends to clients:

```ritz
enum WindowEvent
    Resize { new_size: Size }
    Focus { focused: bool }
    KeyPress { key: KeyCode, mods: Modifiers }
    KeyRelease { key: KeyCode, mods: Modifiers }
    MouseMove { pos: Point }
    MouseButton { button: Button, pressed: bool, pos: Point }
    TouchStart { id: u32, pos: Point }
    TouchMove { id: u32, pos: Point }
    TouchEnd { id: u32 }
    FrameCallback { frame: u64 }
    Close
```

---

## Shell Vision (Future)

The shell layer will provide:

- **Desktop** — Background with widgets (clock, calendar, todo, etc.)
- **Tiling/Floating Windows** — Fluid flexbox-style layout with smooth animations
- **Command Prompt** — Meta+Enter brings up a text input for launching apps
- **Window Focus** — Meta+Space "hovers" current window fullscreen, dims others
- **Window Splay** — Button to push windows aside, reveal desktop widgets
- **Global Hotkeys** — System-wide keyboard shortcuts

---

## Testing Strategy

1. **Unit Tests** — Pure functions, data structures, math
2. **Protocol Tests** — Mock client sends commands, verify state changes
3. **Compositor Tests** — Use MockBackend, inspect pixel buffer
4. **Integration Tests** — Full client lifecycle
5. **Visual Regression** — Render to PNG, compare golden images (future)

---

## MVP Phases

### Phase 1: Foundation
- Basic types (Rect, Color, Point, Size)
- MockBackend with pixel buffer inspection
- Simple compositor that can fill rects
- Protocol structures (commands, events)
- RingBuffer implementation

### Phase 2: Windows
- Window creation/destruction
- Z-ordering and focus
- Basic damage tracking
- Keyboard input routing

### Phase 3: Shell
- Desktop layer
- Window tiling
- Animation engine
- Command prompt

### Phase 4: Polish
- Triple buffering
- Async scanline scheduler
- Multi-touch gestures
- Remote display support

---

*Part of the Ritz ecosystem. See `larb/AGENT.md` for full guidelines.*
