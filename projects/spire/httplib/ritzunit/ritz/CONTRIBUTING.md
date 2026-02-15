# Contributing to Ritz

Welcome to the Ritz language project! This document describes our development process, including test-driven development practices, verification requirements, and multi-project coordination.

## Table of Contents

1. [Development Philosophy](#development-philosophy)
2. [Multi-Project Ecosystem](#multi-project-ecosystem)
3. [Submodule Workflow](#submodule-workflow)
4. [Test-Driven Development](#test-driven-development)
5. [Verification Pipeline](#verification-pipeline)
6. [Code Style](#code-style)
7. [Commit Guidelines](#commit-guidelines)
8. [Pull Request Process](#pull-request-process)

---

## Development Philosophy

The Ritz project follows strict principles documented in `docs/DOCTRINE.md`:

### No Concessions Doctrine

> "Never make concessions for the language - we are MAKING the language."

- Fix language issues at the root, don't work around them
- If something doesn't work, it's a bug to be fixed
- No special cases for "known broken" patterns

### Ghost Doctrine

> "Warnings are the ghosts of future production outages."

- Fix anomalies when discovered, not later
- Track issues properly in GitHub
- Test flakiness must be investigated immediately

---

## Multi-Project Ecosystem

The Ritz ecosystem consists of multiple projects that depend on the core language:

| Project | Description | Repository |
|---------|-------------|------------|
| **langdev** | Core Ritz language (ritz0, ritz1, ritzlib) | `ritz-lang/ritz` |
| **valet** | High-performance HTTP server | `nevelis/valet` |
| **cryptosec** | Cryptographic & security libraries | `nevelis/cryptosec` |

### Project Independence

Each project should:
1. Add `ritz-lang/ritz` as a Git submodule
2. Maintain its own copy of the Ritz compiler
3. Coordinate language patches via the submodule workflow

---

## Submodule Workflow

Projects that need language changes follow this workflow:

### Setting Up a Submodule

```bash
# In your project root
git submodule add https://github.com/ritz-lang/ritz.git ritz
git commit -m "Add ritz language as submodule"
```

### Making Language Patches

When you need to patch the Ritz language:

```bash
# 1. Enter the submodule
cd ritz

# 2. Create a feature branch
git checkout -b my-feature-patch

# 3. Make changes, following TDD process (see below)
# ... write tests, implement, verify ...

# 4. Commit changes
git commit -m "feat: Add X feature for Y use case"

# 5. Push to your fork
git push origin my-feature-patch

# 6. Create PR to ritz-lang/ritz main branch
# 7. In parent project, update submodule reference
cd ..
git add ritz
git commit -m "Update ritz submodule to feature branch"
```

### Rebasing Submodule Branches

When upstream `ritz-lang/ritz` merges your PR or has new changes:

```bash
cd ritz

# Fetch latest from upstream
git fetch origin

# Rebase your patches onto main
git checkout my-feature-patch
git rebase origin/main

# If all your patches are merged:
git checkout main
git pull origin main

# Update parent project
cd ..
git add ritz
git commit -m "Update ritz submodule to latest main"
```

---

## Test-Driven Development

All Ritz development follows strict TDD. See `docs/TESTING.md` for test syntax.

### TDD Cycle

```
1. SPEC    → Define the behavior in a test
2. FAIL    → Run test, verify it fails for the right reason
3. IMPL    → Write minimal code to pass the test
4. PASS    → Run test, verify it passes
5. REFAC   → Clean up while tests stay green
6. VERIFY  → Run full verification pipeline
7. COMMIT  → Document the change
```

### Test Levels

| Level | Features | Examples |
|-------|----------|----------|
| 1 | Basic programs | exit codes, arithmetic, print |
| 2 | Functions | params, returns, recursion |
| 3 | Control flow | if/else, while, break |
| 4 | Structs | fields, pointers, methods |
| 5 | Imports | single, multi, ritzlib |
| 6 | Generics | Vec<T>, generic functions |

### Running Tests

```bash
# Full test suite
make test

# Unit tests only (ritz0 Python tests)
make unit

# Language tests (.ritz files)
make ritz

# ritz1 self-hosted tests
make ritz1

# Build and test all examples
make examples

# Test individual example
make test-hello
make test-05_cat
```

### Dual-Compiler Tests

The `test/dual_compiler/` directory contains tests that must pass on both ritz0 (Python) and ritz1 (self-hosted):

```bash
# Run dual-compiler tests
cd test/dual_compiler
./run_tests.sh

# Run specific level
./run_tests.sh 1

# Verbose output
./run_tests.sh -v
```

---

## Verification Pipeline

Before any code can be merged, it must pass the full verification pipeline.

### Quick Verification (Local Development)

```bash
# Run during active development
make test
```

### Full Verification (Before PR)

```bash
# Complete regression suite (all 4 stages)
make regression

# Quick mode (skip self-hosted bootstrap)
make regression-quick
```

### Regression Stages

| Stage | Description | What it Tests |
|-------|-------------|---------------|
| 1 | Compile examples with ritz0 | Python compiler correctness |
| 2 | Compile ritz1 with ritz0 | Self-hosted compiler builds |
| 3 | Compile examples with ritz1 | Self-hosted produces same output |
| 4 | Self-hosted bootstrap | ritz1 compiles itself correctly |

### Memory Verification

Use valgrind to check for memory leaks:

```bash
# Run valgrind on Tier 1 examples
make valgrind
```

This runs:
```bash
valgrind --error-exitcode=1 --leak-check=full -q <binary>
```

**Valgrind Requirements:**
- Exit code 0 (no errors detected)
- No memory leaks
- No invalid memory access
- No uninitialized value usage

### Adding Valgrind Checks

For new examples, add valgrind verification:

```bash
# In example's test.sh
#!/bin/bash
set -e

# Build
../../ritz build .

# Run with valgrind
valgrind --error-exitcode=1 --leak-check=full -q ./myprogram "$@"

# Verify output
./myprogram | diff - expected_output.txt
```

### CI Expectations

All PRs must:
1. Pass `make test` (all tests green)
2. Pass `make regression-quick` (stages 1-3)
3. Pass `make valgrind` (no memory leaks)
4. Have no compiler warnings

For significant changes, also run `make regression` (full 4-stage).

---

## Code Style

### Ritz Code Style

```ritz
# Function definitions - expression body for simple functions
fn add(a: i32, b: i32) -> i32 = a + b

# Block body for complex functions
fn process(input: &Span<u8>) -> Result<Output, Error>
    let parsed = parse(input)?
    let validated = validate(parsed)?
    Ok(transform(validated))

# Naming conventions
fn snake_case_functions()
struct PascalCaseTypes
let snake_case_variables
const SCREAMING_SNAKE_CONSTANTS

# Line length: 100 characters max
# Indentation: 4 spaces (enforced by lexer)
```

### Python Code Style (ritz0)

```python
# Follow PEP 8
# Use type hints
def compile_expr(self, expr: Expr, ctx: Context) -> str:
    ...

# Docstrings for public functions
def emit_function(self, func: FuncDef) -> None:
    """Emit LLVM IR for a function definition."""
    ...
```

### Test File Conventions

Each test has a `.ritz` file and optional `.expected` file:

```
test_foo.ritz      # Source code
test_foo.expected  # Expected output format:
                   # stdout lines...
                   # EXIT:<code>
```

---

## Commit Guidelines

### Commit Message Format

```
<scope>: <type> <description>

[optional body]

[optional footer]
```

**Scopes:** `ritz0`, `ritz1`, `ritzlib`, `docs`, `examples`, `test`

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `refactor` - Code restructuring
- `docs` - Documentation only
- `test` - Test additions/changes
- `perf` - Performance improvement

### Examples

```
ritz0: feat Add pub visibility modifier

Implements pub keyword for export visibility:
- Lexer recognizes pub token
- Parser handles pub fn, pub struct, pub enum
- AST nodes track visibility

ritzlib: fix Memory leak in Vec::pop

The internal buffer was not being freed when
the last element was popped and capacity > 16.

Fixes #123
```

### Commit Checklist

Before committing:
- [ ] Tests pass (`make test`)
- [ ] No new warnings
- [ ] Code follows style guide
- [ ] Commit message is descriptive
- [ ] Related issue referenced (if applicable)

---

## Pull Request Process

### Creating a PR

1. **Fork the repository** (for external contributors)

2. **Create a feature branch**
   ```bash
   git checkout -b feat-description
   ```

3. **Develop using TDD**
   - Write failing tests
   - Implement
   - Verify all tests pass

4. **Run full verification**
   ```bash
   make test
   make regression-quick
   make valgrind
   ```

5. **Push and create PR**
   ```bash
   git push origin feat-description
   ```

### PR Requirements

- [ ] Clear description of changes
- [ ] Tests for new functionality
- [ ] All CI checks pass
- [ ] Documentation updated (if API changes)
- [ ] No merge conflicts with main

### PR Template

```markdown
## Summary

Brief description of what this PR does.

## Changes

- Added X
- Fixed Y
- Updated Z

## Test Plan

- [ ] New tests added for feature
- [ ] `make test` passes
- [ ] `make regression-quick` passes
- [ ] `make valgrind` passes

## Related Issues

Fixes #123
```

### Review Process

1. Maintainer reviews code
2. CI runs verification pipeline
3. Address feedback
4. Squash commits if requested
5. Merge when approved

---

## Getting Help

- **Issues:** Create a GitHub issue for bugs or feature requests
- **Discussions:** Use GitHub Discussions for questions
- **Documentation:** See `docs/` directory for detailed guides

### Key Documentation

| Document | Purpose |
|----------|---------|
| `docs/LANGUAGE.md` | Language specification |
| `docs/DOCTRINE.md` | Development principles |
| `docs/TESTING.md` | Test syntax and practices |
| `docs/BOOTSTRAP.md` | Self-hosting strategy |
| `docs/RITZLIB.md` | Standard library reference |

---

*Last updated: 2026-01-13*
