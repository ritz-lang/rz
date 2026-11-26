# Review of the Buddhafinger editor proposal

Second review of [BUDDHAFINGER_PROPOSAL.md](BUDDHAFINGER_PROPOSAL.md) at
`01f22e650`, after that commit absorbed the Codex pass. Checked against
`tty/ldisc.ritz`, `tty/console.ritz`, `fs/syscall.ritz`,
`syscall/numbers.ritz`, `ritzlib` (`fd`, `fs`, `process`, `term`, `sys`),
`rzsh`, and `ritz-lsp`.

The direction is sound. It is ready to build on Linux once the command list
is written down and the event loop uses the `poll` and `signalfd` primitives
that already exist. The Harland track is the right split. The save path and
the Escape key are specified against kernel behavior that differs from the
text.

## Recorded decision

Buddhafinger stays a terminal program. On Linux it talks to the tty. On
Harland and Indium it runs in the serial console, the same place rzsh does.
Adding it to `projects/indium/initramfs.pkgs` makes it a program started from
that shell. It does not draw a window.

The editor keeps a grid of styled cells, and a platform adapter emits the
changes. This work's adapter writes terminal sequences. A Prism terminal
emulator would be a later program that interprets those sequences, and it is
outside this proposal. Harland's framebuffer is a pixel map Prism uses. It is
not a text console, and this editor does not target it.

## Decisions in the proposal

1. **Approve modal editing.** Put the initial command list in the proposal
   before any implementation. A first slice that matches decision 4:
   `h j k l`, `w b e`, `0 $`, `gg` `G`, page motions, `i` `a` `o`, `x`,
   `dd` `yy` `p`, `u` and Ctrl-R, `/` `n` `N` as literal search, and
   `:w` `:q` `:q!` `:e`. Counts, operators, Visual, macros, and registers
   come after the adapters work.
2. **Approve a vector of lines**, stored as `Vec<u8>` with terminators in
   metadata (finding 6). Keep fragments and line-blocks behind the buffer
   API until the benchmarks say to switch.
3. **Approve the parallel Harland track**, after findings 1, 4, and 5 are
   folded into the prerequisites table.
4. **Shrink the first usable release** to one buffer, Normal and Insert,
   save, and quit. That gets the Linux adapters under test sooner. It does
   not by itself make the Harland port sooner: Insert mode needs a timed
   read so a bare Escape can be distinguished from an arrow key, and
   Harland `read(0)` blocks until a byte arrives.

The "First usable release" bullets still describe the large product. Once
decision 4 is accepted, that section should describe the slice, and the rest
should move under everyday editing.

## Findings

### 1. Harland save does not work the way the proposal says

A write is buffered on the fd and becomes the file only when the fd is
flushed, on `close` or on process exit (`fs_process_end` flushes every open
fd the same way). The buffer starts empty and is the whole new file, so a
short write that gets flushed replaces the file with that prefix. A kill
during save therefore commits a partial file. A kill before the first write
leaves the old file in place. `O_TRUNC` only clears the fd's view, and only
when `O_WRONLY` is set. `O_RDWR | O_TRUNC` does not truncate, because the
check is `flags & O_WRONLY`. `sys_open3` (the call that takes a mode) is
Linux-only, so `ritzlib/fs.ritz` `write_file` does not compile for Harland.
Durable writes are paths under `/var`. Anything else is the initramfs copy
in RAM and is gone at reboot.

The Indium acceptance test should edit a file under `/var`, write the full
buffer, and close. Warn that a kill while the write fd is open can replace
the file with a prefix.

### 2. Linux signals should come through `signalfd`

`ritzlib/process.ritz` already has it. `sys.ritz` says a real `sigaction`
handler needs a restorer trampoline that pure Ritz does not set up. The only
shipped helper is `signal_ignore`. Block `SIGTERM`, `SIGINT`, `SIGTSTP`,
`SIGCONT`, and `SIGWINCH`, and read them from a signalfd in the same `poll`
as the terminal and the language server. `SIGTSTP` still needs an explicit
step after the event is read: restore the terminal, then suspend. With
`ISIG` off, Ctrl-C is a key and never becomes `SIGINT`.

`poll` is already in `ritzlib/fd.ritz`. The process pipe fd is private and
the reads block. Expose it, set `O_NONBLOCK`, and poll it. That is the
missing piece, rather than a new wait API.

