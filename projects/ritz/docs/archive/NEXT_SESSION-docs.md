# Next Session: Ritz Compiler Development

## Quick Start

```bash
cd /home/aaron/dev/nevelis/langdev

# Verify ritz0 works (should pass 48/48)
./test_examples.sh

# Build ritz1 compiler
cd ritz1 && make clean && make && cd ..

# Test ritz1 on examples (needs RITZ_PATH)
RITZ_PATH=/home/aaron/dev/nevelis/langdev build/ritz1 examples/01_hello/src/main.ritz -o /tmp/hello.ll
llc /tmp/hello.ll -o /tmp/hello.s
gcc /tmp/hello.s -o build/hello -nostartfiles -static
build/hello  # Should print "Hello, Ritz!"
```

## Current State (December 31, 2024)

### Compilation Pipeline Status

| Stage | Description | Status | Pass Rate |
|-------|-------------|--------|-----------|
| 1 | ritz0 compiles all examples | ✅ | **48/48** |
| 2 | ritz0 compiles ritz1 | ✅ | **working** |
| 3 | ritz1 compiles all examples | ⚠️ | **47/48** |
| 4 | ritz1 compiles ritz1 (bootstrap) | ❌ | blocked |

### Compilation Model

The unified compilation model is:

```
.ritz → .ll → link → binary
```

Each `.ritz` file compiles to its own `.ll` file:
- Functions from the current file: `define` (full body)
- Functions from imports: `declare` (external reference)
- Linking: `clang` links all `.ll` files together

**Build commands:**
```bash
# Using the ritz CLI (recommended)
python3 ritz build 12_tac          # Build a specific example
python3 ritz build --all           # Build all examples
python3 ritz test 12_tac           # Build and test

# Direct ritz0 usage
python3 ritz0/ritz0.py examples/01_hello/src/main.ritz -o output.ll
```

### Key Environment Variable

**RITZ_PATH** must point to the **parent** directory of ritzlib:
```bash
export RITZ_PATH=/home/aaron/dev/nevelis/langdev
# Import "ritzlib.sys" resolves to: $RITZ_PATH/ritzlib/sys.ritz
```

## Recent Fixes (Session 11-12)

### Session 12: Struct Return Type Fix
- **Problem:** ritz1 segfaulted on functions returning structs
- **Root cause:** `fn_return_type_name` was never set in the parser
- **Fix:** Added `capture_fn_return_type()` helper to `ast_helpers.ritz`
- **Result:** Stage 3 improved from 36/48 to **47/48**

### Session 11: Metadata Constant Values Fix
- **Problem:** Imported constants had value 0 instead of actual value
- **Root cause:** `ConstMeta` didn't store the `value` field
- **Fix:** Added `value: int` field to `ConstMeta` in `metadata.py`
- **Result:** Stage 3 improved from 0/48 to 36/48

### Session 10: Metadata-Based Incremental Compilation
- Integrated metadata caching into ritz0 import resolver
- Cached metadata now used to skip re-parsing unchanged imports
- ~7x faster second builds for multi-module projects

## Current Blockers

### 1. 49_ritzgen Stack Overflow (Stage 3: 47/48)
The only failing Stage 3 example is `49_ritzgen` which has deep import recursion causing stack overflow in ritz1. The ritz1 import resolver uses recursive function calls with ~64KB stack allocation per import level.

**Workaround:** Use ritz0 to build ritzgen instead of ritz1.

### 2. ritzgen Grammar Action Limitation
The current `ritzgen_old` binary doesn't properly generate function calls in simple semantic actions. The grammar has:
```
return_type -> i32
    : ARROW type_spec { capture_fn_return_type(p, $2) }
    ;
```

But ritzgen generates `return result_2` instead of `return capture_fn_return_type(p, result_2)`.

**Workaround:** Manual edit to `parser_gen.ritz` after regeneration.

### 3. parser_alloc Duplicate Symbol
Both `parser_gen.ritz` and `ast_helpers.ritz` defined `parser_alloc`.

**Fix Applied:** Removed `parser_alloc` generation from ritzgen codegen. The function now only exists in `ast_helpers.ritz`.

## Key Files

| File | Purpose |
|------|---------|
| `ritz0/ritz0.py` | Bootstrap compiler (Python + llvmlite) |
| `ritz0/import_resolver.py` | Import resolution with metadata caching |
| `ritz0/metadata.py` | Module metadata extraction and caching |
| `ritz1/ritz1.grammar` | Grammar specification for ritz1 |
| `ritz1/src/parser_gen.ritz` | Generated parser (with manual patches) |
| `ritz1/src/ast_helpers.ritz` | Parser helper functions |
| `ritz1/src/main_new.ritz` | Main compiler with IR emission |
| `build.py` | Build system (separate compilation + linking) |
| `examples/49_ritzgen/` | Parser generator |

## Next Steps

1. **Fix ritzgen** to properly generate function call semantic actions
2. **Fix ritz1 stack overflow** in import resolver (use iterative approach)
3. **Stage 4:** Get ritz1 to compile itself (self-hosting)

## Testing Commands

```bash
# Stage 1: ritz0 examples
./test_examples.sh

# Stage 3: ritz1 examples
for ex in examples/*/src/main.ritz; do
  name=$(dirname $(dirname $ex) | xargs basename)
  echo -n "$name: "
  RITZ_PATH=/home/aaron/dev/nevelis/langdev build/ritz1 $ex -o /tmp/test.ll 2>/dev/null && echo "✓" || echo "✗"
done

# A/B test (compare ritz0 vs ritz1 output)
./scripts/ab_test.sh examples/01_hello/src/main.ritz
```

## Notes

- All 48 ritz0 examples pass (the "build" entry is not a real example)
- ritz1 at 47/48 (only 49_ritzgen fails)
- RITZ_PATH must point to langdev/, not langdev/ritzlib/
- /tmp may have noexec mount - use build/ directory for binaries
