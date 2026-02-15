# Ritz Example Programs

A graduated suite of example programs. Each example demonstrates specific language features and serves as both documentation and regression tests.

**Status**: This document reflects the current state of examples as of February 2026.

---

## Current Structure

Examples are now organized by complexity tier in the following directory structure:

```
examples/
├── tier1_basics/       # Core language fundamentals
├── tier2_stdlib/       # Standard library usage
├── tier3_coreutils/    # Complete CLI utilities
├── tier4_applications/ # Multi-feature applications
└── tier5_async/        # Advanced async features
```

Within each tier, examples are numbered chronologically to show creation order. The numbering reflects when they were created, not their difficulty level.

### Legend
- ✅ Complete and tested
- 🔄 Works but needs cleanup
- ⚠️ Partial/experimental

---

## Tier 1: Core Language (01-10)

Basic syntax, functions, syscalls, control flow. No stdlib dependencies beyond `ritzlib.sys` and `ritzlib.io`.

| # | Name | Status | Features Demonstrated |
|---|------|--------|----------------------|
| 01 | hello | ✅ | `fn main`, print builtin, trailing expression return |
| 02 | exitcode | ✅ | Return values, exit codes |
| 03 | echo | ✅ | `argc`/`argv`, pointer arithmetic, loops |
| 04 | true_false | ✅ | Trivial programs, different exit codes |
| 05 | cat | ✅ | File I/O, syscalls, buffer loops |
| 06 | head | ✅ | Argument parsing (`-n`), line counting |
| 07 | wc | ✅ | State machines, byte/line/word counting |
| 08 | seq | ✅ | Integer formatting, ranges |
| 09 | yes | ✅ | Infinite loops |
| 10 | sleep | ✅ | Structs (`TimeSpec`), `nanosleep` syscall |

---

## Tier 2: Text Processing (11-20)

Heap allocation, slices, strings, line-oriented utilities.

| # | Name | Status | Features Demonstrated |
|---|------|--------|----------------------|
| 11 | grep | ✅ | Heap allocation, slices, line iteration |
| 12 | tac | ✅ | `Vec<T>` (growable array), `Buffer` |
| 13 | sort | ✅ | Quicksort, byte-wise comparison |
| 14 | uniq | ✅ | Line comparison, `-c`/`-d`/`-u`/`-i` options |
| 15 | cut | ✅ | Field/char extraction, delimiters, ranges |
| 16 | tr | ✅ | Byte arrays, character sets, `-d`/`-s`/`-c` |
| 17 | expand | ✅ | Tab expansion, `-t`/`-i` options |
| 18 | nl | ✅ | Line numbering, integer formatting |
| 19 | base64 | ✅ | Bit manipulation, encoding/decoding |
| 20 | xxd | ✅ | Hex formatting, `-r`/`-c`/`-g`/`-p`/`-u` |

---

## Tier 3: Filesystem (21-30)

Directory operations, file metadata, permissions, recursive traversal.

| # | Name | Status | Features Demonstrated |
|---|------|--------|----------------------|
| 21 | ls | ✅ | `getdents64`, `stat`, entry sorting, mode formatting |
| 22 | mkdir | ✅ | Path parsing, parent creation (`-p`) |
| 23 | rm | ✅ | Recursive unlink, directory traversal |
| 24 | cp | ✅ | File copy, recursive dirs, preserve mode |
| 25 | mv | ✅ | `rename` syscall, cross-path handling |
| 26 | touch | ✅ | `utimensat`, timestamps |
| 27 | stat | ✅ | Stat struct accessors, mode/type formatting |
| 28 | chmod | ✅ | Octal/symbolic mode parsing, recursive |
| 29 | du | ✅ | Recursive size calculation, human-readable (`-h`) |
| 30 | find | ✅ | Tree walk, glob matching, type/depth filters |

---

## Tier 4: Processes & Environment (31-40)

Process management, signals, environment access.

| # | Name | Status | Features Demonstrated |
|---|------|--------|----------------------|
| 31 | env | ✅ | `envp`, print environment |
| 32 | which | ✅ | PATH search, access checks |
| 33 | printenv | ✅ | Single env variable lookup |
| 34 | kill | ✅ | Signals, process targeting |
| 35 | nohup | ✅ | Signal handling, `setsid` |
| 36 | timeout | ✅ | Child timing, signal delivery |
| 37 | xargs | ✅ | Arg building, process spawning |
| 38 | tee | ✅ | Multi-output, stdin copying |
| 39 | time | ✅ | Child timing, `gettimeofday` |
| 40 | watch | ✅ | Periodic exec, screen control |

---

## Tier 5: Parsers (41-50)

Parser construction, recursive descent, interpreters.

