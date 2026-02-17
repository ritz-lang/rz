# Prism

Display server and window compositor for Harland. Active development.

---

## Overview

Prism is the graphical foundation of the Harland OS. It manages windows, routes input events, and composites the final display. Applications communicate with Prism via capability-protected ring buffers.

---

## Where It Fits

```
GUI Applications (Tempest browser, editors, etc.)
        │ WindowCapability (command + event ring buffers)
        ▼
     PRISM (display server)
        │ DrawText calls
        ▼
     ANGELO (font rendering)
        │
        ▼
   Backend (VirtioGpu, DRM/KMS, Mock)
        │
        ▼
   Harland VMM (shared memory allocation)
```

---

## Key Design Decisions

### Hybrid Rendering Model

Applications can choose their rendering strategy per window:

1. **Buffer mode** (Wayland-like) — Application renders into a shared memory buffer and submits it. Best for applications with custom rendering pipelines.
2. **Command mode** (X11-like) — Application sends drawing commands; Prism renders them. Best for simple UI applications.
3. **Hybrid** — Different regions use different modes.

### Capability-Based Security

Windows are capabilities. An application that holds a `WindowCapability` can:
- Write to its buffer region
- Send commands on its command ring
- Receive events on its event ring

It cannot access any other window's memory or send commands on behalf of another window. The capability is unforgeable.

### Async Scanline Compositor

Instead of a global render loop, Prism uses a virtual scanline:

```
┌─────────────────┐
│█████████████████│  LOCKED: scanline passed, row is committed to frame
│█████████████████│  LOCKED
│─────────────────│  <- virtual scanline advances at frame_rate × height
│░░░░░░░░░░░░░░░░░│  OPEN: still time to write here
│░░░░░░░░░░░░░░░░░│  OPEN
└─────────────────┘
```

Multiple workers can render different screen regions in parallel, as long as they do not overlap and stay ahead of the scanline. This gives near-zero compositor overhead for well-behaved clients.

### Triple Buffering

- **Front buffer** — Currently displayed on screen
- **Back buffer** — Fully rendered, ready for next vsync
- **Pending buffer** — Being drawn to by the compositor

### Damage Tracking

Windows report which rectangles changed. Prism unions the dirty rects and only redraws those regions. For mostly-static UIs, this dramatically reduces compositor work.

---

## Protocol

### WindowCapability

```ritz
struct WindowCapability
    id: WindowId
    buffer: SharedMemoryHandle      # Direct rendering (buffer mode)
    buffer_size: Size
    command_ring: RingBufferHandle  # Client to Prism commands
    event_ring: RingBufferHandle    # Prism to client events
```

### RenderCommand

```ritz
enum RenderCommand
    FillRect { rect: Rect, color: Color }
    StrokeRect { rect: Rect, color: Color, width: u32 }
    DrawLine { from: Point, to: Point, color: Color }
    DrawText { pos: Point, text: StrView, font: FontId, size: u32 }
    BlitImage { pos: Point, image: ImageHandle }
    SubmitBuffer { damage: Vec<Rect> }
    Invalidate { region: Rect }
```

### WindowEvent

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

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           PRISM                                      │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                   PROTOCOL LAYER                             │    │
│  │  Ring buffer IPC, capability management, command decode     │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│  ┌───────────────────────────┴───────────────────────────────┐      │
│  │                   RENDER ENGINE                            │      │
│  │  FillRect, DrawLine, DrawText (via Angelo), BlitImage     │      │
│  └───────────────────────────────────────────────────────────┘      │
│                              │                                       │
│  ┌───────────────────────────┴───────────────────────────────┐      │
│  │                   COMPOSITOR                               │      │
│  │  Async scanline, damage tracking, triple buffering        │      │
│  └───────────────────────────────────────────────────────────┘      │
│                              │                                       │
│  ┌───────────────────────────┴───────────────────────────────┐      │
│  │                   SHELL (Future)                           │      │
│  │  Desktop, tiling WM, command launcher, global hotkeys     │      │
│  └───────────────────────────────────────────────────────────┘      │
│                              │                                       │
│  ┌───────────────────────────┴───────────────────────────────┐      │
│  │                   BACKEND                                  │      │
│  │  MockBackend | VirtioGpuBackend | [DRM/KMS planned]       │      │
│  └───────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Shell Layer (Planned)

The future shell layer will provide:

- **Desktop** — Background with clock, calendar, and widget bar
- **Tiling/floating windows** — Flexbox-inspired layout with smooth animations
- **Command launcher** — Meta+Enter brings up a command input
- **Focus mode** — Meta+Space fullscreens the focused window, dims others
- **Window splay** — Push windows aside to reveal desktop

---

## Backends

| Backend | Description | Status |
|---------|-------------|--------|
| `MockBackend` | In-memory pixel buffer. No display. Used in tests. | Active |
| `VirtioGpuBackend` | QEMU VirtIO GPU. Graphical output in emulation. | Active |
| DRM/KMS | Direct hardware framebuffer control. | Planned |

---

## MVP Phases

| Phase | Goals |
|-------|-------|
| 1 | Basic types, MockBackend, FillRect, protocol structures, RingBuffer |
| 2 | Window creation/destruction, Z-ordering, focus, keyboard routing |
| 3 | Shell layer, window tiling, animation engine |
| 4 | Triple buffering, async scanline, multi-touch, remote display |

---

## Current Status

Active development. MockBackend working. Protocol structures defined. Angelo integration in progress.

---

## Related Projects

- [Angelo](angelo.md) — Font rendering, called by Prism for DrawText
- [Harland](harland.md) — Microkernel Prism runs on
- [Tempest](tempest.md) — Browser that uses Prism for display
- [Graphics Subsystem](../subsystems/graphics.md)
