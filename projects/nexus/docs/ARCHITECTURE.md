# Nexus Architecture

**LARB Document** | **Status:** Draft | **Version:** 0.1 | **Date:** 2026-02-14

---

## Overview

Nexus is the Ritz Knowledge Base - a wiki platform documenting the language, stdlib, and ecosystem. It serves as both documentation and a reference implementation of the full Ritz stack.

---

## Stack Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              NEXUS                                       │
│                       Ritz Knowledge Base                                │
│                                                                          │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│   │    Wiki     │  │   Search    │  │   History   │  │    API      │   │
│   │   Pages     │  │   Index     │  │  Versions   │  │   Docs      │   │
│   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
├─────────────────────────────────────────────────────────────────────────┤
│                              SPIRE                                       │
│                        MVRSPT Framework                                  │
│                                                                          │
│   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│   │ Models  │ │  Views  │ │  Repos  │ │Services │ │Presenters│          │
│   │WikiPage │ │Templates│ │Mausoleum│ │Business │ │  Routes  │          │
│   │PageLink │ │  HTML   │ │  Tome   │ │  Logic  │ │  HTTP    │          │
│   └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
├─────────────────────────────────────────────────────────────────────────┤
│                              ZEUS                                        │
│                    App Server / Process Manager                          │
│                                                                          │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│   │   Master    │  │   Workers   │  │   Config    │  │   Signals   │   │
│   │  Process    │  │   (N CPU)   │  │   Loader    │  │   Handler   │   │
│   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
├─────────────────────────────────────────────────────────────────────────┤
│                              VALET                                       │
│                     HTTP/1.1 Server + TLS 1.3                           │
│                                                                          │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│   │   Parser    │  │  Handler    │  │ Middleware  │  │    TLS      │   │
│   │ HTTP/1.1    │  │  Pipeline   │  │   Chain     │  │  Terminator │   │
│   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
├────────────────────────────────┬────────────────────────────────────────┤
│           MAUSOLEUM            │              TOME                       │
│         Document Store         │         In-Memory Cache                 │
│                                │                                         │
│  ┌─────────┐  ┌─────────┐     │  ┌─────────┐  ┌─────────┐              │
│  │ B-tree  │  │  Query  │     │  │   KV    │  │  TTL    │              │
│  │ Storage │  │ Engine  │     │  │  Store  │  │ Evict   │              │
│  └─────────┘  └─────────┘     │  └─────────┘  └─────────┘              │
│  ┌─────────┐  ┌─────────┐     │  ┌─────────┐  ┌─────────┐              │
│  │  MVCC   │  │Secondary│     │  │  Lists  │  │ Hashes  │              │
│  │ Version │  │ Indexes │     │  │  Sets   │  │ ZSets   │              │
│  └─────────┘  └─────────┘     │  └─────────┘  └─────────┘              │
├────────────────────────────────┴────────────────────────────────────────┤
│           CRYPTOSEC            │            SQUEEZE                      │
│            TLS 1.3             │          Compression                    │
│   AES-GCM, ChaCha20, X25519    │      gzip, deflate, zlib                │
├─────────────────────────────────────────────────────────────────────────┤
│                         RITZ + RITZUNIT                                  │
│                    Compiler + Test Framework                             │
│                                                                          │
│   ritz0 (Python bootstrap) → ritz1 (self-hosted) → ritzunit (testing)  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Readiness

| Component | Status | Readiness | Tests | Notes |
|-----------|--------|-----------|-------|-------|
| **Ritz** | Active | 85% | 500+ | Self-hosting in progress |
| **Ritzunit** | Production | 95% | Native | 90x faster than ritz0 |
| **Mausoleum** | Phase 4 | 78% | 373 ✅ | Document storage ready |
| **Tome** | Phase 9b | 72% | 101 ✅ | Single-process ready |
| **Spire** | Phase 1 | 28% | 0 ❌ | HTTP types only |
| **Valet** | Production | 95% | 85+ ✅ | **1.47M req/sec** - HTTP/1.1, TLS 1.3, io_uring, compression |
| **Zeus** | Production | 90% | 127 ✅ | Worker IPC, hot reload, work stealing |
| **Cryptosec** | Production | 95% | 331 ✅ | TLS 1.3 ready |
| **Squeeze** | Production | 95% | 132 ✅ | gzip/deflate ready |

---

## Data Flow

### Request Path

```
Browser → Valet (HTTP) → Zeus (Worker) → Spire (Presenter)
                                              ↓
                                         Service Layer
                                              ↓
                              ┌───────────────┴───────────────┐
                              ↓                               ↓
                        Mausoleum                          Tome
                     (Document DB)                       (Cache)
```

### Page View Flow

```
GET /language/syntax
        │
        ↓
   ┌─────────┐
   │  Valet  │  Parse HTTP request
   └────┬────┘
        │
        ↓
   ┌─────────┐
   │  Zeus   │  Route to worker
   └────┬────┘
        │
        ↓
   ┌─────────┐
   │ Spire   │  PagePresenter.show()
   │Presenter│
   └────┬────┘
        │
        ↓
   ┌─────────┐
   │ Spire   │  WikiService.get_page()
   │ Service │
   └────┬────┘
        │
        ├──────────────────────┐
        ↓                      ↓
   ┌─────────┐            ┌─────────┐
   │  Tome   │  Cache hit?│Mausoleum│
   │ (cache) │←───────────│ (db)    │
   └────┬────┘            └─────────┘
        │
        ↓
   ┌─────────┐
   │  View   │  Render markdown → HTML
   │Template │
   └────┬────┘
        │
        ↓
   HTTP Response (200 OK, text/html)
```

