# Lexis Design Document

HTML5 and CSS parser for the Tempest web browser.

## Architecture Overview

Lexis is a streaming parser that transforms HTML/CSS source into DOM events and computed styles.

```
┌─────────────────────────────────────────────────────────────┐
│                      TEMPEST PROCESS                         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                      LEXIS                            │   │
│  │  ┌─────────────┐    ┌──────────────┐    ┌──────────┐ │   │
│  │  │    HTML     │───▶│    Tree      │───▶│  DOM     │ │   │
│  │  │  Tokenizer  │    │   Builder    │    │ Events   │ │   │
│  │  └─────────────┘    └──────────────┘    └────┬─────┘ │   │
│  │                                              │       │   │
│  │  ┌─────────────┐    ┌──────────────┐         │       │   │
│  │  │    CSS      │───▶│  Selector    │         │       │   │
│  │  │   Parser    │    │   Engine     │         │       │   │
│  │  └─────────────┘    └──────┬───────┘         │       │   │
│  │                            │                 │       │   │
│  │                            ▼                 ▼       │   │
│  │                    ┌─────────────────────────────┐   │   │
│  │                    │        Cascade              │   │   │
│  │                    │  (specificity, inheritance) │   │   │
│  │                    └─────────────┬───────────────┘   │   │
│  │                                  │                   │   │
│  └──────────────────────────────────┼───────────────────┘   │
│                                     │ ComputedStyle          │
│                                     ▼                        │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                       TEMPEST                            ││
│  │  ┌─────────────┐     ┌───────────┐     ┌──────────────┐ ││
│  │  │     DOM     │◀───▶│   Sage    │     │    Debug     │ ││
│  │  │   (owned)   │     │   (JS)    │     │   Console    │ ││
│  │  └──────┬──────┘     └───────────┘     └──────────────┘ ││
│  │         │                                                ││
│  │         │ StyleEvent                                     ││
│  │         ▼                                                ││
│  │  ┌─────────────┐                                        ││
│  │  │    IRIS     │                                        ││
│  │  │  (render)   │                                        ││
│  │  └─────────────┘                                        ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Owns | Responsibility |
|-----------|------|----------------|
| **Lexis** | CSS rules, DOM types | HTML/CSS parsing, cascade, ComputedStyle |
| **Tempest** | DOM tree instances | Navigation, tabs, JS orchestration, DOM storage |
| **Iris** | Render tree | Layout, painting, hit testing |
| **Sage** | JS runtime | JavaScript execution, DOM mutations |

## Streaming Architecture

Lexis is a **streaming parser** — it processes input incrementally and emits events as they occur.

### Why Streaming?

1. **Incremental rendering** — Display content before full document loads
2. **Memory efficient** — Don't buffer entire document
3. **Natural for network** — Bytes arrive incrementally from Valet
4. **JS interop** — `document.write()` can inject into token stream

### Data Flow

```
Network (Valet)
    │
    ▼ bytes
┌─────────────────────┐
│   HTML Tokenizer    │  State machine, character-by-character
└──────────┬──────────┘
           │ Token
           ▼
┌─────────────────────┐
│   Tree Builder      │  HTML5 insertion modes, builds DOM events
└──────────┬──────────┘
           │ DOMEvent
           ▼
┌─────────────────────┐
│   Tempest DOM       │  Stores nodes, triggers style recalc
└──────────┬──────────┘
           │ (on style change)
           ▼
┌─────────────────────┐
│   Cascade Engine    │  Selector matching, specificity
└──────────┬──────────┘
           │ ComputedStyle
           ▼
┌─────────────────────┐
│   Iris (render)     │  Layout, paint
└─────────────────────┘
```

## DOM Event Protocol

Events Lexis emits during HTML parsing:

```ritz
enum DOMEvent
    # Document lifecycle
    DocumentStart
    DocumentEnd

    # Elements
    ElementStart { tag: StrView, attrs: Vec<Attribute>, self_closing: bool }
    ElementEnd { tag: StrView }

    # Content
    Text { content: StrView }
    Comment { content: StrView }

    # Stylesheets (inline <style> or external)
    StylesheetParsed { rules: Stylesheet }

    # Errors (Tempest routes to debug console)
    ParseError { kind: ParseErrorKind, message: StrView, line: u32, col: u32 }
    ParseWarning { kind: ParseWarningKind, message: StrView, line: u32, col: u32 }
