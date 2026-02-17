# rzsh

The Ritz shell. Active development.

---

## Overview

rzsh is the official shell for the Ritz ecosystem. It is a cross-platform shell that runs both on Linux (as a regular userspace process) and natively on Harland (the Ritz microkernel).

---

## Where It Fits

```
On Linux:
    rzsh → Linux syscalls (via ritzlib/sys.ritz)

On Harland:
    rzsh → Harland IPC → user-space services
                └── Goliath (filesystem)
                └── Network daemon
```

---

## Key Design Goals

- **Unified platform** — Same shell codebase on Linux and Harland
- **OS abstraction layer** — Platform differences handled by an OS abstraction layer, not scattered `#ifdef`-style conditionals
- **Ritz-native** — No C dependency, no POSIX libc

---

## Features

- Interactive command prompt with line editing
- Command history
- Pipeline support (`cmd1 | cmd2`)
- Redirection (`cmd > file`, `cmd < file`)
- Variable expansion (`$VAR`, `${VAR}`)
- Built-in commands (`cd`, `pwd`, `exit`, `export`, etc.)
- Script execution (`.rzsh` files)
- Job control (foreground/background processes)

---

## Usage

### Basic Commands

```bash
# Run a command
ls -la /home

# Pipe output
ls | grep .ritz

# Redirect
ritz test . > test_results.txt 2>&1

# Variables
export RITZ_PATH=~/dev/ritz-lang
echo $RITZ_PATH

# Scripts
rzsh build.rzsh
```

### Shell Scripts

```bash
#!/usr/bin/env rzsh

# Build and test a project
for project in squeeze cryptosec valet
    echo "Testing $project..."
    cd $RITZ_PATH/$project
    ritz test .
    if $? != 0
        echo "FAILED: $project"
        exit 1
    end
end

echo "All tests passed!"
```

---

## OS Abstraction Layer

The OS abstraction layer isolates platform-specific code:

```ritz
# Abstract interface
trait OsInterface
    fn spawn(cmd: StrView, args: Vec<StrView>) -> Result<Pid, Error>
    fn wait_for(pid: Pid) -> Result<ExitStatus, Error>
    fn getcwd() -> Result<String, Error>
    fn chdir(path: StrView) -> Result<(), Error>
    fn read_dir(path: StrView) -> Result<Vec<DirEntry>, Error>

# Linux implementation
struct LinuxOs
impl OsInterface for LinuxOs
    fn spawn(cmd: StrView, args: Vec<StrView>) -> Result<Pid, Error>
        # fork() + execve() via direct syscalls

# Harland implementation
struct HarlandOs
impl OsInterface for HarlandOs
    fn spawn(cmd: StrView, args: Vec<StrView>) -> Result<Pid, Error>
        # IPC call to process manager
```

---

## Project Structure

```
rzsh/
├── src/
│   ├── main.ritz          # Entry point
│   ├── shell.ritz         # Main shell loop
│   ├── lexer.ritz         # Command tokenization
│   ├── parser.ritz        # Command parsing
│   ├── executor.ritz      # Command execution
│   ├── builtins.ritz      # Built-in commands
│   ├── history.ritz       # Command history
│   ├── readline.ritz      # Line editing
│   └── os/
│       ├── linux.ritz     # Linux implementation
│       └── harland.ritz   # Harland implementation
├── ritz.toml
└── linker_pie.ld          # PIE linker script
```

---

## Current Status

Active development. Linux implementation functional. Harland integration in progress.

---

## Related Projects

- [Harland](harland.md) — Microkernel rzsh runs on natively
- [Goliath](goliath.md) — Filesystem rzsh accesses on Harland
- [Ritz](ritz.md) — The compiler rzsh is built with
- [Tooling Subsystem](../subsystems/tooling.md)
