# ritz0 Testing Framework

The ritz0 bootstrap compiler includes a comprehensive testing framework for validating language features through executable tests.

## Quick Start

### Run all tests
```bash
python ritz0.py --test-all
```

### Run all tests with verbose output
```bash
python ritz0.py --test-all -v
```

### Run specific test files
```bash
python ritz0.py --test test/test_level1.ritz test/test_level2.ritz -v
```

### Run tests using test_runner directly
```bash
python test_runner.py test/test_level*.ritz -v
```

## Test Framework Architecture

### Components

1. **Lexer** (`lexer.py`)
   - Tokenizes Ritz source code
   - Emits NEWLINE tokens to delimit statements
   - Recognizes `@test` attribute syntax

2. **Parser** (`parser.py`)
   - Parses `@test` function attributes
   - Parses `assert` statements for test assertions
   - Handles indentation-based syntax with proper NEWLINE handling

3. **AST** (`ritz_ast.py`)
   - `Attr` node for function attributes
   - `AssertStmt` node for assertion statements
   - `FnDef.has_attr(name)` for checking function attributes

4. **Emitter** (`emitter_llvmlite.py`)
   - Generates LLVM IR for test functions
   - Compiles `assert` statements to `exit(1)` syscall on failure
   - Enforces that `assert` only appears in `@test` functions

5. **Test Runner** (`test_runner.py`)
   - Discovers `@test` functions in source files
   - Creates test harnesses (main functions that call tests)
   - Compiles each test to machine code (LLVM IR → asm → binary)
   - Executes binary and checks exit code (0 = pass, non-zero = fail)
   - Reports results with optional verbose output

## Test Levels

### Level 1: Basic Arithmetic (12 tests)
- Operators: `+`, `-`, `*`, `/`
- Comparisons: `==`, `!=`, `<`, `>`, `<=`, `>=`
- Parentheses for precedence
- All arithmetic operations implemented

**Files:** `test/test_level1.ritz`

### Level 2: Variables & Pointers (7 tests)
- `let` (immutable) bindings
- `var` (mutable) bindings
- Pointer dereferencing: `*ptr`
- Pointer assignment: `*ptr = value`
- Type annotations: `: i32`, `: *i32`

**Files:** `test/test_level2.ritz`

### Level 3: Function Calls (11 tests)
- Function definitions: `fn name(args) -> return_type`
- Function calls: `name(args)`
- Function parameters
- Return statements
- Nested calls
- Recursive functions (fibonacci)

**Files:** `test/test_level3.ritz`

### Level 4: String Literals & Operations (12 tests)
- String literals with double quotes: `"hello"`
- Escape sequences: `\n`, `\t`, `\\`, `\"`, `\0`
- String as pointer to i8: `let s: *i8 = "hello"`
- Pointer arithmetic: `s + i`
- String length calculation
- String comparison (streq pattern)

**Files:** `test/test_level4.ritz`

### Level 5: Arrays (4 tests)
- Fixed-size array types: `[i32; 4]`
- Array literals: `[1, 2, 3, 4]`
- Array indexing: `arr[i]` for read/write
- Type-safe array initialization (auto type conversion)

**Files:** `test/test_level5.ritz`

### Level 6: Process Control (3 tests)
- Generic syscall builtins: `syscall0()`, `syscall1()`, ..., `syscall6()`
- Fork syscall (57): spawn child process
- Waitpid syscall (61): wait for child and get exit code
- Exit codes as process results

**Files:** `test/test_level6.ritz`

## Test Harness Mechanism

Each test function:

```ritz
@test
fn test_example() -> i32
  assert condition
  0
```

Is compiled with a generated main:

```ritz
fn main() -> i32
  test_example()
```

The test harness:
1. Calls the test function
2. Returns its result (0 = success, non-zero = failure)
3. `assert` statements internally call `exit(1)` on failure

## Emitted Behavior

### Assert Statement
```ritz
assert x == 5
```

Expands to:
```llvm
if (x == 5) is false:
  call exit(1)  ; via syscall
else:
  continue
```

The process exits with code 1, which causes the test runner to mark it as FAIL.

### Success Behavior
If all assertions pass, test function returns 0, process exits with code 0 → test passes.

## Test Execution Flow

```
ritz0.py --test-all
  ├─ discover_tests()
  │   └─ glob test/test_level*.ritz
  ├─ run_test_file() for each file
  │   ├─ find_test_functions()
  │   │   ├─ lex + parse source
  │   │   └─ collect @test functions
  │   └─ for each test function:
  │       ├─ Create harness source (source + main)
  │       ├─ Emit LLVM IR
  │       ├─ llc: IR → machine code
  │       ├─ ld: link to executable
  │       ├─ Execute binary
  │       └─ Check exit code
  └─ Report summary (N passed, M failed)
```

## Total Test Coverage

**49 tests passing across 6 levels:**

| Level | File | Tests | Status |
|-------|------|-------|--------|
| 1 | test_level1.ritz | 12 | ✓ All passing |
| 2 | test_level2.ritz | 7 | ✓ All passing |
| 3 | test_level3.ritz | 11 | ✓ All passing |
| 4 | test_level4.ritz | 12 | ✓ All passing |
| 5 | test_level5.ritz | 4 | ✓ All passing |
| 6 | test_level6.ritz | 3 | ✓ All passing |
| **Total** | | **49** | **✓ All passing** |

## Additional Test Suites

### Unit Tests (Python)

**Lexer tests:** `test_lexer.py`
```bash
pytest ritz0/test_lexer.py -v
```
- 28 lexer tests
- Token type validation
- Indentation handling
- String escape sequences
- Number literal parsing

**Parser tests:** `test_parser.py`
```bash
pytest ritz0/test_parser.py -v
```
- 39 parser tests
- AST construction validation
- Type annotation parsing
- Statement/expression parsing
- Error detection

## Extending the Test Framework

### Creating New Test Levels

1. Create `test/test_levelN.ritz`
2. Define test functions with `@test` attribute:
```ritz
@test
fn test_feature() -> i32
  let result = ...
  assert result == expected
  0
```

3. Run with:
```bash
python ritz0.py --test test/test_levelN.ritz -v
```

### Features That Enable Tests

- NEWLINE tokens for multi-statement support
- Function attributes (`@test`)
- Assert statements with exit on failure
- String literals with escape sequences
- Pointers and pointer arithmetic
- Arrays and indexing
- Process control syscalls (fork/waitpid)

## Troubleshooting

### Test hangs/timeout
- Check for infinite loops in test code
- Default timeout: 10 seconds per test
- Most likely cause: `while` loop without proper exit condition

### Assertion failures
- Test runner shows exit code
- Check test logic carefully
- Use `--test file.ritz -v` to see which assertion fails

### Compilation failures
- Check LLVM IR generation with: `python ritz0.py file.ritz -o out.ll`
- Use `llvm-dis out.ll` to see readable IR
- Common issues: unimplemented operators, missing syscalls

## Performance Notes

- Full test suite (49 tests) takes ~5-10 seconds to run
- Compile per-test (LLVM → binary)
- No caching between tests
- Each test is an independent binary
