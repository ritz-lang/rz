# Tempest

Web browser built on the Ritz ecosystem - multi-process architecture with full HTML5, CSS, and JavaScript support.

**Part of the [Ritz Ecosystem](../ritz/docs/ECOSYSTEM.md)**

## Overview

Tempest is a web browser built entirely from the Ritz ecosystem libraries. It uses a multi-process architecture where the main browser process manages tabs, navigation, and network requests, while each tab runs in an isolated child process that handles DOM ownership, JavaScript execution, and rendering.

The browser delegates to dedicated ecosystem libraries for each component: Lexis parses HTML and CSS, Sage executes JavaScript, Iris computes layout and painting, Prism composites the final output to the display, cryptosec provides TLS 1.3 for HTTPS, squeeze handles content-encoding, and http implements the wire protocol.

Tempest demonstrates the Ritz ecosystem end-to-end: from raw TCP bytes arriving via Valet, through TLS decryption (cryptosec), HTTP parsing (http), HTML/CSS parsing (Lexis), JavaScript execution (Sage), layout (Iris), and final display (Prism).

## Features

> **Planned/partial.** The list below describes the design, not what runs today. See [Status](#status).

- Multi-process architecture (browser process + per-tab processes)
- HTML5 parsing via Lexis with streaming incremental rendering
- CSS cascade and computed styles via Lexis
- JavaScript execution via Sage (ECMAScript engine)
- Layout engine via Iris (block, inline, flexbox)
- Display compositing via Prism (windows, GPU layers)
- HTTP/1.1, HTTP/2, and HTTP/3 via http library
- TLS 1.3 HTTPS via cryptosec
- gzip/deflate content encoding via squeeze
- Tab isolation - a crashing tab cannot affect the browser

## Installation

```bash
# Build from source (run from the monorepo root; `rz` sets RITZ_PATH itself)
./rz build tempest
```

This builds both declared binaries, `build/debug/tempest` and
`build/debug/tempest-tab` (exit 0 since AGAST #3609). `./rz test tempest` runs
the `.ritz` tests under `test/`.

If tempest is ever excused as a known build failure, the reason is stated in
one place: its `gate = "build"` entry in [`known-failures/`](../../known-failures/).
This README does not copy it.

## Usage

Today `tempest` accepts only `--help`. Run with no arguments, it starts the
browser event loop, reports opening one tab and shuts down. It does not fetch
or render anything.

The intended CLI is:

```
tempest https://example.com                    # open a URL
tempest --debug-layout https://example.com     # with layout debugging
```

Neither works yet: the URL argument is ignored.

```ritz
# Browser process entry point
import http { Client }
import cryptosec { TlsContext }
import lexis { HtmlParser }
import sage { Engine }
import iris { RenderEngine }
import prism { Window }

fn main(argc: i32, argv: **u8) -> i32
    let window = prism_create_window(800, 600, "Tempest")
    let tab = spawn_tab_process(window.id)
    tab.navigate(argv[1])
    event_loop(window)
    0
```

```ritz
# Tab process entry point (tab_process.ritz)
fn main(argc: i32, argv: **u8) -> i32
    let renderer = iris_connect(prism_connect())
    let js_engine = sage_create()
    let parser = lexis_create(renderer, js_engine)
    let net = http_client_new()

    # Fetch and render the page
    let resp = net.get(url)
    parser.feed(resp.body, resp.body_len)
    0
```

## Architecture

```
Browser Process
  Tab management | Navigation | Network | UI chrome

Tab Process (one per tab)
  Lexis (parse) -> DOM (owned) <- Sage (JS)
                     |
                  StyleEvent
                     |
                   Iris (layout, paint)
                     |
                  IPC to Prism

Prism (display server)
  Compositor -> Framebuffer -> Screen
```

## Dependencies

- `http` - HTTP/1.1, HTTP/2, HTTP/3 wire protocol
- `cryptosec` - TLS 1.3 for HTTPS
- `squeeze` - Content-Encoding (gzip, deflate)
- `lexis` - HTML5 and CSS parsing
- `iris` - Layout, painting, and layer compositing
- `sage` - JavaScript engine
- `prism` - Display server and window compositor

## Status

**Builds; scaffolding only.** `./rz build tempest` exits 0 and `./rz test
tempest` passes (re-checked 2026-11-18), but the binary does not browse.

Browser and tab process scaffolding, the multi-process architecture and basic
navigation exist in source. [lexis](../lexis) builds and runs its built-in
demo; [sage](../sage) builds but ignores its arguments. End-to-end HTTPS browsing also
needs cryptosec TLS proven end to end, which has not been measured.

## License

MIT License - see LICENSE file
