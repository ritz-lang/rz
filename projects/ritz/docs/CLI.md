# Ritz CLI Reference

The `ritz` command is the unified entry point for all Ritz language toolchain operations.

## Quick Start

```bash
# Make executable (one-time)
chmod +x ritz

# Build and test a package
./ritz build 01_hello
./ritz test 01_hello

# Compile and run a single file
./ritz run examples/01_hello/src/main.ritz

# Run the language test suite
./ritz check
```

## Command Overview

| Command | Description |
|---------|-------------|
| `build` | Build a package or all packages |
| `test` | Build and run tests for a package |
| `run` | Compile and run a single .ritz file |
| `clean` | Remove build artifacts and caches |
| `check` | Run the language test suite |
| `compile` | Low-level: compile .ritz to .ll |
| `regression` | Run multi-stage regression suite |
| `cache` | Manage the build cache |
| `list` | List all available packages |
| `version` | Show version information |
| `help` | Show detailed help |

---

## Build & Run Commands

### `ritz build`

Build a package or all packages.

```bash
ritz build <package>            # Build specific package
ritz build --all                # Build all packages
ritz build -a                   # Short form
ritz build <package> -g         # Keep intermediate files (.ll, .o)
ritz build <package> --no-cache # Disable build cache
```

**Examples:**
```bash
ritz build 01_hello         # Build the hello example
ritz build hello            # Also works (package name)
ritz build --all            # Build all 49 packages
```

**Options:**
- `-g, --debug`: Keep intermediate files in `build/` for debugging
- `--no-cache`: Force rebuild, ignore cached compilation

---

### `ritz test`

Build and run tests for a package. Tests include:
- `.ritz` files in `test/` directory with `@test` functions
- `test.sh` shell scripts for integration tests

```bash
ritz test <package>         # Test specific package
ritz test --all             # Test all packages
ritz test <package> -g      # Keep intermediate files
```

**Example output:**
```bash
ritz test 01_hello
# 📦 Building hello...
#   🔨 hello <- src/main.ritz  [cached]
#   ✓ examples/01_hello/hello
#   🧪 Running .ritz tests...
#     6 passed, 0 failed
#   🧪 Running test.sh...
#     ✓ test.sh passed
# ✓ All tests passed!
```

---

### `ritz run`

Compile and run a single .ritz source file.

```bash
ritz run <file.ritz>                    # Run a file
ritz run <file.ritz> arg1 arg2          # Pass arguments
ritz run <file.ritz> -g                 # Keep debug artifacts
```

**Examples:**
```bash
ritz run examples/01_hello/src/main.ritz
# 🔨 Compiling examples/01_hello/src/main.ritz...
# 🚀 Running main...
# Hello, Ritz!

ritz run examples/03_echo/src/main.ritz hello world
# hello world
```

---

### `ritz clean`

Remove all build artifacts and caches.

```bash
ritz clean
```

This removes:
- Compiled binaries from example directories
- `build/` directory artifacts
- `.ritz-cache/` directory
- `__pycache__` directories

---

## Testing Commands

### `ritz check`

Run the ritz0 language test suite (154+ tests across 17 levels).

```bash
ritz check              # Run ritz0 tests
ritz check --ritz1      # Run ritz1 self-hosting tests
```

---

### `ritz regression`

Run the multi-stage regression test suite for self-hosting validation.

```bash
ritz regression                 # Run all stages
ritz regression --stage 1       # Run only Stage 1
ritz regression --quick         # Skip Stage 4 (slower)
ritz regression -v              # Verbose output
```

**Stages:**
| Stage | Description | Status |
|-------|-------------|--------|
| 1 | ritz0 compiles all examples | ✅ 46/48 |
| 2 | ritz0 compiles ritz1 | ✅ 1/1 |
| 3 | ritz1 compiles all examples | ⚠️ 6/48 |
| 4 | ritz1 self-compiles (bootstrap) | ❌ blocked |

---

## Development Commands

### `ritz compile`

Low-level compilation: compile a .ritz file directly to LLVM IR.

```bash
ritz compile <source.ritz>              # Output to <source>.ll
ritz compile <source.ritz> -o out.ll    # Custom output path
ritz compile <source.ritz> --no-runtime # Library mode (no _start)
ritz compile <source.ritz> -v           # Verbose output
```

**Examples:**
```bash
# Compile to LLVM IR
ritz compile src/main.ritz -o build/main.ll

# Compile as library (no entry point)
ritz compile ritzlib/str.ritz -o build/str.ll --no-runtime

# Full compilation pipeline
ritz compile src/main.ritz -o build/main.ll
llc -filetype=obj build/main.ll -o build/main.o
clang build/main.o -o build/main -nostdlib
./build/main
```

---

## Package Management Commands

### `ritz list`

List all available packages with their binaries.

```bash
ritz list
# Found 49 packages:
#   01_hello/  →  hello (hello)
#   02_exitcode/  →  exitcode (exitcode)
#   ...
```

---

### `ritz cache`

Manage the build cache.

```bash
ritz cache status           # Show cache status
ritz cache status -v        # Detailed information
ritz cache clear            # Clear the cache
```

---

## Environment Variables

### `RITZ_PATH`

Colon-separated list of directories to search for imports.

```bash
export RITZ_PATH="/path/to/project:/path/to/libs"
ritz build mypackage
```

If not set, defaults to the project root (detected by `.git` or `ritzlib/` directory).

---

## Project Structure

A typical Ritz project:

```
myproject/
├── ritz.toml           # Package manifest
├── src/
│   └── main.ritz       # Main source file
├── test/
│   └── test_main.ritz  # Test file with @test functions
└── test.sh             # Optional integration tests
```

### ritz.toml Format

```toml
[package]
name = "myproject"
version = "0.1.0"

# Single binary (default: src/main.ritz → package name)
# No [[bin]] section needed for simple projects

# Multiple binaries
[[bin]]
name = "mybinary"
path = "src/mybinary.ritz"

[[bin]]
name = "mytool"
path = "src/mytool.ritz"
```

---

## Writing Tests

Create test files in the `test/` directory with `@test` functions:

```ritz
# test/test_example.ritz

@test
fn test_addition() -> i32
    assert 2 + 2 == 4
    0

@test
fn test_string_length() -> i32
    let s: *u8 = "hello"
    var len: i64 = 0
    while *(s + len) != 0
        len = len + 1
    assert len == 5
    0
```

Run with:
```bash
ritz test myproject
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Compilation or test failure |
| 2 | Critical failure (couldn't start) |

---

## Future Commands (Planned)

| Command | Description |
|---------|-------------|
| `fmt` | Format Ritz source files |
| `lint` | Check for common issues |
| `new` | Create a new Ritz project |
| `init` | Initialize ritz.toml in current directory |

---

## See Also

- `docs/EXAMPLES.md` - Example programs by tier
- `docs/LANGUAGE.md` - Language reference
- `docs/TESTING.md` - Testing guide
- `TODO.md` - Development roadmap
