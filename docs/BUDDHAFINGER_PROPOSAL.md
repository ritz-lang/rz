# Buddhafinger editor proposal

**Status** Draft for review.

Buddhafinger is a terminal code editor written in Ritz for Linux and Harland.
Spec and build the Linux editor first. Build the Harland kernel and ritzlib
support it needs in parallel (see [Harland prerequisites](#harland-prerequisites)),
then bring the same editor core up on Harland and package it for Indium once
the Harland console and filesystem paths pass the editor's acceptance tests.
Use Vim-style modal editing and build Ritz language support around lexical
highlighting and ritz-lsp.

## Scope

Buddhafinger is a terminal program. On Linux it talks to the tty. On Harland
and Indium it runs in the serial console, the same place rzsh does, and the
host terminal interprets its escape sequences. Adding it to
`projects/indium/initramfs.pkgs` makes it a program started from that shell.
It does not draw a window.

The editor keeps a grid of styled cells, and a platform adapter emits the
changes. This proposal's adapter writes terminal sequences. A Prism terminal
emulator that interprets those sequences would be a later, separate program.
Harland's framebuffer is a pixel map Prism uses, not a text console, and this
editor does not target it.

## Editing experience

### First usable release

One buffer, Normal and Insert modes, save, and quit. This slice puts the
Linux terminal, signal, and save adapters under test as early as possible.
It does not make the Harland port sooner on its own: Insert mode needs the
timed console read listed under the prerequisites (see
[Escape and key timeouts](#escape-and-key-timeouts)).

The command list for this release, fixed before implementation:

| Group | Commands |
|---|---|
| Motion | `h` `j` `k` `l`, arrow keys, `w` `b` `e`, `0` `$`, `gg` `G`, Ctrl-F Ctrl-B (page) |
| Insert | `i` `a` `o` `O`, Escape to leave, Backspace, Enter, Tab |
| Edit | `x`, `dd`, `yy`, `p` `P` (one unnamed register) |
| Undo | `u`, Ctrl-R, insert sessions grouped as one undo step |
| Search | `/` with a literal pattern, `n` `N` |
| Command line | `:w`, `:w <path>`, `:q` (refused with pending edits), `:q!`, `:wq`, `:e <path>` (replaces the one buffer, refused with pending edits), `:<line>` |

The screen has a line-number gutter, horizontal and vertical scrolling
(horizontal scrolling is the default for source files), a status line, and a
command and message area.

### Everyday code editing

After the first release, in roughly this order: counts and operators with
motions (`d{motion}`, `c{motion}`, `y{motion}`), Visual and Visual Line
modes, backward search and regular expressions, multiple buffers, split
views, file and buffer pickers, workspace search and quickfix navigation,
substitution, named registers, block selections, `.` repeat and macros,
configurable mappings, autoindent, bracket matching, soft wrap, relative line
numbers, themes, and recovery after an interrupted session. Views of the same
buffer share its undo history.

### Ritz language tools

Show syntax colors during ordinary editing, overlay diagnostic spans and
messages, and provide hover, go to definition, and jump back. Add semantic
highlighting and completion when ritz-lsp advertises those capabilities.

## Ritz and platform boundaries

Keep buffer edits, undo, modes, commands, and screen layout independent of
terminal and OS I/O. Convert input to typed key, paste, resize, signal, and
timer events. Render to a grid of styled cells, then emit only the cells that
changed since the last frame. Treat buffer contents as display data and
visibly escape control bytes so opening a file cannot emit terminal commands.

Use ritzlib's `Vec<T>` for growable storage, `Span<T>` for bounded views,
`StrView` for borrowed text, and `String` only for text the editor itself
creates (status messages, command lines). Buffer lines are bytes, not
`String`; see [Buffer representation](#buffer-representation-and-performance).
Model modes, events, and errors with enums and `Result`. Add missing reusable
operations to ritzlib with focused tests. Keep raw pointers and NUL-terminated
strings at ABI boundaries that require them. Review the implementation against
[Ritz, Not C](../projects/ritz/docs/RITZ_NOT_C.md),
[Review](../projects/ritz/docs/REVIEW.md), and
[Standard](../projects/ritz/docs/STANDARD.md).

### Shared terminal session

rzsh already switches the console to raw mode on both targets and decodes
keys. `rzsh/src/os.ritz` clears `ECHO`, `ICANON`, `ISIG`, `IEXTEN`, `ICRNL`,
and `IXON` on Linux and `TTY_ECHO | TTY_ICANON | TTY_ISIG` on Harland.
`rzsh/src/input.ritz` decodes CSI sequences into key codes. Lift both into a
ritzlib terminal-session module (enter raw mode, restore, decode keys, write
cursor and style sequences, with the Escape timeout below) and make rzsh and
Buddhafinger call it. Do not write a third copy.

With `ISIG` (or `TTY_ISIG`) cleared, Ctrl-C reaches the editor as a key. With
`TTY_ISIG` set, Harland kills the foreground process with no cleanup.

### Event loop

Drive the editor from one loop using ritzlib's `poll` and signalfd support.
On Linux, poll terminal input and the signal fd alongside the server's stdout
and stderr. Watch the server's stdin for `POLLOUT` only while bytes are queued,
and use the next timer deadline as the poll timeout.

Add borrowed `Fd` accessors to `Process` for the three pipes and a way to
put the parent ends in nonblocking mode. Retain the bytes and offset of a
partially written JSON-RPC frame until it is sent. Coalesce only snapshots
whose frames have yet to start, and cap queued bytes. Read stdout
incrementally and drain stderr separately into a bounded log. Limit pipe
work per iteration so terminal input and redraws keep moving. Block
`SIGPIPE` in the editor so a closed server stdin returns `EPIPE`. On stdout
EOF or `EPIPE`, end the server session and report the failure in the status
area. Restore the inherited signal mask in the child before exec.

On Harland, the loop waits on the console with a timeout until subprocess
pipes exist (see the prerequisites).

### Linux signals

Install no `sigaction` handlers. ritzlib does not wrap `sigaction` because a
handler needs a restorer trampoline that pure Ritz does not set up
(`ritzlib/sys.ritz`). Instead, block `SIGTERM`, `SIGINT`, `SIGHUP`,
`SIGTSTP`, `SIGCONT`, and `SIGWINCH` at startup and read them from a
signalfd in the event loop:

- `SIGTERM`, `SIGINT`, `SIGHUP`: restore the terminal, then exit. With `ISIG`
  off, `SIGINT` comes only from another process.
- `SIGTSTP`: restore the terminal, then stop the process with `SIGSTOP`
  (a blocked `SIGTSTP` does not stop it on its own). Ctrl-Z is a key with
  `ISIG` off, so map it to the same path.
- `SIGCONT`: re-enter raw mode and repaint.
- `SIGWINCH`: query `get_winsize` and relayout.

Use ritzlib's `tcgetattr`, `tcsetattr`, and `get_winsize` (`ritzlib/term.ritz`).
`ritzlib/sys.ritz` keeps `SIGHUP`, `SIGCONT`, `SIGSTOP`, and `SIGTSTP` as
private constants and has no `SIGWINCH`; export them (adding `SIGWINCH`, 28)
for `SigSet` callers.

### Escape and key timeouts

Arrow and function keys arrive as `ESC [ …`, so a lone Escape is
recognizable only when no further byte follows within a short timeout. rzsh
documents `KEY_ESCAPE` as "bare escape after timeout" but sets `VTIME` to 0
and blocks in `read`, so today the next keystroke is what resolves it. For a
modal editor that would make Escape-to-leave-Insert hang until the next key.

On Linux, wait on stdin with `poll` and a configurable timeout (default
25 ms) after an `ESC`. On Harland, `read(0)` blocks until a byte arrives, so
the first Harland port is blocked on a timed console read. A monotonic
timeout is enough; a wall clock is not required.

### Harland console

The console attribute ABI (`tty_getattr`/`tty_setattr`) carries three flags:
`TTY_ECHO`, `TTY_ICANON`, and `TTY_ISIG`. Clear all three while editing
through the shared terminal-session module. Harland reports no window size,
so use a configurable viewport. Escape sequences reach a terminal only on the
serial console, so Buddhafinger runs there. Exercise the adapter under QEMU.

The raw input queue holds `LDISC_QUEUE_SIZE` (1024) bytes and `ldisc_input`
drops anything past that without telling the reader. A paste or burst larger
than the queue is silently truncated, so paste on Harland is not a supported
path until the queue grows or reports overruns.

A killed process runs no cleanup. rzsh restores the console flags at its next
prompt, but alternate-screen and cursor state stay on the host terminal until
signal delivery or an exit hook exists.

### Verification on each target

Verify raw input, the Escape timeout, escape sequences, viewport sizing, file
open and save, and terminal restoration on each target. Probe capabilities
such as alternate screen, bracketed paste, color, and resize. Restore terminal
mode on normal exit, on handled errors, and on the Linux signals above. Use the
existing Indium shell image as the port's test environment, then package the
editor by adding it to `projects/indium/initramfs.pkgs` once the staging
path uses the packaged compiler described under
[Tests and build isolation](#tests-and-build-isolation). [Terminal library](../projects/ritzlib/term.ritz) ·
[Harland line discipline](../projects/harland/kernel/src/tty/ldisc.ritz) ·
[rzsh terminal code](../projects/rzsh/src/os.ritz) ·
[Indium shell image](../projects/indium/README.md)

## Saving files

On both targets: preserve line endings, final newline state, and untouched
bytes on round trips, and keep the buffer dirty if a save fails.

### Linux

Write the buffer to a temporary file in the same directory, `fsync` it,
`rename` it over the target, and `fsync` the directory. Preserve the target's
permissions. Before writing, `stat` the target and compare size and mtime
with what was recorded at open; on a mismatch, refuse the save and ask the
user to confirm the overwrite. On failure, remove the temporary file.
ritzlib has `rename`, `stat`, and `Fd.stat` but no `fsync`; add it.

### Harland

Harland's filesystem does not behave like Linux here, and the save path
follows what the kernel does (`kernel/src/fs/syscall.ritz`):

- A file opened for writing gets a per-fd kernel write buffer that starts
  empty. Each `write` appends to it, whatever the file position. On `close`,
  or on process exit (`fs_process_end` closes every open fd the same way),
  that buffer replaces the file's entire contents. `O_TRUNC` affects only the
  fd's read view, and only with `O_WRONLY` (`O_RDWR | O_TRUNC` does not
  truncate it); it does not change what close commits.
- A kill between two writes therefore commits the prefix written so far. A
  kill before the first write leaves the old file.
- A buffer of zero bytes commits nothing, so writing an empty file leaves the
  old contents in place.
- Only paths under `/var` persist across reboot. Other paths are the
  initramfs copy in RAM. A `/var` close schedules a save to the storage
  device, debounced to at most one per 200 ms; `sync` (syscall 162,
  `sys_sync` in ritzlib) saves at once.
- `ritzlib/fs.ritz` `write_file` opens through `sys_open3`, which exists only
  on Linux, so it does not compile for Harland today.

So the Harland save builds the whole file in one buffer, opens the target
`O_WRONLY | O_CREAT | O_TRUNC`, requires one full-length `write`, and checks
the final `close` result. A single write avoids a process kill between chunks
committing a prefix of an existing file. It requires a contiguous snapshot in
the editor and a kernel write buffer. Until the empty-write fix lands, refuse
an empty save before opening the target.

For RAM-only paths, a successful close completes the save. For `/var`,
require both a successful close and a successful `sync` before marking the
buffer clean. Close updates the runtime tree before updating the persistent
subtree. If the second update fails, the new bytes may be visible in the
running system while a reboot still loads the old file. A failed sync can
also leave the on-disk version behind. Keep the buffer dirty in either case
and report that the live file may already have changed. Keep transactional
replacement across the two trees and storage failure recovery on the Harland
save-parity track.

Without `stat`, the Harland save cannot detect external changes or preserve
permissions; it says so in the message area. Claim save parity only once the
Harland save passes the same contract tests as Linux.

## Buffer representation and performance

Start with a `Vec` of logical lines, each a `Vec<u8>` of the line's bytes
with its terminator kept in line metadata. Not `String`: ritzlib's `String`
is a `Vec<u8>` kept NUL-terminated for C interop, and a zero byte is a legal
file byte that any `as_ptr` consumer would cut the line at. A `Span` over the
line vector works as a temporary view when a caller needs a range of lines.

Direct indexing makes line lookup constant time, while inserting or removing a
line shifts the following entries, and mid-line edits move the line's suffix.
Use line-local edit transactions so normal typing and undo avoid copying the
whole file. Use a buffer API for reading slices, replacing ranges, and walking
lines so the editor stays independent of their storage. The Linux save
streams line slices to the temporary file; the Harland save gathers them into
one buffer first.

Use byte offsets for storage and keep UTF-16 conversion at the ritz-lsp
boundary. ritzlib has no grapheme segmentation or display-width measurement,
so the first release moves the cursor by UTF-8 code point, treats Tab as a
fixed advance to the next tab stop, counts every other code point as one
cell, and displays malformed UTF-8 bytes with a defined escape (for example
`<xx>`) while preserving them on disk. Grapheme clusters (UAX #29) and wide
glyphs are a separate ritzlib project that follows the measurement pass.

Render only the viewport. For long lines, maintain bounded, lazy byte-to-cell
checkpoints so steady scrolling and cursor movement can reuse prior work.
Invalidate checkpoints from the affected edit onward. This still leaves an
initial scan cost when jumping far into an uncached line.

If long-line measurements show suffix movement dominates, compare the
contiguous line with bounded byte fragments in a `Vec<Vec<u8>>` for individual
long lines. Split and merge neighboring fragments to keep repeated local edits
from creating one allocation per keystroke. Measure fragment lookup and
shifting as well as copying. Consider pooled storage only if allocation costs
justify tracking pool lifetime and reclamation across undo history and
discarded edits. If shifting many line entries or allocating once per line
dominates on large files, evaluate indexed blocks of lines with aggregate line
counts. Keep both decisions behind the buffer API.

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

### Lexical colors

In Ritz a newline ends a `"…"` string and a `#` comment (`ritz1/src/lexer.ritz`),
and the language has no multi-line strings or block comments. No lexical state
needed for coloring crosses a line, so the editor lexer works per line and an
edit re-lexes only the lines it touched. The compiler lexer's indent stack
matters only for INDENT/DEDENT tokens, which coloring ignores; bracket depth
matters only for bracket matching, which comes later.

Write a small editor lexer in the editor and leave `ritz1/src/lexer.ritz` in
the compiler. Take keywords, types, and literal rules from the Vim syntax
file that `projects/ritz-lsp/install.sh` writes, which is a keyword list, not
a lexer. Add a test that fails when the compiler gains a keyword the editor
lexer does not know. Apply semantic tokens as an overlay when the server
advertises them.

### ritz-lsp

The current server uses stdio JSON-RPC, full-text document sync, and UTF-16
positions. It advertises hover and definition, and no completion or semantic
tokens. Its diagnostics carry the document version. `didOpen` and `didChange`
mark the document dirty, and `server_run` compiles dirty documents at their
latest version and publishes diagnostics whenever no input is waiting on
stdin, before it blocks for the next message. A burst of changes compiles
once, for the last, with no follow-up request from the client.
[Server README](../projects/ritz-lsp/README.md) ·
[Server loop](../projects/ritz-lsp/src/server.ritz)

Run the server as a child process and read its framed messages from the
event loop without blocking editing. Coalesce rapid changes on the client and
bound queued full-text snapshots. Associate requests with buffer revisions,
discard outdated responses, and show diagnostics only when their version
matches the current revision. Do not send probe requests to pull diagnostics;
they would force extra compiles. Use a timeout and report server failures in
the status area. Selectively suspend sync above a measured document size
while keeping navigation and lexical colors available. Start the real server
on Linux with `RITZ1` pointing to `ritz1_selfhosted`.

Local editing and lexical colors work on either platform. ritz-lsp on Harland
is its own milestone (see below).

## Harland prerequisites

Build these in parallel with the Linux editor. Each kernel item lands in
`kernel/src/syscall/numbers.ritz` with its handler, the matching wrapper in
`ritzlib/sys.ritz`, and the portable ritzlib API the editor calls, with tests
on both targets.

| Need | Today | Required for | Milestone |
|---|---|---|---|
| Timed console read (`VTIME`-like timeout, or `poll` on fd 0) | `read(0)` blocks until a byte arrives | Bare Escape, key timeouts | First port |
| Portable create-and-write in `ritzlib/fs.ritz` | `write_file` uses Linux-only `sys_open3` | Saving through ritzlib on Harland | First port |
| Empty write commits on close | A zero-byte buffer commits nothing | Saving an empty buffer | First port |
| Larger raw input queue, or an overrun the reader can see | Bytes past 1024 dropped silently | Paste, fast input bursts | Paste support |
| `stat` / `fstat` (size, mtime, mode) | Missing; number 4 free | External-change check, permissions | Save parity |
| `chmod` or mode on create | Missing | Preserving permissions | Save parity |
| Transactional replacement and storage failure recovery | Runtime and persistent namespace writes can fail independently | A defined save contract across close and sync failures | Save parity |
| `rename`, `unlink` | Missing | Temporary-file saves, if Harland moves to a Linux-style save | Optional |
| Console window size | Missing | Automatic viewport | Later (configurable viewport until then) |
| Signal delivery or exit hook | Ctrl-C with `TTY_ISIG` kills outright | Terminal restoration after a kill | Later |
| Pipes and spawn with fd redirection | Missing; number 29 free | Running ritz-lsp | ritz-lsp on Harland |
| More than 8 processes | `MAX_PROCS` is 8; init, rzsh, editor, ritz-lsp, and its ritz1 take 5 | Running ritz-lsp alongside other programs | ritz-lsp on Harland |
| A scratch directory for ritz-lsp | Server writes under `$XDG_RUNTIME_DIR` or `/tmp`; Harland has neither | ritz-lsp compiles | ritz-lsp on Harland |
| ritz1 runnable on Harland | Not yet | Diagnostics | ritz-lsp on Harland |

The first Harland port needs the console flags (available now), the
configurable viewport, the timed console read, a ritzlib write path that
compiles for Harland, and the empty-write fix. Its save is the single-write
save described above, with separate RAM-only and persistent success criteria.

## Tests and build isolation

Use a dedicated Buddhafinger test entry point and CI job. Build the editor,
Ritz test binaries, and the real server used by editor tests with
`ritz1_selfhosted` only. Assume a Docker image supplies the packaged compiler
and its build dependencies. Use the same image and compiler artifact for
Linux and Harland targets, pass the compiler explicitly at each build entry
point, and set `RITZ1` to the packaged compiler for real-server tests.

Indium's initramfs build currently invokes `rz build` with the default
compiler for each manifest entry. Before registering Buddhafinger there,
give its staging path an explicit `ritz1_selfhosted` build using the image.
Have the packaging test verify the compiler selection and that the resulting
Harland ELF is staged. Compiler bootstrap belongs to the upstream image build. Keep Buddhafinger out of the compiler regression
suites and generic workspace multi-compiler build and test sweeps through a
reasoned `[workspace.exclude]` entry in `rz.toml`. `rz` refuses an empty
reason or a stale path, and `test_nested_packages.py` fails if a `ritz.toml`
is in neither set. Verify the sweep excludes the editor and the dedicated job
actually runs its suite. [Workspace CLI](../rz) ·
[Compiler test targets](../projects/ritz/Makefile) ·
[CI workflows](../.github/workflows/main.yml)

- **Buffer and command tests.** Use ritzunit for edit ranges, split/join,
  undo/redo, modes, every command in the first-release list, search, and line
  endings. Run deterministic randomized edits against a simple reference
  buffer and keep seeds for reproducing failures. Cover long files, long
  lines, mixed line endings, zero bytes in lines, malformed UTF-8, and the
  byte/code-point/cell/UTF-16 boundaries.
- **Screen and I/O tests.** Assert cell grids for gutters, clipping, tabs,
  control-byte escaping, selections, diagnostics, and resize. Drive a Linux
  PTY through open, edit, save, and exit, including a bare Escape, Ctrl-Z and
  resume, `SIGTERM`, interrupted sessions, and terminal restoration. Inject
  short writes, storage exhaustion, and concurrent file changes.
- **Language tests.** Use a scripted server for partial frames, rapid edits,
  delayed replies, stale results, capability negotiation, and server exit.
  Stall server stdin reads during a full-text update and flood stderr. Verify
  terminal input and repaint continue, queued bytes stay bounded, and a
  partially written frame arrives intact when the server resumes reading.
  Smoke-test the real ritz-lsp with a Ritz file that produces a diagnostic
  without any request after the change, and that supports hover and
  definition lookup. Fail when the compiler's keyword set and the editor
  lexer's differ.
- **Harland acceptance.** Launch the self-hosted-compiler build from the
  serial console under QEMU, edit a file under `/var`, save, reopen, and
  verify the saved bytes and the shell's terminal state after exit. Leave
  Insert mode with a bare Escape. Reboot and verify the file persisted. Kill
  the editor before and after the save's write and verify the file holds the
  old or the new contents, never a prefix. Cover empty saves and RAM-only
  saves without a storage device. Inject failure during the persistent
  subtree update and during sync, then check the dirty flag, error message,
  live contents, and rebooted contents. Repeat the console acceptance test
  against the packaged Indium image when distribution integration lands.
- **Performance tests.** Track the buffer workloads separately from functional
  tests. Set regression limits after collecting repeatable baseline results.

## Proposed AGAST tasks

Work is tracked in AGAST. One task per line; the Harland items can run in
parallel with the Linux ones.

Linux editor:

1. Terminal-session module in ritzlib, lifted from rzsh (raw mode, restore,
   key decoding, Escape timeout, cursor and style output), with rzsh moved
   onto it.
2. `Process` fd accessors and nonblocking pipe reads and writes in
   `ritzlib/process.ritz`.
3. Buffer core: line storage, buffer API, edit transactions, undo/redo,
   round-trip preservation, randomized reference tests.
4. Screen: cell grid, diff output, gutter, scrolling, status and message
   lines, control-byte escaping.
5. Modes and the first-release command list.
6. Event loop with `poll` and signalfd, signal handling (exporting the
   signal constants and adding `SIGWINCH`), PTY tests.
7. Linux save: temporary file, `fsync` (new in ritzlib), `rename`, `stat`
   check, permissions.
8. Editor lexer and lexical colors, with the keyword-drift test.
9. ritz-lsp client: framing, revisions, diagnostics overlay, hover,
   definition, pipe backpressure and scripted-server tests.
10. Benchmarks and the dedicated CI job with the `[workspace.exclude]` entry.

Harland track:

11. Timed console read.
12. Portable create-and-write in `ritzlib/fs.ritz`, and empty writes that
    commit on close.
13. Raw input queue growth or overrun reporting.
14. `stat`/`fstat` and mode on create.
15. Harland adapter, single-write save, QEMU acceptance test, and Indium
    packaging with the Docker-packaged self-hosted compiler.
16. Transactional Harland replacement and storage failure recovery for save
    parity.

ritz-lsp on Harland (later): pipes and fd-redirected spawn, a larger process
table, a scratch directory, and a runnable ritz1.

## Decisions for review

1. Approve modal editing as the default, with the first-release command list
   above as the initial Vim subset.
2. Approve a vector of byte lines (`Vec<u8>`, terminators in metadata) as the
   first implementation, and use benchmark results to decide when to adopt
   fragments or indexed line blocks.
3. Approve the [Harland prerequisites](#harland-prerequisites) as a parallel
   track. The first port needs the timed console read, a Harland-capable
   ritzlib write path, and the empty-write fix, and saves with a single write
   and checks `sync` for `/var`. Save parity waits for `stat`, modes, and a
   transactional replacement and storage failure contract. ritz-lsp on Harland
   waits for pipes, a larger process table, a scratch directory, and ritz1.
4. Approve the smaller first usable release (one buffer, Normal and Insert,
   save, quit), with counts, operators, Visual mode, and multiple buffers
   following under everyday editing.
5. Approve lifting rzsh's terminal code into a shared ritzlib module before
   the editor's terminal adapter is written.
