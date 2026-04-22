"""
Per-function incremental compilation cache.

JADE-inspired token hashing: hash each function's token stream (ignoring
whitespace/comments) to detect which functions actually changed. Functions
whose hash is unchanged can reuse cached LLVM IR.

Key components:
  - fn_token_hash(): Hash a function's token stream (SHA-256, 16 hex chars)
  - source_file_hash(): Hash entire source file contents
  - build_hash_map(): Parse a source file, hash every function -> {name: hash}
  - .ritz.sig file I/O: read_sig_file() / write_sig_file()
  - check_cache(): Compare current vs cached hashes -> (hits, misses)
  - invalidate_dependents(): Propagate signature changes to importers

.ritz.sig format (JSON):
{
  "source_hash": "<sha256 of source file>",
  "functions": {
    "fn_name": {
      "hash": "<token hash>",
      "sig_hash": "<signature-only hash>",
      "ir": "<cached LLVM IR for this function>"
    }
  },
  "imports": ["ritzlib.sys", "ritzlib.io"]
}
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Ensure ritz0 dir is in path for local imports
_ritz0_dir = str(Path(__file__).parent.parent)
if _ritz0_dir not in sys.path:
    sys.path.insert(0, _ritz0_dir)

from tokens import TokenType


# ============================================================================
# Token Hashing
# ============================================================================

# Token types to SKIP when hashing (whitespace/formatting tokens).
# Comments are already stripped by the lexer, so they never appear.
_SKIP_TOKENS = frozenset({
    TokenType.NEWLINE,
    TokenType.INDENT,
    TokenType.DEDENT,
})


def fn_token_hash(tokens: list) -> str:
    """Hash a function's token stream, ignoring whitespace/indent tokens.

    Args:
        tokens: List of Token objects from the lexer for one function body

    Returns:
        16-char hex string (first 64 bits of SHA-256)
    """
    h = hashlib.sha256()
    for tok in tokens:
        if tok.type in _SKIP_TOKENS:
            continue
        # Hash token type name and value
        h.update(tok.type.name.encode('utf-8'))
        if tok.value is not None:
            h.update(str(tok.value).encode('utf-8'))
    return h.hexdigest()[:16]


def sig_token_hash(tokens: list) -> str:
    """Hash only the signature portion of a function's tokens.

    The signature includes everything up to and including the return type,
    but excludes the function body. This is used to detect when a function's
    interface changes (requiring recompilation of callers).

    For simplicity, we hash: fn name, params, return type annotation.

    Args:
        tokens: List of Token objects for the full function definition

    Returns:
        16-char hex string (first 64 bits of SHA-256)
    """
    h = hashlib.sha256()
    # Hash tokens up to the first INDENT (which starts the body)
    for tok in tokens:
        if tok.type == TokenType.INDENT:
            break
        if tok.type in _SKIP_TOKENS:
            continue
        h.update(tok.type.name.encode('utf-8'))
        if tok.value is not None:
            h.update(str(tok.value).encode('utf-8'))
    return h.hexdigest()[:16]


def source_file_hash(source: str) -> str:
    """Hash entire source file contents.

    Args:
        source: Source file text

    Returns:
        16-char hex string (first 64 bits of SHA-256)
    """
    return hashlib.sha256(source.encode('utf-8')).hexdigest()[:16]


# ============================================================================
# Hash Map Building
# ============================================================================

def build_hash_map(source: str, source_path: str = "<unknown>") -> Dict[str, str]:
    """Parse a source file and hash every function.

    Args:
        source: Source code text
        source_path: File path (for lexer error messages)

    Returns:
        Dict mapping function names to their token hashes
    """
    from lexer import Lexer
    from parser import Parser

    lexer = Lexer(source, source_path)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    module = parser.parse_module()

    # Re-lex to get raw tokens for hashing
    lexer2 = Lexer(source, source_path)
    all_tokens = lexer2.tokenize()

    hash_map = {}
    import ritz_ast as rast
    for item in module.items:
        if isinstance(item, rast.FnDef):
            # Get tokens for this function by span range
            fn_tokens = _extract_fn_tokens(all_tokens, item)
            hash_map[item.name] = fn_token_hash(fn_tokens)

    return hash_map


def build_sig_hash_map(source: str, source_path: str = "<unknown>") -> Dict[str, str]:
    """Parse a source file and compute signature hashes for every pub function.

    Args:
        source: Source code text
        source_path: File path (for lexer error messages)

    Returns:
        Dict mapping pub function names to their signature hashes
    """
    from lexer import Lexer
    from parser import Parser

    lexer = Lexer(source, source_path)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    module = parser.parse_module()

    # Re-lex to get raw tokens for hashing
    lexer2 = Lexer(source, source_path)
    all_tokens = lexer2.tokenize()

    sig_map = {}
    import ritz_ast as rast
    for item in module.items:
        if isinstance(item, rast.FnDef) and getattr(item, 'is_pub', False):
            fn_tokens = _extract_fn_tokens(all_tokens, item)
            sig_map[item.name] = sig_token_hash(fn_tokens)

    return sig_map


def _extract_fn_tokens(all_tokens: list, fn_def) -> list:
    """Extract tokens belonging to a specific function definition.

    Uses the function's span (line range) to filter tokens.

    Args:
        all_tokens: All tokens from the source file
        fn_def: The FnDef AST node with span information

    Returns:
        List of tokens for this function
    """
    span = getattr(fn_def, 'span', None)
    if span is None:
        return []

    fn_line = span.line
    # Find the end of this function by looking at indentation
    # Function body is everything from the fn line until we see a dedent
    # back to the same or lesser indentation level.
    # Simple heuristic: collect tokens from fn_line until we see a token
    # on a new line at column 1 (or 0) that isn't part of the function.
    fn_tokens = []
    in_function = False
    indent_depth = 0

    for tok in all_tokens:
        if tok.type == TokenType.EOF:
            break

        tok_line = tok.span.line if hasattr(tok.span, 'line') else 0

        if tok_line == fn_line and tok.type == TokenType.FN:
            in_function = True

        if in_function:
            fn_tokens.append(tok)

            if tok.type == TokenType.INDENT:
                indent_depth += 1
            elif tok.type == TokenType.DEDENT:
                indent_depth -= 1
                if indent_depth <= 0:
                    break

    return fn_tokens


# ============================================================================
# .ritz.sig File I/O
# ============================================================================

def _sig_path(source_path: str) -> Path:
    """Get the .ritz.sig path for a source file.

    .ritz.sig files live alongside source files:
      foo.ritz -> foo.ritz.sig

    Args:
        source_path: Path to the source file

    Returns:
        Path to the .ritz.sig file
    """
    return Path(source_path).with_suffix('.ritz.sig')


def read_sig_file(source_path: str) -> Optional[Dict[str, Any]]:
    """Read a .ritz.sig file, returning None on missing/corrupt.

    Args:
        source_path: Path to the source file (not the .sig file)

    Returns:
        Parsed sig data dict, or None if not available
    """
    sig_file = _sig_path(source_path)
    try:
        if not sig_file.exists():
            return None
        data = json.loads(sig_file.read_text())
        # Validate structure
        if not isinstance(data, dict):
            return None
        if 'functions' not in data:
            return None
        return data
    except (json.JSONDecodeError, OSError):
        return None


def write_sig_file(source_path: str, data: Dict[str, Any]) -> None:
    """Write a .ritz.sig file.

    Args:
        source_path: Path to the source file (not the .sig file)
        data: Sig data dict to write
    """
    sig_file = _sig_path(source_path)
    try:
        sig_file.write_text(json.dumps(data, indent=2) + '\n')
    except OSError as e:
        print(f"Warning: could not write {sig_file}: {e}", file=sys.stderr)


def delete_sig_file(source_path: str) -> None:
    """Delete a .ritz.sig file (invalidation).

    Args:
        source_path: Path to the source file
    """
    sig_file = _sig_path(source_path)
    try:
        if sig_file.exists():
            sig_file.unlink()
    except OSError:
        pass


# ============================================================================
# Cache Detection
# ============================================================================

def check_cache(
    current_hashes: Dict[str, str],
    sig_data: Optional[Dict[str, Any]]
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Compare current function hashes against cached hashes.

    Args:
        current_hashes: {fn_name: hash} from build_hash_map()
        sig_data: Parsed .ritz.sig data (or None if no cache)

    Returns:
        (hits, misses) where:
          hits: {fn_name: hash} for functions with matching hash (cached IR reusable)
          misses: {fn_name: hash} for functions that need re-emission
    """
    hits = {}
    misses = {}

    if sig_data is None:
        # No cache at all - everything is a miss
        return {}, dict(current_hashes)

    cached_fns = sig_data.get('functions', {})

    for fn_name, current_hash in current_hashes.items():
        cached_entry = cached_fns.get(fn_name)
        if cached_entry and cached_entry.get('hash') == current_hash:
            hits[fn_name] = current_hash
        else:
            misses[fn_name] = current_hash

    return hits, misses


