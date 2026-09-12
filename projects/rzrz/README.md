# rzrz

`rz` rewritten in Ritz — the Ritz-native port of the workspace CLI.
("rz in rz" = rzrz.)

**Part of the [Ritz Ecosystem](../ritz/docs/ECOSYSTEM.md)**

## Overview

The workspace CLI at the monorepo root (`./rz`) is a Python script. `rzrz` is the
same CLI written in Ritz, so that the tool which builds the ecosystem is itself
built by the ecosystem. It is the subject of
[`docs/STACK_MATRIX.md`](../../docs/STACK_MATRIX.md), which tracks the compiler
bootstrap layering.

The project is deliberately small: one source file (`src/main.ritz`), one test
file (`test/test_args.ritz`), and `ritzlib` as its only dependency.

## Build

```bash
# From the monorepo root. `rz` sets RITZ_PATH itself.
./rz build rzrz
# Produces projects/rzrz/build/debug/rzrz

# Build it with the self-hosted compiler. The `clean` is REQUIRED —
# without it `--compiler` silently reuses the ritz0 build (AGAST #1360).
./rz clean rzrz && ./rz build rzrz --compiler ritz1

# Or with ritz1 compiled by itself
./rz clean rzrz && ./rz build rzrz --compiler ritz1_selfhosted

# Tests
./rz test rzrz          # 1 file, 4 assertions
```

All four commands above were measured at exit 0 on 2026-09-12.

## Usage

```bash
./projects/rzrz/build/debug/rzrz --help
./projects/rzrz/build/debug/rzrz list
./projects/rzrz/build/debug/rzrz build <project>
```

`--help` reports:

```
rz - Unified workspace CLI for the Ritz ecosystem

Usage:
    rz build [PROJECT]     Build a project (or all with --all)
    rz test [PROJECT]      Run tests for a project (or all with --all)
    rz run PROJECT         Build and run a project
    rz list                List all projects in workspace
    rz clean [PROJECT]     Clean build artifacts
    rz compare [TIER]      Compare ritz0 vs ritz1 on examples

Options:
    --all                  Apply to all projects
    --release              Build with release profile
    --help, -h             Show this help message
    --version, -V          Show version information
```

## Current limitation: it re-enters Python

`rzrz` does **not** compile anything itself. `build_project()`
(`src/main.ritz:225-248`) spawns:

```
python3 ./rz build <project> --compiler ritz1
```

So two things that are easy to assume are not true:

1. **It is not a Python-free orchestrator.** It requires `python3` and the `rz`
   script to be present, and must be run from the workspace root so that `./rz`
   resolves.
2. **It does not drive `ritz1_selfhosted`.** It hardcodes `--compiler ritz1`.
   Running `rzrz build <project>` measures the ritz1 column a second time. For
   the self-hosted column use
   `./rz clean <project> && ./rz build <project> --compiler ritz1_selfhosted`.

`docs/STACK_MATRIX.md` described `rzrz` as the tool that "drives
ritz1_selfhosted" until 2026-09-12; it never did.

Also note `rz run` is a stub — `src/main.ritz` carries a
`# TODO: Build then exec the binary` comment at that path.

## Dependencies

- `ritzlib` (`../ritz/ritzlib`)
- `python3` and the workspace `./rz` script, at runtime (see above)

## Status

**Working as a CLI front-end, not yet as a compiler driver.** It builds with all
three compiler stages and its tests pass. Making it a genuine third orchestrator
means compiling directly instead of spawning `python3 ./rz`, and accepting a
compiler selection rather than hardcoding ritz1.

## License

MIT License - see LICENSE file
