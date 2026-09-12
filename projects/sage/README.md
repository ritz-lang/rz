# Sage

JavaScript engine written in Ritz - register-based bytecode VM with generational garbage collection.

**Part of the [Ritz Ecosystem](../ritz/docs/ECOSYSTEM.md)**

## Overview

Sage is a JavaScript engine implementation written entirely in Ritz. It is designed to run inside the Tempest web browser, executing JavaScript code for web pages with the DOM exposed through Tempest's owned DOM tree. Sage uses a register-based bytecode virtual machine (rather than a stack-based VM) for efficiency, and implements a generational garbage collector.

The engine implements the ECMAScript specification, parsing JavaScript source through a lexer and recursive descent parser, compiling to bytecode, and executing in the VM. Sage communicates with Tempest's DOM tree through a well-defined interface, allowing JavaScript to read and mutate DOM elements while keeping ownership of the DOM with Tempest.

## Features

> **Planned/partial.** The list below describes the design. See [Status](#status) — the binary builds but does not yet execute a script.

- ECMAScript-compliant JavaScript execution
- Register-based bytecode virtual machine
- Generational garbage collector
- Lexer and recursive descent parser
- Bytecode compiler with optimizations
- DOM access interface for browser integration
- Event loop integration
- console.log and basic I/O

## Installation

```bash
# Build from source (run from the monorepo root; `rz` sets RITZ_PATH itself)
./rz build sage
# Produces projects/sage/build/debug/sage
```

See [Usage](#usage) — the binary builds and runs, but does not yet accept a
script argument.

## Usage

```bash
# Build, then run the binary
./rz build sage
./projects/sage/build/debug/sage
```

**The binary currently ignores its arguments.** `sage <file.js>` and
`sage --repl` both exit 0 after printing only `Sage JavaScript Engine v0.1.0` —
no file is read, no script is evaluated, and there is no REPL. There is also no
`projects/sage/examples/` directory, so the `examples/hello.js` path this README
used to show does not exist. Argument parsing and a file-execution path are
still to be written; `src/` currently holds the lexer, parser, AST and VM
scaffolding only.

```ritz
# Embedding Sage in a Ritz application
import sage { Engine, Value }

fn run_script(source: *u8, source_len: i64) -> i32
    let engine = Engine.new()
    let result = engine.eval(source, source_len)
    match result
        Ok(val) => 0
        Err(e)  => 1
```

```javascript
// Example JavaScript executed by Sage
console.log("Hello from Sage!");

function fibonacci(n) {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

console.log(fibonacci(10));  // 55
```

## Dependencies

Sage has no required dependencies beyond `ritzlib`.

## Status

**Alpha — builds and runs, but cannot execute a script yet.** `./rz build sage`
exits 0 producing `build/debug/sage` (measured 2026-09-12), and the binary exits
0 — but it prints only its version banner and ignores every argument. There is no
argument parsing, no file loading, and no REPL, so no JavaScript is evaluated by
the CLI today.

The unit tests do pass: `./rz test sage` exits 0 with `Σ 73 passed, 0 failed`
(2 test files). So the lexer/parser/VM internals are exercised — it is only the
CLI entry point that is missing.

Lexer, parser, AST definitions and basic VM structure are in place in `src/`.
Core JavaScript execution, full ECMAScript compliance, a garbage collector and
DOM integration with [tempest](../tempest) are all still ahead. Note the
`examples/` directory referenced by older docs does not exist.

## License

MIT License - see LICENSE file
