# Ritz Compiler Status

## Compilers

### ritz0 (Bootstrap Compiler)
**Language:** Python
**Status:** ✅ Stable, feature-complete for Tier 1

**Features:**
- Full lexer with indentation-based syntax
- Pratt parser with operator precedence
- LLVM IR emission via llvmlite
- Import system for multi-file compilation
- Testing framework with `@test` attributes
- Built-in functions: `print()`, `syscall0-6`
- Tier 1 language features:
  - Functions, structs, enums
  - Primitives: i8, i16, i32, i64, bool
  - Arrays (fixed-size): `[T; N]`
  - Pointers and references
  - Control flow: if, while, for, match
  - String literals
  - Syscalls (inline assembly)

**CLI Flags:**
```bash
python ritz0/ritz0.py [options] <source.ritz>

Options:
  -o, --output FILE     Output .ll file (required for compile)
  --test                Run tests in file
  --test-all            Run all tests in test/ directory
  -v, --verbose         Verbose output
  --lib FILE ...        Include library files
  --text-ir             Use ritz1/ir text backend instead of llvmlite
  --no-runtime          Don't emit _start (for libraries)
```

**Testing:**
```bash
# Compile a program
python ritz0/ritz0.py examples/02_exitcode/src/main.ritz -o /tmp/prog.ll

# Run tests
python ritz0/ritz0.py --test ritz/tests/test_lexer.ritz

# Multi-file compilation
python ritz0/ritz0.py main.ritz --lib lib1.ritz lib2.ritz -o out.ll
```

---

### ritz1 (Self-Hosting Compiler)
**Language:** Ritz (compiled by ritz0)
**Status:** 🚧 Partial, A/B testing in progress

**Working Features:**
- ✅ Lexer (NFA-based regex patterns)
- ✅ Parser (recursive descent + Pratt)
- ✅ Basic IR emission
- ✅ Simple programs (return literal values)
- ✅ Arithmetic expressions
- ✅ Binary operators (+, -, *, /, ==, !=, <, >, <=, >=)

**Missing/Broken Features:**
- ❌ `print()` builtin (crashes/generates invalid IR)
- ❌ String literals (partially broken)
- ❌ Function calls (untested)
- ❌ Syscalls (not implemented)
- ❌ Control flow (if, while, for)
- ❌ Structs
- ❌ Arrays
- ❌ Multi-file compilation (no import support)

**Compilation:**
```bash
# Compile ritz1 with ritz0
./ritz1/compile.sh

# Use ritz1 to compile a program
/tmp/ritz1 examples/02_exitcode/src/main.ritz -o output.ll
```

**CLI Flags:**
```bash
/tmp/ritz1 [-v] input.ritz -o output.ll

Options:
  -v          Verbose output
  -o FILE     Output .ll file (required)
```

---

## Bootstrap Testing

### A/B Test Suite
**Purpose:** Compare ritz0 vs ritz1 compiled outputs

**Script:** `scripts/bootstrap_test.sh`

**Test Method:**
- **Path A:** Compile example with ritz0 → binary A
- **Path B:** Compile ritz1 with ritz0, compile example with ritz1 → binary B
- **Compare:** Exit codes and output must match

**Current Results:**

| Example | Status | Notes |
|---------|--------|-------|
| 02_exitcode | ✅ PASS | Returns 42 |
| 04_true | ✅ PASS | Returns 0 |
| 04_false | ✅ PASS | Returns 1 |
| 01_hello | ❌ FAIL | `print()` not implemented |
| 03_echo | ⚠️ SKIP | String handling needed |
| 05_cat | ⚠️ SKIP | File I/O syscalls needed |
| 06_head | ⚠️ SKIP | String/I/O needed |
| 07_wc | ⚠️ SKIP | String/I/O needed |
| 08_seq | ⚠️ SKIP | Loops/formatting needed |
| 09_yes | ⚠️ SKIP | Strings/loops needed |
| 10_sleep | ⚠️ SKIP | Syscalls/structs needed |

**Summary:** 3/11 passing (27%)

---

## Roadmap to Full Bootstrap

### Phase 1: Fix ritz1 IR Emission (Current)
**Goal:** Pass all Tier 1 A/B tests

Priority issues:
1. ❗ Fix `print()` builtin support
2. ❗ String literal handling
3. ❗ Function call code generation
4. ❗ Syscall inline assembly
5. Control flow (if, while, for)
6. Struct support
7. Array support

### Phase 2: Self-Compilation
**Goal:** ritz1 compiles ritz1

Steps:
1. Compile ritz1 with ritz0 → ritz1_gen1
2. Compile ritz1 with ritz1_gen1 → ritz1_gen2
3. Verify: ritz1_gen1 and ritz1_gen2 produce identical IR

**Blockers:**
- All Phase 1 issues must be fixed
- ritz1 source uses all Tier 1 features

### Phase 3: Tier 2 Examples
**Goal:** Bootstrap compiler handles production programs

Examples (11-20):
- Text processing (grep, sort, uniq)
- Data formatting (json, base64)
- System utilities (env, which, basename)

### Phase 4: ritz2 (Full Language)
**Goal:** Production-ready compiler with advanced features

New features:
- Generics
- Method syntax
- Interfaces (`iface`)
- Better error messages
- Modules/packages
- Standard library

---

## Testing Infrastructure

### Unit Tests
- **Location:** `ritz/tests/`
- **Framework:** Built-in `@test` attribute
- **Command:** `python build.py ritz-tests`
- **Coverage:** 123 tests across 13 levels

### Integration Tests
- **Tier 1:** `make examples` (10 examples)
- **Bootstrap:** `./scripts/bootstrap_test.sh`
- **A/B Single:** `./scripts/ab_test.sh <file.ritz>`

### Memory Testing
```bash
make valgrind  # Run examples under valgrind
```

---

## Build Artifacts

### Runtime
- **ritz_crt0.ll** - C-style runtime with _start
- **ritz_crt0.o** - Pre-compiled object file
- Links with compiled .o files to create executables

### Compilation Pipeline
```
source.ritz
    ↓ ritz0/ritz1
LLVM IR (.ll)
    ↓ llc
Assembly (.s) or Object (.o)
    ↓ ld.lld
Executable
```

### Linking
```bash
# Method 1: Link with runtime
ld.lld --nostdlib program.o ritz_crt0.o -o program -e _start

# Method 2: Standalone (include _start in .ll)
python ritz0/ritz0.py program.ritz -o program.ll  # includes _start
llc -filetype=obj program.ll -o program.o
ld.lld --nostdlib program.o -o program -e _start
```

---

## Documentation TODO

- [ ] Language specification (syntax, semantics)
- [ ] Standard library API
- [ ] Compiler internals (phases, IR design)
- [ ] Contribution guide
- [ ] Examples tutorial

---

## Issue Tracking

**Repository:** https://github.com/ritz-lang/ritz

**Issue Categories:**
- Bootstrap blockers (High priority)
- Language features (Medium)
- Optimization (Low)
- Documentation (Low)

**Current sprint:** Fix ritz1 to pass Tier 1 A/B tests
