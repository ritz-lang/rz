# Nexus

*The Ritz Knowledge Base*

Nexus is the official documentation and wiki platform for the Ritz ecosystem. It serves as both a living knowledge base and a reference implementation of the full Ritz stack.

## What is Nexus?

Nexus is:
1. **A Wiki** — Documentation for Ritz language, libraries, and ecosystem
2. **A Reference Implementation** — Built on the complete Ritz stack
3. **A Dogfooding Platform** — We use what we build

## Architecture

Nexus runs on the full Ritz stack:

```
┌─────────────────────────────────────────────────────────────────────┐
│                            NEXUS                                     │
│                     Ritz Knowledge Base                              │
├─────────────────────────────────────────────────────────────────────┤
│                            SPIRE                                     │
│                      MVRSPT Framework                                │
│         Models │ Views │ Repos │ Services │ Presenters │ Tests      │
├─────────────────────────────────────────────────────────────────────┤
│                            ZEUS                                      │
│                   App Server / Process Manager                       │
├─────────────────────────────────────────────────────────────────────┤
│                           VALET                                      │
│                  HTTP/1.1 Server + TLS 1.3                          │
├─────────────────────────────────────────────────────────────────────┤
│              MAUSOLEUM           │           TOME                    │
│          Document Store          │      In-Memory Cache              │
│        (wiki pages, history)     │    (sessions, hot pages)         │
├─────────────────────────────────────────────────────────────────────┤
│              CRYPTOSEC           │          SQUEEZE                  │
│             TLS 1.3              │        Compression                │
├─────────────────────────────────────────────────────────────────────┤
│                      RITZ + RITZUNIT                                 │
│                   Compiler + Test Framework                          │
└─────────────────────────────────────────────────────────────────────┘
```

## Features

### Wiki Functionality
- **Hierarchical Pages** — Tree structure with parent/child relationships
- **Version History** — Git-like history for all content (via Mausoleum)
- **Backlinks** — Automatic bidirectional linking
- **Full-Text Search** — Search across all documentation
- **Markdown Rendering** — Write in Markdown, render as HTML

### Ritz-Specific Features
- **Code Highlighting** — Native Ritz syntax highlighting
- **Live Examples** — Compile and run code snippets
- **API Documentation** — Auto-generated from ritzlib source
- **Cross-References** — Link between language spec, stdlib, and examples

## Content Structure

```
/                           # Home
├── /language               # Language Reference
│   ├── /syntax             # Syntax guide
│   ├── /types              # Type system
│   ├── /ownership          # Ownership & borrowing
│   └── /async              # Async/await
├── /stdlib                 # Standard Library
│   ├── /io                 # I/O module
│   ├── /memory             # Memory management
│   ├── /collections        # Data structures
│   └── /...
├── /ecosystem              # Ecosystem Projects
│   ├── /valet              # HTTP server
│   ├── /mausoleum          # Database
│   ├── /tome               # Cache
│   ├── /spire              # Framework
│   ├── /zeus               # App server
│   └── /...
├── /tutorials              # Getting Started
│   ├── /hello-world
│   ├── /web-app
│   └── /...
└── /contributing           # How to contribute
```

## Data Model

```ritz
# Wiki page stored in Mausoleum
struct WikiPage
    id: Uuid
    slug: String              # URL path: "language/syntax"
    title: String
    content: String           # Markdown
    parent_id: Option<Uuid>   # Tree structure
    version: u64              # MVCC version
    created_at: Timestamp
    updated_at: Timestamp
    author_id: Uuid


# Links between pages (graph edges)
struct PageLink
    source_id: Uuid
    target_id: Uuid
    kind: LinkKind            # Reference, SeeAlso, Implements


enum LinkKind
    Reference                 # [[page]] syntax
    SeeAlso                   # Related pages
    Implements                # Spec -> implementation
```

## Deployment

### Docker Compose (Recommended)

```yaml
version: '3.8'

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

  # Or run components separately:
  valet:
    build: ../valet
    ports:
      - "443:443"

  zeus:
    build: ../zeus
    depends_on:
      - mausoleum
      - tome

  mausoleum:
    build: ../mausoleum
    volumes:
      - ./data:/data

  tome:
    build: ../tome
    environment:
      - MAX_MEMORY=256MB
```

### Single Binary (Embedded)

```ritz
# All components linked into one executable
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

## Development

```bash
# Clone with all dependencies
git clone --recursive https://github.com/ritz-lang/nexus.git
cd nexus

# Build
./build.sh

# Run tests
./run_tests.sh

# Start dev server
./nexus serve --dev
```

## Status

**Design Phase** — Architecture being defined.

## The Ritz Stack

Nexus demonstrates the complete Ritz ecosystem:

| Component | Role | Status |
|-----------|------|--------|
| **Ritz** | Compiler | Active |
| **Ritzunit** | Testing | Production |
| **Valet** | HTTP Server | Production |
| **Zeus** | App Server | Design |
| **Spire** | Framework | Design |
| **Mausoleum** | Database | Phase 4 |
| **Tome** | Cache | Design |
| **Squeeze** | Compression | Production |
| **Cryptosec** | Crypto/TLS | Active |
| **Nexus** | Wiki | Design |

## License

MIT
