# Nexus

The Ritz knowledge base - documentation and wiki platform built on the full Ritz ecosystem stack.

**Part of the [Ritz Ecosystem](../ritz/docs/ECOSYSTEM.md)**

## Overview

Nexus is the official documentation wiki for the Ritz ecosystem and a reference implementation of the complete Ritz application stack. It serves as a living knowledge base for the Ritz language, standard library, and ecosystem projects, while also demonstrating how to build production applications using Spire, Zeus, Valet, Mausoleum, and Tome together.

Wiki pages are stored in Mausoleum as versioned documents with Git-like history, enabling time-travel queries and complete audit trails. Hot pages are cached in Tome. The Spire framework provides the MVRSPT application architecture, served via Zeus worker processes and Valet's HTTP layer.

Nexus is the dogfooding platform for the Ritz ecosystem - every component is built and tested through real-world wiki usage.

## Features

> **Partially implemented.** The list below describes the design. See [Status](#status) — nexus builds, but the binary is a Zeus worker with no usable standalone entry point.

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
# Nexus lives in the rz monorepo; there is no separate nexus repository.
git clone git@github.com:ritz-lang/rz.git
cd rz

# Build (run from the monorepo root; `rz` sets RITZ_PATH itself)
./rz build nexus
# Produces projects/nexus/build/debug/nexus
```

**There is no `nexus serve` subcommand and no standalone dev server.** The
binary is a Zeus worker process, not a server; its own usage string is:

```
Usage: nexus <shm_size> <worker_id>
  (This binary is spawned by Zeus daemon)
```

Run with no arguments it prints that and exits 1. Run as
`nexus serve --dev` it parses `serve` as `shm_size` and `--dev` as `worker_id`,
both coercing to 0, then segfaults on the zero-sized shared-memory region:

```bash
./projects/nexus/build/debug/nexus serve --dev ; echo $?   # 139, reproducible
```

Before the crash it does reach the store layer — it tries mausoleum over Spire
at 127.0.0.1:7777, falls back to in-memory mode and seeds 3 pages — so the
failure is the zero `shm_size`, not the wiki code. Running it for real means
bringing up Zeus and letting Zeus spawn it with a valid SHM size and worker id;
that path is not wired up in this repo yet.

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

**Not "design phase" — it is implemented and compiles.** This README described
nexus as design-only while the project had 16 source files and a green build.

Measured 2026-09-12: `./rz build nexus` exits 0 against 6 dependencies,
producing `build/debug/nexus`. 37 `[[test]]` markers across 4 test files.

`./rz test nexus` **exits 1**: `Σ 3 passed, 0 failed, 3 compile-failed` — three
of the four test files fail to compile with
`Import resolution failed: Cannot find module: services.wiki_service`. Real
failures, not excused anywhere.

What is *not* done is the entry point. The binary is a Zeus worker
(`nexus <shm_size> <worker_id>`), there is no `serve` subcommand, and invoking it
by hand segfaults — see Installation above. Page CRUD, versioning and Markdown
rendering exist in source; the store layer reaches mausoleum over Spire and falls
back to in-memory with 3 seeded pages.

It also does not build with the self-hosted compiler:
`./rz clean nexus && ./rz build nexus --compiler ritz1` fails at exit 1 with
`cannot determine receiver type for method call` (×4) and
`unknown identifier 'scan_rebuild_callback'`. Those are ritz1 gaps, not nexus
bugs — see [docs/STACK_MATRIX.md](../../docs/STACK_MATRIX.md).

## License

MIT License - see LICENSE file
