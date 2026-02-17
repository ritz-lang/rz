# Tooling Subsystem

The tooling subsystem provides the compiler, test framework, language server, and shell — everything you need to develop and run Ritz programs.

---

## Projects in This Subsystem

| Project | Role | Status |
|---------|------|--------|
| [Ritz](../projects/ritz.md) | Compiler and standard library | Active (324 tests) |
| [Ritzunit](../projects/ritzunit.md) | Test framework | Production |
| [Ritz-LSP](../projects/ritz-lsp.md) | Language Server Protocol | MVP |
| [rzsh](../projects/rzsh.md) | Ritz shell | Active |

---

## Ritz: The Compiler

The Ritz compiler has two implementations:

| Compiler | Language | Status |
|----------|----------|--------|
| `ritz0` | Python | Production (bootstrap compiler) |
| `ritz1` | Ritz (self-hosted) | Compiles 47/48 examples |

Both compile Ritz source to LLVM IR. LLVM/clang then produces the native binary.

### Compilation Pipeline

```
Ritz source (.ritz)
        │
        ▼
  Lexer → Parser → Type Checker → Code Generator
        │
        ▼
   LLVM IR (.ll)
        │
        ▼
   clang -c  →  Object file (.o)
        │
        ▼
   clang (link)  →  ELF binary
```

### Standard Library (ritzlib)

Ritzlib provides 35 modules covering everything from system calls to async I/O:

| Module | Purpose |
|--------|---------|
| `sys.ritz` | System calls (89 constants), direct Linux interface |
| `io.ritz` | I/O helpers (print, read lines) |
| `memory.ritz` | Memory allocation (mmap/munmap) |
| `gvec.ritz` | Generic Vec<T> — dynamic array |
| `hashmap.ritz` | Hash table |
| `fs.ritz` | Filesystem operations |
| `str.ritz` | String utilities |
| `async.ritz` | Async runtime |
| `async_tasks.ritz` | Async task management |
| `uring.ritz` | io_uring bindings |
| `args.ritz` | Argument parsing |
| `json.ritz` | JSON parsing and serialization |
| `process.ritz` | Process spawning |
| `async_fs.ritz` | Async filesystem I/O |
| `async_net.ritz` | Async network I/O |

### Key Statistics

| Metric | Value |
|--------|-------|
| Language tests | 324 passing |
| Unit tests | 201 passing |
| Examples compiling | 48/48 |
| Self-hosted examples | 47/48 |
| Standard library modules | 35 |

---

## Ritzunit: The Test Framework

Ritzunit is a JUnit/pytest-style unit testing framework for Ritz.

### Key Features

**ELF self-discovery:** Ritzunit finds all test functions by scanning the ELF symbol table — no test registration required. Annotate a function with `[[test]]` and it is automatically discovered.

**Fork-based isolation:** Each test runs in a forked process. A crashing test does not abort the test run. Timeouts are enforced.

**Rich assertions:** 18+ assertion functions covering equality, ordering, string matching, error handling, and more.

**CLI interface:** Filter by name, list available tests, verbose output, custom timeouts.

### Writing Tests

```ritz
[[test]]
fn test_addition() -> i32
    assert 2 + 2 == 4
    0   # 0 = pass, non-zero = fail

[[test]]
fn test_string_length() -> i32
    let s = "hello"
    assert s.len() == 5
    0

[[test]]
fn test_error_handling() -> i32
    let result: Result<i32, String> = Err("oops")
    assert result.is_err()
    0
```

### Running Tests

```bash
ritz test .                          # Run all tests
ritz test . --filter test_addition   # Run specific test
ritz test . --list                   # List all tests
ritz test . --verbose                # Show test output
ritz test . --timeout 10             # Custom timeout (seconds)
```

---

## Ritz-LSP: The Language Server

Ritz-LSP implements the Language Server Protocol for Ritz, providing IDE features in editors that support LSP.

### Current Features

- JSON-RPC 2.0 transport over stdio
- Initialize/shutdown handshake
- Document synchronization (open/change/close)
- Vim syntax highlighting

### Planned Features

- Diagnostics (syntax and type errors)
- Go to definition
- Hover information (types, documentation)
- Code completions (keywords, variables, fields)

### Editor Setup

**Neovim (native LSP):**

```lua
vim.api.nvim_create_autocmd("FileType", {
  pattern = "ritz",
  callback = function()
    vim.lsp.start({
      name = "ritz-lsp",
      cmd = { "ritz-lsp" },
      root_dir = vim.fs.dirname(
        vim.fs.find({ "ritz.toml", ".git" }, { upward = true })[1]
      ),
    })
  end,
})
```

**coc.nvim:**

```json
{
  "languageserver": {
    "ritz": {
      "command": "ritz-lsp",
      "filetypes": ["ritz"],
      "rootPatterns": ["ritz.toml", ".git"]
    }
  }
}
```

---

## rzsh: The Ritz Shell

rzsh is the official shell for the Ritz ecosystem, designed to run both on Linux (as a regular process) and natively on Harland.

The shell provides:
- A unified cross-platform interface
- Ritz-native command execution
- Integration with Goliath (Harland's filesystem)

---

## The ritz.toml Manifest

Every Ritz project has a `ritz.toml` manifest:

```toml
[package]
name = "myapp"
version = "0.1.0"

sources = ["src"]

[[bin]]
name = "myapp"
entry = "main::main"

[dependencies]
squeeze = { path = "../squeeze" }
cryptosec = { path = "../cryptosec" }
valet = { path = "../valet" }
```

---

## See Also

- [Ritz project page](../projects/ritz.md)
- [Ritzunit project page](../projects/ritzunit.md)
- [Ritz-LSP project page](../projects/ritz-lsp.md)
- [rzsh project page](../projects/rzsh.md)
- [Language Overview](../language/overview.md)
- [Getting Started](../getting-started.md)
