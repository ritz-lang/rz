# ritz-lsp

Language Server Protocol (LSP) implementation for the Ritz programming language, written in Ritz.

**Part of the [Ritz Ecosystem](../ritz/docs/ECOSYSTEM.md)**

## Overview

ritz-lsp provides IDE integration for the Ritz programming language through the Language Server Protocol. It runs as a background server that communicates with editors via JSON-RPC 2.0 over stdio, providing real-time diagnostics, navigation, and code intelligence as you write Ritz code.

The server is written entirely in Ritz itself, making it a useful showcase of ritzlib's JSON parsing and string handling capabilities. It integrates with Vim/Neovim via coc.nvim or native LSP, and can work with any LSP-compatible editor. It also installs Ritz syntax highlighting for Vim.

## Features

- JSON-RPC 2.0 transport over stdio
- LSP initialize/shutdown handshake
- Document synchronization (open, change, close)
- Vim and Neovim syntax highlighting for `.ritz` files
- coc.nvim automatic configuration
- Diagnostics (syntax errors, type errors) - in progress
- Hover information (types, documentation) - planned
- Go to definition - planned
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
| Diagnostics | In progress |
| Hover | Advertised in capabilities, not implemented |
| Go to definition | Advertised in capabilities, not implemented |
| Completions | Planned, not advertised |

The hover/definition rows need care: the server's `initialize` reply claims
`"hoverProvider":true,"definitionProvider":true`, so editors will offer both and
then get nothing useful back. Either implement them or stop advertising them —
advertising an unimplemented capability is worse than omitting it.

## License

MIT License - see LICENSE file
