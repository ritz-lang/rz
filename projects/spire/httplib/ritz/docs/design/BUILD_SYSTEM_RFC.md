# RFC: Build System and Compilation Units

**Status:** Accepted
**Issue:** #109
**Author:** Aaron Sinclair, Adele
**Date:** 2026-02-12

---

## Executive Summary

This RFC defines how `ritz.toml` specifies compilation units, linkage, and dependency namespacing. The goal is to replace ad-hoc build scripts with a standardized `ritz build` that works for any project structure.

### Guiding Principles

1. **Source is truth** - All Ritz code is source; precompiled artifacts are cache/optimization
2. **Intuitive mapping** - `import foo.bar` maps to `foo/bar.ritz` on disk
3. **Layered dependencies** - Support deep dependency DAGs (ritz → ritzunit → squeeze → valet)
4. **In-tree and out-of-tree** - Dependencies can be submodules, siblings, or remote
5. **Safe compilation** - No silent symbol collisions; explicit namespacing

---

## 1. Problem Statement

### Current State

Projects use manual build scripts with hardcoded paths:

```bash
# valet/build.sh - hardcoded everything
export RITZ_PATH=$VALET:$VALET/squeeze:$RITZ
python3 $RITZ/ritz0/ritz0.py $VALET/src/main.ritz -o $OUT.ll
```

This doesn't scale because:

| Problem | Impact |
|---------|--------|
| **Hardcoded paths** | Each project needs custom scripts |
| **No multiple targets** | Can't build server + CLI from same source |
| **Namespace collisions** | `import lib.gzip` ambiguous when submodules have `lib/` |
| **RITZ_PATH ordering** | First match wins, no warnings |
| **No library support** | Can't produce reusable `.a` or object files |

### Real Example: Valet + Squeeze

```
valet/
├── src/main.ritz           # Main server
├── lib/                    # Valet's own library code
├── squeeze/                # Git submodule
│   └── lib/                # Squeeze's library (gzip, deflate, etc.)
└── lib_squeeze -> squeeze/lib  # Symlink workaround!
```

To avoid `import lib.gzip` (Valet's lib?) vs `import lib.gzip` (Squeeze's lib?), the workaround is:
- Symlink: `lib_squeeze -> squeeze/lib`
- Import: `import lib_squeeze.gzip`

This is fragile and requires tribal knowledge.

---

## 2. Proposed Solution

### 2.1 Compilation Model

Ritz uses a **merged-module compilation model**:

```
┌─────────────────────────────────────────────────────────────┐
│                    Compilation Unit                          │
│                                                              │
│  main.ritz ──┐                                              │
│              │                                              │
│  lib/a.ritz ─┼──▶ ImportResolver ──▶ Merged AST ──▶ .ll    │
│              │                                              │
│  lib/b.ritz ─┘                                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

Each `[[bin]]` or `[lib]` target produces ONE compilation unit:
1. **Entry point** - The file specified in `path`
2. **Transitive imports** - All files reachable via `import`
3. **Merged module** - Single AST with all functions
4. **Output** - One `.ll` file (and optionally `.o` or binary)

### 2.2 Source Discovery

Source files are discovered based on the `sources` configuration:

```toml
[package]
name = "myapp"

# Source roots - directories or glob patterns
# Directory = shorthand for "dir/**/*.ritz"
sources = ["src"]                    # All .ritz files under src/
sources = ["src", "lib"]             # Multiple directories
sources = ["src/**/*.ritz"]          # Explicit glob (equivalent to "src")
sources = ["src/*.ritz"]             # Only top-level, no subdirs
sources = ["src", "!src/generated"]  # Exclude patterns with !
```

**Default behavior:**
- If `sources` not specified: `["src"]` if `src/` exists, else `["."]`
- Directory entries expand to `dir/**/*.ritz`
- Exclusion patterns start with `!`

### 2.3 ritz.toml Specification

```toml
[package]
name = "valet"
version = "0.1.0"

# Source roots (see §2.2)
sources = ["src"]

