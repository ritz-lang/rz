# ritz-lsp

The Language Server Protocol (LSP) implementation for the [Ritz programming language](https://github.com/ritz-lang/ritz), **written in Ritz**.

## Status

**MVP Complete** - Basic LSP functionality is working:
- ✅ JSON-RPC transport over stdio
- ✅ Initialize/shutdown handshake
- ✅ Document synchronization (open/change/close)
- ✅ Vim syntax highlighting
- 🚧 Diagnostics (in progress)
- 🚧 Hover/Go-to-definition (stubs)

## Quick Start

```bash
# Clone with submodules
git clone --recursive https://github.com/ritz-lang/ritz-lsp.git
cd ritz-lsp

# Install everything (vim syntax, build, configure coc.nvim)
./install.sh

# Or step by step:
./install.sh --vim      # Install vim syntax files only
./install.sh --build    # Build ritz-lsp only
./install.sh --coc      # Configure coc.nvim only
```

Then open a `.ritz` file in vim!

## Features

### Current

- **Vim Syntax Highlighting** - Full syntax support for keywords, types, strings, comments
- **LSP Server** - JSON-RPC 2.0 over stdio with document synchronization
- **coc.nvim Integration** - Automatic setup for vim/neovim

### Planned

- **Diagnostics** - Syntax errors, type errors, import errors
- **Go to Definition** - Navigate to functions, variables, types
- **Hover Information** - View types and documentation
- **Completions** - Keywords, variables, fields

See [TODO.md](TODO.md) for the complete roadmap.

## Installation

### Prerequisites

- **clang** - For compiling runtime objects
- **Python 3.10+** - For ritz0 bootstrap compiler
- **vim** with **coc.nvim** (optional, for LSP integration)

### From Source

```bash
# Clone with submodules
git clone --recursive https://github.com/ritz-lang/ritz-lsp.git
cd ritz-lsp

# Run the installer
./install.sh
```

The installer will:
1. Install vim syntax files to `~/.vim/`
2. Build `ritz-lsp` using the ritz compiler
3. Install binary to `~/.local/bin/`
4. Configure coc.nvim (if present)

### Manual Installation

```bash
# Initialize submodules
git submodule update --init --recursive

# Create ritzlib symlink
ln -s ritz/ritzlib ritzlib

# Build runtime (if needed)
cd ritz/runtime
clang -c -o ritz_start_noargs.x86_64.o ritz_start_noargs.x86_64.ll
clang -c -o ritz_start.x86_64.o ritz_start.x86_64.ll
clang -c -o ritz_start_envp.x86_64.o ritz_start_envp.x86_64.ll
cd ../..

# Build ritz-lsp
./ritz/ritz build .

# Binary is at: build/debug/ritz-lsp
```

## Editor Setup

### Vim with coc.nvim

The installer configures coc.nvim automatically. Manual setup:

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

### Vim (syntax only)

```bash
./install.sh --vim
```

This installs:
- `~/.vim/syntax/ritz.vim` - Syntax highlighting
- `~/.vim/ftdetect/ritz.vim` - Filetype detection

### Neovim (native LSP)

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

### Testing the LSP

```bash
# Manual test
printf 'Content-Length: 58\r\n\r\n{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | ./build/debug/ritz-lsp

# Check vim integration
vim test.ritz
:CocInfo
```

## Project Structure

```
ritz-lsp/
├── src/
│   ├── main.ritz        # Entry point
│   ├── server.ritz      # LSP server loop & dispatch
│   ├── protocol.ritz    # JSON-RPC message handling
│   ├── transport.ritz   # stdio transport layer
│   └── documents.ritz   # Document store
├── ritz/                # Ritz compiler (submodule)
├── ritzlib -> ritz/ritzlib  # Symlink to standard library
├── install.sh           # Installation script
└── ritz.toml            # Package manifest
```

## Architecture

The LSP server is written entirely in Ritz, using:

- **ritzlib/json.ritz** - JSON parsing and serialization
- **ritzlib/gvec.ritz** - Dynamic arrays (Vec<T>)
- **ritzlib/str.ritz** - String operations
- **ritzlib/sys.ritz** - System calls for stdio

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and test with `./ritz/ritz build .`
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Related Projects

- [ritz](https://github.com/ritz-lang/ritz) - The Ritz programming language
