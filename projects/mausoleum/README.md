# Mausoleum

*Where data is entombed forever.*

Embedded database engine for Ritz. Document storage with tree semantics, versioning, and graph-relational capabilities.

## Overview

Mausoleum (m7m) is the persistence layer for the Ritz ecosystem. It combines:
- **Document storage** — Flexible structured data (like CouchDB)
- **Tree semantics** — First-class hierarchical relationships
- **Versioning** — Git-like history for all data (MVCC)
- **Graph queries** — Traverse relationships efficiently
- **Embedded** — In-process, no separate server needed

Primary use case: Backend for [Spectree](https://github.com/ritz-lang/spectree) — the hierarchical spec/plan tree for AI agents.

## Design Goals

| Goal | Description |
|------|-------------|
| **Embedded-first** | Library, not a server. Link it into your Ritz app. |
| **Tree-native** | Parent/child relationships are fundamental, not bolted on. |
| **Versioned** | Every change creates a new version. Full history. Branch/merge. |
| **Document-oriented** | Flexible schemas. Each node is a structured document. |
| **Graph-capable** | Arbitrary links between nodes. Efficient traversal. |
| **Append-only core** | Inspired by Iceberg/Git. Immutable data, mutable pointers. |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Query Layer                          │
│         Tree traversal, graph queries, search           │
├─────────────────────────────────────────────────────────┤
│                   Document Layer                        │
│        Schema validation, indexing, MVCC                │
├─────────────────────────────────────────────────────────┤
│                   Storage Layer                         │
│         Log-structured, append-only, compaction         │
├─────────────────────────────────────────────────────────┤
│                    Page Layer                           │
│         B-tree/LSM pages, buffer pool, WAL              │
├─────────────────────────────────────────────────────────┤
│                    File Layer                           │
│         OS file I/O, memory mapping, checksums          │
└─────────────────────────────────────────────────────────┘
```

## Data Model

```ritz
struct Document {
    id: Uuid,
    parent: Option<DocId>,          // Tree structure
    kind: String,                    // "spec", "plan", "org", etc.
    content: Value,                  // Flexible JSON-like data
    links: Vec<Link>,                // Graph edges to other docs
    version: u64,                    // MVCC version
    created_at: Timestamp,
    updated_at: Timestamp,
}

struct Link {
    kind: LinkKind,                  // Implements, DependsOn, RelatedTo
    target: DocId,
    metadata: Option<Value>,
}

// Version history
struct Version {
    id: VersionId,
    document: DocId,
    parent_version: Option<VersionId>,  // For branching
    snapshot: Document,
    author: String,
    message: String,
    timestamp: Timestamp,
}
```

## Inspirations

| System | What We Take |
|--------|--------------|
| **SQLite** | Embedded, single-file, battle-tested patterns |
| **Git** | Content-addressable, branching, immutable history |
| **CouchDB** | Document model, MVCC, append-only |
| **Apache Iceberg** | Table format, snapshot isolation, time travel |
| **LMDB** | Memory-mapped, copy-on-write, zero-copy reads |
| **Neo4j** | Graph traversal patterns |

## Query Interface

```ritz
use mausoleum::{Db, Query}

let db = Db::open("spectree.m7m")?

// Tree operations
let root = db.root()?
let children = db.children(root.id)?
let ancestors = db.ancestors(node.id)?

// Graph queries
let linked = db.traverse(node.id, LinkKind::Implements)?
let path = db.shortest_path(from, to)?

// Document queries
let specs = db.query()
    .kind("spec")
    .where("status", "draft")
    .order_by("updated_at", Desc)
    .limit(10)
    .exec()?

// Version history (time travel)
let history = db.history(node.id)?
let old_version = db.at_version(node.id, version_id)?
let diff = db.diff(v1, v2)?

// Entomb data forever
db.insert(doc)?  // It's in the mausoleum now. It never leaves.
```

## File Format

Inspired by Iceberg's approach — data in immutable files, metadata pointers:

```
project.m7m/
├── metadata/
│   ├── current.json          # Points to latest snapshot
│   └── snapshots/
│       ├── snap-0001.json
│       └── snap-0002.json
├── data/
│   ├── 0001.tomb             # Immutable data pages
│   ├── 0002.tomb
│   └── ...
├── wal/
│   └── 0001.wal              # Write-ahead log
└── indexes/
    ├── tree.idx              # Parent-child index
    └── links.idx             # Graph edge index
```

## Use Cases

### Spectree Backend
```ritz
// Spectree uses Mausoleum for all persistence
let db = Mausoleum::open("project.m7m")?

// Create spec hierarchy
let org = db.insert(Document::new("org", "Ritz Language"))?
let spec = db.insert(Document::new("spec", "Type System").parent(org))?
let plan = db.insert(Document::new("plan", "Implement Generics").parent(spec))?

// Link plan to spec it implements
db.link(plan, spec, LinkKind::Implements)?

// Query the tree
let all_plans = db.descendants(org).filter(|d| d.kind == "plan")?
```

### General Embedded DB
```ritz
// Any Ritz app can use Mausoleum
let db = Mausoleum::open("myapp.m7m")?

db.insert(Document::new("user", json!({
    "name": "Alice",
    "email": "alice@example.com"
})))?
```

## Why "Mausoleum"?

Because once data enters, it never truly dies. Every version is preserved. Every change is recorded. The mausoleum holds all history, forever entombed but always accessible.

Also: `m7m` is a sick abbreviation.

## Status

**Design Phase** — Architecture and data model being defined.

## Dependencies

- Built in pure Ritz
- Uses `cryptosec` for checksums/hashing
- No external database dependencies

## License

MIT
