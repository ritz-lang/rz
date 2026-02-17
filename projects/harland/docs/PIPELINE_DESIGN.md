# Pipeline & I/O Design for Harland

> Design document for shell pipelines, I/O redirection, and capability-based
> process spawning in the Harland microkernel.

## Overview

Harland uses `spawn()` not `fork()+exec()`, and channels instead of Unix pipes.
This document outlines how shell pipelines (`cmd1 | cmd2 | cmd3`) and I/O
redirection (`cmd > file`, `cmd < file`) should work in this model.

## Design Principles

1. **Capabilities over magic numbers** - No `stdin=0, stdout=1, stderr=2` magic.
   I/O endpoints are explicit capabilities granted at spawn time.

2. **Typed channels** - `Channel<T>` for IPC. For byte streams, `Channel<u8>`
   with internal buffering (chunks of 4KB).

3. **Explicit grants** - Parent must explicitly grant capabilities to child.
   Secure default: children get nothing unless granted.

4. **No fork()** - Process creation is always explicit via `spawn()`.

---

## Part 1: Channel-Based Byte Streams

### Channel Types

```ritz
# Typed channel endpoints
struct ChannelRead<T>
    id: u64          # Kernel-assigned handle

struct ChannelWrite<T>
    id: u64          # Kernel-assigned handle

# Byte channel for stdin/stdout (buffered internally)
type ByteReader = ChannelRead<u8>
type ByteWriter = ChannelWrite<u8>
```

### Internal Buffering

Byte channels use internal 4KB chunks for efficiency:

```ritz
# Kernel-side buffer (internal, not exposed to userspace)
struct ChannelBuffer
    chunks: Vec<[u8; 4096]>
    read_pos: usize        # Position in first chunk
    write_closed: bool
    read_closed: bool
```

User code reads/writes bytes; the kernel handles chunking transparently:

```ritz
# Userspace API
fn channel_read(reader: ByteReader, buf: []u8) -> Result<usize, IoError>
fn channel_write(writer: ByteWriter, data: []u8) -> Result<usize, IoError>
fn channel_close_read(reader: ByteReader)
fn channel_close_write(writer: ByteWriter)
```

### Syscall Interface

```ritz
# Create a byte channel (returns read + write endpoints)
const SYS_CHANNEL_CREATE: u64 = 50

fn sys_channel_create() -> i64
    # Returns: channel ID on success, negative on error
    # Caller then uses SYS_CHANNEL_READ/WRITE with this ID

const SYS_CHANNEL_READ: u64 = 51
const SYS_CHANNEL_WRITE: u64 = 52
const SYS_CHANNEL_CLOSE: u64 = 53

fn sys_channel_read(chan_id: u64, buf: *u8, len: u64) -> i64
    # Returns bytes read, 0 on EOF, negative on error

fn sys_channel_write(chan_id: u64, buf: *u8, len: u64) -> i64
    # Returns bytes written, negative on error

fn sys_channel_close(chan_id: u64, which: u64) -> i64
    # which: 0=read end, 1=write end
```

---

## Part 2: Capability-Based Spawn

### Current State

```ritz
# What we have now (syscall.ritz)
fn sys_spawn(path: *u8) -> i64
fn sys_spawn_args(path: *u8, argv: **u8, argc: i32) -> i64
```

### Target State

```ritz
# New spawn with explicit I/O capabilities
const SYS_SPAWN_EX: u64 = 25

struct SpawnOptions
    stdin_cap: u64      # Channel ID for stdin (0 = none/closed)
    stdout_cap: u64     # Channel ID for stdout (0 = none/closed)
    stderr_cap: u64     # Channel ID for stderr (0 = none/closed)
    cwd_cap: u64        # Path capability for cwd (0 = inherit)
    flags: u64          # Reserved

fn sys_spawn_ex(
    path: *u8,
    argv: **u8,
    argc: i32,
    opts: *SpawnOptions
) -> i64
    # Returns PID on success, negative on error
```

### How Children See I/O

When a child is spawned with `SpawnOptions`, the kernel:

1. Creates the process with empty capability table
2. If `stdin_cap != 0`: Maps channel ID to the child's "stdin slot"
3. If `stdout_cap != 0`: Maps channel ID to the child's "stdout slot"
4. If `stderr_cap != 0`: Maps channel ID to the child's "stderr slot"

Child code uses standard I/O syscalls:

