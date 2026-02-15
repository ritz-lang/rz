# ritz1 - The Ritz Self-Hosting Compiler

The Ritz compiler written in Ritz, compiled by ritz0, growing incrementally towards full self-hosting.

## Status

✅ **Working!** Successfully compiles simple programs and passes A/B tests against ritz0.

**Current capabilities:**
- Parses minimal programs (single `main()` function returning an integer literal)
- Generates LLVM IR as text
- Bootstrapped: compiled by ritz0, emits IR for simple programs
- **Passing A/B tests:** `true.ritz`, `false.ritz` produce identical behavior to ritz0

**Growing towards:**
- Full Tier 1 example support (01_hello through 10_sleep)
- Complete ritz1 language implementation
- Self-hosting (ritz1 compiling ritz1)
- Foundation for ritz2 (full-featured compiler)

## The Big Picture

```
ritz0 (Python bootstrap)
  ↓ compiles
ritz1 source (Ritz subset)
  ↓ produces
ritz1_bootstrap
  ↓ compiles
ritz1 source
  ↓ produces
ritz1 (self-hosted!)
  ↓ compiles
ritz2 source (full Ritz)
  ↓ produces
ritz2
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  ritz1/src/main.ritz (314 lines)                        │
│  ────────────────────────────────────────────────────   │
│  1. Parser (currently minimal, will grow)               │
│  2. IR generation (uses ritz1/ir backend)               │
│  3. Syscall-based file I/O (no libc dependencies)       │
│  4. Compiled by ritz0 to native binary                  │
└─────────────────────────────────────────────────────────┘
         │
         │ ritz0 compiles
         ▼
┌─────────────────────────────────────────────────────────┐
│  ritz1/build/ritz1 binary (10KB)                        │
│  ────────────────────────────────────────────────────   │
│  • Reads .ritz source files                             │
│  • Emits LLVM IR text to output file                    │
│  • A/B tested against ritz0's llvmlite output           │
└─────────────────────────────────────────────────────────┘
         │
         │ uses proven backend
         ▼
┌─────────────────────────────────────────────────────────┐
│  ritz1/ir/ backend (~1650 lines, 38 tests)              │
│  ────────────────────────────────────────────────────   │
│  • IR builder with SSA tracking                         │
│  • LLVM-compatible struct layout                        │
│  • Expression/statement/function codegen                │
│  • No magic offsets - typed field access only           │
└─────────────────────────────────────────────────────────┘
```

## Build

```bash
cd ritz1
python ../ritz0/ritz0.py src/main.ritz -o build/ritz1.ll
llc -filetype=obj build/ritz1.ll -o build/ritz1.o
gcc -nostdlib -no-pie build/ritz1.o -o build/ritz1
```

## Usage

```bash
./build/ritz1 <input.ritz> -o <output.ll>
```

Example:
```bash
./build/ritz1 ../examples/04_true_false/src/true.ritz -o /tmp/true.ll
llc -filetype=obj /tmp/true.ll -o /tmp/true.o
gcc -nostdlib -no-pie /tmp/true.o -o /tmp/true
./tmp/true
echo $?  # 0
```

## A/B Testing

Verify that ritz1 produces binaries with identical behavior to ritz0:

```bash
# Test single file
python ../tools/ab_test.py ../examples/04_true_false/src/true.ritz

# Test multiple files
python ../tools/ab_test.py ../examples/04_true_false/src/*.ritz
```

**Current results:**
- ✅ `true.ritz` - Exit code 0
- ✅ `false.ritz` - Exit code 1

## Development Strategy

**Incremental growth, A/B tested at every step:**

### Phase 1: Foundation ✅ DONE
- [x] Minimal parser (integer literals only)
- [x] Basic IR emission
- [x] File I/O and command-line handling
- [x] A/B test harness working

### Phase 2: Tier 1 Example Support ⏳ CURRENT
Growing feature-by-feature to support all Tier 1 examples:

1. **String literals** → enables `01_hello`
   - [ ] String constant emission in IR
   - [ ] Function calls with arguments

2. **Variables & expressions** → enables `02_exitcode`
   - [ ] Variable declarations
   - [ ] Arithmetic expressions
   - [ ] Multiple return paths

3. **Control flow** → enables `04_true_false`
   - [ ] If/else statements
   - [ ] Boolean expressions

4. **Loops & arrays** → enables `03_echo`
   - [ ] While loops
   - [ ] Array indexing
   - [ ] Pointer arithmetic

5. **File I/O** → enables `05_cat`
   - [ ] Multiple syscalls
   - [ ] Buffer management

6. **Structs** → enables `10_sleep`
   - [ ] Struct type definitions
   - [ ] Struct literals
   - [ ] Field access

### Phase 3: Full Language ⏳ FUTURE
- [ ] Complete lexer/parser (proper tokenization)
- [ ] All ritz1 language features
- [ ] Self-hosting (ritz1 compiles ritz1)

## Why This Approach?

**Old ritz1** (archived in `ritz1_old/`):
- 7768 lines across 17 files
- Grammar DSL that ritz0 can't parse
- Magic struct offsets (Issue #3)
- Too complex to bootstrap all at once

**New ritz1** (this directory):
- Start minimal (314 lines)
- Use proven ritz1/ir backend (no magic offsets!)
- Grow feature-by-feature
- A/B tested at every step
- Working compiler at every stage

**Key insight:** Don't try to build everything at once. Build the smallest thing that works, validate it, then add the next feature.

## Contributing to ritz1

When adding a new feature:

1. **Pick a target example** (e.g., "I want to make 01_hello work")
2. **Identify missing features** (e.g., "need string literals + function calls")
3. **Implement incrementally**:
   - Extend the parser
   - Add IR generation
   - Compile with ritz0
4. **A/B test**: Verify ritz1 output matches ritz0
5. **Iterate**: Fix bugs, test edge cases

The `ritz1/ir/` backend is proven correct - focus on growing the parser and integration!

## Directory Structure

```
ritz1/
├── src/
│   └── main.ritz          # Main compiler implementation
├── ir/                    # Proven IR backend (from Phase 2.9)
│   ├── ir_builder.ritz    # LLVM IR text generation
│   ├── struct_layout.ritz # LLVM-compatible struct layout
│   ├── expr_codegen.ritz  # Expression code generation
│   ├── stmt_codegen.ritz  # Statement code generation
│   ├── function_codegen.ritz # Function/program generation
│   └── test_*.ritz        # 38 tests validating IR generation
├── build/
│   ├── ritz1              # Compiled ritz1 binary
│   ├── ritz1.ll           # Generated LLVM IR
│   └── ritz1.o            # Compiled object file
└── README.md              # This file
```

## See Also

- **ritz1_old/** - Archived original self-hosting attempt (reference implementation)
- **ritz0/** - Python bootstrap compiler
- **examples/** - Tier 1 example programs (test cases)
- **tools/ab_test.py** - A/B testing harness
