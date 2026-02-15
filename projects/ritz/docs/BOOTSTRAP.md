# Ritz Bootstrap Strategy

## Overview

Ritz uses a three-stage bootstrap to achieve self-hosting with minimal external dependencies.

```
ritz0 (Python)     →  ritz1 (Ritz subset)  →  ritz2 (full Ritz)
implements:           implements:              implements:
  minimal language      full language            full language + stdlib
  no generics           generics                 optimizations
  basic borrow check    full borrow check        self-hosted

written in:           written in:              written in:
  Python                ritz0-subset             ritz1

emits:                emits:                   emits:
  LLVM IR               LLVM IR                  LLVM IR (identical)
```

## Stage A: ritz0 (Python Bootstrap)

A minimal compiler written in Python (~2-3k lines) that emits LLVM IR.

### Components

| Component | Lines | Purpose |
|-----------|-------|---------|
| Lexer | ~300 | Tokenize `.ritz` source |
| Parser | ~800 | Pratt parser → AST |
| Type Checker | ~600 | Inference, no generics |
| Borrow Checker | ~400 | Basic ownership, no complex lifetimes |
| IR Emitter | ~500 | Text `.ll` output |

### ritz0 Language Subset

**Supported:**
```
struct, enum, fn, let, var, if, else, while, for, match
&T, &mut T, T (move)
Result[T, E], Option[T], ? operator
i8/i16/i32/i64, u8/u16/u32/u64, f32/f64, bool, Str
extern fn (for libc: malloc, free, read, write, exit)
unsafe blocks
*const T, *mut T (raw pointers)
```

**NOT Supported (deferred to ritz1+):**
```
generics (except built-in Result/Option)
iface
method syntax (use fn Type_method(self: &Type) instead)
operator overloading
closures
```

### Output

- `ritz1.ll` — the ritz1 compiler as LLVM IR
- `runtime0.ll` — minimal runtime intrinsics

## Stage B: ritz1 (Ritz Subset Compiler)

Written in ritz0-subset, compiled by ritz0. Implements the full language.

### Features Added

- Full generics: `Vec[T]`, `Map[K, V]`
- Method syntax: `v.push(42)`
- `iface` for dynamic dispatch
- Full borrow checker with region inference

### Usage

```bash
# Bootstrap ritz1
python ritz0.py ritz1.ritz -o ritz1.ll
llvm-as ritz1.ll -o ritz1.bc
clang ritz1.bc -o ritz1
```

## Stage C: ritz2 (Full Self-Hosted Compiler)

Written in full Ritz, compiled by ritz1. This is the production compiler.

### Features Added

- Optimizations
- Better diagnostics
- GPU lowering (future)
- JIT support (future)

### Usage

```bash
./ritz1 build ritz2.ritz -o ritz2
```

## Reproducible IR

To achieve identical IR output when compiling the compiler with itself:

1. **Stable symbol mangling** — deterministic name generation
2. **Ordered iteration** — use ordered maps, not hash maps
3. **No timestamps/paths** — don't embed build metadata
4. **Canonical debug info** — or strip it in "repro mode"
5. **Fixed LLVM passes** — version-pin the optimization pipeline

## Release Artifact

Ship:
- `ritz2.ll` — the compiler as LLVM IR
- `core.ll` — minimal runtime/ABI glue

Build script requires only:
- `llvm-as` — assemble IR to bitcode
- `llc` or `clang` — compile to native

No Python required after bootstrap.

## Build Flow Example

```bash
# One-time bootstrap (done once by maintainers)
python ritz0.py ritz1.ritz -o ritz1.ll
llvm-as ritz1.ll -o ritz1.bc
clang ritz1.bc -o ritz1

# Build production compiler
./ritz1 build ritz2.ritz -o ritz2

# Verify reproducibility
./ritz2 build ritz2.ritz -o ritz2-check.ll
diff ritz2.ll ritz2-check.ll  # should be identical

# Build anything else with full language
./ritz2 build myproject/
```
