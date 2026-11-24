"""Capture ritz0's refusals from the ritz0-only test files (AGAST #4669).

Self-hosting goal 3 is "ritz1 rejects everything ritz0 rejects".  Most of
ritz0/tests runs ritz1 beside ritz0, but a file that never mentions ritz1
checks ritz0 alone, and every goal-3 gap survey #4631 found was in one of
those files.  This module records what such a file feeds ritz0, so
tools/refusal_parity.py can replay it through ritz1 after the suite.

It is off unless RITZ_REFUSAL_CAPTURE names a directory (main.yml's "ritz0
unit tests" step sets it; `make unit` does not), and then records two kinds
of program, both only for a test in a ritz0-only file (`ritz0_only`):

* `cli`: a `run_ritz0` compile that ritz0 refused (exit > 0).  The source's
  directory is copied (a test's tmp_path is gone by replay time), with the
  compile's RITZ_PATH when it is RITZ_ROOT or inside that directory.
* `inproc`: every source string the pytest process lexes under a name that
  is not a `.ritz` file -- the parser- and type-checker-level tests, which
  never run the CLI.  Their ritz0 verdict is unknown here (a test may only
  parse), so the replay compiles each with ritz0's CLI first and keeps the
  ones it refuses.

Records are JSON lines in <dir>/records-<pid>.jsonl, one file per process
(xdist workers never share one); sources go under <dir>/src/.  Each record
carries the test id, `tests/test_x.py::name[param]`, the key the known-gaps
list (known-failures/, gate `refusal`) uses.

Cost: one `os.environ` lookup per compile and per Lexer when off; when on,
a small copy per refusal and a write per distinct in-process source.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import uuid
from pathlib import Path

ENV = "RITZ_REFUSAL_CAPTURE"
RITZ0_DIR = Path(__file__).resolve().parent.parent
RITZ_ROOT = RITZ0_DIR.parent

# A test file that names ritz1 (a binary, a fixture, a module) runs it, or
# says why not; one that never does checks ritz0 alone.  "ritz1" also
# matches ritz1_selfhosted and ritz1_bin.
_RITZ1 = re.compile(r"ritz1")
# Largest source directory worth copying: a test's tmp_path holds a program
# or a small package, not a tree.
MAX_COPY_BYTES = 2 << 20
MAX_COPY_FILES = 400

_only_cache: dict[str, bool] = {}
_seen_sources: set[str] = set()


def capture_dir() -> Path | None:
    d = os.environ.get(ENV)
    return Path(d) if d else None


def current_test() -> str | None:
    """`tests/test_x.py::name[param]` for the running test, or None."""
    cur = os.environ.get("PYTEST_CURRENT_TEST")
    if not cur:
        return None
    # "tests/test_x.py::name[param] (call)": drop the phase.
    return cur.rsplit(" (", 1)[0]


def ritz0_only(test_id: str) -> bool:
    """Is the test's file one that never runs ritz1?"""
    rel = test_id.split("::", 1)[0]
    hit = _only_cache.get(rel)
    if hit is None:
        try:
            text = (RITZ0_DIR / rel).read_text(errors="replace")
        except OSError:
            text = "ritz1"  # unknown file: not ours to judge
        hit = _only_cache[rel] = _RITZ1.search(text) is None
    return hit


def _record(dirpath: Path, rec: dict) -> None:
    dirpath.mkdir(parents=True, exist_ok=True)
    line = json.dumps(rec, sort_keys=True) + "\n"
    with open(dirpath / f"records-{os.getpid()}.jsonl", "a") as f:
        f.write(line)


def _small_tree(d: Path) -> bool:
    total = 0
    n = 0
    for p in d.rglob("*"):
        if p.is_file():
            n += 1
            total += p.stat().st_size
            if n > MAX_COPY_FILES or total > MAX_COPY_BYTES:
                return False
    return True


def _source_arg(args: list[str]) -> str | None:
    """The one `.ritz` source a CLI compile names, else None."""
    srcs = [a for a in args if a.endswith(".ritz") and not a.startswith("-")]
    return srcs[0] if len(srcs) == 1 else None


