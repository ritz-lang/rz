# Ritzunit

A modern unit testing framework for the Ritz programming language with ELF-based test discovery and fork isolation.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

## Overview

Ritzunit is the standard testing framework for Ritz projects. It discovers tests automatically at runtime by parsing the ELF symbol table of the compiled test binary - no test registration required. Tests marked with the `@test` attribute are found and run without any boilerplate.

Each test runs in a forked process for complete isolation: a crashing test cannot affect other tests or the runner. Ritzunit supports rich filtering with glob patterns and boolean expressions, and outputs results in human-readable, JSON, or JUnit XML formats for CI/CD integration.

The framework handles ASLR and PIE (position-independent executables) correctly by reading the base address from `/proc/self/maps` before resolving symbol addresses.

## Features

- Automatic test discovery via ELF symbol table parsing - no registration needed
- Fork-based process isolation - crashes don't abort the test run
- Glob pattern and boolean expression filtering
- Attribute-based test tagging via naming conventions (`@slow`, `@ignore`, `@fast`)
- JSON output for tooling integration
- JUnit XML output for CI/CD systems
- Configurable per-test timeouts
- Shuffle mode with reproducible seeds
- Fail-fast mode for quick feedback
- ANSI color output with TTY auto-detection

## Installation

```bash
# Build from source (requires ritz compiler)
export RITZ_PATH=/path/to/ritz
./ritz build .

# The library is available as a dependency in ritz.toml:
# [dependencies]
# ritzunit = { path = "../ritzunit" }
```

## Usage

```ritz
import ritzlib.sys

@test
fn test_addition() -> i32
    if 2 + 2 != 4
        return 1  # FAIL
    return 0      # PASS

@test
fn test_string_length() -> i32
    let s: *u8 = "hello"
    if strlen(s) != 5
        return 1
    return 0
```

```bash
# Run all tests
./build/debug/myproject-tests

# Verbose output
./build/debug/myproject-tests -v

# Filter by glob pattern
./build/debug/myproject-tests -f "test_add*"

# Boolean filter expressions
./build/debug/myproject-tests -f "add and not slow"

# JSON output
./build/debug/myproject-tests --json

# JUnit XML for CI
./build/debug/myproject-tests --junit
```

## CLI Reference

```
Usage: ritzunit [OPTIONS]

Options:
  -v, --verbose        Show detailed output
  -q, --quiet          Minimal output (failures + summary only)
  -l, --list           List tests without running them
  -h, --help           Show this help message
  -f, --filter=EXPR    Filter tests by expression
  -t, --timeout=MS     Timeout per test in milliseconds (default: 5000)
  -x, --fail-fast      Stop on first test failure
  -s, --shuffle        Randomize test execution order
      --seed=N         Random seed for shuffling (0 = auto)
  -j, --json           Output results in JSON format
      --junit          Output results in JUnit XML format
      --no-fork        Disable fork isolation (for debugging)
```

## Dependencies

- `ritzlib` - Standard library

## Status

**Production** - Used by goliath, cryptosec, spire, spectree, squeeze, and other ecosystem projects. ELF self-discovery, fork isolation, filtering, and output formats are all working.

## License

MIT License - see LICENSE file
