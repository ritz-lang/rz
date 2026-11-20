"""Which files ARE the ritz0 compiler, and their fingerprint (AGAST #3915).

`hash_ritz0_sources` is the one definition of "this ritz0": build.py's
`cache.compute_compiler_hash("ritz0")` (CAS keys, import scans) folds it in
next to the build driver files, and `emitter.fn_cache.COMPILER_HASH` (every
`.ritz.sig`) is it.  Two hand-kept copies of a directory walk used to do
this job and disagreed (cache.py hashed test_runner.py, fn_cache did not).

The file set is what ritz0's entry points can import, followed transitively:
`ritz0.py`, and `list_deps.py`, which build.py runs to pick every compile's
`--deps`.  Not a walk of ritz0/ minus exclusions: that hashed conftest.py
and the test harness (ritz0/harness/), so an edit to either invalidated
every sig and cached artifact (LARB review/5 ritz0.md N3), and it would hash
any stray scratch file dropped in ritz0/.

The scan is line-oriented, not `ast`: `ast.parse` of the 2 MB closure costs
~0.8 s and fn_cache runs this at import, once per ritz0 process; a line scan
takes ~10 ms.  `bytes.find` locates each `import` / `from` keyword and the
line is parsed around it, accepting any indentation (imports deferred into
functions count) and a parenthesised name list over several lines.  A prose
line that happens to start with `import x` only over-approximates.  It works
on bytes, and on plain `str` paths rather than `pathlib`, because this is on
the import path of every ritz0 process: pathlib object churn alone was 7 of
the first version's 17 ms.
tools/test_compiler_hash_import_graph.py checks the result equals an `ast`
walk of the real tree.
"""

import hashlib
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Run directly as programs; everything else is reached from these.
ENTRY_POINTS = ("ritz0.py", "list_deps.py")

_WS = b" \t"
_NEWLINE = 0x0A
_COMMENT = re.compile(rb"#[^\n]*")
_NAME = re.compile(rb"[\w.]+")


def _names(clause: bytes) -> List[str]:
    """`a.b as c, d` / `(x,\\n y as z)` -> ["a.b", "d"] / ["x", "y"]."""
    clause = _COMMENT.sub(b"", clause).strip().strip(b"()\\")
    out = []
    for part in clause.split(b","):
        words = part.split()
        if words and words[0] != b"*" and _NAME.fullmatch(words[0]):
            out.append(words[0].decode())
    return out


class _Resolver:
    """Where a module name lands, with ritz0's sys.path: ritz0/ (the script
    dir) first, then projects/ritz (module_interface appends it for cas)."""

    def __init__(self, ritz0_root: str):
        self.bases = (ritz0_root, os.path.dirname(ritz0_root))
        self._memo: Dict[str, List[str]] = {}  # a name is looked up once
        # One walk of ritz0/ replaces a stat per candidate module: ~2 ms for
        # 950 files against ~10 ms for the ~750 stats it answers.
        self._prefix = ritz0_root + os.sep
        self._files = set()
        for dirpath, dirnames, filenames in os.walk(ritz0_root):
            dirnames[:] = [d for d in dirnames
                           if d not in ("__pycache__", ".pytest_cache")]
            self._files.update([os.path.join(dirpath, fn) for fn in filenames])

    def _file(self, path: str) -> bool:
        """Whether `path` exists; under ritz0/ answered from the walk."""
        if path.startswith(self._prefix):
            return path in self._files
        return os.path.isfile(path)

    def _under(self, base: str, parts: List[str]) -> List[str]:
        """Files importing `parts` from `base` loads: each package's
        `__init__.py` on the way, then the module (or package) itself."""
        files = []
        for i in range(1, len(parts)):
            init = os.path.join(base, *parts[:i], "__init__.py")
            if not self._file(init):
                return []
            files.append(init)
        mod = os.path.join(base, *parts) + ".py"
        if self._file(mod):
            return files + [mod]
        pkg = os.path.join(base, *parts, "__init__.py")
        if self._file(pkg):
            return files + [pkg]
        return []

    def absolute(self, dotted: str) -> List[str]:
        try:
            return self._memo[dotted]
        except KeyError:
            pass
        parts = dotted.split(".")
        found: List[str] = []
        for base in self.bases:
            # The first base holding the top-level name wins, as on sys.path.
            if self._file(os.path.join(base, parts[0] + ".py")) or \
                    self._file(os.path.join(base, parts[0], "__init__.py")):
                found = self._under(base, parts)
                break
        self._memo[dotted] = found
        return found


def _line_start(text: bytes, i: int) -> bool:
    """`i` is the first non-blank character on its line."""
    j = i
    while j > 0 and text[j - 1] in _WS:
        j -= 1
    return j == 0 or text[j - 1] == _NEWLINE