# ============================================================
# Binary Targets
# ============================================================
# Each [[bin]] produces one executable

[[bin]]
name = "valet"              # Output binary name
entry = "main::main"        # Module path to entry function
# Resolves: src/main.ritz, fn main()

[[bin]]
name = "valet-cli"
entry = "cli::main"         # src/cli.ritz, fn main()

# Alternative: file path (for compatibility)
# [[bin]]
# name = "valet"
# path = "src/main.ritz"   # Direct file path still supported

# ============================================================
# Library Target (Optional)
# ============================================================
# A library is code intended for reuse by other packages
# It has NO main function - just exported definitions

[lib]
name = "valet"
entry = "lib"               # Module that re-exports pub API
# Or: path = "src/lib.ritz" for direct file reference

# ============================================================
# Dependencies
# ============================================================
# Dependencies get their own namespace to avoid collisions

[dependencies]
# Local path dependency (for development or submodules)
squeeze = { path = "squeeze" }

# Git dependency (future - per RFC #107)
# http = { uri = "https://github.com/ritz-lang/http", tag = "v1.0" }

# ============================================================
# Build Configuration
# ============================================================

[build]
# Optimization level: 0 (none), 1 (basic), 2 (default), 3 (aggressive)
opt-level = 2

# Include debug info (DWARF)
debug = true

# Link-time optimization
lto = false

# ============================================================
# Profiles (optional override of [build])
# ============================================================

[profile.debug]
opt-level = 0
debug = true

[profile.release]
opt-level = 3
debug = false
lto = true
```

### 2.4 Entry Point Resolution

Entry points use import-style syntax: `module::function`

```toml
[[bin]]
name = "server"
entry = "server::main"      # src/server.ritz, fn main()

[[bin]]
name = "tools-cli"
entry = "tools.cli::main"   # src/tools/cli.ritz, fn main()
```

**Resolution algorithm:**
1. Parse `entry = "path.to.module::function"`
2. Convert module path to file: `path/to/module.ritz`
3. Search in `sources` directories
4. Find function with matching name

**Examples:**
| Entry | Sources | Resolves To |
|-------|---------|-------------|
| `main::main` | `["src"]` | `src/main.ritz`, `fn main()` |
| `server::main` | `["src"]` | `src/server.ritz`, `fn main()` |
| `http.server::run` | `["src"]` | `src/http/server.ritz`, `fn run()` |
| `app::main` | `["src", "lib"]` | First match in `src/app.ritz` or `lib/app.ritz` |

**Fallback:** `path = "file.ritz"` is still supported for simple cases or compatibility.

### 2.6 Dependency Namespacing

When you declare a dependency:

```toml
[dependencies]
squeeze = { path = "squeeze" }
```

The dependency's exports become available under its namespace:

```ritz
# In valet code:
import squeeze.gzip           # Resolves to squeeze/lib/gzip.ritz
import squeeze.deflate        # Resolves to squeeze/lib/deflate.ritz

# NOT ambiguous with local lib:
import lib.http               # Resolves to valet/lib/http.ritz
```

**Resolution algorithm:**

1. `import foo.bar.baz`
2. Check if `foo` is a declared dependency name
3. If yes: resolve `bar.baz` within that dependency's root
4. If no: resolve `foo.bar.baz` relative to current package root

### 2.7 Library Entry Points

A library package defines its public API through a `lib.ritz` entry point:

```ritz
# squeeze/lib/lib.ritz - Library entry point

# Re-export public modules
pub import lib.gzip
pub import lib.deflate
pub import lib.crc32

# Or re-export specific items
pub import lib.gzip { compress, decompress }
```

When another package depends on `squeeze`:

```ritz
# In valet:
import squeeze                    # Gets all pub exports from squeeze/lib/lib.ritz
import squeeze { compress }       # Selective import
import squeeze.gzip               # Direct module access
```

---

## 3. Build Commands

### 3.1 `ritz build`

```bash
# Build all targets (binaries and libraries)
ritz build

# Build specific target
ritz build --bin valet
ritz build --lib

# Build with profile
ritz build --release
ritz build --debug