```ritz
# In child process (e.g., cat, grep, etc.)
fn main() -> i32
    var buf: [4096]u8

    # sys_read with fd=0 reads from the stdin capability
    let n = sys_read(0, @buf[0], 4096)

    # sys_write with fd=1 writes to the stdout capability
    sys_write(1, @buf[0], n as u64)

    0
```

The kernel translates fd 0/1/2 to the actual channel capabilities.

---

## Part 3: Shell Pipeline Example

### Parsing `ls | grep foo | wc -l`

```ritz
# Shell parses pipeline into:
struct PipelineStage
    cmd: StrView
    args: Vec<StrView>

let stages: Vec<PipelineStage> = [
    PipelineStage { cmd: "ls", args: [] },
    PipelineStage { cmd: "grep", args: ["foo"] },
    PipelineStage { cmd: "wc", args: ["-l"] },
]
```

### Execution Flow

```ritz
fn execute_pipeline(stages: []PipelineStage) -> i32
    let n = stages.len()

    # Create n-1 channels (one between each pair of stages)
    var channels: Vec<(ByteReader, ByteWriter)> = Vec::new()
    for i in 0..n-1
        channels.push(sys_channel_create())

    # Spawn each stage with appropriate I/O
    var pids: Vec<i64> = Vec::new()

    for i in 0..n
        var opts: SpawnOptions

        # stdin: read from previous channel (or shell's stdin for first)
        if i == 0
            opts.stdin_cap = shell_stdin_cap
        else
            opts.stdin_cap = channels[i-1].0.id  # read end

        # stdout: write to next channel (or shell's stdout for last)
        if i == n - 1
            opts.stdout_cap = shell_stdout_cap
        else
            opts.stdout_cap = channels[i].1.id  # write end

        # stderr: inherit shell's stderr
        opts.stderr_cap = shell_stderr_cap

        let pid = sys_spawn_ex(stages[i].cmd, stages[i].args, opts)
        pids.push(pid)

        # Close our handles (children have their own refs)
        if i > 0
            channel_close_read(channels[i-1].0)   # We don't read
        if i < n - 1
            channel_close_write(channels[i].1)    # We don't write

    # Wait for all processes
    var last_exit = 0
    for pid in pids
        last_exit = sys_wait(pid)

    last_exit
```

---

## Part 4: I/O Redirection

### Output Redirection (`cmd > file`)

```ritz
fn execute_with_redirect_out(cmd: StrView, args: []StrView, path: StrView) -> i32
    # Open file for writing
    let fd = sys_open(path.ptr, O_WRONLY | O_CREAT | O_TRUNC)
    if fd < 0
        return -1

    # Spawn with stdout pointing to file
    var opts: SpawnOptions
    opts.stdin_cap = shell_stdin_cap
    opts.stdout_cap = fd as u64  # File descriptor as capability
    opts.stderr_cap = shell_stderr_cap

    let pid = sys_spawn_ex(cmd, args, opts)
    sys_close(fd)  # Close our handle

    sys_wait(pid)
```

### Input Redirection (`cmd < file`)

```ritz
fn execute_with_redirect_in(cmd: StrView, args: []StrView, path: StrView) -> i32
    # Open file for reading
    let fd = sys_open(path.ptr, O_RDONLY)
    if fd < 0
        return -1

    # Spawn with stdin pointing to file
    var opts: SpawnOptions
    opts.stdin_cap = fd as u64
    opts.stdout_cap = shell_stdout_cap
    opts.stderr_cap = shell_stderr_cap

    let pid = sys_spawn_ex(cmd, args, opts)
    sys_close(fd)

    sys_wait(pid)
```

---

## Part 5: Built-in Commands

These commands modify shell state and cannot be external binaries:

| Command | Why Built-in | Implementation |
|---------|--------------|----------------|
| `cd DIR` | Changes shell's CWD | `sys_chdir(dir)` |
| `pwd` | Shows shell's CWD | `sys_getcwd(buf)` |
| `exit [N]` | Exits shell process | `sys_exit(n)` |
| `export VAR=VAL` | Modifies shell env | In-memory env table |

### Required Syscalls

```ritz
const SYS_GETCWD: u64 = 26
const SYS_CHDIR: u64 = 27

fn sys_getcwd(buf: *u8, size: u64) -> i64
    # Returns length of path, or negative on error
    # Writes null-terminated path to buf

fn sys_chdir(path: *u8) -> i64
    # Returns 0 on success, negative on error
    # Changes the calling process's CWD
```

### Per-Process CWD

