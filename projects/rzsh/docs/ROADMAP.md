# rzsh Terminal Roadmap

This document outlines the feature roadmap for rzsh, covering terminal improvements and the kernel syscalls needed to support them.

## Current State Analysis

### What We Have

| Feature | Linux | Harland | Notes |
|---------|-------|---------|-------|
| Basic input/output | ✓ | ✓ | sys_read/sys_write |
| Line editing (backspace) | ✓ | ✓ | Manual terminal escape handling |
| Ctrl+C interrupt | ✓ | ✓ | Character-level detection |
| Ctrl+D EOF | ✓ | ✓ | Character-level detection |
| Built-in commands | ✓ | ✓ | help, exit, pid, echo, ls, clear |
| External commands | ✓ | ✓ | fork+execve / spawn_args |
| Directory listing | ✓ | ✓ | getdents64 / sys_readdir |
| Screen clear (ESC codes) | ✓ | ✓ | ANSI escape sequences |

### What We're Missing

| Feature | Priority | Requires Kernel Support |
|---------|----------|------------------------|
| Arrow key navigation | High | No (escape sequence parsing) |
| Command history | High | No (userspace buffer) |
| Tab completion | Medium | sys_stat or equivalent |
| Raw mode terminal | High | sys_ioctl (Linux), sys_tty_* (Harland) |
| Working directory (cd) | High | sys_chdir, sys_getcwd |
| Environment variables | Medium | Userspace only |
| Pipes | Medium | sys_pipe, sys_dup2 |
| Redirection | Medium | sys_dup2, file I/O |
| Job control (bg/fg) | Low | Signals, process groups |
| Signal handling | Low | sys_rt_sigaction |

---

## Phase 1: Line Editing Improvements

**Goal:** Make rzsh feel like a proper interactive shell with arrow keys and history.

### 1.1 Raw Mode Terminal (HIGH PRIORITY)

**Problem:** Currently the terminal is in "cooked" mode where the kernel handles line buffering. This means:
- We can't detect individual keypresses immediately
- Arrow keys send escape sequences that interfere with input
- Special keys (Home, End, Delete) don't work

**Solution (Linux):** Implement raw terminal mode via `ioctl`:

```ritz
# ritzlib/sys.ritz - New syscalls needed

# Terminal I/O control
[[target_os = "linux"]]
pub fn sys_ioctl(fd: i32, request: u64, arg: *u8) -> i32
    return syscall3(SYS_IOCTL, fd as i64, request as i64, arg as i64) as i32

# ioctl request codes for terminal
[[target_os = "linux"]]
pub const TCGETS: u64 = 0x5401      # Get termios
[[target_os = "linux"]]
pub const TCSETS: u64 = 0x5402      # Set termios
[[target_os = "linux"]]
pub const TCSETSW: u64 = 0x5403     # Set termios, wait for drain
[[target_os = "linux"]]
pub const TCSETSF: u64 = 0x5404     # Set termios, flush pending input
```

**Solution (Harland):** Create a minimal TTY subsystem:

```ritz
# Harland kernel - new syscalls (kernel/src/main.ritz)
const SYS_TTY_GETATTR: u64 = 30    # Get terminal attributes
const SYS_TTY_SETATTR: u64 = 31    # Set terminal attributes

# ritzlib/sys.ritz - Harland wrappers
[[target_os = "harland"]]
pub fn sys_tty_getattr(fd: i32, attr: *TtyAttrs) -> i32

[[target_os = "harland"]]
pub fn sys_tty_setattr(fd: i32, attr: *TtyAttrs) -> i32
```

### 1.2 Escape Sequence Parsing

Once in raw mode, we need to parse escape sequences:

```
Arrow Up:    ESC [ A  (0x1B 0x5B 0x41)
Arrow Down:  ESC [ B
Arrow Right: ESC [ C
Arrow Left:  ESC [ D
Home:        ESC [ H
End:         ESC [ F
Delete:      ESC [ 3 ~
```

**Implementation:** Add escape sequence state machine to `common.ritz`:

```ritz
enum InputState
    Normal
    Escape        # Saw ESC
    Bracket       # Saw ESC [
    Extended      # Saw ESC [ digit

enum Key
    Char(u8)
    Up
    Down
    Left
    Right
    Home
    End
    Delete
    Backspace
    Enter
    CtrlC
    CtrlD
    Unknown
```

### 1.3 Cursor Movement

Add functions to move cursor within the line:

