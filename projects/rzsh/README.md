# rzsh

Minimal cross-platform shell for Harland and Linux - interactive command execution with built-in commands.

**Part of the [Ritz Ecosystem](../ritz/docs/ECOSYSTEM.md)**

## Overview

rzsh is the shell for the Indium distribution running on the Harland microkernel. It is also fully functional on Linux, making it useful for testing shell behavior without requiring a full Harland VM. The cross-platform support is achieved through a clean OS abstraction layer using `[[target_os]]` conditional compilation in Ritz: platform-specific code (directory listing, process spawning) lives in the `os` module and is selected at compile time.

The shell provides basic interactive use: a prompt, command history, line editing with backspace, argument parsing, and execution of both built-in commands and external binaries found on the path. It is intentionally minimal - suitable for a development/debug shell in an early-stage OS.

## Features

- Interactive line editing with backspace
- Built-in commands: help, exit, pid, echo, clear, ls
- External command execution via spawn-and-wait
- Path search in `/bin` and standard paths
- Directory listing via OS abstraction layer
- Cross-platform: compiles for both Harland and Linux
- Conditional compilation via `[[target_os]]` attributes
- Position-independent executable (PIE) for Harland

## Installation

```bash
# Build both targets (run from the monorepo root; `rz` sets RITZ_PATH itself).
# Per-target selection is declared in ritz.toml's [[bin]] sections, not on the
# command line — `rz build` has no --target flag.
./rz build rzsh

# Harland binary (freestanding PIE):
#   projects/rzsh/build/debug/rzsh.elf
# Linux binary (for testing):
./projects/rzsh/build/debug/rzsh.linux --help
```

## Usage

```
$ rzsh
rzsh - Ritz Shell v0.1 (linux)
> help
Built-in commands:
  help   - Show this help
  exit   - Exit the shell
  pid    - Show process ID
  echo   - Echo arguments
  clear  - Clear the screen
  ls     - List directory contents

> ls /
bin  dev  etc  home  lib  proc  usr

> echo Hello from rzsh!
Hello from rzsh!

> pid
12345

> exit
```

```ritz
# OS abstraction layer (os.ritz)
# Platform-specific functions selected at compile time

[[target_os = "linux"]]
fn os_readdir(path: *u8, buf: *u8, buf_size: i64) -> i64
    # Linux getdents64 implementation

[[target_os = "harland"]]
fn os_readdir(path: *u8, buf: *u8, buf_size: i64) -> i64
    # Harland syscall implementation
```

## Dependencies

- `ritzlib` - Standard library (sys, str)

## Status

**Active development.** Measured 2026-09-12: `./rz build rzsh` exits 0, producing
both `build/debug/rzsh.elf` (Harland) and `build/debug/rzsh.linux`;
`rzsh.linux --help` exits 0, and `./rz test rzsh` exits 0 with
`Σ 15 passed, 0 failed` across 3 test files.

Interactive shell loop, built-in commands, line editing and external command
execution work on both Linux and Harland. The shell runs on Harland as part of
the Indium distribution's init sequence (`make -C projects/indium rzsh` pulls it
in). Pipes, redirection, environment variables and history are still planned.

## License

MIT License - see LICENSE file
