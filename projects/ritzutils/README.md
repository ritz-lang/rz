# ritzutils

Coreutils-style command-line utilities written in Ritz, targeting the Harland
microkernel via the Indium distribution.

**Part of the [Ritz Ecosystem](../ritz/docs/ECOSYSTEM.md)**

## Overview

ritzutils holds standalone utility binaries intended to work in shell pipelines
under Harland. Each utility is declared as its own `[[bin]]` in `ritz.toml` and
built as a freestanding, position-independent executable that links the Harland
runtime.

It is deliberately separate from `projects/indium`: indium owns the init system,
bootable images and the distribution-specific test programs, while ritzutils
holds general-purpose userspace tools.

## Contents

Right now there is exactly **one** utility:

| Program | Source | Output |
|---------|--------|--------|
| `cat` | `src/cat.ritz` | `build/debug/cat.elf` |

More are expected; `projects/indium` currently carries its own `echo`, `wc`,
`seq10`, `true` and `false`, which are the natural candidates to migrate here.

## Build

```bash
# From the monorepo root. `rz` sets RITZ_PATH itself.
./rz build ritzutils
# Produces projects/ritzutils/build/debug/cat.elf

./rz test ritzutils
```

Both measured at exit 0 on 2026-09-12. `rz test` reports
`⚠ No tests found, skipping` — there are no tests in this project yet, and it
exits 0 regardless. Do not read that as a passing suite.

**`./rz run ritzutils` does not work** (exit 1,
`Error: Could not find binary for 'ritzutils'`). `rz run` looks for a binary
named after the project, and this project's `[[bin]]` is `cat`. There would be
nothing to run on Linux anyway — see Target below.

## Target

`cat` is built for Harland, not Linux:

```toml
target = "x86_64-unknown-none"
target_os = "harland"
freestanding = true
link_runtime = true
```

It links with `../indium/user/linker_pie.ld` as a position-independent
executable. Running `cat.elf` on the Linux host is not supported; it is meant to
be included in a Harland image and invoked from `rzsh`.

## Dependencies

- `ritzlib` (via the compiler's `RITZ_PATH`)
- `projects/indium` — for the PIE linker script and the Harland runtime objects

## Status

**Early.** One utility, no tests. The build is green.

## License

MIT License - see LICENSE file
