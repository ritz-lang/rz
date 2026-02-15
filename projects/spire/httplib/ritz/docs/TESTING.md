# Ritz Testing

This document describes the current testing infrastructure and proposed improvements.

---

## Current State (February 2026)

### Test Types

| Type | Location | Format | Runner |
|------|----------|--------|--------|
| **Language tests** | `ritz0/test/test_level*.ritz` | `@test` functions | `python3 build.py ritz-tests` |
| **Python unit tests** | `ritz0/test_*.py` | pytest | `cd ritz0 && pytest` |
| **Example tests** | `examples/*/test/*.ritz` | `@test` functions | `python3 build.py test <name>` |
| **Shell tests** | `examples/*/test.sh` | Shell scripts | `python3 build.py test <name>` |
| **Dual-compiler tests** | `test/dual_compiler/` | `@test` functions | Both ritz0 and ritz1 |

### The `@test` Attribute

Ritz supports a `@test` attribute on functions:

```ritz
@test
fn test_addition() -> i32
    assert 2 + 3 == 5
    assert 10 - 4 == 6
    0

@test
fn test_comparison() -> i32
    assert 5 > 3
    assert 3 < 5
    assert 5 == 5
    0
```

**How it works:**
- Test functions must return `i32` (0 = pass, non-zero = fail)
- The `assert` statement aborts with exit code 1 if condition is false
- `ritz0/test_runner.py` discovers `@test` functions and runs each one

### Running Tests

```bash
# Run language tests (test_level*.ritz)
python3 build.py ritz-tests

# Run Python unit tests
cd ritz0 && python -m pytest -q

# Test a specific example
python3 build.py test 21_ls

# Test all examples
python3 build.py test --all

# Full test suite via Makefile
make test
```

### Regression Testing

The `scripts/regression.sh` script runs a 4-stage regression:

| Stage | Description | Purpose |
|-------|-------------|---------|
| 1 | ritz0 compiles examples, runs them | Baseline correctness |
| 2 | ritz0 compiles ritz1 | Bootstrap compiler builds |
| 3 | ritz1 compiles examples, compare output | Compiler equivalence |
| 4 | ritz1 self-compiles, compile examples | Self-hosting validation |

```bash
make regression           # Full 4-stage regression
make regression-quick     # Skip stage 4 (faster)
./scripts/regression.sh --stage 1  # Run specific stage
```

---

## Test File Locations

```
ritz/
├── ritz0/
│   ├── test_parser.py       # Parser unit tests (pytest)
│   ├── test_lexer.py        # Lexer unit tests (pytest)
│   ├── test_runner.py       # @test function runner
│   └── test/
│       ├── test_level1.ritz   # Basic assertions
│       ├── test_level2.ritz   # Functions
│       ├── test_level3.ritz   # Control flow
│       ├── ...                # 38 levels total
│       └── test_level38.ritz  # Advanced features
├── test/
│   └── dual_compiler/       # Tests run by both ritz0 and ritz1
└── examples/
    └── */
        ├── test/
        │   └── test_*.ritz  # Example-specific tests
        └── test.sh          # Shell-based tests (some examples)
```

---

## Current Issues

### Problem 1: Two Test Formats

Some examples use `@test` functions in `test/*.ritz`, others use `test.sh` shell scripts. This makes the test system inconsistent.

**Current workaround**: `build.py` tries both - runs `@test` functions if found, falls back to `test.sh`.

### Problem 2: Tests Don't Match Examples

Example: `examples/01_hello/test/test_hello.ritz` tests **arithmetic and comparisons**, not the hello world program itself. The test file exercises language features rather than the specific example.

### Problem 3: No Clear Tier Support

The build system doesn't understand example tiers. Can't run "just tier 1 tests" easily.

### Problem 4: Shell Scripts Are Fragile

`test.sh` scripts vary in quality and often have path assumptions. They're harder to maintain than pure Ritz tests.

---

## Proposed Improvements

### 1. Standardize on `@test` Functions

All tests should be Ritz code with `@test` attributes:

```ritz
# examples/05_cat/test/test_cat.ritz

import ritzlib.sys
import ritzlib.testing

@test
fn test_cat_reads_file() -> i32
    # Write a temp file
    let fd = sys_open(c"/tmp/test_cat.txt", O_WRONLY | O_CREAT, 0644)
    sys_write(fd, c"hello", 5)
    sys_close(fd)

    # Run cat and capture output (needs spawn/capture support)
    # For now, just verify the binary exists and runs
    0

@test
fn test_cat_exits_zero_on_success() -> i32
    # ...
    0
```

### 2. Add Tier Support to Build System

```bash
python3 build.py test --tier 1    # Run tier 1 tests only
python3 build.py test --tier 2-3  # Run tiers 2 and 3
python3 build.py test --all       # All tiers
```

### 3. Unified Test Runner

A single test command that handles all test types:

```bash
ritz test                    # Run all tests
ritz test --filter "hello"   # Filter by name
ritz test --verbose          # Show all test names
ritz test --tier 1           # Run tier 1 only
```

### 4. Proper Integration Test Support

Add `ritzlib.testing` module with:

```ritz
import ritzlib.testing

@test
fn test_cat_output() -> i32
    let result = run_command(c"./cat", [c"fixtures/small.txt"])
    assert result.exit_code == 0
    assert result.stdout == c"expected content"
    0
```

This requires implementing:
- `fork`/`exec`/`wait` wrappers in ritzlib
- Pipe handling for stdout/stderr capture
- Temp file management

---

## Test Attributes Reference

| Attribute | Status | Description |
|-----------|--------|-------------|
| `@test` | ✅ Implemented | Marks a function as a test |
| `@ignore` | ❌ Not implemented | Skip test unless explicitly requested |
| `@should_panic` | ❌ Not implemented | Test expects a panic |
| `@timeout(ms)` | ❌ Not implemented | Test timeout in milliseconds |

---

## Writing Good Tests

### Language Feature Tests

For `ritz0/test/test_level*.ritz`, test specific language features:

```ritz
# test_level_for_loops.ritz - Tests for `for i in 0..n` syntax

@test
fn test_exclusive_range() -> i32
    var sum: i32 = 0
    for i in 0..5
        sum += i
    assert sum == 10  # 0+1+2+3+4
    0

@test
fn test_inclusive_range() -> i32
    var sum: i32 = 0
    for i in 0..=5
        sum += i
    assert sum == 15  # 0+1+2+3+4+5
    0
```

### Example Tests

For `examples/*/test/`, test the specific example's behavior:

```ritz
# examples/08_seq/test/test_seq.ritz

@test
fn test_seq_default() -> i32
    # seq 5 should output 1 2 3 4 5
    # (requires spawn support)
    0

@test
fn test_seq_start_end() -> i32
    # seq 3 7 should output 3 4 5 6 7
    0
```

---

## Running the Full Test Suite

```bash
# Recommended: use Makefile
make test

# This runs:
# 1. Python unit tests (pytest)
# 2. Language tests (test_level*.ritz)
# 3. ritz1 tests
# 4. Example tests
```

---

*Last updated: 2026-02-11*
