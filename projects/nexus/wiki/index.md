# Ritz

**A systems programming language for the modern era.**

Ritz is a compiled, statically typed systems programming language that compiles to LLVM IR. It brings Python-like readability and Rust-like memory safety to bare-metal programming — with no libc, no garbage collector, and no compromises on performance.

---

## Why Ritz?

| Feature | Description |
|---------|-------------|
| **No libc** | Direct Linux syscalls. No C runtime dependency. |
| **Python-like syntax** | Indentation-based, readable, minimal noise |
| **Rust-like safety** | Ownership, borrowing, and move semantics at compile time |
| **Self-hosting** | The compiler compiles itself (ritz1 compiles 47/48 examples) |
| **LLVM backend** | Native performance via LLVM IR |
| **io_uring async** | First-class async I/O with the modern Linux kernel interface |

---

## The Ecosystem

Ritz is more than a language — it is a complete systems platform. Every component of the stack is written in Ritz.

### Kernel

The foundation of the Ritz OS platform.

| Project | Description | Status |
|---------|-------------|--------|
| [Harland](projects/harland.md) | Microkernel for x86-64 | Active |
| [Indium](projects/indium.md) | OS distribution layer | Active |
| [Goliath](projects/goliath.md) | Content-addressable filesystem | Design |
| [Prism](projects/prism.md) | Display server and compositor | Active |
| [Angelo](projects/angelo.md) | Font loading and rendering | Active |

### Web Stack

A complete, high-performance web platform.

| Project | Description | Status |
|---------|-------------|--------|
| [Valet](projects/valet.md) | HTTP/1.1 server — 1.47M req/s | Production |
| [Zeus](projects/zeus.md) | App server and process manager | Design |
| [Spire](projects/spire.md) | MVRSPT web framework | Design |
| [HTTP](projects/http.md) | HTTP client library | Active |

### Data

Persistence and caching for the Ritz stack.

| Project | Description | Status |
|---------|-------------|--------|
| [Mausoleum](projects/mausoleum.md) | Document database with MVCC | Phase 4 |
| [Tome](projects/tome.md) | In-memory cache (like Redis) | Design |

### Security and Infrastructure

| Project | Description | Status |
|---------|-------------|--------|
| [Cryptosec](projects/cryptosec.md) | TLS 1.3, AES, ChaCha20, X25519 | Active (331 tests) |
| [Squeeze](projects/squeeze.md) | gzip/deflate compression | Production (132 tests) |

### Tooling

| Project | Description | Status |
|---------|-------------|--------|
| [Ritz](projects/ritz.md) | Compiler and standard library | Active (324 tests) |
| [Ritzunit](projects/ritzunit.md) | Test framework with ELF discovery | Production |
| [Ritz-LSP](projects/ritz-lsp.md) | Language Server Protocol implementation | MVP |
| [rzsh](projects/rzsh.md) | Ritz shell | Active |

### Browser Stack

A complete browser built in Ritz.

| Project | Description | Status |
|---------|-------------|--------|
| [Tempest](projects/tempest.md) | Web browser | Active |
| [Iris](projects/iris.md) | Rendering engine | Active |
| [Sage](projects/sage.md) | JavaScript engine | Active |
| [Lexis](projects/lexis.md) | HTML5 and CSS parser | Active |

### Applications

| Project | Description | Status |
|---------|-------------|--------|
| [Nexus](projects/nexus.md) | This wiki — Ritz knowledge base | Design |
| [Spectree](projects/spectree.md) | Spec/plan tree for AI-assisted development | Alpha |

---

## Quick Stats

| Metric | Value |
|--------|-------|
| Language tests passing | 324 |
| Unit tests | 201 |
| Compression tests (squeeze) | 132 |
| Crypto tests (cryptosec) | 331 |
| HTTP server tests (valet) | 85 |
| Total ecosystem tests | ~1,200+ |
| Standard library modules | 35 |
| Example programs | 75+ |
| Valet throughput | 1.47M req/s |

---

## Get Started

New to Ritz? Start here:

1. [Getting Started](getting-started.md) — Install, build, and run your first program
2. [Language Overview](language/overview.md) — Introduction to the language
3. [Syntax Reference](language/syntax.md) — Complete syntax guide
4. [Architecture](architecture.md) — How the ecosystem fits together

---

## Subsystems

The ecosystem is organized into six subsystems. Each subsystem page describes how the projects in that area work together.

- [Kernel Subsystem](subsystems/kernel.md) — Harland, Goliath, Prism, Angelo
- [Graphics Subsystem](subsystems/graphics.md) — Prism display server, Angelo font rendering
- [Web Stack Subsystem](subsystems/web-stack.md) — Valet, Zeus, Spire, HTTP
- [Data Subsystem](subsystems/data.md) — Mausoleum, Tome
- [Tooling Subsystem](subsystems/tooling.md) — Compiler, LSP, Shell
- [Security Subsystem](subsystems/security.md) — Cryptosec, Squeeze

---

## Naming

The Ritz ecosystem draws its names from multiple traditions:

- **StarCraft buildings:** Nexus (Protoss), Spire (Zerg)
- **Classical and arcane:** Mausoleum (data entombed forever), Tome (book of knowledge), Zeus (king of the app tier), Valet (serving HTTP requests)
- **Practical:** Squeeze (compression), Ritz (the language itself), LARB (Language Architecture Review Board)

---

*Nexus is built on the full Ritz stack: Spire + Zeus + Valet + Mausoleum + Tome + Cryptosec + Squeeze.*
*This wiki is both documentation and a reference implementation.*
