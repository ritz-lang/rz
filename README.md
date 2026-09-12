# Ritz 🎭

**Ritz** is a systems programming language and ecosystem for building software from the ground up.

The language compiles to LLVM IR and runs on multiple platforms:
- **Linux** — direct syscalls, no libc dependency
- **Harland** — our own microkernel OS, also written in Ritz

This monorepo (`rz`) contains everything: the compiler, standard library, an operating system, a web stack, a browser engine, and real-world applications — all serving as reference implementations that demonstrate idiomatic Ritz.

## Prerequisites

```bash
sudo apt install clang lld python3 make
```

`lld` is not optional: harland's UEFI bootloader target (`bootx64`) links with
`lld-link`, and without it `./rz build --all` fails at exit 1 with
`Cannot link UEFI target 'bootx64': lld-link not found`. No other project needs
`lld` — but installing it does not make `build --all` green on its own, because
`lexis` and `tempest` fail for unrelated compiler reasons. See the
[build status table](#build-status) below.

`clang` 20 or newer is required. This machine has 21.1.8 (with `clang-20` also
present); no version is pinned anywhere, so plain `clang` is what gets used.

## Quick Start

Run everything from the workspace root. `rz` sets `RITZ_PATH` itself — you do
not need to export it.

```bash
# List the projects rz knows about
./rz list

# Build a project
./rz build valet

# Build everything
./rz build --all

# Run a project's test suite
./rz test valet
```

`./rz test` is **not currently green everywhere**: `spire`, `prism`, `nexus` and
`tome` all exit 1 (mostly test files that no longer compile), and `angelo` exits 0
while running nothing at all. See
[PROJECTS.md § Test suite status](PROJECTS.md#test-suite-status) for the measured
per-project table before trusting a green `rz test`.

### Testing the compiler

`./rz test ritz` exits 0 but only runs the **2** `.ritz` test files that live
under `projects/ritz` itself (11 assertions). It is not the compiler's test
suite and passing it does not mean the compiler is tested. The real gates are:

```bash
# ritz0 Python unit tests — 58 pytest files (~2 min)
make -C projects/ritz unit
# measured 2026-09-12: 846 passed, 8 skipped, 3 xpassed, exit 0

# Language regression matrix across all three compilers (~35s)
make -C projects/ritz matrix-full
# measured 2026-09-12: ritz0 53/53, ritz1 52/53, ritz1_selfhosted 52/53, exit 0.
# The one failure (test_issue_float_coercion) is excused as AGAST #1370, which
# is why the gate is green — "exit 0" here does not mean "53/53 everywhere".

# What CI declares (fast, prints the job list)
make -C projects/ritz ci-local ARGS="--list"

# CI's bootstrap job end to end (several minutes; not timed here).
# ARGS="--jobs" additionally runs the 26-project sweep (~50 min).
make -C projects/ritz ci-local
```

For reference, `projects/ritz` contains 1214 `[[test]]` markers across 208
`.ritz` files. Only 2 of those files sit in `projects/ritz/test/`, which is all
`rz test ritz` looks at — the rest live under `ritz0/` (115 files), `examples/`
(72), `ritzlib/` (18) and `ritz1/` (1), and are driven by `make test` /
`python3 build.py test --all`, not by `rz test`.

## Projects

`./rz list` is the authoritative list — it reports **26** buildable projects.
Two directories under `projects/` are deliberately not among them:

- `projects/ritzlib` is a symlink to `projects/ritz/ritzlib`; it is built as part
  of `ritz`, not as a project of its own.
- `projects/larb` is documentation only (specs, RFCs, review notes). Nothing to
  build or test.

### Core Toolchain

| Project | Description |
|---------|-------------|
| **ritz** | Core compiler — Python-based bootstrap (ritz0) compiling to LLVM IR, plus self-hosted compiler (ritz1) and the `ritzlib` standard library |
| **ritzunit** | Test framework — fork-based isolation, assertions, test discovery, valgrind integration |
| **ritz-lsp** | Language server — JSON-RPC transport and document sync work; diagnostics, hover, completions are not done |
| **rzrz** | `rz` reimplemented in Ritz — the Ritz-native workspace CLI (see [docs/STACK_MATRIX.md](docs/STACK_MATRIX.md)) |

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
| **spire** | Web framework — MVRSPT pattern (Model-View-Repo-Service-Presenter-Test), test-driven routing and middleware |

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
| **ritzutils** | Coreutils-style Harland userspace utilities (currently `cat`) |
| **angelo-simple** | Minimal Angelo render smoke test |

### Build status

The descriptions above state each project's *intent*. For what actually builds
and runs today, read the project's own README — several are further from their
description than the table suggests, and three have known failures:

| Project | `./rz build` | Note |
|---|---|---|
| **harland** | ✗ exit 1 locally | `bootx64` needs `lld`; see Prerequisites |
| **lexis** | ✗ exit 1 | 424 ownership errors, AGAST #1289 |
| **tempest** | ✗ exit 1 | emitter indirection-depth bug, AGAST #1302 |

`lexis` and `tempest` are excused in `rz.toml`'s `[ci.known_failing.build]`, so
`./rz build --all` reports them as advisory rather than gating. Measured
2026-09-12; every other project in `./rz list` built at exit 0.

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
│  ritz (compiler + ritzlib stdlib)  │  ritzunit (testing)        │
└─────────────────────────────────────────────────────────────────┘
```

## Documentation

- [Language Specification](projects/ritz/docs/LANGUAGE_SPEC.md)
- [Style Guide](projects/ritz/docs/STYLE.md)
- [Ecosystem Overview](projects/ritz/docs/ECOSYSTEM.md)
- [Standard Library Reference](projects/ritz/docs/STDLIB_REFERENCE.md)
- [Stack Matrix — bootstrap layering](docs/STACK_MATRIX.md)

## Philosophy

Ritz follows a "no concessions" doctrine: if the language can't express something cleanly, we fix the language rather than work around it. Every project in this repo is both a useful tool and a test case for the language itself.

The ecosystem is *designed* to be self-hosting: Ritz compiles itself, runs on its
own OS, serves its own web applications, and renders its own fonts. The language
half of that is real — `make -C projects/ritz matrix-full` exercises all three
compiler stages. The application half is not finished; see
[docs/STACK_MATRIX.md](docs/STACK_MATRIX.md) for which columns are actually
proven and which are still claims.

## License

MIT
