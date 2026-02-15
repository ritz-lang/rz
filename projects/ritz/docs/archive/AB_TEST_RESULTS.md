# A/B Test Results: ritz0 vs ritz1

**Date:** 2024-12-24
**Test Harness:** `tools/ab_test.py`
**Comparison:** ritz0 (Python + llvmlite) vs ritz1 (Ritz IR emitter)

## Test Methodology

The A/B test harness compares both compilation paths on identical source:

1. **Path A:** ritz0 (Python) uses llvmlite to generate LLVM IR
2. **Path B:** ritz1 (Ritz compiler compiled by ritz0) generates LLVM IR as text

For each path:
- Compile source → LLVM IR (.ll)
- Compile IR → native binary (llc + gcc)
- Run binary and capture: exit code, stdout, stderr

**Pass criteria:** All three outputs must match exactly.

## Summary

| Example | Status | Exit A | Exit B | Stdout A | Stdout B | Stderr A | Stderr B |
|---------|--------|--------|--------|----------|----------|----------|----------|
| 01_hello | ✅ PASS | 0 | 0 | 13B | 13B | 0B | 0B |
| 02_exitcode | ✅ PASS | 42 | 42 | 0B | 0B | 0B | 0B |
| 03_echo | ❌ FAIL | 0 | 3 | 1B | 0B | 0B | 0B |
| 04_true_false/true | ✅ PASS | 0 | 0 | 0B | 0B | 0B | 0B |
| 04_true_false/false | ✅ PASS | 1 | 1 | 0B | 0B | 0B | 0B |
| 05_cat | ❌ FAIL | 0 | 5 | 0B | 0B | 0B | 0B |
| 06_head | ❌ FAIL | 0 | 6 | 0B | 0B | 0B | 0B |
| 07_wc | ❌ FAIL | 0 | 7 | 6B | 0B | 0B | 0B |
| 08_seq | ❌ FAIL | 1 | 8 | 0B | 0B | 0B | 0B |
| 09_yes | ❌ FAIL | -1 | 9 | 0B | 0B | 7B | 0B |
| 10_sleep | ❌ FAIL | 1 | 10 | 0B | 0B | 0B | 0B |

**Total:** 4/10 passing (40%)

## Analysis

### Working Examples (4/10)

✅ **01_hello** - Print "Hello, Ritz!\n"
```ritz
fn main() -> i32
  print("Hello, Ritz!\n")
  0
```
- **Why it works:** Parser detects `print("...")`, emits string constant + write syscall

✅ **02_exitcode** - Return exit code 42
```ritz
fn main() -> i32
  return 42
```
- **Why it works:** Parser detects `return` keyword, parses integer, emits correct exit code

✅ **04_true_false/true.ritz** - Exit code 0
```ritz
fn main() -> i32
  0
```
- **Why it works:** Single integer literal return, minimal parser handles this

✅ **04_true_false/false.ritz** - Exit code 1
```ritz
fn main() -> i32
  1
```
- **Why it works:** Single integer literal return, minimal parser handles this

### Failing Examples (6/10)

All failures are due to **missing parser features**, not IR generation bugs.

ritz1's current minimal parser (lines 139-430 in `ritz1/src/main.ritz`) supports:
- ✅ Return statements (`return 42`)
- ✅ String literals and escape sequences (`"Hello\n"`)
- ✅ print() built-in function
- ✅ Integer literals
- ✅ Comment skipping

Still missing:
- Variables (`var i: i32`)
- Control flow (`if`, `while`)
- String literals (`"hello"`)
- Expressions (binary ops, comparisons)
- Command-line args (`argc`, `argv`)

**Evidence:** All failures show Path B exiting with the line number where the first digit appears in the source (e.g., exit=2 for line 2, exit=3 for line 3), rather than the expected program behavior.

## Feature Roadmap (Prioritized by Example)

### Milestone 1: Return Statements
**Target:** 02_exitcode

**Missing features:**
- `return` keyword parsing
- Return statement AST handling

**Example:**
```ritz
fn main() -> i32
  return 42
```

**Complexity:** LOW (parser change only, IR backend already supports returns)

---

### Milestone 2: String Literals + Function Calls
**Target:** 01_hello

**Missing features:**
- String literal parsing (`"Hello, Ritz!\n"`)
- String constant emission in IR
- Function call parsing (`print(...)`)
- Argument expression lists
- Built-in function recognition (`print`)

