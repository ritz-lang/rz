# Buddhafinger editor proposal

**Status** Draft for review

Buddhafinger is a terminal code editor written in Ritz for Linux and Harland.
Start with a Linux editing loop, bring the same editor core up on Harland, and
package it for Indium once the Harland console and filesystem paths pass the
editor's acceptance tests. Use Vim-style modal editing and build Ritz language
support around lexical highlighting and ritz-lsp.

## Editing experience

- **First usable release.** Open, create, edit, save, and reopen files. Provide
  Normal, Insert, Visual, and command-line modes, with Vim-style motions,
  counts, operators, cut/copy/paste, and grouped undo and redo. Include
  forward/backward search, go to line, and guarded quit when edits are pending.
  Support multiple open buffers, a line-number gutter, horizontal and vertical
  scrolling, a status line, and a command and message area. Use horizontal
  scrolling as the initial default for source files.
- **Everyday code editing.** Add split views, file and buffer pickers, workspace
  search and quickfix navigation, substitution, named registers, block
  selections, repeat and macros, configurable mappings, autoindent, bracket
  matching, soft wrap, relative line numbers, themes, and recovery after an
  interrupted session. Share undo history across views of the same buffer.
- **Ritz language tools.** Show syntax colors during ordinary editing, overlay
  diagnostic spans and messages, and provide hover, go to definition, and
  jump back. Add semantic highlighting and completion when ritz-lsp advertises
  those capabilities.

## Ritz and platform boundaries

Keep buffer edits, undo, modes, commands, and screen layout independent of
terminal and OS I/O. Convert input to typed key, paste, resize, and timer events.
Render to a grid of styled cells, then emit changes to the visible terminal
frame. Treat buffer contents as display data and visibly escape control bytes so
opening a file cannot emit terminal commands.

Use ritzlib's `String` for owned text, `StrView` for borrowed text, `Vec<T>`
for growable storage, and `Span<T>` for bounded views. Model modes, events, and
errors with enums and `Result`. Use ritzlib file, I/O, terminal, process, and
JSON primitives where the target supplies them. Add missing reusable operations
to ritzlib with focused tests. Keep raw pointers and NUL-terminated strings at
ABI boundaries that require them. Review the implementation against
[Ritz, Not C](../projects/ritz/docs/RITZ_NOT_C.md),
[Review](../projects/ritz/docs/REVIEW.md), and
[Standard](../projects/ritz/docs/STANDARD.md).

On Linux, use ritzlib's terminal attribute and window-size operations. On
Harland, use the existing console attribute ABI through a library adapter and
exercise it under QEMU. Verify raw input, escape sequences, viewport sizing,
file open and save, and terminal restoration on each target. Probe capabilities
such as alternate screen, bracketed paste, color, and resize. Allow a
configurable viewport where size reporting is unavailable. Restore terminal
mode on normal exit and handled errors or interruptions. Use the existing
Indium shell image as the port's test environment, then package the editor as
an Indium userspace program. [Terminal library](../projects/ritzlib/term.ritz) ·
[Indium shell image](../projects/indium/README.md)

Preserve line endings, final newline state, and untouched bytes on round trips.
Save via a same-directory temporary file and atomic replacement where supported,
preserving permissions and checking for external changes. Keep the buffer dirty
if a write fails. Establish the save contract on Harland's filesystem before
claiming parity.

## Buffer representation and performance

Start with a growable `Vec<String>` of logical lines. A `Span<String>` works
as a temporary view when a caller needs a range of lines. Direct indexing makes
line lookup constant time, while inserting or removing a line shifts the
following entries, and mid-line edits to a contiguous string move its suffix.
Use line-local edit transactions so normal typing and undo avoid copying the
whole file. Store line terminators with line metadata and stream line slices to
disk. Use a buffer API for reading slices, replacing ranges, and walking lines
so the editor stays independent of their storage.

Use byte offsets for storage, grapheme boundaries for cursor movement, and
display cells for layout. Tabs, combining marks, and wide glyphs affect screen
columns. Keep UTF-16 conversion at the ritz-lsp boundary. Preserve malformed
UTF-8 on disk and display it with a defined replacement or escape policy.
Render only the viewport. For long lines, maintain bounded, lazy byte-to-cell
checkpoints so steady scrolling and cursor movement can reuse prior work.
Invalidate checkpoints from the affected edit onward. This still leaves an
initial scan cost when jumping far into an uncached line.

