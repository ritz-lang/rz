# RFC: Ritz Package Distribution Strategy

**Status:** Accepted
**Issue:** #107
**Author:** Aaron Sinclair, Adele
**Date:** 2026-02-12

---

## Executive Summary

This RFC proposes a packaging strategy for Ritz that prioritizes **source distribution with cached compilation**, avoiding traditional shared library complexity while maintaining small footprints and cross-platform portability.

---

## 1. Problem Statement

Ritz needs a distribution strategy that balances:

| Goal | Constraint |
|------|------------|
| Easy to read/audit | Source must be accessible |
| Easy to distribute | Single artifact, minimal deps |
| Small footprint | Don't ship redundant code |
| Code sharing | Libraries shouldn't duplicate |
| Cross-platform | Same package works everywhere |
| Fast execution | No JIT warmup for CLI tools |

### What We're NOT Doing

- **Traditional shared libraries (.so/.dylib)** - ABI versioning hell, platform-specific
- **Bytecode distribution** - Requires VM, loses optimization opportunities
- **Binary-only packages** - Opaque, platform-locked, hard to audit

---

## 2. Proposed Model: Source-First with Cached Compilation

### Core Principle

> **Source code is the artifact. Binaries are a cache.**

```
┌─────────────────────────────────────────────────────────────┐
│                     Package Contents                         │
├─────────────────────────────────────────────────────────────┤
│  ritz.toml          # Manifest                              │
│  src/               # Source code (REQUIRED)                │
│  README.md          # Documentation                         │
│  LICENSE            # License                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Local Build Cache                         │
│                   (~/.ritz/cache/)                          │
├─────────────────────────────────────────────────────────────┤
│  {content-hash}/                                            │
│    ├── x86_64-linux/bin/myapp                              │
│    ├── aarch64-linux/bin/myapp                             │
│    └── metadata.json                                        │
└─────────────────────────────────────────────────────────────┘
```

### How It Works

1. **Install**: Download/clone source package
2. **First Run**: Compile for local platform, cache result
3. **Subsequent Runs**: Use cached binary (instant)
4. **Source Changes**: Cache invalidated by content hash

### Content-Addressed Caching

Cache key = `hash(source_files + compiler_version + target_triple + optimization_level)`

```
~/.ritz/cache/
├── 7f3a8b2c/                    # Content hash
│   ├── metadata.json            # Build info, timestamps
│   ├── x86_64-linux-gnu/
│   │   └── bin/myapp
│   └── llvm-ir/
│       └── myapp.bc             # Optional: cached IR for LTO
└── 9e4d1f5a/
    └── ...
```

---

## 3. Use Cases

### 3.1 CLI Tools (Primary Use Case)

**Example:** `ritz install github.com/user/mytool`

```
1. Clone/download source to ~/.ritz/packages/mytool/
2. Read ritz.toml, resolve dependencies
3. Compile: source → LLVM IR → native binary
4. Cache binary at ~/.ritz/cache/{hash}/
5. Symlink ~/.ritz/bin/mytool → cached binary
```

**User experience:**
```bash
$ ritz install github.com/user/mytool
Installing mytool v1.2.0...
  Fetching source... done
  Compiling for x86_64-linux... done (2.3s)

$ mytool --version
mytool 1.2.0

$ # Second install on same machine (or different project)
$ ritz install github.com/user/mytool
Installing mytool v1.2.0...
  Using cached build (7f3a8b2c)
```

### 3.2 Libraries

Libraries are **always source**. No pre-compiled artifacts.

```toml
# mylib/ritz.toml
[package]
name = "mylib"
version = "1.0.0"
type = "lib"

[lib]
path = "src/lib.ritz"
```

When a program depends on `mylib`:
1. Source is fetched/vendored
2. Compiled together with the main program
3. LTO can optimize across library boundaries

**Benefits:**
- No ABI compatibility issues
- Dead code elimination works across libraries
- Single optimized binary output

### 3.3 Development Workflow

```bash
$ ritz new myproject
$ cd myproject

$ ritz build              # Compile, cache result
$ ritz run                # Run cached binary
$ ritz run --fresh        # Recompile (ignore cache)

$ vim src/main.ritz       # Edit source
$ ritz run                # Detects change, recompiles
```

### 3.4 Embedded / Resource-Constrained

For targets without a filesystem or with severe constraints:

```bash
$ ritz build --target thumbv7m-none-eabi --release
# Outputs: build/myapp.elf (static, no cache needed)
```

Embedded builds are **always static**, no caching indirection.

---

## 4. Dependency Resolution

### 4.1 Dependency Sources (URI-based)

