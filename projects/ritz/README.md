# Ritz

A minimalistic, type-safe systems programming language with ownership semantics and modern ergonomics.

**Part of the [Ritz Ecosystem](docs/ECOSYSTEM.md)**

## Overview

Ritz is a systems programming language designed to be used everywhere - from bare-metal kernel development to high-level web application code. It uses Python-style indentation with no semicolons or braces, static typing with extensive type inference, and Rust-inspired ownership semantics with a simpler surface syntax.

The compiler is developed in three stages: `ritz0` is a Python bootstrap compiler
that implements enough of the language to compile the self-hosted `ritz1`
compiler; `ritz1_selfhosted` is `ritz1` compiled by `ritz1`. All three exist and
are exercised by the regression matrix. `examples/` holds **82** example packages
(directories with a `ritz.toml`) across five tiers — not the "48 graduated
examples" this README claimed for months.

The standard library (`ritzlib`) is co-located with the compiler and provides system calls, I/O, string handling, memory management, collections, async I/O, JSON, and more.

## Features

- Indentation-based syntax - no semicolons, no braces
- Static types with extensive type inference
- Ownership and borrowing without verbose annotations
- One language from kernel to application code
- Self-hosting compiler written in Ritz
- 82 example packages across 5 tiers (`examples/tier1_basics` … `tier5_async`)
- LLVM backend for optimized native code generation
- Bootstrappable - compiler distributed as LLVM IR

## Installation

The compiler lives in the `rz` monorepo; there is no separate `ritz` repository.

```bash
git clone git@github.com:ritz-lang/rz.git
cd rz/projects/ritz
```

`ritz0` is interpreted Python — there is nothing to build, and **no `ritz0` make
target exists**. (`make ritz0` exits 0 printing
`make: Nothing to be done for 'ritz0'` because `make` matches the `ritz0/`
*directory*. That is a false success, not a build.)

```bash
# Build ritz1 (self-hosted compiler, compiled by ritz0)
make -C ritz1 ritz1

# Build ritz1_selfhosted (ritz1 compiled by itself)
make -C ritz1 bootstrap

# Confirm both binaries compile a program
make -C ritz1 verify

# Regression matrix across all three compilers (~35s)
make matrix-full

# ritz0 Python unit tests, 58 pytest files (~2 min)
make unit

# Everything: doc examples, unit tests, language tests, every example.
# Slow, and NOT run as part of the 2026-09-12 verification pass — treat its
# outcome as unknown until you run it.
make test
```

Note that `make ritz1` at this level does **not** build anything — it runs
ritz1's lexer test suite (`build.py ritz1-tests`). Use `make -C ritz1 ritz1` to
build the binary.

## Usage

There is no `ritz` executable. The tools are the workspace CLI `./rz` at the
monorepo root and `build.py` here; a project scaffolder (`ritz new`) does not
exist.

```bash
# From the monorepo root (cd ../.. if you followed Installation above)
# — build / test / run any workspace project
./rz list
./rz build ritz
./rz run sage        # `rz run` only works when a [[bin]] is named after the
                     # project; otherwise it exits 1 with
                     # "Could not find binary for '<project>'"

# From projects/ritz — build.py drives packages directly.
# It takes a PATH to the package, never a bare name:
export RITZ_PATH=$PWD
python3 build.py build examples/tier2_stdlib/12_tac   # exit 0
python3 build.py build 12_tac                         # exit 1: "Package '12_tac' not found"

# Test a single package
python3 build.py test examples/tier2_stdlib/12_tac

# Build and test every package (slow — this is what `make examples` runs)
python3 build.py test --all

# Compile and run one file
python3 build.py run examples/tier1_basics/01_hello/src/main.ritz

# Other packaging subcommands
python3 build.py list
python3 build.py cache-status
```

```ritz
import ritzlib.io

fn main() -> i32
    print("Hello, Ritz\n")
    0
```

```ritz
import ritzlib.sys
import ritzlib.io

fn main(argc: i32, argv: **u8) -> i32
    let name: *u8 = *(argv + 1)
    prints("Hello, ")
    prints(name)
    prints("!\n")
    0
```

## Dependencies

- Python 3.10+ (for ritz0 bootstrap compiler)
- clang/LLVM 20 or newer (for code generation and linking)
- `ld` and `make` (for build orchestration and linking)
- `lld` — only needed for harland's UEFI bootloader, not for the compiler itself

## Status

**Active development.** The bootstrap is closed: `ritz1` builds, it recompiles
itself into `ritz1_selfhosted`, and the regression matrix runs all three stages.
`make -C ritz1 verify` confirms both Ritz-built binaries compile a program.

Don't trust a hardcoded table here — this one claimed "48/48 examples" and
"self-hosting blocked on one example" for months after the bootstrap closed.
Run the gate and read its output:

```bash
make matrix-full
```

Measured 2026-09-12, exit 0: `ritz0 53/53`, `ritz1 52/53`,
`ritz1_selfhosted 52/53`. The single failure is `test_issue_float_coercion`
(ritz1 has no float method dispatch, **AGAST #1370**), explicitly excused, which
is why the gate is green — *exit 0 does not mean 53/53 on every stage*.

`ritz2`, an optimizing compiler, is a future idea with no code.

## License

MIT License - see LICENSE file
