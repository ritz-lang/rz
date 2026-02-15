# Issues Needed in Other Projects

This document tracks dependencies Tempest needs from other projects in the Ritz ecosystem.

---

## ritz-lang/ritz (ritzlib)

### HIGH PRIORITY

#### 1. `ritzlib.ipc` - Ringbuffer IPC
**Status:** Unknown - need to check Zeus implementation
**Required for:** Multi-process tab architecture

Tempest needs the same IPC mechanism Zeus uses for browser ↔ tab process communication.

```ritz
# What we need:
pub fn ringbuffer_create(size: i64) -> Ringbuffer
pub fn ringbuffer_write(rb: *Ringbuffer, data: *u8, len: i64) -> i64
pub fn ringbuffer_read(rb: *Ringbuffer, buf: *u8, len: i64) -> i64
```

#### 2. `ritzlib.sys` - Process spawning
**Status:** Partial (fork exists)
**Required for:** Spawning tab processes

```ritz
# What we need:
pub fn sys_fork() -> i32
pub fn sys_execve(path: *u8, argv: **u8, envp: **u8) -> i32
pub fn sys_waitpid(pid: i32, status: *i32, options: i32) -> i32
pub fn sys_kill(pid: i32, sig: i32) -> i32
```

### MEDIUM PRIORITY

#### 3. `ritzlib.gvec` - Vec operations
**Status:** Basic implementation exists
**Required for:** DOM tree, collections

```ritz
# What we need (if not present):
pub fn vec_set<T>(v: *Vec<T>, index: i64, value: T)
pub fn vec_pop<T>(v: *Vec<T>) -> Option<T>
pub fn vec_truncate<T>(v: *Vec<T>, len: i64)
pub fn vec_remove<T>(v: *Vec<T>, index: i64) -> T
```

#### 4. `ritzlib.time` - Timestamps
**Status:** Unknown
**Required for:** History timestamps, cookie expiry, JS timers

```ritz
# What we need:
pub fn time_now_ms() -> i64          # Milliseconds since epoch
pub fn time_monotonic_ms() -> i64    # Monotonic clock for timers
```

---

## ritz-lang/http

### HIGH PRIORITY

#### 1. DNS Resolution
**Status:** Not implemented
**Required for:** Connecting to hosts by name

The http library has TCP sockets but only supports IP addresses. Need DNS resolution.

```ritz
# What we need:
pub fn dns_resolve(hostname: *StrView) -> Result<Vec<IpAddr>, DnsError>
# Or integration with system resolver
```

#### 2. TLS Integration
**Status:** TODO (marked in http/TODO.md)
**Required for:** HTTPS

Integration between http and cryptosec for TLS connections.

```ritz
# What we need:
pub fn h1_connect_tls(host: *StrView, port: i32) -> Result<TlsConnection, Error>
```

#### 3. Content-Encoding Integration
**Status:** TODO (marked in http/TODO.md)
**Required for:** Decompressing gzip/deflate responses

Integration between http and squeeze for automatic decompression.

---

## ritz-lang/prism

### HIGH PRIORITY

#### 1. Client Connection API
**Status:** Design done, implementation needed
**Required for:** Displaying browser window

```ritz
# What we need (from Prism API contract):
pub fn prism_connect() -> PrismClient
pub fn prism_create_window(client: *PrismClient, width: u32, height: u32) -> Window
pub fn prism_poll_event(client: *PrismClient) -> Option<WindowEvent>
pub fn prism_get_draw_context(window: *Window) -> DrawContext
pub fn prism_present(window: *Window)
```

#### 2. Widget System (Basic)
**Status:** Unknown
**Required for:** Browser chrome (tabs, URL bar)

Native Prism widgets for browser UI:
- Button
- TextInput (with selection, cursor)
- TabBar
- Label

---

## ritz-lang/lexis

### HIGH PRIORITY

#### 1. HTML Parser
**Status:** Design done (streaming/event-based)
**Required for:** Parsing HTML pages

```ritz
# What we need (from design session):
pub fn lexis_parser_new() -> LexisParser
pub fn lexis_feed(parser: *LexisParser, data: *StrView) -> i32
pub fn lexis_poll_event(parser: *LexisParser) -> Option<ParseEvent>
```

#### 2. CSS Parser + Cascade
**Status:** Design done
**Required for:** Styling pages

```ritz
# What we need:
pub fn lexis_parse_css(css: *StrView) -> Stylesheet
pub fn style_compute(computer: *StyleComputer, ...) -> ComputedStyle
```

#### 3. Selector Engine
**Status:** Design done (bloom filters, rule indexing)
**Required for:** querySelector, CSS matching

```ritz
# What we need:
pub fn lexis_matches_selector(selector: *StrView, ...) -> i32
pub fn lexis_query_selector(doc: *Document, selector: *StrView) -> Option<NodeId>
```

---

## ritz-lang/iris

### HIGH PRIORITY

#### 1. StyleEvent Processing
**Status:** Design done
**Required for:** Rendering DOM changes

```ritz
# What we need (from design session):
pub fn iris_connect() -> IrisClient
pub fn iris_send_events(client: *IrisClient, events: *Vec<StyleEvent>)
```

#### 2. Hit Testing
**Status:** Design done
**Required for:** Click handling

```ritz
# What we need:
pub fn iris_hit_test(client: *IrisClient, x: i32, y: i32) -> HitTestResult
```

#### 3. Scroll Notifications
**Status:** Design done
**Required for:** JS scroll events

```ritz
# What we need:
pub fn iris_poll_scroll(client: *IrisClient) -> Option<ScrollNotification>
```

---

## ritz-lang/sage

### MEDIUM PRIORITY (Phase 4)

#### 1. JS Context Management
**Status:** Stub
**Required for:** Running JavaScript

```ritz
# What we need:
pub fn sage_context_new() -> SageContext
pub fn sage_execute(ctx: *SageContext, script: *StrView) -> i32
```

#### 2. DOM Bindings Interface
**Status:** Not started
**Required for:** JS DOM manipulation

Sage needs a callback mechanism so Tempest can implement DOM operations.

```ritz
# What we need:
pub type DomCallback = fn(request: DomRequest) -> DomResult
pub fn sage_set_dom_callback(ctx: *SageContext, callback: DomCallback)
```

---

## Summary by Priority

### Phase 1: Static Page Display
| Project | Issue | Blocking? |
|---------|-------|-----------|
| prism | Client connection API | YES |
| prism | Basic widgets | YES |
| lexis | HTML parser | YES |
| lexis | CSS parser | YES |
| iris | StyleEvent processing | YES |
| http | DNS resolution | YES |
| http | TLS integration | YES |

### Phase 2: Navigation
| Project | Issue | Blocking? |
|---------|-------|-----------|
| iris | Hit testing | YES |
| ritz | Process spawning | YES |
| ritz | IPC ringbuffers | YES |

### Phase 3: JavaScript
| Project | Issue | Blocking? |
|---------|-------|-----------|
| sage | JS context | YES |
| sage | DOM bindings | YES |
| iris | Scroll notifications | YES |

---

## Notes

- Tempest can start development with stubs for all external dependencies
- Each component can be implemented incrementally
- The multi-process architecture is ready but requires ritzlib.ipc
- Browser chrome (tabs, URL bar) requires Prism widget system
