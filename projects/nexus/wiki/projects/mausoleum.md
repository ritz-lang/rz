# Mausoleum

*"Where data is entombed forever."*

Embedded document database with tree semantics, versioning, and graph queries. Phase 4 complete (server + client).

---

## Overview

Mausoleum (abbreviated `m7m`) is the primary persistence layer for the Ritz ecosystem. It combines document storage, tree-native hierarchical relationships, MVCC versioning, and graph queries — all in a single embedded library with no separate server process required.

---

## Where It Fits

```
Nexus → Mausoleum (wiki page storage, version history)
Spire → Mausoleum (via Repository layer, optional)
Mausoleum → Cryptosec (SHA-256 for checksums)
```

---

## Design Goals

| Goal | Description |
|------|-------------|
| **Embedded-first** | A library, not a server. Link it into your app. |
| **Tree-native** | Parent/child relationships are primitive, not an afterthought |
| **Versioned** | Every write creates a new version. Full history forever. |
| **Document-oriented** | Flexible schemas. No rigid table structure. |
| **Graph-capable** | Arbitrary links between documents. Efficient traversal. |
| **Append-only** | Data files are immutable. Only metadata pointers change. |

---

## Data Model

```ritz
struct Document
    id: Uuid
    parent: Option<DocId>          # Tree structure
    kind: String                   # "user", "task", "page", "spec", etc.
    content: Value                 # Flexible JSON-like data
    links: Vec<Link>               # Graph edges to other documents
    version: u64                   # MVCC version number
    created_at: Timestamp
    updated_at: Timestamp

struct Link
    kind: LinkKind                 # Implements, DependsOn, RelatedTo, etc.
    target: DocId
    metadata: Option<Value>        # Optional data on the edge

struct Version
    id: VersionId
    document: DocId
    parent_version: Option<VersionId>   # Enables branching
    snapshot: Document
    author: String
    message: String
    timestamp: Timestamp
```

---

## Query Interface

### Tree Operations

```ritz
let db = Db.open("myapp.m7m")?

let root = db.root()?
let children = db.children(root.id)?
let ancestors = db.ancestors(node.id)?
let subtree = db.descendants(root.id)?
```

### Document Queries

```ritz
# Query with filtering and ordering
let tasks = db.query()
    .kind("task")
    .where("status", "active")
    .order_by("updated_at", Desc)
    .limit(50)
    .exec()?

# Insert a document
let doc = db.insert(Document {
    id: Uuid.new_v4(),
    parent: Some(project.id),
    kind: String.from("task"),
    content: json!({ "title": "Implement login", "status": "active" }),
    links: Vec.new(),
    ...
})?
```

### Graph Queries

```ritz
# Traverse a specific link type
let implementations = db.traverse(spec.id, LinkKind.Implements)?

# Find shortest path between two documents
let path = db.shortest_path(from, to)?

# Create a link
db.link(plan.id, spec.id, LinkKind.Implements)?
```

### Version History (Time Travel)

```ritz
# Full history of a document
let history = db.history(doc.id)?

# Read a document at a specific past version
let old_doc = db.at_version(doc.id, v1)?

# Diff two versions
let diff = db.diff(v1, v2)?
```

---

## Storage Format

Mausoleum uses an Iceberg-inspired format: data lives in immutable append-only files; metadata pointers are updated atomically:

```
project.m7m/
├── metadata/
│   ├── current.json          # Points to latest snapshot
│   └── snapshots/
│       ├── snap-0001.json    # Immutable snapshot manifest
│       └── snap-0002.json
├── data/
│   ├── 0001.tomb             # Immutable data pages
│   └── 0002.tomb
├── wal/
│   └── 0001.wal              # Write-ahead log (durability)
└── indexes/
    ├── tree.idx               # Parent-child index (fast children() query)
    └── links.idx              # Graph edge index (fast traverse() query)
```

**Why append-only?**

- Snapshot isolation is free — readers see a consistent version while writers append
- Time travel is free — old snapshots are never overwritten
- Crash safety — the WAL provides atomicity; data files are never partially written
- Deduplication — identical content shares underlying pages

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                    Query Layer                           │
│       Tree traversal, graph queries, full-text search   │
├─────────────────────────────────────────────────────────┤
│                   Document Layer                         │
│       Schema validation, indexing, MVCC versioning      │
├─────────────────────────────────────────────────────────┤
│                   Storage Layer                          │
│       Log-structured, append-only, compaction           │
├─────────────────────────────────────────────────────────┤
│                    Page Layer                            │
│       B-tree pages, buffer pool, WAL                    │
├─────────────────────────────────────────────────────────┤
│                    File Layer                            │
│       OS file I/O, memory-mapping, checksums            │
└─────────────────────────────────────────────────────────┘
```

---

## Inspirations

| System | Influence |
|--------|-----------|
| **SQLite** | Embedded, single-file, battle-tested patterns |
| **Git** | Content-addressable storage, branching, immutable history |
| **CouchDB** | Document model, MVCC, append-only |
| **Apache Iceberg** | Snapshot isolation, time travel, immutable data files |
| **LMDB** | Memory-mapped I/O, copy-on-write |
| **Neo4j** | Graph traversal API patterns |

---

## Nexus Use Case

Nexus (this wiki) uses Mausoleum to store all wiki pages with full version history:

```ritz
struct WikiPage
    id: Uuid
    slug: String              # URL path: "language/syntax"
    title: String
    content: String           # Markdown content
    parent_id: Option<Uuid>   # Tree structure
    version: u64
    created_at: Timestamp
    updated_at: Timestamp
    author_id: Uuid
```

When a page is updated, Mausoleum creates a new version automatically. The edit history is always accessible.

---

## Current Status

Phase 4 complete: server and client operational. ~100+ tests passing.

---

## Related Projects

- [Tome](tome.md) — In-memory cache, often used alongside Mausoleum
- [Cryptosec](cryptosec.md) — Provides SHA-256 for checksums
- [Spire](spire.md) — Uses Mausoleum via the Repository layer
- [Nexus](nexus.md) — Primary consumer for wiki page storage
- [Data Subsystem](../subsystems/data.md)
