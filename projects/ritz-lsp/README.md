# ritz-lsp

Language Server Protocol (LSP) implementation for the Ritz programming language, written in Ritz.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

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

```bash
# Quick install (installs vim syntax, builds binary, configures coc.nvim)
git clone --recursive https://github.com/ritz-lang/ritz-lsp.git
cd ritz-lsp
./install.sh

# Install only vim syntax highlighting
./install.sh --vim

# Build only
./install.sh --build

# Configure coc.nvim only
./install.sh --coc
```

## Usage

```bash
# The LSP server communicates over stdio - editors launch it automatically
# Manual test:
printf 'Content-Length: 58\r\n\r\n{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
    | ./build/debug/ritz-lsp
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

**MVP complete** - JSON-RPC transport, initialize/shutdown, document synchronization, and Vim syntax highlighting all work. Diagnostics integration (connecting to the ritz compiler for error reporting) is in active development. Hover, go-to-definition, and completions are planned.

| Feature | Status |
|---------|--------|
| JSON-RPC transport | Working |
| Initialize/shutdown | Working |
| Document sync | Working |
| Vim syntax highlighting | Working |
| Diagnostics | In progress |
| Hover | Planned |
| Go to definition | Planned |
| Completions | Planned |

## License

MIT License - see LICENSE file
