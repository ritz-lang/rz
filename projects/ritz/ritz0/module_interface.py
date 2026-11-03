"""Module interfaces for separate compilation (G9, AGAST #1810).

Compiling one module used to lex and parse its whole transitive import
closure. An imported module only contributes *declarations* to the
importer's IR, though: `emitter_llvmlite._should_emit_body` emits bodies for
the current file only. The exceptions are bodies the importer instantiates
itself -- generic fns and methods of generic impls (monomorphised locally,
`linkonce_odr`) and async fns (state-machine transform runs on the merged
module).

So an imported module is loaded as its *interface*: the parsed module with
every other fn body replaced by an empty block. Everything else is kept
verbatim -- structs, enums, consts, type aliases, traits (default method
bodies), module vars, externs, static asserts and the module's own imports
(re-exports, aliases) -- so `ImportResolver` processes an interface exactly
as it processed the full module.

Storage
-------
Interfaces live in the G7 artifact store (`cas.py`, $RITZ_CACHE_DIR):

    objects/<k[:2]>/<k>.rzi    pickled (interface_hash, stripped Module)
    objects/<k[:2]>/<k>.rzih   interface hash, hex text
    objects/<t[:2]>/<t>.rzi.ritz  interface text (ritz1 reads it), t = text_key

`k = sha256(schema, parser fingerprint, absolute path, source sha256)`. The
absolute path is in the key because spans carry it (diagnostics, assert
messages in kept bodies). The parser fingerprint hashes the files that
produce the AST (tokens, lexer, parser, ritz_ast, this file), so a parser
change can never return an interface from the old one.

Pickle is ritz0-private: the store is the user's own cache directory, and the
fingerprint pins the exact class definitions. Next to it goes the interface
as Ritz source, `<t>.rzi.ritz`, under a key of the source bytes alone (see
"Interface text" below, AGAST #1901): ritz1 parses that instead of the import
when it is stored. Either way ritz1 strips each import in memory by the rule
of `body_needed` (ritz1/src/main.ritz strip_to_interface, AGAST #1899), which
is why `build.cas_module_key` may key ritz1 objects on these interface hashes
too. Keep `body_needed` and strip_to_interface in step: ritz1 must strip at
least what this keeps out.

Interface hash
--------------
What an importer's artifact key depends on (`build.cas_module_key`). A
canonical walk of the interface that omits source positions *outside* kept
bodies: positions of declarations never reach the importer's IR (DWARF
subprograms are emitted only for defined functions), so a body-only edit --
even one that shifts every later line -- keeps the hash. Positions inside
kept bodies do reach it (debug locations of the local instantiation) and are
hashed, without the file name (the importer's key carries the module
identity separately, worktree-independent).

Instrumentation
---------------
`PARSED` lists every source this process parsed; `RITZ0_PARSE_LOG=<file>`
appends each path to a file, across processes. `RITZ0_NO_INTERFACES=1` turns
interfaces off (full parse of every import, the pre-G9 behaviour).
"""

from __future__ import annotations

import copy
import enum
import hashlib
import os
import pickle
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import ritz_ast as rast
from lexer import Lexer
from parser import Parser
from tokens import Span

_RITZ_DIR = Path(__file__).resolve().parent.parent
if str(_RITZ_DIR) not in sys.path:
    sys.path.append(str(_RITZ_DIR))
import cas  # noqa: E402  (projects/ritz/cas.py, the G7 store)

SCHEMA = "ritz0-iface-v1"
DISABLE_ENV = "RITZ0_NO_INTERFACES"
PARSE_LOG_ENV = "RITZ0_PARSE_LOG"
IFACE_EXT = "rzi"
HASH_EXT = "rzih"

# Paths of every source parsed by this process, in order.
PARSED: List[str] = []
# (abs path, size, mtime_ns) -> interface hash, for this process.
_HASH_MEMO: Dict[tuple, str] = {}
_FINGERPRINT: Optional[str] = None

# The files whose code determines the parsed AST and its stripping.
_FINGERPRINT_FILES = ("tokens.py", "lexer.py", "parser.py", "ritz_ast.py",
                      "module_interface.py")