---

## Deployment Architecture

### Docker Compose (Multi-Container)

```yaml
version: '3.8'

services:
  # HTTP Front-end (Valet)
  valet:
    build: ../valet
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./certs:/certs:ro
    environment:
      - UPSTREAM=zeus:8080
      - TLS_CERT=/certs/cert.pem
      - TLS_KEY=/certs/key.pem
    depends_on:
      - zeus

  # App Server (Zeus)
  zeus:
    build: ../zeus
    expose:
      - "8080"
    environment:
      - WORKERS=4
      - MAUSOLEUM_HOST=mausoleum
      - MAUSOLEUM_PORT=7777
      - TOME_HOST=tome
      - TOME_PORT=6379
    depends_on:
      - mausoleum
      - tome

  # Document Database (Mausoleum)
  mausoleum:
    build: ../mausoleum
    expose:
      - "7777"
    volumes:
      - nexus-data:/data
    environment:
      - DATA_PATH=/data/nexus.m7m

  # In-Memory Cache (Tome)
  tome:
    build: ../tome
    expose:
      - "6379"
    environment:
      - MAX_MEMORY=256MB
      - EVICTION_POLICY=allkeys-lru

volumes:
  nexus-data:
```

### Single Binary (Embedded Mode)

For development and simple deployments, all components can be linked into one executable:

```ritz
import mausoleum { Db }
import tome { Store }
import spire { App, Router }

fn main() -> Result<(), NexusError>
    # Embedded storage
    let db = Db.open("nexus.m7m")?
    let cache = Store.new(256 * MB)

    # Build application
    var app = App.new()
    app.set_db(db)
    app.set_cache(cache)

    # Configure routes
    var router = Router.new()
    router.get("/", page_handler)
    router.get("/:slug", page_handler)
    router.get("/:slug/edit", edit_handler)
    router.post("/:slug", save_handler)
    app.set_router(router)

    # Start server (built-in HTTP, no Valet/Zeus)
    app.listen(":8080")?
    Ok(())
```

---

## Gap Analysis Summary

### Ready Now ✅

| Component | Can Use For |
|-----------|-------------|
| **Valet** | HTTP serving, routing, compression, static files (1.47M req/sec!) |
| **Mausoleum** | Store wiki pages, versions, links |
| **Tome** | Cache hot pages, sessions |
| **Cryptosec** | TLS termination (integration in progress) |
| **Squeeze** | Compress HTTP responses (already integrated in Valet) |

### Needs Building ❌

| Component | Effort | Priority |
|-----------|--------|----------|
| **Zeus** (App Server) | 2-3 weeks | HIGH |
| **Spire** Repositories | 1 week | HIGH |
| **Spire** Services | 1 week | HIGH |
| **Spire** Presenters | 1 week | MEDIUM |
| **Spire** Views/Templates | 2 weeks | MEDIUM |
| **TLS in Valet** | 1 week | MEDIUM |

### Blocking Dependencies

```
Nexus ← Spire (28%) ← needs Repos, Services, Presenters
      ← Zeus (0%)   ← NOT STARTED
      ← Valet (90%) ← READY! TLS integration in progress
```

---

## Development Phases

### Phase 0: Integration (Week 1-2)

Wire up existing production-ready components:

1. Integrate Valet HTTP server (already 1.47M req/sec!)
2. Connect to Mausoleum for document storage
3. Connect to Tome for caching
4. Basic wiki page serving

**Goal:** Serve wiki pages using existing infrastructure

### Phase 1: Framework (Week 3-4)

Complete Spire framework integration:

1. Repository layer (Mausoleum + Tome)
2. Service layer (business logic)
3. Presenter layer (HTTP handlers)
4. View layer (templates)

**Goal:** Clean MVRSPT architecture

### Phase 2: TLS & Security (Week 5-6)

Add TLS support:

1. Integrate Cryptosec with Valet
2. Certificate loading
3. ALPN negotiation
4. Security hardening

**Goal:** HTTPS support

### Phase 3: Process Management (Week 7-8)

Build Zeus app server:

1. Master/worker architecture
2. Socket sharing (SO_REUSEPORT)
3. Health monitoring
4. Graceful reload

**Goal:** Multi-process, production-ready

### Phase 4: Production (Week 9+)

1. HTTP/2 support
2. Metrics and monitoring
3. Backup/restore
4. Documentation

---

## Decision: Deployment Strategy

### Recommended: Use Valet Now

```
Week 1-2: Integrate Valet (already done!)
Week 3-4: Complete Spire framework
Week 5-6: Add TLS via Cryptosec
Week 7+:  Build Zeus for multi-process
```

**Pros:**
- Valet already achieves 1.47M req/sec with 85+ tests
- No throwaway code - use production HTTP server
- Demo in 1-2 weeks
- Compression, routing, static files already working

**Alternative: Build Zeus First**

```
Week 1-3: Build Zeus process manager
Week 4+:  Integrate with Valet
```

**Pros:**
- Multi-process from start

**Cons:**
- Delays initial demo
- Valet works fine single-process

---

## Recommended Next Steps

1. **Integrate Valet** - Use the production-ready HTTP server (1.47M req/sec!)
2. **Wire up Mausoleum** - Store/retrieve wiki pages
3. **Wire up Tome** - Cache hot pages
4. **Serve first wiki page** - "Hello World" demo
5. **Complete Spire repos/services** - Clean architecture

The HTTP layer is solved - focus on framework integration!

---

*This document is maintained in the Nexus repository. For updates, see GitHub issues.*
