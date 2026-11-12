# ritz-lsp

Language Server Protocol (LSP) server for Ritz, written in Ritz. **What works
today:** JSON-RPC 2.0 over stdio, the initialize/shutdown handshake, and
full-text document sync, plus Vim syntax highlighting via `install.sh`. It
advertises only `textDocumentSync`. **No diagnostics, hover, definition or
completion yet** (AGAST #2789); hover and definition requests get
MethodNotFound.

**Part of the [Ritz Ecosystem](../ritz/docs/ECOSYSTEM.md)**

## Overview

ritz-lsp provides IDE integration for the Ritz programming language through the Language Server Protocol. It runs as a background server that communicates with editors via JSON-RPC 2.0 over stdio, and is meant to provide diagnostics, navigation and code intelligence; today it
only keeps the editor's open documents in sync (see [Status](#status)).

The server is written entirely in Ritz itself, making it a useful showcase of ritzlib's JSON parsing and string handling capabilities. It integrates with Vim/Neovim via coc.nvim or native LSP, and can work with any LSP-compatible editor. It also installs Ritz syntax highlighting for Vim.

## Features

- JSON-RPC 2.0 transport over stdio
- LSP initialize/shutdown handshake
- Document synchronization (open, change, close)
- Vim and Neovim syntax highlighting for `.ritz` files
- coc.nvim automatic configuration
- Diagnostics (syntax errors, type errors) - planned (AGAST #2789)
- Hover information (types, documentation) - planned, not advertised (#2789)
- Go to definition - planned, not advertised (#2789)
- Completions (keywords, variables, fields) - planned

## Installation

ritz-lsp lives in the `rz` monorepo; there is no separate `ritz-lsp` repository
and there are no submodules.

```bash
git clone git@github.com:ritz-lang/rz.git
cd rz

# Build the server (run from the monorepo root; `rz` sets RITZ_PATH itself)
./rz build ritz-lsp
# Produces projects/ritz-lsp/build/debug/ritz-lsp

# Install Vim syntax highlighting into ~/.vim/
./projects/ritz-lsp/install.sh --vim
```

### `install.sh` is half-broken — use `./rz build` instead

`install.sh --vim` works (exit 0). The build paths do not:

| Command | Result |
|---|---|
| `./install.sh --vim` | ✅ exit 0, installs syntax files to `~/.vim/` |
| `./install.sh --build` | ❌ exit 1 — `cd: ritz/runtime: No such file or directory` |
| `./install.sh` (no args) | ❌ exit 1 — same failure, after doing the `--vim` step |

Cause: `install.sh:169-178` runs `git submodule update --init --recursive` and
then `cd ritz/runtime`, expecting a `ritz` submodule inside this directory. That
layout predates the February 2026 consolidation into the monorepo; the repo has
no `.gitmodules`, so the submodule command is a silent no-op and the `cd` fails.
`./rz build ritz-lsp` is the supported build.

## Usage

```bash
# The LSP server communicates over stdio - editors launch it automatically.
# Manual smoke test (exit 0, replies with its capabilities):
printf 'Content-Length: 58\r\n\r\n{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
    | ./projects/ritz-lsp/build/debug/ritz-lsp
```

### Vim with coc.nvim

Add to `~/.vim/coc-settings.json`:
```json
{
  "languageserver": {
    "ritz": {
      "command": "/path/to/ritz-lsp",
      "filetypes": ["ritz"],
      "rootPatterns": ["ritz.toml", ".git"]
    }
  }
}
```

### Neovim native LSP

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

## Dependencies

ritz-lsp depends only on `ritzlib` (which ships with the Ritz compiler). No external dependencies.

## Status

**MVP complete.** Measured 2026-09-12: `./rz build ritz-lsp` exits 0, and the
binary answers an `initialize` request over stdio at exit 0.

| Feature | Status |
|---------|--------|
| JSON-RPC transport | Working |
| Initialize/shutdown | Working |
| Document sync | Working |
| Vim syntax highlighting | Working (`install.sh --vim`) |
| `install.sh --build` | **Broken** — expects a pre-consolidation `ritz` submodule; use `./rz build ritz-lsp` |
| Diagnostics | Planned (#2789): no `publishDiagnostics` is sent |
| Hover | Not implemented, not advertised: MethodNotFound (#2789) |
| Go to definition | Not implemented, not advertised: MethodNotFound (#2789) |
| Completions | Planned, not advertised |

Hover and definition used to be advertised (`"hoverProvider":true,
"definitionProvider":true`) and answered `null` for every position, so editors
offered both and got nothing back. Since AGAST #2460 `initialize` advertises
only `textDocumentSync`. `test.sh` pins the capabilities and the MethodNotFound
replies.

## License

MIT License - see LICENSE file