```toml
[dependencies]
# Local path (for development)
mylib = { path = "../mylib" }

# HTTPS git
json = { uri = "https://github.com/ritz-lang/json" }
json = { uri = "https://github.com/ritz-lang/json", branch = "main" }
json = { uri = "https://github.com/ritz-lang/json", tag = "v1.0.0" }
json = { uri = "https://github.com/ritz-lang/json", rev = "abc123" }

# SSH git (private repos)
private = { uri = "git@github.com:org/private.git", tag = "v1.0" }

# Future: registry shorthand (if added)
# http = "1.2"  # Expands to ritz://http/1.2
```

### 4.2 Lock File

`ritz.lock` pins exact versions/commits:

```toml
# ritz.lock (auto-generated, commit to git)
[[package]]
name = "json"
source = "git+https://github.com/ritz-lang/json?rev=abc123def"
checksum = "sha256:..."

[[package]]
name = "http"
source = "git+https://github.com/ritz-lang/http?rev=def456abc"
checksum = "sha256:..."
```

### 4.3 Vendoring (Optional)

```bash
$ ritz vendor
# Copies all dependency sources to vendor/
# For offline builds or auditing
```

```
myproject/
├── ritz.toml
├── ritz.lock
├── src/
└── vendor/           # All deps, source only
    ├── json/
    └── http/
```

---

## 5. Cross-Platform Strategy

### 5.1 Supported Targets

| Tier | Target | Support Level |
|------|--------|---------------|
| 1 | x86_64-linux-gnu | Full, tested |
| 1 | aarch64-linux-gnu | Full, tested |
| 2 | x86_64-darwin | Full, CI tested |
| 2 | aarch64-darwin | Full, CI tested |
| 3 | x86_64-windows-msvc | Builds, limited testing |
| 3 | wasm32-unknown | Experimental |
| 3 | thumbv7m-none-eabi | Experimental (embedded) |

### 5.2 Cross-Compilation

```bash
$ ritz build --target aarch64-linux-gnu
# Uses LLVM's cross-compilation, needs appropriate linker
```

### 5.3 Platform-Specific Code

```ritz
# Conditional compilation
#[cfg(target_os = "linux")]
fn platform_specific() -> i32
    // Linux implementation

#[cfg(target_os = "darwin")]
fn platform_specific() -> i32
    // macOS implementation
```

---

## 6. Binary Cache Sharing (Future)

### 6.1 Local Cache

Default, always works:
```
~/.ritz/cache/
```

### 6.2 Shared Cache (CI/Team)

Optional, for build farms or teams:

```toml
# ~/.ritz/config.toml
[cache]
shared = "s3://company-ritz-cache/"
# or
shared = "https://cache.ritz-lang.org/"
```

Cache lookup:
1. Check local cache
2. Check shared cache (download if hit)
3. Build locally, upload to shared cache

**Security:** Only upload to trusted caches. Downloads verified by content hash.

---

## 7. Comparison with Other Languages

| Language | Distribution | Pros | Cons |
|----------|--------------|------|------|
| **Go** | Source → static binary | Simple, portable | Large binaries |
| **Rust** | Source → static binary | Same as Go | Slow builds |
| **Julia** | Source + precompile cache | Fast iteration | Warmup time |
| **Python** | Source + .pyc cache | Simple | Runtime overhead |
| **C/C++** | Headers + .so/.a | Flexible | ABI hell, complex |
| **Ritz (proposed)** | Source + native cache | Portable, fast, auditable | Needs toolchain |

---

## 8. Decisions (Resolved)

### Q1: Package Registry and Dependency Sources

**Decision:** URI-based dependency resolution (no central registry)

Dependencies are specified as URIs supporting multiple schemes:
- `file://` or relative paths - local filesystem
- `https://` - remote git repositories
- `git+ssh://` or `git@` - SSH git access
- Future: `ritz://` for optional registry lookup

```toml
[dependencies]
# Local path (development)
mylib = { path = "../mylib" }

# HTTPS git
json = { uri = "https://github.com/ritz-lang/json", tag = "v1.0" }

# SSH git
private = { uri = "git@gitlab.com:org/private.git", branch = "main" }
```

**Rationale:** URIs are universal, flexible, and don't require central infrastructure. A registry can be added later as syntactic sugar.

### Q2: C Interop Philosophy

**Decision:** Ritz-native approach; C interop is escape hatch only

- `ritzlib` should be pure Ritz (syscalls via inline assembly)
- Use `c"string literals"` for C-compatible null-terminated strings
- FFI is available but discouraged for new code
- Goal: Ritz should be suitable for everything, not dependent on C

```ritz
# Preferred: native Ritz
let msg = "Hello"          # Ritz string (ptr + len)

# When calling C: explicit conversion
let c_msg = c"Hello\0"     # C string (null-terminated)
```

**Rationale:** Languages that lean on C ecosystem inherit C's problems. Ritz should stand alone.

### Q3: Binary Distribution Strategy

**Decision:** Hybrid approach - both pre-built binaries AND source flexibility