# Build with options
ritz build --opt-level 3 --lto
```

**Output structure:**

```
project/
├── build/
│   ├── debug/
│   │   ├── valet           # Debug binary
│   │   ├── valet-cli
│   │   └── libvalet.a      # Debug library (if [lib] defined)
│   └── release/
│       ├── valet           # Release binary
│       ├── valet-cli
│       └── libvalet.a
├── .ritz-cache/            # Intermediate files (can be gitignored)
│   ├── main.ll
│   ├── main.o
│   └── ...
└── ritz.toml
```

### 3.2 `ritz run`

```bash
# Run default binary (first [[bin]] entry)
ritz run

# Run specific binary
ritz run --bin valet-cli

# Run with arguments
ritz run -- --port 8080

# Run single file (doesn't use ritz.toml)
ritz run src/main.ritz
```

### 3.3 `ritz test`

```bash
# Run all tests
ritz test

# Run specific test file
ritz test tests/test_http.ritz

# Run tests matching pattern
ritz test --filter "test_gzip*"
```

---

## 4. Implementation Plan

### Phase 1: Core Build System (Current Priority)

| Task | Description | Effort |
|------|-------------|--------|
| Parse `[[bin]]` entries | Support multiple binary targets | Low |
| Implement `--bin` flag | Build specific target | Low |
| Add build profiles | debug/release subdirectories | Medium |
| RITZ_PATH default to `.` | Simplify default case | Low |
| Output to `build/{debug,release}/` | Structured output | Low |

### Phase 2: Dependency Namespacing

| Task | Description | Effort |
|------|-------------|--------|
| Parse `[dependencies]` | Read path/uri declarations | Low |
| Namespace resolution | `import squeeze.gzip` → `squeeze/src/gzip.ritz` | Medium |
| Transitive deps | Walk dependency tree | Medium |
| Cycle detection | Error on circular dependencies | Low |

### Phase 3: Advanced Features

| Task | Description | Effort |
|------|-------------|--------|
| LLVM BC caching | Precompile to bitcode for faster rebuilds | Medium |
| External .so support | FFI with non-Ritz libraries | High |
| Workspace support | Multi-project builds | Medium |

---

## 5. Decisions (Resolved)

### Q1: How should RITZ_PATH interact with dependencies?

**Decision:** RITZ_PATH defaults to `.` (current directory) and specifies import search paths.

- Dependencies declared in `[dependencies]` get explicit namespaces
- RITZ_PATH can be overridden with multiple entries for development flexibility
- Import resolution: namespace first, then RITZ_PATH search

```bash
# Default - look in current project
RITZ_PATH=.

# Development override - multiple search paths
RITZ_PATH=.:../ritz:../squeeze
```

### Q2: Library output format

**Decision:** Source is primary; precompiled artifacts are optional cache/optimization.

| Layer | Format | Use Case |
|-------|--------|----------|
| **Primary** | Source (.ritz) | Always available, portable, LTO |
| **Cache** | LLVM IR (.bc) | Faster rebuilds, still portable |
| **External** | Shared object (.so) | FFI with non-Ritz libraries |

- Ritz libraries are always source-first
- `.so` files are for importing external (non-Ritz) code
- No separate `lib/` vs `src/` distinction - it's all source

### Q3: How to handle diamond dependencies?

**Decision:** Single version per workspace, with explicit version selection at root.

```
    valet
   /  |  \
squeeze cryptosec ritzunit
   \    |    /
     ritz (single version!)
