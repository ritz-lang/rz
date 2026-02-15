# Iris - Rendering Engine

Rendering engine for layout, painting, and compositing.

---

## Project Overview

Iris is a standalone rendering engine that transforms a document tree into pixels. It handles layout calculation, painting, and compositing.

### Responsibilities

- **Layout** — Box model, flex, grid, text layout
- **Painting** — Drawing primitives, text rendering, image decoding
- **Compositing** — Layer management, GPU acceleration, scrolling
- **Hit testing** — Coordinate to element mapping

### Non-Responsibilities

Iris does NOT handle:
- HTML/CSS parsing (use Lexis)
- JavaScript execution (use Sage)
- Network requests (use Valet)
- Window management (use Prism)

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Document Tree                      │
│              (from Lexis parser)                     │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                    LAYOUT                            │
│         Box model, flex, grid, text                  │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                   PAINT                              │
│       Drawing commands, text, images                 │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                  COMPOSITE                           │
│         Layers, GPU, final output                    │
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
fn layout_box(node: Node, constraints: Constraints) -> LayoutBox
fn paint_box(box: LayoutBox, canvas:& Canvas)
fn composite_layers(layers:= Vec<Layer>) -> Bitmap
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
fn test_box_layout() -> i32
    let node = create_test_node()
    let box = layout_box(node, Constraints.default())
    assert box.width > 0
    0
```

---

## Core Doctrines

### No Concessions Doctrine

> "Never make concessions for the language — we are MAKING the language."

If Ritz can't express something cleanly, fix Ritz. Don't work around limitations.

### Test-Driven Development

1. Write failing tests first
2. Implement to make tests pass
3. Refactor with confidence
4. All tests must pass before committing

---

## Project Structure

```
iris/
├── src/
│   ├── layout/
│   │   ├── box.ritz       # Box model
│   │   ├── flex.ritz      # Flexbox
│   │   ├── grid.ritz      # CSS Grid
│   │   └── text.ritz      # Text layout
│   ├── paint/
│   │   ├── canvas.ritz    # Drawing primitives
│   │   ├── text.ritz      # Text rendering
│   │   └── image.ritz     # Image decoding
│   └── composite/
│       ├── layer.ritz     # Layer management
│       └── gpu.ritz       # GPU acceleration
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
