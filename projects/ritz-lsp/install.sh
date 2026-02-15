#!/bin/bash
# install.sh - Install ritz-lsp and vim configuration
#
# Usage:
#   ./install.sh           # Install everything
#   ./install.sh --vim     # Only install vim syntax files
#   ./install.sh --build   # Only build ritz-lsp
#   ./install.sh --coc     # Only configure coc.nvim

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# =============================================================================
# Vim Syntax Installation
# =============================================================================
install_vim_syntax() {
    info "Installing Ritz syntax highlighting for Vim..."

    mkdir -p ~/.vim/syntax ~/.vim/ftdetect

    # Create syntax file
    cat > ~/.vim/syntax/ritz.vim << 'SYNTAX_EOF'
" Vim syntax file
" Language: Ritz
" Maintainer: Ritz Language Team

if exists("b:current_syntax")
  finish
endif

" Keywords
syn keyword ritzKeyword fn let var if else while for in match return
syn keyword ritzKeyword struct enum import extern const type trait impl
syn keyword ritzKeyword break continue as mut async await loop pub heap
syn keyword ritzKeyword unsafe

" Boolean literals
syn keyword ritzBoolean true false

" Null
syn keyword ritzConstant null

" Assertions
syn keyword ritzAssert assert static_assert

" Built-in types
syn keyword ritzType i8 i16 i32 i64 u8 u16 u32 u64 f32 f64 bool
syn keyword ritzType Self

" Generic types (common ones)
syn keyword ritzType Vec Option Result Some None Ok Err String Span

" Attributes
syn match ritzAttribute "@\w\+"

" Numbers
syn match ritzNumber "\<\d\+\>"
syn match ritzNumber "\<\d\+\.\d*\>"
syn match ritzNumber "\<0x[0-9a-fA-F_]\+\>"
syn match ritzNumber "\<0b[01_]\+\>"
syn match ritzFloat "\<\d\+\.\d\+\([eE][+-]\?\d\+\)\?\>"

" Operators
syn match ritzOperator "[-+*/%&|^~!<>=]"
syn match ritzOperator "=="
syn match ritzOperator "!="
syn match ritzOperator "<="
syn match ritzOperator ">="
syn match ritzOperator "&&"
syn match ritzOperator "||"
syn match ritzOperator "->"
syn match ritzOperator "=>"
syn match ritzOperator "\.\."
syn match ritzOperator "\.\.="
syn match ritzOperator "::"
syn match ritzOperator "+="
syn match ritzOperator "-="
syn match ritzOperator "\*="
syn match ritzOperator "/="
syn match ritzOperator "<<"
syn match ritzOperator ">>"

" Strings - regular (with interpolation support)
syn region ritzString start='"' skip='\\"' end='"' contains=ritzEscape,ritzInterpolation
syn region ritzInterpolation start='{' end='}' contained contains=ritzInterpolationContent
syn match ritzInterpolationContent "[^}]*" contained

" C-strings (c"...")
syn region ritzCString start='c"' skip='\\"' end='"' contains=ritzEscape

" Span strings (s"...")
syn region ritzSpanString start='s"' skip='\\"' end='"' contains=ritzEscape

" Character literals
syn match ritzCharacter "'\\.'"
syn match ritzCharacter "'[^'\\]'"

" Escape sequences
syn match ritzEscape "\\[ntr0\\\"']" contained

" Comments
syn match ritzComment "#.*$"

" Function definitions
syn match ritzFunction "\<fn\s\+\zs\w\+"

" Type annotations (after colon)
syn match ritzTypeAnnotation ":\s*\zs[A-Z]\w*"
syn match ritzTypeAnnotation ":\s*\zs\*[A-Z]\w*"
syn match ritzTypeAnnotation ":\s*\zs\*\*[A-Z]\w*"
syn match ritzTypeAnnotation ":\s*\zs\[[^\]]*\][A-Z]\?\w*"

" Generic type parameters
syn match ritzGeneric "<[A-Z][^>]*>"

" Define highlighting
hi def link ritzKeyword     Keyword
hi def link ritzBoolean     Boolean
hi def link ritzConstant    Constant
hi def link ritzAssert      PreProc
hi def link ritzType        Type
hi def link ritzAttribute   PreProc
hi def link ritzNumber      Number
hi def link ritzFloat       Float
hi def link ritzOperator    Operator
hi def link ritzString      String
hi def link ritzCString     String
hi def link ritzSpanString  String
hi def link ritzCharacter   Character
hi def link ritzEscape      SpecialChar
hi def link ritzComment     Comment
hi def link ritzFunction    Function
hi def link ritzTypeAnnotation Type
hi def link ritzGeneric     Type
hi def link ritzInterpolation Special

let b:current_syntax = "ritz"
SYNTAX_EOF

    # Create ftdetect file
    cat > ~/.vim/ftdetect/ritz.vim << 'FTDETECT_EOF'
" Detect Ritz files
autocmd BufNewFile,BufRead *.ritz set filetype=ritz
FTDETECT_EOF

    info "Vim syntax files installed to ~/.vim/"
}