```

- Root project's `ritz.toml` controls which version of shared deps to use
- If transitive deps request incompatible versions, build fails with clear error
- Future: workspace-level dependency resolution like Cargo

### Q4: Compilation unit structure

**Decision:** All source lives in `src/`; shared code is just modules within the project.

```
project/
├── src/
│   ├── main.ritz        # Entry point → binary
│   ├── server.ritz      # Another entry point (optional)
│   ├── http/            # Shared module (not a separate library)
│   │   ├── request.ritz
│   │   └── response.ritz
│   └── utils.ritz
├── build/
│   ├── debug/           # Debug builds
│   │   └── myapp
│   └── release/         # Release builds
│       └── myapp
└── ritz.toml
```

- No artificial `lib/` separation - modules are just directories
- Multiple entry points (`[[bin]]` entries) share the same source tree
- Build outputs go to `build/debug/` and `build/release/`

---

## 6. Real-World Dependency DAG

The Ritz ecosystem has a layered dependency structure:

```
┌─────────────────────────────────────────────────────────────────┐
│                           valet                                  │
│                    (HTTP server + web framework)                 │
│                                                                  │
│  Depends on: squeeze, cryptosec, ritzunit, ritz/ritzlib         │
└─────────────────────────────────────────────────────────────────┘
                    │           │           │
        ┌───────────┘           │           └───────────┐
        ▼                       ▼                       ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│    squeeze    │      │   cryptosec   │      │   ritzunit    │
│ (compression) │      │   (crypto)    │      │   (testing)   │
│               │      │               │      │               │
│ Uses: ritz,   │      │ Uses: ritz    │      │ Uses: ritz    │
│       ritzunit│      │               │      │               │
└───────────────┘      └───────────────┘      └───────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                ▼
                    ┌───────────────────────┐
                    │         ritz          │
                    │    (base language)    │
                    │                       │
                    │  ritzlib/ - stdlib    │
                    │  ritz0/   - bootstrap │
                    │  ritz1/   - self-host │
                    └───────────────────────┘
```

### Example: valet/ritz.toml

```toml
[package]
name = "valet"
version = "0.1.0"

[[bin]]
name = "valet"
path = "src/main.ritz"

[dependencies]
# In-tree submodule
squeeze = { path = "squeeze" }

# Sibling directory (out-of-tree)
cryptosec = { path = "../cryptosec" }

# Can also use git/SSH (per RFC #107)
# ritzunit = { uri = "https://github.com/ritz-lang/ritzunit", tag = "v1.0" }

# Note: ritz/ritzlib is implicit - it's the base language
```

### Import Resolution

With the above config, imports resolve as:

```ritz
# Namespaced imports (from [dependencies])
import squeeze.gzip          # → squeeze/src/gzip.ritz
import cryptosec.chacha20    # → ../cryptosec/src/chacha20.ritz

# Local imports (from sources)
import http.request          # → src/http/request.ritz
import utils                 # → src/utils.ritz

# Standard library (implicit dependency, ships with compiler)
import ritzlib.sys           # → ritzlib/sys.ritz (no special $RITZ var)
```

### Directory Layouts Supported

**In-tree submodule (squeeze inside valet):**
```
valet/
├── squeeze/              # Git submodule
│   ├── src/
│   │   └── gzip.ritz
│   └── ritz.toml
├── src/
│   └── main.ritz
└── ritz.toml
```

**Out-of-tree sibling (cryptosec next to valet):**
```
workspace/
├── valet/
│   ├── src/main.ritz
│   └── ritz.toml         # cryptosec = { path = "../cryptosec" }
└── cryptosec/
    ├── src/chacha20.ritz
    └── ritz.toml
```

**Mixed (submodules + siblings):**
```
workspace/
├── ritz/                 # Base language
│   └── ritzlib/
├── ritzunit/             # Testing framework
├── valet/
│   ├── squeeze/          # Submodule
│   └── ritz.toml         # Uses squeeze (in-tree) + ritzunit (sibling)
└── cryptosec/
```

---

## 7. Precompiled Libraries (.so)

For importing external (non-Ritz) code, shared objects can be used:

```toml
[dependencies]
# External shared object (FFI)
openssl = { so = "libssl.so.3", headers = "openssl.h" }

# This would generate extern fn declarations from headers
# and link against the .so at build time
```

For Ritz-native libraries that want to distribute precompiled artifacts:

```
libsqueeze-v1.0/
├── src/                    # Source (always present)
│   └── gzip.ritz
├── ritz.toml
└── prebuilt/               # Optional precompiled cache
    ├── x86_64-linux/
    │   └── squeeze.bc      # LLVM bitcode (portable within arch)
    └── aarch64-linux/
        └── squeeze.bc
