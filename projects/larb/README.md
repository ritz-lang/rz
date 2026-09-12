# LARB - Language and Architecture Review Board

LARB holds the design direction and implementation-planning documents for the
**Ritz programming language ecosystem**:

1. **Language Specification** — syntax, semantics, and behavior
2. **Architecture Review** — design decisions, RFCs, and architectural guidance
3. **Agent Context** — minimal, efficient references for AI agents

## This is a documentation directory, not a project

`projects/larb/` contains **only** Markdown, a couple of Python tools, and
archived session logs. There is no `ritz.toml`, nothing to compile, and nothing
to test — `./rz list` deliberately excludes it (it reports 26 buildable
projects; larb is not one of them).

It is also **not a separate repository**. larb was consolidated into the `rz`
monorepo in February 2026. Specifically:

- There is no `github.com/ritz-lang/larb`. The remote is
  `git@github.com:ritz-lang/rz.git`.
- There are no git submodules. The repository has no `.gitmodules`, so
  `git submodule update --init --recursive` is a silent no-op.
- There is no `projects/larb/projects/` directory and no `projects/larb/specs/`
  directory. Earlier revisions of this README described both.

To get these docs, clone the monorepo:

```bash
git clone git@github.com:ritz-lang/rz.git
cd rz/projects/larb
```

## Quick Links

- [Language Quick Reference](docs/QUICK_REFERENCE.md) — minimal context for productive agents
- [Design Decisions](docs/DESIGN_DECISIONS.md) — why the language is the way it is
- [Ecosystem Overview](docs/ECOSYSTEM.md) — all Ritz projects explained
- [Open Issues & Roadmap](docs/ROADMAP.md)
- [LSP Server Requirements](docs/LSP_REQUIREMENTS.md)
- [ritz.toml Specification](docs/RITZ_TOML_SPEC.md)
- [PR Checklist](docs/PR_CHECKLIST.md)

Note that the **canonical** language spec, style guide, stdlib reference and
ecosystem overview moved to `projects/ritz/docs/` on 2026-09-03 (AGAST #1311),
because those are the copies `make -C projects/ritz check-doc-examples`
compiles on every build. The copies here are historical; prefer
`projects/ritz/docs/` when they disagree.

## Ritz Ecosystem Projects

Status and test counts are not tracked here — they go stale. Run the tools:

```bash
./rz list                      # the 26 buildable projects, from rz.toml
./rz build --all               # what compiles today
./rz test <project>            # what passes today
```

Each project's own `README.md` carries its status. For the compiler bootstrap
specifically, see [`docs/STACK_MATRIX.md`](../../docs/STACK_MATRIX.md).

This table previously carried per-project test counts (ritz 324, squeeze 132,
valet 85, cryptosec 331) and a throughput figure for valet of "1.47M req/sec".
All were stale or unsourced. The `[[test]]` marker counts as of 2026-09-12 are
ritz 1214, cryptosec 485, squeeze 199, valet 99 — which is why hardcoding them
here was a mistake worth not repeating. The 1.47M figure has no measurement
behind it anywhere in this repo; `projects/valet/test/test_basic.sh` measured
28,108 and 34,850 req/s across two runs on 2026-09-12.

## Design Principles

1. **Minimal syntax, big library** — Python-style indentation, no semicolons or braces
2. **Type-safe with inference** — static types with extensive type inference
3. **Ownership without annotations** — Rust semantics with simpler surface syntax
4. **One language for everything** — from kernel to script, same syntax
5. **Bootstrappable** — self-hosting compiler shipped as LLVM IR

## Directory Structure

```
projects/larb/
├── docs/                   # Specs, RFCs, design decisions, reviews
├── review/                 # Review instructions
├── tools/                  # migrate_cstr.py, ritz-lint/
├── logs/                   # Archived session transcripts (Feb 2026)
├── CAPABILITY_SPEC.md
├── DEFAULTS.md
├── MISSING_FEATURES_SPEC.md
└── AGENT.md
```

## Contributing

Design discussions happen in GitHub Issues and Discussions on the `rz`
repository. Code changes go to the relevant `projects/<name>/` directory in the
same monorepo — cross-project changes are a single commit.
