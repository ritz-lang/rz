# Ritzunit DONE

## 2026-01-13: Initial Project Setup

### Project Structure
- [x] Created ritzunit project directory structure
- [x] Set up ritz.toml package manifests for ritzunit and inventory demo
- [x] Created src/, test/, inventory/src/, inventory/test/ directories

### Core Types & Assertions
- [x] Created src/types.ritz with TestResult, TestSummary structs
- [x] Created src/assertions.ritz with assertion functions:
  - assert_true, assert_false
  - assert_eq_i32, assert_eq_i64, assert_ne_i32, assert_ne_i64
  - assert_lt_i32, assert_le_i32, assert_gt_i32, assert_ge_i32
  - assert_str_eq, assert_starts_with, assert_contains
  - assert_null, assert_not_null

### Reporter
- [x] Created src/reporter.ritz with visual output functions:
  - ANSI color support (green/red/yellow/cyan)
  - Unicode status symbols (✓ ✗ ⊘ ⚡)
  - Banner, suite headers, test results, summary

### Inventory Demo Application
- [x] Created inventory/src/lib.ritz with:
  - Item struct (name as Vec<u8>, quantity as i32)
  - Inventory struct with Vec<Item>
  - inventory_new(), inventory_drop()
  - inventory_add(), inventory_remove()
  - inventory_count(), inventory_has(), inventory_len()
  - inventory_clear(), inventory_total_quantity()
  - str_eq_ptr() utility function

### Inventory Unit Tests
- [x] Created inventory/test/test_inventory.ritz with 18 tests:
  - test_new_inventory_is_empty
  - test_add_single_item
  - test_add_increments_quantity
  - test_add_multiple_different_items
  - test_remove_decrements_quantity
  - test_remove_insufficient_returns_error
  - test_remove_nonexistent_returns_error
  - test_remove_exact_quantity
  - test_has_returns_false_for_missing
  - test_has_returns_false_for_zero_quantity
  - test_count_returns_zero_for_missing
  - test_len_tracks_unique_items
  - test_clear_removes_all_items
  - test_total_quantity
  - test_total_quantity_empty
  - test_add_zero_quantity
  - test_large_quantities

## 2026-01-13: Runtime Build & Self-Test Framework

### Runtime Build
- [x] Created ritz_start.x86_64.ll for programs with main(argc, argv)
- [x] Created ritz_start_noargs.x86_64.ll for programs with main()
- [x] Built runtime object files for linking

### Self-Test Suite
- [x] Created test/test_assertions.ritz with 23 self-contained tests
- [x] All 23 assertion tests pass using ritz0 test runner
- [x] Tests cover: assert_true, assert_false, assert_eq_i32, assert_ne_i32
- [x] Tests cover: assert_lt_i32, assert_le_i32, assert_gt_i32, assert_ge_i32
- [x] Meta-tests verify assertion failure detection

### ELF-Based Test Runner
- [x] Created src/runner.ritz with self-discovery architecture
- [x] Reads /proc/self/exe to parse own ELF binary
- [x] Discovers test_* functions from symbol table
- [x] Inline assembly call mechanism for test execution

## 2026-01-13: Ritz Submodule & String Interpolation

### Git Submodule
- [x] Added ritz-lang/ritz as git submodule at `ritz/`

### String Interpolation Refactoring
- [x] Discovered ritz native string interpolation: `"text {variable} more"`
- [x] Refactored src/reporter.ritz to use interpolation
  - Replaced 50+ individual print calls with clean interpolated strings
  - Much cleaner, more readable output formatting
- [x] Refactored src/assertions.ritz to use interpolation
  - Cleaner failure messages with embedded values

## 2026-01-13: Inventory Tests Fixed

### Vec<u8> in Struct Bug Workaround
- [x] Identified bug: nested Vec<u8> inside struct loses data when struct pushed to Vec<T>
- [x] Created test/test_vec_string.ritz to isolate and confirm the issue
- [x] Rewrote inventory tests to use fixed-size `[32]u8` arrays for item names
- [x] All 17 inventory tests now pass
- [x] Item struct simplified:
  ```ritz
  struct Item
      name: [32]u8       # Fixed-size name buffer
      name_len: i64      # Actual name length
      quantity: i32      # Current quantity
  ```

## 2026-01-13: Function Pointer Casting (No More Inline Assembly!)

### Discovery
- Tested and confirmed ritz supports casting addresses to function pointer types:
  - `*u8 as fn() -> i32` ✓
  - `i64 as *u8`, then `*u8 as fn() -> i32` ✓
  - `i64 as fn() -> i32` (direct) ✓

### Runner Refactored
- Removed inline assembly from `src/runner.ritz`
- Now uses clean ritz function pointer casting:
  ```ritz
  fn run_test(entry: *TestEntry) -> i32
      let test_fn: fn() -> i32 = entry.addr as fn() -> i32
      return test_fn()
  ```
