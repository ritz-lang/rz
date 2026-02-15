# ritz-lsp Architecture

This document describes the technical architecture of the Ritz Language Server.

## Overview

The Ritz Language Server implements the [Language Server Protocol (LSP)](https://microsoft.github.io/language-server-protocol/) to provide IDE features for the Ritz programming language. It acts as a bridge between editors and the Ritz compiler infrastructure.

### How LSP Works

```
┌─────────────────────────────────────────────────────────────────┐
│                          Editor                                  │
│                   (VS Code, Neovim, Emacs)                       │
│                                                                  │
│  User edits file → Editor sends LSP request → Displays result   │
└─────────────────────────────────────────────────────────────────┘
                              │
                        JSON-RPC/stdio
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        ritz-lsp                                  │
│                                                                  │
│  Receives request → Analyzes code → Returns response            │
└─────────────────────────────────────────────────────────────────┘
```

Communication uses JSON-RPC 2.0 over standard input/output (stdio). The editor starts the language server as a subprocess and sends requests for features like hover information, completions, and diagnostics.

## Component Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         ritz-lsp                                 │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Protocol Layer                           │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │ │
│  │  │  Transport   │  │   Message    │  │    Request       │  │ │
│  │  │   (stdio)    │  │   Parsing    │  │    Dispatch      │  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   Feature Handlers                          │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │ │
│  │  │  Hover  │ │  Goto   │ │Complete │ │  Diag   │  ...      │ │
│  │  │ Handler │ │  Def    │ │ Handler │ │ Handler │           │ │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   Analysis Engine                           │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │ │
│  │  │   Symbol     │  │    Type      │  │     Index        │  │ │
│  │  │   Table      │  │  Database    │  │    (Search)      │  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   Compiler Frontend                         │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │ │
│  │  │    Lexer     │  │    Parser    │  │   Type Checker   │  │ │
│  │  │              │  │              │  │                  │  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Cache Layer                              │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │ │
│  │  │     AST      │  │    Types     │  │   File Watcher   │  │ │
│  │  │    Cache     │  │    Cache     │  │  (Invalidation)  │  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Component Descriptions

#### Protocol Layer

The protocol layer handles LSP communication:

- **Transport**: Manages stdio communication with the editor
- **Message Parsing**: Deserializes JSON-RPC messages into typed requests
- **Request Dispatch**: Routes requests to appropriate feature handlers

#### Feature Handlers

Each LSP feature has a dedicated handler:

| Handler | LSP Methods | Description |
|---------|-------------|-------------|
| DiagnosticsHandler | `textDocument/publishDiagnostics` | Reports errors and warnings |
| HoverHandler | `textDocument/hover` | Shows type and documentation |
| DefinitionHandler | `textDocument/definition` | Navigates to symbol definitions |
| CompletionHandler | `textDocument/completion` | Provides code completions |
| ReferencesHandler | `textDocument/references` | Finds all symbol usages |
| RenameHandler | `textDocument/rename` | Renames symbols project-wide |
| SymbolHandler | `textDocument/documentSymbol` | Provides outline/structure |

#### Analysis Engine

The analysis engine maintains the semantic understanding of code:

- **Symbol Table**: Tracks all defined symbols (functions, variables, types)
- **Type Database**: Stores resolved types and type relationships
- **Index**: Enables fast symbol lookup and search

#### Compiler Frontend

Reuses components from the Ritz compiler:

- **Lexer**: Tokenizes source code
- **Parser**: Produces AST with location information
- **Type Checker**: Infers and validates types, checks ownership

#### Cache Layer

Manages performance through caching:

- **AST Cache**: Stores parsed ASTs per file
- **Type Cache**: Caches type inference results
- **File Watcher**: Invalidates caches when files change

## Compiler Integration

### Phase 1: Python Implementation (ritz0)

Initial implementation reuses ritz0 (Python reference compiler) components:

```
┌─────────────────────────────────────────────────────────────────┐
│                        ritz-lsp                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                         imports
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         ritz0                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │    lexer     │  │    parser    │  │    type_checker      │   │
│  │  (lexer.py)  │  │  (parser.py) │  │  (type_checker.py)   │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

Benefits:
- Single source of truth for language semantics
- Faster development (reuse existing code)
- Consistent error messages

### Phase 2: Native Implementation (ritz1)

Future implementation in Ritz itself:

```
┌─────────────────────────────────────────────────────────────────┐
│                   ritz-lsp (native)                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │    lexer     │  │    parser    │  │    type_checker      │   │
│  │  (Ritz)      │  │   (Ritz)     │  │       (Ritz)         │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

Benefits:
- Better performance
- Dogfooding the language
- Path to self-hosting

## Data Flow

### Request Processing

```
1. Editor sends request
   textDocument/hover { uri: "file:///code/main.ritz", position: {line: 5, char: 10} }
                              │
                              ▼
2. Protocol Layer parses JSON-RPC message
   → Extracts method name and parameters
   → Routes to HoverHandler
                              │
                              ▼
3. HoverHandler processes request
   → Gets document from cache (or parses if stale)
   → Locates AST node at position
   → Resolves symbol/expression type
   → Formats hover content
                              │
                              ▼
4. Response returned to editor
   { contents: "fn calculate(x: Int, y: Int) -> Int", range: {...} }
```

### Document Synchronization

```
1. User opens file
   textDocument/didOpen { uri: "...", text: "..." }
   → Store document in memory
   → Parse and cache AST
   → Run diagnostics
   → Publish diagnostics to editor

2. User edits file
   textDocument/didChange { uri: "...", changes: [...] }
   → Apply incremental changes
   → Invalidate cached AST
   → Re-parse affected regions
   → Update diagnostics

3. User saves file
   textDocument/didSave { uri: "..." }
   → Full re-analysis if needed
   → Update cross-file references

4. User closes file
   textDocument/didClose { uri: "..." }
   → Remove from active documents
   → Keep cached data for references
```

### Incremental Analysis

For performance, the server uses incremental analysis:

```
File Change Detected
        │
        ▼
┌───────────────────┐
│ Invalidate cached │
│   AST for file    │
├───────────────────┤
│ Re-parse modified │
│     regions       │
├───────────────────┤
│  Update symbol    │
│     table         │
├───────────────────┤
│ Re-typecheck only │
│  affected scopes  │
├───────────────────┤
│ Update dependent  │
│     files         │
└───────────────────┘
```

## Key Modules

### Planned Module Structure

```
src/
├── main.ritz              # Entry point, argument parsing
├── server.ritz            # LSP server lifecycle
├── protocol/
│   ├── transport.ritz     # stdio communication
│   ├── messages.ritz      # LSP message types
│   └── dispatch.ritz      # Request routing
├── handlers/
│   ├── diagnostics.ritz   # Error reporting
│   ├── hover.ritz         # Hover information
│   ├── definition.ritz    # Go to definition
│   ├── completion.ritz    # Code completions
│   ├── references.ritz    # Find references
│   ├── rename.ritz        # Symbol renaming
│   └── symbols.ritz       # Document outline
├── analysis/
│   ├── document.ritz      # Document management
│   ├── symbols.ritz       # Symbol table
│   ├── index.ritz         # Project indexing
│   └── resolver.ritz      # Name resolution
├── compiler/
│   ├── lexer.ritz         # Tokenization
│   ├── parser.ritz        # Parsing (error-recovering)
│   ├── ast.ritz           # AST definitions
│   └── types.ritz         # Type checking
└── cache/
    ├── ast_cache.ritz     # AST caching
    ├── type_cache.ritz    # Type caching
    └── watcher.ritz       # File watching
```

### Module Responsibilities

| Module | Purpose |
|--------|---------|
| `server` | Initialize LSP, handle lifecycle (initialize, shutdown) |
| `protocol/transport` | Read/write JSON-RPC messages over stdio |
| `protocol/messages` | Define LSP message types (requests, responses, notifications) |
| `handlers/*` | Implement specific LSP features |
| `analysis/document` | Track open documents, manage versions |
| `analysis/symbols` | Build and query symbol tables |
| `analysis/index` | Index entire project for fast lookup |
| `compiler/*` | Parsing and type checking (from ritz0/ritz1) |
| `cache/*` | Performance optimization through caching |

## Error Recovery

For IDE use, the parser must recover from errors to provide useful results:

```ritz
fn example():
    let x = 10
    let y =        # Incomplete expression
    x + y          # Still want to recognize this
```

Strategy:
1. On parse error, record the error
2. Skip to a recovery point (next statement)
3. Continue parsing
4. Return partial AST with error nodes

## Performance Considerations

### Target Latencies

| Operation | Target | Strategy |
|-----------|--------|----------|
| Diagnostics | < 100ms | Incremental parsing |
| Go to definition | < 50ms | Symbol index lookup |
| Completions | < 100ms | Prefix tree for names |
| Hover | < 50ms | Cached type info |
| Find references | < 500ms | Pre-built index |

### Memory Budget

- Target: < 500MB for typical project
- Lazy loading for large projects
- LRU eviction for cached data
- Compact AST representation

## Future Considerations

### Self-Hosting Path

Once ritz1 is complete:

1. Port core analysis logic to Ritz
2. Compile ritz-lsp with ritz1
3. Use native ritz-lsp for development

### Multi-Root Workspaces

Support for multiple project roots:

```
workspace/
├── core/          # Core library
├── stdlib/        # Standard library
└── app/           # Application
```

Each root has its own `ritz.toml` and may have cross-dependencies.

### Remote Development

Support for LSP over network (SSH, containers):

- Support TCP/socket transport
- Handle path translation
- Manage file synchronization
