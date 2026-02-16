# ritz.toml Specification

This document defines the canonical structure for `ritz.toml` manifest files in the Ritz ecosystem.

---

## Overview

Every Ritz project contains a `ritz.toml` at its root. This manifest defines:

- Package metadata
- Source discovery
- Binary and library targets
- Dependencies
- Build configuration
- Compilation profiles

---

## Required Section: [package]

Every `ritz.toml` must have a `[package]` section:

```toml
[package]
name = "project-name"
version = "0.1.0"
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✓ | Package identifier (kebab-case recommended) |
| `version` | ✓ | Semantic version (e.g., "0.1.0", "1.0.0-alpha") |
| `description` | | Human-readable description |
| `authors` | | List: `["Name <email@example.com>"]` |
| `repository` | | URL to source repository |
| `edition` | | Language edition (e.g., "2024") |
| `license` | | License identifier (e.g., "MIT") |

### Example

```toml
[package]
name = "cryptosec"
version = "0.1.0"
description = "Cryptographic primitives for Ritz"
authors = ["Aaron Sinclair <nevelis@gmail.com>"]
license = "MIT"
```

---

## Source Discovery: sources

The `sources` field specifies directories to scan for `.ritz` files:

```toml
sources = ["src"]           # Single directory
sources = ["lib", "test"]   # Multiple directories
```

Directories expand to `**/*.ritz` for recursive discovery. If omitted, defaults depend on project type.

---

## Targets

### Binary Targets: [[bin]]

For executable programs:

```toml
[[bin]]
name = "my-tool"
entry = "main::main"
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✓ | Binary name (output filename) |
| `entry` | ✓* | Module entry point: `"module::function"` |
| `path` | | Explicit file path (legacy, prefer `entry`) |
| `sources` | | Override sources for this target |
| `target` | | Cross-compilation target (e.g., "x86_64-unknown-uefi") |

*Either `entry` or `path` required. Use `entry` for Ritz code.

**Entry Point Format**: `"module::function"` where:
- `module` is the filename without `.ritz` extension
- `function` is the entry function (typically `main`)

### Library Targets: [[lib]]

For library packages:

```toml
[[lib]]
name = "cryptosec"
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✓ | Library name (used in imports) |

### Test Targets: [[test]]

For test suites:

```toml
[[test]]
name = "crypto-tests"
entry = "test::main"
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✓ | Test suite name |
| `entry` | | Test entry point |
| `sources` | | Test source directories |

---

## Dependencies: [dependencies]

Path-based dependencies:

```toml
[dependencies]
ritzlib = { path = "../ritz/ritzlib" }
squeeze = { path = "../squeeze" }
cryptosec = { path = "../cryptosec" }
```

Paths are relative to the `ritz.toml` location.

### Dev Dependencies: [dev-dependencies]

Dependencies only needed for development/testing:

```toml
[dev-dependencies]
ritzunit = { path = "../ritzunit" }
```

---

## Build Configuration: [build]

```toml
[build]
target = "x86_64-linux"
test_only = true           # Library-only package (no main binary)
```

| Field | Description |
|-------|-------------|
| `target` | Default compilation target |
| `test_only` | Mark as library-only (no executable output) |
| `build` | Custom build command |
| `test` | Custom test command |
| `clean` | Custom clean command |

---

## Compilation Profiles

### Debug Profile: [profile.debug]

```toml
[profile.debug]
opt-level = 2    # 0-3 (note: LLVM 20 has issues with O0/O1)
debug = true     # Include debug symbols
```

### Release Profile: [profile.release]

```toml
[profile.release]
opt-level = 3
debug = false
lto = true       # Link-time optimization
```

**Note**: Due to LLVM 20 DAG combiner issues, most projects use `opt-level = 2` for both debug and release.

---

## Complete Examples

### Executable Project

```toml
[package]
name = "valet"
version = "0.1.0"
description = "HTTP server for Ritz"

sources = ["src"]

[[bin]]
name = "valet"
entry = "main::main"

[dependencies]
ritzlib = { path = "../ritz/ritzlib" }
http = { path = "../http" }
cryptosec = { path = "../cryptosec" }

[profile.debug]
opt-level = 2
debug = true

[profile.release]
opt-level = 2
debug = true
```

### Library Project

```toml
[package]
name = "squeeze"
version = "0.1.0"
description = "Compression algorithms for Ritz"

sources = ["lib"]

[[lib]]
name = "squeeze"

[build]
test_only = true

[dependencies]
ritzlib = { path = "../ritz/ritzlib" }
```

### Multi-Binary Project

```toml
[package]
name = "tome"
version = "0.1.0"
description = "In-memory cache system"

sources = ["src", "test"]

[[bin]]
name = "tome-server"
entry = "tome_server::main"

[[bin]]
name = "tome-cli"
entry = "tome_cli::main"

[[bin]]
name = "run-tests"
entry = "run_tests::main"

[dependencies]
ritzlib = { path = "../ritz/ritzlib" }
```

### Workspace Root

```toml
[package]
name = "ritz"
version = "0.1.0-alpha"
description = "Ritz programming language"

[workspace]
members = [
    "ritz0",
    "ritz1",
    "examples"
]
```

---

## Anti-Patterns

### ❌ Don't Use

| Bad | Good | Reason |
|-----|------|--------|
| `[deps]` | `[dependencies]` | Non-standard section name |
| `[lib]` | `[[lib]]` | Use array syntax for targets |
| `[test]` | `[[test]]` | Use array syntax for targets |
| `[profile.dev]` | `[profile.debug]` | Inconsistent naming |
| `path = "src/main.ritz"` | `entry = "main::main"` | Prefer entry points |

### ❌ Don't Omit

- `version` — always include
- `[[lib]]` for library packages — make intent explicit
- `sources` — prefer explicit over implicit

---

## Migration Checklist

When auditing existing `ritz.toml` files:

- [ ] Has `version` field
- [ ] Uses `[dependencies]` not `[deps]`
- [ ] Uses `[[lib]]` not `[lib]` for library targets
- [ ] Uses `[[test]]` not `[test]` for test targets
- [ ] Uses `[profile.debug]` not `[profile.dev]`
- [ ] Uses `entry` not `path` for Ritz binaries
- [ ] Has explicit `sources` declaration

---

*Maintained by LARB (Language Architecture Review Board)*
