# Lexis

HTML5 and CSS parser for the Tempest web browser - streaming tokenization, DOM events, and style cascade.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

## Overview

Lexis is the parsing layer for the Tempest web browser. It transforms raw HTML and CSS source bytes into structured DOM events and computed styles that Tempest can use to build and update its DOM tree. The parser is streaming - it processes input incrementally and emits events as they occur, enabling the browser to begin rendering before the full document has loaded.

The HTML tokenizer implements the HTML5 parsing algorithm as a state machine, handling the quirks and error recovery requirements of real-world web content. The CSS parser resolves the cascade, specificity, and inheritance rules to produce a `ComputedStyle` for each element. Lexis delivers `ComputedStyle` objects to Tempest, which forwards them as `StyleEvent` streams to Iris for layout and rendering.

## Features

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
# Build from source
export RITZ_PATH=/path/to/ritz
./ritz build .

# Run the parser on an HTML file
./build/debug/lexis index.html
```

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

**Alpha** - HTML tokenizer, CSS parser scaffolding, and test infrastructure are in place. Core HTML5 tokenization, CSS selector matching, and cascade resolution are being implemented. Full HTML5 spec compliance and full CSS3 property coverage are planned for subsequent phases.

## License

MIT License - see LICENSE file
