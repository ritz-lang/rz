# Ritz Ecosystem Overview

The Ritz ecosystem is a complete systems programming platform with twelve interconnected projects, from compiler to web framework to knowledge base.

## The Full Stack

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              LARB                                        │
│                   (Standards & Coordination)                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
┌───────────────────────────────────┴───────────────────────────────────┐
│                                                                        │
│   ┌─────────────────────────────────────────────────────────────────┐ │
│   │                          NEXUS                                   │ │
│   │                  Ritz Knowledge Base / Wiki                      │ │
│   └─────────────────────────────────────────────────────────────────┘ │
│                                 │                                      │
│   ┌─────────────────────────────┴─────────────────────────────────┐   │
│   │                          SPIRE                                 │   │
│   │                 MVRSPT Web Framework                           │   │
│   │      Model │ View │ Repository │ Service │ Presenter │ Tests  │   │
│   └─────────────────────────────────────────────────────────────────┘ │
│                                 │                                      │
│   ┌─────────────────────────────┴─────────────────────────────────┐   │
│   │                          ZEUS                                  │   │
│   │              App Server / Process Manager                      │   │
│   └─────────────────────────────────────────────────────────────────┘ │
│                                 │                                      │
│   ┌─────────────────────────────┴─────────────────────────────────┐   │
│   │                         VALET                                  │   │
│   │               HTTP/1.1 Server (1.47M req/s)                    │   │
│   └─────────────────────────────────────────────────────────────────┘ │
│                      │                   │                             │
│   ┌──────────────────┴───┐   ┌──────────┴──────────┐                  │
│   │      MAUSOLEUM       │   │        TOME         │                  │
│   │    Document Store    │   │   In-Memory Cache   │                  │
│   │  (persistence, MVCC) │   │  (sessions, pub/sub)│                  │
│   └──────────────────────┘   └─────────────────────┘                  │
│                      │                   │                             │
│   ┌──────────────────┴───────────────────┴──────────┐                 │
│   │              CRYPTOSEC │ SQUEEZE                │                 │
│   │              TLS 1.3   │ Compression            │                 │
│   └─────────────────────────────────────────────────┘                 │
│                                 │                                      │
│   ┌─────────────────────────────┴─────────────────────────────────┐   │
│   │                    RITZ + RITZUNIT                             │   │
│   │              Compiler + Standard Library + Testing             │   │
│   └─────────────────────────────────────────────────────────────────┘ │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Project Summary

| Project | Purpose | Status |
|---------|---------|--------|
| **Ritz** | Compiler + standard library | Active (324+ tests) |
| **Ritzunit** | Testing framework | Production |
| **Squeeze** | Compression (gzip/deflate) | Production (132 tests) |
| **Cryptosec** | Cryptography (TLS 1.3) | Active (331 tests) |
| **Valet** | HTTP/1.1 server | Production (1.47M req/s) |
| **Zeus** | App server / process manager | Design |
| **Mausoleum** | Document database (MVCC) | Phase 4 (server complete) |
| **Tome** | In-memory cache | Design |
| **Spire** | MVRSPT web framework | Design |
| **Nexus** | Wiki / knowledge base | Design |
| **Harland** | Kernel | Active |
| **LARB** | Standards & coordination | Active |

---

## Layer Details

### Foundation Layer

#### 1. Ritz (Core Compiler)

**Repository:** `ritz-lang/ritz`
**Purpose:** The Ritz programming language compiler and standard library
**Status:** Active development, 324 tests passing

| Component | Description | Lines |
|-----------|-------------|-------|
| `ritz0/` | Bootstrap compiler (Python → LLVM IR) | ~27k |
| `ritz1/` | Self-hosted compiler (Ritz → LLVM IR) | In progress |
| `ritzlib/` | Standard library (35 modules) | ~8k |
| `examples/` | 75+ example programs in 5 tiers | ~15k |
| `grammars/` | Canonical grammar specification | - |

**Key Statistics:**
- Language tests: 324 passing
- Unit tests: 201 passing
- Examples: 48/48 compiling
- Self-hosting: ritz1 compiles 47/48 examples

