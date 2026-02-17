# Tempest

Web browser written in Ritz. Active development.

---

## Overview

Tempest is a complete web browser built on the Ritz ecosystem. Every component — from HTML parsing to TLS to the rendering engine — is written in Ritz. Tempest demonstrates the power of the full Ritz stack assembled into a real application.

---

## Where It Fits

```
┌─────────────────────────────────────────────────────┐
│                     TEMPEST                          │
│              Browser Shell and UI                    │
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

---

## Component Responsibilities

| Component | Project | Responsibility |
|-----------|---------|----------------|
| Browser Shell | Tempest | Tab management, URL bar, bookmarks, history, settings |
| Rendering | [Iris](iris.md) | Box model layout, painting, compositing |
| JavaScript | [Sage](sage.md) | JS parsing, compilation, bytecode execution |
| HTML/CSS Parsing | [Lexis](lexis.md) | HTML5 tokenization, DOM construction, CSS cascade |
| HTTP Networking | [Valet HTTP](http.md) | HTTP/1.1 and HTTP/2 client |
| TLS | [Cryptosec](cryptosec.md) | HTTPS via TLS 1.3 |
| Compression | [Squeeze](squeeze.md) | gzip/deflate content decompression |
| Display | [Prism](prism.md) | Window management (on Harland) |

---

## Browser Architecture

### Tab Model

Each tab is an independent unit:

```ritz
struct Tab
    id: TabId
    url: String
    title: String
    document: Option<Document>     # From Lexis
    history: Vec<HistoryEntry>
    loading: bool
```

### Navigation Flow

```
User types URL or clicks link
        │
        ▼
Fetch HTML via Valet HTTP + Cryptosec TLS
        │
        ▼
Lexis: Parse HTML → Document tree
Lexis: Parse CSS → Stylesheets → Computed styles
        │
        ▼
Iris: Layout (box model, flexbox, text)
        │
        ▼
Iris: Paint (drawing primitives, text glyphs)
        │
        ▼
Iris: Composite (layers → final bitmap)
        │
        ▼
Prism: Display bitmap in window
```

### JavaScript Execution

```
<script> tag encountered during HTML parsing
        │
        ▼
Sage: Tokenize → Parse → AST
        │
        ▼
Sage: Compile AST → Bytecode
        │
        ▼
Sage: Execute bytecode in VM
        │
        ▼ DOM API calls
Lexis/Iris: DOM mutation, style updates
        │
        ▼
Iris: Re-layout and repaint affected regions
```

---

## Project Structure

```
tempest/
├── src/
│   ├── main.ritz          # Entry point
│   ├── browser.ritz       # Browser shell, tab management
│   ├── tab.ritz           # Individual tab state and lifecycle
│   ├── history.ritz       # Navigation history
│   ├── bookmarks.ritz     # Bookmark management
│   └── ui/                # User interface components
├── tests/
└── ritz.toml
```

---

## No Concessions

Tempest follows the Ritz "No Concessions" doctrine: if Ritz cannot express something cleanly, the language is fixed, not worked around. Any language limitation discovered while building Tempest becomes a proposal for a Ritz language improvement.

---

## Current Status

Active development. Component integration in progress.

---

## Related Projects

- [Iris](iris.md) — Rendering engine
- [Sage](sage.md) — JavaScript engine
- [Lexis](lexis.md) — HTML5 and CSS parser
- [HTTP](http.md) — HTTP client library
- [Cryptosec](cryptosec.md) — TLS 1.3 for HTTPS
- [Squeeze](squeeze.md) — Content decompression
- [Prism](prism.md) — Display server (on Harland)
