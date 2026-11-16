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

**Not "design phase" — it is implemented and compiles.**

The binary is a Zeus worker (`nexus <shm_size> <worker_id> <worker_count>`),
there is no `serve` subcommand, and invoking it by hand segfaults — see
Installation above. Each route parses its request and hands it to a presenter
(`src/presenters/`), which runs it through the wiki service (`src/services/`)
and the page repository (`src/repos/`) and renders the page (#2209). The
repository reaches mausoleum over Spire at `MAUSOLEUM_HOST`:`MAUSOLEUM_PORT`
(default 127.0.0.1:7777; Zeus passes its environment on to its workers, #3065),
encrypted unless `MAUSOLEUM_PLAINTEXT=1` (for `mausoleum --no-encryption`,
#2466). A set but unusable value of any of the three makes every page request
a 503 rather than fall back to a default. Mausoleum is the only
copy of a page: every request reads it there, so all of Zeus's workers serve
the same wiki (#2459); the Tome page cache stays off for the same reason. A
connection that drops is dialled again on the next request. Without mausoleum,
a single worker (`zeus -w 1`) falls back to an in-memory wiki with 3 seeded
pages; with several workers every page request is a 503 (each would otherwise
serve a private wiki) until mausoleum answers. Startup is `src/wiki_app.ritz`.

Slugs are 1-128 bytes of `/`-separated `[a-z0-9-]` segments (`src/slug.ritz`,
the one rule for routes and the service); `new` and slugs ending in `/edit`
are reserved for the routes. Pages written before #2209 (documents with only
`slug` and `content`) are still served, titled by their slug (or the `title`
wiki-seed stored), and rewritten in the current format on their next save;
documents that aren't pages are skipped. A slug lookup scans the collection
(#3644).

Upgrading a store written before mausoleum #3637, when every CONNECT name
shared one collection: such a store opens with nexus's pages (and wiki-seed's)
in the `default` collection, while nexus reads `nexus_pages`. No operator step
is needed. The first time a worker reaches mausoleum it moves every page in
`default` into `nexus_pages` (the newest copy of each slug, rewritten in the
current format) and deletes them from `default`. Other apps' documents stay
there. A slug `nexus_pages` already holds keeps its page. A move that fails
leaves `default` intact and runs again on the next dial (#3681,
`test/fixtures/store_v1_wiki`, written by the pre-#3637 binaries).

Page size: a page is one Mausoleum document, and a document is at most
`MAX_DOC_SIZE` (1992 bytes, one B-tree value; bigger ones would need overflow
pages). A page also carries its slug, title and six numbers, so its content is
at most `MAX_CONTENT_SIZE` (1229, `src/services/validation.ritz`). Longer
content is a 413, not a database error (#2208). The in-memory fallback keeps
its own 8192-byte limit (`wiki_page_repo_max_content_len`).

It also does not build with the self-hosted compiler:
`./rz clean nexus && ./rz build nexus --compiler ritz1` fails at exit 1 with
`cannot determine receiver type for method call` (×4) and
`unknown identifier 'scan_rebuild_callback'`. Those are ritz1 gaps, not nexus
bugs — see [docs/STACK_MATRIX.md](../../docs/STACK_MATRIX.md).

## License

MIT License - see LICENSE file
