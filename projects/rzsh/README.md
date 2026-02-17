# rzsh

Minimal cross-platform shell for Harland and Linux - interactive command execution with built-in commands.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

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
# Build for Harland (freestanding PIE)
export RITZ_PATH=/path/to/ritz
./ritz build . --target harland

# Build for Linux (for testing)
./ritz build . --target linux

# The Linux binary is at:
./build/debug/rzsh.linux
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

**Active development** - Interactive shell loop, built-in commands, line editing, and external command execution all work on both Linux and Harland. The shell runs on Harland as part of the Indium distribution's init sequence. Pipes, redirection, environment variables, and history are planned for future phases.

## License

MIT License - see LICENSE file