def enabled() -> bool:
    return os.environ.get(DISABLE_ENV, "") in ("", "0")


def parser_fingerprint() -> str:
    global _FINGERPRINT
    if _FINGERPRINT is None:
        h = hashlib.sha256(SCHEMA.encode())
        h.update(f"py{sys.version_info[0]}.{sys.version_info[1]}".encode())
        here = Path(__file__).resolve().parent
        for name in _FINGERPRINT_FILES:
            h.update(name.encode())
            h.update((here / name).read_bytes())
        _FINGERPRINT = h.hexdigest()
    return _FINGERPRINT


# ============================================================================
# Parsing (instrumented)
# ============================================================================

def _parse_with_tokens(source: str, path: str) -> Tuple[list, rast.Module]:
    PARSED.append(path)
    log = os.environ.get(PARSE_LOG_ENV)
    if log:
        try:
            with open(log, "a") as f:
                f.write(path + "\n")
        except OSError:
            pass
    tokens = Lexer(source, path).tokenize()
    try:
        parser = Parser(list(tokens), source=source)
    except TypeError:
        parser = Parser(list(tokens))
    return tokens, parser.parse_module()


def parse_source(source: str, path: str) -> rast.Module:
    """Lex and parse one module. Every compiler-path parse goes through here."""
    return _parse_with_tokens(source, path)[1]


# ============================================================================
# Stripping
# ============================================================================

def body_needed(fn: rast.FnDef, impl: Optional[rast.ImplBlock] = None) -> bool:
    """Does an importer need this fn's body? See the module docstring."""
    if fn.type_params or getattr(fn, "is_async", False):
        return True
    return bool(impl is not None and impl.type_params)


def _stripped(fn: rast.FnDef) -> rast.FnDef:
    new = copy.copy(fn)
    new.body = rast.Block(fn.body.span, [], None)
    return new


def strip_module(module: rast.Module) -> rast.Module:
    """The interface of `module`: a new Module; `module` is not modified."""
    items = []
    for item in module.items:
        if isinstance(item, rast.FnDef) and not body_needed(item):
            item = _stripped(item)
        elif isinstance(item, rast.ImplBlock) and any(
                not body_needed(m, item) for m in item.methods):
            impl = copy.copy(item)
            impl.methods = [m if body_needed(m, item) else _stripped(m)
                            for m in item.methods]
            item = impl
        items.append(item)
    return rast.Module(module.span, items)


# ============================================================================
# Interface text (G9c, AGAST #1901)
# ============================================================================
#
# The interface as Ritz source, which ritz1 reads (ritz1/src/main.ritz
# load_and_parse) instead of parsing the import itself. It is the source with
# every fn `strip_module` strips turned into a declaration-only fn
# (LANGUAGE_SPEC §5.3, AGAST #1900):
#
#   - the header is kept verbatim up to its last token (a trailing comment
#     goes), and ` = extern` is appended;
#   - every line of the body is emptied: the lines after the header up to the
#     last line, before the next code line indented no deeper than the fn's
#     own line, that is indented deeper. Blank and comment-only lines don't
#     end a body (the lexer emits no INDENT/DEDENT for them either);
#   - everything else is byte-for-byte the source.
#
# Line numbers and columns of everything kept are therefore the source's, so
# the interface parses to the stripped module with the source's spans, and
# the reader names the import's real path in diagnostics: the text holds no
# path. Kept as written, besides what body_needed keeps: [[test]] fns, which
# can't be declaration-only (ritz1 strips them after parsing anyway, and
# ritz0's importers never read them).
#
# The text is a function of the source bytes alone, so it is stored under a
# key both compilers compute without knowing anything of the writer:
#
#   objects/<k[:2]>/<k>.rzi.ritz
#   k = sha256_hex(TEXT_SCHEMA + "\n" + sha256_hex(source bytes))
#
# TEXT_SCHEMA changes whenever the stripping rule does. ritz1 must use
# the same constant (ritz1/src/main.ritz IFACE_TEXT_SCHEMA).

TEXT_SCHEMA = "ritz-iface-text-v1"
TEXT_EXT = "rzi.ritz"


