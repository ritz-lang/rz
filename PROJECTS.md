# Ritz Monorepo — Project Summary

A complete systems programming ecosystem built from scratch in the **Ritz language**, which compiles to LLVM IR with no libc (direct Linux syscalls only).

`./rz list` is the authoritative project list — it reports **26** buildable
projects. `projects/ritzlib` (a symlink into `projects/ritz/ritzlib`) and
`projects/larb` (documentation only) are deliberately excluded.

Counts and status below are measured, with the date. Where a number would go
stale, the command to regenerate it is given instead.

## Core Toolchain

| Project | Description |
|---|---|
| **ritz** | The Ritz compiler — Python bootstrap (ritz0) + self-hosted compiler (ritz1) + ritz1 compiled by itself (ritz1_selfhosted) |
| **ritzlib** | Standard library, inside `projects/ritz/ritzlib` (sys, io, memory, async, collections, …) |
| **ritzunit** | Unit testing framework with ELF symbol auto-discovery and fork-based isolation |
| **ritz-lsp** | Language Server Protocol implementation with Vim/coc.nvim integration |
| **rzrz** | `rz` reimplemented in Ritz — see [docs/STACK_MATRIX.md](docs/STACK_MATRIX.md) |
| **larb** | Language Architecture Review Board — specs, design decisions, RFCs (docs only, not a build target) |

## Core Libraries

| Project | Description |
|---|---|
| **cryptosec** | Crypto library: TLS 1.3, AES-GCM, ChaCha20-Poly1305, SHA-2, X25519, Ed25519, P-256, RSA, X.509 |
| **squeeze** | Compression: gzip/deflate/zlib, streaming readers and writers, SIMD acceleration |
| **http** | HTTP wire protocol for HTTP/1.x, HTTP/2, and HTTP/3+QUIC (library only, `test_only = true`) |

## Web & Network Stack

| Project | Description |
|---|---|
| **valet** | Async HTTP/1.1 server using io_uring, with routing, static files, middleware, compression and TLS |
| **zeus** | Zero-copy process runner with shared memory ring buffer IPC between Valet and workers |
| **spire** | MVRSPT web framework (Django/Rails-like productivity); library only, `test_only = true` |

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
| **indium** | Harland distribution — init, userspace utilities (incl. `cat`, formerly ritzutils), bootable ISO/UEFI images |
| **prism** | Display server & compositor; currently ships two Harland-target demo binaries, not a server |
| **angelo** | Font rendering library — TrueType/OpenType parsing and glyph rasterization |
| **iris** | Rendering engine for layout, painting, and hit testing |

## Browser Stack

| Project | Description |
|---|---|
| **tempest** | Multi-process web browser integrating the full Ritz stack — builds; browser and tab process scaffolding only (ignores its URL argument) |
| **lexis** | HTML5 & CSS parser — builds and runs its built-in tokenizer/parser demo |
| **sage** | JavaScript engine — builds and runs, but does not yet accept a script argument |

## Applications & Tools

| Project | Description |
|---|---|
| **nexus** | Knowledge base & wiki — builds; the binary is a Zeus worker, not a standalone server |
| **rzsh** | Cross-platform shell — builds for both Harland (`rzsh.elf`) and Linux (`rzsh.linux`) |
| **buddhafinger** | Modal terminal code editor, skeleton so far ([proposal](docs/BUDDHAFINGER_PROPOSAL.md)); built and tested with ritz1_selfhosted only, by `make -C projects/buddhafinger test` |

## Workspace Tooling

