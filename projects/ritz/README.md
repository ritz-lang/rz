# Ritz

A minimalistic, type-safe systems programming language with ownership semantics and modern ergonomics.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

## Overview

Ritz is a systems programming language designed to be used everywhere - from bare-metal kernel development to high-level web application code. It uses Python-style indentation with no semicolons or braces, static typing with extensive type inference, and Rust-inspired ownership semantics with a simpler surface syntax.

The compiler is developed in two stages: `ritz0` is a Python bootstrap compiler that implements enough of the language to compile the self-hosted `ritz1` compiler. Once `ritz1` can compile itself, the bootstrap is complete. The project currently ships 48 graduated example programs as the language test suite.

The standard library (`ritzlib`) is co-located with the compiler and provides system calls, I/O, string handling, memory management, collections, async I/O, JSON, and more.

## Features

- Indentation-based syntax - no semicolons, no braces
- Static types with extensive type inference
- Ownership and borrowing without verbose annotations
- One language from kernel to application code
- Self-hosting compiler written in Ritz
- 48 graduated example programs (Tier 1-8)
- LLVM backend for optimized native code generation
- Bootstrappable - compiler distributed as LLVM IR

## Installation

```bash
# Clone the repository
git clone https://github.com/ritz-lang/ritz.git
cd ritz

# Build ritz0 (Python bootstrap compiler)
make ritz0

# Build ritz1 (self-hosted compiler, compiled by ritz0)
make ritz1

# Run the full test suite
make test
```

## Usage

```bash
# Create a new project
./ritz new myproject
cd myproject

# Build and run
./ritz build
./ritz run src/main.ritz

# Run tests
./ritz test

# Build a specific package
./ritz build 12_tac

# Test all packages
./ritz test --all

# Check language test suite
./ritz check
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
- clang/LLVM 20 (for code generation and linking)
- make (for build orchestration)

## Status

**Active development** - ritz0 (Python bootstrap) passes all 48 example programs. ritz1 (self-hosted compiler) passes 47/48 examples; self-hosting (ritz1 compiling itself) is the next milestone.

| Stage | Description | Status |
|-------|-------------|--------|
| ritz0 | Python bootstrap compiler | 48/48 examples |
| ritz1 | Self-hosted compiler (compiled by ritz0) | 47/48 examples |
| Self-hosting | ritz1 compiles itself | Blocked on one example |
| ritz2 | Optimizing compiler (future) | Planned |

## License

MIT License - see LICENSE file
