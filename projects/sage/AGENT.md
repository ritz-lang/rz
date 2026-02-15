# Sage - JavaScript Engine

JavaScript engine written in Ritz.

---

## Project Overview

Sage is a standalone JavaScript engine providing parsing, compilation, and execution of JavaScript code.

### Responsibilities

- **Parsing** — JavaScript source to AST
- **Compilation** — AST to bytecode (and JIT)
- **Execution** — Bytecode interpreter
- **Runtime** — Built-in objects, garbage collection

### Non-Responsibilities

Sage does NOT handle:
- DOM APIs (provided by browser integration)
- HTML/CSS parsing (use Lexis)
- Rendering (use Iris)
- Network requests (use Valet)

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                 JavaScript Source                    │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                    LEXER                             │
│              Tokenization                            │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                    PARSER                            │
│                AST Generation                        │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                   COMPILER                           │
│              Bytecode Generation                     │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                 INTERPRETER                          │
│            Bytecode Execution + JIT                  │
└─────────────────────────────────────────────────────┘
```

---

## Ritz Coding Guidelines

### Parameter Syntax

| Syntax | Meaning | Usage |
|--------|---------|-------|
| `x: T` | Const borrow | Default (~70% of params) |
| `x:& T` | Mutable borrow | When modifying the value |
| `x:= T` | Move ownership | When taking ownership |

**NO SPACE between `:` and modifier!** Write `:&` not `: &`

```ritz
fn parse(source: StrView) -> Result<AST, ParseError>
fn compile(ast: AST) -> Bytecode
fn execute(vm:& VM, bytecode: Bytecode) -> Value
```

### Reference Syntax

| Syntax | Meaning |
|--------|---------|
| `@x` | Take immutable reference |
| `@&x` | Take mutable reference |
| `@T` | Immutable reference type |
| `@&T` | Mutable reference type |

### String Literals

```ritz
"hello"              # StrView (zero-copy) — DEFAULT
String.from("hello") # String (heap-allocated)
c"hello"             # *u8 for FFI ONLY
```

### Testing

```ritz
[[test]]
fn test_arithmetic() -> i32
    let vm = VM.new()
    let result = vm.eval("2 + 2")
    assert result.as_number() == 4.0
    0
```

---

## Core Doctrines

### No Concessions Doctrine

> "Never make concessions for the language — we are MAKING the language."

If Ritz can't express something cleanly, fix Ritz. Don't work around limitations.

### Test-Driven Development

1. Write failing tests first
2. Implement to make tests pass
3. Refactor with confidence
4. All tests must pass before committing

---

## Project Structure

```
sage/
├── src/
│   ├── lexer.ritz         # Tokenization
│   ├── parser.ritz        # AST generation
│   ├── ast.ritz           # AST types
│   ├── compiler.ritz      # Bytecode generation
│   ├── bytecode.ritz      # Bytecode definitions
│   ├── vm.ritz            # Virtual machine
│   ├── runtime/
│   │   ├── object.ritz    # JS objects
│   │   ├── array.ritz     # JS arrays
│   │   ├── string.ritz    # JS strings
│   │   └── function.ritz  # JS functions
│   └── gc.ritz            # Garbage collector
├── tests/
└── ritz.toml
```

---

## Style Guidelines

- **Indentation:** 4 spaces (no tabs)
- **Line length:** 100 characters max
- **Naming:** `snake_case` for functions, `PascalCase` for types
- **Immutable by default:** Use `let`, only `var` when mutation needed
- **Use `defer`** for resource cleanup

---

*Part of the Ritz ecosystem. See `larb/AGENT.md` for full guidelines.*
