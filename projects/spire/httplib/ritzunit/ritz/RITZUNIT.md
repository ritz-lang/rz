# Ritzunit Integration Guide

Ritzunit is a fast, native test runner for Ritz projects. It discovers tests via ELF symbol table parsing and runs them with fork-based isolation.

## Why Ritzunit?

- **Fast**: Native execution, no Python interpreter overhead
- **Isolated**: Each test runs in a forked process (crashes don't affect other tests)
- **Self-discovering**: No test registration needed - uses ELF symbols
- **Rich output**: Colored output, timing, failure diagnostics

## Test File Conventions

### Directory Structure

```
myproject/
├── ritz.toml
├── src/
│   └── main.ritz
├── lib/
│   └── mylib.ritz
├── test/
│   ├── test_mylib.ritz      # Tests for lib/mylib.ritz
│   └── test_integration.ritz
└── ritzunit -> ../ritzunit   # Symlink to ritzunit repo
```

### Test File Naming

- Test files should be named `test_*.ritz`
- Place them in a `test/` directory
- Each file should test a specific module or feature

### Test Function Conventions

```ritz
import ritzlib.sys
import ritzlib.io

# Test functions MUST:
# 1. Be annotated with @test
# 2. Start with "test_"
# 3. Return i32 (0 = pass, non-zero = fail)

@test
fn test_addition() -> i32
    if 2 + 2 != 4
        return 1
    return 0

# Using assert (preferred - clearer error messages)
@test
fn test_with_assert() -> i32
    let result: i32 = compute_something()
    assert result == 42, "compute_something should return 42"
    return 0

# Non-test helper functions (NOT discovered)
fn helper_function() -> i32
    return 123
```

### The `assert` Statement

Ritz's built-in `assert` statement works with ritzunit:

```ritz
@test
fn test_example() -> i32
    assert condition, "message if condition is false"
    assert x == y, "x should equal y"
    return 0
```

When an assertion fails, the test returns non-zero and ritzunit reports failure.

## Build Integration

### Option 1: Build Script (Recommended)

Create a `build_tests.sh` in your project:

```bash
#!/bin/bash
# build_tests.sh - Build test binary with ritzunit

set -e

RITZ0="python3 ritz/ritz0/ritz0.py"
LIST_DEPS="python3 ritz/ritz0/list_deps.py"
RUNTIME="ritz/runtime/ritz_start.x86_64.o"

# Create build directory
rm -rf build/test
mkdir -p build/test

echo "=== Building Tests ==="

# Collect all dependencies
declare -A COMPILED
LL_FILES=""

# Step 1: Compile ritzunit runner and dependencies
RUNNER_DEPS=$($LIST_DEPS ritzunit/src/runner.ritz)
for SRC in $RUNNER_DEPS; do
    BASENAME=$(basename "$SRC" .ritz)
    OUTFILE="build/test/${BASENAME}.ll"
    if [ -z "${COMPILED[$BASENAME]}" ]; then
        echo "Compiling $SRC"
        $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime
        COMPILED[$BASENAME]=1
        LL_FILES="$LL_FILES $OUTFILE"
    fi
done

# Step 2: Compile your library code
for SRC in lib/*.ritz; do
    BASENAME=$(basename "$SRC" .ritz)
    OUTFILE="build/test/${BASENAME}.ll"
    if [ -z "${COMPILED[$BASENAME]}" ]; then
        echo "Compiling $SRC"
        $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime
        COMPILED[$BASENAME]=1
        LL_FILES="$LL_FILES $OUTFILE"
    fi
done

# Step 3: Compile test files
for SRC in test/test_*.ritz; do
    BASENAME=$(basename "$SRC" .ritz)
    OUTFILE="build/test/${BASENAME}.ll"
    echo "Compiling $SRC"
    $RITZ0 "$SRC" -o "$OUTFILE" --no-runtime
    LL_FILES="$LL_FILES $OUTFILE"
done

# Step 4: Link everything
echo "Linking..."
clang $RUNTIME $LL_FILES -o build/test/tests -nostdlib -g

echo "Build complete: build/test/tests"
```

### Option 2: Makefile Target

```makefile
.PHONY: test build-tests

RITZ0 = python3 ritz/ritz0/ritz0.py
RUNTIME = ritz/runtime/ritz_start.x86_64.o

build-tests:
	./build_tests.sh

test: build-tests
	./build/test/tests

test-verbose: build-tests
	./build/test/tests -v

test-filter: build-tests
	./build/test/tests -f $(FILTER)
```

## Running Tests

### Basic Usage

```bash
# Run all tests
./build/test/tests

# Verbose mode (show test names as they run)
./build/test/tests -v

# Quiet mode (only failures + summary)
./build/test/tests -q

# List tests without running
./build/test/tests -l

# Filter tests by substring
./build/test/tests -f sha256
./build/test/tests -f "test_add"

# Set timeout (milliseconds)
./build/test/tests -t 5000

# Disable fork isolation (for debugging)
./build/test/tests --no-fork
```

### Exit Codes

- `0`: All tests passed
- `1`: One or more tests failed
- Other: Error during test execution

### Example Output

```
Running 5 tests...

  test_mem_zero_basic ................. OK (0ms)
  test_mem_zero_partial ............... OK (0ms)
  test_mem_eq_equal ................... OK (0ms)
  test_sha256_basic ................... FAIL [code=1] (0ms)
  test_hmac_basic ..................... OK (0ms)

================================================

Results: 4 passed, 1 failed, 5 total
Time: 1ms
```

## Project Integration Patterns

### Pattern: Submodule

```bash
# Add ritzunit as a git submodule
git submodule add https://github.com/ritz-lang/ritzunit.git

# Your .gitmodules will have:
# [submodule "ritzunit"]
#     path = ritzunit
#     url = https://github.com/ritz-lang/ritzunit.git
```

### Pattern: Symlink (Monorepo)

```bash
# If ritzunit is a sibling directory
ln -s ../ritzunit ritzunit
```

### Pattern: Ritz Submodule (Common)

If your project already has `ritz` as a submodule (for ritzlib), you can either:

1. Add ritzunit as another submodule
2. Add ritzunit as a submodule *of* ritz (nested)
3. Use symlinks in a monorepo setup

## CLI Reference

```
ritzunit - A modern unit testing framework for Ritz

Usage: tests [OPTIONS]

Options:
  -v, --verbose     Show test names as they run
  -q, --quiet       Minimal output (failures + summary)
  -l, --list        List tests without running
  -f, --filter=PAT  Run only tests matching substring
  -t, --timeout=MS  Set per-test timeout (default: 5000ms)
  --no-fork         Disable fork isolation (for debugging)
  -h, --help        Show this help message
```

## Writing Good Tests

### Do

```ritz
@test
fn test_sha256_empty_input() -> i32
    # Descriptive name
    var hash: [32]u8
    sha256(c"", 0, &hash[0])

    # Test specific, expected values
    assert hash[0] == 0xe3, "SHA256('') first byte"
    return 0
```

### Don't

```ritz
@test
fn test1() -> i32  # Bad: non-descriptive name
    # ...
    return 0

fn test_helper() -> i32  # Not discovered: no @test attribute
    return 0
```

### Test Isolation

Each test runs in a forked process. This means:
- Tests can crash without affecting others
- Global state is reset between tests
- Tests can be run in any order

### Debugging Failures

```bash
# Run with --no-fork to get stack traces
./build/test/tests --no-fork -f test_that_crashes

# Run under gdb
gdb -ex run --args ./build/test/tests --no-fork -f test_that_crashes
```

## Performance Comparison

| Runner | 100 tests | Notes |
|--------|-----------|-------|
| ritz0 --test | ~45s | Python interpreter, sequential |
| ritzunit | ~0.5s | Native, fork-based |

Ritzunit is approximately **90x faster** than ritz0's built-in test runner.

## Troubleshooting

### "No tests found"

- Ensure test functions are annotated with `@test`
- Ensure function names start with `test_`
- Ensure functions return `i32`
- Check that test files are compiled and linked

### Tests hang

- Reduce timeout: `./tests -t 1000`
- Check for infinite loops in test code
- Run with `--no-fork` to debug

### Segfaults during test discovery

- Ensure the binary is linked with all required `.ll` files
- Check that ritzlib modules are compiled and linked

## Future Enhancements

See ritzunit's TODO.md for planned features:
- Glob pattern matching (`test_add*`)
- Parallel test execution (`--jobs N`)
- JUnit XML output
- JSON output
- Fail-fast mode