| # | Name | Status | Features Demonstrated |
|---|------|--------|----------------------|
| 41 | calc | ✅ | Expression parser, RPN mode, infix with precedence |
| 42 | json | ✅ | Recursive descent, tree construction, arrays/objects |
| 43 | toml | ✅ | Config parsing, tables, arrays, dotted keys |
| 44 | csv | ✅ | Streaming parser, quoting, field extraction |
| 45 | regex | ✅ | Backtracking matcher, `.`, `*`, `+`, `?`, char classes |
| 46 | markdown | ✅ | Document parser, headings, lists, code, HTML output |
| 47 | lisp | ✅ | S-expressions, lambda, define, quote, car/cdr/cons |
| 48 | ritzfmt | ✅ | Ritz lexer, indent normalization, `-c`/`-w` |
| 49 | ritzgen | ✅ | Parser generator from grammar |
| 50 | http | ✅ | HTTP/1.0 server |

---

## Tier 6: Advanced Features (51-76)

Async I/O, io_uring, closures, generics, error handling.

| # | Name | Status | Features Demonstrated |
|---|------|--------|----------------------|
| 51 | iovec | ✅ | Vectored I/O (`writev`) |
| 51 | loadtest | ✅ | HTTP load testing tool |
| 52 | uring | ✅ | io_uring syscall bindings |
| 53 | async | ✅ | `async fn` / `await` syntax |
| 54 | async_fs | ✅ | Async file I/O |
| 55 | async_state_machine | ✅ | State machine transformation |
| 56 | async_runtime | ✅ | io_uring-backed async runtime |
| 57 | fn_ptr | ✅ | Function pointer types, indirect calls |
| 58 | closures | ✅ | Closures with captures, higher-order functions |
| 59 | async_net | ✅ | TCP socket operations with async runtime |
| 60 | echo_server | ✅ | TCP echo server with io_uring |
| 61 | true_async | 🔄 | True async suspension/resume |
| 62 | async_compiler | 🔄 | Compiler transform tests |
| 63 | executor | ✅ | Executor implementation |
| 64 | async_io | ✅ | Async I/O primitives |
| 65 | async_main | 🔄 | Async main entry point |
| 66 | for_loops | ✅ | `for i in 0..n` syntax |
| 67 | autoderef | ✅ | `ptr.field` auto-dereference |
| 68 | result_error_handling | ✅ | `Result<T, E>`, `?` operator |
| 69 | result_string | ✅ | `Result` with `String` type |
| 70 | interp_string | ✅ | String interpolation `"{x}"` |
| 71 | type_inference | ✅ | `let x = expr` without type annotation |
| 72 | raii | ✅ | Drop trait, automatic cleanup |
| 73 | heap | ✅ | Heap allocation patterns |
| 74 | async_tiers | 🔄 | Tiered async examples |
| 74 | autodrop | ✅ | Automatic Drop at scope exit |
| 75 | async_reference | ✅ | Reference async patterns (7 tests) |
| 75 | tier2_uring | 🔄 | io_uring tier 2 |
| 76 | tier3_http | 🔄 | HTTP tier 3 |

**Note**: Numbers 51, 74, and 75 have duplicates due to historical naming conflicts.

---

## Example Structure

Each example is a package:

```
examples/
  05_cat/
    ritz.toml          # Package config
    src/
      main.ritz        # Main source
    test/              # Optional
      test_cat.ritz    # @test functions
    test.sh            # Optional shell tests
    fixtures/          # Optional test data
```

### ritz.toml format

```toml
[package]
name = "cat"
version = "0.1.0"

[build]
target = "x86_64-linux"

[[bin]]
name = "cat"
```

---

## Testing Examples

```bash
# Build and test a specific example
python3 build.py test 21_ls

# Build all examples
python3 build.py build --all

# Run ritz0's language test suite
python3 build.py ritz-tests
```

---

## Tier Reorganization (Completed February 2026)

As of February 12, 2026, examples are now organized into tier directories:

### Implementation Details

- **Directories Created**: `tier1_basics/`, `tier2_stdlib/`, `tier3_coreutils/`, `tier4_applications/`, `tier5_async/`
- **Examples Moved**: All 79 example packages distributed across tiers
- **build.py Updates**: Already supports recursive `ritz.toml` discovery via `**/ritz.toml` glob pattern
- **Path Examples**: Packages are now at paths like `examples/tier1_basics/01_hello/ritz.toml`

### Build System Compatibility

The `build.py` build system automatically discovered the new tier structure because it uses recursive glob patterns:

```python
for toml_path in sorted(search_dir.glob("**/ritz.toml")):
```

This means:
- `python3 build.py list` shows all 79 packages correctly
- `python3 build.py test examples/tier1_basics/01_hello` still works
- Tier-specific batch testing can be done: `python3 build.py test examples/tier1_basics/*`

---

## Adding New Examples

1. Create directory: `examples/NN_name/`
2. Create `ritz.toml` with package info
3. Create `src/main.ritz` with the program
4. Optionally add `test/test_name.ritz` with `@test` functions
5. Run: `python3 build.py test NN_name`

---

*Last updated: 2026-02-11*
