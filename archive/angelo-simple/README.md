# angelo-simple

A minimal render smoke test for [Angelo](../angelo), the Ritz font-rendering
library.

**Part of the [Ritz Ecosystem](../ritz/docs/ECOSYSTEM.md)**

## Overview

This is the smallest thing that proves the rasterisation path works end to end:
it builds a 50×50 greyscale gradient in a `Vec<u8>`, writes it out as a binary
PGM (P5) file, and exits. It exercises `ritzlib.gvec`, `ritzlib.strview` and raw
`sys_open`/`sys_write`/`sys_close` with no external dependencies.

It lives as its own project rather than inside `projects/angelo` so that it can be
built and run on the Linux host in isolation, without pulling in Angelo's font
parsing or Prism's framebuffer.

## Contents

| File | Purpose |
|------|---------|
| `src/main.ritz` | The whole program (~50 lines) |
| `ritz.toml` | Declares one `[[bin]]` named `simple-render` |

## Build and run

```bash
# From the monorepo root. `rz` sets RITZ_PATH itself.
./rz build angelo-simple
# Produces projects/angelo-simple/build/debug/simple-render
```

**Do not use `./rz run angelo-simple`** — it builds, then fails with
`Error: Could not find binary for 'angelo-simple'` and exits 1. `rz run` looks
for a binary named after the *project*, and this project's `[[bin]]` is named
`simple-render`. (The `# Run: ./rz run angelo-simple` comment at the top of
`src/main.ritz` is wrong for the same reason.) Invoke the binary directly.

It writes `test_output.pgm` into the **current working directory**, so `cd`
somewhere writable first:

```bash
cd /tmp && /path/to/rz/projects/angelo-simple/build/debug/simple-render
# Angelo Minimal Render Test
# Wrote test_output.pgm successfully!
# View with: feh test_output.pgm
```

Measured 2026-09-12: build exit 0, run exit 0, 2513-byte PGM produced.

View the output with any PGM-capable viewer (`feh`, `display`, GIMP).

## Tests

There are none. `./rz test angelo-simple` exits 0 printing
`⚠ No tests found, skipping` — that is not a passing suite.

## Dependencies

- `ritzlib` (via the compiler's `RITZ_PATH`)

## Status

**Working.** It does the one thing it exists to do.

## License

MIT License - see LICENSE file
