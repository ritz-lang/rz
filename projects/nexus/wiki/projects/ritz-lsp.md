# Ritz-LSP

Language Server Protocol implementation for Ritz. MVP complete.

---

## Overview

Ritz-LSP is the official IDE integration for Ritz. It implements the Language Server Protocol (LSP) — a standardized interface between editors and language tooling — so that any LSP-compatible editor can provide Ritz-aware features.

Ritz-LSP is itself written in Ritz, demonstrating the language's capability for building developer tools.

---

## Where It Fits

```
Your Editor (Vim, Neovim, VS Code, etc.)
    │ LSP (JSON-RPC over stdio)
    ▼
RITZ-LSP (language server)
    │ Parses .ritz files
    └── Ritz compiler internals
```

---

## Current Features

| Feature | Status |
|---------|--------|
| JSON-RPC 2.0 transport over stdio | Complete |
| Initialize/shutdown handshake | Complete |
| Document synchronization (open/change/close) | Complete |
| Vim syntax highlighting | Complete |
| coc.nvim integration | Complete |
| Diagnostics (syntax errors) | In progress |
| Hover (show types) | Stub |
| Go to definition | Stub |
| Code completion | Planned |

---

## Installation

### Quick Install

```bash
git clone --recursive https://github.com/ritz-lang/ritz-lsp.git
cd ritz-lsp
./install.sh
```

The installer:
1. Installs Vim syntax files (`~/.vim/syntax/ritz.vim`)
2. Builds `ritz-lsp` using the Ritz compiler
3. Installs binary to `~/.local/bin/`
4. Configures coc.nvim (if present)

### Manual

```bash
git submodule update --init --recursive
./ritz/ritz build .
# Binary at: build/debug/ritz-lsp
```

---

## Editor Setup

### Neovim (Native LSP)

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

### coc.nvim (Vim/Neovim)

Add to `~/.vim/coc-settings.json`:

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

### Vim (Syntax Only)

```bash
./install.sh --vim
```

Installs syntax highlighting without the LSP server.

---

## Architecture

Ritz-LSP uses only ritzlib modules — no external dependencies:

| Module | Purpose |
|--------|---------|
| `ritzlib/json.ritz` | JSON parsing and serialization (for JSON-RPC) |
| `ritzlib/gvec.ritz` | Dynamic arrays |
| `ritzlib/str.ritz` | String operations |
| `ritzlib/sys.ritz` | stdin/stdout syscalls |

```
ritz-lsp/
├── src/
│   ├── main.ritz        # Entry point, server loop
│   ├── server.ritz      # LSP method dispatch
│   ├── protocol.ritz    # JSON-RPC message types
│   ├── transport.ritz   # stdio read/write with Content-Length framing
│   └── documents.ritz   # In-memory document store
└── ritz.toml
```

---

## LSP Protocol

Ritz-LSP communicates via JSON-RPC 2.0 with Content-Length framing:

```
Content-Length: 87\r\n
\r\n
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"capabilities":{}}}
```

### Supported Methods

| Method | Direction | Status |
|--------|-----------|--------|
| `initialize` | Client → Server | Complete |
| `initialized` | Client → Server | Complete |
| `shutdown` | Client → Server | Complete |
| `exit` | Client → Server | Complete |
| `textDocument/didOpen` | Client → Server | Complete |
| `textDocument/didChange` | Client → Server | Complete |
| `textDocument/didClose` | Client → Server | Complete |
| `textDocument/publishDiagnostics` | Server → Client | In progress |
| `textDocument/hover` | Client → Server | Stub |
| `textDocument/definition` | Client → Server | Stub |
| `textDocument/completion` | Client → Server | Planned |

---

## Vim Syntax Highlighting

The Vim syntax file provides highlighting for:

- Keywords (`fn`, `let`, `var`, `if`, `else`, `while`, `for`, `match`, `return`, `import`, `pub`, `struct`, `enum`, `impl`, `trait`)
- Types (`i8`, `i16`, `i32`, `i64`, `u8`, ..., `bool`, `StrView`, `String`, `Vec`, `Option`, `Result`)
- Literals (numbers, strings, booleans)
- Comments (`#` line comments)
- Attributes (`[[test]]`, `[[route(...)]]`)
- Operators and punctuation

---

## Testing

```bash
# Manual protocol test
printf 'Content-Length: 58\r\n\r\n{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  | ./build/debug/ritz-lsp

# In Vim
vim test.ritz
:CocInfo   # Check LSP status
```

---

## Current Status

MVP complete. JSON-RPC transport and document synchronization working. Diagnostics in progress.

---

## Related Projects

- [Ritz](ritz.md) — The compiler Ritz-LSP analyzes
- [Tooling Subsystem](../subsystems/tooling.md)
