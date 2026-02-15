# 🎭 Ritz

A minimalistic, type-safe systems programming language.

## Goals

- **Minimal syntax**: Indentation-based, no semicolons, no braces
- **Type-safe with inference**: Static types, rarely written
- **Ownership without annotations**: Rust semantics, simpler surface
- **One language for everything**: Kernel to script, same syntax
- **Bootstrappable**: Ship compiler as LLVM IR

## Quick Example

```ritz
fn main() -> i32
  print("Hello, Ritz\n")
  0
```

```ritz
import ritzlib.sys
import ritzlib.io

fn main(argc: i32, argv: **u8) -> i32
    let name: *u8 = *(argv + 1)
    prints("Hello, ")
    prints(name)
    prints("!\n")
    0
```

## Quick Start

```bash
# Create a new project
./ritz new myproject
cd myproject

# Build and run
./ritz build
./ritz run src/main.ritz

# Run tests
./ritz test

# Or work with existing packages:
./ritz build 12_tac      # Build a specific package
./ritz test --all        # Test all packages
./ritz check             # Run language test suite

# Package for distribution
./ritz package
```

### Manual Compilation

```bash
# Low-level compilation pipeline
./ritz compile src/main.ritz -o output.ll
clang output.ll -o hello -nostdlib
./hello
```

## Status

**Current Phase:** ritz0 Stabilization + ritz1 Self-Hosting

| Stage | Description | Status |
|-------|-------------|--------|
| **ritz0** | Python bootstrap compiler | ✅ 48/48 examples |
| **ritz1** | Self-hosted compiler (compiled by ritz0) | ⚠️ 47/48 examples |
| **Self-hosting** | ritz1 compiles itself | 🔜 blocked |

See [TODO.md](TODO.md) for detailed progress and [docs/NEXT_SESSION.md](docs/NEXT_SESSION.md) for session continuity.

## Compilation Model

```
.ritz → .ll → link → binary
```

Each `.ritz` file compiles to its own `.ll` file:
- Functions from the current file: `define` (full body)
- Functions from imports: `declare` (external reference)
- Linking: `clang` links all `.ll` files together

## Documentation

- [Language Design](docs/DESIGN.md) - Syntax, types, ownership
- [Bootstrap Strategy](docs/BOOTSTRAP.md) - ritz0 → ritz1 → ritz2
- [CLI Reference](docs/CLI.md) - `ritz run`, `ritz build`, `ritz test`
- [Packaging](docs/PACKAGING.md) - Project structure, ritz.toml
- [Testing](docs/TESTING.md) - Built-in test framework
- [Examples](docs/EXAMPLES.md) - 48 graduated programs
- [Standard Library](docs/RITZLIB.md) - ritzlib structure
- [Next Session](docs/NEXT_SESSION.md) - Session continuity guide

## Project Structure

```
langdev/
├── ritz              # CLI entry point
├── build.py          # Build system
├── ritz0/            # Python bootstrap compiler
│   ├── ritz0.py      # Main compiler
│   ├── import_resolver.py  # Import resolution + metadata caching
│   └── metadata.py   # Module metadata extraction
├── ritz1/            # Self-hosted compiler (in Ritz)
│   ├── ritz1.grammar # Grammar specification
│   ├── src/          # Compiler source
│   └── Makefile      # Build script
├── ritzlib/          # Standard library
│   ├── sys.ritz      # Syscall wrappers
│   ├── io.ritz       # I/O helpers
│   ├── str.ritz      # String utilities
│   ├── memory.ritz   # Memory allocation
│   └── ...
├── examples/         # 48 example programs
├── docs/             # Documentation
└── tests/            # Test suites
```

## Building ritz1

```bash
# Build ritz1 compiler (uses ritz0)
cd ritz1 && make

# Test ritz1 on an example
RITZ_PATH=/path/to/langdev build/ritz1 examples/01_hello/src/main.ritz -o test.ll
llc test.ll -o test.s
gcc test.s -o test -nostartfiles -static
./test
```

**Note:** `RITZ_PATH` must point to the **parent** directory of ritzlib (e.g., `langdev/`), not `langdev/ritzlib/`.

## License

TBD