```

## HTML Tokenizer

The tokenizer is a state machine that converts characters into tokens.

### State Machine

```
┌─────────────────┐
│    Data         │◀─────────────────────────────────┐
│    State        │                                   │
└────────┬────────┘                                   │
         │ '<'                                        │
         ▼                                            │
┌─────────────────┐  '!'   ┌──────────────────────┐  │
│  Tag Open       │───────▶│  Markup Declaration  │  │
│  State          │        │  (comment, doctype)  │  │
└────────┬────────┘        └──────────────────────┘  │
         │ alpha                                      │
         ▼                                            │
┌─────────────────┐  '>'   ┌──────────────────────┐  │
│  Tag Name       │───────▶│  Emit StartTag       │──┘
│  State          │        └──────────────────────┘
└────────┬────────┘
         │ space
         ▼
┌─────────────────┐
│  Attribute      │
│  States...      │
└─────────────────┘
```

### Key States (from HTML5 spec)

- `Data` — Normal content
- `TagOpen` — After `<`
- `TagName` — Reading tag name
- `SelfClosingStartTag` — After `/` in tag
- `BeforeAttributeName` — After tag name, before attributes
- `AttributeName` — Reading attribute name
- `AfterAttributeName` — After attribute name
- `BeforeAttributeValue` — After `=`
- `AttributeValueDoubleQuoted` — In `"..."`
- `AttributeValueSingleQuoted` — In `'...'`
- `AttributeValueUnquoted` — Unquoted value
- `AfterAttributeValueQuoted` — After closing quote
- `BogusComment` — Error recovery
- `MarkupDeclarationOpen` — After `<!`
- `CommentStart` — In `<!--`
- `DOCTYPE` — In `<!DOCTYPE`
- `RAWTEXT` — Inside `<script>`, `<style>`, etc.
- `RCDATA` — Inside `<textarea>`, `<title>`
- ... (80+ states total in full spec)

### Tokens

```ritz
enum HtmlToken
    DOCTYPE { name: StrView, public_id: Option<StrView>, system_id: Option<StrView> }
    StartTag { name: StrView, attrs: Vec<Attribute>, self_closing: bool }
    EndTag { name: StrView }
    Character { char: char }
    Comment { data: StrView }
    EOF
```

## Tree Builder

The tree builder implements HTML5's insertion modes to construct the DOM.

### Insertion Modes

- `Initial` — Before DOCTYPE
- `BeforeHtml` — Before `<html>`
- `BeforeHead` — Before `<head>`
- `InHead` — Inside `<head>`
- `AfterHead` — After `</head>`, before `<body>`
- `InBody` — Inside `<body>`
- `Text` — Inside `<script>`, `<style>`
- `InTable` — Inside `<table>`
- `InTableBody` — Inside `<tbody>`, `<thead>`, `<tfoot>`
- `InRow` — Inside `<tr>`
- `InCell` — Inside `<td>`, `<th>`
- `InSelect` — Inside `<select>`
- `AfterBody` — After `</body>`
- `AfterAfterBody` — After `</html>`
- ... (more for frameset, etc.)

### Stack of Open Elements

The tree builder maintains a stack of open elements for proper nesting:

```ritz
struct TreeBuilder
    # Stack of open element tags
    open_elements: Vec<StackEntry>

    # Current insertion mode
    insertion_mode: InsertionMode

    # Original insertion mode (for returning from Text mode)
    original_insertion_mode: InsertionMode

    # Head element pointer (for later insertion)
    head_pointer: Option<NodeId>

    # Form element pointer (for form association)
    form_pointer: Option<NodeId>

    # Event sink for emitting DOM events
    event_sink: fn(DOMEvent)
```

### Adoption Agency Algorithm

For handling misnested formatting elements like:
```html
<p><b>bold <i>bold-italic</b> italic</i></p>
```

The adoption agency algorithm properly closes and reopens tags.

## CSS Tokenizer

The CSS tokenizer converts CSS source into tokens per CSS Syntax Module Level 3.

### Token Types

```ritz
enum CssToken
    # Identifiers and strings
    Ident { value: StrView }
    Function { name: StrView }      # "rgba("
    AtKeyword { name: StrView }     # "@media"
    Hash { value: StrView, is_id: bool }  # "#foo"
    String { value: StrView }
    Url { value: StrView }

    # Numbers
    Number { value: f64, int_value: Option<i64>, has_sign: bool }
    Percentage { value: f64 }
    Dimension { value: f64, unit: StrView }

    # Punctuation
    Delim { char: char }
    Colon
    Semicolon
    Comma
    OpenSquare           # [
    CloseSquare          # ]
    OpenParen            # (
    CloseParen           # )
    OpenCurly            # {
    CloseCurly           # }

    # Special
    Whitespace
    Comment
    CDO                  # <!--
    CDC                  # -->
    EOF
