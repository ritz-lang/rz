# Ritz Language

Systems programming language compiling to LLVM IR. No libc - direct Linux syscalls.

## Status (February 2026)

| Component | Status |
|-----------|--------|
| **ritz0** (Python bootstrap) | ✅ 324 tests passing |
| **ritz1** (self-hosted) | 🔄 Blocked on generics monomorphization |
| **ritzlib** | 34 modules |
| **examples** | 75+ programs |

## Quick Start

```bash
# Build an example
python3 build.py build 21_ls

# Run tests
make test

# Run regression suite
make regression
```

## Directory Structure

```
ritz/
├── ritz0/           # Bootstrap compiler (Python)
├── ritz1/           # Self-hosted compiler (Ritz)
├── ritzlib/         # Standard library
├── examples/        # Example programs
├── build.py         # Build system
└── Makefile
```

## Key Syntax

```ritz
import ritzlib.sys
import ritzlib.io

fn main() -> i32
    print(c"Hello, world!\n")
    0
```

**String literals:**
- `"hello"` → `String` (heap-allocated)
- `c"hello"` → `*u8` (C string)
- `s"hello"` → `Span<u8>` (zero-copy)

**Testing:**
```ritz
@test
fn test_add() -> i32
    assert 2 + 3 == 5
    0
```

## Principles

1. **No concessions** - Missing feature? Implement it in the language.
2. **No libc** - Direct syscalls only.
3. **Test-driven** - Write tests, then implement.

## Documentation

- `docs/LANGUAGE.md` - Full language reference
- `docs/EXAMPLES.md` - Example program guide
- `docs/TESTING.md` - Test system documentation
- `STYLE.md` - Code style guide
- `TODO.md` / `DONE.md` - Work tracking