def text_key(source_bytes: bytes) -> str:
    """Store key of the interface text of a module with these bytes."""
    inner = hashlib.sha256(source_bytes).hexdigest()
    return hashlib.sha256(f"{TEXT_SCHEMA}\n{inner}".encode()).hexdigest()


def _code_end(line: str) -> int:
    """Index where `line`'s trailing comment (if any) starts, right-trimmed."""
    quote = None
    i = 0
    while i < len(line):
        c = line[i]
        if quote:
            if c == "\\":
                i += 1
            elif c == quote:
                quote = None
        elif c in "\"'":
            quote = c
        elif c == "#":
            break
        i += 1
    return len(line[:i].rstrip())


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _fns_to_declare(module: rast.Module) -> List[rast.FnDef]:
    def wanted(fn, impl=None):
        return (not body_needed(fn, impl) and not getattr(fn, "is_decl", False)
                and not any(a.name == "test" for a in fn.attrs))
    out = []
    for item in module.items:
        if isinstance(item, rast.FnDef) and wanted(item):
            out.append(item)
        elif isinstance(item, rast.ImplBlock):
            out.extend(m for m in item.methods if wanted(m, item))
    return out


def interface_text(source: str, tokens: list, module: rast.Module) -> str:
    """The interface text of `source`, given its tokens and parsed module."""
    from tokens import TokenType
    opens = (TokenType.LPAREN, TokenType.LBRACKET)
    closes = (TokenType.RPAREN, TokenType.RBRACKET)
    layout = (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT, TokenType.EOF)
    at = {(t.span.line, t.span.column): i for i, t in enumerate(tokens)
          if t.type == TokenType.FN}
    lines = source.split("\n")
    for fn in _fns_to_declare(module):
        i = at[(fn.span.line, fn.span.column)]
        # The header: from `fn` to the first NEWLINE outside brackets.
        depth, last = 0, tokens[i]
        for t in tokens[i:]:
            if t.type in opens:
                depth += 1
            elif t.type in closes:
                depth -= 1
            elif t.type == TokenType.NEWLINE and depth == 0:
                break
            if t.type not in layout:
                last = t
        head = last.span.line  # 1-based
        base = _indent(lines[fn.span.line - 1])
        end = head
        for n in range(head + 1, len(lines) + 1):
            s = lines[n - 1]
            code = s.lstrip(" ")
            if code == "" or code.startswith("#"):
                continue
            if _indent(s) <= base:
                break
            end = n
        if end == head:
            raise ValueError(f"{fn.span}: fn '{fn.name}' has no body lines")
        h = lines[head - 1]
        lines[head - 1] = h[:_code_end(h)] + " = extern"
        for n in range(head + 1, end + 1):
            lines[n - 1] = ""
    return "\n".join(lines)


# ============================================================================
# Interface hash
# ============================================================================