**ritzlib Modules:**

| Module | Purpose |
|--------|---------|
| `sys.ritz` | System calls (89 constants) |
| `io.ritz` | I/O helpers |
| `memory.ritz` | Memory allocation (mmap/munmap) |
| `gvec.ritz` | Generic Vec<T> |
| `hashmap.ritz` | Hash table |
| `fs.ritz` | Filesystem operations |
| `str.ritz` | String utilities |
| `async_tasks.ritz` | Async runtime |
| `uring.ritz` | io_uring bindings |
| `args.ritz` | Argument parsing |
| `json.ritz` | JSON parsing |
| `process.ritz` | Process spawning |

---

#### 2. Ritzunit (Test Framework)

**Repository:** `ritz-lang/ritzunit`
**Purpose:** JUnit/pytest-style unit testing for Ritz
**Status:** Production ready

**Key Features:**
- **ELF self-discovery** - No manual test registration
- **Fork-based isolation** - Catches crashes and timeouts
- **Rich assertions** - 18+ assertion functions
- **CLI interface** - Filter, list, verbose, timeout options

```ritz
[[test]]
fn test_something() -> i32
    if condition
        return 0    # PASS
    return 1        # FAIL
```

---

### Infrastructure Layer

#### 3. Squeeze (Compression Library)

**Repository:** `ritz-lang/squeeze`
**Purpose:** High-performance compression (gzip/deflate)
**Status:** Production ready, 132 tests passing

| Algorithm | Standard | Status |
|-----------|----------|--------|
| CRC-32 | ISO 3309 | ✅ + SIMD |
| Adler-32 | RFC 1950 | ✅ + SIMD |
| Deflate | RFC 1951 | ✅ |
| Gzip | RFC 1952 | ✅ |
| Zlib | RFC 1950 | ✅ |

**SIMD Acceleration:**
- CRC32: PCLMULQDQ folding (~15x speedup)
- Adler-32: PSADBW vectorization

---

#### 4. Cryptosec (Cryptography)

**Repository:** `ritz-lang/cryptosec`
**Purpose:** Cryptographic primitives for TLS 1.3
**Status:** Active development, 331 tests passing

| Category | Algorithms |
|----------|------------|
| Hashes | SHA-256, SHA-384, SHA-512 |
| MACs | HMAC-SHA-256/384/512, Poly1305 |
| KDFs | HKDF |
| Symmetric | AES-128/256, AES-GCM, ChaCha20, ChaCha20-Poly1305 |
| Asymmetric | X25519, Ed25519, RSA (verify only) |
| TLS 1.3 | Key schedule, record layer |
| X.509 | ASN.1/DER parsing, certificate validation |

---

### Server Layer

#### 5. Valet (HTTP Server)

**Repository:** `ritz-lang/valet`
**Purpose:** High-performance async HTTP/1.1 server
**Status:** Production ready, 85 tests passing

**Performance:**
- **1.47M requests/sec** (10.7x faster than nginx)
- io_uring async I/O
- Zero-copy operations
- Multi-process with SO_REUSEPORT

| Phase | Features |
|-------|----------|
| 0 | Async I/O, HTTP parsing, keep-alive |
| 1 | Zero-copy send, memory pools |
| 2 | JSON config, graceful shutdown |
| 3 | Static files, Range requests, ETag |
| 4 | Routing, middleware, interceptors |
| 5 | Gzip/deflate compression |
| 6 | TLS 1.3 (in progress) |

---

#### 6. Zeus (App Server)

**Repository:** `ritz-lang/zeus`
**Purpose:** Application server and process manager
**Status:** Design phase

Zeus sits between Valet and application frameworks like Spire:
- Process management (spawn, monitor, restart)
- Load balancing across worker processes
- Zero-downtime deployments
- IPC via shared memory / ring buffers

---

### Storage Layer

#### 7. Mausoleum (Document Database)

**Repository:** `ritz-lang/mausoleum`
**Purpose:** Embedded document store with tree semantics, versioning, and graph queries
**Status:** Phase 4 complete (server + client)

