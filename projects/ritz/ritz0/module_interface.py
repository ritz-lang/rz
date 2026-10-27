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

`k = sha256(schema, parser fingerprint, absolute path, source sha256)`. The
absolute path is in the key because spans carry it (diagnostics, assert
messages in kept bodies). The parser fingerprint hashes the files that
produce the AST (tokens, lexer, parser, ritz_ast, this file), so a parser
change can never return an interface from the old one.

Pickle is ritz0-private: the store is the user's own cache directory, and the
fingerprint pins the exact class definitions. ritz1 needs a language-neutral
encoding of the same content (follow-up ticket).

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

def parse_source(source: str, path: str) -> rast.Module:
    """Lex and parse one module. Every compiler-path parse goes through here."""
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
        parser = Parser(tokens, source=source)
    except TypeError:
        parser = Parser(tokens)
    return parser.parse_module()


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
    iface = strip_module(parse_source(source_bytes.decode(), abs_path))
    digest = hash_interface(iface)
    try:
        cas._atomic_write(store.path(key, IFACE_EXT),
                          pickle.dumps((digest, iface), pickle.HIGHEST_PROTOCOL))
        cas._atomic_write(store.path(key, HASH_EXT), digest.encode())
    except (OSError, pickle.PicklingError, RecursionError) as e:
        print(f"Warning: module interface not stored for {abs_path}: {e}",
              file=sys.stderr)
    return digest, iface


def _load(path: str) -> Tuple[str, rast.Module]:
    abs_path = str(Path(path).resolve())
    source_bytes = Path(abs_path).read_bytes()
    key = _store_key(abs_path, source_bytes)
    store = cas.ArtifactStore()
    hit = _get(store, key, IFACE_EXT)
    if hit is not None:
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
        if hit is not None:
            digest = hit.read_text().strip()
        if not digest:
            digest = _build(str(p), source_bytes, key, store)[0]
        _HASH_MEMO[memo] = digest
    return digest
