# Nexus

The Ritz knowledge base - documentation and wiki platform built on the full Ritz ecosystem stack.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

## Overview

Nexus is the official documentation wiki for the Ritz ecosystem and a reference implementation of the complete Ritz application stack. It serves as a living knowledge base for the Ritz language, standard library, and ecosystem projects, while also demonstrating how to build production applications using Spire, Zeus, Valet, Mausoleum, and Tome together.

Wiki pages are stored in Mausoleum as versioned documents with Git-like history, enabling time-travel queries and complete audit trails. Hot pages are cached in Tome. The Spire framework provides the MVRSPT application architecture, served via Zeus worker processes and Valet's HTTP layer.

Nexus is the dogfooding platform for the Ritz ecosystem - every component is built and tested through real-world wiki usage.

## Architecture

The Ritz application stack is a complete, self-hosted ecosystem written entirely in Ritz with direct Linux syscalls (no libc). Each component serves a specific role:

| Component   | Role                                         |
|-------------|----------------------------------------------|
| **Valet**   | HTTP server with io_uring, TLS termination   |
| **Zeus**    | App server, worker process management        |
| **Spire**   | Web framework (MVRSPT pattern)               |
| **Tome**    | In-memory key-value cache                    |
| **Mausoleum** | Document database with versioning          |

### Request Flow

```
HTTP Request
    │
    ▼
┌─────────┐
│  Valet  │  ← HTTP parsing, TLS, io_uring
└────┬────┘
     │ ring buffer
     ▼
┌─────────┐
│  Zeus   │  ← Worker dispatch, process isolation
└────┬────┘
     │
     ▼
┌─────────┐
│  Spire  │  ← Routing, controllers, views
└────┬────┘
     │
     ▼
┌─────────┐     ┌─────────┐
│  Tome   │ ←→  │Mausoleum│
└─────────┘     └─────────┘
   cache          storage
```

### Deployment Model

- **Valet** binds to port 80/443, handles TLS termination and HTTP parsing
- **Zeus** spawns worker processes with shared memory ring buffers
- **Spire** workers (Nexus) receive requests via ring buffer, return responses
- **Mausoleum** runs as a separate daemon for persistent storage
- **Tome** provides in-process caching (future: separate daemon mode)

All components communicate via Unix sockets and shared memory - no TCP overhead within the stack.

### The Vision

Nexus demonstrates the full Ritz stack today on Linux. The ultimate goal:

1. **Harland** - Microkernel written in Ritz
2. **Indium** - Linux-compatible distro running on Harland
3. **Nexus on Indium** - Wiki running Ritz all the way down to the kernel

No C. No libc. Just Ritz.

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

**Deployed** - Nexus is running in production on AWS EC2 with systemd service management. The core stack (Valet → Zeus → Spire workers, with Mausoleum storage) is operational. Currently implementing:

- [ ] Ring buffer request dispatch (Valet → Zeus workers)
- [ ] Wiki page CRUD operations
- [ ] Markdown rendering with Ritz syntax highlighting
- [ ] Tome caching integration
- [ ] Full-text search

### Production Deployment

```bash
# Deploy to EC2 (requires AWS credentials and terraform)
cd projects/nexus/deploy/scripts
./deploy.sh

# Just rebuild and provision (skip terraform)
./deploy.sh build
./deploy.sh provision

# SSH into the server
./deploy.sh ssh
```

Services managed via systemd:
- `mausoleum.service` - Document storage daemon
- `zeus.service` - App server with Nexus workers
- `valet.service` - HTTP frontend

## License

MIT License - see LICENSE file
