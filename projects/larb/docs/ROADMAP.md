# Ritz Ecosystem Roadmap: superseded

**This file was retired on 2026-10-25 by the LARB retrospective (AGAST #1800).**

The one current roadmap is
[`projects/ritz/docs/ROADMAP.md`](../../ritz/docs/ROADMAP.md), in the section
"The destination, and the tracks that get there". It holds structure only:
epics, milestones and their definitions of done, each with an AGAST ID. Status
lives in AGAST and in the commands that roadmap cites.

The previous contents were written on 2026-02-15 and never updated. By October,
almost every row was stale:

- **Self-hosting:** listed as blocked on monomorphization. In fact ritz1 self-hosts, and regression.sh Stage 5 asserts the fixed point.
- **DWARF:** listed as open. ritz0 already emits it.
- **Squeeze:** dynamic Huffman listed as open, but it is implemented (`squeeze/lib/deflate.ritz`).
- **ritzunit:** filters listed as open, but they are implemented (`ritzunit/src/filter.ritz`).
- **cryptosec:** the TLS 1.3 handshake listed as open, but it is implemented (`cryptosec/lib/tls13_client.ritz`).
- **Kernel track:** it never mentioned harland, the kernel track, EC2 or inline `asm`.

Git keeps the old text (`git show 7eedf4f:projects/larb/docs/ROADMAP.md`).

## Items carried forward

These feature ideas from the old file still have no home in a track. They are
parked, not dropped. Each one goes into AGAST when a track depends on it.

| Idea | Old reference | Where it would land |
|---|---|---|
| Package distribution and shared libraries (RFC) | GH #107 | Tooling epic #1833, after the manifest schema (#1837) |
| Compile-time function evaluation (comptime) | GH #101 | Track 1, M1.2 (#1829), as a language decision |
| Parameterized tests (RFC) | GH #100 | Track 1, M1.2 (#1829) |
| Const struct literals at module level | GH #95 | Track 1, M1.2 (#1829). Check first whether it already works. |
| LSP: completion, diagnostics, references (definition and hover exist in `projects/ritz-lsp`) | Phase 2 | Parked. Resumes after M1.4 (#1831), when ritz1 is the compiler to embed. |
| `rz fmt`, doc generator | Phase 4 | Tooling epic #1833 |
| Compiler performance (incremental, parallel) | Phase 5 | Track 0, epic #1801 (fast iteration) |
| ritzunit parallel execution, JUnit XML; squeeze lazy matching; valet HTTP/2 and WebSocket; cryptosec AES-NI | Project tables | Parked with PHASE 8 (#50) |
