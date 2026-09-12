# Lexis

HTML5 and CSS parser for the Tempest web browser - streaming tokenization, DOM events, and style cascade.

**Part of the [Ritz Ecosystem](../ritz/docs/ECOSYSTEM.md)**

## Overview

Lexis is the parsing layer for the Tempest web browser. It transforms raw HTML and CSS source bytes into structured DOM events and computed styles that Tempest can use to build and update its DOM tree. The parser is streaming - it processes input incrementally and emits events as they occur, enabling the browser to begin rendering before the full document has loaded.

The HTML tokenizer implements the HTML5 parsing algorithm as a state machine, handling the quirks and error recovery requirements of real-world web content. The CSS parser resolves the cascade, specificity, and inheritance rules to produce a `ComputedStyle` for each element. Lexis delivers `ComputedStyle` objects to Tempest, which forwards them as `StyleEvent` streams to Iris for layout and rendering.

## Features

> **Planned/partial.** The list below describes the design. See [Status](#status) — lexis does not currently compile (AGAST #1289).

- HTML5 streaming tokenizer (state machine)
- Incremental DOM event emission - render before full load
- CSS parser with selector engine
- Cascade resolution (specificity, inheritance, `!important`)
- Computed style calculation
- `document.write()` token stream injection for JavaScript
- Error recovery for malformed HTML
- Full CSS selector matching (class, ID, element, pseudo-class)

## Installation

```bash
# Build from source (run from the monorepo root; `rz` sets RITZ_PATH itself)
./rz build lexis
```

**This build currently fails (exit 1).** `lexis` does not compile: the ownership
checker reports 424 "use of moved value" errors across 13 files, the largest
being `lib/html/tree_builder.ritz`. It is tracked as **AGAST #1289** and is
listed in the workspace manifest's `[ci.known_failing.build]`, so `rz build
--all` reports it as an advisory failure rather than gating.

Consequently there is no `lexis` binary — `projects/lexis/build/debug/` is
empty, and the `./build/debug/lexis index.html` invocation this README used to
document cannot work until #1289 is fixed.

## Usage

```ritz
import lib.html { HtmlParser, DomEvent }
import lib.css { CssParser, ComputedStyle }

# Streaming HTML parse
let parser = HtmlParser.new()
parser.set_handler(fn(event: DomEvent)
    match event.kind
        DomEventKind.ElementOpen  => tempest.open_element(event.tag, event.attrs)
        DomEventKind.ElementClose => tempest.close_element(event.tag)
        DomEventKind.Text         => tempest.append_text(event.text)
)

# Feed bytes incrementally (as they arrive from network)
parser.feed(bytes, byte_count)
```

```ritz
# CSS parsing and cascade
let css_parser = CssParser.new()
css_parser.parse(stylesheet_source, stylesheet_len)

# Compute styles for an element
let style = css_parser.compute_style(element_tag, element_classes, element_id, parent_style)
# style is now a ComputedStyle with all properties resolved
```

## Dependencies

Lexis has no required dependencies beyond `ritzlib`. Future integration with Iris and Prism for pipeline testing is planned.

## Status

**Does not compile.** This is the honest headline; the README previously said
"Alpha — … in place", which reads as though it builds.

`./rz build lexis` exits 1. The ownership checker reports **424** "use of moved
value" errors across 13 files — `lib/style/cascade.ritz`, `lib/lexis.ritz`,
`src/main.ritz` and, largest of all, `lib/html/tree_builder.ritz`. Tracked as
**AGAST #1289**; cross-check **#1315** (suspected move-checker false positive)
before changing source, because some of those 424 may not be real defects.

There is no binary, so nothing here can be run or tested end to end. The HTML
tokenizer, CSS parser and cascade code all exist in `lib/` — the blocker is
getting them past the move checker, not writing them. Downstream,
[tempest](../tempest) and [iris](../iris) cannot exercise a real parse until this
is fixed.

## License

MIT License - see LICENSE file
