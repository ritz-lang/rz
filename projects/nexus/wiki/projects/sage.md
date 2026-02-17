# Sage

JavaScript engine written in Ritz. Active development.

---

## Overview

Sage is a standalone JavaScript engine providing parsing, compilation to bytecode, and bytecode interpretation. It is used by Tempest (the Ritz browser) to execute JavaScript on web pages.

Sage handles JavaScript execution only. DOM APIs are provided by the browser integration layer in Tempest. HTML/CSS parsing is handled by Lexis.

---

## Where It Fits

```
TEMPEST (browser)
    └── Sage (JavaScript execution)
            ├── Lexer (tokenization)
            ├── Parser (AST generation)
            ├── Compiler (bytecode)
            ├── Interpreter / JIT
            └── Runtime (GC, built-ins)
```

---

## Architecture

```
JavaScript source
        │
        ▼
┌─────────────────────────────────┐
│             LEXER               │
│     Character → Token stream    │
└─────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────┐
│             PARSER              │
│      Tokens → AST nodes         │
└─────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────┐
│            COMPILER             │
│       AST → Bytecode            │
└─────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────┐
│         INTERPRETER / JIT       │
│     Execute bytecode            │
│     Garbage collect             │
└─────────────────────────────────┘
```

---

## Components

### Lexer

Tokenizes JavaScript source. Produces a flat token stream:

```ritz
enum Token
    Keyword(Keyword)
    Identifier(String)
    Number(f64)
    String(String)
    Punctuator(Punctuator)
    RegExp(String, String)
    EOF

fn tokenize(source: StrView) -> Vec<Token>
```

### Parser

Builds the Abstract Syntax Tree (AST) from the token stream:

```ritz
enum Expr
    Literal(Value)
    Identifier(String)
    BinOp { op: BinOp, left: Box<Expr>, right: Box<Expr> }
    Call { callee: Box<Expr>, args: Vec<Expr> }
    Arrow { params: Vec<String>, body: Box<Stmt> }
    ...

enum Stmt
    Var { name: String, init: Option<Expr> }
    Expr(Expr)
    Return(Option<Expr>)
    If { cond: Expr, then: Box<Stmt>, else_: Option<Box<Stmt>> }
    While { cond: Expr, body: Box<Stmt> }
    ...
```

### Compiler

Compiles AST to register-based bytecode:

```ritz
enum Opcode
    LoadConst(u16)     # Load constant by index
    LoadVar(u16)       # Load variable by slot
    StoreVar(u16)      # Store to variable slot
    Add                # Pop two, push sum
    Call(u8)           # Function call with N args
    Return             # Return from function
    Jump(i16)          # Unconditional jump
    JumpFalse(i16)     # Jump if top of stack is falsy
    ...
```

### Runtime

Built-in objects and garbage collection:

```ritz
# JavaScript values
enum Value
    Undefined
    Null
    Boolean(bool)
    Number(f64)
    String(String)
    Object(GcRef<Object>)
    Function(GcRef<Function>)

# JS objects (property map)
struct Object
    properties: HashMap<String, Value>
    prototype: Option<GcRef<Object>>
```

---

## JavaScript Compatibility

| Feature | Status |
|---------|--------|
| ES5 syntax | Planned |
| ES6 arrow functions | Planned |
| ES6 let/const | Planned |
| Promises | Planned |
| async/await | Planned |
| ES modules (import/export) | Planned |
| DOM API | Via Tempest integration |

---

## Testing

```ritz
[[test]]
fn test_arithmetic() -> i32
    let vm = VM.new()
    let result = vm.eval("2 + 2")
    assert result.as_number() == 4.0
    0

[[test]]
fn test_string_concat() -> i32
    let vm = VM.new()
    let result = vm.eval("'hello' + ' world'")
    assert result.as_string() == "hello world"
    0

[[test]]
fn test_function_call() -> i32
    let vm = VM.new()
    let result = vm.eval("function add(a, b) { return a + b; } add(3, 4)")
    assert result.as_number() == 7.0
    0
```

---

## Project Structure

```
sage/
├── src/
│   ├── lexer.ritz         # Tokenization
│   ├── parser.ritz        # AST generation
│   ├── ast.ritz           # AST type definitions
│   ├── compiler.ritz      # Bytecode generation
│   ├── bytecode.ritz      # Bytecode instruction definitions
│   ├── vm.ritz            # Virtual machine execution
│   ├── runtime/
│   │   ├── object.ritz    # JS Object
│   │   ├── array.ritz     # JS Array
│   │   ├── string.ritz    # JS String
│   │   └── function.ritz  # JS Function
│   └── gc.ritz            # Garbage collector
├── tests/
└── ritz.toml
```

---

## Current Status

Active development. Lexer and parser implementation in progress.

---

## Related Projects

- [Tempest](tempest.md) — Browser that uses Sage for JavaScript execution
- [Lexis](lexis.md) — HTML/CSS parser used alongside Sage
- [Iris](iris.md) — Rendering engine that responds to DOM mutations from Sage
