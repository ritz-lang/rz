# Prism

Display server and window compositor for Harland - capability-based windowing with async scanline compositing.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

## Overview

Prism is the display server for the Harland microkernel ecosystem. It sits between applications and the GOP framebuffer hardware, managing windows, routing input events, and compositing the final display. Prism uses a hybrid rendering model where clients can either render into shared memory buffers (Wayland-style) or send drawing commands for Prism to execute (X11-style).

Security is enforced via capabilities: each client receives a `WindowCapability` token that grants write access to their specific buffer region and command ringbuffer. The compositor uses an async scanline approach where the virtual scanline advances at frame_rate x screen_height per second, allowing parallel rendering of non-overlapping screen regions.

Prism uses Angelo for all font rendering and text display, and is in turn used by Iris (the browser rendering engine) for compositing browser output to the screen.

## Features

- Capability-based window security model
- Hybrid rendering: client-side buffer mode and server-side command mode
- Async scanline compositor with parallel render workers
- Triple buffering for smooth animation
- Damage tracking - only redraws changed regions
- Shared memory ring buffer IPC for commands and events
- Remote protocol - commands are serializable (no pointers)
- Angelo integration for font rendering
- Input event routing (keyboard, mouse, touch)
- Window management (create, resize, focus, close)

## Installation

```bash
# Build from source (requires Harland kernel or Linux with framebuffer)
export RITZ_PATH=/path/to/ritz
./ritz build .

# Run Prism display server
./build/debug/prism
```

## Usage

```ritz
import prism { connect, Window, WindowCapability }

# Connect to Prism server
let display = prism_connect()

# Create a window
let window = display.create_window(WindowSpec {
    title: "My App",
    width: 800,
    height: 600,
    x: 100,
    y: 100,
})

# Send drawing commands
let cmd = FillRect { x: 0, y: 0, width: 800, height: 600, color: 0xFFFFFF }
window.send_command(cmd)

let text_cmd = DrawText { x: 10, y: 10, text: "Hello, Prism!", font_size: 14 }
window.send_command(text_cmd)

# Flush to display
window.flush()

# Poll events
let event = display.poll_event()
match event.kind
    EventKind.KeyPress   => handle_key(event.key)
    EventKind.MouseMove  => handle_mouse(event.x, event.y)
    EventKind.Close      => shutdown()
```

## Dependencies

- `angelo` - Font loading and glyph rasterization

## Status

**Alpha** - Architecture, capability model, and rendering protocol are designed. Basic framebuffer initialization, window creation, and the command protocol are being implemented. Full compositor, damage tracking, and input routing are planned for subsequent phases.

## License

MIT License - see LICENSE file
