# Sage

JavaScript engine written in Ritz - register-based bytecode VM with generational garbage collection.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

## Overview

Sage is a JavaScript engine implementation written entirely in Ritz. It is designed to run inside the Tempest web browser, executing JavaScript code for web pages with the DOM exposed through Tempest's owned DOM tree. Sage uses a register-based bytecode virtual machine (rather than a stack-based VM) for efficiency, and implements a generational garbage collector.

The engine implements the ECMAScript specification, parsing JavaScript source through a lexer and recursive descent parser, compiling to bytecode, and executing in the VM. Sage communicates with Tempest's DOM tree through a well-defined interface, allowing JavaScript to read and mutate DOM elements while keeping ownership of the DOM with Tempest.

## Features

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
# Build from source
export RITZ_PATH=/path/to/ritz
./ritz build .

# Run a JavaScript file
./build/debug/sage script.js
```

## Usage

```bash
# Run a JavaScript file directly
./build/debug/sage examples/hello.js

# REPL (planned)
./build/debug/sage --repl
```

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

**Alpha** - Lexer, parser, AST definitions, and basic VM structure are in place. Core JavaScript execution (arithmetic, variables, functions, closures) is being implemented. Full ECMAScript compliance, garbage collector, and DOM integration with Tempest are planned for subsequent phases.

## License

MIT License - see LICENSE file