```

## CSS Parser

Parses tokens into stylesheet structure.

### Stylesheet Structure

```ritz
struct Stylesheet
    rules: Vec<CSSRule>

enum CSSRule
    Style { selector: Selector, declarations: Vec<Declaration> }
    AtRule { name: StrView, prelude: Vec<CssToken>, block: Option<Block> }
    # @media, @import, @keyframes, etc.

struct Declaration
    property: StrView
    value: CSSValue
    important: bool

struct Selector
    components: Vec<SelectorComponent>
    specificity: Specificity

enum SelectorComponent
    # Simple selectors
    Universal                           # *
    Type { name: StrView }              # div
    Id { name: StrView }                # #foo
    Class { name: StrView }             # .bar
    Attribute { name: StrView, matcher: AttrMatcher, value: Option<StrView> }
    PseudoClass { name: StrView, arg: Option<StrView> }
    PseudoElement { name: StrView }

    # Combinators
    Descendant                          # space
    Child                               # >
    NextSibling                         # +
    SubsequentSibling                   # ~
```

## Selector Engine

High-performance selector matching using multiple optimization techniques.

### Rule Indexing

At stylesheet parse time, rules are indexed for fast lookup:

```ritz
struct SelectorMap
    # Index by rightmost simple selector
    id_rules: HashMap<StrView, Vec<RuleEntry>>
    class_rules: HashMap<StrView, Vec<RuleEntry>>
    tag_rules: HashMap<StrView, Vec<RuleEntry>>
    universal_rules: Vec<RuleEntry>

struct RuleEntry
    selector: Selector
    declarations: Vec<Declaration>
    specificity: Specificity
    source_order: u32
```

When matching element `<div class="foo bar" id="main">`:
1. Look up `id_rules["main"]`
2. Look up `class_rules["foo"]`
3. Look up `class_rules["bar"]`
4. Look up `tag_rules["div"]`
5. Check `universal_rules`
6. Collect all, sort by specificity

### Bloom Filter

Fast rejection of ancestor selectors:

```ritz
struct AncestorFilter
    filter: [u64; 4]  # 256-bit bloom filter

fn insert(filter:& AncestorFilter, hash: u32)
    let bit = hash % 256
    filter.filter[bit / 64] |= (1u64 << (bit % 64))

fn might_contain(filter: AncestorFilter, hash: u32) -> bool
    let bit = hash % 256
    (filter.filter[bit / 64] & (1u64 << (bit % 64))) != 0
```

Each element's filter = parent's filter + element's ID/class/tag hashes.

For selector `div.foo .bar`:
- If `might_contain(element.ancestor_filter, hash("foo"))` is false → no match
- Quickly reject without walking ancestors

### Right-to-Left Matching

Match the rightmost (key) selector first, then verify ancestors:

```
Selector: div.container > ul.menu > li.item

Matching against <li class="item">:
1. Match key selector "li.item" against element → YES
2. Walk to parent, match "ul.menu" → YES
3. Parent must be direct child, check ">" → YES
4. Walk to parent, match "div.container" → YES
5. MATCH!
```

Most selectors fail at step 1, so this is very efficient.

## Cascade Algorithm

Determine final property values per CSS Cascading and Inheritance Level 5.

### Cascade Layers

1. **Origin** — User agent < User < Author
2. **Importance** — Normal < !important (reversed for UA/User)
3. **@layer** — Later layers override earlier
4. **Specificity** — (ID count, class count, type count)
5. **Source order** — Later declarations win

### Inheritance

Some properties inherit by default (e.g., `color`, `font-family`).
Others don't (e.g., `width`, `margin`).

```ritz
fn compute_style(
    element: Element,
    matching_rules: Vec<RuleEntry>,
    parent_style: Option<ComputedStyle>
) -> ComputedStyle
    var style = computed_style_default()

    # Sort by cascade order
    let sorted = sort_by_cascade(matching_rules)

    # Apply each declaration
    for rule in sorted
        for decl in rule.declarations
            apply_declaration(@&style, decl)

    # Inherit from parent
    if parent_style.is_some()
        inherit_properties(@&style, parent_style.unwrap())

    style