```ritz
# In kernel Process struct
pub struct Process
    pid: u64
    state: u64
    entry_point: u64
    user_stack_top: u64
    kernel_stack_top: u64
    page_table: u64
    # NEW: Working directory
    cwd: [256]u8           # Current working directory path
    cwd_len: u16           # Length of CWD string
```

---

## Part 6: ritzutils Project

External utilities that work with pipelines:

| Utility | Description |
|---------|-------------|
| `cat` | Concatenate files to stdout |
| `head` | Output first N lines |
| `tail` | Output last N lines |
| `wc` | Word/line/byte count |
| `grep` | Pattern matching |
| `sort` | Sort lines |
| `uniq` | Remove duplicate lines |
| `tr` | Translate characters |
| `cut` | Extract columns |
| `tee` | Copy stdin to file and stdout |

### Project Structure

```
projects/ritzutils/
├── ritz.toml           # Multi-binary build
├── src/
│   ├── cat.ritz
│   ├── head.ritz
│   ├── tail.ritz
│   ├── wc.ritz
│   ├── grep.ritz
│   └── ...
└── build/debug/
    ├── cat.elf
    ├── head.elf
    └── ...
```

### ritz.toml

```toml
[package]
name = "ritzutils"
version = "0.1.0"
target = "harland"

[[bin]]
name = "cat"
path = "src/cat.ritz"

[[bin]]
name = "head"
path = "src/head.ritz"

[[bin]]
name = "wc"
path = "src/wc.ritz"

# ... more binaries
```

---

## Implementation Phases

### Phase 1: Foundation (This PR)
- [ ] `sys_getcwd` syscall
- [ ] `sys_chdir` syscall
- [ ] Per-process CWD in Process struct
- [ ] Tests for CWD operations

### Phase 2: Byte Channels
- [ ] `sys_channel_create` syscall
- [ ] `sys_channel_read` / `sys_channel_write` syscalls
- [ ] `sys_channel_close` syscall
- [ ] Internal buffering (4KB chunks)
- [ ] Tests for channel operations

### Phase 3: Spawn with Capabilities
- [ ] `sys_spawn_ex` syscall
- [ ] `SpawnOptions` struct
- [ ] Map stdin/stdout/stderr caps to fd 0/1/2
- [ ] Tests for capability-based spawn

### Phase 4: ritzutils
- [ ] Create project structure
- [ ] Implement `cat` utility
- [ ] Update indium build to include ritzutils
- [ ] Test `cat` with pipelines

### Phase 5: rzsh Integration
- [ ] `cd` / `pwd` builtins
- [ ] Pipeline parsing (`|`)
- [ ] Output redirection (`>`, `>>`)
- [ ] Input redirection (`<`)

---

## Security Considerations

### Principle of Least Privilege

Children receive **only** the capabilities explicitly granted:

```ritz
# BAD (Unix-style): Child inherits everything
fork()  # Child has access to all parent's fds, memory, etc.

# GOOD (Harland-style): Explicit grants
var opts: SpawnOptions
opts.stdin_cap = channel.read_end    # Only stdin
opts.stdout_cap = channel.write_end  # Only stdout
# No stderr, no filesystem, no network
spawn_ex(cmd, args, opts)
```

### Secure Defaults

```ritz
# Default SpawnOptions (no capabilities)
const SPAWN_OPTS_DEFAULT: SpawnOptions = SpawnOptions {
    stdin_cap: 0,   # Closed
    stdout_cap: 0,  # Closed
    stderr_cap: 0,  # Closed
    cwd_cap: 0,     # Inherit parent's CWD
    flags: 0,
}
```

### Capability Inheritance Options

For convenience, we may add flags:

```ritz
const SPAWN_INHERIT_STDIO: u64 = 1 << 0    # Inherit stdin/stdout/stderr
const SPAWN_INHERIT_CWD: u64 = 1 << 1      # Inherit CWD
const SPAWN_INHERIT_ENV: u64 = 1 << 2      # Inherit environment

# Shell convenience: inherit everything (less secure)
var opts: SpawnOptions
opts.flags = SPAWN_INHERIT_STDIO | SPAWN_INHERIT_CWD | SPAWN_INHERIT_ENV
```

But the secure default remains explicit grants.

---

## References

- `projects/harland/docs/ARCHITECTURE.md` - Kernel architecture
- `projects/harland/docs/KERNEL_CONTRACT.md` - API contract
- `projects/harland/kernel/src/arch/x86_64/syscall.ritz` - Syscall implementation
- `projects/rzsh/` - Ritz shell project

---

*This design document was created for LARB review and implementation planning.*