def _clause(text: bytes, start: int) -> bytes:
    """The name list after `import`, to the end of the statement: the closing
    `)` of a parenthesised list, else end of line; comments and `;` dropped."""
    k = start
    while k < len(text) and text[k] in _WS:
        k += 1
    if k < len(text) and text[k] == 0x28:  # '('
        close = text.find(b")", k)
        end = len(text) if close == -1 else close + 1
    else:
        end = text.find(b"\n", start)
        end = len(text) if end == -1 else end
    raw = _COMMENT.sub(b"", text[start:end])
    semi = raw.find(b";")
    return raw[:semi] if semi != -1 else raw


def _statements(text: bytes) -> List[Tuple[bool, bytes, bytes]]:
    """`(is_from, module, clause)` for every import line in `text`.

    `bytes.find` rather than a regex: this runs in every ritz0 process, and
    the file it scans most (emitter_llvmlite.py, 900 kB) is twice as fast
    this way."""
    out = []
    for kw in (b"import", b"from"):
        i = text.find(kw)
        while i != -1:
            j = i + len(kw)
            if j < len(text) and text[j] in _WS and _line_start(text, i):
                if kw == b"import":
                    out.append((False, b"", _clause(text, j)))
                else:
                    k = j
                    while k < len(text) and text[k] in _WS:
                        k += 1
                    m = k
                    while m < len(text) and text[m] not in _WS \
                            and text[m] != _NEWLINE:
                        m += 1
                    q = m
                    while q < len(text) and text[q] in _WS:
                        q += 1
                    if text.startswith(b"import", q) and q + 6 < len(text) \
                            and text[q + 6] in _WS:
                        out.append((True, text[k:m], _clause(text, q + 6)))
            i = text.find(kw, i + 1)
    return out


def _imports_of(path: str, text: bytes, res: _Resolver) -> List[str]:
    found: List[str] = []
    for is_from, module, clause in _statements(text):
        names = _names(clause)
        if not is_from:
            for name in names:
                found += res.absolute(name)
            continue
        module = module.decode()
        dots = len(module) - len(module.lstrip("."))
        module = module[dots:]
        if not dots:
            if not module:
                continue
            found += res.absolute(module)
            for n in names:  # `from pkg import submodule`
                found += res.absolute(f"{module}.{n}")
            continue
        base = os.path.dirname(path)  # `from .x`: this package; one up per dot
        for _ in range(dots - 1):
            base = os.path.dirname(base)
        parts = module.split(".") if module else []
        if parts:
            found += res._under(base, parts)
        else:
            init = os.path.join(base, "__init__.py")
            if os.path.isfile(init):
                found.append(init)
        for n in names:
            found += res._under(base, parts + [n])
    return found


def _closure(ritz0_root) -> Tuple[str, Dict[str, bytes]]:
    """`(parent, {path relative to parent: file bytes})` for every file the
    entry points reach.  Keys stay relative because the digest needs each
    path next to its bytes, and `projects/ritz` is the one root every path
    is taken from."""
    root = os.path.abspath(os.fspath(ritz0_root))
    parent = os.path.dirname(root)
    res = _Resolver(root)
    raw: Dict[str, bytes] = {}
    name = os.path.basename(root)
    todo = [os.path.join(name, e) for e in ENTRY_POINTS
            if os.path.isfile(os.path.join(root, e))]
    while todo:
        rel = os.path.normpath(todo.pop())
        if rel in raw:
            continue
        path = os.path.join(parent, rel)
        with open(path, "rb") as fh:
            data = fh.read()
        raw[rel] = data
        todo += [os.path.relpath(f, parent) for f in _imports_of(path, data, res)]
    return parent, raw


def ritz0_sources(ritz0_root) -> List[Path]:
    """Every file ritz0's entry points can import, sorted by its path
    relative to projects/ritz (the parent of `ritz0_root`).

    Paths are absolute but leave symlinks unresolved: a test copies ritz0/
    elsewhere and symlinks the drivers beside it, and those copies must stay
    under their own root."""
    parent, raw = _closure(ritz0_root)
    return [Path(parent, rel) for rel in sorted(raw)]


def hash_ritz0_sources(ritz0_root) -> str:
    """Hex sha256 over `ritz0_sources`: each file's relative path and bytes."""
    parent, raw = _closure(ritz0_root)
    h = hashlib.sha256(b"ritz0-sources\n")
    for rel in sorted(raw):
        h.update(rel.replace(os.sep, "/").encode() + b"\0")
        h.update(raw[rel])
        h.update(b"\0")
    return h.hexdigest()