**Features:**
- Document storage with flexible schemas
- Tree-native hierarchical relationships
- MVCC versioning (git-like history)
- Graph queries and traversal
- Network server with binary protocol (M7SP)

---

#### 8. Tome (In-Memory Cache)

**Repository:** `ritz-lang/tome`
**Purpose:** High-performance in-memory data store (like Redis)
**Status:** Design phase

**Features:**
- Rich data structures (strings, lists, sets, sorted sets, hashes)
- TTL and eviction policies
- Pub/sub messaging
- Optional persistence (snapshots, AOF)
- Zero-copy IPC mode via Zeus

---

### Application Layer

#### 9. Spire (Web Framework)

**Repository:** `ritz-lang/spire`
**Purpose:** MVRSPT web framework for Ritz
**Status:** Design phase

Spire implements the MVRSPT (Model-View-Repository-Service-Presenter-Tests) pattern:

| Layer | Directory | Responsibility |
|-------|-----------|----------------|
| **M** - Model | `models/` | Pure data structs, no behavior |
| **V** - View | `views/` | Templates, HTML/JSON rendering |
| **R** - Repository | `repos/` | Data access abstraction |
| **S** - Service | `services/` | Business logic, workflows |
| **P** - Presenter | `presenters/` | HTTP handlers, routing |
| **T** - Tests | `tests/` | Unit + integration tests |

**Why MVRSPT over MVC?**
- Repository layer enables easy mocking and database swapping
- Service layer isolates business logic from HTTP concerns
- Tests are first-class citizens, not an afterthought

---

#### 10. Nexus (Knowledge Base)

**Repository:** `ritz-lang/nexus`
**Purpose:** Official Ritz documentation wiki
**Status:** Design phase

Nexus is both:
1. **A Wiki** — Documentation for language, stdlib, and ecosystem
2. **A Reference Implementation** — Built on the full Ritz stack

Built on: Spire → Zeus → Valet → Mausoleum/Tome → Cryptosec/Squeeze → Ritz

---

### System Layer

#### 11. Harland (Kernel)

**Repository:** `ritz-lang/harland`
**Purpose:** Operating system kernel written in Ritz
**Status:** Active development

Currently migrating to new Ritz syntax via `--syntax reritz`.

---

## Project Dependencies

```
ritz (compiler)
└── (none - foundation)

ritzunit
└── ritz

squeeze
├── ritz
└── ritzunit

cryptosec
├── ritz
└── ritzunit

mausoleum
├── ritz
├── ritzunit
└── cryptosec

tome
├── ritz
└── ritzunit

valet
├── ritz
├── squeeze
└── cryptosec

zeus
├── ritz
└── valet

spire
├── ritz
├── ritzunit
├── zeus
├── mausoleum (optional)
└── tome (optional)

nexus
├── spire
├── mausoleum
└── tome

larb
├── ritz
├── ritzunit
├── squeeze
├── valet
├── cryptosec
├── mausoleum
├── tome
├── zeus
├── spire
└── nexus
```

---

## Test Counts Summary

| Project | Tests | Coverage |
|---------|-------|----------|
| ritz | 324 + 201 | Language + unit |
| ritzunit | Self-testing | Framework validation |
| squeeze | 132 | All algorithms |
| valet | 85 | Server features |
| cryptosec | 331 | All crypto primitives |
| mausoleum | ~100+ | Database operations |
| **Total** | **~1,200+** | - |

---

## Naming Theme

The Ritz ecosystem draws from multiple naming conventions:

**StarCraft Buildings:**
- **Nexus** (Protoss) — Knowledge base
- **Spire** (Zerg) — Web framework
- *(Terran building TBD)* — CLI/scaffolding?

**Classical/Arcane:**
- **Mausoleum** — Where data is entombed forever
- **Tome** — Book of knowledge (in-memory)
- **Valet** — Attendant/servant (HTTP server)
- **Zeus** — King of gods (app server)
- **Cryptosec** — Secrets/security

**Practical:**
- **Squeeze** — Compression
- **Ritz** — The language (crackers, luxury)
- **LARB** — Language Architecture Review Board
