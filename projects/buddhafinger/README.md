# Buddhafinger

A modal (Vim-style) terminal code editor written in Ritz, for Linux first and
then Harland. [`docs/BUDDHAFINGER_PROPOSAL.md`](../../docs/BUDDHAFINGER_PROPOSAL.md)
is the design and AGAST epic #4782 tracks the work. The core (buffer,
screen, modes and the first-release commands), the Linux save, the Linux
event loop, lexical colors and the ritz-lsp client are in: `buddhafinger
[FILE]` edits FILE on the terminal on stdin.
On Harland, `buddhafinger [--rows N] [--cols N] [FILE]` edits it on the
serial console (AGAST #4833).

## Language server

A `.ritz` file starts ritz-lsp as a child process, with `RITZ1` pointing at
`ritz1_selfhosted`. Which server: `$BUDDHAFINGER_LSP` if set (empty turns
it off), else the monorepo's `projects/ritz-lsp/build/debug/ritz-lsp`
beside this editor, else `ritz-lsp` on `$PATH`; `RITZ1` is `$RITZ1`, else
the monorepo's `ritz1_selfhosted`, else the one on `$PATH`.

- Diagnostics come on their own after each change (the editor sends no
  request for them) and show underlined, errors in red, only while they are
  for the text on screen; the cursor line's message shows on the message
  line.
- `K` shows hover on the message line; `gd` goes to the definition, in this
  file or another; `Ctrl-O` or `Ctrl-T` goes back.
- Files over 1 MiB are not synced (`lsp: off (large file)`): colors and
  editing are unaffected.
- When the server fails or exits the status line says so (`lsp: exited
  (status 1)`) and editing goes on.

## Layout

- `src/core/`: the editor core (`buffer` with its undo `history` and
  `utf8` cursor stepping, `screen`, `modes`, `commands`, `editor`, which
  applies typed keys to the editor state, and `paint`, which composes one
  frame of it for the terminal). It does no terminal or OS
  I/O, so it is tested without a terminal: files go through the
  `FileStore` seam in `files`, which the platform implements.
- `src/syntax/`: lexical colors. `lexer` splits one line into tokens (no
  state crosses a line in Ritz); `highlight` caches each line's colored runs
  for the screen, and an edit re-lexes only the lines it touched.
  `test_lexer.ritz` fails when ritz1's keyword table and the lexer's drift.
  `marks` draws diagnostics over those colors.
- `src/lsp/`: the language client, no I/O: `wire` (UTF-16 columns, JSON-RPC
  frames, the outbox that keeps a partly written frame and coalesces
  full-text changes that haven't started) and `client` (initialize and
  capabilities, sync by revision, hover and definition tied to revisions,
  timeouts, version-matched diagnostics).
- `src/platform/`: the platform adapters that do that I/O: `linux` (the
  terminal session and event loop: raw mode on the alternate screen, one
  `poll` on the terminal and a signalfd with the Escape timeout as its
  deadline, Ctrl-Z/SIGTSTP suspend, SIGCONT resume, SIGWINCH resize,
  SIGTERM/SIGINT/SIGHUP exit, the terminal restored on every way out) and
  `save` (`LinuxFiles`, the Linux `core/files` `FileStore`: temp file, fsync,
  rename, directory fsync, permissions kept, external-change check),
  `lsp` (ritz-lsp on nonblocking pipes in the same poll, a bounded amount of
  pipe work per loop turn, a bounded stderr log, EOF and EPIPE ending the
  session),
  `harland` (the console session: termsession's raw mode, a `--rows` x
  `--cols` viewport since Harland reports no window size, KeyReader's timed
  console read for the Escape timeout, input overruns reported) and
  `harland_save` (`HarlandFiles`: the whole file in one write, the close
  checked, and for `/var` a `sync` too; a failure keeps the buffer dirty).
- `src/main.ritz`: the `buddhafinger` binary, `platform/linux`'s `run_editor`
  on stdin. `src/main_harland.ritz`: the Harland one
  (`build/debug/buddhafinger.harland.elf`), `platform/harland` only.
- `src/bench/`: `buddhafinger-bench`, the performance workloads (a million
  short lines, one 8 MiB line, ordinary Ritz sources). `bench/` holds their
  regression limits and the recorded results; `bench/README.md` says how to
  run them.
- `test/`: the ritzunit suites. `test_buffer_fuzz.ritz` runs seeded random
  edits against a reference buffer; a failure prints its seed, and
  `BF_FUZZ_SEED=<seed> make -C projects/buddhafinger test` replays it alone.
  `test_lsp_wire.ritz` and `test_lsp_client.ritz` drive the language client
  with scripted messages; `test_lsp_server.ritz` runs it against scripted
  servers (`test/fake_lsp/*.sh`) on real pipes, a stalled one flooding its
  stderr included; `test_lsp_editor.ritz` runs the editor with a scripted
  server and with the real ritz-lsp on a pty (the latter skipped, saying
  so, where ritz-lsp isn't built).
  `test_terminal.ritz` runs the editor on a pty: open, edit, save and exit,
  a bare Escape, Ctrl-Z and SIGTSTP then SIGCONT, SIGTERM/SIGINT/SIGHUP and
  a resize, comparing the terminal's attributes before and after each.
  `test_harland_save.ritz` runs the Harland save's every step and failure
  against a scripted kernel.
- `tools/test_harland_console.sh`: the Harland acceptance test. It boots the
  shell image with the editor under QEMU (KVM where it works) six times on
  one storage disk and drives it over the serial console
  (`tools/harland_console.py`): edit, bare Escape, save, reopen, the shell's
  terminal state, an empty save, kills before and after the save's write,
  reboots, the `fault-persist` and `fault-sync` boot options, and a boot
  with no storage device.

## Build and test

```bash
make -C projects/buddhafinger test            # the suites, then the QEMU test
make -C projects/buddhafinger harland-test    # the QEMU test alone
```

The editor builds and tests with `ritz1_selfhosted` only, and the Makefile
passes it to every `rz` call (`rz`'s default is ritz0). rz.toml's
`[workspace.exclude]` keeps the package out of the `rz build --all` /
`rz test --all` sweeps, and CI runs the command above instead.
`projects/ritz/tools/test_buddhafinger_isolation.py` checks both.

## Benchmarks

```bash
make -C projects/buddhafinger bench         # the workloads, results printed
make -C projects/buddhafinger bench-check   # held to bench/limits.txt
```

`bench/README.md` describes the workloads and metrics; `bench/RESULTS.md`
has the baselines and the line representation decision they support.
