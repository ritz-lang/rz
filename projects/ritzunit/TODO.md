# Ritzunit TODO

## Phase 6: RERITZ Syntax Migration (Partial)

Modernizing ritzunit to RERITZ syntax per `/home/aaron/dev/ritz-lang/ritz-amd64/RERITZ.md`.

**Note:** Only converting `@test` → `[[test]]` for now. The address-of syntax (`&` → `@`)
is part of the "Reference philosophy" phase which is NOT started in the ritz compiler yet.

### Completed
- [x] Convert `@test` → `[[test]]` in `inventory/test/test_inventory.ritz`
- [x] Update build script with `RITZ_SYNTAX=reritz` environment variable
- [x] Fix duplicate `print_char` symbol in json_reporter.ritz (renamed to `json_print_char`)
- [x] Verify build and tests pass (24/24 tests passing)

### Deferred (waiting on ritz compiler support)
- [ ] Address-of: `&x` → `@x` (requires "Reference philosophy" phase)
- [ ] Mutable borrow params: `data: &mut T` → `data:& T`
- [ ] Const borrow params: `data: &T` → `data: T` (just the type)
- [ ] Reference types: `&T` → `@T`, `&mut T` → `@&T`

---

## Phase 1: Core Framework ✓
- [x] Create runner.ritz with ELF-based self-discovery
- [x] Read /proc/self/exe and parse ELF symbol table
- [x] Discover test_* functions from symbol table
- [x] Call test functions using function pointer casting (no inline assembly!)
- [x] Created self-test suite (23 passing tests)
- [x] Built runtime object files for linking
- [x] Fixed inventory tests (17 passing) - workaround for Vec<u8>-in-struct bug
- [x] Build standalone test binary with ELF discovery
- [x] Handle PIE/ASLR by detecting base address from /proc/self/maps
- [x] Integrate reporter for visual output (full runner with types/reporter imports)
- [x] Created working demo: test/runner_test_v2.ritz
- [x] Multi-file test discovery working (8 tests from 2 files)
- [x] CLI argument parsing using ritzlib.args:
  - `-v/--verbose` - show test names as they run
  - `-q/--quiet` - minimal output (failures + summary only)
  - `-f/--filter PATTERN` - run only tests matching substring
  - `-l/--list` - list tests without running
  - `-h/--help` - show help message

## Phase 2: Test Execution ✓
- [x] Implement timing for individual tests (get_time_ms() via gettimeofday)
- [x] Add timeout support with configurable limits (`-t/--timeout MS`)
- [x] Handle test isolation via fork (fresh state per test)
- [x] Capture and report crashes gracefully (SIGSEGV, SIGABRT, etc.)
- [x] Added `--no-fork` option to disable isolation for debugging

## Phase 3: Filter Expressions ✓
- [x] Glob pattern matching (`test_add*`, `*remove*`, `test_?_foo`)
- [x] Suite::test syntax (inventory::test_add) - parses and matches test part
- [x] Boolean expressions (`and`, `or`, `not`)
  - `test_add* and not *slow*` - match tests starting with test_add but not containing slow
  - `json or add` - match tests containing json OR add
  - `not add` - match all tests NOT containing add
- [x] Attribute filters via naming convention:
  - `@slow` - matches tests with "slow" in name
  - `@ignore` / `@skip` - matches tests with "ignore" in name
  - `@fast` - matches tests NOT marked as @slow
  - Can combine with boolean: `@fast and not @ignore`

## Phase 4: Advanced Features ✓
- [x] Test shuffling (`-s/--shuffle`, `--seed N`)
- [x] Fail-fast mode (`-x/--fail-fast`)
- [x] JSON output (`-j/--json`)
- [x] JUnit XML output (`--junit`)
  - Compatible with Jenkins, GitLab CI, etc.
  - Supports failure/error elements with messages

## Phase 4b: Future Features
- [ ] Parallel test execution (--jobs N) - requires careful IPC design

## Phase 5: Polish ✓
- [x] ANSI color support with TTY detection
  - Auto-detects TTY using ioctl(TIOCGWINSZ)
  - `--color` to force colors on
  - `--no-color` to disable colors
  - Green for pass, red for fail/crash, yellow for timeout/skip
- [x] Created README.md with full documentation
  - CLI reference
  - Filter expression guide
  - Output format examples
  - Debugging tips

## Future Work
- [ ] Improve failure messages with source locations
- [ ] Write self-tests for ritzunit

## Inventory Demo
- [x] Create Inventory struct with Vec<Item>
- [x] Implement add, remove, count, has, clear operations
- [x] Write comprehensive unit tests (17 tests with fixed-size arrays)
- [x] Add serialization tests (4 tests: to_json for empty, single, multiple, quantities)

## Known Issues
- Vec<u8> inside struct loses data when struct pushed to Vec<T>
  - Documented in known_issues/test_vec_string.ritz
  - Workaround: use fixed-size arrays `[N]u8` instead
- Ritz string escape sequences don't support `\x` hex escapes
  - ANSI color codes use workaround: print ESC (27) as raw byte
- ~~**sizeof(T) bug in generics**~~ - FIXED in PR #91
  - Was: ritz0 uses pointer size (8) instead of actual type size
  - Fix: substitute type params in sizeof() during monomorphization
  - PR: https://github.com/ritz-lang/ritz/pull/91