```ritz
fn cursor_left(n: i32)
    # ESC [ <n> D

fn cursor_right(n: i32)
    # ESC [ <n> C

fn cursor_save()
    # ESC [ s

fn cursor_restore()
    # ESC [ u
```

### 1.4 Command History

Simple ring buffer for history:

```ritz
const HISTORY_SIZE: i32 = 100
const MAX_HISTORY_LINE: i64 = 512

var g_history: [100][512]u8
var g_history_count: i32 = 0
var g_history_pos: i32 = 0     # Current position when navigating
var g_history_next: i32 = 0    # Next slot to write

fn history_add(line: *u8)
fn history_prev() -> *u8
fn history_next() -> *u8
```

---

## Phase 2: Working Directory & Navigation

**Goal:** Support `cd` command and path operations.

### 2.1 Linux Implementation

Already have syscalls:
- `sys_getcwd` - Get current working directory
- `sys_chdir` - Change directory

### 2.2 Harland Implementation

Need new syscalls:

```ritz
# Kernel syscall numbers
const SYS_GETCWD: u64 = 32
const SYS_CHDIR: u64 = 33

# Implementation in kernel/src/main.ritz
fn sys_getcwd_impl(buf: *u8, size: i64) -> i64
    # Copy process's cwd path to buf
    # Return length on success, -1 on error

fn sys_chdir_impl(path: *u8) -> i32
    # Resolve path and set process's cwd
    # Return 0 on success, -errno on error
```

### 2.3 Shell Integration

```ritz
# common.ritz
fn cmd_cd(argc: i32) -> i32
    if argc == 1
        # cd with no args -> go to home (or /)
        return os_chdir(c"/")

    let path: *u8 = g_argv[1]
    let result: i32 = os_chdir(path)

    if result < 0
        puts(c"cd: ")
        puts(path)
        println(c": No such directory")
        return 1

    return 0

fn cmd_pwd() -> i32
    var buf: [256]u8
    let len: i64 = os_getcwd(@buf[0], 256)
    if len > 0
        println(@buf[0])
        return 0
    return 1
```

---

## Phase 3: Tab Completion

**Goal:** Complete file/command names with Tab key.

### 3.1 Requirements

1. `sys_stat` or equivalent to check if path is file/directory
2. `sys_readdir` (already have) to list directory contents
3. Prefix matching algorithm

### 3.2 Linux Implementation

Already have `sys_stat`, `sys_lstat` in ritzlib/sys.ritz.

### 3.3 Harland Implementation

Add sys_stat syscall:

```ritz
const SYS_STAT: u64 = 34

# Minimal stat structure for Harland
struct HarlandStat
    st_mode: u32     # File type and permissions
    st_size: i64     # File size in bytes
    st_mtime: i64    # Modification time

# File type bits (compatible with Linux)
const S_IFDIR: u32 = 0x4000   # Directory
const S_IFREG: u32 = 0x8000   # Regular file
```

### 3.4 Completion Algorithm

```ritz
fn tab_complete(line: *u8, pos: i64) -> i64
    # 1. Find word boundaries
    # 2. Determine if completing command or file
    # 3. If command (first word):
    #    - Search /bin for matches
    # 4. If file:
    #    - Parse path prefix (dir + partial name)
    #    - List directory, find matches
    # 5. If single match: complete it
    # 6. If multiple matches: show options
    # 7. Return new cursor position
```

---

## Phase 4: Pipes & Redirection

**Goal:** Support `cmd1 | cmd2` and `cmd > file`.

### 4.1 Linux Implementation

Already have:
- `sys_pipe` - Create pipe
- `sys_dup2` - Duplicate file descriptor
- `sys_fork`/`sys_execve` - Process creation

### 4.2 Harland Implementation

Need new syscalls:

```ritz
const SYS_PIPE: u64 = 35
const SYS_DUP2: u64 = 36

fn sys_pipe_impl(pipefd: *i32) -> i32
    # Create IPC channel pair
    # pipefd[0] = read end
    # pipefd[1] = write end

fn sys_dup2_impl(oldfd: i32, newfd: i32) -> i32
    # Duplicate oldfd to newfd
    # Close newfd if open
```

### 4.3 Pipe Implementation (Harland Kernel)

Harland has IPC channels that can serve as pipes:

```ritz
# Use existing channel infrastructure
fn sys_pipe_impl(pipefd: *i32) -> i32
    # Create channel pair
    let pair: ChannelPair = channel_create(pid)

    # Allocate file descriptors
    let read_fd: i32 = fd_alloc_channel(pair.endpoint_a)
    let write_fd: i32 = fd_alloc_channel(pair.endpoint_b)

    *pipefd = read_fd
    *(pipefd + 1) = write_fd
    return 0
```

