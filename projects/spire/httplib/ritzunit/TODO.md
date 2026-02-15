# Ritzunit TODO

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

## Phase 3: Filter Expressions (Partial)
- [x] Glob pattern matching (`test_add*`, `*remove*`, `test_?_foo`)
- [x] Suite::test syntax (inventory::test_add) - parses and matches test part
- [ ] Boolean expressions (and, or, not)
- [ ] Attribute filters (@ignore, @slow)

## Phase 4: Advanced Features (Partial)
- [x] Test shuffling (`-s/--shuffle`, `--seed N`)
- [x] Fail-fast mode (`-x/--fail-fast`)
- [x] JSON output (`-j/--json`)
- [ ] Parallel test execution (--jobs N)
- [ ] JUnit XML output (--junit report.xml)

## Phase 5: Polish
- [ ] Improve failure messages with source locations
- [ ] Add color detection (disable for non-TTY)
- [ ] Add ANSI color support (requires \x escape sequences in ritz)
- [ ] Create man page / --help documentation
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
  - ANSI color codes require workaround (build strings with raw bytes)
- ~~**sizeof(T) bug in generics**~~ - FIXED in PR #91
  - Was: ritz0 uses pointer size (8) instead of actual type size
  - Fix: substitute type params in sizeof() during monomorphization
  - PR: https://github.com/ritz-lang/ritz/pull/91
