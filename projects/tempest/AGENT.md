# Tempest - Web Browser

Web browser written in Ritz.

---

## Project Overview

Tempest is a complete web browser built on the Ritz ecosystem. It consumes standalone components for rendering, JavaScript execution, and HTML/CSS parsing.

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                     TEMPEST                          │
│              (Browser Shell & UI)                    │
│         Tabs, bookmarks, history, settings           │
└───────────────────────┬─────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
   ┌─────────┐    ┌─────────┐    ┌─────────┐
   │  IRIS   │    │  SAGE   │    │  LEXIS  │
   │ Render  │    │   JS    │    │HTML/CSS │
   └─────────┘    └─────────┘    └─────────┘
        │               │               │
        └───────────────┴───────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
   ┌─────────┐    ┌─────────┐    ┌─────────┐
   │  VALET  │    │CRYPTOSEC│    │ SQUEEZE │
   │  HTTP   │    │  TLS    │    │  gzip   │
   └─────────┘    └─────────┘    └─────────┘
```

### Dependencies

- **Iris** — Rendering engine (layout, painting, compositing)
- **Sage** — JavaScript engine
- **Lexis** — HTML5 and CSS parser
- **Valet** — HTTP client for network requests
- **Cryptosec** — TLS 1.3 for HTTPS
- **Squeeze** — Content-Encoding (gzip, deflate)
- **Prism** — Display server integration (on Harland)

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
fn render_page(document: Document) -> Bitmap    # const borrow
fn update_tab(tab:& Tab)                        # mutable borrow
fn close_tab(tab:= Tab)                         # move ownership

# Call sites are always clean
render_page(doc)
update_tab(tab)
close_tab(tab)
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
fn test_url_parsing() -> i32
    let url = parse_url("https://example.com/path")
    assert url.host == "example.com"
    0
```

### Error Handling

```ritz
fn fetch_page(url: StrView) -> Result<Response, Error>
    let conn = connect(url)?
    defer conn.close()

    let response = conn.request("GET", url)?
    Ok(response)
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

## Development Setup

```bash
export RITZ_PATH=~/dev/ritz-lang
cd $RITZ_PATH/tempest
```

### Building

```bash
make build
make test
```

### Project Structure

```
tempest/
├── src/
│   ├── main.ritz          # Entry point
│   ├── browser.ritz       # Browser shell
│   ├── tab.ritz           # Tab management
│   ├── history.ritz       # Navigation history
│   └── ui/                # User interface
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
