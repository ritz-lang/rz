# ritz-lsp Development Roadmap

This document tracks the development progress of the Ritz Language Server.

## Phase 1: MVP (P0 Features)

Target: Basic IDE support with diagnostics and navigation.

### Infrastructure

- [ ] Project setup with build configuration
- [ ] LSP protocol layer (JSON-RPC over stdio)
- [ ] Document synchronization (open, change, close)
- [ ] Logging and debugging support
- [ ] Error handling framework

### Diagnostics

- [ ] Integrate with ritz0 parser for syntax errors
- [ ] Report parse errors with line/column positions
- [ ] Integrate with ritz0 type checker for type errors
- [ ] Report type mismatch errors
- [ ] Report undefined symbol errors
- [ ] Report ownership/borrow violations
- [ ] Report import resolution errors
- [ ] Incremental diagnostics on file change

### Go to Definition

- [ ] Function definitions
- [ ] Variable definitions
- [ ] Struct type definitions
- [ ] Enum type definitions
- [ ] Method definitions
- [ ] Field definitions
- [ ] Module/import navigation
- [ ] Cross-file navigation

### Hover Information

- [ ] Show type of expressions
- [ ] Show function signatures
- [ ] Show struct field types
- [ ] Show documentation comments
- [ ] Show definition location

### VS Code Extension (MVP)

- [ ] Basic extension skeleton
- [ ] Language configuration (comments, brackets)
- [ ] Syntax highlighting (TextMate grammar)
- [ ] Extension settings for server path
- [ ] Package extension for marketplace

---

## Phase 2: Usable (P1 Features)

Target: Productive editing experience with completions and search.

### Completions

- [ ] Keyword completions
- [ ] Local variable completions
- [ ] Function name completions
- [ ] Struct field completions (after `.`)
- [ ] Module member completions (after `::`)
- [ ] Enum variant completions
- [ ] Parameter name completions
- [ ] Completion item details (type, docs)
- [ ] Snippet completions for common patterns

### Find References

- [ ] Find all references to a symbol
- [ ] Distinguish read vs write references
- [ ] Include/exclude declaration
- [ ] Cross-file reference search
- [ ] Performance optimization for large projects

### Signature Help

- [ ] Show function parameter hints
- [ ] Highlight active parameter
- [ ] Trigger on `(` and `,`
- [ ] Support for generic functions
- [ ] Support for methods

### Document Symbols

- [ ] List all symbols in document
- [ ] Support for outline view
- [ ] Breadcrumb navigation
- [ ] Symbol kind icons

### Workspace Symbols

- [ ] Search symbols across workspace
- [ ] Fuzzy matching
- [ ] Symbol indexing
- [ ] Incremental index updates

---

## Phase 3: Polish (P2 Features)

Target: Professional-grade tooling with refactoring support.

### Rename

- [ ] Rename local variables
- [ ] Rename functions
- [ ] Rename types (structs, enums)
- [ ] Rename fields
- [ ] Rename methods
- [ ] Preview rename changes
- [ ] Validate new name
- [ ] Cross-file rename

### Code Actions

- [ ] Quick fix for import errors (add import)
- [ ] Quick fix for undefined variable (create variable)
- [ ] Extract variable refactoring
- [ ] Extract function refactoring
- [ ] Convert between literal styles
- [ ] Add type annotation
- [ ] Remove unused import

### Formatting

- [ ] Integrate with ritz fmt (when available)
- [ ] Format on save support
- [ ] Format selection
- [ ] Format on type (after `:`, etc.)

### Folding Ranges

- [ ] Function body folding
- [ ] Struct definition folding
- [ ] Import block folding
- [ ] Comment block folding
- [ ] Region folding

---

## Phase 4: Advanced (P3 Features)

Target: Best-in-class IDE experience.

### Semantic Highlighting

- [ ] Distinguish variable types (local, parameter, field)
- [ ] Highlight mutable vs immutable
- [ ] Highlight lifetime annotations
- [ ] Highlight type parameters
- [ ] Custom token types for Ritz

### Inlay Hints

- [ ] Inferred type hints
- [ ] Parameter name hints
- [ ] Lifetime hints
- [ ] Chained method type hints
- [ ] Configurable hint styles

### Call Hierarchy

- [ ] Incoming calls (who calls this)
- [ ] Outgoing calls (what this calls)
- [ ] Navigate call chains

### Type Hierarchy

- [ ] Trait implementations
- [ ] Supertypes/subtypes
- [ ] Navigate type relationships

### Code Lens

- [ ] Reference counts
- [ ] Test run buttons
- [ ] Implementation counts

---

## Integration Tasks

### Editor Extensions

#### VS Code (Primary)

- [ ] MVP extension with LSP support
- [ ] Syntax highlighting (TextMate grammar)
- [ ] Snippet definitions
- [ ] Debug adapter protocol integration
- [ ] Task integration (build, test)
- [ ] Publish to VS Code Marketplace

#### Neovim

- [ ] lspconfig entry for ritz-lsp
- [ ] Tree-sitter grammar
- [ ] Filetype detection
- [ ] Documentation for setup
- [ ] Plugin for lazy.nvim/packer

#### Emacs

- [ ] lsp-mode client configuration
- [ ] eglot configuration
- [ ] ritz-mode for syntax highlighting
- [ ] Documentation for setup

### Testing

- [ ] Unit tests for each handler
- [ ] Integration tests for LSP protocol
- [ ] Test fixtures for common scenarios
- [ ] Performance benchmarks
- [ ] Editor E2E tests

### Documentation

- [ ] User guide
- [ ] Editor setup guides
- [ ] Troubleshooting guide
- [ ] API documentation
- [ ] Contribution guide

---

## Technical Debt / Improvements

- [ ] Incremental parsing (avoid full re-parse)
- [ ] Persistent index (survive restarts)
- [ ] Memory optimization for large projects
- [ ] Parallel analysis
- [ ] Remote development support
- [ ] Multi-root workspace support

---

## Milestones

### v0.1.0 - MVP

- Diagnostics (syntax + type errors)
- Go to definition
- Hover
- VS Code extension

### v0.2.0 - Completions

- Code completions
- Signature help
- Document symbols

### v0.3.0 - References

- Find references
- Workspace symbols
- Rename

### v0.4.0 - Refactoring

- Code actions
- Formatting integration
- Quick fixes

### v1.0.0 - Stable

- All P0-P2 features complete
- Stable API
- Published editor extensions
- Comprehensive documentation
