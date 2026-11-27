# Buddhafinger benchmark results

Baselines for the workloads in [README.md](README.md) (AGAST #4821), the line
representation decision they support, and how [limits.txt](limits.txt) was
set. Re-run with `make -C projects/buddhafinger bench`.

## Environment

| | |
|---|---|
| Date | 2026-11-27 |
| Host | huburght: AMD Ryzen 5 5600GT, 12 logical CPUs, 48 GB |
| OS | Linux 6.6.87.2-microsoft-standard-WSL2 (WSL 2) |
| Build | `buddhafinger-bench`, ritz1_selfhosted, release profile (each module `clang -O2`) |
| Source | base 533510720350 plus #4821's change |
| Load | a shared host: other rooms' builds ran beside the benchmark at a higher CPU weight |
| Frame | 40 x 120 cells, flushed to `/dev/null` |

Each workload ran three times, each in a fresh process. The tables give the
**median of the three runs**. Timings varied up to about 3x between runs
(the shared host); memory varied by under 3%.

## Open, save, memory

| | lines | lines-hl | long | long-hl | src:editor.ritz | src:parser_gen.ritz |
|---|---|---|---|---|---|---|
| file | 36.9 MB | 36.9 MB | 8.4 MB | 8.4 MB | 28 kB | 234 kB |
| open | 238 ms | 248 ms | 51 ms | 48 ms | 0 ms | 2 ms |
| first paint | 121 µs | 183 µs | 149 µs | 244.1 ms | 137 µs | 200 µs |
| peak memory | 153 MiB | 177 MiB | 32 MiB | 52 MiB | 3.9 MiB | 5.0 MiB |
| save | 80 ms | 93 ms | 8 ms | 7 ms | 0 ms | 0 ms |

## Edit-to-paint latency, p50 / p95

The proposal's initial Linux target for steady typing and scrolling is one
60 Hz frame, about 17 ms. **✗** marks a p95 over it.

| | lines | lines-hl | long | long-hl | src:editor.ritz | src:parser_gen.ritz |
|---|---|---|---|---|---|---|
| `type_start` | 67 µs / 79 µs | 111 µs / 165 µs | 920 µs / 1.1 ms | 179.1 ms / 207.3 ms **✗** | 82 µs / 103 µs | 86 µs / 152 µs |
| `type_middle` | 68 µs / 91 µs | 1.4 ms / 1.7 ms | 36.5 ms / 42.4 ms **✗** | 211.2 ms / 240.8 ms **✗** | 124 µs / 146 µs | 105 µs / 139 µs |
| `type_end` | 102 µs / 118 µs | 3.0 ms / 3.6 ms | 70.3 ms / 84.1 ms **✗** | 259.1 ms / 408.1 ms **✗** | 86 µs / 136 µs | 103 µs / 166 µs |
| `split_middle` | 2.9 ms / 4.4 ms | 4.3 ms / 4.9 ms | 37.3 ms / 45.7 ms **✗** | 143.8 ms / 253.6 ms **✗** | 72 µs / 131 µs | 84 µs / 155 µs |
| `join_middle` | 2.8 ms / 3.3 ms | 4.3 ms / 5.1 ms | 36.7 ms / 45.6 ms **✗** | 123.1 ms / 149.3 ms **✗** | 103 µs / 127 µs | 126 µs / 190 µs |
| `delete_middle` | 71 µs / 85 µs | 1.4 ms / 1.6 ms | 84.5 ms / 92.4 ms **✗** | 191.2 ms / 270.8 ms **✗** | 100 µs / 122 µs | 151 µs / 187 µs |
| `undo_delete` | 71 µs / 83 µs | 1.4 ms / 1.6 ms | 152.7 ms / 188.8 ms **✗** | 232.3 ms / 254.6 ms **✗** | 100 µs / 128 µs | 108 µs / 134 µs |
| `redo_delete` | 71 µs / 82 µs | 1.4 ms / 1.6 ms | 140.8 ms / 153.5 ms **✗** | 235.2 ms / 262.0 ms **✗** | 100 µs / 130 µs | 109 µs / 143 µs |
| `undo_typing` | 71 µs / 122 µs | 1.5 ms / 2.2 ms | 102.2 ms / 152.3 ms **✗** | 234.6 ms / 360.9 ms **✗** | 102 µs / 149 µs | 109 µs / 124 µs |
| `search` | 25.1 ms / 41.7 ms **✗** | 29.1 ms / 48.5 ms **✗** | 17.3 ms / 21.8 ms **✗** | 11.9 ms / 12.9 ms | 103 µs / 164 µs | 262 µs / 341 µs |
| `search_next` | 25.1 ms / 35.2 ms **✗** | 25.4 ms / 49.9 ms **✗** | 16.1 ms / 19.7 ms **✗** | 12.2 ms / 18.8 ms **✗** | 101 µs / 114 µs | 255 µs / 359 µs |
| `page_down` | 73 µs / 91 µs | 151 µs / 189 µs | 55 µs / 83 µs | 53 µs / 65 µs | 52 µs / 112 µs | 117 µs / 161 µs |
| `line_down` | 72 µs / 96 µs | 97 µs / 133 µs | — | — | 97 µs / 152 µs | 88 µs / 110 µs |
| `word_right` | — | — | 92 µs / 134 µs | 79 µs / 107 µs | — | — |
| `jump_end` | 79 µs / 109 µs | 104 µs / 117 µs | 74.3 ms / 79.8 ms **✗** | 64.8 ms / 71.7 ms **✗** | 98 µs / 120 µs | 98 µs / 109 µs |
| `jump_start` | 76 µs / 86 µs | 100 µs / 119 µs | 62 µs / 81 µs | 55 µs / 77 µs | 102 µs / 122 µs | 91 µs / 118 µs |
| `resize` | 303 µs / 536 µs | 347 µs / 580 µs | 288 µs / 591 µs | 534 µs / 732 µs | 265 µs / 451 µs | 249 µs / 468 µs |

## Decision: the line representation stays `Vec<Vec<u8>>`

Neither bounded fragments for long lines nor indexed line blocks: the
numbers don't call for either. Both stay options behind the buffer API.

**Fragments: no.** The proposal adopts them "if long-line measurements show
suffix movement dominates". It doesn't. `long`'s `type_start` moves the
whole 8 MiB suffix of the line on every key and costs 0.9 ms p50 / 1.1 ms
p95, 15x under the frame. The costly long-line cases grow with the cursor's
column, not with the bytes an edit moves: `type_end` (70 ms) moves nothing
and costs twice `type_middle` (37 ms). `jump_end` (`$`, no edit at all)
costs 74 ms. These costs come from work above the storage, which fragments
would not remove:

1. `Painter.compose` drops every line's byte-to-cell checkpoints on any text
   change (`text_changed(0, 0)`), so the cursor's cell is scanned again from
   byte 0 each frame. It should invalidate from the edited line and byte,
   which needs the buffer to report where its last edit was.
2. `Editor.place` scans the line from its start twice per move:
   `normal_col` (the code point holding a byte, which needs at most 3 steps
   back from the byte) and `units_before` (the `want` column for `j`/`k`).
3. Undo and redo go through `Buffer.replace_bytes`, which rebuilds and
   re-parses every line the range touches: the whole 8 MiB line, twice
   copied, per `u` (150 ms). An undo inside one line can splice in place,
   as `replace` already does for a forward edit.
4. With colors on, the highlighter lexes a whole line to color the visible
   part of it: 180-400 ms per frame on the 8 MiB line. Lexing stops being
   per-line-whole once lexer state is checkpointed along a long line, as
   the screen's cell checkpoints are.

Linear suffix movement reaches one frame at roughly 120 MiB per line on
this machine. Revisit fragments if a real workload has lines that long, or
if `long`'s `type_start` p95 passes 17 ms once 1-4 are fixed.

**Indexed line blocks: no.** The proposal adopts them "if shifting many line
entries or allocating once per line dominates on large files". With a
million lines, steady typing and scrolling stay under 0.2 ms. Splitting or
joining a line in the middle shifts about 500,000 entries in 2.9 ms p50,
4.4 ms p95, a quarter of the frame. Linear in the line count, that reaches
17 ms at about 4 million lines. Open is 238 ms and save 80 ms for 37 MB.
The cost is memory: 153 MiB for a 37 MB file, about 120 bytes per line
beyond the text (the line's `Vec` header and terminator, one heap
allocation per line, the line-start cache). Revisit blocks if multi-million
line files matter or that memory does. Highlighting adds a separate per-line
cost (`lines-hl` `type_end` 3.0 ms at line 1,000,000): the highlighter's
cache is a dense vector from line 0 and is rebuilt every frame after an
edit. That is the highlighter's to fix (report edits through
`lines_changed` instead of resetting), not the buffer's.

