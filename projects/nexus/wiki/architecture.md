# Architecture

The Ritz ecosystem is a complete, vertically integrated systems platform. Every layer — from the microkernel to the web framework — is written in Ritz.

---

## The Full Stack

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              LARB                                        │
│                   (Standards and Coordination)                           │
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

## Browser Stack

In parallel to the web server stack, the browser stack forms a complete web client:

```
┌─────────────────────────────────────────────────────────────────────┐
│                           TEMPEST                                    │
│                       Web Browser Shell                              │
│                  Tabs, bookmarks, history, UI                        │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
    ┌─────────┐       ┌─────────┐       ┌─────────┐
    │  IRIS   │       │  SAGE   │       │  LEXIS  │
    │ Layout  │       │   JS    │       │HTML/CSS │
    │ Paint   │       │ Engine  │       │ Parser  │
    └────┬────┘       └─────────┘       └─────────┘
         │
         ▼
    ┌─────────┐
    │  PRISM  │
    │Display  │
    │ Server  │
    └─────────┘
```

---

## OS Stack

The Harland microkernel sits beneath everything on native hardware:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        User Space                                   │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐                │
│  │  Shell  │  │ Goliath │  │  NetD   │  │ Drivers │                │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘                │
│       │            │            │            │                      │
│       └────────────┴──────┬─────┴────────────┘                      │
│                           │ IPC (message passing)                   │
├───────────────────────────┼─────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  HARLAND MICROKERNEL                         │   │
│  │                                                              │   │
│  │  Scheduler │ IPC │ VMM (4-level paging) │ Interrupts        │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Project Dependencies

```
ritz (compiler)
└── (none — foundation)

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

tempest
├── iris
├── sage
├── lexis
├── valet
├── cryptosec
└── squeeze
```

---

## Layer Descriptions

### Foundation Layer

[Ritz](projects/ritz.md) and [Ritzunit](projects/ritzunit.md) are the foundation of everything. Every other project depends on them.

- **Ritz**: The compiler and standard library (ritzlib). Compiles to LLVM IR. No libc dependency.
- **Ritzunit**: Test framework with automatic test discovery via ELF symbol scanning.

### Infrastructure Layer

[Squeeze](projects/squeeze.md) and [Cryptosec](projects/cryptosec.md) provide the infrastructure primitives needed by the server layer.

- **Squeeze**: gzip/deflate compression used by Valet for HTTP compression and by Tempest for content-encoding.
- **Cryptosec**: Full TLS 1.3 implementation, hash functions, symmetric and asymmetric cryptography.

### Server Layer

[Valet](projects/valet.md) and [Zeus](projects/zeus.md) handle HTTP.

- **Valet**: The HTTP/1.1 server. Uses io_uring for async I/O. Benchmarks at 1.47M req/s — 10.7x faster than nginx.
- **Zeus**: The app server. Manages worker processes, load balancing, and zero-downtime deployments.

### Storage Layer

[Mausoleum](projects/mausoleum.md) and [Tome](projects/tome.md) handle persistence and caching.

- **Mausoleum**: An embedded document database with tree semantics, MVCC versioning, and graph queries. Inspired by SQLite, Git, and CouchDB.
- **Tome**: An in-memory data store similar to Redis, with pub/sub, TTL, and rich data structures.

### Application Layer

[Spire](projects/spire.md) and [Nexus](projects/nexus.md) provide application frameworks and the documentation platform.

- **Spire**: MVRSPT (Model-View-Repository-Service-Presenter-Tests) web framework. Provides Django/Rails-like productivity with Ritz performance.
- **Nexus**: This wiki — both documentation platform and reference implementation of the full Ritz stack.

### System Layer

[Harland](projects/harland.md), [Goliath](projects/goliath.md), [Prism](projects/prism.md), and [Angelo](projects/angelo.md) form the OS layer.

- **Harland**: IPC-based microkernel with preemptive scheduler, 4-level paging, and APIC interrupt handling.
- **Goliath**: Content-addressable filesystem with immutable blobs and mutable namespaces.
- **Prism**: Display server and window compositor with capability-based security.
- **Angelo**: Font loading and rendering library (TTF/OTF) for Prism.

---

## Design Principles

### No libc

Ritz programs make direct Linux syscalls using ritzlib's `sys.ritz` module. There is no dependency on glibc or any other C runtime.

```ritz
import ritzlib.sys { write, SYS_write }

fn print(msg: StrView)
    write(1, msg.as_ptr(), msg.len())
```

### Flat Ecosystem

All projects share a flat directory structure under `RITZ_PATH`. Dependencies are referenced by path:

```toml
[dependencies]
squeeze = { path = "../squeeze" }
cryptosec = { path = "../cryptosec" }
```

This means there is one copy of each project, and changes propagate immediately.

### No Concessions Doctrine

If Ritz cannot express something cleanly, the language is extended — not worked around. Every awkward pattern is an opportunity to improve the language.

### Test-Driven Development

Every project follows strict TDD. Tests are written before implementation. Over 1,200 tests pass across the ecosystem.

---

## Compile Pipeline

```
Ritz source (.ritz)
        │
        ▼
  ritz0 (Python bootstrap compiler)
  or
  ritz1 (self-hosted compiler)
        │
        ▼
   LLVM IR (.ll)
        │
        ▼
   LLVM/clang
        │
        ▼
   Native binary (ELF)
```

The self-hosted compiler ritz1 currently compiles 47 of 48 examples. Full self-hosting is in progress.

---

## See Also

- [Kernel Subsystem](subsystems/kernel.md)
- [Graphics Subsystem](subsystems/graphics.md)
- [Web Stack Subsystem](subsystems/web-stack.md)
- [Data Subsystem](subsystems/data.md)
- [Tooling Subsystem](subsystems/tooling.md)
- [Security Subsystem](subsystems/security.md)
