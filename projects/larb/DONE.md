# LARB Completed Work

## 2026-02-13: Initial Setup

### Repository Structure
- Created larb repository for Ritz ecosystem coordination
- Established directory structure:
  - `docs/` - Primary documentation
  - `specs/rfcs/` - Formal specifications
  - `projects/` - Git submodules
  - `logs/` - Session logs

### Git Submodules
- Added all five ecosystem projects as submodules:
  - `projects/ritz` - Core compiler and standard library
  - `projects/ritzunit` - Unit testing framework
  - `projects/squeeze` - Compression library (gzip/deflate)
  - `projects/valet` - HTTP/1.1 server
  - `projects/cryptosec` - Cryptographic primitives

### Documentation
- **README.md** - Project overview and quick links
- **docs/QUICK_REFERENCE.md** - Agent-optimized language summary (~150 lines)
- **docs/ECOSYSTEM.md** - All five projects explained with architecture diagram
- **docs/ROADMAP.md** - Open issues, priorities, and completed work
- **docs/LSP_REQUIREMENTS.md** - Full LSP server specification
- **docs/LANGUAGE_SPEC.md** - Complete language specification (~800 lines)

### Research Completed
Comprehensive analysis of all Ritz ecosystem projects:

| Project | Tests | Lines | Key Achievement |
|---------|-------|-------|-----------------|
| ritz | 324+201 | ~50k | Grammar-driven parser |
| ritzunit | Self-testing | ~1.5k | ELF self-discovery |
| squeeze | 132 | ~10k | SIMD acceleration |
| valet | 85 | ~5k | 1.47M req/sec |
| cryptosec | 331 | ~19k | TLS 1.3 foundation |
| **Total** | **~1,073** | **~85k** | |

### Open Issues Identified
- **#72**: ritz1 bootstrap (blocked on monomorphization)
- **#107**: RFC: Package Distribution (Phase 3 pending)
- **#101**: Comptime evaluation
- **#100**: Parameterized tests RFC
- **#95**: Const struct literals

### Key Decisions
1. LARB will version standards via git tags
2. All projects use submodules for coordination
3. LSP server will be Python-based initially (reusing ritz0)
4. Quick reference prioritizes minimal context for agents

## 2026-02-13: Language Review Complete

### Documents Created
- **docs/LANGUAGE_REVIEW.md** - Comprehensive usability, security, and aesthetics review
- **docs/SYNTAX_PROPOSALS.md** - Address-of, ownership, and borrowing syntax proposals
- **docs/DESIGN_DECISIONS.md** - Finalized language design decisions

### Major Design Decisions Finalized

#### Ownership & Borrowing (Colon-Modifier Syntax)
| Syntax | Meaning | Frequency |
|--------|---------|-----------|
| `x: T` | Const borrow (or copy for primitives) | ~70% |
| `x:& T` | Mutable borrow | ~20% |
| `x:= T` | Move ownership | ~10% |

**Key insight:** Clean call sites — no `&x` or `&mut x` at call sites, function signature tells the whole story.

#### Address-Of & Reference Types
- `@` for address-of ("at" mnemonic)
- `@T` for immutable reference
- `@&T` for mutable reference
- `[[attr]]` for attributes (frees `@`)

#### String System
- `StrView` as default literal type (zero-copy)
- `String.from()` for heap allocation
- Drop `c""` and `s""` prefixes
- Add `.as_cstr()` for FFI

### Features Identified from Mausoleum Review
Critical gaps surfaced from real-world database engine development:

1. **`sizeof(T)`** — Compile-time size of type/struct
2. **`alignof(T)`** — Compile-time alignment
3. **Computed range bounds** — `for i in start..end` with variable bounds
4. **`defer`** — RAII-style cleanup without explicit drop impls
5. **`loop` keyword** — Infinite loop (documented but not in grammar)

### Safety Defaults Established
- Integer overflow: panic in debug, wrap with explicit `wrapping_add()`
- Array init: require `zeroed()` or explicit `uninit()`
- Match: exhaustive by default

### Sexiness Rating
Before review: 7/10 → Target: 9/10

With finalized design decisions, Ritz achieves the target through:
- Clean call sites (no `&x` annotations)
- Minimal ceremony for common case (`:` for const borrow)
- Zero-copy strings by default
- `@` address-of mnemonic
- Consistent `&` = mutable throughout

## 2026-02-14: Architectural Review (ChatGPT PR + Self-Review)

### PR #1 Analysis

Analyzed ChatGPT's LARB architectural review. Findings:

**Good insights (accepted):**
- Zeus/Valet boundary: Routing and middleware should be in Zeus, not Valet
- M7SP protocol needs versioning
- Transaction isolation guarantees need documentation
- Repository abstractions shouldn't assume Mausoleum

**Nonsense (ignored):**
- "Goliath" architecture — doesn't exist
- "Formalized audit documentation" — vague platitude
- "Fuzzing harness specification" — premature (TLS not done)

### Stack Health Assessment

| Stack | Health | Key Issue |
|-------|--------|-----------|
| **Foundation** (ritz, ritzunit, cryptosec, squeeze) | 🟢 Strong | ritz1 monomorphization blocks self-host |
| **Web** (valet, zeus, mausoleum, tome, spire) | 🟡 Mixed | Valet overloaded with routing/middleware |
| **System** (harland) | 🟡 Active | Syscall versioning needed |

