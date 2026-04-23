# ritz1 Architecture

ritz1 is the self-hosted Ritz compiler, written in Ritz and compiled by ritz0
(the Python bootstrap compiler). It compiles `.ritz` source files to LLVM IR.

## Module Overview

11 source files in `src/`, totaling ~13,700 lines:

| Module | Lines | Purpose |
|--------|------:|---------|
| `tokens_gen` | 138 | Token type constants and `Token` struct (generated) |
| `nfa` | 289 | NFA engine with Thompson's construction |
| `regex` | 221 | Regex parser that builds NFAs from pattern strings |
| `lexer_nfa` | 467 | Multi-pattern NFA lexer with indentation tracking |
| `lexer_setup_gen` | 110 | Generated lexer pattern registration (generated) |
| `ast` | 351 | AST node types, expression/statement/type kind constants |
| `ast_helpers` | 1,494 | AST node constructors and bump allocator |
| `parser_gen` | 4,407 | Recursive descent parser (generated from grammar) |
| `monomorph` | 1,083 | Generic function/struct monomorphization pass |
| `emitter` | 4,573 | LLVM IR code generator |
| `main` | 591 | Compiler driver and import resolution |

Files marked "generated" are produced by ritzgen from the Ritz grammar.

## Compilation Pipeline

```
source.ritz
    |
    v
[tokenize]  lexer_setup_gen + lexer_nfa + nfa + regex
    |         Setup NFA patterns, tokenize with longest-match
    v
[parse]     parser_gen + ast + ast_helpers
    |         Recursive descent, builds AST with bump allocator
    v
[resolve]   main (import resolution)
    |         Recursively tokenize+parse imported modules,
    |         inline their declarations into the main Module
    v
[monomorph] monomorph
    |         Specialize generic functions/structs with
    |         concrete type arguments (Vec<i32>, etc.)
    v
[emit]      emitter
    |         Walk AST, generate LLVM IR with SSA registers
    v
output.ll
```

## Module Dependency Graph

```
tokens_gen ─────────────────────────────────────────┐
    |                                                |
   nfa                                              ast
    |                                                |
  regex                                         ast_helpers
    |                                                |
 lexer_nfa ──────────────────────────────────  parser_gen
    |                                                |
lexer_setup_gen                                      |
    |               ┌──── monomorph ─────────────────┤
    └───────────────┤                                |
                    └──── emitter ───────────────────┘
                    |
                   main
```

Arrows point from dependency to dependent. `main` imports all modules.

## Key Data Structures

### Token (`tokens_gen`)
```
struct Token
    kind: i32       # TOK_FN, TOK_IDENT, TOK_NUMBER, etc.
    start: *u8      # pointer into source buffer
    len: i32        # token length in bytes
    line: i32
    col: i32
    string_val: *u8 # processed string value (for string literals)
    string_len: i32
```

### AST Nodes (`ast`)
- **`Expr`** — expression tree (literals, identifiers, binary/unary ops, calls, field access, indexing)
- **`Stmt`** — statement list (var decl, assignment, if/while/for, return, break, continue)
- **`FnDef`** — function definition (name, params, return type, body, generic params)
- **`StructDef`** — struct definition (name, fields, type params)
- **`Module`** — top-level container (imports, functions, structs, constants, globals, impls)

All AST nodes are allocated from a bump allocator (`parser_alloc()` in `ast_helpers`).
Linked lists (via `next` pointers) are used for ordered collections.

### NFA (`nfa`)
- **`NFAState`** — state with accept flag and token type
- **`Transition`** — edges: char, range, epsilon, or any
- **`NFA`** — state machine with pre-allocated arrays (`MAX_STATES=256`, `MAX_TRANS=512`)

### Lexer (`lexer_nfa`)
- **`Lexer`** — NFA-based tokenizer with indent stack, bracket depth tracking, and string escape processing
- **`TokenPattern`** — maps NFA fragment to token type with priority

### Emitter State (`emitter`)
- **`EmitterState`** — LLVM IR output buffer, SSA register counter, label counter, local variable table, string constant pool, extern tracking, struct/function deduplication

## Build System

Each `.ritz` file compiles to one `.ll` file (1:1 mapping). The Makefile orchestrates:

```
ritz0 src/*.ritz  -->  build/*.ll  (11 LLVM IR files)
clang -c build/*.ll  -->  build/*.o  (11 object files)
ld build/*.o + ritzlib/*.o + runtime  -->  build/ritz1
```

### Bootstrap

ritz1 can compile itself (bootstrap):

```
build/ritz1 src/*.ritz  -->  build/*_sh.ll  (self-hosted IR)
llc + clang  -->  build/*_sh.o
ld  -->  build/ritz1_selfhosted
```

### Runtime Dependencies

- **ritzlib modules**: sys, io, str, string, hash, memory, gvec, drop, env
- **Runtime entry point**: `ritz_start_envp.x86_64.o` (provides `_start`, calls `main(argc, argv, envp)`)
- **No libc** for syscalls — direct Linux syscalls via ritzlib.sys

## Import Resolution

`main.ritz` implements recursive import resolution:

1. Parse source file into a `Module`
2. For each `import` declaration, search for the source file:
   - Relative to the importing file's directory
   - In directories listed in `RITZ_PATH` environment variable
3. Tokenize and parse the imported file
4. Inline its declarations (functions, structs, constants) into the importing module
5. Track processed imports to prevent circular dependencies

## Generated vs Hand-Written Code

| Generated (by ritzgen) | Hand-Written |
|------------------------|--------------|
| `tokens_gen` | `nfa` |
| `lexer_setup_gen` | `regex` |
| `parser_gen` | `lexer_nfa` |
| | `ast` |
| | `ast_helpers` |
| | `monomorph` |
| | `emitter` |
| | `main` |

## Signature Files (`.ritz.sig`)

Each source file has a corresponding `.ritz.sig` file containing cached compilation
metadata — function signatures with pre-compiled LLVM IR. These enable separate
compilation: when module B imports module A, ritz0 reads A's `.sig` file to get
external declarations without recompiling A.