If long-line measurements show suffix movement dominates, compare the
contiguous representation with bounded owned string fragments in a
`Vec<String>` for individual long lines. Split and merge neighboring fragments
to keep repeated local edits from creating one allocation per keystroke.
Measure fragment lookup and shifting as well as copying. Consider pooled
storage only if allocation costs justify tracking pool lifetime and reclamation
across undo history and discarded edits. If shifting many line entries or
allocating once per line dominates on large files, evaluate indexed blocks of
lines with aggregate line counts. Keep both decisions behind the buffer API.

Benchmark a million short lines, a single multi-megabyte line, and ordinary
source files. Measure open and save time, peak memory, edits at the start,
middle, and end, undo, search, scrolling, and resize. Run long-line and
many-line cases with highlighting and language tools enabled where supported.
Record p50 and p95 edit-to-paint latency and the measurement environment.
Use one 60 Hz frame (about 17 ms) as an initial Linux target for steady typing
and scrolling after load. Measure Harland independently before setting its
latency target. Use the results to choose a representation and regression
thresholds.

## Ritz syntax and language server

Use a lightweight, incremental Ritz lexer for immediate syntax colors and
invalidate from the edited line until the outgoing lexical state stabilizes.
Share lexical rules with existing Ritz tooling where practical. Apply semantic
tokens as an overlay when the server advertises them. The current server uses
stdio JSON-RPC, full-text document sync, and UTF-16 positions. It exposes
diagnostics, function hover, and function definition. The Vim syntax installer
supplies lexical rules outside the server. [Server README](../projects/ritz-lsp/README.md) ·
[Server capabilities](../projects/ritz-lsp/src/server.ritz)

Run the server as a background process and handle framed messages outside the
editing loop. Coalesce rapid changes and bound queued full-text snapshots.
Associate requests with buffer revisions, discard outdated responses, and
suppress stale diagnostics during edits. For unversioned diagnostics, keep at
most one diagnostic-producing update in flight per document and display results
only while the corresponding revision is current. Use a timeout and report
server failures in the status area. Selectively suspend sync above a measured
document size while keeping navigation and lexical colors available. Start
the real server on Linux with `RITZ1` pointing to `ritz1_selfhosted` for
diagnostics. Enable the Harland server integration once subprocess pipes and
a runnable diagnostic compiler are available there. Local editing and lexical
colors work with either platform adapter.

## Tests and build isolation

Use a dedicated Buddhafinger test entry point and CI job. Build the editor,
Ritz test binaries, and the real server used by editor tests with
`ritz1_selfhosted` only. Pass the compiler explicitly at every build entry
point and set `RITZ1` explicitly for real-server tests. Use one compiler
artifact for Linux and Harland targets. Compiler bootstrap remains an upstream
toolchain dependency. Keep Buddhafinger out of the compiler regression
suites and generic workspace multi-compiler build and test sweeps, including
implicit discovery when the package is registered. Verify the sweep excludes
the editor and the dedicated job actually runs its suite.
[Workspace CLI](../rz) · [Compiler test targets](../projects/ritz/Makefile) ·
[CI workflows](../.github/workflows/main.yml)

- **Buffer and command tests.** Use ritzunit for edit ranges, split/join,
  undo/redo, modes, search, and line endings. Run deterministic randomized edits
  against a simple reference buffer and keep seeds for reproducing failures.
  Cover long files, long lines, mixed line endings, malformed UTF-8, and the
  byte/grapheme/cell/UTF-16 boundaries.
- **Screen and I/O tests.** Assert cell grids for gutters, clipping, tabs, wide
  glyphs, selections, diagnostics, and resize. Drive a Linux PTY through open,
  edit, save, and exit, including interrupted sessions and terminal restoration.
  Inject short writes, storage exhaustion, and concurrent file changes.
- **Language tests.** Use a scripted server for partial frames, rapid edits,
  delayed replies, stale results, capability negotiation, and server exit.
  Smoke-test the real ritz-lsp with a Ritz file that produces a diagnostic and
  supports hover and definition lookup.
- **Harland acceptance.** Launch the self-hosted-compiler build from the QEMU
  console, edit and save a writable file, reopen it, and verify both the saved
  bytes and the shell's terminal state after exit. Repeat against the packaged
  Indium image when distribution integration lands.
- **Performance tests.** Track the buffer workloads separately from functional
  tests. Set regression limits after collecting repeatable baseline results.

## Decisions for review

1. Approve modal editing as the default and confirm the initial Vim command
   subset before defining keybinding compatibility.
2. Approve a vector of owned lines as the first implementation and use benchmark
   results to decide when to adopt fragments or indexed line blocks.
3. Confirm the Harland console and save semantics required for the first port,
   and the separate milestone for running ritz-lsp on Harland.
