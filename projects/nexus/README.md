# Nexus

The Ritz knowledge base - documentation and wiki platform built on the full Ritz ecosystem stack.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

## Overview

Nexus is the official documentation wiki for the Ritz ecosystem and a reference implementation of the complete Ritz application stack. It serves as a living knowledge base for the Ritz language, standard library, and ecosystem projects, while also demonstrating how to build production applications using Spire, Zeus, Valet, Mausoleum, and Tome together.

Wiki pages are stored in Mausoleum as versioned documents with Git-like history, enabling time-travel queries and complete audit trails. Hot pages are cached in Tome. The Spire framework provides the MVRSPT application architecture, served via Zeus worker processes and Valet's HTTP layer.

Nexus is the dogfooding platform for the Ritz ecosystem - every component is built and tested through real-world wiki usage.

## Features

- Hierarchical wiki pages with parent/child tree structure
- Complete version history for all content via Mausoleum
- Automatic backlinks between pages
- Full-text search across all documentation
- Markdown rendering with Ritz syntax highlighting
- Live code example execution
- Auto-generated API documentation from ritzlib source
- Cross-references between language spec, stdlib, and examples
- TLS 1.3 HTTPS via cryptosec

## Installation

```bash
# Clone with dependencies
git clone --recursive https://github.com/ritz-lang/nexus.git
cd nexus

# Build
./ritz build .

# Start development server
./build/debug/nexus serve --dev
```

## Usage

```ritz
import mausoleum { Db }
import tome { Cache }
import spire { App }
import valet { Server }

fn main() -> i32
    let db = Db.open("nexus.m7m")
    let cache = Cache.new(256 * 1024 * 1024)

    var app = App.new()
    app.set_repository(WikiRepository.new(db, cache))
    app.set_service(WikiService.new())
    app.set_presenter(WikiPresenter.new())
    app.set_views("views/")

    var server = Server.new()
    server.set_app(app)
    server.listen(":8080")
    0
```

## Content Structure

```
/                       Home
/language               Language Reference
  /syntax               Syntax guide
  /types                Type system
  /ownership            Ownership and borrowing
/stdlib                 Standard Library (ritzlib)
/ecosystem              Ecosystem Projects
  /valet                HTTP server
  /mausoleum            Database
  /tome                 Cache
  /spire                Web framework
/tutorials              Getting Started guides
/contributing           Contribution guidelines
```

## Dependencies

- `spire` - MVRSPT web framework
- `mausoleum` - Document storage for wiki pages
- `tome` - In-memory cache for sessions and hot pages
- `valet` - HTTP server
- `zeus` - App server / process isolation
- `cryptosec` - TLS 1.3
- `squeeze` - HTTP compression

## Status

**Design phase** - Architecture, content structure, and data model are defined. Core wiki functionality (page CRUD, versioning, Markdown rendering) is being implemented using TDD once the underlying Spire, Mausoleum, and Tome libraries stabilize.

## License

MIT License - see LICENSE file
