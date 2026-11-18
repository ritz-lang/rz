# Sage

A JavaScript engine in Ritz, early. **What works today:** a lexer, a
recursive-descent parser and a tree-walking interpreter (AGAST #2787):
`sage t.js` runs `console.log(6 * 7)` and prints `42`. It covers numbers,
strings, objects, functions and closures, control flow, exceptions and
console.log (see [Status](#status) for what it doesn't cover yet). The
bytecode VM and generational GC described below are the design, not code.

**Part of the [Ritz Ecosystem](../ritz/docs/ECOSYSTEM.md)**

## Overview

Sage is a JavaScript engine implementation written entirely in Ritz. It is designed to run inside the Tempest web browser, executing JavaScript code for web pages with the DOM exposed through Tempest's owned DOM tree. Sage uses a register-based bytecode virtual machine (rather than a stack-based VM) for efficiency, and implements a generational garbage collector.

The engine implements the ECMAScript specification, parsing JavaScript source through a lexer and recursive descent parser, compiling to bytecode, and executing in the VM. Sage communicates with Tempest's DOM tree through a well-defined interface, allowing JavaScript to read and mutate DOM elements while keeping ownership of the DOM with Tempest.

## Features

> **Planned/partial.** The list below describes the design. See [Status](#status): today a tree-walking interpreter runs scripts; there is no bytecode, VM or GC.

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

See [Usage](#usage).

## Usage

```bash
./rz build sage
./projects/sage/build/debug/sage --help      # usage, exit 0
./projects/sage/build/debug/sage --version   # exit 0
./projects/sage/build/debug/sage t.js        # runs t.js
```

`sage FILE.js` parses the file and runs it; console.log writes to stdout as
the script runs. Exit 0 means the script ran to the end. A script that does
not parse, or throws an uncaught exception, exits 1 with the error on stderr,
e.g. `t.js: Uncaught ReferenceError: nope is not defined` (never exit 0 for
work not done, #2460). No arguments or an unknown option is a usage error
(exit 2). There is no REPL. `projects/sage/test.sh` pins this behaviour.

From Ritz, `js_run(source)` (in `src/interp.ritz`) runs a script and keeps
its output: `interp_output`, `interp_failed` and `interp_error` read the
result. The `Engine` API below is the intended design; it does not exist yet.

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

**Alpha: a tree-walking interpreter over the parser's AST.** `src/` holds
the lexer, parser, AST and `interp.ritz`, the evaluator (AGAST #2787).

It supports numbers (printed as node prints them), strings with escapes,
booleans, null, undefined and objects; arithmetic, comparison, equality,
logical, bitwise, unary, `typeof`, update and compound assignment operators;
let/const/var; function declarations (hoisted) and expressions, closures and
recursion (a runaway recursion is a RangeError); if, while, do-while, for,
break, continue and return; throw/try/catch/finally with Error objects
(`e.name`, `e.message`); console.log, console.error and a string's
`.length`.

Not yet: arrays (#4074), arrow functions (#4075), and `new`, `this`,
classes, prototypes, for-in/of, switch, labels and the standard built-ins
such as Math (#4077); each throws `SyntaxError: sage does not support this
yet`. Numbers beyond 10^22 can print an ulp out (#4076). Nothing is freed:
there is no GC yet. Full ECMAScript compliance, the bytecode VM, a garbage
collector and DOM integration with [tempest](../tempest) are all still
ahead. Note the `examples/` directory referenced by older docs does not
exist.

The unit tests pass: `./rz test sage` runs the lexer, parser and interpreter
tests (116 at 2026-11-18) and `test.sh`, which checks `sage t.js` prints 42,
and that a script that throws or does not parse exits 1.

## License

MIT License - see LICENSE file
