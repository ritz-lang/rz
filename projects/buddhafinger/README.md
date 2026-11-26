# Buddhafinger

A modal (Vim-style) terminal code editor written in Ritz, for Linux first and
then Harland. [`docs/BUDDHAFINGER_PROPOSAL.md`](../../docs/BUDDHAFINGER_PROPOSAL.md)
is the design and AGAST epic #4782 tracks the work. This is the skeleton:
the modules exist, the editor does not yet.

## Layout

- `src/core/`: the editor core (`buffer` with its undo `history` and
  `utf8` cursor stepping, `screen`, `modes`, `commands`). It does no
  terminal or OS I/O, so it is tested without a terminal.
- `src/syntax/`: lexical colors. `lexer` splits one line into tokens (no
  state crosses a line in Ritz); `highlight` caches each line's colored runs
  for the screen, and an edit re-lexes only the lines it touched.
  `test_lexer.ritz` fails when ritz1's keyword table and the lexer's drift.
- `src/platform/`: the platform adapters that do that I/O (`linux` so far).
- `src/main.ritz`: the `buddhafinger` binary.
- `test/`: the ritzunit suites. `test_buffer_fuzz.ritz` runs seeded random
  edits against a reference buffer; a failure prints its seed, and
  `BF_FUZZ_SEED=<seed> make -C projects/buddhafinger test` replays it alone.

## Build and test

```bash
make -C projects/buddhafinger test
```

The editor builds and tests with `ritz1_selfhosted` only, and the Makefile
passes it to every `rz` call (`rz`'s default is ritz0). rz.toml's
`[workspace.exclude]` keeps the package out of the `rz build --all` /
`rz test --all` sweeps, and CI runs the command above instead.
`projects/ritz/tools/test_buddhafinger_isolation.py` checks both.
