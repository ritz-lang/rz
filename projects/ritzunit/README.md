# Ritzunit

A fast, native unit testing framework for the [Ritz programming language](https://github.com/ritz-lang/ritz).

## Features

- **Fast**: Native execution with fork-based isolation
- **Self-discovering**: Tests found via ELF symbol table parsing
- **Rich filtering**: Glob patterns, boolean expressions, attribute markers
- **CI/CD ready**: JSON and JUnit XML output formats
- **Colorful**: ANSI colors with TTY auto-detection

## Quick Start

```bash
# Build and run tests
./build_inventory_tests.sh

# Run with options
./build/inventory_tests -v              # Verbose
./build/inventory_tests -f "add*"       # Filter by glob
./build/inventory_tests --json          # JSON output
./build/inventory_tests --junit         # JUnit XML output
```

## Writing Tests

```ritz
import ritzlib.sys

@test
fn test_addition() -> i32
    if 2 + 2 != 4
        return 1  # FAIL
    return 0      # PASS

@test
fn test_slow_computation() -> i32
    # "slow" in name marks this for @slow filter
    # ...expensive test...
    return 0

@test
fn test_ignore_wip() -> i32
    # "ignore" in name marks this for @ignore filter
    return 0
```

## CLI Reference

```
Usage: ritzunit [OPTIONS]

Options:
  -v, --verbose        Show detailed output
  -q, --quiet          Minimal output (failures + summary only)
  -l, --list           List tests without running them
  -h, --help           Show this help message
  -f, --filter=EXPR    Filter tests by EXPR (see below)
  -t, --timeout=MS     Timeout per test in milliseconds (default: 5000)
  -x, --fail-fast      Stop on first test failure
  -s, --shuffle        Randomize test execution order
      --seed=N         Random seed for shuffling (0 = auto)
  -j, --json           Output results in JSON format
      --junit          Output results in JUnit XML format
      --color          Force colored output
      --no-color       Disable colored output
      --no-fork        Disable fork isolation (for debugging)
```

## Filter Expressions

Ritzunit supports powerful filter expressions for selecting tests.

### Substring Match (default)
```bash
./tests -f add          # Tests containing "add"
```

### Glob Patterns
```bash
./tests -f "test_add*"      # Starts with test_add
./tests -f "*remove*"       # Contains remove
./tests -f "test_?_foo"     # Single char wildcard
```

### Boolean Operators
```bash
./tests -f "add and not slow"      # add tests, excluding slow
./tests -f "json or xml"           # json OR xml tests
./tests -f "not ignore"            # all except ignore
```

### Attribute Markers
Tests can be tagged via naming convention:

| Attribute | Description | Example Function |
|-----------|-------------|------------------|
| `@slow` | Tests with "slow" in name | `test_slow_integration()` |
| `@ignore` | Tests with "ignore" in name | `test_ignore_wip()` |
| `@skip` | Alias for @ignore | |
| `@fast` | Tests NOT marked @slow | All others |

```bash
./tests -f "@slow"                  # Only slow tests
./tests -f "not @ignore"            # Skip ignored tests
./tests -f "@fast and not json"     # Fast tests, no json
```

### Suite::Test Syntax
```bash
./tests -f "inventory::test_add"    # Tests in inventory suite matching test_add
```

## Output Formats

### Default (Human-Readable)
```
======================================================================
  RITZUNIT v0.1.0 - Test Framework for Ritz
======================================================================

tests
  test_add_single_item ...................................... OK (1ms)
  test_add_increments_quantity .............................. OK (1ms)
  test_should_fail .......................................... FAIL [code=1] (1ms)
  ----------------------------------------------------------------------
  3 tests: 2 passed, 1 failed (3ms)

======================================================================
TOTAL: 3 tests | 2 passed | 1 failed (3ms)
======================================================================
```

### JSON (`--json`)
```json
{
  "version": "0.1.0",
  "summary": {
    "total": 3,
    "passed": 2,
    "failed": 1,
    "crashed": 0,
    "timeout": 0,
    "skipped": 0,
    "duration_ms": 3
  },
  "tests": [
    {"name": "test_add_single_item", "status": "pass", "duration_ms": 1},
    {"name": "test_add_increments_quantity", "status": "pass", "duration_ms": 1},
    {"name": "test_should_fail", "status": "fail", "duration_ms": 1, "exit_code": 1}
  ]
}
```

### JUnit XML (`--junit`)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="ritzunit" tests="3" failures="1" errors="0" time="0.003">
  <testcase name="test_add_single_item" time="0.001"/>
  <testcase name="test_add_increments_quantity" time="0.001"/>
  <testcase name="test_should_fail" time="0.001">
    <failure message="exit code 1">Test assertion failed</failure>
  </testcase>
</testsuite>
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed |
| N > 0 | N tests failed/crashed/timed out |

## Architecture

Ritzunit discovers tests at runtime by:

1. Reading `/proc/self/exe` to access the current binary
2. Parsing ELF headers to find the symbol table
3. Finding all functions starting with `test_`
4. Handling PIE/ASLR by detecting base address from `/proc/self/maps`
5. Running each test in a forked process for isolation

## Building from Source

```bash
# Ensure ritz submodule is initialized
git submodule update --init

# Build the inventory tests example
./build_inventory_tests.sh
```

## Debugging Tests

```bash
# Run without fork isolation (see crashes directly)
./tests --no-fork -f "test_that_crashes"

# Run under GDB
gdb -ex run --args ./tests --no-fork -f "test_that_crashes"
```

## License

See LICENSE file.