For releases:
1. **Pre-built binaries** for common platforms (Tier 1/2 targets)
2. **LLVM IR** for portable compilation without full toolchain
3. **Source** always included and authoritative

Install behavior:
- `ritz install <uri>` - fetches source, compiles locally, caches globally
- `ritz install <uri> --binary` - prefer pre-built if available
- Pre-built binaries are convenience, not requirement

```
Release artifact structure:
  mytool-v1.0.0/
  ├── src/                    # Source (always present)
  ├── ritz.toml
  ├── bin/                    # Pre-built binaries (optional)
  │   ├── x86_64-linux/mytool
  │   └── aarch64-darwin/mytool
  └── ir/                     # LLVM IR (optional)
      └── mytool.bc
```

**Rationale:** Pre-built binaries enable quick adoption; source ensures auditability and portability.

### Q4: Compiler Distribution (ritz1)

**Decision:** Ship ritz1 as binary + LLVM IR; deprecate Python bootstrapper

Distribution package:
```
ritz-compiler-v1.0.0/
├── bin/
│   ├── x86_64-linux/ritz1      # Native binary
│   └── aarch64-darwin/ritz1
├── ir/
│   └── ritz1.bc                # LLVM IR (compile with: llc + clang)
└── src/                        # Source (for auditing/rebuilding)
    └── ...
```

Bootstrap chain:
1. Download ritz1 binary (or compile from IR)
2. ritz1 can compile itself (self-hosting verified)
3. ritz0 (Python) retained only for historical/emergency bootstrap

**Rationale:** Python bootstrapper is slow and has different behavior. LLVM IR provides portable fallback without Python dependency.

---

## 9. Implementation Phases

### Phase 1: Foundation (Current)
- [x] `ritz build` compiles packages
- [x] `ritz.toml` manifest format
- [ ] Basic local caching (content-addressed)
- [ ] `ritz install` from git URL

### Phase 2: Dependencies
- [ ] `[dependencies]` in ritz.toml
- [ ] `ritz.lock` file generation
- [ ] Dependency resolution algorithm
- [ ] `ritz vendor` command

### Phase 3: Polish
- [ ] Cross-compilation support
- [ ] Shared cache support
- [ ] `ritz publish` (if we add a registry)
- [ ] Binary release artifacts

---

## 10. Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary artifact | Source | Auditable, portable, no ABI issues |
| Caching strategy | Content-addressed | Reproducible, shareable |
| Library linking | Static (compile together) | LTO, dead code elim, simplicity |
| Dependency source | URIs (path, git, ssh) | Universal, no central infra needed |
| C interop | Escape hatch only | Ritz should stand alone |
| Binary releases | Hybrid (binary + IR + source) | Quick adoption + auditability |
| Compiler shipping | Binary + LLVM IR | Fast install, portable fallback |

---

## Appendix A: ritz.toml Full Specification

```toml
[package]
name = "mypackage"
version = "1.0.0"
authors = ["Name <email>"]
edition = "2024"
description = "Short description"
repository = "https://github.com/..."
license = "MIT"
keywords = ["cli", "utility"]

# Binary targets
[[bin]]
name = "myapp"
path = "src/main.ritz"

[[bin]]
name = "helper"
path = "src/helper.ritz"

# Library (optional)
[lib]
name = "mylib"
path = "src/lib.ritz"

# Dependencies (URI-based)
[dependencies]
otherlib = { uri = "https://github.com/user/otherlib", tag = "v1.0" }
locallib = { path = "../locallib" }
private = { uri = "git@gitlab.com:org/private.git", branch = "main" }

# Dev dependencies (tests, benchmarks)
[dev-dependencies]
testutil = { uri = "https://github.com/ritz-lang/testutil" }

# Build configuration
[build]
# Default optimization level
opt-level = 2

# Platform-specific settings
[target.x86_64-linux-gnu]
# Linux-specific options

[target.aarch64-darwin]
# macOS ARM-specific options
```

---

## Appendix B: Cache Directory Structure

```
~/.ritz/
├── config.toml              # User configuration
├── bin/                     # Symlinks to installed tools
│   ├── mytool → ../cache/7f3a8b2c/x86_64-linux/bin/mytool
│   └── othertool → ...
├── cache/                   # Build cache (content-addressed)
│   ├── 7f3a8b2c/
│   │   ├── metadata.json
│   │   └── x86_64-linux/
│   │       └── bin/mytool
│   └── 9e4d1f5a/
│       └── ...
├── packages/                # Installed package sources
│   ├── mytool/
│   │   ├── ritz.toml
│   │   └── src/
│   └── othertool/
│       └── ...
└── registry/                # Registry index cache (future)
    └── ...
```

---

**Next Steps:**
1. ~~Review this RFC~~ ✓
2. ~~Make decisions on open questions~~ ✓
3. Implement Phase 1 (local caching, `ritz install` from URI)
4. Iterate based on real-world usage
