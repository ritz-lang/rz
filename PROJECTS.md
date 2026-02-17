# Ritz Monorepo — Project Summary

A complete systems programming ecosystem built from scratch in the **Ritz language**, which compiles to LLVM IR with no libc (direct Linux syscalls only).

## Core Toolchain

| Project | Description |
|---|---|
| **ritz** | The Ritz compiler — Python bootstrap (ritz0, 324 tests) + self-hosted compiler (ritz1) |
| **ritzlib** | Standard library (34 modules: sys, io, memory, async, collections, etc.) |
| **ritzunit** | Unit testing framework with ELF symbol auto-discovery and fork-based isolation |
| **ritz-lsp** | Language Server Protocol implementation with Vim/coc.nvim integration |
| **larb** | Language Architecture Review Board — spec, design decisions, RFCs |

## Core Libraries

| Project | Description |
|---|---|
| **cryptosec** | Crypto library: TLS 1.3, AES-GCM, ChaCha20, SHA-2, X25519, Ed25519 (331 tests) |
| **squeeze** | Compression: gzip/deflate/zlib with SIMD acceleration (132 tests) |
| **http** | HTTP wire protocol for HTTP/1.x, HTTP/2, and HTTP/3+QUIC |

## Web & Network Stack

| Project | Description |
|---|---|
| **valet** | High-performance async HTTP/1.1 server using io_uring (~250k+ req/sec, 85 tests) |
| **zeus** | Zero-copy process runner with shared memory ring buffer IPC between Valet and workers |
| **spire** | MVRSPT web framework (Django/Rails-like productivity) |

## Data & Storage

| Project | Description |
|---|---|
| **mausoleum** | Embedded document database with tree semantics, MVCC versioning, graph queries |
| **tome** | In-memory data store (Redis-like) with pub/sub and optional persistence |
| **goliath** | Content-addressable filesystem with immutable blobs and mutable namespaces |

## OS & Graphics

| Project | Description |
|---|---|
| **harland** | Microkernel OS — UEFI boot, 4-level paging, SMP scheduler, L4-style IPC |
| **prism** | Display server & compositor with hybrid rendering (buffer + command modes) |
| **angelo** | Font rendering library — TrueType/OpenType parsing and glyph rasterization |
| **iris** | Rendering engine for layout, painting, and hit testing |

## Browser Stack

| Project | Description |
|---|---|
| **tempest** | Multi-process web browser integrating the full Ritz stack |
| **lexis** | HTML5 & CSS parser with streaming tokenizer and cascade engine |
| **sage** | JavaScript engine for Tempest |

## Applications

| Project | Description |
|---|---|
| **nexus** | Knowledge base & wiki — reference app demonstrating the full stack |
| **spectree** | Hierarchical spec/planning tree with MCP server for AI-assisted development |

## Workspace Tooling

- **`rz`** — CLI script for building, testing, running, and managing projects
- **`rz.toml`** — Workspace manifest defining all member projects and build settings
- **Shared `.ritz` modules** — `blob_id`, `blob_store`, `dir_entry`, `error`, `namespace`, `path` (from goliath)

## Project Maturity

The most mature projects are **ritz** (compiler), **cryptosec**, **squeeze**, **valet**, and **ritzunit**. Projects like **harland** (OS) and **mausoleum** (database) are in active development, while the browser stack (tempest/lexis/sage) and some applications (nexus, spectree) are in design phase. The guiding principle is the **"No Concessions Doctrine"** — fix the language rather than work around limitations.