```

The build system would:
1. Check if prebuilt bitcode exists for target
2. If yes and source hasn't changed: use bitcode (faster)
3. If no: compile from source

**Note:** This is optimization, not the primary distribution mechanism. Source is always authoritative.

---

## 8. Examples

### Simple Binary

```toml
# Minimal project
[package]
name = "hello"
version = "0.1.0"

# sources defaults to ["src"]

[[bin]]
name = "hello"
entry = "main::main"    # src/main.ritz, fn main()
```

### Multiple Binaries Sharing Code

```toml
[package]
name = "myapp"
version = "0.1.0"

sources = ["src"]       # All .ritz files under src/

[[bin]]
name = "server"
entry = "server::main"  # src/server.ritz

[[bin]]
name = "client"
entry = "client::main"  # src/client.ritz

# Both binaries share code from src/common/, src/http/, etc.
# Only the entry point differs - everything else is available to both
```

### Library-Only Package (for reuse)

```toml
# A library package - no binaries, just reusable code
[package]
name = "squeeze"
version = "1.0.0"

# No [[bin]] entries
# Consumers import via: import squeeze.gzip
```

### Full Application with Dependencies

```toml
[package]
name = "valet"
version = "0.1.0"

sources = ["src"]

[[bin]]
name = "valet"
entry = "main::main"

[[bin]]
name = "valet-cli"
entry = "cli::main"

[dependencies]
# In-tree submodule
squeeze = { path = "squeeze" }

# Out-of-tree sibling
cryptosec = { path = "../cryptosec" }

# Remote git (per RFC #107)
# ritzunit = { uri = "https://github.com/ritz-lang/ritzunit", tag = "v1.0" }

[build]
opt-level = 2

[profile.debug]
opt-level = 0
debug = true

[profile.release]
opt-level = 3
lto = true
```

### Project with Exclusions

```toml
[package]
name = "myapp"
version = "0.1.0"

# Include all of src/ except generated code
sources = ["src", "!src/generated"]

[[bin]]
name = "myapp"
entry = "main::main"
```

---

## 9. Migration Path

### For Existing Projects

1. Run `ritz init` to create `ritz.toml`
2. Add `[[bin]]` entries for each executable
3. Replace `RITZ_PATH` manipulation with `[dependencies]`
4. Update imports to use dependency namespaces
5. Remove custom build scripts

### For Valet Specifically

**Current workarounds to remove:**
```bash
# build.sh - DELETE THIS
export RITZ_PATH=$VALET:$VALET/squeeze:$RITZ
lib_squeeze -> squeeze/lib  # Symlink - DELETE
```

**New ritz.toml:**
```toml
[package]
name = "valet"
version = "0.1.0"

[[bin]]
name = "valet"
path = "src/main.ritz"

[dependencies]
squeeze = { path = "squeeze" }
cryptosec = { path = "cryptosec" }
```

**Code changes:**
```ritz
# Before: import lib_squeeze.gzip
# After:  import squeeze.gzip

# Before: import cryptosec.lib.chacha20
# After:  import cryptosec.chacha20
```

**Build command:**
```bash
# Before: ./build.sh --release
# After:  ritz build --release
```

---

## Appendix: Comparison with Other Languages

| Feature | Ritz | Rust | Go | Zig |
|---------|------|------|----|----|
| Manifest | ritz.toml | Cargo.toml | go.mod | build.zig |
| Multiple binaries | `[[bin]]` | `[[bin]]` | main packages | build steps |
| Libraries | `[lib]` | `[lib]` | importable packages | modules |
| Dependencies | URI-based | Registry + git | Module proxy | Package manager |
| Build profiles | Yes | Yes | Build tags | Release modes |
| Namespacing | By dependency name | By crate name | By import path | By package name |

---

**Next Steps:**
1. ~~Review and finalize open questions~~ ✓
2. Implement Phase 1 (core build system)
3. Migrate Valet as proof of concept
