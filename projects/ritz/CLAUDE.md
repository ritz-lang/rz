# Ritz Language

Systems programming language compiling to LLVM IR. No libc - direct Linux syscalls.

## Status

Three compilers are in play: **ritz0** (Python bootstrap), **ritz1** (written in
Ritz, built by ritz0), and **ritz1_selfhosted** (ritz1 compiled by itself). The
bootstrap closes — the regression suite's last stage asserts ritz1 and
ritz1_selfhosted accept an identical set of programs.

For current numbers, run the gate rather than reading a table:

```bash
make -C projects/ritz ci-local      # everything CI runs, in CI's order
```

A hardcoded status table lived here until 2026-09-12 claiming "33/33" for each
compiler, 34 ritzlib modules and "75+" examples, under a heading dated five months
earlier. Every figure had drifted. Counts belong in command output; work status
belongs in AGAST.

## Quick Start

```bash
# Build an example — build.py takes a PATH to the package, not a bare name.
# `build.py build 21_ls` answers "Package '21_ls' not found"; the bare-name
# form documented here until 2026-09-09 never worked.
python3 build.py build examples/tier3_coreutils/21_ls

# ritzlib imports resolve via RITZ_PATH. Without it, every example that
# imports ritzlib fails with "Cannot find module: ritzlib.io" — which reads
# like a broken package rather than a missing environment variable.
RITZ_PATH=$PWD python3 build.py build examples/tier1_basics/03_echo

# Pre-commit validation (incremental ritz1, 30-60s)
make matrix

# Pre-push validation (full bootstrap + matrix, ~1m 40s)
make matrix-full

# All tests, all examples (slow)
make test
```

**Read `docs/VALIDATION.md` before running clean rebuilds.** The hard rule is:
never `make clean` to "make sure it works" — Make's incremental rebuild is
correct; if it isn't, that's a Makefile bug to fix, not paper over. A previous
session burned 100 minutes on redundant full bootstraps.

## Directory Structure

```
ritz/
├── ritz0/           # Bootstrap compiler (Python)
├── ritz1/           # Self-hosted compiler (Ritz)
├── ritzlib/         # Standard library
├── examples/        # Example programs
├── build.py         # Build system
└── Makefile
```

## Key Syntax

```ritz
import ritzlib.sys
import ritzlib.io

fn main() -> i32
    print(c"Hello, world!\n")
    0
```

**String literals:**
- `"hello"` → `StrView` (a `{ ptr, len }` pair; no allocation)
- `c"hello"` → `*u8` (NUL-terminated C string)

`s"hello"` was removed by AGAST #98: bare `"..."` now produces a `StrView` of
the same `{ ptr, len }` shape, so the prefix was redundant. `make
check-no-s-strings` fails the build if one reappears.

**Testing:**
```ritz
[[test]]
fn test_add() -> i32
    assert 2 + 3 == 5
    0
```

See `docs/TESTING.md` for the canonical fork+exec integration-test template
and the four harness gotchas (read-until-EOF, temp-file stdin, etc.).

## Principles

1. **No concessions** - Missing feature? Implement it in the language.
2. **No libc** - Direct syscalls only.
3. **Test-driven** - Write tests, then implement.

## Documentation

**Normative and compile-gated.** Every fenced ` ```ritz ` block in these four is
compiled by `make check-doc-examples` on every build, so their examples cannot
drift from the compiler. Membership in that gate is the only thing that has
actually prevented doc rot here — docs inside it are accurate, docs outside it
have not been:

- `docs/LANGUAGE_SPEC.md` - **the language standard. Start here.**
- `docs/STDLIB_REFERENCE.md` - ritzlib reference
- `docs/STYLE.md` - style guide
- `docs/ECOSYSTEM.md` - ecosystem overview

These four moved here from `projects/larb/docs/` on 2026-09-03 (AGAST #1311):
living outside `projects/ritz` is why they went seven months without a migration
pass.

**Guides** (prose, not gated — treat specifics with more suspicion):

- `docs/ROADMAP.md` - the plan, and which command answers which question
- `docs/EXAMPLES.md` - example program guide
- `docs/TESTING.md` - test system documentation
- `docs/VALIDATION.md` - **validation workflow & build cadence** (read this!)

**Work tracking lives in AGAST**, the external task tracker — not in this repo.
Per-project `TODO.md` / `DONE.md` files were deleted on 2026-09-12 after going
seven months stale; git retains them. Do not recreate them. `docs/archive/` holds
historical session logs and superseded status reports, and is not authoritative —
see `docs/archive/README.md`.