---

## Phase 5: Environment Variables

**Goal:** Support `export VAR=value` and `$VAR` expansion.

### 5.1 Implementation (Pure Userspace)

```ritz
# Environment storage
const MAX_ENV_VARS: i32 = 128
const MAX_ENV_NAME: i32 = 64
const MAX_ENV_VALUE: i32 = 256

struct EnvVar
    name: [64]u8
    value: [256]u8
    set: bool

var g_environ: [128]EnvVar

fn env_get(name: *u8) -> *u8
fn env_set(name: *u8, value: *u8) -> i32
fn env_unset(name: *u8) -> i32

# Shell expansion
fn expand_vars(input: *u8, output: *u8, max_len: i64) -> i64
    # Replace $VAR with env value
    # Handle $? for last exit code
    # Handle $$ for PID
```

---

## Implementation Order

### Sprint 1: Raw Mode + Arrow Keys (Week 1-2)
1. Add `sys_ioctl` to ritzlib/sys.ritz (Linux)
2. Create termios structure and helpers
3. Add `sys_tty_getattr`/`sys_tty_setattr` stubs for Harland
4. Implement escape sequence parser
5. Add cursor movement functions
6. Test on Linux

### Sprint 2: History (Week 2-3)
1. Implement history ring buffer
2. Integrate with arrow up/down
3. Add !n and !! syntax (optional)
4. Test on Linux

### Sprint 3: Working Directory (Week 3-4)
1. Add `sys_getcwd`/`sys_chdir` to Harland kernel
2. Add wrapper in ritzlib/sys.ritz
3. Implement `cd` and `pwd` commands
4. Update prompt to show cwd (optional)

### Sprint 4: Tab Completion (Week 4-5)
1. Add `sys_stat` to Harland kernel
2. Implement prefix matching
3. Integrate with Tab key
4. Handle directories vs files

### Sprint 5: Pipes (Week 5-6)
1. Add `sys_pipe`/`sys_dup2` to Harland kernel
2. Implement pipe parsing in shell
3. Create pipeline execution logic
4. Test with simple commands

---

## Kernel Syscall Summary

### New Linux Syscalls (ritzlib/sys.ritz)

| Syscall | Number | Args | Returns | Description |
|---------|--------|------|---------|-------------|
| sys_ioctl | 16 | fd, request, arg | i32 | Device control |

### New Harland Syscalls (kernel/src/main.ritz)

| Syscall | Number | Args | Returns | Description |
|---------|--------|------|---------|-------------|
| sys_tty_getattr | 30 | fd, *attr | i32 | Get terminal attributes |
| sys_tty_setattr | 31 | fd, *attr | i32 | Set terminal attributes |
| sys_getcwd | 32 | buf, size | i64 | Get working directory |
| sys_chdir | 33 | path | i32 | Change directory |
| sys_stat | 34 | path, *stat | i32 | Get file status |
| sys_pipe | 35 | *pipefd | i32 | Create pipe |
| sys_dup2 | 36 | oldfd, newfd | i32 | Duplicate file descriptor |

---

## Testing Strategy

### Unit Tests (ritzlib)
- Test termios structure serialization
- Test escape sequence parser
- Test history buffer operations
- Test environment variable operations

### Integration Tests (rzsh)
- Test raw mode enable/disable
- Test arrow key navigation
- Test history navigation
- Test cd/pwd commands
- Test tab completion
- Test pipe execution

### Cross-Platform Tests
- Verify same behavior on Linux and Harland
- Test OS abstraction layer isolation

---

## Files to Modify

### ritzlib/sys.ritz
- Add `sys_ioctl` (Linux)
- Add termios structures and constants
- Add `sys_tty_*` stubs for Harland

### rzsh/src/common.ritz
- Add escape sequence parser
- Add history buffer
- Add cursor movement helpers
- Add environment variable storage

### rzsh/src/os.ritz
- Add `os_tty_raw_mode(enable: bool)`
- Add `os_getcwd`, `os_chdir`
- Add `os_stat`

### rzsh/src/main.ritz
- Integrate raw mode on startup/shutdown
- Update input loop for escape sequences
- Add new built-in commands (cd, pwd, export)

### harland/kernel/src/main.ritz
- Add syscall handlers for new syscalls
- Implement TTY attribute storage
- Implement per-process cwd tracking