# =============================================================================
# Build ritz-lsp
# =============================================================================
build_ritz_lsp() {
    info "Building ritz-lsp..."

    cd "$SCRIPT_DIR"

    # Initialize submodule if needed
    if [ ! -f "ritz/ritz" ]; then
        info "Initializing ritz submodule..."
        git submodule update --init --recursive
    fi

    # Build runtime objects if needed
    if [ ! -f "ritz/runtime/ritz_start_noargs.$(uname -m).o" ]; then
        info "Building runtime objects..."
        cd ritz/runtime
        if command -v clang &> /dev/null; then
            clang -c -o ritz_start.$(uname -m).o ritz_start.$(uname -m).ll 2>/dev/null || true
            clang -c -o ritz_start_noargs.$(uname -m).o ritz_start_noargs.$(uname -m).ll 2>/dev/null || true
            clang -c -o ritz_start_envp.$(uname -m).o ritz_start_envp.$(uname -m).ll 2>/dev/null || true
        else
            error "clang not found. Please install clang to build ritz-lsp."
        fi
        cd "$SCRIPT_DIR"
    fi

    # Create ritzlib symlink if needed
    if [ ! -L "ritzlib" ] && [ ! -d "ritzlib" ]; then
        ln -s ritz/ritzlib ritzlib
    fi

    # Build
    ./ritz/ritz build .

    info "ritz-lsp built successfully: $SCRIPT_DIR/build/debug/ritz-lsp"
}

# =============================================================================
# Install binary
# =============================================================================
install_binary() {
    info "Installing ritz-lsp to $INSTALL_DIR..."

    mkdir -p "$INSTALL_DIR"
    cp "$SCRIPT_DIR/build/debug/ritz-lsp" "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/ritz-lsp"

    # Check if INSTALL_DIR is in PATH
    if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        warn "$INSTALL_DIR is not in your PATH."
        warn "Add this to your shell rc file:"
        warn "  export PATH=\"\$PATH:$INSTALL_DIR\""
    fi

    info "ritz-lsp installed to $INSTALL_DIR/ritz-lsp"
}

# =============================================================================
# Configure coc.nvim
# =============================================================================
configure_coc() {
    info "Configuring coc.nvim for ritz-lsp..."

    local COC_SETTINGS="$HOME/.vim/coc-settings.json"
    local RITZ_LSP_PATH="$INSTALL_DIR/ritz-lsp"

    # Check if ritz-lsp is installed
    if [ ! -f "$RITZ_LSP_PATH" ]; then
        RITZ_LSP_PATH="$SCRIPT_DIR/build/debug/ritz-lsp"
    fi

    if [ ! -f "$RITZ_LSP_PATH" ]; then
        warn "ritz-lsp binary not found. Run with --build first."
        return 1
    fi

    mkdir -p ~/.vim

    # Create or update coc-settings.json
    if [ -f "$COC_SETTINGS" ]; then
        # Check if ritz config already exists
        if grep -q '"ritz"' "$COC_SETTINGS"; then
            info "Ritz LSP already configured in coc-settings.json"
            return 0
        fi

        # Backup existing config
        cp "$COC_SETTINGS" "$COC_SETTINGS.bak"
        warn "Backed up existing coc-settings.json to $COC_SETTINGS.bak"

        # Try to merge (simple approach - just warn user)
        warn "Please manually add the ritz language server to your existing coc-settings.json:"
        echo ""
        echo "  \"languageserver\": {"
        echo "    \"ritz\": {"
        echo "      \"command\": \"$RITZ_LSP_PATH\","
        echo "      \"filetypes\": [\"ritz\"],"
        echo "      \"rootPatterns\": [\"ritz.toml\", \".git\"]"
        echo "    }"
        echo "  }"
        echo ""
    else
        cat > "$COC_SETTINGS" << EOF
{
  "languageserver": {
    "ritz": {
      "command": "$RITZ_LSP_PATH",
      "filetypes": ["ritz"],
      "rootPatterns": ["ritz.toml", ".git"]
    }
  }
}
EOF
        info "Created coc-settings.json with ritz-lsp configuration"
    fi
}

# =============================================================================
# Main
# =============================================================================
main() {
    echo "=========================================="
    echo "  ritz-lsp Installer"
    echo "=========================================="
    echo ""

    case "${1:-}" in
        --vim)
            install_vim_syntax
            ;;
        --build)
            build_ritz_lsp
            ;;
        --install)
            install_binary
            ;;
        --coc)
            configure_coc
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  (no args)   Install everything"
            echo "  --vim       Only install vim syntax files"
            echo "  --build     Only build ritz-lsp"
            echo "  --install   Only install binary to $INSTALL_DIR"
            echo "  --coc       Only configure coc.nvim"
            echo "  --help      Show this help"
            echo ""
            echo "Environment:"
            echo "  INSTALL_DIR  Installation directory (default: ~/.local/bin)"
            ;;
        *)
            install_vim_syntax
            build_ritz_lsp
            install_binary
            configure_coc
            echo ""
            info "Installation complete!"
            echo ""
            echo "To test, open a .ritz file in vim:"
            echo "  vim test.ritz"
            echo ""
            echo "Check LSP status with:"
            echo "  :CocInfo"
            ;;
    esac
}

main "$@"
