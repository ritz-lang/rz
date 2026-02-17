# Data Subsystem

The data subsystem provides persistence and in-memory caching for the Ritz ecosystem. It replaces the need for external databases like PostgreSQL, Redis, or MongoDB.

---

## Projects in This Subsystem

| Project | Role | Status |
|---------|------|--------|
| [Mausoleum](../projects/mausoleum.md) | Embedded document database with MVCC | Phase 4 |
| [Tome](../projects/tome.md) | In-memory data store | Design |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Application / Spire                              │
└─────────────────────────────────────────────────────────────────────┘
                        │                │
              ┌─────────┘                └─────────┐
              │                                    │
              ▼                                    ▼
┌─────────────────────────┐          ┌─────────────────────────┐
│       MAUSOLEUM         │          │          TOME           │
│   Persistent Storage    │          │    In-Memory Cache      │
│                         │          │                         │
│  Documents, trees,      │          │  Sessions, hot data,    │
│  versions, graphs       │          │  pub/sub, TTL           │
│  (like Git + CouchDB)   │          │  (like Redis)           │
└─────────────────────────┘          └─────────────────────────┘
              │
              ▼
┌─────────────────────────┐
│      CRYPTOSEC          │
│  (checksums/hashing)    │
└─────────────────────────┘
```

---

## Mausoleum: The Document Database

Mausoleum (abbreviated `m7m`) is an embedded document database inspired by SQLite, Git, CouchDB, and Apache Iceberg.

### Design Goals

| Goal | Description |
|------|-------------|
| **Embedded-first** | A library, not a server. Link it into your Ritz app. |
| **Tree-native** | Parent/child relationships are fundamental, not bolted on |
| **Versioned** | Every change creates a new version. Full history. |
| **Document-oriented** | Flexible schemas. Each node is a structured document |
| **Graph-capable** | Arbitrary links between nodes, efficient traversal |
| **Append-only core** | Immutable data files, mutable metadata pointers |

### Data Model

```ritz
struct Document
    id: Uuid
    parent: Option<DocId>     # Tree structure
    kind: String              # "user", "task", "page", etc.
    content: Value            # Flexible JSON-like data
    links: Vec<Link>          # Graph edges to other documents
    version: u64              # MVCC version
    created_at: Timestamp
    updated_at: Timestamp

struct Link
    kind: LinkKind            # Implements, DependsOn, RelatedTo
    target: DocId
    metadata: Option<Value>
```

### Query Interface

```ritz
let db = Db.open("myapp.m7m")?

# Tree operations
let root = db.root()?
let children = db.children(root.id)?
let ancestors = db.ancestors(node.id)?

# Graph queries
let linked = db.traverse(node.id, LinkKind.Implements)?
let path = db.shortest_path(from, to)?

# Document queries
let specs = db.query()
    .kind("spec")
    .where("status", "draft")
    .order_by("updated_at", Desc)
    .limit(10)
    .exec()?

# Version history (time travel)
let history = db.history(node.id)?
let old_version = db.at_version(node.id, version_id)?
let diff = db.diff(v1, v2)?
```

### Storage Architecture

```
project.m7m/
├── metadata/
│   ├── current.json          # Points to latest snapshot
│   └── snapshots/            # Immutable snapshot manifests
├── data/
│   └── *.tomb                # Immutable data pages
├── wal/
│   └── *.wal                 # Write-ahead log
└── indexes/
    ├── tree.idx               # Parent-child index
    └── links.idx              # Graph edge index
```

Inspired by Apache Iceberg: data lives in immutable files, metadata pointers are updated atomically. Snapshots enable time travel queries.

### Inspirations

| System | What Mausoleum Takes |
|--------|---------------------|
| **SQLite** | Embedded, single-file, battle-tested patterns |
| **Git** | Content-addressable, branching, immutable history |
| **CouchDB** | Document model, MVCC, append-only |
| **Apache Iceberg** | Snapshot isolation, time travel |
| **LMDB** | Memory-mapped, copy-on-write |
| **Neo4j** | Graph traversal patterns |

---

## Tome: The In-Memory Cache

Tome is a high-performance in-memory data store similar to Redis. It provides fast access to frequently used data and session state.

### Data Structures

| Type | Description | Use Case |
|------|-------------|----------|
| Strings | Simple key-value | Session tokens, feature flags |
| Lists | Ordered sequences | Activity feeds, queues |
| Sets | Unordered collections | Unique visitors, tags |
| Sorted Sets | Score-ordered sets | Leaderboards, priority queues |
| Hashes | Field-value maps | User profiles, counters |

### Key Features

- **TTL (Time-To-Live)** — Automatic expiration of keys
- **Eviction policies** — LRU, LFU, random when memory is full
- **Pub/sub messaging** — Channel-based publish/subscribe
- **Snapshots** — Optional persistence to disk
- **AOF (Append-Only File)** — Optional durable write log
- **Zero-copy IPC mode** — Via Zeus for same-machine applications

---

## How They Work Together

In a Nexus (wiki) deployment:

```
Request: "Load wiki page /language/syntax"
    │
    ▼
Tome.get("page:/language/syntax")  ─── HIT ──→  Return cached HTML
    │
   MISS
    │
    ▼
Mausoleum.query().slug("/language/syntax").exec()
    │
    ▼
Render Markdown → HTML
    │
    ▼
Tome.set("page:/language/syntax", html, ttl: 300)  # Cache for 5 min
    │
    ▼
Return HTML to client
```

Tome caches hot pages in memory. Mausoleum stores all content with full version history. When content is updated in Mausoleum, the Tome cache is invalidated.

---

## See Also

- [Mausoleum project page](../projects/mausoleum.md)
- [Tome project page](../projects/tome.md)
- [Web Stack Subsystem](web-stack.md) — Spire uses these for data access
- [Nexus](../projects/nexus.md) — Reference implementation using both
