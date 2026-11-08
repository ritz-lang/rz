# Mausoleum

Embedded document database for Ritz with tree semantics, versioning, and graph-relational capabilities.

**Part of the [Ritz Ecosystem](../ritz/docs/ECOSYSTEM.md)**

## Overview

Mausoleum (abbreviated m7m) is the persistence layer for the Ritz ecosystem. It combines document storage, first-class hierarchical tree relationships, Git-like version history, and graph traversal in a single embedded library that links directly into Ritz applications - no separate server process needed.

The design is inspired by SQLite (embedded, single-file), Git (content-addressable, immutable history), CouchDB (document model, MVCC), Apache Iceberg (snapshot isolation, append-only), and LMDB (memory-mapped, zero-copy reads). Data written to Mausoleum is never truly deleted - every change creates a new version, preserving complete history.

The primary use case is as the persistence backend for Spectree (hierarchical specification trees for AI-assisted development) and Nexus (the Ritz knowledge base wiki).

## Features

- Document storage with flexible JSON-like schemas
- First-class tree structure (parent/child relationships are native)
- MVCC versioning - every change creates a new version
- Full version history with time-travel queries
- Graph edges (arbitrary links between documents)
- Efficient tree traversal and graph queries
- Append-only core storage (immutable data files)
- Content-addressable storage via SHA-256 (via cryptosec)
- Snapshot isolation for consistent reads
- Embedded library - no separate server

## Installation

```bash
# As a dependency in ritz.toml:
# [dependencies]
# mausoleum = { path = "../mausoleum" }

# Build from source (run from the monorepo root; `rz` sets RITZ_PATH itself)
./rz build mausoleum
```

## Usage

```ritz
import mausoleum { Db, Document }

# Open or create a database
let db = Db.open("myapp.m7m")

# Insert a document
let org = db.insert(Document.new("org", "Ritz Language"))
let spec = db.insert(Document.new("spec", "Type System").parent(org.id))
let plan = db.insert(Document.new("plan", "Implement Generics").parent(spec.id))

# Tree operations
let children = db.children(org.id)
let ancestors = db.ancestors(plan.id)
let all_plans = db.descendants(org.id).filter_kind("plan")

# Graph links between documents
db.link(plan.id, spec.id, LinkKind.Implements)
let linked = db.traverse(spec.id, LinkKind.Implements)

# Version history (time travel)
let history = db.history(spec.id)
let old = db.at_version(spec.id, history[0].version_id)
```

## Dependencies

- `cryptosec` - SHA-256 for content-addressable storage

## Status

**Active development**, further along than "Alpha — architecture designed", which
is what this README said while the code was already building and running.

Measured 2026-09-26: `./rz build mausoleum` exits 0, producing three binaries —
`mausoleum`, `wiki-seed` and `concurrent_bench`. (The former `test_integration`
and `test_storage` binaries are now `[[test]]` files: `test/test_integration.ritz`
starts its own `mausoleum serve --no-encryption` on a pid-derived port, and
`test/test_storage_persistence.ritz` does the open/commit/reopen round trip.)
Run `./rz test mausoleum` for the current pass count.

Persistence (AGAST #2458): with `serve --data-dir DIR`, every INSERT / UPDATE /
DELETE is committed before it is acknowledged: dirty pages and the collection's
root page and counters go to the WAL as one transaction, then to `data.m7m` and
`meta.m7m`. A restart on DIR (including after `kill -9`, or a crash mid-flush)
redoes the WAL and reopens the same collection; a checkpoint (on open, on close,
or past 4 MiB) cuts the WAL back. `test/test_restart.ritz` restarts a store
those ways; `projects/ritz/tools/smoke_stack.py mausoleum` does it with the
real binaries.

`mausoleum shell` and `wiki-seed` speak the encrypted protocol by default, like
the server; pass `--no-encryption` to both for a `serve --no-encryption` server.
The shell takes `put key=value ...`, `get <id>`, `delete <id>`, `list`, `ping`
and `help`, reads commands from a pipe as well as a terminal, and exits 1 if any
command failed.

Not yet proven: it does **not** build with the self-hosted compiler.
`./rz clean mausoleum && ./rz build mausoleum --compiler ritz1` fails at exit 1
with `ritz1 cannot emit: cannot determine receiver type for method call` (×4) and
`unknown identifier 'handle_task_event'`. Those are ritz1 gaps, not mausoleum
bugs — see [docs/STACK_MATRIX.md](../../docs/STACK_MATRIX.md).

## License

MIT License - see LICENSE file