def on_cli(args: list[str], cwd: str | None, env: dict, rc: int | None,
           stderr: bytes) -> None:
    """`run_ritz0` finished: record it if ritz0 refused a ritz0-only test's program."""
    dirpath = capture_dir()
    if dirpath is None or rc is None or rc <= 0:
        return
    test = current_test()
    if test is None or not ritz0_only(test):
        return
    rec = {"kind": "cli", "test": test, "args": args, "rc": rc,
           "stderr": stderr.decode(errors="replace")[-4000:]}
    src_s = _source_arg(args)
    src = Path(cwd or ".", src_s).resolve() if src_s else None
    if src is None or not src.is_file():
        rec["skip"] = "no single .ritz source on the command line"
        _record(dirpath, rec)
        return
    root = src.parent
    if root in (RITZ_ROOT, RITZ0_DIR) or not _small_tree(root):
        rec["skip"] = f"source directory {root} is not a test's own"
        _record(dirpath, rec)
        return
    dest = dirpath / "src" / uuid.uuid4().hex
    shutil.copytree(root, dest, symlinks=True,
                    ignore=shutil.ignore_patterns("*.ll", "*.o", ".ritz-cache*"))
    rec["dir"] = str(dest.relative_to(dirpath))
    rec["source"] = src.name
    ritz_path = env.get("RITZ_PATH")
    if ritz_path:
        rec["ritz_path"] = [_portable(c, root) for c in ritz_path.split(":") if c]
    _record(dirpath, rec)


def _portable(component: str, root: Path) -> str:
    """One RITZ_PATH entry as the replay can rebuild it: RITZ_ROOT, a
    directory inside the copied source directory, or `@OTHER` (dropped)."""
    rp = Path(component).resolve()
    if rp == RITZ_ROOT:
        return "@RITZ_ROOT"
    if rp == root or root in rp.parents:
        return "@DIR/" + str(rp.relative_to(root))
    return "@OTHER"


def on_lex(source: str, filename: str) -> None:
    """A Lexer was built in the pytest process: record an in-process source."""
    dirpath = capture_dir()
    if dirpath is None or filename.endswith(".ritz") or "_pytest" not in sys.modules:
        return
    test = current_test()
    if test is None or not ritz0_only(test) or not source.strip():
        return
    digest = hashlib.sha256(source.encode()).hexdigest()[:20]
    key = f"{test}\0{digest}"
    if key in _seen_sources:
        return
    _seen_sources.add(key)
    dest = dirpath / "src" / "inproc"
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"{digest}.ritz"
    if not path.exists():
        tmp = path.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(source)
        os.replace(tmp, path)
    _record(dirpath, {"kind": "inproc", "test": test,
                      "source": str(path.relative_to(dirpath))})


MARKER = "capture-on"


def on_test_ran(nodeid: str) -> None:
    """A test finished its call phase: the replay's "ran" set (strict xpass
    needs to know a listed test ran, not only that it captured nothing)."""
    dirpath = capture_dir()
    if dirpath is None or not ritz0_only(nodeid):
        return
    _record(dirpath, {"kind": "ran", "test": nodeid})


def install_lexer_hook() -> None:
    """Mark the capture as live, and wrap Lexer.__init__ (the class every
    `from lexer import Lexer` shares).  The marker is what tells the replay
    the hook ran: without it, an empty capture is a broken capture."""
    dirpath = capture_dir()
    if dirpath is None:
        return
    dirpath.mkdir(parents=True, exist_ok=True)
    (dirpath / MARKER).touch()
    import lexer
    cls = lexer.Lexer
    if getattr(cls.__init__, "_refusal_capture", False):
        return
    orig = cls.__init__

    def __init__(self, source, filename="<stdin>", *a, **kw):
        orig(self, source, filename, *a, **kw)
        if isinstance(source, str):
            try:
                on_lex(source, str(filename))
            except OSError as e:  # a full disk must not fail the test
                print(f"refusal_capture: {e}", file=sys.stderr)

    __init__._refusal_capture = True
    cls.__init__ = __init__