### 3. ritz-lsp already publishes diagnostics when its stdin goes idle

`server_run` calls `publish_pending` when `input_pending()` is false, before
it blocks on the next message. A `didChange` with nothing else queued is
compiled at its latest version without a follow-up request. The idle "cheap
request" would force an extra compile. Keep client-side coalescing and the
version check. Drop the probe request.

### 4. A bare Escape cannot be recognized on Harland today

Arrow keys arrive as `ESC [ …`. `rzsh` documents `KEY_ESCAPE` as "bare
escape after timeout", then sets `VTIME` to 0 and blocks in `read`. The next
byte is what disambiguates, so Escape-to-leave-Insert waits forever if the
next event is nothing. Linux `poll` with a short timeout covers this. The
first Harland port stays blocked on a timed console read even if Visual mode
and counts are cut. The same timeout is what the idle diagnostic path and
cursor-checkpoint work want later. A wall clock is not required for that.

### 5. Raw input silently drops bytes past 1024

`ldisc_input` gives up when `LDISC_QUEUE_SIZE` is full. A bracketed paste or
a fast burst larger than that queue is truncated, and the editor cannot see
the loss. Put a larger raw queue, or an overrun the editor can report, on
the Harland prerequisites. Until then, paste on Harland is not a supported
path.

### 6. Store lines as `Vec<u8>`, not `String`

`String` is a `Vec<u8>` with a trailing NUL for C interop, and `read_file`
returns one. A line that contains a zero byte is a legal file byte and will
be cut by any `as_ptr` consumer. Keep terminators in line metadata, as the
proposal says, and keep `String` for status text the editor itself creates.

### 7. Lift rzsh's terminal session instead of writing a third one

`rzsh/src/os.ritz` already switches raw mode on both targets, clearing
`TTY_ECHO | TTY_ICANON | TTY_ISIG` on Harland and the corresponding termios
bits on Linux. `rzsh/src/input.ritz` already decodes CSI and writes cursor
sequences. Those belong in ritzlib, with the Escape timeout added there, and
both the shell and the editor should call them.

### 8. The incremental lexer is an indent-stack problem

A newline ends a `"` string and a `#` comment (`lexer.ritz`). The state that
crosses lines is the indent stack, which the compiler lexer already tracks,
plus bracket depth if mismatch highlighting is on. The Vim syntax file is a
keyword heredoc in `projects/ritz-lsp/install.sh`, not a lexer. Copy the
keyword and literal rules into a small editor lexer. Leave
`ritz1/src/lexer.ritz` in the compiler.

### 9. Running ritz-lsp on Harland needs more than pipes

The process table holds 8 processes (`MAX_PROCS`). Init, rzsh, the editor,
ritz-lsp, and the ritz1 it spawns per compile already take 5. The server
also writes the buffer to a scratch directory under `$XDG_RUNTIME_DIR` or
`/tmp` before compiling. Harland has neither. Those two belong in the
ritz-lsp milestone next to pipes.

### 10. Grapheme-cluster cursor motion is its own ritzlib project

Nothing in ritzlib segments graphemes or measures display width. The first
release should move by byte, treat TAB as a fixed column advance, and show
invalid UTF-8 with the replacement policy the proposal already requires.
UAX #29 and wide glyphs can follow the measurement pass.

## What already matches the tree

`TTY_ECHO`, `TTY_ICANON`, and `TTY_ISIG` match the line discipline, and
Ctrl-C with `TTY_ISIG` set kills the foreground process with no user
cleanup. Syscall numbers 4 (`stat`) and 29 (`pipe`) are reserved and
unimplemented. `rename`, `unlink`, `chmod`, and `fstat` are absent.
`[workspace.exclude]` is a real gate: `rz` refuses an empty reason and a
stale path, and `test_nested_packages.py` fails if a `ritz.toml` is in
neither set. ritz-lsp advertises full-text sync, hover, and definition
only, and diagnostics carry the document version. Linux `rename`, `stat`,
`tcgetattr`, `tcsetattr`, and `get_winsize` exist. Packaging through
`projects/indium/initramfs.pkgs` is the path
`test_indium_initramfs_pkgs.py` checks. The buffer API hiding the line
representation is the right seam, and the 17 ms Linux frame target is a
reasonable initial bar to measure against.
