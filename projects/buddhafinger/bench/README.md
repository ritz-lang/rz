# Buddhafinger benchmarks

The editor's performance workloads (AGAST #4821; docs/BUDDHAFINGER_PROPOSAL.md,
"Buffer representation and performance" and "Performance tests"). They are
kept apart from the functional tests: `make test` never runs them.

```bash
make -C projects/buddhafinger bench         # run every workload, print the results
make -C projects/buddhafinger bench-check   # the same, held to limits.txt: exit 1 on a regression
```

Both build `buddhafinger-bench` (`src/bench/`) with ritz1_selfhosted in the
release profile, then run each workload in its own process, so each peak
memory figure is that workload's own. Scratch files go in `BENCH_DIR`
(default `/tmp/buddhafinger-bench`). One workload by hand:

```bash
build/release/buddhafinger-bench long-hl /tmp/bf                     # one workload
build/release/buddhafinger-bench src /tmp/bf path/to/file.ritz       # a source file
build/release/buddhafinger-bench lines /tmp/bf --check bench/limits.txt
```

## Workloads

| Workload | File | Colors |
|---|---|---|
| `lines` | 1,000,000 short Ritz-shaped lines (~37 MB), `.txt` | off |
| `lines-hl` | the same, as `.ritz` | lexical |
| `long` | one 8 MiB line, no terminator, `.txt` | off |
| `long-hl` | the same, as `.ritz` | lexical |
| `src:<name>` | an ordinary Ritz source, copied (the original is never written) | lexical |

`make bench` runs two sources: `src/core/editor.ritz` (754 lines, a typical
module) and `projects/ritz/ritz1/src/parser_gen.ritz` (6,137 lines, the
largest Ritz file in the tree). The generated text is code-shaped, so with
colors on the lexer sees keywords, names, numbers and punctuation, not one
comment or string. The search target `needle_4821` is only at the very end.

## What is measured

**Edit-to-paint** is what one typed key costs the event loop: `handle_key`,
then `Painter.compose` (`src/core/paint.ritz`, the code `platform/linux.ritz`
paints with), then the flush. The flush goes to `/dev/null`, so the terminal
emulator's own drawing is not included. The frame is 40 x 120. Each series
reports `_p50_us`, `_p95_us` and `_max_us` (nearest-rank percentiles, in
microseconds) and `_n`, the sample count.

| Metric | What happens |
|---|---|
| `file_bytes`, `lines` | the workload's size (`lines` counts the empty line after a final newline) |
| `open_ms` | read the file and build the buffer, as `buddhafinger FILE` does |
| `first_paint_us` | the first frame after open |
| `open_rss_kb`, `peak_rss_kb` | peak resident memory (VmHWM) above the process baseline, after the first frame and at the end |
| `type_start`, `type_middle`, `type_end` | 200 characters typed in one Insert session at the start of the file, the middle of the middle line, and the end of the file |
| `split_middle`, `join_middle` | 100 Enters in the middle, then 100 Backspaces joining the lines back |
| `delete_middle`, `undo_delete`, `redo_delete` | 100 `x` in Normal mode, then 100 `u`, then 100 Ctrl-R |
| `undo_typing` | `u` undoing a 20-key Insert session, 20 times |
| `search`, `search_next` | `/needle_4821` Enter from the top (the match is at the end), 20 times; then 20 `n`, each wrapping the whole file |
| `page_down`, `line_down` | 200 Ctrl-F, then 500 `j`, from the top |
| `word_right` | on the one-line workloads, 500 `w` from the start instead of `j` |
| `jump_end`, `jump_start` | `G` and `gg` (or `$` and `0` on one line), 20 times each |
| `resize` | the terminal size toggled between 40 x 120 and 50 x 200, 20 times: a full layout and repaint |
| `save_ms` | `:w` through `LinuxFiles` (temp file, fsync, rename, directory fsync) |

Every run starts with `# kernel`, `# cpu` and `# memory` lines naming the
machine. RESULTS.md has the recorded baselines, the representation decision
and how limits.txt was set.

## Regression limits

`limits.txt` has one `<workload> <metric> <max>` per line. `--check` fails
the run when a result is above its limit. The limits come from repeated
runs on the RESULTS.md machine; on a slower host, re-baseline as RESULTS.md
describes rather than loosening one line at a time.
