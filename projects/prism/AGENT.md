# Prism - Display Server

Display server and window compositor for Harland.

---

## Project Overview

Prism is the display server for the Harland microkernel. It manages windows, handles input, and composites the final display output.

### Responsibilities

- **Window Management** — Create, destroy, move, resize windows
- **Compositing** — Combine window buffers into final output
- **Input Handling** — Keyboard, mouse, touch distribution
- **GPU Interface** — virtio-gpu for QEMU, hardware acceleration

### Non-Responsibilities

Prism does NOT handle:
- Application rendering (apps provide buffers)
- Widget toolkits (separate libraries)
- File system access (use Goliath via Harland)

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   APPLICATIONS                       │
│        (Tempest, terminal, editors, etc.)            │
└───────────────────────┬─────────────────────────────┘
                        │ (window buffers)
                        ▼
┌─────────────────────────────────────────────────────┐
│                     PRISM                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │   Window    │ │   Input     │ │ Compositor  │   │
│  │   Manager   │ │   Handler   │ │             │   │
│  └─────────────┘ └─────────────┘ └─────────────┘   │
└───────────────────────┬─────────────────────────────┘
                        │ (capability calls)
                        ▼
┌─────────────────────────────────────────────────────┐
│                    HARLAND                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │  virtio-gpu │ │virtio-input │ │   Memory    │   │
│  │   driver    │ │   driver    │ │   Manager   │   │
│  └─────────────┘ └─────────────┘ └─────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## Ritz Coding Guidelines

### Parameter Syntax

| Syntax | Meaning | Usage |
|--------|---------|-------|
| `x: T` | Const borrow | Default (~70% of params) |
| `x:& T` | Mutable borrow | When modifying the value |
| `x:= T` | Move ownership | When taking ownership |

**NO SPACE between `:` and modifier!** Write `:&` not `: &`

```ritz
fn create_window(config: WindowConfig) -> Window
fn resize_window(window:& Window, width: u32, height: u32)
fn destroy_window(window:= Window)
```

### Reference Syntax

| Syntax | Meaning |
|--------|---------|
| `@x` | Take immutable reference |
| `@&x` | Take mutable reference |
| `@T` | Immutable reference type |
| `@&T` | Mutable reference type |

### String Literals

```ritz
"hello"              # StrView (zero-copy) — DEFAULT
String.from("hello") # String (heap-allocated)
c"hello"             # *u8 for FFI ONLY
```

### Testing

```ritz
[[test]]
fn test_window_creation() -> i32
    let config = WindowConfig { width: 800, height: 600 }
    let window = create_window(config)
    assert window.width == 800
    0
```

---

## Core Doctrines

### No Concessions Doctrine

> "Never make concessions for the language — we are MAKING the language."

If Ritz can't express something cleanly, fix Ritz. Don't work around limitations.

### Capability-Based Security

Prism integrates with Harland's capability model:
- Windows are capabilities
- Input events require capability to receive
- GPU access is mediated by capabilities

### Test-Driven Development

1. Write failing tests first
2. Implement to make tests pass
3. Refactor with confidence
4. All tests must pass before committing

---

## Project Structure

```
prism/
├── src/
│   ├── server.ritz        # Main display server
│   ├── window.ritz        # Window management
│   ├── compositor.ritz    # Buffer compositing
│   ├── input/
│   │   ├── keyboard.ritz  # Keyboard handling
│   │   ├── mouse.ritz     # Mouse/pointer
│   │   └── touch.ritz     # Touch input
│   ├── gpu/
│   │   ├── virtio.ritz    # virtio-gpu driver
│   │   └── buffer.ritz    # Framebuffer management
│   └── protocol.ritz      # Client-server protocol
├── tests/
└── ritz.toml
```

---

## Style Guidelines

- **Indentation:** 4 spaces (no tabs)
- **Line length:** 100 characters max
- **Naming:** `snake_case` for functions, `PascalCase` for types
- **Immutable by default:** Use `let`, only `var` when mutation needed
- **Use `defer`** for resource cleanup

---

*Part of the Ritz ecosystem. See `larb/AGENT.md` for full guidelines.*
