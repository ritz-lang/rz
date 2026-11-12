# Sage

A JavaScript engine in Ritz, early. **What works today:** a lexer and a
recursive-descent parser for JavaScript, used as a library (`./rz test sage`:
73 tests). **There is no interpreter yet** (AGAST #2787): `sage FILE.js` exits 1
with `not implemented`, and `sage --help` / `--version` are the only commands
that succeed. The bytecode VM and generational GC described below are the
design, not code.

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

See [Usage](#usage) — the binary builds, but cannot execute a script yet.

## Usage

```bash
./rz build sage
./projects/sage/build/debug/sage --help      # usage, exit 0
./projects/sage/build/debug/sage --version   # exit 0
./projects/sage/build/debug/sage t.js        # "not implemented", exit 1
```

**No script is executed.** `sage FILE.js` checks the file can be opened, then
exits 1 with `sage: not implemented: executing JavaScript` (AGAST #2460; the
interpreter is #2787). It used to print a version banner and exit 0 without
reading the file. No arguments or an unknown option is a usage error (exit 2).
There is no REPL. `projects/sage/test.sh` pins this behaviour.

The embedding API and JavaScript below show the intended design; `Engine` does
not exist yet.

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

**Alpha: lexer and parser only, no interpreter.** `./rz build sage` produces
`build/debug/sage`; running a script exits 1 `not implemented` (above).

The unit tests pass: `./rz test sage` runs the lexer and parser tests
(73 at 2026-09-12) and `test.sh`, which checks the CLI never exits 0 for a
script it did not run.

Lexer, parser and AST definitions are in `src/`. There is no VM, bytecode
compiler or interpreter yet (AGAST #2787).
Core JavaScript execution, full ECMAScript compliance, a garbage collector and
DOM integration with [tempest](../tempest) are all still ahead. Note the
`examples/` directory referenced by older docs does not exist.

## License

MIT License - see LICENSE file