def get_cached_ir(fn_name: str, sig_data: Dict[str, Any]) -> Optional[str]:
    """Get cached LLVM IR for a function if available.

    Args:
        fn_name: Function name
        sig_data: Parsed .ritz.sig data

    Returns:
        Cached IR string, or None if not cached
    """
    cached_fns = sig_data.get('functions', {})
    entry = cached_fns.get(fn_name)
    if entry and 'ir' in entry and entry['ir']:
        return entry['ir']
    return None


def check_source_hash(source: str, source_path: str) -> bool:
    """Check if the source file hash matches the cached hash.

    Args:
        source: Source file contents
        source_path: Path to the source file

    Returns:
        True if the source hasn't changed (hash matches cache)
    """
    sig_data = read_sig_file(source_path)
    if sig_data is None:
        return False

    cached_hash = sig_data.get('source_hash')
    if cached_hash is None:
        return False

    current_hash = source_file_hash(source)
    return current_hash == cached_hash


def build_sig_data(
    source: str,
    fn_hashes: Dict[str, str],
    sig_hashes: Optional[Dict[str, str]] = None,
    fn_ir: Optional[Dict[str, str]] = None,
    imports: Optional[List[str]] = None,
    old_sig_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a .ritz.sig data dict.

    Args:
        source: Source file contents (for source hash)
        fn_hashes: {fn_name: body_hash}
        sig_hashes: {fn_name: sig_hash} (optional, for pub functions)
        fn_ir: {fn_name: ir_text} (optional, cached IR)
        imports: List of import paths (e.g., ["ritzlib.sys"])
        old_sig_data: Previous sig data (to preserve cached IR for unchanged fns)

    Returns:
        Dict suitable for write_sig_file()
    """
    sig_hashes = sig_hashes or {}
    fn_ir = fn_ir or {}
    imports = imports or []

    # Merge with old data: preserve cached IR for unchanged functions
    old_fns = {}
    if old_sig_data:
        old_fns = old_sig_data.get('functions', {})

    functions = {}
    for fn_name, body_hash in fn_hashes.items():
        entry = {
            'hash': body_hash,
        }
        if fn_name in sig_hashes:
            entry['sig_hash'] = sig_hashes[fn_name]

        # Use new IR if provided, else preserve old IR if hash unchanged
        if fn_name in fn_ir:
            entry['ir'] = fn_ir[fn_name]
        elif fn_name in old_fns and old_fns[fn_name].get('hash') == body_hash:
            entry['ir'] = old_fns[fn_name].get('ir', '')
        else:
            entry['ir'] = ''

        functions[fn_name] = entry

    return {
        'source_hash': source_file_hash(source),
        'functions': functions,
        'imports': imports,
    }


# ============================================================================
# Signature Change Propagation
# ============================================================================

def detect_sig_changes(
    source_path: str,
    new_sig_hashes: Dict[str, str],
) -> List[str]:
    """Detect which pub function signatures changed since last compilation.

    Args:
        source_path: Path to the source file
        new_sig_hashes: {fn_name: new_sig_hash} for pub functions

    Returns:
        List of function names whose signature changed
    """
    old_data = read_sig_file(source_path)
    if old_data is None:
        # No previous cache - all signatures are "new"
        return list(new_sig_hashes.keys())

    changed = []
    old_fns = old_data.get('functions', {})

    for fn_name, new_hash in new_sig_hashes.items():
        old_entry = old_fns.get(fn_name)
        if old_entry is None:
            changed.append(fn_name)
        elif old_entry.get('sig_hash') != new_hash:
            changed.append(fn_name)

    # Also check for removed functions
    for fn_name in old_fns:
        if fn_name not in new_sig_hashes and old_fns[fn_name].get('sig_hash'):
            changed.append(fn_name)

    return changed


def invalidate_dependents(
    source_path: str,
    changed_sigs: List[str],
    project_root: Optional[str] = None,
) -> List[str]:
    """Invalidate .ritz.sig caches of modules that import a changed module.

    When a module's pub function signatures change, any module that imports
    it may need recompilation (since it may call those functions).

    Strategy: scan all .ritz.sig files in the project, check their 'imports'
    list, and delete sig files for modules that import the changed module.

    Args:
        source_path: Path to the module whose signatures changed
        changed_sigs: List of changed function names (for logging)
        project_root: Project root directory to search for sig files

    Returns:
        List of paths whose .ritz.sig was invalidated
    """
    if not changed_sigs:
        return []

    source_abs = str(Path(source_path).resolve())
    # Derive the module import path from the file path
    # e.g., /path/to/ritzlib/sys.ritz -> ritzlib.sys
    module_import_name = _path_to_import_name(source_abs, project_root)

    if not module_import_name:
        return []

    # Find all .ritz.sig files in the project
    if project_root:
        search_root = Path(project_root)
    else:
        search_root = Path(source_path).parent

    invalidated = []
    for sig_file in search_root.rglob('*.ritz.sig'):
        try:
            data = json.loads(sig_file.read_text())
            imports = data.get('imports', [])
            if module_import_name in imports:
                # This module imports the changed module - invalidate its cache
                sig_file.unlink()
                invalidated.append(str(sig_file))
        except (json.JSONDecodeError, OSError):
            continue

    return invalidated


def _path_to_import_name(source_path: str, project_root: Optional[str] = None) -> Optional[str]:
    """Convert a file path to its import module name.

    e.g., /path/to/project/ritzlib/sys.ritz -> ritzlib.sys

    Args:
        source_path: Absolute path to source file
        project_root: Project root directory

    Returns:
        Import name string, or None if cannot determine
    """
    source = Path(source_path)

    if project_root:
        root = Path(project_root)
        try:
            rel = source.relative_to(root)
            # Convert path to import name: ritzlib/sys.ritz -> ritzlib.sys
            parts = list(rel.parts)
            if parts and parts[-1].endswith('.ritz'):
                parts[-1] = parts[-1][:-5]  # Strip .ritz extension
            return '.'.join(parts)
        except ValueError:
            pass

    # Fallback: try to find ritzlib in the path
    parts = source.parts
    for i, part in enumerate(parts):
        if part == 'ritzlib':
            remaining = list(parts[i:])
            if remaining[-1].endswith('.ritz'):
                remaining[-1] = remaining[-1][:-5]
            return '.'.join(remaining)

    return None
