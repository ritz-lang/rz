# Dual-Compiler Test Suite

This directory contains tests that run on both ritz0 (Python bootstrap) and ritz1 (self-hosted).

## Purpose

1. **Regression Prevention**: Ensure both compilers produce correct, consistent output
2. **Bootstrap Validation**: Verify ritz1 can eventually compile itself
3. **Feature Parity**: Track which features work in ritz0 vs ritz1

## Test Levels

| Level | Description | Features Tested |
|-------|-------------|-----------------|
| 1 | Basic programs | exit codes, arithmetic, print |
| 2 | Functions | params, returns, recursion |
| 3 | Control flow | if/else, while, break |
| 4 | Structs | fields, pointers, methods |
| 5 | Imports | single, multi, ritzlib |
| 6 | Generics | Vec<T>, generic functions |

## Running Tests

```bash
# Run all tests on both compilers
./run_tests.sh

# Run specific level
./run_tests.sh 1

# Run with verbose output
./run_tests.sh -v

# Run only ritz0 tests
./run_tests.sh --ritz0-only

# Run only ritz1 tests
./run_tests.sh --ritz1-only
```

## Adding Tests

Each test is a `.ritz` file with a corresponding `.expected` file:
- `test_foo.ritz` - the source code
- `test_foo.expected` - expected stdout + exit code

Test format:
```
# Expected output lines
EXIT:0
```

If a test requires linking with ritzlib, add a `.deps` file listing dependencies.
