# Ritz Language

Systems programming language compiling to LLVM IR. No libc - direct Linux syscalls.

## Status (April 2026)

| Component | Status |
|-----------|--------|
| **ritz0** (Python bootstrap) | ✅ 33/33 regression matrix |
| **ritz1** (self-hosted, ritz0-built) | ✅ 33/33 regression matrix |
| **ritz1_selfhosted** (ritz1 self-compiling) | ✅ 33/33 regression matrix |
| **ritzlib** | 34 modules |
| **examples** | 75+ programs |

## Quick Start

```bash
# Build an example
python3 build.py build 21_ls

# Pre-commit validation (incremental ritz1, 30-60s)
make matrix

# Pre-push validation (full bootstrap + matrix, ~1m 40s)
make matrix-full

# All tests, all examples (slow)
make test
```

**Read `docs/VALIDATION.md` before running clean rebuilds.** The hard rule is:
never `make clean` to "make sure it works" — Make's incremental rebuild is
correct; if it isn't, that's a Makefile bug to fix, not paper over. A previous
session burned 100 minutes on redundant full bootstraps.

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
[[test]]
fn test_add() -> i32
    assert 2 + 3 == 5
    0
```

See `docs/TESTING.md` for the canonical fork+exec integration-test template
and the four harness gotchas (read-until-EOF, temp-file stdin, etc.).

## Principles

1. **No concessions** - Missing feature? Implement it in the language.
2. **No libc** - Direct syscalls only.
3. **Test-driven** - Write tests, then implement.

## Documentation

- `docs/LANGUAGE.md` - Full language reference
- `docs/EXAMPLES.md` - Example program guide
- `docs/TESTING.md` - Test system documentation
- `docs/VALIDATION.md` - **Validation workflow & build cadence** (read this!)
- `STYLE.md` - Code style guide
- `TODO.md` / `DONE.md` - Work tracking
- `docs/XARGS_WATCH_BLOCKER.md` - Pre-existing StrView/i8* type-mismatch
  blocking 37_xargs and 40_watch builds. Fix sketch included.
