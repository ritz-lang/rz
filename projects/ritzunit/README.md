# Ritzunit

The test runner of every Ritz test binary: compiler-emitted test discovery and fork isolation.

**Part of the [Ritz Ecosystem](../ritz/docs/ECOSYSTEM.md)**

## Overview

Ritzunit is the `main` of every Ritz test binary (LANGUAGE_SPEC.md §17.1). The compiler, in test mode, emits a table of a test file's `[[test]]` functions; ritzunit runs each entry. No registration and no naming convention: `[[test]]` decides what is a test.

Each test runs in a forked process for complete isolation: a crashing test cannot affect other tests or the runner. Ritzunit supports rich filtering with glob patterns and boolean expressions, and outputs results in human-readable, JSON, or JUnit XML formats for CI/CD integration.

The framework handles ASLR and PIE (position-independent executables) correctly by reading the base address from `/proc/self/maps` before resolving symbol addresses.

## Features

- Discovery from the compiler's `[[test]]` table - no registration, no `test_` naming rule
- Each test's stdout/stderr captured; shown (and put in `--json`) only for tests that did not pass
- Exit status 0 iff every selected test passed, else 1
- Fork-based process isolation - crashes don't abort the test run
- `-j N`: up to N tests at once, each in its own child with its own capture; reported in run order, so the report does not depend on scheduling
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
# Run ritzunit's own tests
./rz test ritzunit

# The library is available as a dependency in ritz.toml:
# [dependencies]
# ritzunit = { path = "../ritzunit" }
```

## Usage

Mark tests with `[[test]]`. (`@test` was the old syntax and is no longer
correct — see `projects/ritz/docs/STYLE.md`.)

```ritz
import ritzlib.sys

[[test]]
fn test_addition() -> i32
    if 2 + 2 != 4
        return 1  # FAIL
    return 0      # PASS

[[test]]
fn test_string_length() -> i32
    let s: *u8 = "hello"
    if strlen(s) != 5
        return 1
    return 0
```

### Running tests

```bash
./rz test <project>
```

For each `test/*.ritz`, `ritz0 --test` builds one test binary: the file
compiled in test mode (`ritz0 --test-table`), linked with `src/bin_main.ritz`
and the runner as one object whose only global symbol is `main` (so the
runner's names cannot collide with yours), and runs it once with `--json`.
That logic lives in `projects/ritz/ritz0/test_runner.py` (`build_test_binary`).
A test binary takes the options below.

### CLI Reference

From a test binary's `--help`:

```
Usage: ritzunit [OPTIONS]

Unit test framework for Ritz

Options:
  -v, --verbose        Show detailed output
  -q, --quiet          Minimal output - only failures and summary
  -l, --list           List tests without running them
  -h, --help           Show this help message
  -f, --filter=EXPR    Filter tests by EXPR (glob, @attr, bool)
  -t, --timeout=MS     Timeout per test in milliseconds (default: 5000)
      --no-fork        Disable fork isolation (run tests in main process)
  -j, --jobs=N         Run up to N tests at once, each in its own child (default: 1)
  -x, --fail-fast      Stop on first test failure
  -s, --shuffle        Randomize test execution order
      --seed=N         Random seed for shuffling (0 = auto)
      --json           Output results in JSON format (no short form: -j is --jobs)
      --junit          Output results in JUnit XML format
      --color          Force colored output (even when not a TTY)
      --no-color       Disable colored output
```

## Dependencies

- `ritzlib` - Standard library

## Status

Runs every `./rz test` of every package under ritz0. ritz1 does not emit the test table yet (tracked in AGAST).

## License

MIT License - see LICENSE file
