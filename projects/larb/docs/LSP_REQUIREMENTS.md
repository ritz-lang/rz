# Ritz LSP Server Requirements

## Overview

The Ritz Language Server Protocol (LSP) implementation (`ritz-lsp`) will provide IDE support for editors like VS Code, Neovim, and Emacs.

## Priority Features

### P0: Essential (MVP)

#### 1. Diagnostics

- **Syntax errors** - Parse errors with line/column
- **Type errors** - Type mismatch, undefined symbols
- **Ownership errors** - Move/borrow violations
- **Import errors** - Missing modules, unresolved imports

```
Error format:
  file.ritz:12:5: error: cannot borrow `x` as mutable because it is already borrowed
```

#### 2. Go to Definition

- Functions (including methods)
- Variables
- Types (structs, enums)
- Module imports
- Fields

#### 3. Hover Information

- Type of expression
- Function signature
- Documentation (when available)
- Definition location

### P1: High Priority

#### 4. Find References

- All usages of a symbol
- Write vs read references
- Include/exclude definition

#### 5. Completions

- Keywords
- Local variables
- Struct fields after `.`
- Module members after `::`
- Function parameters

#### 6. Signature Help

- Parameter hints while typing
- Active parameter highlighting
- Overload selection (if applicable)

### P2: Medium Priority

#### 7. Rename

- Symbol rename across project
- Preview changes
- Validate new name

#### 8. Code Actions

- Quick fixes for common errors
- Auto-import suggestions
- Convert between literal styles

#### 9. Document Symbols

- Outline view
- Breadcrumbs
- Folding ranges

### P3: Nice to Have

#### 10. Semantic Highlighting

- Distinguish variable types
- Highlight mutable vs immutable
- Lifetime highlighting

#### 11. Inlay Hints

- Inferred types
- Parameter names
- Implicit conversions

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Editor                                │
│                  (VS Code, Neovim, etc.)                     │
└─────────────────────────────────────────────────────────────┘
                             │
                       JSON-RPC/stdio
                             │
┌─────────────────────────────────────────────────────────────┐
│                       ritz-lsp                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Protocol   │  │   Analysis   │  │    Cache     │       │
│  │   Handler    │  │    Engine    │  │   Manager    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                             │                                │
│                    ┌────────┴────────┐                       │
│                    ▼                 ▼                       │
│            ┌──────────────┐  ┌──────────────┐               │
│            │    Parser    │  │ Type Checker │               │
│            │  (from ritz0)│  │  (from ritz0)│               │
│            └──────────────┘  └──────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Options

#### Option A: Python (Reuse ritz0)

**Pros:**
- Reuse existing parser, type checker
- Faster development
- Single source of truth

**Cons:**
- Python startup overhead
- Memory usage
- Not self-hosting

#### Option B: Ritz (Native)

**Pros:**
- Dogfooding the language
- Better performance
- Path to self-hosting

**Cons:**
- Need to reimplement parser
- Blocked on ritz1 completion
- More development time

#### Recommendation

**Phase 1:** Python-based LSP using ritz0 components
**Phase 2:** Ritz native LSP (post-self-hosting)

---

## Protocol Support

### LSP Version

Target LSP 3.17 (latest stable).

### Required Capabilities

```json
{
  "textDocumentSync": "incremental",
  "hoverProvider": true,
  "completionProvider": {
    "triggerCharacters": [".", ":", "<"]
  },
  "definitionProvider": true,
  "referencesProvider": true,
  "documentSymbolProvider": true,
  "diagnosticProvider": {
    "interFileDependencies": true,
    "workspaceDiagnostics": true
  }
}
```

### File Watching

- Watch `*.ritz` files
- Watch `ritz.toml` for project config
- Invalidate on dependency changes

---

## Analysis Requirements

### Incremental Analysis

- Parse individual files on change
- Cache ASTs between requests
- Incremental type checking where possible

### Project Understanding

- Read `ritz.toml` for project structure
- Resolve import paths
- Handle multi-package workspaces

### Error Recovery

- Continue analysis after errors
- Provide partial results
- Graceful degradation

---

## Performance Targets

| Operation | Target Latency |
|-----------|----------------|
| Diagnostics (single file) | < 100ms |
| Go to definition | < 50ms |
| Completions | < 100ms |
| Hover | < 50ms |
| Find references (project) | < 500ms |

### Memory

- < 500MB for typical project
- Lazy loading for large projects
- Cache eviction for stale data

---

## Testing Strategy

### Unit Tests

- Parser edge cases
- Type inference scenarios
- Symbol resolution

### Integration Tests

- Full LSP request/response
- Multi-file projects
- Error scenarios

### Editor Tests

- VS Code extension E2E
- Neovim plugin E2E

---

## Deliverables

### Phase 1: MVP (4-6 weeks)

- [ ] Project skeleton with LSP framework
- [ ] Basic diagnostics (syntax errors)
- [ ] Go to definition (functions, variables)
- [ ] Hover (types)
- [ ] VS Code extension packaging

### Phase 2: Usable (4-6 weeks)

- [ ] Full diagnostics (type errors, ownership)
- [ ] Completions (keywords, locals, fields)
- [ ] Find references
- [ ] Document symbols

### Phase 3: Polish (4-6 weeks)

- [ ] Rename
- [ ] Signature help
- [ ] Code actions
- [ ] Semantic highlighting
- [ ] Inlay hints

---

## Editor Extensions

### VS Code

- Extension using `vscode-languageclient`
- Syntax highlighting via TextMate grammar
- Package on VS Code Marketplace

### Neovim

- Native LSP client configuration
- Tree-sitter grammar for highlighting
- Plugin distribution (lazy.nvim, packer)

### Emacs

- `lsp-mode` or `eglot` configuration
- `ritz-mode` for syntax highlighting

---

## Related Work

### Inspiration

- rust-analyzer (Rust)
- gopls (Go)
- pyright (Python)

### Ritz-Specific Considerations

- Indentation-based syntax (like Python)
- Ownership model (like Rust)
- Generic monomorphization
- Async transforms

---

## Open Questions

1. **Where should ritz-lsp live?**
   - In ritz repo as tool?
   - Separate ritz-lsp repo?
   - Recommendation: Separate repo, submodule in larb

2. **Python or Ritz for v1?**
   - Recommendation: Python to ship faster

3. **How to handle ritz0 vs ritz1 divergence?**
   - Share core analysis logic
   - Abstract over parser differences

4. **Tree-sitter grammar?**
   - Useful for Neovim and other editors
   - Could inform parser improvements