```

## Dependencies

- **iris.lib.style.types** — ComputedStyle, Display, Position, etc.
- **prism.api** — Color (shared primitive)

## Module Structure

```
lexis/
├── lib/
│   ├── lexis.ritz              # Main API
│   │
│   ├── dom/
│   │   ├── mod.ritz
│   │   ├── node.ritz           # Node, Element, Text, Document
│   │   ├── attribute.ritz      # Attribute handling
│   │   └── tag.ritz            # HTML tag enum
│   │
│   ├── html/
│   │   ├── mod.ritz
│   │   ├── tokenizer.ritz      # State machine tokenizer
│   │   ├── token.ritz          # HTML token types
│   │   ├── tree_builder.ritz   # HTML5 insertion modes
│   │   ├── entities.ritz       # Character entity decoding
│   │   └── input_stream.ritz   # Buffered character stream
│   │
│   ├── css/
│   │   ├── mod.ritz
│   │   ├── tokenizer.ritz      # CSS tokenizer
│   │   ├── token.ritz          # CSS token types
│   │   ├── parser.ritz         # Parse rules from tokens
│   │   ├── selector.ritz       # Selector types and parsing
│   │   ├── value.ritz          # CSS value types and parsing
│   │   └── stylesheet.ritz     # Stylesheet, CSSRule
│   │
│   ├── style/
│   │   ├── mod.ritz
│   │   ├── selector_map.ritz   # Indexed rules by ID/class/tag
│   │   ├── bloom.ritz          # Ancestor bloom filter
│   │   ├── matching.ritz       # Right-to-left selector matching
│   │   ├── specificity.ritz    # Specificity calculation
│   │   ├── cascade.ritz        # Cascade algorithm
│   │   └── computed.ritz       # ComputedStyle builder
│   │
│   └── event.ritz              # DOMEvent enum
│
├── src/
│   └── main.ritz               # CLI for testing
│
└── tests/
    ├── test_html_tokenizer.ritz
    ├── test_tree_builder.ritz
    ├── test_css_tokenizer.ritz
    ├── test_css_parser.ritz
    ├── test_selector_matching.ritz
    ├── test_specificity.ritz
    └── test_cascade.ritz
```

## MVP Phases

### Phase 1: Foundation
- [ ] DOM types (Node, Element, Text, Attribute)
- [ ] HTML tag enum
- [ ] Basic HTML tokenizer (enough for simple tags)
- [ ] Basic tree builder (no complex insertion modes)

### Phase 2: HTML Compliance
- [ ] Full tokenizer state machine
- [ ] Character entity decoding
- [ ] All insertion modes
- [ ] Adoption agency algorithm
- [ ] Parse error handling

### Phase 3: CSS Parsing
- [ ] CSS tokenizer
- [ ] Selector parsing
- [ ] Declaration parsing
- [ ] Stylesheet structure

### Phase 4: Selector Engine
- [ ] Rule indexing (ID, class, tag maps)
- [ ] Right-to-left matching
- [ ] Bloom filter for ancestors
- [ ] Specificity calculation

### Phase 5: Cascade
- [ ] Cascade algorithm
- [ ] Inheritance
- [ ] ComputedStyle generation
- [ ] !important handling

### Phase 6: Polish
- [ ] @media queries
- [ ] @import handling
- [ ] CSS custom properties (variables)
- [ ] Shorthand property expansion

## Error Handling

HTML parsing is lenient — browsers accept broken HTML. Lexis does too.

Parse errors are reported via events:
```ritz
DOMEvent.ParseError {
    kind: ParseErrorKind.UnexpectedToken,
    message: "Unexpected end tag 'div' in body",
    line: 42,
    col: 15
}
```

CSS parsing drops invalid rules:
```ritz
DOMEvent.ParseWarning {
    kind: ParseWarningKind.InvalidProperty,
    message: "Unknown property 'colr' (did you mean 'color'?)",
    line: 10,
    col: 3
}
```

Tempest routes these to the debug console.

---

*Part of the Ritz ecosystem. See `larb/AGENT.md` for full guidelines.*