- **`rz`** — Python CLI for building, testing, running, and managing projects
- **`rz.toml`** — Workspace manifest: member projects and build settings
- **`known-failures/`** — every failure any gate excuses, one `<agast>.toml`
  per ticket, read by `projects/ritz/tools/known_failures.py` (AGAST #1834)
- **Shared `.ritz` modules** — `blob_id`, `blob_store`, `dir_entry`, `error`,
  `namespace`, `path` (from goliath)

## Build status (measured 2026-09-12)

`./rz build --all` exits 1 on a machine without `lld`. Everything builds except:

| Project | Cause |
|---|---|
| **harland** | `lld` not installed locally: `Cannot link UEFI target 'bootx64': lld-link not found`. Not excused in `known-failures/` — CI installs lld. |

Which projects are *excused* as known build failures, and why, is stated in one
place only: the `gate = "build"` entries in `known-failures/`, one file per
AGAST ticket. This file does not copy those reasons, because copies go stale.
`tempest` (since AGAST #3609) and `lexis` (since #3689) both build at exit 0,
re-checked 2026-11-18.

## Test counts

`[[test]]` markers in `.ritz` sources, counted 2026-09-12:

| Project | `[[test]]` markers |
|---|---|
| ritz | 1214 |
| cryptosec | 485 |
| squeeze | 199 |
| valet | 99 |

Regenerate with:

```bash
grep -rho '\[\[test\]\]' projects/<name> --include='*.ritz' | wc -l
```

Earlier revisions of this file reported 324 / 331 / 132 / 85 for these four.
Prefer running the suite over trusting a number in a doc:

```bash
./rz test <project>                 # per-project suite
make -C projects/ritz unit          # 58 pytest files (846 passed, exit 0)
make -C projects/ritz matrix-full   # 53 regression programs × 3 compilers
```

## Test suite status

Running `./rz test <project>` for each project, measured 2026-09-12.

**`rz test` is not green across the workspace.** Four suites fail and one passes
vacuously:

| Project | Exit | Result |
|---|---|---|
| valet | 0 | 99 passed, 5 files |
| squeeze | 0 | 199 passed, 15 files |
| sage | 0 | 73 passed, 2 files |
| iris | 0 | 30 passed, 3 files |
| ritzunit | 0 | 27 passed, 6 files |
| rzsh | 0 | 15 passed, 3 files |
| rzrz | 0 | 4 passed, 1 file |
| ritz | 0 | 11 passed, 2 files — **not the compiler suite**, see above |
| **spire** | **1** | 13 passed, **10 compile-failed** of 12: missing `spire.http.*` / `spire.app` modules, `headers_get` arity drift, unknown `clock_gettime` / `uuid_to_str` |
| **prism** | **1** | 14 passed, **6 compile-failed** of 9: parse error at `test/test_text_rendering.ritz:92:26` |
| **nexus** | **1** | 3 passed, **3 compile-failed** of 4: `Cannot find module: services.wiki_service` |
| **tome** | **1** | **0 passed**, 1 compile-failed of 5: `test_server_auth.ritz` exits 2 |
| **angelo** | **0** | `⚠ No tests found, skipping` — a **false green**. 106 `[[test]]` markers sit in `src/`; `rz test` looks for `test/` or a `[test]` section and finds neither |
| cryptosec, http, mausoleum, zeus, goliath | — | **not completed** within this pass (each runs for many minutes). goliath's own binary `build/debug/goliath-tests` does pass: 33 passed, exit 0 |

None of the four failures is excused: there is deliberately **no** test-side
excuse (`known-failures/` has no `test` gate, by design: "a test-side excuse
would excuse behavioural failure"). These should therefore be gating `rz test --all`.

## Project Maturity

The most mature projects are **ritz** (compiler), **cryptosec**, **squeeze**,
**valet**, **zeus** and **ritzunit** — all build clean and have substantial
passing suites. **harland** / **indium** (OS), **mausoleum** and **tome** build
and run but are less complete. The browser stack is the weakest link: **tempest**
builds but is scaffolding that ignores its URL argument, **lexis** runs only its
built-in demo, and **sage** compiles but ignores its arguments. **nexus** builds but has no runnable entry point yet.

The guiding principle is the **"No Concessions Doctrine"** — fix the language
rather than work around limitations.

## Archived

`spectree` and `angelo-simple` were taken out of the workspace by AGAST #1875;
they live under [`archive/`](archive/README.md), which records why. ritzutils
(one utility, `cat`) was merged into indium.
