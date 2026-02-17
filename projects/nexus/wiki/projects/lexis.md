# Lexis

HTML5 and CSS parser written in Ritz. Active development.

---

## Overview

Lexis parses HTML and CSS source documents into a typed, styled document tree that Iris can use for layout and rendering. It follows the HTML5 parsing specification and CSS3 standards.

---

## Where It Fits

```
Raw HTML + CSS (fetched by Valet HTTP client)
        │
        ▼
     LEXIS
        ├── HTML Tokenizer (characters → tokens)
        ├── Tree Builder (tokens → DOM nodes)
        ├── CSS Parser (stylesheet → rules)
        └── Style Resolver (DOM + CSS → computed styles)
                │
                ▼
         Styled Document Tree
                │
                ▼
          IRIS (rendering)
```

---

## Responsibilities

- **HTML5 parsing** — Compliant tokenization and tree construction, including error recovery
- **DOM construction** — Element, text, comment, and document nodes
- **CSS parsing** — Selectors, properties, values, at-rules
- **Style resolution** — Cascade, specificity, computed styles
- **Selector matching** — CSS selectors applied to DOM tree

## Non-Responsibilities

- Layout and rendering (Iris)
- JavaScript execution (Sage)
- Network requests (Valet/HTTP)

---

## Architecture

```
HTML Source
    │
    ▼ HTML Tokenizer
Token stream (StartTag, EndTag, Text, Comment, ...)
    │
    ▼ Tree Builder
Document
    ├── <html>
    │   ├── <head>
    │   │   └── <style> (triggers CSS parsing)
    │   └── <body>
    │       ├── <h1>Welcome</h1>
    │       └── <p class="intro">...</p>
    │
    ▼ CSS Parser
Stylesheet
    ├── .intro { color: blue; font-size: 16px; }
    └── h1 { font-weight: bold; }
    │
    ▼ Style Resolver (cascade + specificity)
Styled Document
    └── Each element has computed style properties
```

---

## Core Types

```ritz
# DOM node types
enum Node
    Document(Document)
    Element(Element)
    Text(String)
    Comment(String)

struct Element
    tag: String
    attributes: HashMap<String, String>
    children: Vec<Node>
    computed_style: ComputedStyle

# CSS
struct Stylesheet
    rules: Vec<Rule>

struct Rule
    selectors: Vec<Selector>
    declarations: Vec<Declaration>

struct Declaration
    property: String
    value: CssValue

struct ComputedStyle
    color: Color
    background_color: Color
    font_size: f32
    font_family: String
    display: Display
    width: Length
    height: Length
    margin: BoxSpacing
    padding: BoxSpacing
    # ... all CSS properties
```

---

## HTML5 Parsing Algorithm

Lexis follows the HTML5 parsing specification which defines specific error recovery behavior:

```ritz
fn parse_html(source: StrView) -> Result<Document, ParseError>
    let tokens = tokenize_html(source)
    let doc = build_tree(tokens)
    Ok(doc)

# The tokenizer handles malformed HTML:
# <p>Hello <b>world  (missing closing tags)
# is recovered as:
# <p>Hello <b>world</b></p>
```

### HTML5 Tokenizer States

The HTML5 specification defines 80+ tokenizer states. Key states:

- Data state (default)
- Tag open state (`<`)
- Tag name state (element name)
- Before attribute name state
- Attribute name/value states
- Script data states (special handling for `<script>`)

---

## CSS Parsing

### Selector Support

| Selector Type | Example | Status |
|---------------|---------|--------|
| Type selector | `p` | Planned |
| Class selector | `.intro` | Planned |
| ID selector | `#main` | Planned |
| Universal | `*` | Planned |
| Attribute | `[href]`, `[type="text"]` | Planned |
| Descendant | `div p` | Planned |
| Child | `ul > li` | Planned |
| Adjacent | `h1 + p` | Planned |
| Pseudo-class | `:hover`, `:first-child` | Planned |

### Cascade Algorithm

1. Collect all rules matching each element
2. Sort by specificity (ID > class > element)
3. Sort by source order (later rules win)
4. Apply `!important` overrides
5. Fall back to browser defaults for unset properties

---

## Testing

```ritz
[[test]]
fn test_basic_html() -> i32
    let doc = parse_html("<div class='test'>Hello</div>").unwrap()
    let div = doc.query_selector("div.test").unwrap()
    assert div.text_content() == "Hello"
    assert div.get_attribute("class") == Some("test")
    0

[[test]]
fn test_css_cascade() -> i32
    let doc = parse_html("
        <style>p { color: red; } .blue { color: blue; }</style>
        <p class='blue'>text</p>
    ").unwrap()
    let p = doc.query_selector("p").unwrap()
    # Class specificity wins over element
    assert p.computed_style.color == Color.blue()
    0
```

---

## Project Structure

```
lexis/
├── src/
│   ├── html/
│   │   ├── tokenizer.ritz  # HTML5 tokenizer (80+ states)
│   │   ├── parser.ritz     # Tree builder
│   │   └── entities.ritz   # HTML entity decoding (&amp; etc.)
│   ├── css/
│   │   ├── tokenizer.ritz  # CSS tokenizer
│   │   ├── parser.ritz     # CSS rule parser
│   │   ├── selector.ritz   # Selector matching engine
│   │   └── cascade.ritz    # Style resolution
│   └── dom/
│       ├── node.ritz       # Node types
│       ├── element.ritz    # Element operations
│       └── document.ritz   # Document root, query_selector
├── tests/
└── ritz.toml
```

---

## Current Status

Active development. HTML tokenizer implementation in progress.

---

## Related Projects

- [Iris](iris.md) — Rendering engine that consumes Lexis output
- [Sage](sage.md) — JavaScript engine that interacts with the DOM Lexis builds
- [Tempest](tempest.md) — Browser that uses Lexis
