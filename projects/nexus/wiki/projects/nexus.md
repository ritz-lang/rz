# Nexus

*The Ritz Knowledge Base.*

*(Protoss Nexus — the heart of the hive.)*

Official Ritz documentation wiki and reference implementation of the full Ritz stack. Design phase.

---

## Overview

Nexus is two things simultaneously:

1. **A Wiki** — The authoritative documentation for the Ritz language, standard library, and ecosystem. This very page you are reading is Nexus content.

2. **A Reference Implementation** — Built on every layer of the Ritz stack. Nexus demonstrates that the ecosystem is production-capable by eating its own cooking.

---

## Where It Fits

Nexus sits at the top of the Ritz web stack:

```
NEXUS (wiki application)
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│                         SPIRE                             │
│               MVRSPT Web Framework                        │
│   Model │ View │ Repo │ Service │ Presenter │ Tests      │
└───────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│                         ZEUS                              │
│                   App Server                              │
└───────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│                        VALET                              │
│                  HTTP/1.1 + TLS 1.3                       │
└───────────────────────────────────────────────────────────┘
        │
   ┌────┴────┐
   │         │
   ▼         ▼
MAUSOLEUM   TOME
(wiki pages) (sessions, hot pages)
   │
   ▼
CRYPTOSEC  SQUEEZE
(TLS)      (gzip)
   │
   ▼
  RITZ (compiler)
```

---

## Features

### Wiki Functionality

- **Hierarchical pages** — Tree structure with parent/child relationships
- **Version history** — Every edit is preserved. Full git-like history via Mausoleum.
- **Backlinks** — Automatic bidirectional linking between pages
- **Full-text search** — Search across all documentation
- **Markdown rendering** — Write in Markdown, read as HTML
- **Live examples** — Compile and run Ritz code snippets in the browser

### Ritz-Specific Features

- **Native Ritz syntax highlighting** — Fully aware of Ritz syntax
- **API documentation** — Auto-generated from ritzlib source
- **Cross-references** — Links between language spec, stdlib modules, and examples
- **Ecosystem graph** — Visual map of project dependencies

---

## Data Model

```ritz
# Stored in Mausoleum
struct WikiPage
    id: Uuid
    slug: String              # URL path: "language/syntax"
    title: String
    content: String           # Markdown source
    parent_id: Option<Uuid>   # Tree structure
    version: u64              # MVCC version
    created_at: Timestamp
    updated_at: Timestamp
    author_id: Uuid

# Graph edges between pages
struct PageLink
    source_id: Uuid
    target_id: Uuid
    kind: LinkKind

enum LinkKind
    Reference                 # [[page]] inline link
    SeeAlso                   # Related page suggestion
    Implements                # Spec → implementation link
```

---

## URL Structure

```
/                           → Home
/getting-started            → Getting started guide
/language/                  → Language reference
/language/syntax            → Syntax reference
/language/ownership         → Ownership and borrowing
/projects/                  → All ecosystem projects
/projects/valet             → Valet project page
/subsystems/web-stack       → Web stack subsystem overview
/contributing               → How to contribute
```

---

## Application Structure (MVRSPT)

```
nexus/
├── models/
│   ├── page.ritz            # WikiPage struct
│   ├── user.ritz            # User account
│   └── link.ritz            # PageLink
├── views/
│   ├── layouts/
│   │   └── base.html        # Base template with nav
│   └── wiki/
│       ├── show.html        # Render a wiki page
│       ├── edit.html        # Edit form
│       └── history.html     # Version history list
├── repos/
│   ├── page_repo.ritz       # Mausoleum-backed page storage
│   └── search_repo.ritz     # Full-text search
├── services/
│   ├── wiki_service.ritz    # Page CRUD, validation
│   ├── render_service.ritz  # Markdown → HTML
│   └── link_service.ritz    # [[link]] extraction
├── presenters/
│   └── wiki_presenter.ritz  # HTTP routes
└── main.ritz
```

---

## Deployment

### Single Binary (Embedded Mode)

```ritz
import mausoleum { Db }
import tome { Cache }
import spire { App }
import valet { Server }

const MB: i64 = 1024 * 1024

fn main() -> Result<(), NexusError>
    let db = Db.open("nexus.m7m")?
    let cache = Cache.new(256 * MB)?

    var app = App.new()
    app.set_repository(WikiRepository.new(db, cache))
    app.set_service(WikiService.new())
    app.set_presenter(WikiPresenter.new())
    app.set_views("views/")

    var server = Server.new()
    server.set_app(app)
    server.set_tls("cert.pem", "key.pem")
    server.listen(":443")?

    Ok(())
```

### Docker Compose

```yaml
services:
  nexus:
    build: .
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./data:/data
    environment:
      - MAUSOLEUM_PATH=/data/nexus.m7m
      - TOME_MAX_MEMORY=256MB
```

---

## Stack Component Summary

| Component | Role | Status |
|-----------|------|--------|
| [Ritz](ritz.md) | Compiler | Active |
| [Ritzunit](ritzunit.md) | Testing | Production |
| [Valet](valet.md) | HTTP server | Production |
| [Zeus](zeus.md) | App server | Design |
| [Spire](spire.md) | Framework | Design |
| [Mausoleum](mausoleum.md) | Database | Phase 4 |
| [Tome](tome.md) | Cache | Design |
| [Squeeze](squeeze.md) | Compression | Production |
| [Cryptosec](cryptosec.md) | TLS | Active |

---

## Current Status

Design phase. Wiki content (this wiki) created and ready. Application implementation awaiting Spire and Zeus stabilization.

---

## Related Projects

All of them — Nexus is the capstone project of the Ritz ecosystem.

- [Architecture](../architecture.md) — How the full stack fits together
- [Getting Started](../getting-started.md)
- [Contributing](../contributing.md)