def _canon(obj, out: list, keep_spans: bool) -> None:
    """Deterministic token stream of an AST value (no hash-seed ordering)."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        out.append(repr(obj))
    elif isinstance(obj, Span):
        out.append(f"@{obj.line}:{obj.column}:{obj.length}" if keep_spans else "@")
    elif isinstance(obj, enum.Enum):
        out.append(f"{type(obj).__name__}.{obj.name}")
    elif isinstance(obj, (list, tuple)):
        out.append("[")
        for x in obj:
            _canon(x, out, keep_spans)
        out.append("]")
    elif isinstance(obj, dict):
        out.append("{")
        for k in sorted(obj, key=repr):
            out.append(repr(k))
            _canon(obj[k], out, keep_spans)
        out.append("}")
    elif isinstance(obj, (set, frozenset)):
        out.append("<")
        for x in sorted(obj, key=repr):
            _canon(x, out, keep_spans)
        out.append(">")
    elif hasattr(obj, "__dict__"):
        if isinstance(obj, rast.FnDef) and (obj.body.stmts or obj.body.expr is not None):
            keep_spans = True  # a kept body: its positions reach the importer
        elif isinstance(obj, rast.TraitDef):
            keep_spans = True  # default methods are instantiated by importers
        out.append(type(obj).__name__ + "(")
        for k in sorted(vars(obj)):
            if k == "source_file":
                continue
            out.append(k + "=")
            _canon(getattr(obj, k), out, keep_spans)
        out.append(")")
    else:
        out.append(f"{type(obj).__name__}:{obj!r}")


def hash_interface(iface: rast.Module) -> str:
    out: list = [SCHEMA]
    for item in iface.items:
        _canon(item, out, keep_spans=False)
    return hashlib.sha256("\x00".join(out).encode()).hexdigest()


# ============================================================================
# Store
# ============================================================================

def _store_key(abs_path: str, source_bytes: bytes) -> str:
    h = hashlib.sha256()
    for part in (SCHEMA, parser_fingerprint(), abs_path,
                 hashlib.sha256(source_bytes).hexdigest()):
        h.update(part.encode())
        h.update(b"\x00")
    return h.hexdigest()


def _get(store: cas.ArtifactStore, key: str, ext: str) -> Optional[Path]:
    """Like `ArtifactStore.get`, but not counted in `cas.STATS`: those count
    compiled modules (the gate's "compiled more than once" report)."""
    p = store.path(key, ext)
    if not p.is_file():
        return None
    try:
        os.utime(p)  # least-recently-used order for `cas gc`
    except OSError:
        pass
    return p


def _build(abs_path: str, source_bytes: bytes, key: str,
           store: cas.ArtifactStore) -> Tuple[str, rast.Module]:
    source = source_bytes.decode()
    tokens, module = _parse_with_tokens(source, abs_path)
    iface = strip_module(module)
    digest = hash_interface(iface)
    try:
        # The text first: a pickle hit means the text is there too (_text_ok).
        text = interface_text(source, tokens, module)
        cas._atomic_write(store.path(text_key(source_bytes), TEXT_EXT),
                          text.encode())
        cas._atomic_write(store.path(key, IFACE_EXT),
                          pickle.dumps((digest, iface), pickle.HIGHEST_PROTOCOL))
        cas._atomic_write(store.path(key, HASH_EXT), digest.encode())
    except (OSError, pickle.PicklingError, RecursionError, KeyError, ValueError) as e:
        print(f"Warning: module interface not stored for {abs_path}: {e}",
              file=sys.stderr)
    return digest, iface


def _text_ok(store: cas.ArtifactStore, source_bytes: bytes) -> bool:
    """Is the interface text stored? Stores from before #1901 have only the
    pickle and hash: those entries are rebuilt once, to add it."""
    return store.path(text_key(source_bytes), TEXT_EXT).is_file()


def _load(path: str) -> Tuple[str, rast.Module]:
    abs_path = str(Path(path).resolve())
    source_bytes = Path(abs_path).read_bytes()
    key = _store_key(abs_path, source_bytes)
    store = cas.ArtifactStore()
    hit = _get(store, key, IFACE_EXT)
    if hit is not None and _text_ok(store, source_bytes):
        try:
            with open(hit, "rb") as f:
                digest, iface = pickle.load(f)
            return digest, iface
        except Exception:
            pass  # torn/foreign entry: rebuild over it
    return _build(abs_path, source_bytes, key, store)


def load_interface(path: str) -> rast.Module:
    """The interface of the module at `path`, parsing it only on a store miss.

    Lexer/parse errors propagate exactly as from a direct parse.
    """
    return _load(path)[1]


def interface_hash(path: str) -> str:
    """Interface hash of the module at `path` (memoised per file state)."""
    p = Path(path).resolve()
    st = p.stat()
    memo = (str(p), st.st_size, st.st_mtime_ns)
    digest = _HASH_MEMO.get(memo)
    if digest is None:
        source_bytes = p.read_bytes()
        key = _store_key(str(p), source_bytes)
        store = cas.ArtifactStore()
        hit = _get(store, key, HASH_EXT)
        if hit is not None and _text_ok(store, source_bytes):
            digest = hit.read_text().strip()
        if not digest:
            digest = _build(str(p), source_bytes, key, store)[0]
        _HASH_MEMO[memo] = digest
    return digest
