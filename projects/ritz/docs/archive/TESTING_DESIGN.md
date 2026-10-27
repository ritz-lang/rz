# Ritz Testing Framework Design v2

## Principles

1. **No Concessions** - Improve the language, don't work around it
2. **Tests near code** - Unit tests next to what they test, integration tests next to integrations
3. **ELF discovery** - Discover tests from compiled symbols, not source parsing
4. **Ownership cleanup** - Process handles auto-cleanup via Drop
5. **Clean console output** - Pretty, iterative-friendly (JUnit deferred)
6. **No attribute soup** - Keep it minimal and readable
7. **No Java-style verbosity** - Simple, direct APIs

---

## Current State

### What Works

**Attributes**: `@test` and `@ignore` are parsed as `Attr` nodes
- `@test` marks functions as test targets
- `assert` statement only allowed in `@test` functions
- `FnDef.has_attr("test")` checks for attribute

**Test Discovery** (ritz0/test_runner.py):
- Parses source files to find `@test` functions
- Generates harness with main() that calls test
- Compiles and executes, checks exit code

**Test Library** (ritzlib/testing.ritz):
- `register_test()` / `run_all_tests()`
- Assertion helpers: `assert_msg()`, `assert_eq_i32()`, etc.

### What's Missing

1. **ELF-based discovery** - Currently parses source, should read symbols
2. **Subprocess testing** - For integration tests
3. **Before/after hooks** - Suite and test level setup/teardown
4. **Fixtures** - Temp files, environment setup

---

## Proposed Design

### Test Anatomy

```ritz
import ritzlib.testing
import ritzlib.process

@test
fn test_hello_output() -> i32
    # Spawn the program - ownership means auto-cleanup
    let proc = spawn(c"./hello")

    # Read all output (simple, no BufferedStreamReader nonsense)
    let output = proc.read_stdout()

    # Assert with clear intent
    assert output.contains(c"Hello")
    assert proc.wait().success()
    0
```

### Process API (Simple and Direct)

```ritz
# Spawn a process
fn spawn(cmd: *u8) -> Process
fn spawn_args(cmd: *u8, args: []*u8) -> Process

# Process operations
struct Process
    # ... internal fields

# Write to stdin
fn process_write(p: *Process, data: *u8, len: i64) -> i64
fn process_write_str(p: *Process, s: *u8) -> i64
fn process_close_stdin(p: *Process)

# Read from stdout/stderr (simple!)
fn process_read_stdout(p: *Process, buf: *u8, max: i64) -> i64
fn process_read_stdout_all(p: *Process) -> Span<u8>  # Allocates, returns all output
fn process_read_line(p: *Process) -> Span<u8>        # Read one line

# Wait and get result
fn process_wait(p: *Process) -> ProcessResult

struct ProcessResult
    exit_code: i32
    signaled: i32

fn result_success(r: *ProcessResult) -> bool
fn result_code(r: *ProcessResult) -> i32

# Drop trait for cleanup (when we have it)
# For now: explicit process_kill() if needed
fn process_kill(p: *Process)
```

### Before/After Hooks

Two levels of setup/teardown:

```ritz
# Suite level - runs once before/after all tests in file
@before_all
fn setup_suite() -> i32
    # Create temp directory, start server, etc.
    0

@after_all
fn teardown_suite() -> i32
    # Cleanup
    0

# Test level - runs before/after each test
@before_each
fn setup_test() -> i32
    0

@after_each
fn teardown_test() -> i32
    0

@test
fn test_something() -> i32
    # setup_test() already ran
    assert 1 == 1
    0
    # teardown_test() will run
```

**Alternative: Explicit fixtures** (simpler, no new attributes)

```ritz
# Just use helper functions - no magic
fn with_temp_file(content: *u8, body: fn(*u8) -> i32) -> i32
    let tf = temp_file_create(content)
    let result = body(temp_file_path(&tf))
    temp_file_delete(&tf)
    result

@test
fn test_cat_file() -> i32
    with_temp_file(c"hello\n", fn(path: *u8) -> i32
        let proc = spawn_args(c"./cat", [path])
        let out = process_read_stdout_all(&proc)
        assert span_eq_cstr(&out, c"hello\n")
        0
    )
```

### ELF Discovery

Instead of parsing source files, discover tests from compiled object files:

```bash
# Current (source parsing)
python test_runner.py test_level1.ritz

# Proposed (ELF symbol discovery)
ritz test test_level1.o   # Read symbols, find test_* functions
```

The compiler would:
1. Compile test files with `@test` functions
2. Export test functions with a known prefix (e.g., `__ritz_test_*`)
3. Test runner reads ELF symbols to find tests
4. Generates minimal main() that calls discovered tests

### Console Output

```
Running 12 tests from test_level1.ritz

  [OK] test_addition
  [OK] test_subtraction
  [FAIL] test_division_by_zero
         assert failed: expected != 0
         at test_level1.ritz:45
  [OK] test_multiplication
  ...

8 passed, 1 failed, 3 skipped

Failures:
  test_division_by_zero (test_level1.ritz:45)
    assert failed: expected != 0
```

---

## Migration Path

### Phase 1: Add Process API ✅ COMPLETE
- Created `ritzlib/process.ritz` (270 lines) with spawn/read/write/wait
- Functions: `spawn()`, `spawn_args()`, `spawn_full()`,
  `process_read_stdout_all()`, `process_read_line()`,
  `process_write()`, `process_wait()`, `process_cleanup()`
- Returns `Vec<u8>` for output (heap-allocated, owned, growable)
- Fixed parser_gen.py to properly handle `c"..."` and `s"..."` literals

### Phase 2: Convert Simple test.sh (Pending)
- Start with `01_hello/test.sh` → `01_hello/test/test_hello.ritz`
- Pattern: `./hello | grep -q "Hello"` → spawn + read_stdout + contains
- Integration test added but needs full compilation to verify

### Phase 3: ELF Discovery (Pending)
- Update compiler to emit test symbols with prefix (`__ritz_test_*`)
- Update test_runner to read ELF symbols via `nm` or similar
- Remove source-parsing discovery

### Phase 4: Before/After Hooks (Pending)
- Attribute-based approach preferred (`@before_all`, `@after_all`, etc.)
- Requires compiler support for new attributes

---

## Design Decisions Made

1. **Memory allocation** - `Vec<u8>` for output capture
   - Uses jemalloc-style allocator from `ritzlib/memory.ritz`
   - Grows dynamically, owned by caller
   - Cleanup via `vec_drop<u8>()` or future Drop trait

2. **Span<u8> for non-owning views** - When slicing or comparing
   - `span_from_vec<u8>(&output)` for comparisons
   - `span_contains()` for substring checks

3. **Attribute-based hooks** - Preferred over explicit fixtures
   - `@before_all` / `@after_all` for suite-level
   - `@before_each` / `@after_each` for test-level

4. **ELF discovery from start** - Tests run from compiled binary

---

## Open Questions

1. **Closures for fixtures** - Yes, closures exist (lambda implementation)
   - Can capture context for fixture patterns

2. **Drop trait for Process** - Manual cleanup for now (`process_cleanup()`)
   - Proper Drop impl waiting on generic impl block support

3. **Test filtering** - Deferred
   `ritz test test_level1.o --filter "test_add*"`

---

*Updated: February 2026*