**Example:**
```ritz
fn main() -> i32
  print("Hello, Ritz!\n")
  0
```

**Complexity:** MEDIUM (parser + IR string constants + call emission)

---

### Milestone 3: Variables + Expressions
**Target:** 03_echo (partial)

**Missing features:**
- Variable declarations (`var i: i32 = 1`)
- Binary operators (`i < argc`, `i + 1`)
- Assignment statements (`i = i + 1`)
- Type inference for `let` bindings

**Example:**
```ritz
fn main() -> i32
  var i: i32 = 0
  i = i + 42
  i
```

**Complexity:** MEDIUM (expression parser + SSA value tracking)

---

### Milestone 4: Control Flow
**Target:** 03_echo (full), 06_head, 08_seq

**Missing features:**
- While loops (`while condition { ... }`)
- If statements (`if condition { ... }`)
- Block parsing (curly braces)
- Comparison operators (`<`, `>`, `==`, `!=`)

**Example:**
```ritz
fn main() -> i32
  var i: i32 = 0
  while i < 10
    i = i + 1
  i
```

**Complexity:** HIGH (control flow graph, label management, phi nodes)

---

### Milestone 5: Pointers + Arrays
**Target:** 03_echo (argv), 05_cat, 06_head, 07_wc

**Missing features:**
- Pointer arithmetic (`argv[i]`, `buf + offset`)
- Array indexing (`s[len]`)
- Pointer dereferencing
- Address-of operator

**Example:**
```ritz
fn main(argc: i32, argv: **u8) -> i32
  let s = argv[1]
  var len: i32 = 0
  while s[len] != 0
    len = len + 1
  len
```

**Complexity:** HIGH (pointer GEP, type tracking)

---

### Milestone 6: Extern Functions + Syscalls
**Target:** 05_cat, 07_wc, 09_yes

**Missing features:**
- `extern fn` declarations
- Syscall invocation (via inline asm or builtins)
- Multi-parameter function calls

**Example:**
```ritz
extern fn write(fd: i32, buf: *u8, len: i64) -> i64

fn main() -> i32
  write(1, "Hello\n", 6)
  0
```

**Complexity:** MEDIUM (extern declaration parsing + call codegen)

---

### Milestone 7: Structs
**Target:** 10_sleep

**Missing features:**
- Struct definitions (`struct Timespec { ... }`)
- Struct literals (`Timespec { tv_sec: 1, tv_nsec: 0 }`)
- Struct field access (`.` operator)
- Struct layout in IR (already implemented in `ritz1/ir/struct_layout.ritz`!)

**Example:**
```ritz
struct Timespec
  tv_sec: i64
  tv_nsec: i64

fn main() -> i32
  let ts = Timespec { tv_sec: 1, tv_nsec: 0 }
  nanosleep(&ts, 0)
  0
```

**Complexity:** HIGH (parser + type system + struct IR already done)

---

## Next Steps

**Immediate action:** Implement Milestone 1 (return statements) to make 02_exitcode pass.

**Order of implementation:**
1. Return statements → 02_exitcode ✓
2. String literals + function calls → 01_hello ✓
3. Variables + expressions → Simple arithmetic programs
4. Control flow → 03_echo, 06_head, 08_seq ✓
5. Pointers + arrays → Full 03_echo, 05_cat, 07_wc ✓
6. Extern + syscalls → 05_cat, 09_yes ✓
7. Structs → 10_sleep ✓

**Testing strategy:**
- After each milestone, run A/B tests on ALL examples
- Document which new tests pass
- Regression test: ensure previously passing tests still pass
- Use A/B test output to guide debugging

**IR Backend Status:**
The `ritz1/ir/` backend (38 passing tests) is proven correct for:
- ✅ Basic types (i8, i16, i32, i64, ptr)
- ✅ Struct layout (field offsets, alignment, padding)
- ✅ Expression codegen (literals, binary ops, variables)
- ✅ Statement codegen (var, assign, return, if, while)
- ✅ Function definitions with parameters
- ✅ _start wrapper with exit syscall

**Missing from IR backend:**
- [ ] String constants (need @.str.N global variables)
- [ ] Function calls (need call instruction emission)
- [ ] Extern function declarations
- [ ] Multi-function modules
- [ ] GEP for pointers/arrays (partially done, needs array indexing)

**Focus:** Parser is the bottleneck. IR backend is ready for most features.
