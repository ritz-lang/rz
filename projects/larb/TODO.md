# LARB TODO

## Phase 1: Foundation (Complete)

- [x] Create repository structure
- [x] Add all ecosystem projects as submodules
- [x] Write language quick reference
- [x] Write ecosystem overview
- [x] Write roadmap document
- [x] Write LSP requirements
- [x] Write full language specification

## Phase 2: Language Review (Complete)

LARB's core mission: Make Ritz sexy and safe.

- [x] Usability review (ergonomics, learnability)
- [x] Security review (footguns, memory safety gaps)
- [x] Syntax polish (consistency, aesthetics)
- [x] Identify optimization opportunities
- [x] String system redesign proposal
- [x] Pointer vs reference philosophy
- [x] Async/await deep-dive and audit
- [x] Create DESIGN_DECISIONS.md (finalized language design)

## Phase 3: Compiler Features (From Mausoleum Review)

Critical features surfaced from real-world database engine development:

### 3.1 Core Operators (High Priority)

- [ ] `sizeof(T)` — Compile-time size of type/struct
- [ ] `alignof(T)` — Compile-time alignment of type
- [ ] Computed range bounds (`for i in start..end` where start/end are variables)

### 3.2 Resource Management (High Priority)

- [ ] `defer` statement — RAII-style cleanup without explicit drop impls
- [ ] `defer` stacking (LIFO execution order)

### 3.3 Syntax Migration (Medium Priority)

- [ ] `@` for address-of (replaces `&`)
- [ ] `[[attr]]` for attributes (frees `@`)
- [ ] Colon-modifier syntax (`:`, `:&`, `:=` for param passing)
- [ ] `@T` / `@&T` for reference types

### 3.4 Type System (Medium Priority)

- [ ] Bare enum variants (`Some(x)` instead of `Option::Some(x)`)
- [ ] Methods on primitives (`42.to_string()`)
- [ ] `loop` keyword (infinite loop)

### 3.5 Safety Defaults (Medium Priority)

- [ ] Integer overflow panic in debug mode
- [ ] `wrapping_add()`, `saturating_add()`, `checked_add()` methods
- [ ] `zeroed()` and `uninit()` for array initialization
- [ ] Exhaustive match enforcement

### 3.6 String System Migration

- [ ] `StrView` as default string literal type
- [ ] `String.from()` for heap allocation
- [ ] `StringBuilder` in stdlib
- [ ] Remove `c""` and `s""` prefixes
- [ ] Add `.as_cstr()` for FFI

## Phase 4: Standards Documentation

- [ ] Document all ritzlib modules
- [x] Create grammar specification (formal)
- [ ] Document error codes and diagnostics
- [x] Create coding style guide (STYLE.md)
- [ ] Add architecture decision records (ADRs)
- [ ] Error message quality review

### 4.1 Documentation Sync (From February Review)

Update all docs to finalized syntax (prevents agents writing bad code):

- [x] **ritz/AGENT.md** — Update to `[[test]]`, remove `c""` prefixes, use StrView default (PR #128)
- [ ] **larb/docs/LANGUAGE_SPEC.md** — Update `@test` → `[[test]]`, keep `and`/`or`/`not`
- [ ] **larb/docs/QUICK_REFERENCE.md** — Same syntax updates
- [ ] **larb/docs/GRAMMAR_SPEC.md** — Update attribute syntax to `[[attr]]`
- [ ] Archive superseded docs (LANGUAGE_REVIEW.md, SYNTAX_PROPOSALS.md)

### 4.2 Architecture Documentation (From ChatGPT Review)

- [ ] **Zeus/Valet boundary** — Document that routing/middleware belong in Zeus, not Valet
- [ ] **M7SP protocol versioning** — Add version field to Mausoleum binary protocol
- [ ] **Transaction isolation spec** — Document MVCC guarantees in Mausoleum
- [ ] **Harland syscall versioning** — Version kernel/userland interface

## Phase 5: LSP Server

- [ ] Create ritz-lsp repository
- [ ] Implement diagnostics (syntax errors)
- [ ] Implement go-to-definition
- [ ] Implement hover information
- [ ] Package VS Code extension
- [ ] Package Neovim plugin

## Phase 6: Self-Hosting

- [ ] Track ritz1 monomorphization progress
- [ ] Track ritz1 type checker progress
- [ ] Document bootstrap process
- [ ] Create 4-stage validation test

## Phase 7: Code Quality Tools

- [x] `ritz-lint` — AI-powered purist linter using Claude (`tools/ritz-lint/`)
- [x] `AGENT.md` — Authoritative ecosystem agent prompt with No Concessions doctrine
- [x] Pre-commit hook (`tools/ritz-lint/install-hook.sh`)
- [x] PR Readiness Checklist (`docs/PR_CHECKLIST.md`)
- [ ] GitHub Action for automated PR reviews
- [ ] LSP lint integration (future)

## Future

- [ ] Tree-sitter grammar
- [ ] Formatter specification
- [ ] Documentation generator spec
- [ ] Package registry design
