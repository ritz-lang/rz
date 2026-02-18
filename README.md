# Ritz 🎭

**Ritz** is a systems programming language and ecosystem for building software from the ground up.

The language compiles to LLVM IR and runs on multiple platforms:
- **Linux** — direct syscalls, no libc dependency
- **Harland** — our own microkernel OS, also written in Ritz

This monorepo (`rz`) contains everything: the compiler, standard library, an operating system, a web stack, a browser engine, and real-world applications — all serving as reference implementations that demonstrate idiomatic Ritz.

## Quick Start

```bash
# Set up the environment
export RITZ_PATH=$PWD/projects

# Build a project
./rz build valet

# Run tests
./rz test ritz

# Build everything
./rz build --all
```

## Projects

### Core Toolchain

| Project | Description |
|---------|-------------|
| **ritz** | Core compiler — Python-based bootstrap (ritz0) compiling to LLVM IR, plus self-hosted compiler (ritz1) |
| **ritzlib** | Standard library — sys (syscalls), io, memory, strings, collections, async primitives |
| **ritzunit** | Test framework — fork-based isolation, assertions, test discovery, valgrind integration |
| **ritz-lsp** | Language server — IDE support with completions, hover, go-to-definition |
| **larb** | Language Architecture Review Board — specs, RFCs, style guides, tooling standards |

### Core Libraries

| Project | Description |
|---------|-------------|
| **cryptosec** | Cryptography — TLS 1.3, AES-GCM, SHA-256/512, Ed25519, X25519, P-256, ChaCha20-Poly1305 |
| **squeeze** | Compression — gzip, deflate, zlib with streaming support |
| **http** | HTTP protocol — HTTP/1.x parser, HTTP/2 with HPACK, HTTP/3 with QUIC |

### Web & Network Stack

| Project | Description |
|---------|-------------|
| **valet** | Async HTTP server — io_uring backend, TLS termination, static files, reverse proxy |
| **zeus** | Process runner — zero-copy IPC, worker pool management, graceful restarts |
| **spire** | Web framework — MVRSPT pattern (Model-View-Repo-Service-Presenter-Template), routing, middleware |

### Data & Storage

| Project | Description |
|---------|-------------|
| **mausoleum** | Document database — tree/graph queries, BSON-like format, persistence, replication |
| **tome** | In-memory cache — Redis-compatible protocol, LRU eviction, pub/sub |
| **goliath** | Content-addressable filesystem — blob storage, deduplication, integrity verification |

### OS & Graphics

| Project | Description |
|---------|-------------|
| **harland** | Microkernel OS — UEFI boot, SMP, L4-style IPC, VirtIO drivers, memory-mapped I/O |
| **prism** | Display server — Wayland-inspired compositor, GPU framebuffer, window management |
| **angelo** | Font rendering — TrueType/OpenType parsing, hinting, subpixel rendering |
| **iris** | Rendering engine — layout, paint, hit testing, display lists |

### Browser Stack

| Project | Description |
|---------|-------------|
| **tempest** | Web browser — multi-process architecture, built on lexis/sage/iris/angelo, the ultimate Ritz stress test |
| **lexis** | HTML/CSS parser — HTML5-compliant tokenizer and tree builder, CSS selectors |
| **sage** | JavaScript engine — bytecode compiler, garbage collector, ES6+ support |

### Applications & Tools

| Project | Description |
|---------|-------------|
| **nexus** | Official Ritz wiki — built on the full stack (mausoleum → tome → spire → zeus → valet), serves as living documentation |
| **spectree** | Specification tree — hierarchical specs and actions that drive each other, planning tool |
| **indium** | Harland distribution — packaging, installation, system images |
| **rzsh** | Ritz shell — terminal shell with raw mode input, line editing, history, runs on Linux and Harland |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Applications                              │
│  nexus  │  spectree  │  tempest  │  rzsh                        │
├─────────────────────────────────────────────────────────────────┤
│                      Web & Network Stack                         │
│  spire (framework)  │  valet (server)  │  zeus (process runner) │
├─────────────────────────────────────────────────────────────────┤
│                        Core Libraries                            │
│  cryptosec  │  squeeze  │  http  │  mausoleum  │  tome          │
├─────────────────────────────────────────────────────────────────┤
│                     Graphics & Display                           │
│  prism (compositor)  │  angelo (fonts)  │  iris (rendering)     │
├─────────────────────────────────────────────────────────────────┤
│                        OS / Kernel                               │
│  harland (microkernel)  │  goliath (filesystem)  │  indium      │
├─────────────────────────────────────────────────────────────────┤
│                        Core Toolchain                            │
│  ritz (compiler)  │  ritzlib (stdlib)  │  ritzunit (testing)    │
└─────────────────────────────────────────────────────────────────┘
```

## Documentation

- [Language Specification](projects/larb/docs/LANGUAGE_SPEC.md)
- [Style Guide](projects/larb/docs/STYLE.md)
- [Ecosystem Overview](projects/larb/docs/ECOSYSTEM.md)
- [Standard Library Reference](projects/larb/docs/STDLIB_REFERENCE.md)

## Philosophy

Ritz follows a "no concessions" doctrine: if the language can't express something cleanly, we fix the language rather than work around it. Every project in this repo is both a useful tool and a test case for the language itself.

The ecosystem is designed to be self-hosting: Ritz compiles itself, runs on its own OS, serves its own web applications, and renders its own fonts.

## License

MIT