### Zeus/Valet Boundary Defined

```
SPIRE (MVRSPT framework)
    ↓
ZEUS (routing, middleware, process mgmt, sessions)
    ↓
VALET (HTTP transport, io_uring, TLS, keep-alive)
```

**Decision:** Move routing and middleware from Valet to Zeus.

### Documentation Audit

| Action | Files |
|--------|-------|
| **Update syntax** | AGENT.md, LANGUAGE_SPEC.md, QUICK_REFERENCE.md, GRAMMAR_SPEC.md |
| **Archive** | LANGUAGE_REVIEW.md, SYNTAX_PROPOSALS.md (superseded by DESIGN_DECISIONS) |
| **Keep** | All others |

**Critical finding:** ritz/AGENT.md uses outdated syntax (`@test`, `c""` prefixes), causing agents to write bad code. Must update to finalized syntax.

### ritz/AGENT.md Updated (PR #128)

Fixed AGENT.md to use finalized syntax:
- `[[test]]` instead of `@test`
- `"string"` (StrView) instead of `c"string"`
- Documented `String.from()` and `.as_cstr()` patterns

## 2026-02-14: ritz-lint Created

### AI-Powered Code Linter

Created `tools/ritz-lint/` — an AI-powered linter using Claude Haiku to catch "C developer code in Ritz clothing".

**Anti-patterns detected:**
| Anti-Pattern | Idiomatic Ritz |
|--------------|----------------|
| `fn foo(x: *T)` | `fn foo(x: T)` (const borrow) |
| `fn foo(x: *mut T)` | `fn foo(x:& T)` (mutable borrow) |
| `c"string"` | `"string"` (StrView default) |
| `@test` | `[[test]]` |
| `&&` / `\|\|` / `!` | `and` / `or` / `not` |
| `if ptr != null` | `match opt { Some(x) => ... }` |
| Missing `defer` | Resource cleanup with `defer` |
| Excessive `var` | Prefer `let` (immutable by default) |

**Usage:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python tools/ritz-lint/ritz_lint.py src/
```

### Logical Operators Decision Reversed

Changed DESIGN_DECISIONS.md section 6.1:
- **Old:** Use `&&`, `||`, `!` (C-style)
- **New:** Use `and`, `or`, `not` (Python-style)

**Rationale:** Ritz prioritizes readability over brevity. Keywords read like prose, symbols read like line noise.

## 2026-02-14: Ecosystem AGENT.md & Flat Structure

### Authoritative AGENT.md Created

Created `/home/aaron/dev/ritz-lang/larb/AGENT.md` — the authoritative agent prompt for the entire Ritz ecosystem.

**Key additions over ritz/AGENT.md:**

1. **No Concessions Doctrine** — Emphasized as foundational principle with clear guidance
2. **Idiomatic Ritz Anti-Patterns** — Comprehensive table with bad patterns and good alternatives
3. **Flat Ecosystem Structure** — RITZ_PATH approach instead of nested submodules
4. **Contributing Upstream Workflow** — Step-by-step guide for PRs to any ritz-lang project
5. **Ownership Modifiers** — Clear documentation of `:`, `:&`, `:=` syntax with frequencies
6. **Clean Call Sites** — Explicit that Ritz has no `&x` or `&mut x` at call sites

### Flat Ecosystem Decision

**Problem:** Submodules create nested dependency nightmares:
```
your-app/
├── ritz/                    # Your copy
├── squeeze/
│   └── ritz/                # Squeeze's copy (duplicate!)
├── valet/
│   ├── ritz/                # Valet's copy (duplicate!)
│   └── squeeze/
│       └── ritz/            # Triple nested!
```

**Solution:** Flat siblings with RITZ_PATH:
```bash
export RITZ_PATH=~/dev/ritz-lang
```

All projects live as siblings:
```
~/dev/ritz-lang/
├── ritz/
├── ritzunit/
├── squeeze/
├── cryptosec/
├── valet/
├── zeus/
├── mausoleum/
├── tome/
├── spire/
├── harland/
├── larb/
└── your-app/
```

Any project can import from any other:
```ritz
import ritzlib.sys           # From ritz/ritzlib/
import squeeze.gzip          # From squeeze/src/
import cryptosec.sha256      # From cryptosec/src/
```

### ritz-lint Updated

Enhanced system prompt with No Concessions doctrine and ownership frequency table:

| Syntax | Meaning | Frequency |
|--------|---------|-----------|
| `x: T` | Const borrow | ~70% |
| `x:& T` | Mutable borrow | ~20% |
| `x:= T` | Move ownership | ~10% |
| `*T` | Raw pointer (FFI only) | <1% |

### Purist Mode & PR Checklist

Made the linter intentionally harsh — it's a purist that treats C-style code as errors, not suggestions.

**New files:**
- `tools/ritz-lint/install-hook.sh` — Pre-commit hook installer
- `docs/PR_CHECKLIST.md` — The Three Gates: Tests, Valgrind, Lint

**The Three Gates (PR Readiness):**
1. `make test` — All tests pass
2. `make valgrind` — Zero leaks, zero errors
3. `ritz-lint src/` — No C-style code

Updated linter personality to be a "purist" that escalates C-style patterns to errors.
