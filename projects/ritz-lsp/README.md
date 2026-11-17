# ritz-lsp

Language Server Protocol (LSP) server for Ritz, written in Ritz. **What works
today:** JSON-RPC 2.0 over stdio, the initialize/shutdown handshake, and
full-text document sync, diagnostics from a ritz1 compile of the buffer,
hover and go-to-definition for function names in the open document
(AGAST #2789), plus Vim syntax highlighting via `install.sh`. **No completion
yet**: anything it does not advertise gets MethodNotFound.

**Part of the [Ritz Ecosystem](../ritz/docs/ECOSYSTEM.md)**

## Overview

ritz-lsp provides IDE integration for the Ritz programming language through the Language Server Protocol. It runs as a background server that communicates with editors via JSON-RPC 2.0 over stdio, and is meant to provide diagnostics, navigation and code intelligence; today it
reports compiler errors and resolves function names within one document (see
[Status](#status)).

The server is written entirely in Ritz itself, making it a useful showcase of ritzlib's JSON parsing and string handling capabilities. It integrates with Vim/Neovim via coc.nvim or native LSP, and can work with any LSP-compatible editor. It also installs Ritz syntax highlighting for Vim.

## Features

- JSON-RPC 2.0 transport over stdio
- LSP initialize/shutdown handshake
- Document synchronization (open, change, close)
- Vim and Neovim syntax highlighting for `.ritz` files
- coc.nvim automatic configuration
- Diagnostics: every error ritz1 reports for the buffer (#2789)
- Hover: the signature of a function declared in the open document (#2789)
- Go to definition: a function's declaration in the open document (#2789)
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

`ritz-lsp --help` (or `-h`) prints usage and exits 0 without starting the
server. `--stdio`, which editors' LSP clients pass, is accepted and is the
default. Any other argument is a usage error: exit 2, usage on stderr.

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

ritz-lsp depends only on `ritzlib` (which ships with the Ritz compiler) to
build. Diagnostics need the `ritz1` compiler at run time (below); hover and
definition do not.

## Diagnostics

On `didOpen` and every `didChange` the server writes the buffer to a private
scratch directory (`$XDG_RUNTIME_DIR/ritz-lsp`, else
`${TMPDIR:-/tmp}/ritz-lsp-<uid>`) under the document's file name, runs
`ritz1 <copy> -o <scratch .ll> -I <dirs>`, removes the copy, and sends
`textDocument/publishDiagnostics` (an empty list once the buffer compiles):

- `<file>:<line>:<col>: error: <msg>` in the buffer: an error at that
  position, spanning the identifier there.
- An error located in another file (an import), or an unlocated `error`
  line: an error on the first line carrying ritz1's whole line. `note:`
  lines are dropped.
- ritz1 failing with no error line: one error naming its exit code.

Which ritz1: `$RITZ1`; else `projects/ritz/ritz1/build/ritz1` in the monorepo
this binary was built in (`make -C projects/ritz ritz1`); else `ritz1` on
`$PATH`. With none, one warning on line 1 says so.

Imports: `-I` lists the document's directory and up to seven ancestors (where
ritz1 would look beside the real file), then the monorepo's `projects/ritz`
for `ritzlib`; ritz1 appends `$RITZ_PATH`. A cross-project import that needs
a `RITZ_PATH` entry needs it in the editor's environment.

The compile runs on the request loop, so it has a deadline (#3883): a ritz1
still running after 5 seconds (`COMPILE_DEADLINE_SECS`) is killed and the
document gets one warning that the check timed out. Every open/change still
compiles in turn; only the latest of a burst would be enough (#3902). Columns are bytes, which equal LSP's UTF-16 columns on ASCII lines.

## Hover and go-to-definition

Both read the open buffer, not a compile, so they answer while it does not
parse. A function declaration is a line starting `fn <name>` after any
indentation and `pub` / `extern` / `async`. On a name in code (not in a
comment or string literal) that some line declares, hover answers the
declaration's line as a `ritz` code block and definition answers its
location; anything else answers `null`. Only the open document is searched:
a function imported from another file answers `null`.

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
| Diagnostics | Working: ritz1 errors on open/change (#2789) |
| Hover | Working: function names in the open document (#2789) |
| Go to definition | Working: function names in the open document (#2789) |
| Completions | Planned, not advertised: MethodNotFound |

Hover and definition used to be advertised and answered `null` for every
position (#2460); they were unadvertised until #2789 gave them real answers.
`test.sh` pins the capabilities, the hover/definition answers, how ritz1's
output becomes diagnostics (with a stub ritz1) and, when ritz1 is built, the
end-to-end answer for a call to an undefined function.

## License

MIT License - see LICENSE file
