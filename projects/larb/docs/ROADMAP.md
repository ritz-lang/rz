# Ritz Ecosystem Roadmap

## Open Issues & Priorities

### Critical Path: Self-Hosting Compiler

The primary goal is achieving a **self-hosting Ritz compiler** (ritz1 compiles itself).

| Issue | Description | Status | Blocker |
|-------|-------------|--------|---------|
| #72 | Complete ritz1 bootstrap | Open | Monomorphization |
| - | ritz1 monomorphization | Blocked | Core blocker |
| #62 | Compiler pipeline diagrams | Open | Documentation |
| #60 | Improve compiler diagnostics | Open | Quality of life |
| #71 | Standardize 4-space indentation | Open | Code quality |

### Open Feature Requests

| Issue | Description | Priority | Effort |
|-------|-------------|----------|--------|
| #107 | RFC: Package Distribution & Shared Libraries | High | Large |
| #101 | Compile-time function evaluation (comptime) | Medium | Large |
| #100 | RFC: Parameterized Tests | Medium | Medium |
| #95 | Const struct literals at module level | Low | Small |

---

## Phase Priorities

### Phase 1: Self-Hosting (Highest Priority)

**Goal:** ritz1 can compile itself

1. **Fix ritz1 monomorphization** - Generic instantiation in self-hosted compiler
2. **Complete type checker in ritz1** - Full type inference and checking
3. **Bootstrap validation** - 4-stage regression test (ritz0 → ritz1 → ritz1' → diff)

**Acceptance Criteria:**
- ritz1 compiles ritz1 producing identical output
- All 324 language tests pass with ritz1-compiled ritz1
- Performance within 2x of ritz0

### Phase 2: LSP Server (High Priority)

**Goal:** Language server for IDE support

See [LSP_REQUIREMENTS.md](LSP_REQUIREMENTS.md) for full specification.

Key features:
- Go to definition
- Find references
- Hover information
- Completions
- Diagnostics
- Rename

### Phase 3: Package Ecosystem (Medium Priority)

**Goal:** Robust dependency management

1. **RFC #107 Phase 3:** Shared library support (.so/.dylib)
2. **Central registry:** Package discovery and versioning
3. **Build caching:** Content-addressed remote cache

### Phase 4: Tooling (Medium Priority)

**Goal:** Developer productivity

1. **Formatter:** Automatic code formatting (`ritz fmt`)
2. **Documentation generator:** API docs from source
3. **Debugger integration:** DWARF debug info (#51)

### Phase 5: Performance (Lower Priority)

**Goal:** Production-ready performance

1. **Incremental compilation:** Only recompile changed modules
2. **Parallel compilation:** Multi-threaded module compilation
3. **Better codegen:** LLVM optimization tuning

---

## Recently Completed

### February 2026

- ✅ RFC #107 Phase 2: Lock files and vendoring
- ✅ RFC #107 Phase 1: Global install system
- ✅ Build System Phase 3: LLVM BC caching (3.4x speedup)
- ✅ #112: Add pub to all ritzlib public functions
- ✅ #111: Non-pub functions get internal linkage
- ✅ #110: Fix debug info crash with IntLit array sizes
- ✅ #109: Build system with ritz.toml
- ✅ #108: AVX2 256-bit SIMD support
- ✅ #106: BitOps intrinsics for primitive types
- ✅ #105: Const expressions in array size
- ✅ #104: @inline attribute
- ✅ #103: static_assert
- ✅ #102: SIMD types and intrinsics
- ✅ #99: Qualified import resolution
- ✅ #98: Struct array member comparison fix
- ✅ #97: Bit manipulation trait methods

### January 2026

- ✅ Testing framework integration (ritzunit)
- ✅ External runtime linking
- ✅ Examples reorganization (5 tiers)
- ✅ Grammar-driven parser
- ✅ Native string literals
- ✅ Async/await improvements
- ✅ Phase 14: Process library
- ✅ Phase 12: Valet HTTP server (1.47M req/sec)

---

## Project-Specific Roadmaps

### Ritz Compiler

| Priority | Task | Issue |
|----------|------|-------|
| P0 | ritz1 monomorphization | #72 |
| P0 | ritz1 type checker | #72 |
| P1 | Improved diagnostics | #60 |
| P1 | DWARF debug info | #51 |
| P2 | Comptime evaluation | #101 |

### Ritzunit

| Priority | Task |
|----------|------|
| P1 | Filter expressions (glob patterns) |
| P1 | Attribute filters (@ignore, @slow) |
| P2 | Parallel test execution |
| P2 | JUnit XML output |

### Squeeze

| Priority | Task |
|----------|------|
| P1 | Dynamic Huffman encoding |
| P2 | Lazy matching |
| P2 | Runtime CPU detection |

### Valet

| Priority | Task |
|----------|------|
| P0 | TLS 1.3 handshake |
| P1 | HTTP/2 support |
| P2 | WebSocket support |

### Cryptosec

| Priority | Task |
|----------|------|
| P0 | TLS 1.3 handshake state machine |
| P1 | Certificate chain validation polish |
| P2 | AES-NI acceleration |

---

## New Project: LSP Server

A new project `ritz-lsp` should be created to provide IDE support.

See [LSP_REQUIREMENTS.md](LSP_REQUIREMENTS.md) for detailed requirements.

**Initial Scope:**
- Diagnostics (errors, warnings)
- Go to definition
- Hover for type information
- Basic completions

---

## Contribution Guidelines

### For LARB

- Design discussions in GitHub Issues
- RFCs for significant changes
- Update specs when features land

### For Code Projects

- Follow TDD methodology
- Add tests before implementation
- Update project TODO.md/DONE.md
- Use conventional commit messages

### Commit Message Format

```
<project>: <emoji> <description>

* Details if needed
```

Emojis:
- 🤖 AI-assisted
- 🐛 Bug fix
- ✨ New feature
- 📝 Documentation
- ♻️ Refactor
