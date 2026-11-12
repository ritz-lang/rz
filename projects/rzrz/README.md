# rzrz

`rz` rewritten in Ritz — the Ritz-native port of the workspace CLI.
("rz in rz" = rzrz.) `list`, `--help` and `--version` run natively.
`build`, `test`, `run`, `clean` and `compare` delegate to `python3 ./rz`
(see below) and exit with its status (AGAST #2790). An unknown command
exits 2.

**Part of the [Ritz Ecosystem](../ritz/docs/ECOSYSTEM.md)**

## Overview

The workspace CLI at the monorepo root (`./rz`) is a Python script. `rzrz` is the
same CLI written in Ritz, so that the tool which builds the ecosystem is itself
built by the ecosystem. It is the subject of
[`docs/STACK_MATRIX.md`](../../docs/STACK_MATRIX.md), which tracks the compiler
bootstrap layering.

The project is deliberately small: two source files (`src/main.ritz`, the
commands; `src/args.ritz`, `parse_args`), one test file
(`test/test_args.ritz`, which calls `parse_args` on real argv vectors),
`test.sh`, and `ritzlib` as its only dependency.

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
./rz test rzrz          # test/test_args.ritz, then test.sh (CLI exit codes)
```

All four commands above were measured at exit 0 on 2026-09-12.

## Usage

```bash
./projects/rzrz/build/debug/rzrz --help
./projects/rzrz/build/debug/rzrz list
./projects/rzrz/build/debug/rzrz build <project>
./projects/rzrz/build/debug/rzrz test <project>      # or --all
./projects/rzrz/build/debug/rzrz run <project> -- <program args>
./projects/rzrz/build/debug/rzrz clean <project>     # or --all
./projects/rzrz/build/debug/rzrz compare tier2
```

`--help` reports:

```
rz - Unified workspace CLI for the Ritz ecosystem

Usage:
    rz build [PROJECT]          Build a project (or all with --all)
    rz test [PROJECT]           Test a project (or all with --all)
    rz run PROJECT [-- ARGS]    Build and run a project
    rz list                     List all projects in workspace
    rz clean [PROJECT]          Remove build artifacts (or all with --all)
    rz compare [TIER]           Compare ritz0 vs ritz1 on example TIER

Options:
    --all                       Apply to all projects
    --release                   Build with release profile
    --help, -h                  Show this help message
    --version, -V               Show version information

build/test/run/clean/compare run `python3 ./rz` (build, test and
run with --compiler ritz1) from the workspace root.
```

## Current limitation: it re-enters Python

`rzrz` does **not** compile anything itself. Every command but `list`,
`--help` and `--version` runs `python3 ./rz` with the child on rzrz's own
stdin/stdout/stderr, and exits with the child's status:

| rzrz                               | runs                                                |
|------------------------------------|-----------------------------------------------------|
| `build <p> [--release]`            | `./rz build <p> --compiler ritz1 [--release]`       |
| `build --all`                      | the above, once per `projects/*/ritz.toml`          |
| `test <p>` / `test --all`          | `./rz test <p>\|--all --compiler ritz1`             |
| `run <p> [--release] [-- ARGS]`    | `./rz run <p> --compiler ritz1 [--release] [-- ARGS]` |
| `clean <p>` / `clean --all`        | `./rz clean <p>\|--all`                             |
| `compare [TIER]`                   | `./rz compare [TIER]`                               |

Before #2790 `build` read the child's stdout to EOF and only then its
stderr, through pipes: a child writing more than a pipe's worth (64 KiB) to
stderr hung it. Inherited stdio can't; `test.sh` pins it with 1 MiB.

`build`, `test`, `run` and `clean` without a project (`run` takes no
`--all`) are an error and spawn nothing.

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

`test`, `run`, `clean` and `compare` used to print "Testing project: X" (and
so on) and exit 0 having done nothing; #2460 made them exit 1, and #2790
implemented them by delegation. `test.sh` pins every exit code and the exact
argv each command hands `./rz`, using a fake `./rz` in a scratch directory.

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
