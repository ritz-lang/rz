# Lexis - HTML5 and CSS Parser

HTML5 and CSS parser written in Ritz.

---

## Project Overview

Lexis is a standalone parser for HTML5 and CSS. It produces a document tree suitable for rendering engines.

### Responsibilities

- **HTML Parsing** — HTML5 compliant parsing, DOM construction
- **CSS Parsing** — CSS3 parsing, selector matching
- **Style Resolution** — Cascade, specificity, computed styles
- **Document Tree** — DOM-like tree structure

### Non-Responsibilities

Lexis does NOT handle:
- Layout/rendering (use Iris)
- JavaScript execution (use Sage)
- Network requests (use Valet)

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   HTML Source                        │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                  HTML TOKENIZER                      │
│              Character → Tokens                      │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                  TREE BUILDER                        │
│              Tokens → Document                       │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌───────────────────────┴─────────────────────────────┐
│                                                      │
│  ┌─────────────────┐      ┌─────────────────────┐   │
│  │  CSS PARSER     │      │  STYLE RESOLVER     │   │
│  │  Stylesheets    │ ───▶ │  Computed Styles    │   │
│  └─────────────────┘      └─────────────────────┘   │
│                                                      │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                  STYLED DOCUMENT                     │
│           (Ready for Iris rendering)                 │
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
fn parse_html(source: StrView) -> Result<Document, ParseError>
fn parse_css(source: StrView) -> Stylesheet
fn resolve_styles(doc:& Document, sheets: Vec<Stylesheet>)
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
fn test_html_parsing() -> i32
    let doc = parse_html("<div class='test'>Hello</div>").unwrap()
    let div = doc.query_selector("div.test").unwrap()
    assert div.text_content() == "Hello"
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
lexis/
├── src/
│   ├── html/
│   │   ├── tokenizer.ritz  # HTML5 tokenizer
│   │   ├── parser.ritz     # Tree builder
│   │   └── entities.ritz   # HTML entities
│   ├── css/
│   │   ├── tokenizer.ritz  # CSS tokenizer
│   │   ├── parser.ritz     # CSS parser
│   │   ├── selector.ritz   # Selector matching
│   │   └── cascade.ritz    # Style resolution
│   └── dom/
│       ├── node.ritz       # DOM nodes
│       ├── element.ritz    # Element nodes
│       └── document.ritz   # Document root
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