- This is idiomatic ritz - no platform-specific assembly needed!

## 2026-01-13: ELF Self-Discovery Working! 🎉

### PIE/ASLR Support
- [x] Discovered that PIE executables need base address offset
- [x] Symbol table values are virtual addresses, not runtime addresses
- [x] Implemented `detect_base_address()` parsing /proc/self/maps
- [x] Runtime address = base_address + symbol_virtual_address

### Test Runner v2
- [x] Created `test/runner_test_v2.ritz` - standalone self-discovering test runner
- [x] Successfully discovers 4 test_* functions at runtime
- [x] Correctly calls each test via function pointer with PIE offset
- [x] All 4 tests pass!
- [x] Verified failure detection works (intentionally broken test reports FAIL)

### Updated Main Runner
- [x] Updated `src/runner.ritz` with PIE base address detection
- [x] Global `g_base_addr` stores detected load base
- [x] `run_test()` computes runtime address before casting to fn pointer

### Test Output Example
```
=== ritzunit self-discovery test v2 ===

PIE base address: 0x98742141394944
Discovered 4 test(s):

Running: test_addition
  Symbol VA=0x28160 + base -> runtime=0x98742141423104
  -> OK
Running: test_simple_pass
  -> OK
Running: test_comparison
  -> OK
Running: test_memory_ops
  -> OK

4 passed, 0 failed
```

## 2026-01-13: Multi-File Test Discovery & Reporter Integration

### Multi-File Test Discovery
- [x] Proved ELF discovery works across multiple source files
- [x] Created `test/test_math.ritz` with 4 additional tests
- [x] Built binary linking `runner_test_v2.ritz` + `test_math.ritz`
- [x] Successfully discovered 8 tests from both files!
- [x] Test output:
  ```
  Discovered 8 test(s):
  - test_addition (runner_test_v2)
  - test_multiplication (test_math)
  - test_simple_pass (runner_test_v2)
  - test_comparison (runner_test_v2)
  - test_memory_ops (runner_test_v2)
  - test_division (test_math)
  - test_modulo (test_math)
  - test_negative (test_math)

  8 passed, 0 failed
  ```

### Reporter Integration
- [x] Simplified `src/reporter.ritz` to use ASCII output (ritz lacks `\x` escapes)
- [x] Full integration with `src/runner.ritz` and `src/types.ritz`
- [x] Created `build_inventory_tests.sh` for complete build workflow
- [x] All 17 inventory tests pass with beautiful output:
  ```
  ======================================================
    RITZUNIT v0.1.0 - Test Framework for Ritz
  ======================================================

  --- Tests ---
    [OK] test_remove_decrements_quantity (0ms)
    [OK] test_has_returns_false_for_zero_quantity (0ms)
    ... (15 more tests)

  ------------------------------------------------------

  Results: 17 passed
  Time:    0ms
  ```

### Build Infrastructure
- [x] Created `ritzlib` symlink for import resolution
- [x] Created `build_multifile_test.sh` demonstrating multi-file discovery
- [x] Created `build_inventory_tests.sh` for full ritzunit + inventory tests
- [x] Build scripts use `list_deps.py` to collect all dependencies automatically

### Key Architecture Insight
The ELF-based self-discovery approach naturally supports multi-file tests:
1. All test files are compiled to `.ll` with `--no-runtime`
2. Files are linked together into a single binary
3. ELF symbol table contains ALL `test_*` functions from ALL linked files
4. Runner's `discover_tests()` finds them all at runtime

This is the same approach used by unittest++ and other C++ test frameworks!

## 2026-01-13: Valgrind Analysis & Compiler Bug Discovery

### Valgrind Testing
- [x] Ran inventory tests under valgrind to check for memory issues
- [x] Discovered heap corruption in `vec_push$Item`

### ritz0 Compiler Bug Identified
- [x] **Bug**: `sizeof(T)` in generic functions uses pointer size (8) instead of actual type size
- [x] Example: `Vec<Item>` where Item is 48 bytes, but vec_grow allocates `new_cap * 8` bytes
- [x] Generated LLVM IR shows: `mul i64 %new_cap, 8` instead of `mul i64 %new_cap, 48`
- [x] Impact: Vec<T> corrupts heap for any T larger than 8 bytes
- [x] Documented in `known_issues/sizeof_generic_bug.ritz`
- [x] Debug metadata correctly shows `Item size: 384 bits (48 bytes)` - only sizeof(T) codegen is wrong

### Verification
- [x] Created `test/test_sizeof.ritz` to confirm sizeof(Item) = 48 at runtime
- [x] Struct layout verified: name@0 (32B), name_len@32 (8B), quantity@40 (4B), padding to 48B
- [x] The tests "pass" without valgrind because the heap corruption doesn't always cause crashes