**Search** is a one-shot command, not steady typing. A literal search over
37 MB takes 25 ms p50 (a byte-at-a-time naive match), and 12-17 ms through
one 8 MiB line. It's fine for M1; a faster matcher comes with M6's regex
search.

**Ordinary sources** stay under 0.5 ms p95 on every operation, over 30x
under the frame, with colors on.

The over-target long-line costs above are recorded here and on epic #4782.
None of them changes the representation.

## A memory leak the first runs found

The first highlighted runs grew to 3.3 GB resident and went into swap.
`Painter.compose` replaced its highlighter with `self.styler =
highlighter_new()` every frame. Under ritz1 a store through a `self: @&T`
receiver doesn't drop the old value (ritz0 does; AGAST #4905), so every
frame leaked the last frame's color runs. `compose` now calls
`Highlighter.reset()`, which clears in place (since #4828, through
`Marked.text_changed`, which had made the same store). Other `self.f = v` stores in
the package (`Screen.resize`'s grids, `Editor.replace_buffer`'s buffer,
`Highlighter.compact` and `lines_changed`) leak until #4905 lands. None is
on this benchmark's hot path: `peak_rss_kb` holds steady across runs.

## How limits.txt was set

From the three runs above, per workload and metric:

- latency p95s and `first_paint_us`: 2x the worst run, at least 1000 µs
  (below a millisecond these numbers are scheduler noise on a shared host)
- `open_ms`, `save_ms`: 2x the worst run, at least 10 ms
- `open_rss_kb`, `peak_rss_kb`: 1.25x the worst run, rounded up to a MiB

A limit catches a change that makes an operation about twice as slow as its
worst baseline run. The over-target long-line rows are limited too, as
they stand, so they can only improve. When one improves (fixes 1-4 above),
re-baseline its workload: run `make bench` three times on a quiet machine,
apply the rules above, and update this file's tables with the new medians.