### Bug Fix (PR #91)
- [x] Created branch `fix-sizeof-generic-type` in ritz submodule
- [x] Fixed `ritz0/monomorph.py` to substitute type params in sizeof() args
- [x] Added `ritz0/test/test_sizeof_generic.ritz` with 4 test cases
- [x] Verified fix with valgrind - no more heap corruption!
- [x] PR: https://github.com/ritz-lang/ritz/pull/91

## 2026-01-13: CLI Argument Parsing

### Phase 1 Complete
- [x] Added CLI argument parsing using `ritzlib.args`
- [x] Implemented options:
  - `-v/--verbose` - Show test names as they run
  - `-q/--quiet` - Minimal output (failures + summary only)
  - `-f/--filter PATTERN` - Run only tests matching substring
  - `-l/--list` - List discovered tests without running
  - `-h/--help` - Show help message
- [x] Filter shows count of skipped tests
- [x] Verbose mode shows "Running: test_name... OK (Xms)"
- [x] Quiet mode shows only failures and final summary

### Example Usage
```bash
./build/inventory_tests --help
./build/inventory_tests --list
./build/inventory_tests --filter add        # Only run tests containing "add"
./build/inventory_tests --quiet             # Minimal output
./build/inventory_tests --verbose --filter remove
```

## 2026-01-13: Fork-Based Test Isolation

### Wait Status Helpers
- [x] Added wait status functions to ritzlib/sys.ritz:
  - WIFEXITED(status) - check if child exited normally
  - WEXITSTATUS(status) - get exit code
  - WIFSIGNALED(status) - check if killed by signal
  - WTERMSIG(status) - get terminating signal
  - WIFSTOPPED(status) - check if stopped
  - WSTOPSIG(status) - get stop signal

### Fork Isolation Implementation
- [x] Implemented `run_test_forked()` in src/runner.ritz:
  - Parent forks for each test
  - Child executes test and exits with result
  - Parent waits with timeout (polling via WNOHANG)
  - Catches signal termination (SIGSEGV, SIGABRT, etc.)
  - Kills child and reports TIMEOUT if exceeded
- [x] Added `TestRunResult` struct with status, exit_code, signal fields
- [x] Test result types: PASS, FAIL, SIGNAL, TIMEOUT

### CLI Options
- [x] Added `-t/--timeout MS` option (default: 5000ms)
- [x] Added `--no-fork` option to disable isolation
- [x] Updated help text and parse_args()

### Signal Reporting
- [x] Added `signal_name()` helper for human-readable signal names
- [x] Output shows `[CRASH] test_name - SIGSEGV (11)` for crashes
- [x] Output shows `[TIMEOUT] test_name (exceeded Nms)` for timeouts
- [x] Verbose mode shows inline: `Running: test_name... CRASHED (SIGSEGV)`

### Isolation Tests
- [x] Created test/test_isolation.ritz with:
  - Normal passing tests
  - Intentional assertion failures
  - Null pointer crash tests (SIGSEGV)
  - Infinite loop timeout tests
  - Tests that run after crashes (verify runner continues)
- [x] Created build_isolation_tests.sh

### Test Results
All 17 inventory tests pass with fork isolation (19ms overhead vs 0ms without).
Isolation tests verify:
- Crashes are caught and reported (SIGSEGV)
- Timeouts are enforced and killed
- Assertion failures show exit code
- Runner continues after crashes

## 2026-01-13: Improved Test Output Format

### Right-Aligned Status Output
- [x] Updated reporter for right-aligned status with dot leaders
- [x] Format: `  test_name ................................... OK (1ms)`
- [x] Different status formats: OK, FAIL, CRASH, TIMEOUT, SKIP

### Suite Grouping & Summaries
- [x] Suite header at start of test output
- [x] Per-suite divider and summary
- [x] Summary shows: passed, failed, crashed, timeout counts
- [x] Grand total summary with all categories

### Updated TestSummary Struct
- [x] Added `crashed` and `timeout` fields for granular tracking
- [x] Added `summary_merge()` for combining suite results
- [x] Exit code now returns sum of failures + crashes + timeouts

### Example Output
```
======================================================================
  RITZUNIT v0.1.0 - Test Framework for Ritz
======================================================================

tests
  test_normal_pass .......................................... OK (1ms)
  test_assertion_failure ......................... FAIL [code=42] (1ms)
  test_null_pointer_crash ........................... CRASH (SIGSEGV) (77ms)
  test_infinite_loop_timeout ....................... TIMEOUT (500ms)
  ----------------------------------------------------------------------
  4 tests: 1 passed, 1 failed, 1 crashed, 1 timeout (579ms)

======================================================================
TOTAL: 4 tests | 1 passed | 1 failed | 1 crashed | 1 timeout (579ms)
======================================================================
```
